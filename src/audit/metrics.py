"""Q0.0 — the FREE audit metrics: every §1 number that costs no tokens.

`collect_free()` reads the live world-store, walks the programming grid, assembles one
real writer context and inspects the code, and returns the PHASE_Q_TASKS.md §1 table as
a nested dict. It is the cheap half of the Phase Q feedback loop (§2a): seconds to run,
no API calls, and safe against a station that is on air.

This is the production form of `scripts/audit_seed/free_metrics.py` — the throwaway
script the external audit of 2026-07-26 actually ran. The maths is deliberately kept
identical so the committed baseline is comparable with the original findings; the rough
edges the seed's README lists (hardcoded `sys.path`, no key contract, non-deterministic
ordering) are fixed here.

**The key names are a contract.** `GROUP_KEYS` declares them, Q8 reads them by name, and
`docs/audit/gates.yaml` asserts on them — so a key may be *added*, never renamed or
quietly dropped. `collect_free()` normalises every group against that declaration, which
means a group that fails to collect degrades to explicit `null` values (plus an `error`
string) rather than vanishing: "not measured" must never read as "fine".

Two clocks, both pinned so a re-run reproduces itself (Q0.0's "identical twice" rule):

  * `_GRID_WEEK_START` — a Monday. The grid walk covers a whole week from it, so format
    share and host load don't drift with the weekday you happen to audit on. The probe
    (Q0.1) pins its fixed slot list to the same date.
  * `reference_now` — noon on the day of the run (override with `--now`). The event
    window and the assembled-context sizes hang off it, so they follow the living world
    day to day while staying stable within one day's runs.

STRICTLY READ-ONLY: no writes, no generation, no dial mutation.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger
from ..world import clock, programming, store
from . import textstats
from .textstats import register_stats

log = get_logger(__name__)

# The Monday the grid walk starts from — pinned so the week (and therefore format share
# and host hours) is the same measurement every time. Also the probe's slot date (Q0.1).
_GRID_WEEK_START = datetime(2026, 7, 27)
_GRID_WEEK_SLOTS = 7 * 24 * 4  # a full week at 15-minute resolution

# THE METRIC CONTRACT. Q8 and gates.yaml read these by name; add, never rename.
GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "world": (
        "new_stories_per_tick_min",
        "new_stories_per_tick_max",
        "max_active_stories",
        # TWO different counts, and conflating them misreads the supply problem by ~2x
        # (seed README §4): `active_stories` is what the tick and the writers' room
        # actually SEE (it excludes arc_stage='past'); the raw row count is bigger.
        "active_stories",
        "stories_status_active_rows",
        "stories_total",
        "domains_covered",
        "events_in_window",
        "title_colon_schema_pct",
        "title_subtitle_article_pct",
        # Q1 — the supply fix. `items_per_night` is the Q1 gate metric: how many small
        # items the LATEST item tick wrote (not a rolling count, so a half-failed run
        # shows up). `items_in_window` is what the room actually sees right now;
        # `items_total` is the whole disposable table.
        "items_per_night",
        "items_in_window",
        "items_total",
    ),
    "quotes": (
        "count",
        "mean_words",
        "median_words",
        "pct_with_contraction",
        "hedges_per_1000w",
        "pct_under_12w",
    ),
    "grid": (
        "format_share",
        "programs",
        "registered_formats",
        "host_hours_per_day",
        "max_host_hours_per_day",
        "min_host_hours_per_day",
        "news_anchor_count",
        "news_words_low",
        "news_words_high",
        "news_words_distinct_per_program",
    ),
    "context": (
        "bible_chars",
        "cards_chars",
        "dynamic_chars",
        "events_rendered",
        "canon_rendered",
        "quotes_rendered",
        "topic_passed_on_live_path",
        "event_window_days",
        # Measured by the probe (Q0.1), so a free-only run reports them as null — which
        # a Q2 gate must read as FAIL, not as a pass. That is the point.
        "cached_tokens",
        "uncached_tokens",
        "seconds_per_call",
    ),
    "freshness": ("window_hours", "recent_limit", "mode", "enabled"),
    "models": ("haiku", "sonnet", "opus", "default_tier", "batch_enabled_paths"),
    "cost": ("usd_per_talk_segment", "talk_usd_window", "talk_calls_window", "days"),
}

# The §2b guards that are facts about the repo, not the world (src/audit/checks.py).
# Slow, so they are opt-in: a run without `--with-checks` reports them null, and a gate
# reads null as FAIL — a pack is not green on a run that never checked the tests.
CHECK_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "acceptance": (
        "properties_passed",
        "properties_total",
        "properties_failed",
        "window_hours",
    ),
    "tests": ("passed", "failed", "errors", "skipped", "exit_code"),
}

# The groups only the API probe can fill (Q0.1). Declared here beside the free ones so
# there is ONE place that says what an audit JSON contains.
PROBE_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    "topic": (
        "cross_run_beat_identity_pct",
        "top_entity",
        "top_entity_mentions",
        "top_entity_mentions_total",
        "top_entity_share",
        "distinct_entities_per_segment",
        "segments",
        "runs",
    ),
    "register": (
        "median_turn_words",
        "mean_turn_words",
        "pct_turns_over_40w",
        "pct_turns_under_4w",
        "contractions_per_100w",
        "hedges_per_1000w",
        "banned_abstractions_daytime",
        "banned_phrases_found",
        "segments",
        "turns",
    ),
    "continuity": (
        "max_verbatim_overlap_chars",
        "mean_verbatim_overlap_chars",
        "repeated_ngram_rate",
        "distinct_beats_in_run",
        "slots",
        "program",
    ),
}

# Every group an audit JSON may carry, free + checks + probe.
ALL_GROUP_KEYS: dict[str, tuple[str, ...]] = {
    **GROUP_KEYS,
    **CHECK_GROUP_KEYS,
    **PROBE_GROUP_KEYS,
}


# --- small shared maths -----------------------------------------------------


def _pct(n: int, d: int) -> float | None:
    """A percentage rounded to 0.1, or None when there is nothing to divide by."""
    return round(100 * n / d, 1) if d else None


# `register_stats` lives in textstats.py (the pure text maths the probe shares) and is
# re-exported here, because the `quotes.*` group is its caller.


# --- world: supply, titles ---------------------------------------------------


def world_metrics(now: datetime) -> dict:
    """Story supply, domain spread and the title schema (§1a, §1d)."""
    window = timedelta(days=settings.context_event_window_days)
    iw_now = clock.to_inworld(now)
    with store.connect() as conn:
        titles = [r[0] for r in conn.execute("SELECT title FROM stories").fetchall()]
        active = len(store.active_stories(conn))
        raw_active = conn.execute(
            "SELECT count(*) FROM stories WHERE status = 'active'"
        ).fetchone()[0]
        domains = conn.execute(
            "SELECT count(DISTINCT tags[1]) FROM stories"
        ).fetchone()[0]
        events = len(store.events_in_range(conn, iw_now - window, iw_now + window))
        items_total, items_per_night = _item_supply(conn)
        items_in_window = len(
            store.items_in_range(
                conn,
                iw_now - timedelta(hours=settings.item_window_hours),
                iw_now,
                limit=None,
            )
        )

    # Title schema uniformity: "The Noun Phrase: A Clause Explaining It" (92% at
    # baseline). The pair is deliberate — the colon share is the schema, the article
    # share is how mechanically the subtitle is built.
    colon = [t for t in titles if ":" in t]
    article = [
        t for t in colon if re.match(r"^(A|An|The)\b", t.split(":", 1)[1].strip())
    ]
    return {
        "new_stories_per_tick_min": settings.world_tick_new_stories_min,
        "new_stories_per_tick_max": settings.world_tick_new_stories_max,
        "max_active_stories": settings.world_tick_max_active_stories,
        "active_stories": active,
        "stories_status_active_rows": raw_active,
        "stories_total": len(titles),
        "domains_covered": domains,
        "events_in_window": events,
        "title_colon_schema_pct": _pct(len(colon), len(titles)),
        "title_subtitle_article_pct": _pct(len(article), len(colon)),
        "items_per_night": items_per_night,
        "items_in_window": items_in_window,
        "items_total": items_total,
    }


def _item_supply(conn) -> tuple[int, int]:
    """`(items in the table, items the LATEST item tick wrote)` — the Q1 gate metric.

    Per-night rather than rolling, because the gate asks whether the generator produced
    a night's worth: a run that half-failed reads as a small number here, where a
    rolling count would hide it behind the previous nights that are still in retention.
    `(0, 0)` before the first `make item-tick` — an honest zero, not a null.
    """
    total = conn.execute("SELECT count(*) FROM items").fetchone()[0]
    row = conn.execute(
        "SELECT count(*) FROM items WHERE created_tick = "
        "(SELECT max(created_tick) FROM items)"
    ).fetchone()
    return total, (row[0] if total else 0)


def world_vocabulary() -> tuple[list[str], list[str]]:
    """`(names the world knows, cast names to exclude)` — the entity list for §1a.

    The seed's probe scored proper nouns with a bare regex, which counted "That" and
    "Because" as names; its README asks Q0 to use a real entity list instead. Three
    sources, all free:

      * the gazetteer's `## ` headings — every named world and station, which is where
        "Cold Harbor" (23 mentions at baseline) comes from;
      * the `figures` table — the world's people, full name and surname, because a
        bulletin says "Sorn" after introducing "Aldric Sorn";
      * the story and event log — the names the tick has invented since.

    The cast is returned separately so `entity_counts` can drop it: two hosts using each
    other's name says nothing about what the segment is *about*.
    """
    names: set[str] = set(_gazetteer_places())
    cast: set[str] = set()
    try:
        with store.connect() as conn:
            for (figure,) in conn.execute("SELECT name FROM figures").fetchall():
                names.add(figure)
                names.update(part for part in figure.split() if len(part) > 2)
            texts = [
                r[0]
                for r in conn.execute(
                    "SELECT title FROM stories UNION ALL SELECT title FROM events"
                ).fetchall()
            ]
            for member in store.all_cast(conn):
                cast.update({member.id, member.name})
    except Exception as exc:  # noqa: BLE001 — the gazetteer alone still measures
        log.warning("audit_vocabulary_partial", error=str(exc))
        texts = []
    names |= textstats.vocabulary_from(texts)
    names -= cast
    return sorted(names), sorted(cast)


def _gazetteer_places() -> list[str]:
    """The named worlds and stations — the gazetteer cornerstone's `## ` headings."""
    path = settings.canon_dir / "06-gazetteer.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        log.warning("audit_gazetteer_missing", path=str(path))
        return []
    out: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            # One heading can name two places ("Far Reach and Breathe Easy").
            out += [part.strip() for part in line[3:].split(" and ") if part.strip()]
    return out


def quote_metrics() -> dict:
    """The register of the world's stored quotes (§1d) — every source is an aphorist."""
    with store.connect() as conn:
        texts = [r[0] for r in conn.execute("SELECT text FROM quotes").fetchall()]
    return register_stats(texts)


# --- grid: format mix, host load, news shape ---------------------------------


def grid_metrics(start: datetime | None = None) -> dict:
    """Format share, host hours and the news shape across a full week (§1b, §1c)."""
    start = start or _GRID_WEEK_START
    host_minutes: Counter = Counter()
    occupancy: Counter = Counter()
    progs: dict[str, programming.Program] = {}

    for i in range(_GRID_WEEK_SLOTS):
        at = start + timedelta(minutes=15 * i)
        prog = programming.program_for(at)
        progs[prog.id] = prog
        occupancy[prog.id] += 0.25  # hours
        # Lead + second host only: the pair actually in the room for the slot.
        for host in prog.hosts[:2]:
            host_minutes[host] += 15

    # Format share = each programme's clock composition, weighted by its hours on air.
    share: Counter = Counter()
    for pid, hours in occupancy.items():
        clock_steps = progs[pid].clock
        if not clock_steps:
            continue
        per = Counter(step.format for step in clock_steps)
        total_steps = sum(per.values())
        for fmt, count in per.items():
            share[fmt] += hours * count / total_steps
    total = sum(share.values()) or 1.0

    host_hours = {
        host: round(minutes / 60 / 7, 2)
        for host, minutes in sorted(
            host_minutes.items(), key=lambda kv: (-kv[1], kv[0])
        )
    }

    # Distinct bulletin budgets across the week's programmes. The word budget scales
    # from the length target (Q4.0 threads a per-programme `news_length_sec`), so
    # distinct lengths == distinct word budgets. 1 today = one budget for all bulletins.
    news_lengths = {
        getattr(p, "news_length_sec", None) or settings.format_news_length_target_sec
        for p in progs.values()
    }

    from ..formats import FORMATS  # local: the registry pulls in every builder

    return {
        "format_share": {
            fmt: round(100 * v / total, 1) for fmt, v in sorted(share.items())
        },
        "programs": len(progs),
        "registered_formats": len(FORMATS),
        "host_hours_per_day": host_hours,
        "max_host_hours_per_day": max(host_hours.values()) if host_hours else None,
        "min_host_hours_per_day": min(host_hours.values()) if host_hours else None,
        "news_anchor_count": len(settings.news_anchor_ids),
        "news_words_low": settings.format_news_words_low,
        "news_words_high": settings.format_news_words_high,
        "news_words_distinct_per_program": len(news_lengths),
    }


# --- context: what every prompt actually ships -------------------------------


def context_metrics(now: datetime) -> dict:
    """The cached/dynamic split and whether the RAG is reachable live (§1f)."""
    from ..world import context  # local: pulls in embeddings

    ctx = context.assemble(now, speakers=list(settings.convo_speaker_ids))
    return {
        "bible_chars": len(ctx.bible),
        "cards_chars": len(ctx.cards_text),
        "dynamic_chars": len(ctx.dynamic),
        "events_rendered": len(ctx.events),
        "canon_rendered": len(ctx.canon),
        "quotes_rendered": len(ctx.quotes),
        "topic_passed_on_live_path": topic_passed_on_live_path(),
        "event_window_days": settings.context_event_window_days,
    }


def topic_passed_on_live_path(source: Path | None = None) -> bool:
    """Does the scheduler pass a `topic` into `make_format_segment`? (§1f)

    It does not, at baseline — so `_select_canon` falls through to `all_canon` and D2's
    semantic recall never runs in production. Read off the code rather than a comment,
    because that is the thing Q2.1 has to change.
    """
    path = source or Path(__file__).resolve().parent.parent / "scheduler.py"
    try:
        src = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "topic=" in _call_args(src, "make_format_segment(")


def _call_args(src: str, call: str) -> str:
    """The argument text of the first `call` in `src`, paren-balanced ("" if absent)."""
    start = src.find(call)
    if start < 0:
        return ""
    i = start + len(call)
    depth = 1
    while i < len(src) and depth:
        depth += {"(": 1, ")": -1}.get(src[i], 0)
        i += 1
    return src[start + len(call) : i - 1]


# --- dials, models, cost -----------------------------------------------------


def freshness_metrics() -> dict:
    """The anti-repetition dials (§1g) — a 6h window lets a topic return forever."""
    return {
        "window_hours": settings.freshness_window_hours,
        "recent_limit": settings.freshness_recent_limit,
        "mode": settings.freshness_mode,
        "enabled": settings.freshness_enabled,
    }


def model_metrics() -> dict:
    """The routing table + which code paths actually claim the batch discount (§1h)."""
    return {
        "haiku": settings.model_haiku,
        "sonnet": settings.model_sonnet,
        "opus": settings.model_opus,
        "default_tier": settings.llm_default_tier,
        "batch_enabled_paths": batch_enabled_paths(),
    }


def batch_enabled_paths(root: Path | None = None) -> list[str]:
    """Modules that call `llm.generate_batch` — the tick only, at baseline (§1h).

    CLAUDE.md calls the 50% batch discount mandatory; measuring the call sites (rather
    than trusting `llm_batch_enabled`) is what makes Q7.2's claim checkable.
    """
    src_root = root or Path(__file__).resolve().parent.parent
    if not settings.llm_batch_enabled:
        return []
    # An actual call, not a docstring mention: the prose in world_tick/config writes
    # `llm.generate_batch` in backticks, which this deliberately does not match.
    call = re.compile(r"\bllm\.generate_batch\s*\(")
    found: set[str] = set()
    for path in sorted(src_root.rglob("*.py")):
        if path.parent.name == "audit":
            continue  # this measurement of the seam is not a use of it
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if call.search(text):
            found.add(str(path.relative_to(src_root.parent)))
    return sorted(found)


def cost_metrics(days: int | None = None) -> dict:
    """Measured $ per talk segment from the `usage` ledger (§1f)."""
    from .. import usage

    days = settings.audit_cost_window_days if days is None else days
    with store.connect() as conn:
        rollup = usage.load_rollup(conn)
    talk_usd = talk_calls = 0.0
    cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
    for day, categories in (rollup.get("days") or {}).items():
        if day < cutoff:
            continue
        bucket = categories.get("talk")
        if bucket:
            talk_usd += float(bucket.get("usd", 0.0))
            talk_calls += float(bucket.get("calls", 0.0))
    segments = talk_calls / settings.audit_llm_calls_per_talk_segment
    return {
        "usd_per_talk_segment": round(talk_usd / segments, 4) if segments else None,
        "talk_usd_window": round(talk_usd, 4),
        "talk_calls_window": talk_calls,
        "days": days,
    }


# --- the collector -----------------------------------------------------------


def reference_now(now: datetime | None = None) -> datetime:
    """The pinned clock the world/context reads hang off: noon on the day of the run.

    Pinned to noon (not `datetime.now()`) so two runs minutes apart return the same
    numbers, and to *today* (not a fixed date) so the audit keeps following the living
    world as the days pass. `--now` overrides it for an exact reproduction.
    """
    base = now or datetime.now()
    return base.replace(hour=12, minute=0, second=0, microsecond=0)


def collect_free(now: datetime | None = None) -> dict:
    """Every §1 metric that needs no API call. Pure reads; never raises.

    A group that cannot be collected (DB unreachable, grid unparseable) degrades to its
    declared keys set to `null`, plus an `error` string — the shape stays whole, so a
    gate sees an explicit "not measured" instead of a silent pass.
    """
    at = reference_now(now)
    log.info("audit_collect_free_start", reference_now=at.isoformat())
    out: dict = {
        "collected_at": datetime.now().isoformat(),
        "reference_now": at.isoformat(),
        "grid_week_start": _GRID_WEEK_START.isoformat(),
    }
    collectors = (
        ("world", lambda: world_metrics(at)),
        ("quotes", quote_metrics),
        ("grid", grid_metrics),
        ("context", lambda: context_metrics(at)),
        ("freshness", freshness_metrics),
        ("models", model_metrics),
        ("cost", cost_metrics),
    )
    for name, fn in collectors:
        try:
            out[name] = _normalise(name, fn())
        except Exception as exc:  # noqa: BLE001 — degrade explicitly, never crash
            log.warning("audit_group_failed", group=name, error=str(exc))
            out[name] = _normalise(name, {}, error=f"{type(exc).__name__}: {exc}")
    log.info("audit_collect_free_done", groups=sorted(GROUP_KEYS))
    return out


def normalise_group(group: str, values: dict, *, error: str | None = None) -> dict:
    """Fill the group out to its declared keys — missing ones become explicit `null`."""
    out: dict = {key: values.get(key) for key in ALL_GROUP_KEYS[group]}
    for key, value in values.items():  # keep extras, but never drop a declared key
        if key not in out:
            out[key] = value
    if error:
        out["error"] = error
    return out


_normalise = normalise_group  # the in-module short name


def merge_checks(free: dict, checks: dict) -> dict:
    """Fold the slow local checks (acceptance, tests) into a run."""
    out = dict(free)
    for group, values in checks.items():
        out[group] = normalise_group(group, values, error=values.get("error"))
    return out


def merge_probe(free: dict, probe: dict) -> dict:
    """Fold a probe result into a free run — one audit JSON with every group in it.

    The probe's `context.*` keys (cached/uncached tokens, seconds per call) land inside
    the free `context` group rather than beside it, because §1f treats them as one
    story: what every prompt ships and what it costs to ship it.
    """
    out = dict(free)
    for group, values in probe.items():
        if group == "context":
            merged = {**(out.get("context") or {}), **values}
            out["context"] = normalise_group("context", merged)
        elif group in ALL_GROUP_KEYS:
            out[group] = normalise_group(group, values)
        else:
            out[group] = values  # probe metadata (the plan, the spend)
    return out


# --- rendering ---------------------------------------------------------------


def render_table(data: dict) -> str:
    """The audit as a readable table — the thing `make audit` prints."""
    lines = [
        "===== SETTLEMENT RADIO — AUDIT (docs/PHASE_Q_TASKS.md §1) =====",
        f"  collected {data.get('collected_at', '—')}"
        f"  ·  reference now {data.get('reference_now', '—')}"
        f"  ·  grid week from {(data.get('grid_week_start') or '—')[:10]}",
    ]
    for group in ALL_GROUP_KEYS:
        if group not in GROUP_KEYS and group not in data:
            continue  # a free-only run: don't print empty probe/check groups
        body = data.get(group) or {}
        lines += ["", f"── {group.upper()} ──"]
        if body.get("error"):
            lines.append(f"  (unavailable: {body['error']})")
        for key, value in body.items():
            if key == "error":
                continue
            lines.append(f"  {key:<34s} {_fmt(value)}")
    lines += ["", "=" * 56]
    return "\n".join(lines)


def _fmt(value: object) -> str:
    """One metric value on one line — dicts collapse into `k=v` pairs."""
    if value is None:
        return "—  (not measured)"
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items()) or "—  (empty)"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) or "—  (none)"
    return str(value)


__all__ = [
    "ALL_GROUP_KEYS",
    "CHECK_GROUP_KEYS",
    "GROUP_KEYS",
    "PROBE_GROUP_KEYS",
    "batch_enabled_paths",
    "collect_free",
    "context_metrics",
    "cost_metrics",
    "freshness_metrics",
    "grid_metrics",
    "merge_checks",
    "merge_probe",
    "model_metrics",
    "normalise_group",
    "quote_metrics",
    "reference_now",
    "register_stats",
    "render_table",
    "topic_passed_on_live_path",
    "world_metrics",
    "world_vocabulary",
]

"""Audit seed — the FREE metrics (no API calls, no writes).

Reference implementation of every §1 number in `docs/PHASE_Q_TASKS.md` that can be
read from the DB, the grid, or the code. This is the ad-hoc script the 2026-07-26
audit actually ran, tidied into one file — Q0.0 turns it into `src/audit/metrics.py`
with the documented key names.

    .venv/bin/python scripts/audit_seed/free_metrics.py          # table
    .venv/bin/python scripts/audit_seed/free_metrics.py --json   # machine-readable

Pure reads. Safe to run against the live world at any time.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, "/Users/pavel/station")

from src.config import settings  # noqa: E402
from src.world import programming, store  # noqa: E402

_CONTR = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.I)
_HEDGE = re.compile(
    r"\b(um|uh|sort of|kind of|you know|I mean|I guess|maybe|probably|"
    r"honestly|look,|well,|I think|we'll see)\b",
    re.I,
)


# --- world: stories, titles, quotes ----------------------------------------
def world_metrics() -> dict:
    """Story supply + the title/quote register (§1a, §1d)."""
    out: dict = {}
    with store.connect() as conn:
        titles = [r[0] for r in conn.execute("select title from stories").fetchall()]
        quotes = [r[0] for r in conn.execute("select text from quotes").fetchall()]
        # TWO different counts — keep both, they get confused otherwise.
        # `active_stories` is what the tick and the writers' room actually SEE
        # (store.active_stories excludes arc_stage='past'); the raw row count is
        # bigger and is not the supply number.
        out["active_stories"] = len(store.active_stories(conn))
        out["stories_status_active_rows"] = conn.execute(
            "select count(*) from stories where status='active'"
        ).fetchone()[0]
        out["stories_total"] = len(titles)
        out["domains_covered"] = conn.execute(
            "select count(distinct tags[1]) from stories"
        ).fetchone()[0]

    out["new_stories_per_tick_min"] = settings.world_tick_new_stories_min
    out["new_stories_per_tick_max"] = settings.world_tick_new_stories_max
    out["max_active_stories"] = settings.world_tick_max_active_stories

    # Title schema uniformity: "The Noun Phrase: A Clause Explaining It"
    colon = [t for t in titles if ":" in t]
    art = [t for t in colon if re.match(r"^(A|An|The)\b", t.split(":", 1)[1].strip())]
    out["title_colon_schema_pct"] = _pct(len(colon), len(titles))
    out["title_subtitle_article_pct"] = _pct(len(art), len(colon))

    out["quotes"] = _register_stats(quotes, label="quotes")
    return out


def _register_stats(texts: list[str], *, label: str) -> dict:
    """Shared register maths for stored quotes and for generated scripts."""
    if not texts:
        return {"count": 0}
    words = [len(t.split()) for t in texts]
    joined = " ".join(texts)
    n_words = max(1, len(joined.split()))
    return {
        "count": len(texts),
        "mean_words": round(statistics.mean(words), 1),
        "median_words": statistics.median(words),
        "pct_with_contraction": _pct(
            sum(1 for t in texts if _CONTR.search(t)), len(texts)
        ),
        "hedges_per_1000w": round(1000 * len(_HEDGE.findall(joined)) / n_words, 1),
        "pct_under_12w": _pct(sum(1 for w in words if w <= 12), len(texts)),
    }


# --- grid: format mix, host load, news shape -------------------------------
def grid_metrics(start: datetime | None = None) -> dict:
    """Format share, host hours and the news shape across a full week (§1b, §1c)."""
    start = start or datetime(2026, 7, 27, 0, 0)  # a Monday
    slots = 7 * 24 * 4  # 15-minute resolution
    host_min: Counter = Counter()
    occupancy: Counter = Counter()
    progs: dict = {}

    for i in range(slots):
        now = start + timedelta(minutes=15 * i)
        p = programming.program_for(now)
        progs[p.id] = p
        occupancy[p.id] += 0.25  # hours
        for h in p.hosts[:2]:
            host_min[h] += 15

    # Format share = each programme's clock composition, weighted by hours on air.
    share: Counter = Counter()
    for pid, hours in occupancy.items():
        clock = progs[pid].clock
        if not clock:
            continue
        per = Counter(s.format for s in clock)
        n = sum(per.values())
        for fmt, c in per.items():
            share[fmt] += hours * c / n
    total = sum(share.values()) or 1

    host_hours = {h: round(m / 60 / 7, 2) for h, m in host_min.most_common()}

    news_lengths = {
        getattr(p, "news_length_sec", None) or settings.format_news_length_target_sec
        for p in progs.values()
    }

    from src.formats import (
        FORMATS,  # local import: avoids a heavy import at module load
    )

    return {
        "format_share": {f: round(100 * v / total, 1) for f, v in share.most_common()},
        "programs": len(progs),
        "registered_formats": len(FORMATS),
        "host_hours_per_day": host_hours,
        "max_host_hours_per_day": max(host_hours.values()) if host_hours else 0.0,
        "news_anchor_count": len(settings.news_anchor_ids),
        "news_words_low": settings.format_news_words_low,
        "news_words_high": settings.format_news_words_high,
        "news_words_distinct_per_program": len(news_lengths),
    }


# --- context: what every prompt actually ships -----------------------------
def context_metrics() -> dict:
    """The cached/dynamic split and whether the RAG is reachable (§1f)."""
    from src.world import context  # local: pulls in embeddings

    ctx = context.assemble(datetime.now(), speakers=list(settings.convo_speaker_ids))
    marker = "World facts you simply know:"
    idx = ctx.dynamic.find(marker)
    return {
        "bible_chars": len(ctx.bible),
        "cards_chars": len(ctx.cards_block),
        "dynamic_chars": len(ctx.dynamic),
        "dynamic_events_chars": idx if idx > 0 else None,
        "events_rendered": len(ctx.events),
        "canon_rendered": len(ctx.canon),
        "quotes_rendered": len(ctx.quotes),
        # The live scheduler path never passes a `topic`, so `_select_canon` falls
        # through to `all_canon` and D2's semantic recall never runs in production.
        "topic_passed_on_live_path": "topic=" in _scheduler_call_site(),
        "context_event_window_days": settings.context_event_window_days,
    }


def _scheduler_call_site() -> str:
    from pathlib import Path

    src = Path("src/scheduler.py").read_text(encoding="utf-8")
    i = src.find("make_format_segment(")
    return src[i : i + 200] if i >= 0 else ""


# --- freshness, models, cost ------------------------------------------------
def freshness_metrics() -> dict:
    return {
        "window_hours": settings.freshness_window_hours,
        "recent_limit": settings.freshness_recent_limit,
        "mode": settings.freshness_mode,
        "enabled": settings.freshness_enabled,
    }


def model_metrics() -> dict:
    return {
        "haiku": settings.model_haiku,
        "sonnet": settings.model_sonnet,
        "opus": settings.model_opus,
        "default_tier": settings.llm_default_tier,
        "batch_enabled": settings.llm_batch_enabled,
    }


def cost_metrics(days: int = 7) -> dict:
    """Measured $ per talk segment from the usage ledger (§1f)."""
    from src import usage

    with store.connect() as conn:
        rollup = usage.load_rollup(conn)
    talk_usd = talk_calls = 0.0
    cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
    for day, cats in (rollup.get("days") or {}).items():
        if day < cutoff:
            continue
        bucket = cats.get("talk")
        if bucket:
            talk_usd += bucket.get("usd", 0.0)
            talk_calls += bucket.get("calls", 0.0)
    # ~4 LLM calls per talk segment (showrunner + orchestrate + continuity + journal)
    segments = talk_calls / 4 if talk_calls else 0
    return {
        "talk_usd_window": round(talk_usd, 4),
        "talk_calls_window": talk_calls,
        "usd_per_talk_segment": round(talk_usd / segments, 4) if segments else None,
    }


def _pct(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def collect_free() -> dict:
    out = {"collected_at": datetime.now().isoformat()}
    for name, fn in (
        ("world", world_metrics),
        ("grid", grid_metrics),
        ("context", context_metrics),
        ("freshness", freshness_metrics),
        ("models", model_metrics),
        ("cost", cost_metrics),
    ):
        try:
            out[name] = fn()
        except Exception as exc:  # degrade explicitly, never crash the audit
            out[name] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


if __name__ == "__main__":
    data = collect_free()
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(json.dumps(data, indent=2, default=str))

"""The nightly small-items tick (PHASE_Q_TASKS.md Q1.1) — the world's second class.

The measured problem (§1a): the station consumes ~150 content slots a day and the
story tick produces 2-4 stories a night, so every show reaches for the same beat and
"Cold Harbor" gets named 23 times across four unrelated programmes. The missing thing
is not a better beat-picker — it is the second class of happening a real newsroom runs
on: **dozens of small items that get thirty seconds each**. A price. A delay. A
result. A fine. A queue. A birth. Something that broke again.

This module makes them. `run_item_tick()` is the sibling of `world_tick.run_tick()`,
and it is deliberately the cheap one:

* **haiku through the Batch API** — CLAUDE.md routes high-volume/low-stakes work to
  haiku, and the nightly batch is where the other 50% lives. A whole night's items
  costs pennies (the Q1.1 gate: under $0.15).
* **the shared bible cache block** (`bible=…`), so each request pays full price only
  for its small variable part.
* **one sentence each, no arc, no figures, no quotes** — an item that needs any of
  those is a story, and the story tick already makes those.
* **safety-gated per item, but never regenerated** — a flagged item is dropped. They
  are disposable and there are dozens; the C0 discipline here is "never write it",
  not "get this one right".

THE REGISTER IS LOAD-BEARING (Q1.1, and it matches Q5.0's fix to the story prompt):
items are ordinary, often boring, sometimes petty. A good night's batch contains
things nobody would write a story about. The prompt bans the epigram outright — the
world already speaks in aphorisms (§1d: 1 hedge in 120 stored quotes) and this is
where the ordinary gets a vocabulary.

Writes go through `world/store` (Q1.0's `items` table) in one transaction, with the
expiry sweep on the tail. It never touches the schedule, the segments, or stories.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm
from ..safety import safety_check
from . import canon_source, clock, store
from .world_tick import DOMAINS, _extract_json_array, _jaccard_dup

log = get_logger(__name__)

# The everyday CATEGORIES the world has no vocabulary for (Q1.1). Distinct from
# `DOMAINS` (which is *what field* a happening belongs to, and is what a programme's
# domain filter matches): a category is *what kind of small thing* it is. An item
# carries both — the domain in its own column, the category as a tag — so The Ward can
# ask for health items and still get a queue, a price and a rota among them.
# Intrinsic domain data, not config (the config.py rule), and the list is the spread
# one night is generated across: `_request_groups` slices it across the batch.
CATEGORIES: tuple[str, ...] = (
    "prices",
    "delays",
    "results",
    "weather",
    "rosters",
    "repairs",
    "fines",
    "queues",
    "births and deaths",
    "arrivals",
    "complaints",
    "small crime",
    "lost property",
    "what is cheap this week",
    "what broke again",
)

# State keys the item tick owns (the `state` kv table; survive a canon refresh). Its
# OWN counter, separate from the nightly story tick's and the micro-tick's, so item ids
# stay unique and neither counter pollutes the other's pacing maths.
_ITEM_COUNT_KEY = "world_item_tick_count"
_ITEM_LAST_AT_KEY = "world_item_tick_last_at"


# --- Shapes -----------------------------------------------------------------


@dataclass(frozen=True)
class ProposedItem:
    """One small thing the tick proposes, before the gate and the store (Q1.1).

    `text` is ONE sentence. `domain` is one of `DOMAINS` (validated — an item with an
    unknown domain is dropped rather than mislabelled, because the domain is what the
    programme filter reads). `category` is one of `CATEGORIES`, kept as a tag.
    `hour` is the in-world hour (0-23) it happened at; `_materialise` resolves that to
    a datetime in the last 24 in-world hours, so an item is always already true.
    """

    text: str
    domain: str
    category: str
    hour: int


@dataclass
class ItemTickResult:
    """What one `run_item_tick()` did — printed by the CLI and logged as telemetry."""

    tick: int
    requested: int = 0  # items asked for across the batch
    proposed: int = 0  # items the model returned and we could parse
    accepted: int = 0  # items written
    dropped: int = 0  # malformed / unknown-domain / safety-flagged
    duplicates: int = 0  # near-duplicates of a recent item
    pruned: int = 0  # expired items swept on the tail
    item_ids: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


# --- The tick ---------------------------------------------------------------


def run_item_tick(now: datetime | None = None) -> ItemTickResult:
    """Generate one night's small items: propose in batch, gate, de-dup, write, sweep.

    Returns an `ItemTickResult` summary. Transactional like the story tick — every
    write happens in one `store.connect` block after all network I/O, so a failure
    rolls back cleanly and leaves last night's items untouched. A disabled tick
    (`item_tick_enabled=False`) is a valid no-op run, not an error.
    """
    now = now or datetime.now()
    iw_now = clock.to_inworld(now)
    log.info("item_tick_start", now=now.isoformat(), inworld=iw_now.isoformat())

    with store.connect() as conn:
        tick_no = (int(store.get_state(conn, _ITEM_COUNT_KEY) or 0)) + 1
        recent = store.items_in_range(
            conn,
            iw_now - timedelta(days=settings.item_tick_dedup_window_days),
            iw_now,
        )
    result = ItemTickResult(tick=tick_no)

    if not settings.item_tick_enabled:
        log.info("item_tick_disabled", tick=tick_no)
        return result

    bible = canon_source.load_bible(settings.canon_dir, settings.canon_path)
    proposals = _propose(bible, iw_now, result)
    accepted = _gate(proposals, result)
    accepted = _dedup(accepted, [i.text for i in recent], result)

    with store.connect() as conn:
        items = [
            _materialise(p, tick_no, iw_now, i) for i, p in enumerate(accepted, start=1)
        ]
        store.insert_items(conn, items)
        result.accepted = len(items)
        result.item_ids = [i.id for i in items]
        result.pruned = store.prune_items(
            conn, iw_now, keep=timedelta(days=settings.item_retention_days)
        )
        store.set_state(conn, _ITEM_COUNT_KEY, str(tick_no))
        store.set_state(conn, _ITEM_LAST_AT_KEY, now.isoformat())

    log.info(
        "item_tick_done",
        tick=tick_no,
        requested=result.requested,
        proposed=result.proposed,
        accepted=result.accepted,
        dropped=result.dropped,
        duplicates=result.duplicates,
        pruned=result.pruned,
        **{f"usage_{k}": v for k, v in result.usage.items()},
    )
    return result


# --- Step 1: propose (haiku, batch, shared bible cache) ---------------------


def _propose(
    bible: str, iw_now: datetime, result: ItemTickResult
) -> list[ProposedItem]:
    """Ask for the night's items as several independent batch requests.

    Split rather than one giant list for three reasons: each request's output stays
    inside `item_tick_max_tokens`; independent samples repeat each other far less than
    one long list does; and a request that fails costs a slice of the night, not the
    night. All of them share the cached bible block, so the marginal cost of the split
    is the small per-call variable part only.
    """
    groups = _request_groups()
    per = math.ceil(settings.item_tick_max / max(1, len(groups)))
    result.requested = per * len(groups)

    reqs = [
        llm.BatchRequest(
            custom_id=str(n),
            prompt=f"Generate {per} small items as a JSON array.",
            system=_system(iw_now, group, per),
            bible=bible,  # CO2: the shared bible cache block (the cost lever)
            model=settings.item_tick_tier,
            max_tokens=settings.item_tick_max_tokens,
        )
        for n, group in enumerate(groups)
    ]
    result.usage["item_calls"] = len(reqs)

    out: list[ProposedItem] = []
    for r in llm.generate_batch(reqs):
        for k, v in r.usage.items():
            result.usage[k] = result.usage.get(k, 0) + v
        if not r.ok:
            log.warning(
                "item_tick_request_failed", custom_id=r.custom_id, error=r.error
            )
            continue
        out += _parse_items(r.text or "", result)
    result.proposed = len(out)
    log.info("item_tick_proposed", count=len(out), requests=len(reqs))
    return out


def _request_groups() -> list[tuple[str, ...]]:
    """Slice `CATEGORIES` across `item_tick_requests` batch requests, in order.

    Each request gets its own few kinds of small thing (and the full domain list), so
    one night covers the whole everyday spread instead of whatever three categories the
    model happens to favour.
    """
    n = max(1, settings.item_tick_requests)
    size = math.ceil(len(CATEGORIES) / n)
    return [CATEGORIES[i : i + size] for i in range(0, len(CATEGORIES), size)]


def _system(iw_now: datetime, categories: tuple[str, ...], per: int) -> str:
    """The item-writer's instructions — the REGISTER half is load-bearing (Q1.1)."""
    return (
        "You are the world-simulation engine for Settlement Radio, a tribute "
        f"science-fiction radio station broadcasting from the year {iw_now.year} "
        "(600 years ahead of the present). You are writing the SMALL ITEMS half of "
        "tonight's world: the dozens of little things that happened today across the "
        "settlements, the ones a bulletin gives ten seconds to and then moves on "
        "from. Not stories. Not arcs. Not turning points.\n\n"
        f"In-world now: {iw_now:%A, %-d %B %Y, %H:%M}.\n\n"
        f"Generate exactly {per} items, each ONE plain sentence. Spread them across "
        f"these KINDS of small thing: {', '.join(categories)}. Give each one a "
        f"`domain` from this list: {', '.join(DOMAINS)}.\n\n"
        "WHAT THESE ARE. Ordinary. Often boring. Sometimes petty. A price moved. A "
        "ferry is late again. A team lost. A pipe failed in the same corridor as last "
        "month. Someone was fined for something small. A queue. A birth. A rota "
        "change nobody likes. A thing that is cheap this week. A complaint about a "
        "smell. A good night's batch INCLUDES things nobody would ever write a story "
        "about — if every line sounds important, you have done it wrong.\n\n"
        "HOW TO WRITE THEM — this matters more than the content:\n"
        "- Flat and factual. State what happened. A number, a place, a name is worth "
        "more than an adjective.\n"
        "- NO epigrams. Never the shape 'X is one thing. Y is another.' Never a "
        "second sentence that lands a moral, a lesson, or a resonance. No 'which is "
        "to say', no 'as ever', no 'the way things go'.\n"
        "- No poetry, no melancholy, no wistfulness, no meaning. These are not "
        "observations about the human condition. They are the grain price.\n"
        "- Plain words. Contractions where a person would use one.\n"
        "- Vary the shape: some are five words, some are twenty-five. Some name "
        "someone, most don't.\n\n"
        "Stay strictly consistent with the world bible in the cached context above — "
        "real places, plausible detail, the right technology level. Stay entirely "
        "inside the fiction: original world only, never real franchises, real people, "
        "or trademarks.\n\n"
        "Return ONLY a JSON array (no prose, no code fence). Each element:\n"
        '{"text": str, "domain": str, "category": str, "hour": int}\n'
        "`hour` is the in-world hour of day it happened, 0-23. `category` is which of "
        "the kinds above it is."
    )


def _parse_items(raw: str, result: ItemTickResult) -> list[ProposedItem]:
    """Parse one request's JSON array into items, dropping the malformed."""
    data = _extract_json_array(raw)
    if data is None:
        log.warning("item_tick_parse_failed", sample=raw[:200])
        return []
    out: list[ProposedItem] = []
    for entry in data:
        item = _coerce_item(entry)
        if item is None:
            result.dropped += 1
            continue
        out.append(item)
    return out


def _coerce_item(entry: object) -> ProposedItem | None:
    """Validate/normalise one parsed object into a `ProposedItem`, or None if junk.

    Strict about `domain` on purpose: it is the column the programme filter reads, so a
    mislabelled item would surface on the wrong show. An unknown domain drops the item
    rather than guessing — there are dozens more where it came from.
    """
    if not isinstance(entry, dict):
        return None
    text = " ".join(str(entry.get("text", "")).split())
    if not text:
        return None
    domain = str(entry.get("domain", "")).strip().lower()
    if domain not in DOMAINS:
        log.debug("item_tick_unknown_domain", domain=domain, text=text[:80])
        return None
    category = str(entry.get("category", "")).strip().lower()
    hour = entry.get("hour")
    hour = int(hour) if isinstance(hour, int | float | str) and _is_int(hour) else 0
    return ProposedItem(
        text=text, domain=domain, category=category, hour=max(0, min(23, hour))
    )


def _is_int(value: object) -> bool:
    """True when `value` parses as a whole number (the model sometimes sends "7")."""
    return bool(re.fullmatch(r"-?\d+", str(value).strip()))


# --- Step 2: gate + de-dup ---------------------------------------------------


def _gate(proposals: list[ProposedItem], result: ItemTickResult) -> list[ProposedItem]:
    """Safety-gate each item; a flagged item is DROPPED, never regenerated (Q1.1).

    Deliberately NOT the story tick's full escalation (safety → continuity → regenerate
    once → drop): an item is one disposable sentence, and the continuity risk of "the
    ferry was late" is nil. Cheap per item, and the drop is the whole policy.
    """
    kept: list[ProposedItem] = []
    for p in proposals:
        verdict = safety_check(p.text)
        if not verdict.ok:
            result.dropped += 1
            log.warning(
                "item_tick_item_flagged", text=p.text[:120], reason=verdict.reason[:200]
            )
            continue
        kept.append(p)
    return kept


def _dedup(
    proposals: list[ProposedItem], recent: list[str], result: ItemTickResult
) -> list[ProposedItem]:
    """Drop items too close to a recent one, or to an earlier sibling in this batch.

    Structural (Jaccard) only — the same helper the story tick uses. No semantic pass:
    items are not embedded (they expire in days, and 60 vectors a night for that is
    waste), and one flat sentence is exactly what token overlap is good at.
    """
    kept: list[ProposedItem] = []
    seen = list(recent)
    for p in proposals:
        if _jaccard_dup(p.text, seen):
            result.duplicates += 1
            log.debug("item_tick_dedup_rejected", text=p.text[:80])
            continue
        kept.append(p)
        seen.append(p.text)
    return kept


# --- Step 3: materialise -----------------------------------------------------


def _materialise(p: ProposedItem, tick_no: int, iw_now: datetime, n: int) -> store.Item:
    """Turn a gated proposal into an `items` row, dated in the last 24 in-world hours.

    An item is always ALREADY TRUE — there is no planned/upcoming item (that is a
    story's job), so an hour later than the in-world clock resolves to yesterday. The
    minute is spread deterministically off the index so a night's items don't all land
    on the hour.
    """
    day = (
        iw_now.date() if p.hour <= iw_now.hour else (iw_now - timedelta(days=1)).date()
    )
    when = datetime.combine(day, datetime.min.time()).replace(
        hour=p.hour, minute=(n * 13) % 60
    )
    tags = [p.domain] + ([p.category] if p.category else [])
    return store.Item(
        id=f"i{tick_no}-{n}",
        text=p.text,
        domain=p.domain,
        in_world_datetime=when,
        tags=tags,
        source=store.ITEM_SOURCE_TICK,
        created_tick=tick_no,
    )


# --- CLI ---------------------------------------------------------------------


def main() -> int:
    """Run one item tick from the CLI; print a summary; return a process exit code.

    `python -m src.world.items` / `make item-tick`. One-shot by design: this is a
    nightly WORLD-STATE job for the C5 cron, run BEFORE the story tick so the story
    tick's context already carries the day's texture. A failure is logged loudly and
    returns non-zero for the timer, but never corrupts the store (all writes are in one
    rolled-back-on-error transaction).
    """
    from .. import usage

    try:
        with usage.job("item-tick"):
            r = run_item_tick()
    except Exception as exc:  # noqa: BLE001 — fail loud for the timer; store rolled back
        log.error("item_tick_failed", error=str(exc))
        usage.flush()
        print(f"Item tick FAILED (store unchanged): {exc}")
        return 1
    usage.flush()  # R5.1 — persist the run's LLM spend to the usage rollup

    print(
        f"\nItem tick #{r.tick}: asked {r.requested}, parsed {r.proposed}, "
        f"wrote {r.accepted} (dropped {r.dropped}, duplicates {r.duplicates}); "
        f"swept {r.pruned} expired."
    )
    if r.accepted < settings.item_tick_min:
        print(
            f"  ! below the Q1 target of {settings.item_tick_min} items — "
            "check the logs for parse/safety drops."
        )
    return 0


if __name__ == "__main__":
    # .venv/bin/python -m src.world.items   (or: make item-tick)
    # Needs `make seed-canon` + a populated .env. LLM_BATCH_ENABLED=false for a quick
    # synchronous local run (no async batch wait); default True takes the 50% discount.
    raise SystemExit(main())

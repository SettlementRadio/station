"""DJ memory (D9.4) — a host remembers what the world (and they) lived through.

Assembles a small "what the hosts remember" block from the D3 story log: recent
past/resolved happenings a DJ can reference on air as LIVED history ("that dust
season last month…"), in character. Per-host and persona-weighted — a story
whose tags overlap a host's card tags ranks higher for that host — so different
DJs remember different things about the same world.

Placement is deliberate (the prompt-cache lever, OVERVIEW §2): the block is
small and VARIABLE, so it rides the per-call dynamic part of the orchestrator
prompt, never the cached bible. It is bounded by two dials —
`convo_memory_window_days` (how far back "lived history" reaches on the
in-world timeline) and `convo_memory_per_host` (how many stories each host
recalls) — so it can't bloat the prompt or drown freshness.

Distinct from its neighbours (they must not merge): D4's coverage memory drives
the NEWS DESK's intended story recurrence; D5's airplay memory is OUTPUT
anti-repetition (don't re-pick/re-phrase); D9.4 is a DJ *remembering on
purpose*, as a person. Consistency is enforced downstream: the same block is
shown to the continuity editor, so a host misremembering a resolved story flags
like any continuity error.

Degrades cleanly: disabled, an empty log, or a DB failure all yield "" — the
room writes exactly as it did before D9.4.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..world import clock, events, store
from ..world.store import ARC_PAST, CastMember, Story

log = get_logger(__name__)


def _rank_for(
    card: CastMember, candidates: list[tuple[Story, datetime]], per_host: int
) -> list[tuple[Story, datetime]]:
    """The stories THIS host remembers: persona-weighted, bounded, stable.

    Tag overlap with the host's card ranks first (a sports story sticks with the
    sports host); ties keep the store order (resolved first, then most recent).
    """
    tags = set(card.tags)
    ranked = sorted(
        enumerate(candidates),
        key=lambda pair: (-len(set(pair[1][0].tags) & tags), pair[0]),
    )
    return [item for _i, item in ranked[:per_host]]


# A memory is a HANDLE, not a re-report: tick summaries run a paragraph, so a
# remembered story is clipped to its first sentence (bounded by this cap) — it
# keeps the prompt small (the pack's bound) and reads more like recall anyway.
_SUMMARY_MAX_CHARS = 240


def _clip(summary: str) -> str:
    """The summary's first sentence, hard-capped at `_SUMMARY_MAX_CHARS`."""
    first = summary.split(". ")[0].strip().rstrip(".") + "."
    if len(first) <= _SUMMARY_MAX_CHARS:
        return first
    return first[: _SUMMARY_MAX_CHARS - 1].rstrip() + "…"


def _line(story: Story, last_beat: datetime, now: datetime) -> str:
    """One remembered story as a prompt bullet, clock-framed for `now`."""
    phrase = events.phrase_for_datetime(last_beat, now)
    state = "resolved" if story.arc_stage == ARC_PAST else "still unfolding"
    return f"- {story.title} ({phrase}; {state}): {_clip(story.summary)}"


def memory_section(speakers: list[CastMember], now: datetime) -> str:
    """The per-host "what {DJ} remembers" block for the orchestrator ('' if none).

    Reads the story log once (bounded by the window/per-host dials), ranks per
    host, and renders a section for the per-call system prompt. Any failure
    (no DB, empty log) degrades to "" — memory is texture, never load-bearing.
    """
    if not settings.convo_memory_enabled or not speakers:
        return ""
    per_host = settings.convo_memory_per_host
    if per_host <= 0:
        return ""
    try:
        with store.connect() as conn:
            candidates = store.remembered_stories(
                conn,
                iw_now=clock.to_inworld(now),
                window_days=settings.convo_memory_window_days,
                # Enough headroom that persona-weighting has real choices beyond
                # the per-host cut (a small window makes every host converge on
                # the same newest stories), without reading an unbounded log.
                limit=per_host * max(4, 2 * len(speakers)),
            )
    except Exception as exc:  # noqa: BLE001 — memory must never kill a slot
        log.warning("memory_read_failed", error=str(exc))
        return ""
    if not candidates:
        return ""

    blocks: list[str] = []
    for card in speakers:
        picked = _rank_for(card, candidates, per_host)
        if not picked:
            continue
        lines = "\n".join(_line(story, beat, now) for story, beat in picked)
        blocks.append(f"What {card.name} remembers:\n{lines}")
    if not blocks:
        return ""

    body = "\n\n".join(blocks)
    log.info("memory_assembled", hosts=len(blocks), stories=len(candidates))
    return (
        "The hosts' lived history — what they remember from the station log "
        "(reference naturally and sparingly, as people who were on air when it "
        "happened; past tense for what's resolved — never re-announce it as "
        f"news):\n{body}\n\n"
    )

"""Context assembly for the writers' room (PHASE_B_TASKS.md B3).

The job: hand the writer the *right slice* of the world for `now`, cheaply and
fast — without standing up vector search before it earns its keep. Retrieval here
is structured (date / status / tag queries over the DB), which is the correct tool
while the canon is small and date/tag recall is enough. The semantic seam lives in
`providers/embeddings.py`, documented and unused (see its TRIGGER note).

`assemble(now, *, topic, speaker)` splits the world into two parts, matching the
two seams in CLAUDE.md:

* the **stable core** — the series bible (standing prose from CANON.md) plus the
  speaking DJ's character card. This is slow-changing and identical across calls,
  so it goes out as `cached_context` (the prompt-cache cost lever): repeat runs
  pay ~0.1x on it.
* the **dynamic bits** — what is true *right now*: events near `now` (with live
  status and a natural relative phrase from `events.py`) and the topic-relevant
  canon. Small and per-call, so it rides in the variable part of the prompt.

The split is deliberate: the cached core barely changes, while the dynamic part is
what makes the segment feel time-aware. As the world grows, only the dynamic query
widens (and eventually gains the embeddings seam) — the cached core stays cached.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import settings
from ..logging_setup import get_logger
from . import canon_source, clock, store
from . import events as events_mod
from .store import CanonFact, CastMember, Event

log = get_logger(__name__)


@dataclass(frozen=True)
class AssembledContext:
    """The world slice for one generation: a cached core + the dynamic now.

    `cached_context` is for `llm.generate(..., cached_context=...)`; `dynamic` is
    woven into the per-call system prompt. The structured fields (`speakers`,
    `events`, `canon`) are exposed too, so later callers (the B4 conversation
    orchestrator, B5 formats) can reuse the same query without re-fetching.

    `speakers` holds one card for the single-DJ writer (B3) or both for a two-DJ
    conversation (B4); `speaker` is a convenience for the single-DJ case.
    """

    cached_context: str
    dynamic: str
    speakers: list[CastMember] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    canon: list[CanonFact] = field(default_factory=list)

    @property
    def speaker(self) -> CastMember | None:
        """The first (or only) speaking DJ — for single-DJ callers like B3."""
        return self.speakers[0] if self.speakers else None


def assemble(
    now: datetime,
    *,
    topic: str | None = None,
    speakers: str | Sequence[str] | None = None,
) -> AssembledContext:
    """Assemble the world context for `now`.

    Args:
        now: the current real time. The in-world face (`now + 600y`) drives the
            event window and the relative phrasing.
        topic: optional subject; when given, canon is filtered to tag-matched
            facts (falling back to all facts when nothing matches — see below).
        speakers: one cast id (e.g. "vell") or several (e.g. ["vell", "wren"]);
            each one's card joins the cached stable core, so the writer — single
            DJ (B3) or a two-DJ conversation (B4) — speaks in character. An unknown
            id raises rather than silently dropping a persona.

    Returns:
        An `AssembledContext` — cached stable core + dynamic now + the rows used.
    """
    ids = [speakers] if isinstance(speakers, str) else list(speakers or [])
    log.info("context_assemble_start", now=now.isoformat(), topic=topic, speakers=ids)

    bible = canon_source.load_series_bible(settings.canon_path)
    iw_now = clock.to_inworld(now)
    window = timedelta(days=settings.context_event_window_days)

    # All SQL stays behind the store seam; this block is the only DB work.
    with store.connect() as conn:
        cards: list[CastMember] = []
        for sid in ids:
            card = store.get_cast_member(conn, sid)
            if card is None:
                # Fail loud rather than silently dropping the DJ's persona.
                raise ValueError(f"unknown speaker cast id {sid!r} (run `make seed`?)")
            cards.append(card)
        raw_events = store.events_in_range(conn, iw_now - window, iw_now + window)
        canon = _select_canon(conn, topic)

    # Recompute each event's status live so the writer never sees a stale snapshot.
    near_events = [events_mod.progressed(e, now) for e in raw_events]

    cached_context = _render_core(bible, cards)
    dynamic = _render_dynamic(near_events, canon, now)

    log.info(
        "context_assemble_done",
        speakers=[c.id for c in cards],
        events=len(near_events),
        canon=len(canon),
        cached_chars=len(cached_context),
        dynamic_chars=len(dynamic),
    )
    return AssembledContext(
        cached_context=cached_context,
        dynamic=dynamic,
        speakers=cards,
        events=near_events,
        canon=canon,
    )


# --- Structured retrieval ---------------------------------------------------
# The event window query lives inline in `assemble` (the only DB block); only the
# topic→canon selection is factored out, since it branches. Both keep SQL behind
# the store seam — this module never touches psycopg.


def _select_canon(conn, topic: str | None) -> list[CanonFact]:
    """Canon facts for the prompt: tag-matched to `topic`, else all of them.

    With no topic we include the whole (small) canon. With a topic we try a
    tag-match and fall back to the full set when nothing matches — which is the
    case today, since seeded facts carry no tags yet (the seam is ready for when
    they do; see `store.canon_by_tags`). The writer thus never loses the core
    facts, while the retrieval narrows automatically once canon is tagged.
    """
    if topic:
        hits = store.canon_by_tags(conn, _topic_tags(topic))
        if hits:
            return hits
        log.debug("context_canon_topic_fallback", topic=topic)
    return store.all_canon(conn)


def _topic_tags(topic: str) -> list[str]:
    """Lowercase word tokens from a free-text topic, to match against canon tags."""
    return [t for t in re.split(r"[^a-z0-9]+", topic.lower()) if t]


# --- Rendering --------------------------------------------------------------


def _render_core(bible: str, cards: list[CastMember]) -> str:
    """The cached stable core: series bible + each speaking DJ's character card."""
    parts = [bible]
    parts += [f"## Character — {c.name}\n\n{c.card_text}" for c in cards]
    return "\n\n".join(p for p in parts if p).strip()


def _render_dynamic(events: list[Event], canon: list[CanonFact], now: datetime) -> str:
    """The per-call dynamic block: what is true right now, for the system prompt."""
    sections: list[str] = []

    if events:
        lines = [
            f"- {e.title} — {events_mod.relative_phrase(e, now)} ({e.status}): {e.body}"
            for e in events
        ]
        header = "Current events (reference naturally, don't recite):\n"
        sections.append(header + "\n".join(lines))

    if canon:
        lines = [f"- {f.text}" for f in canon]
        sections.append("World facts you simply know:\n" + "\n".join(lines))

    return "\n\n".join(sections).strip()


if __name__ == "__main__":
    # Runnable check: print the assembled context for Vell, now.
    #   .venv/bin/python -m src.world.context      (or: make context)
    ctx = assemble(datetime.now(), speakers=settings.writer_speaker_id)
    print("===== CACHED CORE (stable) =====\n")
    print(ctx.cached_context)
    print("\n===== DYNAMIC (this call) =====\n")
    print(ctx.dynamic)

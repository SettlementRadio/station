"""Context assembly for the writers' room (PHASE_B_TASKS.md B3).

The job: hand the writer the *right slice* of the world for `now`, cheaply and
fast. Event/status retrieval is structured (date / status queries over the DB); for
a topic, canon is selected by a hybrid of **semantic** recall (`embeddings.retrieve`,
top-k by meaning — live since D2.4) and the **structured** tag-match, falling back to
the whole canon when neither hits or vectors are unavailable. All embedding work
stays behind `providers/embeddings.py`; all SQL behind the store seam.

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
from ..providers import embeddings
from . import canon_source, clock, store
from . import events as events_mod
from .store import CanonFact, CastMember, Event, Figure, Quote

log = get_logger(__name__)


# The separator between the bible and each character card in the stable core.
# It is the ONE place the core's byte layout is defined, so the two cache blocks
# (CO2) and the back-compat `cached_context` join stay in lockstep. See below.
_CORE_SEP = "\n\n"


@dataclass(frozen=True)
class AssembledContext:
    """The world slice for one generation: a cached core + the dynamic now.

    The stable core is exposed in TWO parts so the prompt cache can share it (CO2,
    docs/CACHE_OPTIMIZATION_TASKS.md):

    * `bible` — the series bible, byte-identical across every speaker set and the
      world tick, so it caches ONCE as a shared block.
    * `cards_text` — the speaking DJs' character cards (joined, no leading
      separator), which vary per speaker set and cache as a second block.

    `cached_context` (property) rejoins them into the pre-split single string, so
    callers not yet migrated to the two-block seam keep working unchanged; it is
    for `llm.generate(..., cached_context=...)`. `cards_block` (property) is the
    cards region as it sits AFTER the bible block — the separator plus the cards —
    so `bible + cards_block` reproduces `cached_context` byte-for-byte when passed
    as two cache blocks (the CO1 equivalence invariant). `dynamic` is woven into
    the per-call system prompt.

    The structured fields (`speakers`, `events`, `canon`) are exposed too, so
    later callers (the B4 conversation orchestrator, B5 formats) can reuse the same
    query without re-fetching. `speakers` holds one card for the single-DJ writer
    (B3) or both for a two-DJ conversation (B4); `speaker` is a convenience for the
    single-DJ case.
    """

    dynamic: str
    bible: str = ""
    cards_text: str = ""
    speakers: list[CastMember] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    canon: list[CanonFact] = field(default_factory=list)
    # D10.2 — recent/relevant attributable quotes (paired with their figure), so the DJs
    # can reference what someone in the world said. Empty when there are no figures yet.
    quotes: list[tuple[Quote, Figure]] = field(default_factory=list)

    @property
    def speaker(self) -> CastMember | None:
        """The first (or only) speaking DJ — for single-DJ callers like B3."""
        return self.speakers[0] if self.speakers else None

    @property
    def cached_context(self) -> str:
        """The stable core as ONE string (pre-CO2 shape): bible + cards joined.

        A back-compat join so the single-`cached_context` seam path keeps working
        while call sites migrate to the two-block `bible` + `cards_block` shape.
        Byte-identical to the pre-split `_render_core` output.
        """
        return _join_core(self.bible, self.cards_text)

    @property
    def cards_block(self) -> str:
        """The cards region as it follows the shared bible block: separator + cards.

        Empty when there are no cards. For a non-empty `bible` (always, in
        production), `bible + cards_block == cached_context` byte-for-byte, so
        emitting the two as separate cache blocks is transparent to the model
        (CO1). Pass this as `llm.generate(..., cards=ctx.cards_block)`.
        """
        return f"{_CORE_SEP}{self.cards_text}" if self.cards_text else ""


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

    bible = canon_source.load_bible(settings.canon_dir, settings.canon_path)
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
        quotes = _select_quotes(conn, topic, iw_now, window)

    # Recompute each event's status live so the writer never sees a stale snapshot.
    near_events = [events_mod.progressed(e, now) for e in raw_events]

    cards_text = _render_cards(cards)
    dynamic = _render_dynamic(near_events, canon, quotes, now)

    log.info(
        "context_assemble_done",
        speakers=[c.id for c in cards],
        events=len(near_events),
        canon=len(canon),
        quotes=len(quotes),
        # CO2 — the stable core is now two cache blocks; log both spans so a silent
        # size regression in either is visible.
        bible_chars=len(bible),
        cards_chars=len(cards_text),
        dynamic_chars=len(dynamic),
    )
    return AssembledContext(
        dynamic=dynamic,
        bible=bible,
        cards_text=cards_text,
        speakers=cards,
        events=near_events,
        canon=canon,
        quotes=quotes,
    )


# --- Structured retrieval ---------------------------------------------------
# The event window query lives inline in `assemble` (the only DB block); only the
# topic→canon selection is factored out, since it branches. Both keep SQL behind
# the store seam — this module never touches psycopg.


def _select_canon(conn, topic: str | None) -> list[CanonFact]:
    """Canon facts for the prompt: hybrid semantic + tag recall for a `topic`, else all.

    With no topic we include the whole (still small) canon. With a topic we combine
    two retrievals (D2.4):

    * **semantic** — `embeddings.retrieve` returns the top-k canon by MEANING (so a
      topic like "loneliness" finds the right facts even when nothing is tagged that
      word), ranked by similarity;
    * **structured** — `store.canon_by_tags` adds any tag-matched facts the vectors
      missed (the complement; it earns its keep once facts are tagged in D2.5).

    The union is semantic-first (preserving meaning-rank), then any tag-only extras.
    If BOTH come back empty — no vector hit AND no tag match, or vectors unavailable
    (pgvector off / embeddings backend down, where `retrieve` returns `[]`) — we fall
    back to the whole canon, so the writer never loses the core facts.
    """
    if not topic:
        return store.all_canon(conn)

    k = settings.context_canon_top_k
    semantic = embeddings.retrieve(topic, k=k, corpus="canon")
    sem_ids = [r.id for r in semantic]
    tag_ids = [f.id for f in store.canon_by_tags(conn, _topic_tags(topic))]

    seen = set(sem_ids)
    union_ids = sem_ids + [i for i in tag_ids if not (i in seen or seen.add(i))]
    if union_ids:
        log.debug(
            "context_canon_hybrid",
            topic=topic,
            semantic=len(sem_ids),
            tag_only=len(union_ids) - len(sem_ids),
        )
        return store.canon_by_ids(conn, union_ids)

    log.debug("context_canon_topic_fallback", topic=topic)
    return store.all_canon(conn)


def _topic_tags(topic: str) -> list[str]:
    """Lowercase word tokens from a free-text topic, to match against canon tags."""
    return [t for t in re.split(r"[^a-z0-9]+", topic.lower()) if t]


def _select_quotes(
    conn, topic: str | None, iw_now: datetime, window: timedelta
) -> list[tuple[Quote, Figure]]:
    """Attributable quotes for the writers' room (D10.2): semantic on topic else recent.

    With a `topic`, recall the most relevant quotes by MEANING (`embeddings.retrieve`
    over the `quote` corpus, D2) and resolve them to rows with their speaker — so a DJ
    can react to an on-topic opinion. With no topic (or when recall returns nothing /
    vectors are unavailable), fall back to the newest quotes in the same event window —
    the structured, story-linked read that always works. Bounded by
    `settings.context_quotes_limit`; the section is off when that is 0.
    """
    limit = settings.context_quotes_limit
    if limit <= 0:
        return []
    if topic:
        hits = embeddings.retrieve(
            topic, k=settings.context_quotes_top_k, corpus="quote"
        )
        attributed = store.attributed_quotes_by_ids(conn, [h.id for h in hits])
        if attributed:
            return attributed[:limit]
    return store.attributed_quotes_near(
        conn, iw_now - window, iw_now + window, limit=limit
    )


# --- Rendering --------------------------------------------------------------


def _render_cards(cards: list[CastMember]) -> str:
    """The speaking DJs' character cards, joined (no leading separator).

    The per-speaker-set half of the stable core (CO2). Empty when there are no
    cards. `_join_core` re-attaches it to the bible for the back-compat single
    string; the two-block seam path pairs it with the bible as a second cache
    block via `AssembledContext.cards_block`.
    """
    return _CORE_SEP.join(f"## Character — {c.name}\n\n{c.card_text}" for c in cards)


def _join_core(bible: str, cards_text: str) -> str:
    """Rejoin the two stable-core parts into the pre-split single string.

    Byte-identical to the pre-CO2 `_render_core`: bible then cards, `_CORE_SEP`
    between non-empty parts, outer `strip()`. Both parts arrive already stripped
    (the bible from `canon_source.load_bible`, each card from its parser), so the
    outer strip is a no-op in practice — kept for exact equivalence.
    """
    return _CORE_SEP.join(p for p in (bible, cards_text) if p).strip()


def _render_dynamic(
    events: list[Event],
    canon: list[CanonFact],
    quotes: list[tuple[Quote, Figure]],
    now: datetime,
) -> str:
    """The per-call dynamic block: what is true right now, for the system prompt."""
    sections: list[str] = []

    if events:
        lines = [
            f"- {e.title} — {events_mod.relative_phrase(e, now)} ({e.status}): {e.body}"
            for e in events
        ]
        header = "Current events (reference naturally, don't recite):\n"
        sections.append(header + "\n".join(lines))

    if quotes:
        lines = [
            f"- {fig.name} ({fig.role}) said "
            f"{events_mod.phrase_for_datetime(q.in_world_datetime, now)}: "
            f'"{q.text}"'
            for q, fig in quotes
        ]
        header = (
            "What people are saying (you may reference or react to an opinion in "
            "character — don't recite it):\n"
        )
        sections.append(header + "\n".join(lines))

    if canon:
        lines = [f"- {f.text}" for f in canon]
        sections.append("World facts you simply know:\n" + "\n".join(lines))

    return "\n\n".join(sections).strip()


if __name__ == "__main__":
    # Runnable check: print the assembled context for Vell, now.
    #   .venv/bin/python -m src.world.context      (or: make context)
    ctx = assemble(datetime.now(), speakers=settings.writer_speaker_id)
    print("===== BIBLE (shared cache block) =====\n")
    print(ctx.bible)
    print("\n===== CARDS (per-speaker-set cache block) =====\n")
    print(ctx.cards_text)
    print("\n===== DYNAMIC (this call) =====\n")
    print(ctx.dynamic)

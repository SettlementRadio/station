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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import settings
from ..logging_setup import get_logger
from ..providers import embeddings
from . import canon_source, clock, store
from . import events as events_mod
from .store import CanonFact, CastMember, Event, Figure, Item, Quote

log = get_logger(__name__)


# The separator between the bible and each character card in the stable core.
# It is the ONE place the core's byte layout is defined, so the two cache blocks
# (CO2) and the back-compat `cached_context` join stay in lockstep. See below.
_CORE_SEP = "\n\n"


# --- Q2.0: the event ranking weights ----------------------------------------
# Intrinsic to the ranking algorithm, so they are named module constants here rather
# than settings (the config-vs-constant rule in config.py); the operator's dials are
# the three counts — `context_events_max` / `_domain_min` / `_tail`.

# Recency: a half-life in in-world hours. At 36h an event scores half of one happening
# right now, at 72h a quarter — so a fortnight-old beat is ~0.1% and effectively only
# reachable via the title tail. The window itself stays ±14 days; this is what stops
# that width from costing anything.
_RECENCY_HALFLIFE_HOURS = 36.0
# The future is worth slightly less than the past at equal distance: a thing that
# happened is reportable, a thing that will happen is only trailable.
_FUTURE_DISCOUNT = 0.8

# Arc stage of the beat's PARENT STORY (store.ARC_STAGES). A live arc outranks a
# resolved one at the same age; `_ARC_DEFAULT` covers a standalone bible event with no
# story, which sits mid-table (it is world texture, neither breaking nor spent).
_ARC_WEIGHT: dict[str, float] = {
    store.ARC_HAPPENING: 1.0,
    store.ARC_DEVELOPING: 0.9,
    store.ARC_UPCOMING: 0.7,
    store.ARC_RUMOURED: 0.6,
    store.ARC_PAST: 0.45,
}
_ARC_DEFAULT = 0.55

# Breaking-ness: the beat's own kind (`events.beat_kind`, free-form as authored by the
# tick — anything unlisted is neutral), times a bump for a beat dated TODAY in-world.
_BEAT_WEIGHT: dict[str, float] = {
    "announcement": 1.15,
    "development": 1.1,
    "consequence": 1.0,
    "resolution": 1.0,
    "rumour": 0.9,
}
_BEAT_DEFAULT = 1.0
_TODAY_BOOST = 1.25

# Domain match: a beat whose story is in the on-air programme's field. Big enough to
# lift a quiet in-field beat over a loud out-of-field one, and backed by the reserved
# sub-quota (`context_events_domain_min`) for when even that isn't enough.
_DOMAIN_BOOST = 2.0


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
    # Q1.2 — the night's SMALL ITEMS inside the read window: the ordinary things (a
    # price, a delay, a queue) the room can use in passing or build a short slot around.
    # Empty before the first `make item-tick`, which is exactly the pre-Q1 behaviour.
    items: list[Item] = field(default_factory=list)
    # Q2.0 — the events ranked JUST below the bodied `events`: rendered as title-only
    # one-liners, so the room knows they exist (continuity) without paying for a
    # paragraph each. Empty when the window holds nothing beyond the bodied set.
    tail_events: list[Event] = field(default_factory=list)

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
    domains: Sequence[str] | None = None,
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
        domains: the on-air program's world-domains (R4.3). When set, the near-events
            whose STORY is in one of these domains are surfaced as this show's own
            beats (preferred), the rest as background — so a vertical (The Exchange,
            The Ward) talks THIS week's story in its field, not the topic in the
            abstract. None / empty keeps the full undifferentiated mix (a general show).

    Returns:
        An `AssembledContext` — cached stable core + dynamic now + the rows used.
    """
    ids = [speakers] if isinstance(speakers, str) else list(speakers or [])
    log.info(
        "context_assemble_start",
        now=now.isoformat(),
        topic=topic,
        speakers=ids,
        domains=list(domains or []),
    )

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
        items = _select_items(conn, iw_now, domains)
        # R4.3 — the domain of each near-event lives on its parent story's tags.
        # Q2.0 — and its arc stage on the same row; both feed `rank_events`, so unlike
        # R4.3's read these are fetched whether or not the programme sets a domain.
        story_ids = [e.story_id for e in raw_events if e.story_id]
        story_tags = store.story_tags_for(conn, story_ids)
        story_arcs = store.story_arcs_for(conn, story_ids)

    # Recompute each event's status live so the writer never sees a stale snapshot.
    # R4.0: `airable` first — the window reaches forward, so it would otherwise pick up
    # a same-day arc's PLANNED beats and hand the DJs something that hasn't happened
    # yet. An ordinary future event stays (trailing what's coming is the point).
    near_events = [
        events_mod.progressed(e, now) for e in events_mod.airable(raw_events, now)
    ]

    # Q2.0 — rank the whole window, then take a BOUNDED slice: the top
    # `context_events_max` get bodies, the next `context_events_tail` get titles. The
    # window may hold 80 beats; the room reads the 15 that matter plus 10 it should
    # know exist.
    ranked = rank_events(
        near_events, now, domains, story_tags=story_tags, story_arcs=story_arcs
    )
    bodied = ranked[: settings.context_events_max]
    tail_events = ranked[
        settings.context_events_max : settings.context_events_max
        + max(settings.context_events_tail, 0)
    ]

    # R4.3 — split into THIS show's own beats (its domain) and the background mix. Only
    # when both a program domain is set AND at least one near-event is in it; otherwise
    # the show keeps the full mix (a general show, or a vertical with no story yet).
    # Applied to the BODIED slice: ranking already guaranteed the domain's sub-quota is
    # in there, this decides how those beats are PRESENTED.
    preferred_events, near_events = _split_by_domain(bodied, domains, story_tags)

    cards_text = _render_cards(cards)
    dynamic = _render_dynamic(
        near_events,
        canon,
        quotes,
        now,
        preferred_events=preferred_events,
        items=items,
        tail_events=tail_events,
    )

    log.info(
        "context_assemble_done",
        speakers=[c.id for c in cards],
        events=len(near_events),
        preferred=len(preferred_events),
        tail=len(tail_events),
        in_window=len(ranked),
        canon=len(canon),
        quotes=len(quotes),
        items=len(items),
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
        events=preferred_events + near_events,
        canon=canon,
        quotes=quotes,
        items=items,
        tail_events=tail_events,
    )


def topic_for(program: object | None) -> str | None:
    """The canon-retrieval topic for the programme on air (Q2.1) — brief, else tagline.

    The §1f finding was that the live path never passed a `topic`, so `_select_canon`
    fell through to `all_canon` and D2's semantic RAG never ran in production — 267
    facts, uncached, on every call. The programme's editorial **brief** is the right
    key: it is the only sentence-level statement of what THIS show is about, and it is
    already authored per programme in the grid. Its public one-liner (`tagline`) is the
    fallback for a programme that has no brief; `None` for one with neither, which keeps
    the whole-canon behaviour exactly as it was for those shows.

    Lives here, and is used by the scheduler, the audit probe AND the free metrics, so
    what the audit measures cannot drift from what production ships.
    """
    if program is None:
        return None
    return getattr(program, "brief", "") or getattr(program, "tagline", "") or None


def rank_events(
    events: Sequence[Event],
    now: datetime,
    domains: Sequence[str] | None = None,
    *,
    story_tags: Mapping[str, Sequence[str]] | None = None,
    story_arcs: Mapping[str, str] | None = None,
) -> list[Event]:
    """Order near-events by how much this show, right now, needs to read them (Q2.0).

    The baseline audit's §1f finding: `events_in_range` has no cap and no ranking, so
    every call shipped 74–82 full event bodies — ~81k characters of flat, equally
    weighted paragraphs. That is most of the uncached half of the prompt, most of the
    25s latency, and the reason the beat-picker had no signal about what matters.

    Score is a product of four independent factors, each a pure function of the row:

    * **recency** — exponential decay on the in-world hours between the beat and `now`
      (`_RECENCY_HALFLIFE_HOURS`), with the future discounted slightly against the past;
    * **arc stage** — the parent story's stage (`_ARC_WEIGHT`): a `happening` arc
      outranks one that resolved, at equal age;
    * **domain match** — `_DOMAIN_BOOST` when the story's tags meet the programme's
      `domains`;
    * **breaking-ness** — the beat's own `beat_kind` (`_BEAT_WEIGHT`), bumped when the
      beat is dated TODAY in-world.

    Returns **every** event, highest first — truncation is the caller's, because the
    caller needs both slices: the bodied head AND the title-only tail just behind it.
    `context_events_domain_min` is honoured here rather than by the caller, as a
    reserved sub-quota inside the first `context_events_max`: if the programme's own
    field would otherwise be crowded out by a louder story elsewhere, its top-ranked
    beats are promoted into the head. Order *within* the head stays by score.

    Pure: no DB, no clock read beyond `now` (`clock.to_inworld` is a fixed offset), and
    ties break on the id, so the same world at the same instant always ranks the same.
    `story_tags` / `story_arcs` are the two `store` lookups the caller already does;
    absent, the corresponding factor is simply neutral.
    """
    iw_now = clock.to_inworld(now)
    tags = story_tags or {}
    arcs = story_arcs or {}
    domset = {d.lower() for d in (domains or [])}

    def in_domain(e: Event) -> bool:
        return bool(e.story_id) and bool(
            domset.intersection(t.lower() for t in tags.get(e.story_id, []))
        )

    def key(e: Event) -> tuple[float, float, str]:
        hours = (e.in_world_datetime - iw_now).total_seconds() / 3600.0
        score = 0.5 ** (abs(hours) / _RECENCY_HALFLIFE_HOURS)
        if hours > 0:
            score *= _FUTURE_DISCOUNT
        score *= _ARC_WEIGHT.get(arcs.get(e.story_id or "", ""), _ARC_DEFAULT)
        score *= _BEAT_WEIGHT.get(e.beat_kind or "", _BEAT_DEFAULT)
        if e.in_world_datetime.date() == iw_now.date():
            score *= _TODAY_BOOST
        if in_domain(e):
            score *= _DOMAIN_BOOST
        return (-score, abs(hours), e.id)

    ranked = sorted(events, key=key)
    return _promote_domain_quota(ranked, in_domain)


def _promote_domain_quota(
    ranked: list[Event], in_domain: Callable[[Event], bool]
) -> list[Event]:
    """Guarantee the programme's own field a floor inside the bodied head (Q2.0).

    `ranked` is already in score order. If fewer than `context_events_domain_min` of
    the first `context_events_max` are in-domain, promote the next-best in-domain beats
    into that head — displacing the weakest out-of-domain ones, which drop to just
    behind it (they become the title tail, not nothing). Order within each region stays
    by score, so the promotion is the only thing that reorders anything.
    """
    head_n = settings.context_events_max
    floor = min(settings.context_events_domain_min, head_n)
    if head_n <= 0 or floor <= 0 or len(ranked) <= head_n:
        return ranked
    dom = [e for e in ranked if in_domain(e)]
    if sum(1 for e in ranked[:head_n] if in_domain(e)) >= min(floor, len(dom)):
        return ranked
    keep = {e.id for e in dom[:floor]}
    for e in ranked:
        if len(keep) >= head_n:
            break
        keep.add(e.id)
    log.debug("context_events_domain_promoted", head=head_n, floor=floor, dom=len(dom))
    return [e for e in ranked if e.id in keep] + [e for e in ranked if e.id not in keep]


def _split_by_domain(
    events: list[Event],
    domains: Sequence[str] | None,
    story_tags: dict[str, list[str]],
) -> tuple[list[Event], list[Event]]:
    """Partition near-events into (this-show's-domain, the rest) — R4.3.

    An event is in-domain when its parent story's tags intersect the program's
    `domains`. Returns `([], events)` unchanged when no domain is set or nothing
    matches (a general show, or a vertical whose story hasn't happened yet — it keeps
    the full mix rather than going silent). Order within each group is preserved.
    """
    if not domains:
        return [], events
    domset = {d.lower() for d in domains}

    def in_domain(e: Event) -> bool:
        return bool(e.story_id) and bool(
            domset.intersection(story_tags.get(e.story_id, []))
        )

    preferred = [e for e in events if in_domain(e)]
    if not preferred:
        return [], events
    rest = [e for e in events if not in_domain(e)]
    return preferred, rest


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

    The union is semantic-first (preserving meaning-rank), then any tag-only extras,
    **bounded to `context_canon_top_k`** (Q2.1). That bound is new and load-bearing: the
    live path now passes a programme BRIEF as the topic, and a brief is three sentences,
    so `_topic_tags` tokenises it into dozens of ordinary words that tag-match most of
    the canon — 80 facts, uncached, every call. Semantic rank decides who makes the cut;
    the tag complement fills whatever is left below k (which is what it was always for —
    covering the facts the vectors missed, not doubling the block).

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
    union_ids = (sem_ids + [i for i in tag_ids if not (i in seen or seen.add(i))])[:k]
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


def _select_items(conn, iw_now: datetime, domains: Sequence[str] | None) -> list[Item]:
    """The small items this show can use (Q1.2) — its own field first, then the rest.

    The same shape R4.3 gives events, applied to a much cheaper row: a vertical sees
    ITS field's items at the top of the block, and the general mix fills the remainder
    so a quiet domain never leaves the section empty. Bounded by
    `settings.context_items_limit` (the section is off at 0) and by
    `settings.item_window_hours` — an item older than the window is not "right now".
    """
    limit = settings.context_items_limit
    if limit <= 0:
        return []
    start = iw_now - timedelta(hours=settings.item_window_hours)
    picked = (
        store.items_in_range(conn, start, iw_now, domains=domains, limit=limit)
        if domains
        else []
    )
    if len(picked) < limit:
        seen = {i.id for i in picked}
        rest = store.items_in_range(conn, start, iw_now, limit=limit)
        picked += [i for i in rest if i.id not in seen][: limit - len(picked)]
    return picked


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


def _event_line(e: Event, now: datetime) -> str:
    """One event rendered for the dynamic block: title, relative time, status, body."""
    return f"- {e.title} — {events_mod.relative_phrase(e, now)} ({e.status}): {e.body}"


def _render_dynamic(
    events: list[Event],
    canon: list[CanonFact],
    quotes: list[tuple[Quote, Figure]],
    now: datetime,
    *,
    preferred_events: list[Event] | None = None,
    items: list[Item] | None = None,
    tail_events: list[Event] | None = None,
) -> str:
    """The per-call dynamic block: what is true right now, for the system prompt.

    `preferred_events` (R4.3) are this show's own-domain beats. When present they lead
    as a "this show's beat — prefer these" section, and `events` (the rest) follow as
    background — so a vertical picks from its field first. When None/empty the events
    render as one undifferentiated "Current events" list (a general show, as before).

    `items` (Q1.2) are the night's small things, rendered as their own compact section:
    ONE LINE EACH, never a paragraph. That density is the point — the room should be
    able to glance down a list of twelve ordinary happenings and pick one, which is what
    a world of 23 stories could never offer it.

    `tail_events` (Q2.0) are the beats ranked just below the bodied set: TITLE ONLY, so
    the room knows a running story exists — and can pick it up next time it leads —
    without paying a paragraph for each. They render last of the event material,
    deliberately quiet.
    """
    sections: list[str] = []

    if preferred_events:
        lines = [_event_line(e, now) for e in preferred_events]
        sections.append(
            "On THIS show's subject — prefer these, they're what the show covers:\n"
            + "\n".join(lines)
        )
        if events:
            other = [_event_line(e, now) for e in events]
            sections.append(
                "Also happening elsewhere (only if it genuinely fits the show):\n"
                + "\n".join(other)
            )
    elif events:
        lines = [_event_line(e, now) for e in events]
        header = "Current events (reference naturally, don't recite):\n"
        sections.append(header + "\n".join(lines))

    if tail_events:
        lines = [
            f"- {e.title} ({events_mod.relative_phrase(e, now)})" for e in tail_events
        ]
        sections.append(
            "Also running, headlines only — you know these are out there, but you "
            "don't have the detail, so don't invent it:\n" + "\n".join(lines)
        )

    if items:
        lines = [
            f"- {events_mod.phrase_for_datetime(i.in_world_datetime, now)}: {i.text}"
            for i in items
        ]
        sections.append(
            "Small things happening right now (a line each — use one in passing, or "
            "build a short item around it):\n" + "\n".join(lines)
        )

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

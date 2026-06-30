"""News-desk story selection (PHASE_D_NEWS_DESK_TASKS.md D4.1).

Picks which of the living world's running stories (the D3 log) THIS HOUR's bulletin
reports, and tags each one so the D4.2 producer can frame it. The replacement for the
old `news.py` flat `_headlines_block` — calendar-only, memoryless — with a selection
that balances three things:

* **now-relevance** — the temporal kind of each story relative to the in-world clock:
  ``breaking`` (a beat at/near now), ``trailed`` (a notable upcoming beat to preview),
  or ``ongoing`` (a story whose movement is behind us but still developing). Derived
  from each beat's `in_world_datetime` via the same B2 clock/`events` machinery.
* **coverage recurrence** — from the D4.0 coverage memory, each story is tagged
  ``new`` (never aired), ``repeat`` (aired before, no new beat since), or ``evolve``
  (aired before AND a newer beat / stage exists → an UPDATE, not a re-read). A cold
  ``repeat`` (older than `news_repeat_max_stale_hours`) is dropped so the desk doesn't
  loop a stale item.
* **canon-relevance** — each candidate is grounded against the bible by semantic
  recall (`embeddings.retrieve` over the canon corpus, D2), so the bulletin connects
  to the world's standing facts, not just the calendar. This DEGRADES gracefully: if
  embeddings/pgvector are unavailable `retrieve` returns ``[]`` and selection falls
  back to pure temporal/structured ranking (the D4.1 capability-fallback rule).

The result is a ranked, tagged `SelectedStory` list, bounded by `news_story_count`,
mixing the three kinds via soft per-kind quotas. It carries everything D4.2 needs to
write the brief (the lead beat for its relative phrase, the arc stage, the delta beat
for an `evolve` update, and the prior coverage for consistent naming — D4.3).

This module reads the log and the coverage memory; it writes NOTHING (the producer
records coverage after a successful render, D4.2). All SQL stays behind `world.store`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ..config import settings
from ..logging_setup import get_logger
from ..providers import embeddings
from ..world import clock, store
from ..world.store import Event, Figure, NewsCoverage, Quote, Story

if TYPE_CHECKING:  # type-only: psycopg stays behind the world.store seam at runtime
    from psycopg import Connection

log = get_logger(__name__)


# --- Tags (the vocabulary D4.2 frames against) ------------------------------
# Coverage tags: how this story relates to what the desk has already aired (D4.0).
COVERAGE_NEW = "new"  # never covered before
COVERAGE_REPEAT = "repeat"  # covered before, no new beat/stage since → re-air as-is
COVERAGE_EVOLVE = "evolve"  # covered before AND a newer beat/stage → air as an update

# Temporal kinds: where the story sits relative to in-world now (drives the mix).
KIND_BREAKING = "breaking"  # a beat at/near now
KIND_TRAILED = "trailed"  # a notable upcoming beat worth previewing
KIND_ONGOING = "ongoing"  # movement behind us but the story is still developing

# Air/quota order: a bulletin leads with breaking, then trails what's coming, then
# revisits the ongoing thread. The per-kind quota dials are read in this order.
_KIND_ORDER = (KIND_BREAKING, KIND_TRAILED, KIND_ONGOING)


@dataclass(frozen=True)
class SelectedStory:
    """One story chosen for the hour's bulletin, with everything D4.2 needs to frame it.

    `coverage_tag` ∈ {new, repeat, evolve}; `temporal_kind` ∈ {breaking, trailed,
    ongoing}. `lead_beat` is the beat the anchor frames the item around (its
    `events.relative_phrase` gives "tonight"/"tomorrow"/"yesterday"); it is None only
    for a beatless story. `new_beat` is the development since the last coverage (set
    for `evolve` when a concrete newer beat exists) — the delta the anchor reports as
    "an update on …". `latest_beat` is the story's newest beat overall (what the
    producer records as the coverage's `last_beat_id`, so the NEXT bulletin's evolve
    check fires only on a genuinely newer beat — D4.2). `prior_coverage` is the last
    D4.0 record (the angle/stage/beat the desk last used) so naming stays consistent
    (D4.3). `canon_score` is the best bible-recall similarity (0.0 when recall is
    unavailable); `score` is the final rank.
    """

    story: Story
    coverage_tag: str
    temporal_kind: str
    lead_beat: Event | None
    new_beat: Event | None
    latest_beat: Event | None
    prior_coverage: NewsCoverage | None
    canon_score: float
    score: float
    # D10.2 — the story's newest attributable quotes (paired with their figure), for
    # the anchor to attribute; bounded by `news_quotes_per_story`, empty when none.
    quotes: list[tuple[Quote, Figure]] = field(default_factory=list)


# --- Candidate assembly (one story -> a scored, tagged candidate) -----------


def _hours_from(beat: Event, iw_now: datetime) -> float:
    """Absolute distance in hours between a beat's in-world datetime and now."""
    return abs((beat.in_world_datetime - iw_now).total_seconds()) / 3600.0


def _nearest_beat(beats: list[Event], iw_now: datetime) -> Event | None:
    """The beat closest in time to in-world now (None if the story has no beats)."""
    if not beats:
        return None
    return min(beats, key=lambda b: _hours_from(b, iw_now))


def _classify_temporal(
    beats: list[Event], new_beat: Event | None, iw_now: datetime
) -> tuple[str, Event | None]:
    """Return (temporal_kind, lead_beat) for a story from its beats vs in-world now.

    Breaking wins over trailed (a beat happening now leads even if more are upcoming);
    a story with only a soon upcoming beat is trailed; everything else is ongoing,
    framed around its freshest development (the new beat, else its latest beat).
    """
    nearest = _nearest_beat(beats, iw_now)
    if nearest is not None and _hours_from(nearest, iw_now) <= (
        settings.news_breaking_window_hours
    ):
        return KIND_BREAKING, nearest

    upcoming = [b for b in beats if b.in_world_datetime > iw_now]
    if upcoming:
        next_up = min(upcoming, key=lambda b: b.in_world_datetime)
        days_ahead = (next_up.in_world_datetime.date() - iw_now.date()).days
        if days_ahead <= settings.news_trail_horizon_days:
            return KIND_TRAILED, next_up

    lead = new_beat or (beats[-1] if beats else None)
    return KIND_ONGOING, lead


def _classify_coverage(
    story: Story, beats: list[Event], prior: NewsCoverage | None
) -> tuple[str, Event | None]:
    """Return (coverage_tag, new_beat) for a story from its prior coverage (D4.0).

    A never-covered story is `new`. Otherwise it `evolve`s when there is a beat newer
    than the one last reported (or the arc stage has moved on since); the newest such
    beat is the delta. With no newer beat or stage change it is a plain `repeat`.
    """
    if prior is None:
        return COVERAGE_NEW, None

    covered_dt: datetime | None = None
    if prior.last_beat_id is not None:
        covered = next((b for b in beats if b.id == prior.last_beat_id), None)
        covered_dt = covered.in_world_datetime if covered is not None else None

    if covered_dt is None:
        # Last time we had no concrete beat (a bare rumour) — any beat now is fresh.
        newer = list(beats)
    else:
        newer = [b for b in beats if b.in_world_datetime > covered_dt]

    stage_changed = story.arc_stage != prior.arc_stage
    if newer or stage_changed:
        new_beat = max(newer, key=lambda b: b.in_world_datetime) if newer else None
        return COVERAGE_EVOLVE, new_beat
    return COVERAGE_REPEAT, None


def _canon_score(story: Story) -> float:
    """Best canon-recall similarity for a story (0.0 when recall is unavailable).

    Grounds the story against the bible (D2): the highest cosine similarity among the
    `news_canon_recall_k` nearest canon facts to the story's title+summary. `retrieve`
    degrades to `[]` on any backend failure, so this returns 0.0 and selection falls
    back to temporal/structured ranking — the D4.1 capability fallback.
    """
    query = f"{story.title}. {story.summary}"
    hits = embeddings.retrieve(query, k=settings.news_canon_recall_k, corpus="canon")
    return max((h.score for h in hits), default=0.0)


def _build_candidate(
    conn: Connection, story: Story, iw_now: datetime, *, ground: bool = True
) -> SelectedStory:
    """Assemble one scored, tagged `SelectedStory` for a story (pre-selection).

    `ground=False` skips the canon-recall step (no embedding model load) — the pure
    temporal/structured ranking, used by the offline demo and any caller that doesn't
    want RAG in the loop.
    """
    beats = store.story_beats(conn, story.id)
    prior = store.last_coverage(conn, story.id)
    # D10.2 — the story's newest attributable quotes (with their figure), so the brief
    # can attribute them. Bounded; empty (no extra read cost beyond the JOIN) for a
    # people-less story.
    quotes = (
        store.attributed_quotes_for_story(
            conn, story.id, limit=settings.news_quotes_per_story
        )
        if settings.news_quotes_per_story > 0
        else []
    )

    coverage_tag, new_beat = _classify_coverage(story, beats, prior)
    temporal_kind, lead_beat = _classify_temporal(beats, new_beat, iw_now)
    latest_beat = beats[-1] if beats else None  # story_beats is chronological
    canon = _canon_score(story) if ground else 0.0

    # Recency: a lead beat near now scores ~1, decaying over days; canon grounding
    # and the kind/coverage bonuses lift the most newsworthy items in the ranking.
    if lead_beat is not None:
        recency = 1.0 / (1.0 + _hours_from(lead_beat, iw_now) / 24.0)
    else:
        recency = 0.0
    score = recency + settings.news_canon_weight * canon
    if temporal_kind == KIND_BREAKING:
        score += settings.news_breaking_bonus
    if coverage_tag == COVERAGE_EVOLVE:
        score += settings.news_evolve_bonus

    return SelectedStory(
        story=story,
        coverage_tag=coverage_tag,
        temporal_kind=temporal_kind,
        lead_beat=lead_beat,
        new_beat=new_beat,
        latest_beat=latest_beat,
        prior_coverage=prior,
        canon_score=canon,
        score=score,
        quotes=quotes,
    )


def _is_cold_repeat(cand: SelectedStory, iw_now: datetime) -> bool:
    """True if a `repeat` is older than the staleness limit — too cold to re-air."""
    if cand.coverage_tag != COVERAGE_REPEAT or cand.prior_coverage is None:
        return False
    stale_hours = (iw_now - cand.prior_coverage.covered_at).total_seconds() / 3600.0
    return stale_hours > settings.news_repeat_max_stale_hours


# --- Selection (assemble the mix, ranked + bounded) -------------------------


def _quota(kind: str) -> int:
    """The soft per-kind target count (config dials), in `_KIND_ORDER`."""
    return {
        KIND_BREAKING: settings.news_target_breaking,
        KIND_TRAILED: settings.news_target_trailed,
        KIND_ONGOING: settings.news_target_ongoing,
    }[kind]


def _assemble_mix(candidates: list[SelectedStory], count: int) -> list[SelectedStory]:
    """Pick up to `count` candidates honouring the per-kind quotas, then backfill.

    Buckets by temporal kind, ranks each bucket by score, fills up to each kind's
    quota without exceeding `count`, then backfills any remaining slots with the
    best leftover regardless of kind. Returns the result ranked by score (desc).
    """
    buckets: dict[str, list[SelectedStory]] = {k: [] for k in _KIND_ORDER}
    for cand in candidates:
        buckets[cand.temporal_kind].append(cand)
    for bucket in buckets.values():
        bucket.sort(key=lambda c: c.score, reverse=True)

    selected: list[SelectedStory] = []
    taken = dict.fromkeys(_KIND_ORDER, 0)
    # One quota pass: give each kind up to its quota, in order, capped at `count`.
    for kind in _KIND_ORDER:
        while taken[kind] < _quota(kind) and buckets[kind] and len(selected) < count:
            selected.append(buckets[kind].pop(0))
            taken[kind] += 1

    # Backfill remaining slots with the best leftover of any kind.
    leftover = [c for bucket in buckets.values() for c in bucket]
    leftover.sort(key=lambda c: c.score, reverse=True)
    while len(selected) < count and leftover:
        selected.append(leftover.pop(0))

    selected.sort(key=lambda c: c.score, reverse=True)
    return selected


def select_for(
    conn: Connection,
    now: datetime,
    *,
    count: int | None = None,
    ground: bool = True,
) -> list[SelectedStory]:
    """`select_stories` against a caller-supplied connection (the testable core).

    Pure reads, so it is safe to share a connection; `select_stories` is the
    convenience that opens its own short read transaction (never held across the
    producer's later LLM/TTS work). `ground=False` skips canon recall (the offline
    demo's fast path).
    """
    n = settings.news_story_count if count is None else count
    iw_now = clock.to_inworld(now)

    active = store.active_stories(conn)
    candidates = [_build_candidate(conn, s, iw_now, ground=ground) for s in active]
    fresh = [c for c in candidates if not _is_cold_repeat(c, iw_now)]
    selected = _assemble_mix(fresh, n)

    log.info(
        "news_select",
        now=now.isoformat(),
        active=len(active),
        dropped_cold=len(candidates) - len(fresh),
        selected=len(selected),
        tags=[f"{c.story.id}:{c.temporal_kind}/{c.coverage_tag}" for c in selected],
    )
    return selected


def select_stories(
    now: datetime, *, count: int | None = None, ground: bool = True
) -> list[SelectedStory]:
    """Choose + tag the running stories this hour's bulletin reports (D4.1).

    Reads the D3 active story log, tags each story new/repeat/evolve from the D4.0
    coverage memory and breaking/trailed/ongoing from the clock, grounds it against
    canon (D2 recall), drops cold repeats, and returns a ranked set of at most
    `count` (defaults to `settings.news_story_count`) mixing the three kinds. Opens
    its own short read transaction; the producer records coverage separately after a
    successful render (D4.2), so no DB transaction is held across generation.
    """
    with store.connect() as conn:
        return select_for(conn, now, count=count, ground=ground)

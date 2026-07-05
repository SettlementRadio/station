"""D7.4 — the music selector: the brain that decides what to play.

A RULE-BASED selection policy over the curated `tracks` catalogue — documented,
weighted, deterministic, **no LLM** (the LLM only writes the intro/back-announce
around the track this module picks). When a `music` slot comes up the scheduler
needs "the right song for this hour, in this world, not the one we just played";
that is a scoring problem, not a writing problem.

The policy (weights are the `music_select_*` dials in config.py):

  * **Daypart mood** — the active program's daypart prefers matching track
    moods (mellow/melancholy overnight, brighter through the day) — the
    `_DAYPART_MOODS` sets below.
  * **World mood** — the live story log (D3) tilts the pick: a cheap keyword
    rule classifies the active stories' tone (somber / upbeat / neutral) and
    matching track moods score (`_SOMBER_*` / `_UPBEAT_*` below). Never an LLM
    call — this runs inside the scheduler loop.
  * **Freshness** — a track or artist that aired within the D5 freshness window
    is penalised (the airplay memory records `music` slots' track id + artist —
    src/freshness.py), so songs don't loop on a small catalogue.
  * **Era spread** — sitting in the same era as the LAST spin is penalised, so
    the air mixes eras instead of running all "24th-century classics".
  * **Featured** — an artist named in a running story is boosted (the world
    just "released their album" → the station leans in), as is any track the
    human tags `featured`/`pinned` in config/tracks.yaml.

Determinism: `select_track(tracks, inputs, seed)` is a pure function — the same
candidates + inputs + seed always return the same track (unit-checkable). The
seed adds a small bounded jitter (`music_select_jitter`) so equal-scored tracks
rotate across hours instead of always winning by id; `choose_track` derives it
from the slot's air time.

Only PLAYABLE tracks (file on disk — `media.is_playable`) are candidates; the
catalogue's lore-only rows stay referenceable world culture (the D7.0 boundary).
Every DB/world read degrades: no catalogue → None (the music format falls back
to evergreen — never a silent gap); no story log / no program → neutral inputs.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..config import settings
from ..freshness import ARTIST_FEATURE_PREFIX
from ..logging_setup import get_logger
from ..world import programming, store
from . import media

log = get_logger(__name__)

# --- The policy's domain data (named constants, not config — config.py rule) --

# Daypart (the D6 grid's `daypart` label) -> the track moods that suit it.
# Vocabulary matches docs/MEDIA_LIBRARY.md's mood field (the manifest's values).
_DAYPART_MOODS: dict[str, frozenset[str]] = {
    "deep night": frozenset(
        {"melancholy", "contemplative", "wistful", "mellow", "tender", "serene"}
    ),
    "first light": frozenset({"hopeful", "bright", "warm", "serene", "tender"}),
    "daytime": frozenset({"joyful", "bright", "driving", "warm", "hopeful"}),
    "nightfall": frozenset({"warm", "mellow", "nostalgic", "tender", "wistful"}),
}

# World-tone classification: cheap keyword markers over the active stories'
# title/summary/tags. Deliberately small — a tilt, not a sentiment engine.
_SOMBER_MARKERS = frozenset(
    """
    missing lost accident mourning memorial tension dispute failure outage damage
    warning shortage stranded crisis emergency illness grief farewell
    """.split()
)
_UPBEAT_MARKERS = frozenset(
    """
    festival celebration award record victory launch reunion premiere anniversary
    harvest discovery rescue triumph founding jubilee
    """.split()
)

# World tone -> the track moods that answer it.
_TONE_MOODS: dict[str, frozenset[str]] = {
    "somber": frozenset({"melancholy", "solemn", "wistful", "contemplative", "tender"}),
    "upbeat": frozenset({"joyful", "bright", "hopeful", "driving", "warm"}),
}

# The human's explicit promote flags on a manifest row's tags (D7.4 "featured").
_FEATURE_TAGS = frozenset({"featured", "pinned"})

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SelectionInputs:
    """Everything the pure policy scores against — gathered once per slot."""

    daypart: str = ""  # the active program's daypart label ("" = unknown)
    world_tone: str = "neutral"  # somber | upbeat | neutral (from the story log)
    recent_track_ids: frozenset[str] = frozenset()  # aired in the freshness window
    recent_artists: frozenset[str] = frozenset()
    last_era: str | None = None  # era of the most recent spin (variety spread)
    featured_artists: frozenset[str] = frozenset()  # named in a running story
    stories: tuple[str, ...] = field(default=(), repr=False)  # debug provenance


def world_tone(texts: list[str]) -> str:
    """Classify the running world's tone from story text — the cheap rule.

    Counts somber vs upbeat marker words across the given texts (title + summary
    + tags of the active stories); the majority wins, ties/nothing = neutral.
    """
    tokens = [t for text in texts for t in _WORD_RE.findall(text.lower())]
    somber = sum(1 for t in tokens if t in _SOMBER_MARKERS)
    upbeat = sum(1 for t in tokens if t in _UPBEAT_MARKERS)
    if somber > upbeat:
        return "somber"
    if upbeat > somber:
        return "upbeat"
    return "neutral"


def score_track(track: store.Track, inputs: SelectionInputs) -> float:
    """The documented policy as one number — pure, weights from settings."""
    s = 0.0
    if track.mood in _DAYPART_MOODS.get(inputs.daypart, frozenset()):
        s += settings.music_select_daypart_weight
    if track.mood in _TONE_MOODS.get(inputs.world_tone, frozenset()):
        s += settings.music_select_world_weight
    if track.id in inputs.recent_track_ids:
        s -= settings.music_select_repeat_track_penalty
    if track.in_world_artist in inputs.recent_artists:
        s -= settings.music_select_repeat_artist_penalty
    if inputs.last_era is not None and track.era == inputs.last_era:
        s -= settings.music_select_era_repeat_penalty
    if track.in_world_artist in inputs.featured_artists or _FEATURE_TAGS & set(
        track.tags
    ):
        s += settings.music_select_featured_weight
    return s


def select_track(
    tracks: list[store.Track], inputs: SelectionInputs, *, seed: int
) -> store.Track | None:
    """Pick one track by the weighted policy — pure and deterministic.

    Candidates are scored, given a small seeded jitter (bounded by
    `music_select_jitter`; candidates are visited in id order so the rng stream
    is stable), and the highest total wins (id breaks exact ties). The same
    tracks + inputs + seed always return the same pick. None on no candidates.
    """
    if not tracks:
        return None
    rng = random.Random(seed)
    best: tuple[float, str] | None = None
    winner: store.Track | None = None
    for track in sorted(tracks, key=lambda t: t.id):
        total = score_track(track, inputs) + rng.uniform(
            0, settings.music_select_jitter
        )
        key = (total, track.id)
        if best is None or key > best:
            best = key
            winner = track
    assert winner is not None  # tracks is non-empty
    log.info(
        "selector_pick",
        track=winner.id,
        artist=winner.in_world_artist,
        mood=winner.mood,
        daypart=inputs.daypart,
        world_tone=inputs.world_tone,
        score=round(best[0], 2),
        candidates=len(tracks),
    )
    return winner


# --- Gathering the inputs (the impure shell around the pure policy) ----------


def _recent_spins(
    conn, now: datetime
) -> tuple[frozenset[str], frozenset[str], str | None]:
    """(recent track ids, recent artists, last spin's era) from the D5 memory.

    The airplay memory records each placed `music` slot's track id (topic) and
    artist (an `artist:` feature — src/freshness.py). The era of the most recent
    spin is resolved back through the catalogue for the variety spread.
    """
    within = timedelta(hours=settings.freshness_window_hours)
    records = store.recent_by_format(conn, now, "music", within=within)
    track_ids = frozenset(r.topic for r in records if r.topic)
    artists = frozenset(
        f[len(ARTIST_FEATURE_PREFIX) :]
        for r in records
        for f in r.features
        if f.startswith(ARTIST_FEATURE_PREFIX)
    )
    last_era: str | None = None
    for r in records:  # newest first (store contract)
        if r.topic:
            last = store.get_track(conn, r.topic)
            if last is not None:
                last_era = last.era
            break
    return track_ids, artists, last_era


def gather_inputs(
    conn, now: datetime, candidates: list[store.Track]
) -> SelectionInputs:
    """Assemble the selection inputs for one slot (DB reads; degrades gracefully)."""
    try:
        program = programming.program_for(now)
        daypart = program.daypart
    except Exception as exc:  # no grid — neutral daypart, never block the pick
        log.warning("selector_no_program", error=str(exc))
        daypart = ""

    stories = store.active_stories(conn, limit=settings.world_tick_active_context_limit)
    story_texts = [f"{s.title} {s.summary} {' '.join(s.tags)}" for s in stories]
    tone = world_tone(story_texts)

    # Featured = a candidate's artist literally named in a running story (the
    # world is talking about them). Exact, case-insensitive name match — cheap
    # and precise; D10's figure link makes this richer later.
    blob = " ".join(story_texts).lower()
    featured = frozenset(
        t.in_world_artist for t in candidates if t.in_world_artist.lower() in blob
    )

    track_ids, artists, last_era = _recent_spins(conn, now)
    return SelectionInputs(
        daypart=daypart,
        world_tone=tone,
        recent_track_ids=track_ids,
        recent_artists=artists,
        last_era=last_era,
        featured_artists=featured,
        stories=tuple(s.id for s in stories),
    )


def choose_track(now: datetime) -> store.Track | None:
    """The top-level pick for a `music` slot at `now`, or None (no playable track).

    Playable candidates only (file on disk); the seed derives from the slot's
    air time, so the same slot re-run picks the same track while different slots
    rotate. Any failure returns None — the music format then falls back to an
    evergreen segment, never a silent gap.
    """
    try:
        with store.connect() as conn:
            candidates = [t for t in store.all_tracks(conn) if media.is_playable(t)]
            if not candidates:
                log.warning("selector_no_playable_tracks")
                return None
            inputs = gather_inputs(conn, now, candidates)
    except Exception as exc:  # noqa: BLE001 — a selector failure must not crash a slot
        log.error("selector_failed", error=str(exc))
        return None
    return select_track(candidates, inputs, seed=int(now.timestamp()))

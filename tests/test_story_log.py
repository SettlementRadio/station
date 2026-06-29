"""Tests for the story-log schema (src/world/store.py) — D3.0 (the world engine).

Two layers, matching CLAUDE.md's "surgical, on real logic" rule:

* Pure arc-stage logic (no DB): the legal-transition rule is the brittle bit a
  silent bug would corrupt an arc through — forward-or-same only, `past` terminal,
  unknown stages fail loud.
* Store integration (skips cleanly without Postgres/pgvector): a story + its beats
  round-trip; `advance_story` moves the stage; `active_stories` excludes resolved
  ones; and the LOAD-BEARING seed/reset contract — a `seed-canon` refresh leaves the
  tick-generated world standing while a full reset clears it. Every DB test rolls
  back at teardown, so it NEVER mutates a developer's seeded dev DB (the destructive
  `reset-world`-scope path included).
"""

from __future__ import annotations

import contextlib
from datetime import datetime

import pytest
from src.world import store

# --- Arc-stage transitions (pure; no DB) ------------------------------------


def test_arc_stages_are_ordered_and_past_is_terminal():
    assert store.ARC_STAGES == (
        "rumoured",
        "upcoming",
        "happening",
        "developing",
        "past",
    )
    assert store.is_resolved(store.ARC_PAST)
    assert not store.is_resolved(store.ARC_DEVELOPING)
    assert store.ARC_TRANSITIONS[store.ARC_PAST] == ()  # nothing follows `past`


def test_can_transition_forward_same_and_jumps_ok():
    # Same stage (a new beat, no move), one step, and a forward jump are all legal.
    assert store.can_transition(store.ARC_UPCOMING, store.ARC_UPCOMING)
    assert store.can_transition(store.ARC_UPCOMING, store.ARC_HAPPENING)
    assert store.can_transition(store.ARC_RUMOURED, store.ARC_PAST)  # false rumour


def test_can_transition_rejects_backward_and_terminal():
    assert not store.can_transition(store.ARC_HAPPENING, store.ARC_UPCOMING)
    assert not store.can_transition(store.ARC_PAST, store.ARC_DEVELOPING)  # terminal


def test_can_transition_fails_loud_on_unknown_stage():
    with pytest.raises(ValueError, match="unknown arc stage"):
        store.can_transition("nonsense", store.ARC_PAST)


# --- Store integration (skips without Postgres/pgvector) --------------------


@pytest.fixture
def db():
    """A store connection with the schema, that ALWAYS rolls back at teardown.

    Skips cleanly if Postgres or pgvector is absent (the suite must stay green on a
    machine without it). The teardown rollback is what makes the destructive
    `reset-world`-scope test safe to run against a real dev DB — nothing persists.
    """
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001 - any connect failure -> skip, not fail
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001 - e.g. CREATE EXTENSION vector unavailable
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"pgvector unavailable: {exc}")
    try:
        yield conn
    finally:
        conn.rollback()  # undo every test write (incl. any TRUNCATE) — dev DB pristine
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _story(
    story_id: str, *, stage: str, source: str = store.EVENT_SOURCE_TICK
) -> store.Story:
    return store.Story(
        id=story_id,
        title=f"Story {story_id}",
        summary="A happening in the +600y world.",
        arc_stage=stage,
        tags=["finance"],
        source=source,
        created_tick=1,
    )


def _beat(
    beat_id: str, story_id: str, *, source: str = store.EVENT_SOURCE_TICK
) -> store.Event:
    return store.Event(
        id=beat_id,
        title=f"Beat {beat_id}",
        body="A development.",
        in_world_datetime=datetime(2626, 6, 24, 20, 0),
        status="today",
        source=source,
        story_id=story_id,
        beat_kind="development",
    )


def test_story_and_beats_round_trip(db):
    store.insert_story(db, _story("d30-s1", stage=store.ARC_UPCOMING))
    store.insert_beats(db, [_beat("d30-b1", "d30-s1"), _beat("d30-b2", "d30-s1")])

    got = store.get_story(db, "d30-s1")
    assert got is not None
    assert got.arc_stage == store.ARC_UPCOMING
    assert got.source == store.EVENT_SOURCE_TICK
    assert got.created_at is not None  # DB default filled the audit timestamp

    beats = store.story_beats(db, "d30-s1")
    assert [b.id for b in beats] == ["d30-b1", "d30-b2"]
    assert all(b.story_id == "d30-s1" for b in beats)
    assert beats[0].beat_kind == "development"  # the beat link round-trips


def test_insert_beats_requires_story_id(db):
    orphan = store.Event(
        id="d30-orphan",
        title="No story",
        body="x",
        in_world_datetime=datetime(2626, 1, 1),
        status="today",
    )
    with pytest.raises(ValueError, match="missing story_id"):
        store.insert_beats(db, [orphan])


def test_advance_story_moves_stage_and_rejects_backward(db):
    store.insert_story(db, _story("d30-adv", stage=store.ARC_UPCOMING))

    store.advance_story(db, "d30-adv", store.ARC_HAPPENING, tick=2)
    moved = store.get_story(db, "d30-adv")
    assert moved.arc_stage == store.ARC_HAPPENING
    assert moved.last_advanced_tick == 2

    with pytest.raises(ValueError, match="illegal arc transition"):
        store.advance_story(db, "d30-adv", store.ARC_UPCOMING)  # backward -> reject


def test_active_stories_excludes_resolved(db):
    store.insert_story(db, _story("d30-active", stage=store.ARC_DEVELOPING))
    store.insert_story(db, _story("d30-done", stage=store.ARC_PAST))

    ids = {s.id for s in store.active_stories(db)}
    assert "d30-active" in ids
    assert "d30-done" not in ids  # resolved stories stop being offered for advancing


def test_seed_canon_keeps_tick_stories_full_reset_clears_them(db):
    # A seeded example story (D3.5) vs a tick-generated one: a canon refresh must
    # replace only the seed, leaving the living world standing; a full reset clears all.
    seed, tick = store.EVENT_SOURCE_SEED, store.EVENT_SOURCE_TICK
    store.insert_story(db, _story("d30-seed", stage=store.ARC_UPCOMING, source=seed))
    store.insert_story(db, _story("d30-tick", stage=store.ARC_UPCOMING, source=tick))
    store.insert_beats(db, [_beat("d30-seed-b", "d30-seed", source=seed)])
    store.insert_beats(db, [_beat("d30-tick-b", "d30-tick", source=tick)])

    store.clear_world(db, scope="canon")  # the SAFE refresh
    assert store.get_story(db, "d30-seed") is None  # seed story replaced
    assert store.get_story(db, "d30-tick") is not None  # living world SURVIVES
    assert store.get_event(db, "d30-seed-b") is None  # seed beat gone
    assert store.get_event(db, "d30-tick-b") is not None  # tick beat survives

    store.clear_world(db, scope="world")  # the DESTRUCTIVE full wipe
    assert store.get_story(db, "d30-tick") is None  # now cleared
    assert store.counts(db)["stories"] == 0

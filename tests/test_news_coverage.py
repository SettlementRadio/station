"""Tests for the news-desk coverage memory (src/world/store.py) — D4.0.

The substrate the rest of D4 reads: a per-story record of how the desk has covered
each story (stage + latest beat + angle), so bulletins can repeat, evolve, and stay
consistent. Surgical, on the real logic a silent bug would corrupt:

* a coverage row round-trips (stage/beat/angle read back);
* `last_coverage` returns the LATEST of several, and None when never covered;
* `coverage_since` windows by in-world time;
* the seed/reset contract: coverage SURVIVES a `seed-canon` refresh and is CLEARED by
  the destructive `reset-world`, and is counted by `counts`;
* the FK CASCADE: replacing a seed story on a canon refresh drops its coverage (no
  orphan), while tick-story coverage stands.

Every DB test rolls back at teardown, so the suite never mutates a dev DB and skips
cleanly without Postgres/pgvector.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

import pytest
from src.world import store


@pytest.fixture
def db():
    """A store connection with the schema, that ALWAYS rolls back at teardown."""
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
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _story(
    story_id: str,
    *,
    stage: str = store.ARC_UPCOMING,
    source: str = store.EVENT_SOURCE_TICK,
) -> store.Story:
    return store.Story(
        id=story_id,
        title=f"Story {story_id}",
        summary="A happening in the +600y world.",
        arc_stage=stage,
        source=source,
        created_tick=1,
    )


def _beat(beat_id: str, story_id: str) -> store.Event:
    return store.Event(
        id=beat_id,
        title=f"Beat {beat_id}",
        body="A development.",
        in_world_datetime=datetime(2626, 6, 24, 20, 0),
        status="today",
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind="development",
    )


def _coverage(
    story_id: str, *, when: datetime, stage: str, beat_id: str | None, angle: str = ""
) -> store.NewsCoverage:
    return store.NewsCoverage(
        story_id=story_id,
        covered_at=when,
        arc_stage=stage,
        last_beat_id=beat_id,
        angle=angle,
    )


def test_coverage_round_trips_stage_beat_and_angle(db):
    store.insert_story(db, _story("d40-s1", stage=store.ARC_HAPPENING))
    store.insert_beats(db, [_beat("d40-s1-b1", "d40-s1")])

    store.record_coverage(
        db,
        _coverage(
            "d40-s1",
            when=datetime(2626, 6, 24, 21, 0),
            stage=store.ARC_HAPPENING,
            beat_id="d40-s1-b1",
            angle="the harvest failure",
        ),
    )

    got = store.last_coverage(db, "d40-s1")
    assert got is not None
    assert got.arc_stage == store.ARC_HAPPENING
    assert got.last_beat_id == "d40-s1-b1"
    assert got.angle == "the harvest failure"
    assert got.id is not None  # DB assigned the identity


def test_last_coverage_returns_most_recent(db):
    store.insert_story(db, _story("d40-s2", stage=store.ARC_DEVELOPING))
    store.insert_beats(db, [_beat("d40-s2-b1", "d40-s2"), _beat("d40-s2-b2", "d40-s2")])

    store.record_coverage(
        db,
        _coverage(
            "d40-s2",
            when=datetime(2626, 6, 24, 9, 0),
            stage=store.ARC_UPCOMING,
            beat_id="d40-s2-b1",
        ),
    )
    store.record_coverage(
        db,
        _coverage(
            "d40-s2",
            when=datetime(2626, 6, 24, 17, 0),
            stage=store.ARC_DEVELOPING,
            beat_id="d40-s2-b2",
        ),
    )

    latest = store.last_coverage(db, "d40-s2")
    assert latest.arc_stage == store.ARC_DEVELOPING  # the later bulletin wins
    assert latest.last_beat_id == "d40-s2-b2"


def test_last_coverage_none_when_never_covered(db):
    store.insert_story(db, _story("d40-uncovered"))
    assert store.last_coverage(db, "d40-uncovered") is None


def test_coverage_can_record_without_a_beat(db):
    # A rumour with no concrete event row yet: last_beat_id NULL is allowed.
    store.insert_story(db, _story("d40-rumour", stage=store.ARC_RUMOURED))
    store.record_coverage(
        db,
        _coverage(
            "d40-rumour",
            when=datetime(2626, 6, 24, 8, 0),
            stage=store.ARC_RUMOURED,
            beat_id=None,
        ),
    )
    got = store.last_coverage(db, "d40-rumour")
    assert got is not None
    assert got.last_beat_id is None


def test_coverage_since_windows_by_inworld_time(db):
    store.insert_story(db, _story("d40-s3"))
    store.record_coverage(
        db,
        _coverage(
            "d40-s3",
            when=datetime(2626, 6, 24, 6, 0),
            stage=store.ARC_UPCOMING,
            beat_id=None,
        ),
    )
    store.record_coverage(
        db,
        _coverage(
            "d40-s3",
            when=datetime(2626, 6, 24, 18, 0),
            stage=store.ARC_UPCOMING,
            beat_id=None,
        ),
    )

    since_noon = store.coverage_since(db, datetime(2626, 6, 24, 12, 0))
    times = [c.covered_at for c in since_noon if c.story_id == "d40-s3"]
    assert datetime(2626, 6, 24, 18, 0) in times
    assert datetime(2626, 6, 24, 6, 0) not in times  # before the window


def test_coverage_counted_and_cleared_by_reset_kept_by_canon_refresh(db):
    # A seed story + a tick story, each covered. A canon refresh keeps tick coverage
    # (and CASCADE-drops the replaced seed story's coverage); a full reset clears all.
    # Delta-count, not absolute: a real dev DB may already hold coverage from aired
    # bulletins (a rolled-back txn hides this test's writes, not pre-committed rows).
    base = store.counts(db)["news_coverage"]
    store.insert_story(db, _story("d40-seed", source=store.EVENT_SOURCE_SEED))
    store.insert_story(db, _story("d40-tick", source=store.EVENT_SOURCE_TICK))
    when = datetime(2626, 6, 24, 12, 0)
    store.record_coverage(
        db, _coverage("d40-seed", when=when, stage=store.ARC_UPCOMING, beat_id=None)
    )
    store.record_coverage(
        db, _coverage("d40-tick", when=when, stage=store.ARC_UPCOMING, beat_id=None)
    )

    assert store.counts(db)["news_coverage"] == base + 2  # folded into counts

    store.clear_world(db, scope="canon")  # SAFE refresh
    assert store.last_coverage(db, "d40-tick") is not None  # living coverage stands
    assert store.last_coverage(db, "d40-seed") is None  # seed story + coverage gone

    store.clear_world(db, scope="world")  # DESTRUCTIVE wipe
    assert store.counts(db)["news_coverage"] == 0

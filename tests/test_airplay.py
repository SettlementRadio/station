"""Tests for the on-air anti-repetition memory (src/world/store.py) — D5.0.

The substrate the rest of D5 reads: a broad, cross-format record of WHAT aired
recently (a topic/beat handle, an opening fingerprint, a few key phrases — never the
audio), so the writers' room can steer the next segment off recently-used ground.
Surgical, on the real logic a silent bug would corrupt:

* a record round-trips (topic/opening/features read back);
* `recent_airplay` windows by in-world time and returns newest-first;
* `recent_by_format` scopes to one format;
* the reads degrade cleanly on a cold start (empty memory);
* `prune_airplay` bounds the table (drops rows older than the keep window);
* the seed/reset + persistence contract: airplay SURVIVES a `seed-canon` refresh, is
  CLEARED by the destructive `reset-world`, and is counted by `counts`.

Every DB test rolls back at teardown, so the suite never mutates a dev DB and skips
cleanly without Postgres/pgvector.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta

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


def _record(
    seg_id: str,
    *,
    fmt: str = "talk",
    when: datetime,
    topic: str | None = "the relay drift",
    opening: str | None = "tonight we open on the quiet",
    features: list[str] | None = None,
) -> store.AirplayRecord:
    return store.AirplayRecord(
        seg_id=seg_id,
        format=fmt,
        aired_at=when,
        topic=topic,
        opening=opening,
        features=features if features is not None else ["drift", "quiet", "relay"],
    )


def test_record_round_trips_topic_opening_and_features(db):
    when = datetime(2626, 6, 24, 21, 0)
    store.record_airplay(db, _record("d50-s1", when=when))

    got = store.recent_airplay(db, when, within=timedelta(hours=6))
    mine = [r for r in got if r.seg_id == "d50-s1"]
    assert len(mine) == 1
    rec = mine[0]
    assert rec.format == "talk"
    assert rec.aired_at == when
    assert rec.topic == "the relay drift"
    assert rec.opening == "tonight we open on the quiet"
    assert rec.features == ["drift", "quiet", "relay"]
    assert rec.id is not None  # DB assigned the identity


def test_recent_airplay_windows_by_inworld_time_newest_first(db):
    now = datetime(2626, 6, 24, 20, 0)
    store.record_airplay(db, _record("d50-old", when=now - timedelta(hours=10)))
    store.record_airplay(db, _record("d50-mid", when=now - timedelta(hours=2)))
    store.record_airplay(db, _record("d50-new", when=now - timedelta(minutes=30)))

    got = store.recent_airplay(db, now, within=timedelta(hours=6))
    ids = [r.seg_id for r in got if r.seg_id.startswith("d50-")]
    assert "d50-old" not in ids  # outside the 6h window
    assert ids[: ids.index("d50-mid") + 1].count("d50-new") == 1
    # newest first: d50-new precedes d50-mid
    assert ids.index("d50-new") < ids.index("d50-mid")


def test_recent_airplay_includes_segments_placed_ahead_of_now(db):
    # The buffer model: segments are placed with FUTURE air_times. The next segment's
    # generation must still see them as "recent" so it doesn't loop them.
    now = datetime(2626, 6, 24, 20, 0)
    store.record_airplay(db, _record("d50-ahead", when=now + timedelta(hours=2)))

    got = store.recent_airplay(db, now, within=timedelta(hours=6))
    assert any(r.seg_id == "d50-ahead" for r in got)


def test_recent_by_format_scopes_to_one_format(db):
    now = datetime(2626, 6, 24, 20, 0)
    store.record_airplay(db, _record("d50-talk", fmt="talk", when=now))
    store.record_airplay(db, _record("d50-news", fmt="news", when=now))

    talk = [
        r.seg_id
        for r in store.recent_by_format(db, now, "talk", within=timedelta(hours=6))
    ]
    assert "d50-talk" in talk
    assert "d50-news" not in talk


def test_recent_limit_caps_rows(db):
    now = datetime(2626, 6, 24, 20, 0)
    for i in range(5):
        store.record_airplay(
            db, _record(f"d50-cap-{i}", when=now - timedelta(minutes=i))
        )
    got = store.recent_airplay(db, now, within=timedelta(hours=6), limit=2)
    # newest two (i=0, i=1)
    assert len(got) <= 2


def test_reads_degrade_on_cold_start(db):
    # Empty memory (within a rolled-back txn, far in the future so no committed rows
    # fall in the window) returns an empty list rather than erroring.
    far = datetime(3000, 1, 1, 0, 0)
    assert store.recent_airplay(db, far, within=timedelta(hours=1)) == []
    assert store.recent_by_format(db, far, "talk", within=timedelta(hours=1)) == []


def test_prune_airplay_drops_rows_older_than_keep(db):
    now = datetime(2626, 6, 24, 20, 0)
    store.record_airplay(db, _record("d50-keep", when=now - timedelta(hours=5)))
    store.record_airplay(db, _record("d50-drop", when=now - timedelta(hours=30)))

    removed = store.prune_airplay(db, now, keep=timedelta(hours=24))
    assert removed >= 1

    surviving = [
        r.seg_id
        for r in store.recent_airplay(db, now, within=timedelta(hours=48))
        if r.seg_id.startswith("d50-")
    ]
    assert "d50-keep" in surviving
    assert "d50-drop" not in surviving


def test_airplay_counted_and_cleared_by_reset_kept_by_canon_refresh(db):
    # Delta-count, not absolute: a real dev DB may already hold airplay rows from aired
    # segments (a rolled-back txn hides this test's writes, not pre-committed rows).
    base = store.counts(db)["airplay_history"]
    when = datetime(2626, 6, 24, 12, 0)
    store.record_airplay(db, _record("d50-a", when=when))
    store.record_airplay(db, _record("d50-b", when=when))

    assert store.counts(db)["airplay_history"] == base + 2  # folded into counts

    store.clear_world(db, scope="canon")  # SAFE refresh — airplay SURVIVES
    assert store.counts(db)["airplay_history"] == base + 2

    store.clear_world(db, scope="world")  # DESTRUCTIVE wipe — airplay cleared
    assert store.counts(db)["airplay_history"] == 0

"""Tests for the small-items log (src/world/store.py) — Q1.0 (the supply keystone).

An item is the arc-less, disposable companion to a story: one sentence, dozens a
night, read for a day and then gone. The logic worth testing is exactly the part that
differs from `stories` — the bounded read (window + domain filter + status), the sweep
that makes items expire, and the §2a seed/reset posture (a canon refresh must leave a
night's items standing; the destructive reset must clear them).

Store-integration only, and it skips cleanly without Postgres/pgvector. Every test
rolls back at teardown, so it never mutates a developer's seeded dev DB — including the
`reset-world`-scope path.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta

import pytest
from src.world import store

IW_NOW = datetime(2626, 6, 24, 12, 0)


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
        conn.rollback()  # undo every test write (incl. any TRUNCATE) — dev DB pristine
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _item(
    item_id: str,
    *,
    domain: str = "finance",
    hours_ago: float = 1.0,
    status: str = store.ITEM_STATUS_ACTIVE,
    text: str = "The grain price moved a quarter and nobody enjoyed it.",
) -> store.Item:
    return store.Item(
        id=item_id,
        text=text,
        domain=domain,
        in_world_datetime=IW_NOW - timedelta(hours=hours_ago),
        tags=[domain],
        source=store.ITEM_SOURCE_TICK,
        created_tick=1,
        status=status,
    )


def test_items_round_trip(db):
    store.insert_items(db, [_item("q10-a"), _item("q10-b", hours_ago=2)])

    got = store.items_in_range(db, IW_NOW - timedelta(hours=36), IW_NOW)
    ids = [i.id for i in got]
    assert ids == ["q10-a", "q10-b"]  # newest first
    assert got[0].domain == "finance"
    assert got[0].tags == ["finance"]
    assert got[0].source == store.ITEM_SOURCE_TICK
    assert got[0].created_tick == 1


def test_insert_items_ignores_a_duplicate_id(db):
    # Items are disposable: a colliding id drops that row, it never sinks the batch.
    store.insert_items(db, [_item("q10-dup")])
    store.insert_items(
        db, [_item("q10-dup", text="A different line."), _item("q10-ok")]
    )

    got = {
        i.id: i.text for i in store.items_in_range(db, IW_NOW - timedelta(2), IW_NOW)
    }
    assert "q10-ok" in got
    assert got["q10-dup"].startswith("The grain price")  # the first write stands


def test_items_in_range_bounds_window_domain_and_status(db):
    store.insert_items(
        db,
        [
            _item("q10-fresh", hours_ago=1),
            _item("q10-stale", hours_ago=200),  # outside any sane read window
            _item("q10-health", domain="health", hours_ago=1),
            _item("q10-dropped", hours_ago=1, status=store.ITEM_STATUS_DROPPED),
        ],
    )
    window_start = IW_NOW - timedelta(hours=36)

    ids = {i.id for i in store.items_in_range(db, window_start, IW_NOW)}
    assert ids == {"q10-fresh", "q10-health"}  # stale is out of window
    assert "q10-dropped" not in ids  # a flagged item never reaches a read

    scoped = store.items_in_range(db, window_start, IW_NOW, domains=["Health"])
    assert [i.id for i in scoped] == ["q10-health"]  # domain match is case-insensitive

    assert len(store.items_in_range(db, window_start, IW_NOW, limit=1)) == 1


def test_prune_items_expires_the_old_ones(db):
    store.insert_items(
        db, [_item("q10-keep", hours_ago=1), _item("q10-gone", hours_ago=24 * 9)]
    )

    removed = store.prune_items(db, IW_NOW, keep=timedelta(days=7))
    assert removed == 1

    survivors = {i.id for i in store.items_in_range(db, IW_NOW - timedelta(30), IW_NOW)}
    assert survivors == {"q10-keep"}


def test_seed_canon_keeps_items_full_reset_clears_them(db):
    # §2a: tick-owned, survives `seed-canon` (no folder-authored items to replace),
    # cleared by the destructive `reset-world`.
    store.insert_items(db, [_item("q10-live")])

    store.clear_world(db, scope="canon")  # the SAFE refresh
    assert store.counts(db)["items"] == 1  # a night's items SURVIVE a bible edit

    store.clear_world(db, scope="world")  # the DESTRUCTIVE full wipe
    assert store.counts(db)["items"] == 0

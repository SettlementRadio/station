"""Tests for the major-event gate (PHASE_R_TASKS.md R5.3).

The load-bearing property: a tick-flagged MAJOR story lands `pending` and is
INVISIBLE to every air-reaching read until the operator acts — it never airs while
pending, airs once approved, and vanishes (archived + embeddings stripped) once
rejected; a non-major story is unaffected. Two halves:

* the WRITE side (`world_tick`): the model's `major` flag survives into the stored
  story's `status` (pure, no DB);
* the READ side (`store.active_stories` / `events_in_range`): a pending/archived
  story's rows are excluded; approve/reject flip that. The DB test rolls back at
  teardown and skips cleanly without Postgres. No LLM is called.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta

import pytest
from src.config import settings
from src.world import clock, store
from src.world import world_tick as wt

TICK_NOW = datetime(2026, 6, 24, 6, 0)  # in-world +600y → 2626-06-24 06:00
IW = clock.to_inworld(TICK_NOW)


# --- Write side: the major flag → pending status (pure, no DB) ----------------


def _proposal(*, major: bool) -> wt.ProposedStory:
    return wt.ProposedStory(
        title="The lattice war begins",
        summary="Two settlements break the long peace.",
        scale="large",
        domain="politics",
        arc_stage=store.ARC_HAPPENING,
        beats=[wt.ProposedBeat("First strike", "It began at dawn.", "event", 0, 6)],
        major=major,
    )


def _ctx() -> wt._TickContext:
    return wt._TickContext(bible="", active_summary="", now=TICK_NOW, iw_now=IW)


def test_coerce_story_reads_major_and_defaults_false():
    base = {"title": "T", "summary": "S", "beats": [{"title": "b", "body": "x"}]}
    assert wt._coerce_story({**base, "major": True}).major is True
    assert wt._coerce_story(base).major is False  # pre-R5.3 proposal → not major


def test_materialise_marks_major_pending_else_active():
    major, _ = wt._materialise(_proposal(major=True), 1, _ctx(), 0)
    assert major.status == store.STORY_STATUS_PENDING
    ordinary, _ = wt._materialise(_proposal(major=False), 1, _ctx(), 1)
    assert ordinary.status == store.STORY_STATUS_ACTIVE


def test_drop_stale_pending_releases_old_pending_only():
    fresh = store.Story(
        id="p1",
        title="A",
        summary="",
        arc_stage=store.ARC_HAPPENING,
        status=store.STORY_STATUS_PENDING,
        created_at=TICK_NOW,
    )
    stale = store.Story(
        id="p2",
        title="B",
        summary="",
        arc_stage=store.ARC_HAPPENING,
        status=store.STORY_STATUS_PENDING,
        created_at=TICK_NOW - timedelta(days=10),
    )
    active = store.Story(
        id="a1",
        title="C",
        summary="",
        arc_stage=store.ARC_HAPPENING,
        status=store.STORY_STATUS_ACTIVE,
        created_at=TICK_NOW - timedelta(days=10),
    )
    kept = wt._drop_stale_pending([fresh, stale, active], TICK_NOW)
    ids = {s.id for s in kept}
    assert ids == {"p1", "a1"}  # fresh pending + active kept; stale pending dropped


# --- Read side: the gate over the real store (DB) ----------------------------


@pytest.fixture
def db():
    """A store connection with the schema, that ALWAYS rolls back at teardown."""
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001
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


def _story(sid: str, status: str) -> store.Story:
    return store.Story(
        id=sid,
        title=f"Story {sid}",
        summary="A happening.",
        arc_stage=store.ARC_HAPPENING,
        source=store.EVENT_SOURCE_TICK,
        created_tick=1,
        status=status,
    )


def _beat(sid: str) -> store.Event:
    return store.Event(
        id=f"{sid}-b0",
        title=f"Beat of {sid}",
        body="A development.",
        in_world_datetime=IW.replace(hour=12),
        status="today",
        source=store.EVENT_SOURCE_TICK,
        story_id=sid,
    )


def _seed(db) -> None:  # noqa: ANN001
    store.clear_world(db, scope="world")
    store.insert_story(db, _story("act", store.STORY_STATUS_ACTIVE))
    store.insert_story(db, _story("maj", store.STORY_STATUS_PENDING))
    store.insert_beats(db, [_beat("act"), _beat("maj")])


def _window(db) -> list[store.Event]:  # noqa: ANN001
    lo, hi = IW.replace(hour=0), IW.replace(hour=23, minute=59)
    return store.events_in_range(db, lo, hi)


def test_pending_major_is_excluded_from_air_reads(db):
    _seed(db)
    # active_stories excludes the pending major; pending_stories is the queue.
    assert [s.id for s in store.active_stories(db)] == ["act"]
    assert [s.id for s in store.pending_stories(db)] == ["maj"]
    # events_in_range hides the pending story's beat, keeps the active one's.
    beat_ids = {e.id for e in _window(db)}
    assert "act-b0" in beat_ids and "maj-b0" not in beat_ids


def test_approve_lets_the_major_air(db):
    _seed(db)
    store.set_story_status(db, "maj", store.STORY_STATUS_ACTIVE)
    assert {s.id for s in store.active_stories(db)} == {"act", "maj"}
    assert {e.id for e in _window(db)} >= {"act-b0", "maj-b0"}
    assert store.pending_stories(db) == []


def test_reject_archives_and_strips_embeddings(db):
    _seed(db)
    # give the pending story embeddings (story + its beat), then reject.
    vec = [0.0] * settings.embeddings_dim
    store.insert_embeddings(
        db, "story", [store.EmbeddingRow("maj", "text", "tick", vec)]
    )
    store.insert_embeddings(
        db, "event", [store.EmbeddingRow("maj-b0", "text", "tick", vec)]
    )

    def _emb_count() -> int:
        return db.execute(
            "SELECT count(*) FROM embeddings WHERE entity_id IN ('maj', 'maj-b0')"
        ).fetchone()[0]

    assert _emb_count() == 2
    store.reject_story(db, "maj")

    archived = store.get_story(db, "maj")
    assert archived.status == store.STORY_STATUS_ARCHIVED
    assert store.pending_stories(db) == []  # gone from the queue
    assert {s.id for s in store.active_stories(db)} == {"act"}  # never active
    assert "maj-b0" not in {e.id for e in _window(db)}  # still off air
    assert _emb_count() == 0  # embeddings stripped from recall


def test_non_major_flow_is_byte_identical(db):
    """With no pending/archived stories, the reads match the pre-R5.3 behaviour."""
    store.clear_world(db, scope="world")
    store.insert_story(db, _story("a1", store.STORY_STATUS_ACTIVE))
    store.insert_story(db, _story("a2", store.STORY_STATUS_ACTIVE))
    store.insert_beats(db, [_beat("a1"), _beat("a2")])
    assert {s.id for s in store.active_stories(db)} == {"a1", "a2"}
    assert {e.id for e in _window(db)} == {"a1-b0", "a2-b0"}
    assert store.pending_stories(db) == []

"""Tests for news-desk story selection (src/formats/news_select.py) — D4.1.

The brittle logic a silent bug would corrupt: tagging each story new/repeat/evolve
from the D4.0 coverage memory, classifying breaking/trailed/ongoing from the clock,
dropping cold repeats, and assembling a ranked, bounded mix. `embeddings.retrieve` is
monkeypatched so the canon-recall step never loads a model or needs pgvector — which
also exercises the capability-fallback (recall returns nothing → temporal ranking).

DB tests roll back at teardown and skip cleanly without Postgres.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

import pytest
from src.formats import news_select
from src.providers import embeddings
from src.world import store

# A fixed real `now`; the in-world face is +600 (2626-06-24 12:00).
NOW = datetime(2026, 6, 24, 12, 0)


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


@pytest.fixture(autouse=True)
def _no_recall(monkeypatch):
    """Default: canon recall returns nothing (no model load; structured fallback)."""
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [])


def _story(story_id: str, *, stage: str) -> store.Story:
    return store.Story(
        id=story_id,
        title=f"Story {story_id}",
        summary="A happening in the +600y world.",
        arc_stage=stage,
        source=store.EVENT_SOURCE_TICK,
        created_tick=1,
    )


def _beat(beat_id: str, story_id: str, when: datetime) -> store.Event:
    return store.Event(
        id=beat_id,
        title=f"Beat {beat_id}",
        body="A development.",
        in_world_datetime=when,
        status="today",
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind="development",
    )


def _cov(
    story_id: str, *, when: datetime, stage: str, beat_id: str | None
) -> store.NewsCoverage:
    return store.NewsCoverage(
        story_id=story_id, covered_at=when, arc_stage=stage, last_beat_id=beat_id
    )


def _seed_world(db):
    """A small story log spanning every tag x kind the selector must distinguish.

    Clears the world first (inside the rolled-back txn) so selection is deterministic
    regardless of what a developer's dev DB already holds — restored at teardown.
    """
    store.clear_world(db, scope="world")
    # breaking + new: a beat right now, never covered.
    store.insert_story(db, _story("breaking-new", stage=store.ARC_HAPPENING))
    store.insert_beats(db, [_beat("bn1", "breaking-new", datetime(2626, 6, 24, 12, 0))])

    # trailed + new: a beat two days out, never covered.
    store.insert_story(db, _story("trailed-new", stage=store.ARC_UPCOMING))
    store.insert_beats(db, [_beat("tn1", "trailed-new", datetime(2626, 6, 26, 9, 0))])

    # ongoing + repeat: a past beat, covered recently, no new beat/stage since.
    store.insert_story(db, _story("ongoing-repeat", stage=store.ARC_DEVELOPING))
    store.insert_beats(
        db, [_beat("or1", "ongoing-repeat", datetime(2626, 6, 20, 10, 0))]
    )
    store.record_coverage(
        db,
        _cov(
            "ongoing-repeat",
            when=datetime(2626, 6, 24, 6, 0),  # 6h ago — not stale
            stage=store.ARC_DEVELOPING,
            beat_id="or1",
        ),
    )

    # ongoing + evolve: covered at an earlier beat; a newer beat has since landed.
    store.insert_story(db, _story("evolving", stage=store.ARC_DEVELOPING))
    store.insert_beats(
        db,
        [
            _beat("ev_old", "evolving", datetime(2626, 6, 19, 10, 0)),
            _beat("ev_new", "evolving", datetime(2626, 6, 22, 10, 0)),
        ],
    )
    store.record_coverage(
        db,
        _cov(
            "evolving",
            when=datetime(2626, 6, 20, 6, 0),
            stage=store.ARC_DEVELOPING,
            beat_id="ev_old",  # newer beat ev_new exists -> evolve
        ),
    )

    # repeat gone cold: covered long ago, no new beat -> dropped from selection.
    store.insert_story(db, _story("stale-repeat", stage=store.ARC_DEVELOPING))
    store.insert_beats(db, [_beat("sr1", "stale-repeat", datetime(2626, 6, 18, 10, 0))])
    store.record_coverage(
        db,
        _cov(
            "stale-repeat",
            when=datetime(2626, 6, 22, 0, 0),  # >18h ago, no new beat -> cold
            stage=store.ARC_DEVELOPING,
            beat_id="sr1",
        ),
    )


def _by_id(selected):
    return {s.story.id: s for s in selected}


def test_tags_and_kinds_are_assigned_per_story(db):
    _seed_world(db)
    sel = _by_id(news_select.select_for(db, NOW, count=10))

    assert sel["breaking-new"].temporal_kind == news_select.KIND_BREAKING
    assert sel["breaking-new"].coverage_tag == news_select.COVERAGE_NEW

    assert sel["trailed-new"].temporal_kind == news_select.KIND_TRAILED
    assert sel["trailed-new"].coverage_tag == news_select.COVERAGE_NEW

    assert sel["ongoing-repeat"].temporal_kind == news_select.KIND_ONGOING
    assert sel["ongoing-repeat"].coverage_tag == news_select.COVERAGE_REPEAT


def test_evolve_carries_the_new_beat_delta(db):
    _seed_world(db)
    sel = _by_id(news_select.select_for(db, NOW, count=10))

    evolving = sel["evolving"]
    assert evolving.coverage_tag == news_select.COVERAGE_EVOLVE
    assert evolving.new_beat is not None
    assert evolving.new_beat.id == "ev_new"  # the development since last coverage


def test_cold_repeat_is_dropped(db):
    _seed_world(db)
    sel = _by_id(news_select.select_for(db, NOW, count=10))
    assert "stale-repeat" not in sel  # too stale to re-air without a new beat


def test_selection_is_ranked_breaking_first(db):
    _seed_world(db)
    selected = news_select.select_for(db, NOW, count=10)
    # Ranked by score (desc); the breaking-now story leads the bulletin.
    assert selected[0].story.id == "breaking-new"
    scores = [s.score for s in selected]
    assert scores == sorted(scores, reverse=True)


def test_count_bound_and_mix_quotas(db):
    _seed_world(db)
    selected = news_select.select_for(db, NOW, count=2)
    assert len(selected) == 2
    # The per-kind quotas mix the bulletin rather than taking two of one kind:
    # breaking leads, then the trailed preview (not the lower-ranked ongoing pair).
    kinds = {s.temporal_kind for s in selected}
    assert news_select.KIND_BREAKING in kinds
    assert news_select.KIND_TRAILED in kinds


def test_canon_recall_grounds_the_score(db, monkeypatch):
    _seed_world(db)
    hit = embeddings.Retrieved(id="canon-x", text="a bible fact", score=0.9)
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [hit])

    selected = news_select.select_for(db, NOW, count=10)
    # Every candidate is grounded by the recalled canon similarity.
    assert all(s.canon_score == pytest.approx(0.9) for s in selected)


def test_empty_log_returns_nothing(db):
    store.clear_world(db, scope="world")  # isolate from any seeded dev DB (rolled back)
    assert news_select.select_for(db, NOW, count=5) == []

"""Tests for the living-day news desk — R4.2.

R4.2 makes the on-air language match the machinery. The brittle logic here:

* the desk BRIEF for an `evolve` item references what was said last time AND frames
  the delta (an update, not a re-read); a `trailed` item reads as a COUNTDOWN;
* the bulletin SHAPE follows the grid slot — a short program's news pin runs a lean
  bulletin, a flagship/drive desk the full mix, and only the drive desk gets the "day
  so far" wrap;
* SELECTION: a trailed upcoming event recurs across days without going cold (the
  countdown that shouldn't lapse), and proximity raises its rank (closer = more).

Pure brief/shape tests need no DB; the selection tests use a rolled-back Postgres
connection and skip cleanly without one. `embeddings.retrieve` is stubbed so canon
recall never loads a model.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta

import pytest
from src.config import settings
from src.formats import news, news_select
from src.providers import embeddings
from src.world import store
from src.world.context import AssembledContext

# A fixed real `now`; in-world face is +600 (2626-06-24 12:00).
NOW = datetime(2026, 6, 24, 12, 0)
NOW_IW = datetime(2626, 6, 24, 12, 0)  # the in-world face of NOW (coverage timeline)


def _story(story_id: str, *, stage: str = store.ARC_DEVELOPING) -> store.Story:
    return store.Story(
        id=story_id,
        title=f"The {story_id} Affair",
        summary="A happening in the +600y world.",
        arc_stage=stage,
        source=store.EVENT_SOURCE_TICK,
        created_tick=1,
    )


def _beat(beat_id: str, story_id: str, when: datetime) -> store.Event:
    return store.Event(
        id=beat_id,
        title=f"Beat {beat_id}",
        body=f"the {beat_id} development",
        in_world_datetime=when,
        status="today",
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind="development",
    )


def _sel(
    story,
    *,
    coverage_tag,
    temporal_kind,
    lead_beat=None,
    new_beat=None,
    prior_coverage=None,
):
    return news_select.SelectedStory(
        story=story,
        coverage_tag=coverage_tag,
        temporal_kind=temporal_kind,
        lead_beat=lead_beat,
        new_beat=new_beat,
        latest_beat=new_beat if new_beat is not None else lead_beat,
        prior_coverage=prior_coverage,
        canon_score=0.0,
        score=1.0,
    )


# --- Brief language (pure) --------------------------------------------------


def test_evolve_brief_references_last_report_and_frames_the_delta():
    story = _story("orbital")
    delta = _beat("nb", "orbital", datetime(2626, 6, 24, 9, 0))  # this morning
    prior = store.NewsCoverage(
        story_id="orbital",
        covered_at=datetime(2626, 6, 24, 7, 0),  # earlier today
        arc_stage=store.ARC_HAPPENING,
        last_beat_id="ob-old",
        angle="the orbital stand-off",
    )
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_EVOLVE,
        temporal_kind=news_select.KIND_ONGOING,
        lead_beat=delta,
        new_beat=delta,
        prior_coverage=prior,
    )
    brief = news._story_brief(sel, NOW)

    assert "you last reported this this morning" in brief
    assert "the orbital stand-off" in brief  # the prior handle, for consistent naming
    assert "UPDATE" in brief
    assert "the nb development" in brief  # the delta body
    assert "frame it AS an update" in brief  # the explicit delta-framing instruction


def test_trailed_brief_reads_as_a_countdown():
    story = _story("games", stage=store.ARC_UPCOMING)
    lead = _beat("gb", "games", datetime(2626, 6, 27, 9, 0))  # in three days
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_NEW,
        temporal_kind=news_select.KIND_TRAILED,
        lead_beat=lead,
    )
    brief = news._story_brief(sel, NOW)

    assert "COUNTDOWN" in brief
    assert "in three days" in brief  # the multi-day relative phrase
    assert "trail it as approaching" in brief
    assert "still developing" not in brief  # a countdown is not a stale-repeat touch


def test_trailed_repeat_skips_the_still_developing_touch():
    # A trailed item covered before (repeat) is a countdown re-mention, not a
    # "still developing" ongoing touch.
    story = _story("expo", stage=store.ARC_UPCOMING)
    lead = _beat("eb", "expo", datetime(2626, 6, 27, 9, 0))
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_REPEAT,
        temporal_kind=news_select.KIND_TRAILED,
        lead_beat=lead,
    )
    brief = news._story_brief(sel, NOW)
    assert "COUNTDOWN" in brief
    assert "don't re-read it word for word" not in brief


# --- Bulletin shape (pure) --------------------------------------------------


def _flow(*, short: bool):
    from src.flow import OPEN, ShowFlow

    return ShowFlow(position=OPEN, short_show=short)


def test_shape_short_slot_runs_a_lean_bulletin():
    count, day_summary = news._bulletin_shape(NOW, _flow(short=True))
    assert count == settings.news_story_count_short
    assert not day_summary


def test_shape_flagship_runs_the_full_mix():
    count, day_summary = news._bulletin_shape(NOW, _flow(short=False))
    assert count == settings.news_story_count
    assert not day_summary  # midday, not the drive window
    # No flow at all (a direct call) is also the full mix.
    assert news._bulletin_shape(NOW, None)[0] == settings.news_story_count


def test_shape_drive_desk_gets_the_day_so_far_wrap():
    drive = datetime(2026, 6, 24, 18, 0)  # in the day-summary window
    count, day_summary = news._bulletin_shape(drive, _flow(short=False))
    assert count == settings.news_story_count and day_summary
    # A short slot in the same window never gets the wrap.
    assert news._bulletin_shape(drive, _flow(short=True))[1] is False


def test_build_system_weaves_the_day_summary_wrap_only_when_asked():
    ctx = AssembledContext(dynamic="", bible="B", cards_text="C")
    with_wrap = news._build_system(ctx, NOW, "Ada", [], day_summary=True)
    without = news._build_system(ctx, NOW, "Ada", [], day_summary=False)
    assert "the day so far" in with_wrap
    assert "the day so far" not in without


# --- Selection: countdowns don't go cold, proximity raises rank (DB) --------


@pytest.fixture
def db():
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
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [])


def _cand(db, story, now):
    from src.world import clock

    return news_select._build_candidate(
        db, story, now, clock.to_inworld(now), ground=False
    )


def _cover(db, story_id, when, *, beat_id, stage=store.ARC_UPCOMING):
    store.record_coverage(
        db,
        store.NewsCoverage(
            story_id=story_id, covered_at=when, arc_stage=stage, last_beat_id=beat_id
        ),
    )


def test_trailed_upcoming_recurs_across_days_without_going_cold(db):
    from src.world import clock

    store.clear_world(db, scope="world")
    # A games festival five days out, last mentioned 24h ago (yesterday's bulletin).
    store.insert_story(db, _story("festival", stage=store.ARC_UPCOMING))
    store.insert_beats(db, [_beat("fb", "festival", datetime(2626, 6, 29, 9, 0))])
    _cover(db, "festival", NOW_IW - timedelta(hours=24), beat_id="fb")

    # A day-old mention is PAST the ordinary repeat staleness (18h) — an ongoing story
    # would be dropped — but the trailed window (48h) keeps the countdown alive.
    cand = _cand(db, _story("festival", stage=store.ARC_UPCOMING), NOW)
    assert cand.temporal_kind == news_select.KIND_TRAILED
    assert (NOW_IW - cand.prior_coverage.covered_at) > timedelta(
        hours=settings.news_repeat_max_stale_hours
    )
    assert not news_select._is_cold_repeat(cand, clock.to_inworld(NOW))
    assert any(
        s.story.id == "festival" for s in news_select.select_for(db, NOW, ground=False)
    )

    # The desk airs it again today; a day later it is STILL live (and nearer).
    _cover(db, "festival", NOW_IW, beat_id="fb")
    day1 = news_select.select_for(db, NOW + timedelta(days=1), ground=False)
    assert any(s.story.id == "festival" for s in day1)


def test_ordinary_repeat_still_goes_cold(db):
    from src.world import clock

    store.clear_world(db, scope="world")
    # An ongoing (not trailed) story last mentioned 30h ago, no new beat -> cold.
    store.insert_story(db, _story("levee", stage=store.ARC_DEVELOPING))
    store.insert_beats(db, [_beat("lb", "levee", datetime(2626, 6, 20, 9, 0))])
    store.record_coverage(
        db,
        store.NewsCoverage(
            story_id="levee",
            covered_at=datetime(2626, 6, 23, 6, 0),  # 30h before NOW
            arc_stage=store.ARC_DEVELOPING,
            last_beat_id="lb",
        ),
    )
    cand = _cand(db, _story("levee", stage=store.ARC_DEVELOPING), NOW)
    assert cand.temporal_kind == news_select.KIND_ONGOING
    assert news_select._is_cold_repeat(cand, clock.to_inworld(NOW))


def test_proximity_raises_a_trailed_events_rank(db):
    store.clear_world(db, scope="world")
    # Two trailed events, one tomorrow and one six days out; nearer must rank higher.
    store.insert_story(db, _story("near", stage=store.ARC_UPCOMING))
    store.insert_beats(db, [_beat("nb", "near", datetime(2626, 6, 25, 9, 0))])  # +1d
    store.insert_story(db, _story("far", stage=store.ARC_UPCOMING))
    store.insert_beats(db, [_beat("fb", "far", datetime(2626, 6, 30, 9, 0))])  # +6d

    near = _cand(db, _story("near", stage=store.ARC_UPCOMING), NOW)
    far = _cand(db, _story("far", stage=store.ARC_UPCOMING), NOW)
    assert near.temporal_kind == far.temporal_kind == news_select.KIND_TRAILED
    assert near.score > far.score

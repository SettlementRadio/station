"""Tests for same-day arcs — the living day (PHASE_R_TASKS.md R4.0).

The brittle logic here is a content-safety property, not just correctness: a
`planned` beat is the tick's PLAN for later today, and airing one before its hour
would have the news desk report something that has not happened yet. So the tests
cover both halves of the gate —

* the WRITE side (`world_tick`): the model's `planned` flag survives into the stored
  beat, but only while the beat is genuinely ahead of the clock;
* the READ side (`events.airable` + `news_select`): a planned beat is invisible until
  its hour passes, a story whose every beat is still planned is not selected at all,
  and as the day runs the same story re-tags `breaking -> evolve -> evolve`.

The DB test drives a frozen clock across three simulated hours; it rolls back at
teardown and skips cleanly without Postgres. No LLM is called.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime

import pytest
from src.config import settings
from src.formats import news_select
from src.providers import embeddings
from src.world import clock, events, store
from src.world import world_tick as wt

# The nightly tick's real `now`; its in-world face is +600y (2626-06-24 06:00).
TICK_NOW = datetime(2026, 6, 24, 6, 0)


def _ctx() -> wt._TickContext:
    return wt._TickContext(
        bible="", active_summary="", now=TICK_NOW, iw_now=clock.to_inworld(TICK_NOW)
    )


# --- Write side: the tick's planned flag ------------------------------------


def test_coerce_beat_reads_planned_and_defaults_false():
    planned = wt._coerce_beat(
        {"title": "Located", "body": "Tugs find the hull.", "hour": 13, "planned": True}
    )
    assert planned is not None and planned.planned
    # A pre-R4 beat (no key at all) is an ordinary beat, not a plan.
    plain = wt._coerce_beat({"title": "Vanished", "body": "Last ping at dusk."})
    assert plain is not None and not plain.planned


def test_materialise_keeps_planned_only_for_beats_ahead_of_the_clock():
    p = wt.ProposedStory(
        title="Drifting Liner",
        summary="A cruise liner goes missing.",
        scale="small",
        domain="geography",
        arc_stage=store.ARC_HAPPENING,
        beats=[
            # Already happened by tick time (06:00 in-world) — the record.
            wt.ProposedBeat("Vanished", "Last ping at dusk.", "rumour", -1, 22),
            # Later today — the plan.
            wt.ProposedBeat(
                "Located", "Tugs find the hull.", "development", 0, 13, planned=True
            ),
            wt.ProposedBeat(
                "Reached", "The crew is aboard.", "resolution", 0, 19, planned=True
            ),
        ],
    )
    _story, beats = wt._materialise(p, tick_no=1, ctx=_ctx(), index=0)

    assert [b.planned for b in beats] == [False, True, True]
    assert [b.in_world_datetime.hour for b in beats] == [22, 13, 19]


def test_materialise_drops_planned_on_a_beat_that_has_already_landed():
    """A beat the model marked planned but dated behind now has no hour left to wait
    for — storing it planned would suppress it from air forever."""
    p = wt.ProposedStory(
        title="Late Plan",
        summary="A plan dated in the past.",
        scale="small",
        domain="geography",
        arc_stage=store.ARC_HAPPENING,
        beats=[wt.ProposedBeat("Done", "It happened.", "development", -2, 9, [], True)],
    )
    _story, beats = wt._materialise(p, tick_no=1, ctx=_ctx(), index=0)
    assert not beats[0].planned


def test_proposal_prompt_asks_for_day_arcs_and_can_be_dialled_off(monkeypatch):
    on = wt._dayarc_instruction(_ctx())
    assert "SAME-DAY ARCS" in on
    assert str(settings.world_tick_dayarc_beats_max) in on

    monkeypatch.setattr(settings, "world_tick_dayarc_stories_max", 0)
    assert wt._dayarc_instruction(_ctx()) == ""


def test_parse_proposals_carries_planned_through():
    raw = json.dumps(
        [
            {
                "title": "Drifting Liner",
                "summary": "A liner goes missing.",
                "scale": "small",
                "domain": "geography",
                "arc_stage": "happening",
                "beats": [
                    {"title": "Vanished", "body": "Last ping.", "hour": 3},
                    {"title": "Located", "body": "Found.", "hour": 13, "planned": True},
                ],
            }
        ]
    )
    (story,) = wt._parse_proposals(raw)
    assert [b.planned for b in story.beats] == [False, True]


# --- Read side: the airable gate (pure) -------------------------------------


def _beat(beat_id: str, story_id: str, when: datetime, *, planned: bool) -> store.Event:
    return store.Event(
        id=beat_id,
        title=f"Beat {beat_id}",
        body="A development.",
        in_world_datetime=when,
        status="today",
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind="development",
        planned=planned,
    )


def test_airable_holds_a_planned_beat_until_its_hour_passes():
    later = _beat("b2", "s", datetime(2626, 6, 24, 13, 0), planned=True)
    trailed = _beat("b3", "s", datetime(2626, 6, 27, 9, 0), planned=False)

    # 07:30 in-world: the plan is still ahead; a genuinely announced future event
    # (planned=False) stays airable — that is what `trailed` items are.
    assert not events.has_landed(later, datetime(2026, 6, 24, 7, 30))
    assert events.has_landed(trailed, datetime(2026, 6, 24, 7, 30))
    # 13:30: its hour has passed, so it becomes the record.
    assert events.has_landed(later, datetime(2026, 6, 24, 13, 30))
    assert events.airable([later, trailed], datetime(2026, 6, 24, 13, 30)) == [
        later,
        trailed,
    ]


# --- Read side: the news desk across a simulated day (DB) -------------------


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
    """Canon recall returns nothing (no model load; the structured-ranking fallback)."""
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [])


def _seed_day_arc(db) -> None:
    """One story unfolding across the day: 07:00 -> 13:00 -> 19:00, all planned."""
    store.clear_world(db, scope="world")
    store.insert_story(
        db,
        store.Story(
            id="liner",
            title="Drifting Liner",
            summary="A cruise liner goes missing on the dayside lane.",
            arc_stage=store.ARC_HAPPENING,
            source=store.EVENT_SOURCE_TICK,
            created_tick=1,
        ),
    )
    store.insert_beats(
        db,
        [
            _beat("liner-b0", "liner", datetime(2626, 6, 24, 7, 0), planned=True),
            _beat("liner-b1", "liner", datetime(2626, 6, 24, 13, 0), planned=True),
            _beat("liner-b2", "liner", datetime(2626, 6, 24, 19, 0), planned=True),
        ],
    )


def _select_at(db, hour: int, minute: int = 30) -> list[news_select.SelectedStory]:
    return news_select.select_for(db, datetime(2026, 6, 24, hour, minute), ground=False)


def _record(db, cand: news_select.SelectedStory, hour: int) -> None:
    """Record coverage of `cand`, as the D4.2 producer does after a render."""
    store.record_coverage(
        db,
        store.NewsCoverage(
            story_id=cand.story.id,
            covered_at=datetime(2626, 6, 24, hour, 30),
            arc_stage=cand.story.arc_stage,
            last_beat_id=cand.latest_beat.id if cand.latest_beat else None,
        ),
    )


def test_planned_beats_never_air_early_and_the_story_evolves_across_the_day(db):
    _seed_day_arc(db)

    # 06:30 — the tick has written the whole arc, but nothing has landed. The story
    # has not started, so the desk must not pick it up at all.
    assert _select_at(db, 6) == []

    # 07:30 — the first beat has landed: breaking, never covered.
    (first,) = _select_at(db, 7)
    assert first.temporal_kind == news_select.KIND_BREAKING
    assert first.coverage_tag == news_select.COVERAGE_NEW
    assert first.latest_beat is not None and first.latest_beat.id == "liner-b0"
    _record(db, first, 7)

    # 13:30 — the 13:00 beat has landed: an UPDATE, and the 19:00 beat is still hidden.
    (second,) = _select_at(db, 13)
    assert second.coverage_tag == news_select.COVERAGE_EVOLVE
    assert second.new_beat is not None and second.new_beat.id == "liner-b1"
    assert second.latest_beat is not None and second.latest_beat.id == "liner-b1"
    _record(db, second, 13)

    # 19:30 — the resolution lands: a second update, off the newest beat.
    (third,) = _select_at(db, 19)
    assert third.coverage_tag == news_select.COVERAGE_EVOLVE
    assert third.new_beat is not None and third.new_beat.id == "liner-b2"
    _record(db, third, 19)


def test_an_ordinary_future_beat_is_still_trailed(db):
    """The planned gate must not swallow genuinely announced future events."""
    _seed_day_arc(db)
    store.insert_beats(
        db,
        [_beat("liner-b3", "liner", datetime(2626, 6, 26, 9, 0), planned=False)],
    )
    (cand,) = _select_at(db, 6)
    assert cand.temporal_kind == news_select.KIND_TRAILED
    assert cand.lead_beat is not None and cand.lead_beat.id == "liner-b3"

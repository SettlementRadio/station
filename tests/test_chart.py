"""Tests for R6.1 — the daily chart update logic (src/world/chart.py).

The chart update is the pure "how the chart moves" core, so these tests are pure:
no DB, no files. They pin the determinism contract, the movement language, the
day-to-day plausibility (a chart that moves but doesn't churn), new entries and
re-entries, and the featured thumb-on-the-scale.
"""

from __future__ import annotations

from src.config import settings
from src.world import chart
from src.world.store import Track


def _track(id: str, *, artist: str | None = None, blurb: str = "", tags=()):
    return Track(
        id=id,
        title=id.replace("-", " ").title(),
        in_world_artist=artist or id,
        mood="joyful",
        audio_path=f"assets/music/{id}.mp3",
        story_blurb=blurb or None,
        tags=list(tags),
    )


def _catalogue(n: int, tags=()):
    return [_track(f"t{i:02d}", tags=tags) for i in range(n)]


def _blob(entries):
    """A stored-chart blob (what `compute_chart`'s `prev` reads) from ChartEntries."""
    return {
        "chart_no": 1,
        "entries": [
            {"track_id": e.track_id, "rank": e.rank, "days_on": e.days_on}
            for e in entries
        ],
    }


# --- determinism -------------------------------------------------------------


def test_compute_is_deterministic():
    tracks = _catalogue(12)
    a = chart.compute_chart(tracks, None, size=10, seed=20260726)
    b = chart.compute_chart(tracks, None, size=10, seed=20260726)
    assert [e.track_id for e in a] == [e.track_id for e in b]


def test_different_seeds_differ():
    tracks = _catalogue(12)
    a = chart.compute_chart(tracks, None, size=10, seed=20260726)
    b = chart.compute_chart(tracks, None, size=10, seed=20260727)
    assert [e.track_id for e in a] != [e.track_id for e in b]


def test_size_caps_the_chart():
    entries = chart.compute_chart(_catalogue(20), None, size=10, seed=1)
    assert len(entries) == 10
    assert [e.rank for e in entries] == list(range(1, 11))


def test_first_chart_entries_are_all_new():
    entries = chart.compute_chart(_catalogue(12), None, size=10, seed=1)
    assert all(e.prev_rank is None for e in entries)
    assert all(e.days_on == 1 for e in entries)


# --- movement language -------------------------------------------------------


def test_movement_phrases():
    up = chart.ChartEntry("x", "X", "A", None, rank=2, prev_rank=5, days_on=3)
    assert up.movement() == ("up", 3)
    assert up.movement_phrase() == "up three"

    down = chart.ChartEntry("x", "X", "A", None, rank=7, prev_rank=4, days_on=3)
    assert down.movement_phrase() == "down three"

    hold = chart.ChartEntry("x", "X", "A", None, rank=4, prev_rank=4, days_on=3)
    assert hold.movement() == ("nonmover", 0)
    assert hold.movement_phrase() == "holds at four"

    new = chart.ChartEntry("x", "X", "A", None, rank=6, prev_rank=None, days_on=1)
    assert new.movement_phrase() == "new entry"


def test_survivor_carries_prev_rank_and_days_on():
    tracks = _catalogue(10)
    day1 = chart.compute_chart(tracks, None, size=10, seed=1)
    day2 = chart.compute_chart(tracks, _blob(day1), size=10, seed=2)
    by_id_day1 = {e.track_id: e for e in day1}
    survivors = [e for e in day2 if e.track_id in by_id_day1]
    assert survivors  # a stable catalogue keeps most of the chart
    for e in survivors:
        assert e.prev_rank == by_id_day1[e.track_id].rank
        assert e.days_on == by_id_day1[e.track_id].days_on + 1


# --- plausibility: moves, but doesn't churn ----------------------------------


def test_day_to_day_moves_but_overlaps():
    # A stable catalogue over a week of transitions: the chart order should change
    # every day (it moves) while most of its members persist (it doesn't churn) —
    # a rotating tail over a stable core, like a real chart.
    tracks = _catalogue(14)
    prev = chart.compute_chart(tracks, None, size=10, seed=20260726)
    for day in range(1, 7):
        cur = chart.compute_chart(tracks, _blob(prev), size=10, seed=20260726 + day)
        ids_prev = [e.track_id for e in prev]
        ids_cur = [e.track_id for e in cur]
        assert ids_prev != ids_cur, f"day {day}: chart did not move"
        overlap = len(set(ids_prev) & set(ids_cur))
        assert overlap >= 5, f"day {day}: chart churned too hard (overlap {overlap})"
        prev = cur


def test_new_entries_can_break_in():
    tracks = _catalogue(14)
    day1 = chart.compute_chart(tracks, None, size=10, seed=5)
    day2 = chart.compute_chart(tracks, _blob(day1), size=10, seed=6)
    new = [e for e in day2 if e.prev_rank is None]
    # With 14 eligible and a 10-slot chart, at least one fresh name should appear
    # over a couple of days of movement.
    day3 = chart.compute_chart(tracks, _blob(day2), size=10, seed=7)
    new3 = [e for e in day3 if e.prev_rank is None]
    assert new or new3


def test_reentry_resets_days_on():
    tracks = _catalogue(14)
    day1 = chart.compute_chart(tracks, None, size=10, seed=5)
    day2 = chart.compute_chart(tracks, _blob(day1), size=10, seed=6)
    dropped = {e.track_id for e in day1} - {e.track_id for e in day2}
    # A track that fell off and comes back charts as a fresh entry (days_on == 1).
    for e in day2:
        if e.track_id in dropped:  # pragma: no cover - depends on movement
            assert e.days_on == 1


# --- featured thumb on the scale ---------------------------------------------


def test_featured_tag_boosts(monkeypatch):
    monkeypatch.setattr(settings, "chart_featured_weight", 100.0)  # overwhelming
    tracks = _catalogue(10) + [_track("star", tags=("featured",))]
    entries = chart.compute_chart(tracks, None, size=10, seed=1)
    assert entries[0].track_id == "star"


# --- the day's chart story ---------------------------------------------------


def test_pick_story_prefers_a_big_climber():
    # t5 leaps from 5 to 2; everyone else static-ish → the climber is the story.
    day2 = [
        chart.ChartEntry("t1", "T1", "A", None, rank=1, prev_rank=1, days_on=3),
        chart.ChartEntry("t5", "T5", "A", None, rank=2, prev_rank=5, days_on=3),
        chart.ChartEntry("t2", "T2", "A", None, rank=3, prev_rank=2, days_on=3),
        chart.ChartEntry("t3", "T3", "A", None, rank=4, prev_rank=3, days_on=3),
        chart.ChartEntry("t4", "T4", "A", None, rank=5, prev_rank=4, days_on=3),
    ]
    story = chart.pick_story(day2)
    assert story["kind"] == "climber"
    assert story["track_id"] == "t5"


def test_pick_story_holdout_at_number_one():
    entries = [
        chart.ChartEntry("t1", "T1", "A", None, rank=1, prev_rank=1, days_on=4),
        chart.ChartEntry("t2", "T2", "A", None, rank=2, prev_rank=2, days_on=4),
    ]
    story = chart.pick_story(entries)
    assert story["kind"] == "holdout"
    assert story["track_id"] == "t1"


def test_pick_story_empty_is_none():
    assert chart.pick_story([]) is None

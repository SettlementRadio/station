"""Tests for the figures + quotes schema (src/world/store.py) — D10.0.

The store-integration layer (skips cleanly without Postgres/pgvector, like
test_story_log.py): a figure + an attributable, dated quote round-trip and link to a
story/beat; figures link to a story THROUGH their quotes; the date-window read frames
quotes by time; and the LOAD-BEARING seed-vs-generated `source` split — a `seed-canon`
refresh clears BIBLE figures/quotes but leaves TICK-generated ones standing, while a
full reset clears both. Every DB test rolls back at teardown, so it NEVER mutates a
developer's seeded dev DB (the destructive `reset-world`-scope path included).
"""

from __future__ import annotations

import contextlib
from datetime import datetime

import pytest
from src.world import store


@pytest.fixture
def db():
    """A store connection with the schema, that ALWAYS rolls back at teardown.

    Skips cleanly if Postgres or pgvector is absent (the suite stays green without it).
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


def _story(story_id: str, *, source: str = store.EVENT_SOURCE_TICK) -> store.Story:
    return store.Story(
        id=story_id,
        title=f"Story {story_id}",
        summary="A happening in the +600y world.",
        arc_stage=store.ARC_HAPPENING,
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


def _figure(
    figure_id: str,
    *,
    source: str = store.FIGURE_SOURCE_TICK,
    voice_id: str | None = None,
) -> store.Figure:
    return store.Figure(
        id=figure_id,
        name=f"Figure {figure_id}",
        role="relay-keeper",
        card_text="A steady hand on the orbital relay.",
        voice_id=voice_id,
        tags=["relay"],
        source=source,
    )


def _quote(
    quote_id: str,
    story_id: str,
    figure_id: str,
    *,
    beat_id: str | None = None,
    when: datetime = datetime(2626, 6, 24, 20, 0),
    source: str = store.FIGURE_SOURCE_TICK,
) -> store.Quote:
    return store.Quote(
        id=quote_id,
        story_id=story_id,
        figure_id=figure_id,
        text="The relay held. We are not going dark tonight.",
        in_world_datetime=when,
        beat_id=beat_id,
        stance="reassuring",
        tags=["relay"],
        source=source,
    )


def test_figure_and_quote_round_trip_with_dates(db):
    store.insert_story(db, _story("d100-s1"))
    store.insert_beats(db, [_beat("d100-b1", "d100-s1")])
    store.insert_figures(db, [_figure("d100-f1", voice_id="vx-keeper")])
    store.insert_quotes(
        db, [_quote("d100-q1", "d100-s1", "d100-f1", beat_id="d100-b1")]
    )

    fig = store.get_figure(db, "d100-f1")
    assert fig is not None
    assert fig.role == "relay-keeper"
    assert fig.voice_id == "vx-keeper"  # the optional voice link round-trips
    assert fig.source == store.FIGURE_SOURCE_TICK

    quotes = store.quotes_for_story(db, "d100-s1")
    assert [q.id for q in quotes] == ["d100-q1"]
    q = quotes[0]
    assert q.figure_id == "d100-f1"
    assert q.beat_id == "d100-b1"  # pinned to a specific beat
    assert q.stance == "reassuring"
    assert q.in_world_datetime == datetime(2626, 6, 24, 20, 0)  # dated for the clock


def test_figures_for_story_links_through_quotes_and_dedupes(db):
    store.insert_story(db, _story("d100-s2"))
    store.insert_figures(db, [_figure("d100-fa"), _figure("d100-fb")])
    # fa speaks twice, fb once; fc never speaks in this story.
    store.insert_figures(db, [_figure("d100-fc")])
    store.insert_quotes(
        db,
        [
            _quote("d100-qa1", "d100-s2", "d100-fa"),
            _quote("d100-qa2", "d100-s2", "d100-fa"),
            _quote("d100-qb1", "d100-s2", "d100-fb"),
        ],
    )

    ids = [f.id for f in store.figures_for_story(db, "d100-s2")]
    assert ids == ["d100-fa", "d100-fb"]  # deduped, ordered by id; fc absent (silent)


def test_quotes_near_windows_by_in_world_time(db):
    store.insert_story(db, _story("d100-s3"))
    store.insert_figures(db, [_figure("d100-fn")])
    store.insert_quotes(
        db,
        [
            _quote("d100-old", "d100-s3", "d100-fn", when=datetime(2626, 6, 1, 9, 0)),
            _quote("d100-now", "d100-s3", "d100-fn", when=datetime(2626, 6, 24, 9, 0)),
        ],
    )

    near = store.quotes_near(
        db, datetime(2626, 6, 20, 0, 0), datetime(2626, 6, 25, 0, 0)
    )
    near_ids = {q.id for q in near}
    assert "d100-now" in near_ids
    assert "d100-old" not in near_ids  # outside the window


def test_attributed_quotes_for_story_pairs_and_orders_newest_first(db):
    store.insert_story(db, _story("d102-s1"))
    store.insert_figures(db, [_figure("d102-f1"), _figure("d102-f2")])
    store.insert_quotes(
        db,
        [
            _quote("d102-old", "d102-s1", "d102-f1", when=datetime(2626, 6, 1, 9, 0)),
            _quote("d102-new", "d102-s1", "d102-f2", when=datetime(2626, 6, 24, 9, 0)),
        ],
    )

    pairs = store.attributed_quotes_for_story(db, "d102-s1")
    assert [q.id for q, _f in pairs] == ["d102-new", "d102-old"]  # newest first
    # Each quote is paired with the RIGHT figure (the JOIN), and figures round-trip.
    by_quote = {q.id: f.id for q, f in pairs}
    assert by_quote == {"d102-new": "d102-f2", "d102-old": "d102-f1"}
    assert store.attributed_quotes_for_story(db, "d102-s1", limit=1)[0][0].id == (
        "d102-new"
    )


def test_attributed_quotes_by_ids_preserves_rank_order(db):
    store.insert_story(db, _story("d102-s2"))
    store.insert_figures(db, [_figure("d102-fa")])
    store.insert_quotes(
        db,
        [
            _quote("d102-qa", "d102-s2", "d102-fa"),
            _quote("d102-qb", "d102-s2", "d102-fa"),
        ],
    )
    # Pass ids in a deliberate (non-chronological) rank order — it must be preserved.
    pairs = store.attributed_quotes_by_ids(db, ["d102-qb", "d102-qa", "missing"])
    assert [q.id for q, _f in pairs] == ["d102-qb", "d102-qa"]  # unknown id skipped


def test_seed_canon_keeps_tick_figures_quotes_full_reset_clears_them(db):
    # A bible-authored figure/quote vs a tick-generated one: a canon refresh replaces
    # only the bible rows, leaving the living world standing; a full reset clears all.
    bible, tick = store.FIGURE_SOURCE_BIBLE, store.FIGURE_SOURCE_TICK
    store.insert_story(db, _story("d100-st", source=store.EVENT_SOURCE_TICK))
    store.insert_figures(
        db,
        [
            _figure("d100-fbible", source=bible),
            _figure("d100-ftick", source=tick),
        ],
    )
    store.insert_quotes(
        db,
        [
            _quote("d100-qbible", "d100-st", "d100-fbible", source=bible),
            _quote("d100-qtick", "d100-st", "d100-ftick", source=tick),
        ],
    )

    store.clear_world(db, scope="canon")  # the SAFE refresh
    assert store.get_figure(db, "d100-fbible") is None  # bible figure replaced
    assert store.get_figure(db, "d100-ftick") is not None  # living world SURVIVES
    surviving = {q.id for q in store.quotes_for_story(db, "d100-st")}
    assert surviving == {"d100-qtick"}  # bible quote gone, tick quote stands

    store.clear_world(db, scope="world")  # the DESTRUCTIVE full wipe
    assert store.get_figure(db, "d100-ftick") is None  # now cleared
    assert store.counts(db)["figures"] == 0
    assert store.counts(db)["quotes"] == 0

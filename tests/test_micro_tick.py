"""Tests for the intra-day micro-tick (src/world/world_tick.py) — R4.1.

The brittle logic a silent bug would corrupt:

* **the quiet contract** — a run that shouldn't act (disabled, dice, no live story,
  the model declining, the gate flagging) writes NOTHING, and two quiet runs in a row
  leave the world byte-identical (the R4.1 done-when);
* **the acting path** — one small LANDED beat is added to the freshest live story, the
  micro counter advances only then (unique `m{n}` beat ids), the arc stage is left
  untouched, and a bulletin generated afterwards reports the beat as an `evolve` update;
* **candidate selection** — only stories with a recent, already-landed beat qualify;
  planned-only and stale threads are excluded.

The LLM + safety seams are mocked (no tokens); DB writes roll back at teardown and the
suite skips cleanly without Postgres.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime, timedelta

import pytest
from src.config import settings
from src.formats import news_select
from src.providers import embeddings, llm
from src.safety import SafetyResult
from src.world import store
from src.world import world_tick as wt

# A fixed real `now`; the in-world face is +600 (2626-06-24 15:00).
NOW = datetime(2026, 6, 24, 15, 0)
IW_NOW = datetime(2626, 6, 24, 15, 0)


def _beat_json(hour: int = 15) -> str:
    return json.dumps(
        {
            "beat": {
                "title": "Tugs reach the hull",
                "body": "A salvage crew makes contact with the drifting liner.",
                "beat_kind": "development",
                "day_offset": 0,
                "hour": hour,
                "planned": False,
                "quotes": [],
            },
            "new_figures": [],
        }
    )


def _mock_generate(beat_raw: str = "", *, continuity: str = "OK"):
    """An `llm.generate` stand-in: the beat JSON for the generation call, a continuity
    verdict for the gate call (told apart by the advance-text prompt prefix)."""

    def _gen(prompt: str, **_kw) -> str:
        if prompt.startswith("Advancing:"):  # the continuity gate's prompt
            return continuity
        return beat_raw or _beat_json()

    return _gen


@pytest.fixture
def micro_db(monkeypatch):
    """One rolled-back connection shared across the micro-tick's read+write txns.

    Clears tick/micro state + the story log in THIS transaction so every test starts
    from an empty, deterministic world (mirrors the world_tick suite's isolation).
    """
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001 - no DB -> skip
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001 - pgvector unavailable
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"pgvector unavailable: {exc}")

    conn.execute("DELETE FROM quotes")
    conn.execute("DELETE FROM figures")
    conn.execute("DELETE FROM events WHERE source = %s", (store.EVENT_SOURCE_TICK,))
    conn.execute("DELETE FROM news_coverage")
    conn.execute("DELETE FROM stories")
    conn.execute(
        "DELETE FROM state WHERE key IN "
        "('world_tick_count', 'world_tick_last_at', "
        "'world_micro_tick_count', 'world_micro_tick_last_at')"
    )

    @contextlib.contextmanager
    def fake_connect():
        yield conn  # shared, uncommitted — every txn in a run lands here

    monkeypatch.setattr(store, "connect", fake_connect)
    monkeypatch.setattr(
        embeddings,
        "embed",
        lambda texts: [[0.0] * settings.embeddings_dim for _ in texts],
    )
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(
        wt, "safety_check", lambda text: SafetyResult(True, "OK", "disabled")
    )
    # Default: the dice always say "act", so a test's outcome is decided by what it
    # seeds + mocks, not chance. Quiet-path tests override this.
    monkeypatch.setattr(wt, "_random_unit", lambda: 0.0)
    try:
        yield conn
    finally:
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _seed_live_story(
    conn, *, story_id: str = "liner", beat_hours_ago: float = 3.0
) -> store.Event:
    """A running story whose newest LANDED beat is `beat_hours_ago` before now."""
    store.insert_story(
        conn,
        store.Story(
            id=story_id,
            title="Drifting Liner",
            summary="A cruise liner goes missing on the dayside lane.",
            arc_stage=store.ARC_HAPPENING,
            source=store.EVENT_SOURCE_TICK,
            created_tick=1,
            last_advanced_tick=1,
        ),
    )
    beat = store.Event(
        id=f"{story_id}-b0",
        title="The liner goes silent",
        body="Its last ping came at midday.",
        in_world_datetime=IW_NOW - timedelta(hours=beat_hours_ago),
        status="past",
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind="inciting",
    )
    store.insert_beats(conn, [beat])
    return beat


# --- The quiet contract -----------------------------------------------------


def test_disabled_writes_nothing(micro_db, monkeypatch):
    _seed_live_story(micro_db)
    monkeypatch.setattr(settings, "micro_tick_enabled", False)
    monkeypatch.setattr(llm, "generate", _mock_generate())

    r = wt.run_micro_tick(NOW)

    assert not r.acted and r.reason == "disabled"
    assert len(store.story_beats(micro_db, "liner")) == 1  # only the seed beat


def test_dice_quiet_run_changes_nothing_and_repeats(micro_db, monkeypatch):
    _seed_live_story(micro_db)
    monkeypatch.setattr(wt, "_random_unit", lambda: 0.99)  # >= prob -> quiet
    monkeypatch.setattr(llm, "generate", _mock_generate())

    before = len(store.story_beats(micro_db, "liner"))
    r1 = wt.run_micro_tick(NOW)
    r2 = wt.run_micro_tick(NOW)

    assert not r1.acted and not r2.acted
    assert store.get_state(micro_db, "world_micro_tick_count") is None  # never bumped
    assert len(store.story_beats(micro_db, "liner")) == before  # byte-identical


def test_no_live_story_is_quiet(micro_db, monkeypatch):
    # A story whose only beat is a PLANNED future one is not "live today".
    store.insert_story(
        micro_db,
        store.Story(
            id="future",
            title="A Festival Next Week",
            summary="Announced, not yet happening.",
            arc_stage=store.ARC_UPCOMING,
            source=store.EVENT_SOURCE_TICK,
            created_tick=1,
        ),
    )
    store.insert_beats(
        micro_db,
        [
            store.Event(
                id="future-b0",
                title="Doors open",
                body="Next week.",
                in_world_datetime=IW_NOW + timedelta(days=6),
                status="upcoming",
                source=store.EVENT_SOURCE_TICK,
                story_id="future",
                beat_kind="announcement",
                planned=True,
            )
        ],
    )
    monkeypatch.setattr(llm, "generate", _mock_generate())

    r = wt.run_micro_tick(NOW)
    assert not r.acted and "no live story" in r.reason


def test_model_declining_is_quiet(micro_db, monkeypatch):
    _seed_live_story(micro_db)
    monkeypatch.setattr(llm, "generate", _mock_generate('{"beat": null}'))

    r = wt.run_micro_tick(NOW)
    assert not r.acted and "added nothing" in r.reason
    assert len(store.story_beats(micro_db, "liner")) == 1


def test_gate_flag_drops_the_beat(micro_db, monkeypatch):
    _seed_live_story(micro_db)
    monkeypatch.setattr(
        llm, "generate", _mock_generate(continuity="ISSUES: contradicts the bible")
    )

    r = wt.run_micro_tick(NOW)
    assert not r.acted and r.reason.startswith("gate:")
    assert len(store.story_beats(micro_db, "liner")) == 1  # nothing written


# --- The acting path --------------------------------------------------------


def test_acting_adds_one_landed_beat_and_bumps_counter(micro_db, monkeypatch):
    seed = _seed_live_story(micro_db)
    monkeypatch.setattr(llm, "generate", _mock_generate())

    r1 = wt.run_micro_tick(NOW)
    assert r1.acted and r1.story_id == "liner"
    assert r1.micro_tick == 1 and r1.beat_id == "liner-m1"

    beats = store.story_beats(micro_db, "liner")
    assert len(beats) == 2
    new = next(b for b in beats if b.id == "liner-m1")
    assert not new.planned  # a micro-beat lands immediately (reportable now)
    assert new.in_world_datetime <= IW_NOW

    # The arc stage is the nightly tick's to move — the micro-tick must not touch it.
    story = next(s for s in store.active_stories(micro_db) if s.id == "liner")
    assert story.arc_stage == store.ARC_HAPPENING
    assert story.last_advanced_tick == 1  # unchanged (no advance_story call)
    assert seed.id in {b.id for b in beats}  # the original beat is still there

    # A second acting run gets a fresh, unique id and bumps the counter again.
    r2 = wt.run_micro_tick(NOW)
    assert r2.micro_tick == 2 and r2.beat_id == "liner-m2"
    assert len(store.story_beats(micro_db, "liner")) == 3


def test_bulletin_reports_the_micro_beat_as_an_update(micro_db, monkeypatch):
    seed = _seed_live_story(micro_db)
    # The desk has already covered the story at its seed beat.
    store.record_coverage(
        micro_db,
        store.NewsCoverage(
            story_id="liner",
            covered_at=IW_NOW - timedelta(hours=2),
            arc_stage=store.ARC_HAPPENING,
            last_beat_id=seed.id,
        ),
    )
    monkeypatch.setattr(llm, "generate", _mock_generate())

    wt.run_micro_tick(NOW)

    (sel,) = news_select.select_for(micro_db, NOW, ground=False)
    assert sel.coverage_tag == news_select.COVERAGE_EVOLVE
    assert sel.new_beat is not None and sel.new_beat.id == "liner-m1"


# --- Candidate selection ----------------------------------------------------


def test_live_stories_excludes_planned_only_and_stale(micro_db, monkeypatch):
    fresh = _seed_live_story(micro_db, story_id="fresh", beat_hours_ago=2.0)
    # 1000h ago is well outside the 48h live window.
    _seed_live_story(micro_db, story_id="stale", beat_hours_ago=1000.0)
    monkeypatch.setattr(settings, "micro_tick_live_window_hours", 48.0)

    active = store.active_stories(micro_db)
    live = wt._micro_live_stories(micro_db, active, IW_NOW)

    ids = [s.id for s, _beats, _newest in live]
    assert ids == ["fresh"]  # stale dropped; freshest-first ordering
    assert live[0][2].id == fresh.id


def _entry(story_id: str, *, fresh_rank: int, micro: int):
    """A `_micro_live_stories`-shaped tuple: (story, beats, newest). `fresh_rank` sets
    the newest-beat time (lower = fresher); `micro` seeds that many micro-beats."""
    story = store.Story(id=story_id, title=story_id, summary="", arc_stage="happening")
    newest = store.Event(
        id=f"{story_id}-b0",
        title="beat",
        body="",
        in_world_datetime=IW_NOW - timedelta(hours=fresh_rank),
        status="past",
        story_id=story_id,
    )
    beats = [newest] + [
        store.Event(
            id=f"{story_id}-m{n}",
            title="m",
            body="",
            in_world_datetime=IW_NOW,
            status="past",
            story_id=story_id,
        )
        for n in range(1, micro + 1)
    ]
    return (story, beats, newest)


def test_pick_rotates_to_the_least_touched_thread():
    # Two live stories, both untouched: the freshest wins.
    a = _entry("a", fresh_rank=1, micro=0)  # fresher
    b = _entry("b", fresh_rank=5, micro=0)
    assert wt._micro_pick([a, b])[0].id == "a"

    # Once `a` has a micro-beat and `b` has none, `b` is picked even though `a` is
    # fresher — attention spreads instead of one thread running away.
    a2 = _entry("a", fresh_rank=1, micro=1)
    assert wt._micro_pick([a2, b])[0].id == "b"

    assert wt._micro_pick([]) is None

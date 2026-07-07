"""Tests for D12.0 — the talk-continuity substrate (src/flow.py + scheduler wiring).

Two layers: the pure position/hand-off logic (unit), and that `top_up` actually
computes a show position per content slot and persists the last talk hand-off in
`clock_state` (integration, generation monkeypatched — no Claude/TTS). D12.0 changes
no OUTPUT; these assert only that the substrate is computed, carried, and persisted.
"""

from __future__ import annotations

import json
from datetime import datetime

from src import flow, scheduler
from src.flow import CLOSE, CONTINUE, OPEN, Handoff, ShowFlow, handoff_from_segment
from src.segment import Segment
from src.world import programming

# --- The pure position logic ------------------------------------------------


def test_show_position_open_when_first_of_program():
    assert flow.show_position(is_first=True, is_last=False) == OPEN


def test_show_position_close_when_last_but_not_first():
    assert flow.show_position(is_first=False, is_last=True) == CLOSE


def test_show_position_open_wins_for_a_lone_slot():
    # A single-content-slot program is both first and last — it still OPENs.
    assert flow.show_position(is_first=True, is_last=True) == OPEN


def test_show_position_continue_in_the_middle():
    assert flow.show_position(is_first=False, is_last=False) == CONTINUE


# --- The hand-off capture ---------------------------------------------------


def _talk_segment(script: str, beat: str = "the water reclaim") -> Segment:
    return Segment(
        id="talk-001",
        format="talk",
        length_target_sec=300,
        air_time="2026-06-22T14:00:00",
        script=script,
        meta={"beat": beat},
    )


def test_handoff_captures_tail_topic_and_open_thread():
    seg = _talk_segment(
        "Vell: so the reclaim crews finally hit the aquifer.\n"
        "Wren: right, and that's the part nobody's talking about yet."
    )
    ho = handoff_from_segment(seg, "night_show")
    assert ho is not None
    # tail = the last two spoken lines, verbatim.
    assert "nobody's talking about yet" in ho.tail
    assert "reclaim crews" in ho.tail
    assert ho.topic == "the water reclaim"
    assert ho.open_thread is True  # not a sign-off -> more to say
    assert ho.program == "night_show"
    assert ho.air_time == "2026-06-22T14:00:00"


def test_handoff_open_thread_false_on_a_signoff_tail():
    seg = _talk_segment(
        "Wren: that's all from us tonight.\nVell: goodnight, settlement."
    )
    ho = handoff_from_segment(seg, "night_show")
    assert ho is not None
    assert ho.open_thread is False


def test_handoff_none_for_an_evergreen_fallback():
    # A gate-failed talk slot returns an evergreen (format != "talk") -> no thread.
    ever = Segment(
        id="talk-002",
        format="evergreen",
        length_target_sec=300,
        script="A calm evergreen reflection.",
        meta={"fallback": True},
    )
    assert handoff_from_segment(ever, "night_show") is None


def test_handoff_none_when_there_is_no_script():
    seg = Segment(id="talk-003", format="talk", length_target_sec=300, script=None)
    assert handoff_from_segment(seg, "night_show") is None


def test_handoff_roundtrips_through_a_dict():
    ho = Handoff(
        tail="Vell: and that's the thing.",
        topic="the long night",
        open_thread=True,
        program="night_show",
        air_time="2026-06-22T02:00:00",
    )
    restored = Handoff.from_dict(json.loads(json.dumps(ho.to_dict())))
    assert restored == ho


# --- Scheduler integration: positions computed + hand-off persisted ---------

# Two programs across a 01:00 boundary, each a pure talk clock. With a slot
# duration equal to the look-ahead horizon, positions are deterministic.
_GRID = """
programs:
  prog_a:
    name: "Program A"
    hosts: [vell, wren]
    framing: solo
    clock: [talk]
  prog_b:
    name: "Program B"
    hosts: [wren, vell]
    framing: solo
    clock: [talk]
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk]
grid:
  daily:
    "00:00-01:00": prog_a
    "01:00-24:00": prog_b
"""


def _flow_recording_generator(tmp_path, *, duration=1200.0):
    """A stand-in `make_format_segment` that records the `flow` handed to each slot."""
    calls: list[dict] = []

    def _gen(name, now_iso, *, topic=None, speakers=None, flow=None):
        calls.append({"format": name, "air_time": now_iso, "flow": flow})
        path = tmp_path / f"{name}-{len(calls):03d}.mp3"
        path.write_bytes(b"\x00")
        return Segment(
            id=f"{name}-{len(calls):03d}",
            format=name,
            length_target_sec=1200,
            air_time=now_iso,
            script=(
                "Vell: picking up where we were.\nWren: exactly, more to chew on there."
            ),
            audio_path=str(path),
            actual_duration_sec=duration,
            meta={"beat": "a running thread"},
        )

    return calls, _gen


def _wire(monkeypatch, tmp_path, generator):
    grid_path = tmp_path / "grid.yaml"
    grid_path.write_text(_GRID, encoding="utf-8")
    monkeypatch.setattr(scheduler.settings, "programming_grid_path", grid_path)
    programming.reload()

    monkeypatch.setattr(scheduler, "make_format_segment", generator)
    monkeypatch.setattr(scheduler.settings, "programming_enabled", True)
    monkeypatch.setattr(scheduler.settings, "buffer_rotation", ["talk"])
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", 1.2)  # ~4 slots
    monkeypatch.setattr(scheduler.settings, "segment_default_length_target_sec", 1200)
    monkeypatch.setattr(scheduler.settings, "schedule_topup_max_segments", 100)
    monkeypatch.setattr(scheduler.settings, "schedule_failure_max_retries", 1)
    monkeypatch.setattr(scheduler.settings, "segments_dir", tmp_path)
    monkeypatch.setattr(scheduler.settings, "segment_retention_hours", 24.0)
    monkeypatch.setattr(scheduler.settings, "segment_retention_max_gb", None)
    monkeypatch.setattr(
        scheduler.settings, "schedule_state_path", tmp_path / "schedule.json"
    )
    monkeypatch.setattr(
        scheduler.settings, "schedule_playlist_path", tmp_path / "playlist.txt"
    )
    monkeypatch.setattr(scheduler.settings, "disclosure_enabled", False)
    monkeypatch.setattr(scheduler.settings, "production_ident_every_n", 0)
    monkeypatch.setattr(scheduler.settings, "production_theme_at_boundary", False)
    monkeypatch.setattr(scheduler.settings, "production_sting_before_news", False)
    monkeypatch.setattr(scheduler.settings, "production_bedded_programs", [])
    monkeypatch.setattr(scheduler.settings, "commercial_break_enabled", False)
    monkeypatch.setattr(scheduler, "ensure_fallback_assets", lambda **k: {})
    monkeypatch.setattr(scheduler, "record_airplay_features", lambda seg: False)
    monkeypatch.setattr(scheduler, "sweep_airplay", lambda now: 0)


def teardown_function(_):
    programming.reload()  # never leak the fixture grid into other test modules


def test_top_up_computes_positions_and_persists_the_handoff(monkeypatch, tmp_path):
    calls, gen = _flow_recording_generator(tmp_path)
    _wire(monkeypatch, tmp_path, gen)

    # Start at 00:05 so prog_a runs, crosses the 01:00 boundary into prog_b.
    scheduler.top_up(now=datetime(2026, 6, 22, 0, 5))

    positions = [c["flow"].position for c in calls]
    programs_seen = [c["air_time"] for c in calls]
    assert len(calls) >= 4, programs_seen
    # prog_a: open (first) -> continue (middle) -> close (last before the boundary);
    # then prog_b: open (a new program instance opens fresh).
    assert positions[0] == OPEN
    assert positions[1] == CONTINUE
    assert positions[2] == CLOSE
    assert positions[3] == OPEN

    # A ShowFlow was threaded into every grid content slot.
    assert all(isinstance(c["flow"], ShowFlow) for c in calls)

    # The substrate is persisted in clock_state for the next top-up run.
    state = json.loads((tmp_path / "schedule.json").read_text())
    saved = state["clock_state"]["_flow"]
    assert saved["last_content_program"] == "prog_b"  # last placed content program
    assert saved["handoff"]["topic"] == "a running thread"
    assert "more to chew on there" in saved["handoff"]["tail"]
    assert saved["handoff"]["open_thread"] is True


def test_flat_rotation_carries_no_flow(monkeypatch, tmp_path):
    # programming disabled = the pre-D6 flat path; slots stay standalone (flow=None).
    calls, gen = _flow_recording_generator(tmp_path)
    _wire(monkeypatch, tmp_path, gen)
    monkeypatch.setattr(scheduler.settings, "programming_enabled", False)

    scheduler.top_up(now=datetime(2026, 6, 22, 0, 5))

    assert calls, "expected some slots to be generated"
    assert all(c["flow"] is None for c in calls)

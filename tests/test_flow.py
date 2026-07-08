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
from src.formats import talk as talk_fmt
from src.segment import Segment
from src.world import programming
from src.world.context import AssembledContext
from src.world.framing import ShowFrame
from src.writers import conversation as convo

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


def _wire(monkeypatch, tmp_path, generator, grid_text=_GRID, *, max_segments=3):
    grid_path = tmp_path / "grid.yaml"
    grid_path.write_text(grid_text, encoding="utf-8")
    monkeypatch.setattr(scheduler.settings, "programming_grid_path", grid_path)
    programming.reload()
    monkeypatch.setattr(scheduler.settings, "convo_continuity_enabled", True)
    monkeypatch.setattr(
        scheduler.settings, "convo_continuity_max_segments", max_segments
    )

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


# --- D12.1: positional backbone selection -----------------------------------


def test_backbone_is_standalone_without_flow():
    assert talk_fmt._backbone_for(None) == talk_fmt._BACKBONE_STANDALONE


def test_backbone_is_standalone_when_continuity_disabled(monkeypatch):
    monkeypatch.setattr(talk_fmt.settings, "convo_continuity_enabled", False)
    got = talk_fmt._backbone_for(ShowFlow(OPEN))
    assert got == talk_fmt._BACKBONE_STANDALONE


def test_backbone_positional_open_continue_close():
    assert "OPENS" in talk_fmt._backbone_for(ShowFlow(OPEN))
    middle = talk_fmt._backbone_for(ShowFlow(CONTINUE))
    assert "MIDDLE" in middle and "COLD" in middle
    assert "CLOSES" in talk_fmt._backbone_for(ShowFlow(CLOSE))


# --- D12.1: positional / policy-gated time-check ----------------------------

_NOON = datetime(2026, 6, 22, 14, 30)  # mid-afternoon, mid-hour (no pin)
_TOP_OF_HOUR = datetime(2026, 6, 22, 14, 2)  # within the top-of-hour window


def _frame(*, is_handover=False, part="afternoon"):
    return ShowFrame(
        part_of_day=part,
        lead="wren",
        companion="vell",
        is_handover=is_handover,
        situation="{lead} anchors",
    )


def _has_timecheck(directive: str) -> bool:
    """A directive INCLUDES a time-check (vs. instructing not to give one)."""
    return "belongs near" in directive and "do not" not in directive.lower()


def test_timecheck_standalone_always_present():
    # No flow (direct path): keep the pre-D12 always-a-time-check behaviour.
    assert _has_timecheck(convo._time_check_directive(_frame(), None, _NOON))


def test_timecheck_dropped_on_a_cold_continue(monkeypatch):
    monkeypatch.setattr(convo.settings, "convo_flow_timecheck", "hourly")
    monkeypatch.setattr(convo.settings, "convo_continuity_enabled", True)
    directive = convo._time_check_directive(_frame(), ShowFlow(CONTINUE), _NOON)
    assert not _has_timecheck(directive)
    assert "do not" in directive.lower()


def test_timecheck_present_on_the_open(monkeypatch):
    monkeypatch.setattr(convo.settings, "convo_flow_timecheck", "open")
    directive = convo._time_check_directive(_frame(), ShowFlow(OPEN), _NOON)
    assert "belongs near the open" in directive


def test_handover_always_timechecks_regardless_of_position(monkeypatch):
    monkeypatch.setattr(convo.settings, "convo_flow_timecheck", "open")
    directive = convo._time_check_directive(
        _frame(is_handover=True, part="first light"), ShowFlow(CONTINUE), _NOON
    )
    assert "belongs near the handover" in directive


def test_never_policy_suppresses_even_the_open(monkeypatch):
    monkeypatch.setattr(convo.settings, "convo_flow_timecheck", "never")
    directive = convo._time_check_directive(_frame(), ShowFlow(OPEN), _NOON)
    assert not _has_timecheck(directive)


def test_hourly_allows_a_top_of_hour_continue(monkeypatch):
    monkeypatch.setattr(convo.settings, "convo_flow_timecheck", "hourly")
    directive = convo._time_check_directive(_frame(), ShowFlow(CONTINUE), _TOP_OF_HOUR)
    assert _has_timecheck(directive)


def test_open_policy_does_not_grant_top_of_hour_continue(monkeypatch):
    # `open` is stricter than `hourly`: a mid-show continue never time-checks.
    monkeypatch.setattr(convo.settings, "convo_flow_timecheck", "open")
    directive = convo._time_check_directive(_frame(), ShowFlow(CONTINUE), _TOP_OF_HOUR)
    assert not _has_timecheck(directive)


# --- D12.2: showrunner thread directive + orchestrator pickup (pure) ---------


def _handoff(*, open_thread=True, topic="the reclaim", tail="Wren: more to say."):
    return Handoff(tail=tail, topic=topic, open_thread=open_thread, program="p")


def test_showrunner_thread_fresh_without_flow():
    block, task = convo._showrunner_thread(None)
    assert block == ""
    assert "Pick exactly ONE" in task


def test_showrunner_thread_continue_deepens_same_beat():
    flow = ShowFlow(CONTINUE, handoff=_handoff(), continue_thread=True)
    block, task = convo._showrunner_thread(flow)
    assert "CONTINUE" in block and "the reclaim" in block
    assert "SAME thread" in task and "Pick exactly ONE" not in task


def test_showrunner_thread_transition_moves_on():
    # Handoff present but not continuing (budget/spent) -> a deliberate transition.
    flow = ShowFlow(CONTINUE, handoff=_handoff(), continue_thread=False)
    block, task = convo._showrunner_thread(flow)
    assert "FRESH subject" in block or "move ON" in block
    assert "Pick exactly ONE" in task  # still a fresh pick


def test_showrunner_thread_fresh_when_disabled(monkeypatch):
    monkeypatch.setattr(convo.settings, "convo_continuity_enabled", False)
    flow = ShowFlow(CONTINUE, handoff=_handoff(), continue_thread=True)
    block, task = convo._showrunner_thread(flow)
    assert block == "" and "Pick exactly ONE" in task


def test_pickup_only_on_a_continuing_continue_slot():
    cont = ShowFlow(
        CONTINUE, handoff=_handoff(tail="Vell: right there."), continue_thread=True
    )
    got = convo._pickup_section(cont)
    assert "PICK UP" in got and "Vell: right there." in got


def test_pickup_empty_on_open_close_transition_and_none():
    ho = _handoff()
    assert convo._pickup_section(None) == ""
    assert (
        convo._pickup_section(ShowFlow(OPEN, handoff=ho, continue_thread=False)) == ""
    )
    assert (
        convo._pickup_section(ShowFlow(CLOSE, handoff=ho, continue_thread=True)) == ""
    )
    # a continue slot that is NOT continuing (transition/soft-open) gets no pickup
    assert (
        convo._pickup_section(ShowFlow(CONTINUE, handoff=ho, continue_thread=False))
        == ""
    )


# --- D12.2: scheduler pacing / continuation decision (integration) ----------

# One program, all-talk, tiling the whole day: positions are open then continue,
# so the thread pacing is the only thing moving continue_thread.
_ONE_PROGRAM = """
programs:
  night:
    name: "The Long Night"
    hosts: [vell, wren]
    framing: solo
    clock: [talk]
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk]
grid:
  daily:
    "00:00-24:00": night
"""

# talk alternating with music, so the thread must carry ACROSS the music slot.
_TALK_MUSIC = """
programs:
  night:
    name: "The Long Night"
    hosts: [vell, wren]
    framing: solo
    clock: [talk, music]
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk]
grid:
  daily:
    "00:00-24:00": night
"""


def test_thread_paces_out_at_the_budget(monkeypatch, tmp_path):
    calls, gen = _flow_recording_generator(tmp_path)
    # depth 2h at 1200s/slot => 6 talk slots; max_segments=3.
    _wire(monkeypatch, tmp_path, gen, _ONE_PROGRAM, max_segments=3)
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", 2.0)

    scheduler.top_up(now=datetime(2026, 6, 22, 0, 5))

    decisions = [c["flow"].continue_thread for c in calls]
    # open starts fresh; the thread holds for 3 (opener + 2), then transitions; repeat.
    assert decisions[:6] == [False, True, True, False, True, True]


def test_thread_carries_across_a_music_slot(monkeypatch, tmp_path):
    calls, gen = _flow_recording_generator(tmp_path)
    _wire(monkeypatch, tmp_path, gen, _TALK_MUSIC, max_segments=3)
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", 1.5)

    scheduler.top_up(now=datetime(2026, 6, 22, 0, 5))

    talk_decisions = [c["flow"].continue_thread for c in calls if c["format"] == "talk"]
    # the 2nd talk continues the 1st's thread even though a music slot aired between.
    assert talk_decisions[0] is False  # the open
    assert talk_decisions[1] is True  # continues across the music


def test_evergreen_talk_breaks_the_thread(monkeypatch, tmp_path):
    # A generator whose 2nd talk slot falls to an evergreen (format != "talk").
    calls: list[dict] = []

    def gen(name, now_iso, *, topic=None, speakers=None, flow=None):
        calls.append({"format": name, "flow": flow})
        n = len(calls)
        fmt = "evergreen" if n == 2 else name
        path = tmp_path / f"{name}-{n:03d}.mp3"
        path.write_bytes(b"\x00")
        return Segment(
            id=f"{name}-{n:03d}",
            format=fmt,
            length_target_sec=1200,
            air_time=now_iso,
            script="Vell: a line.\nWren: another, still going.",
            audio_path=str(path),
            actual_duration_sec=1200.0,
            meta={"beat": "a thread"},
        )

    _wire(monkeypatch, tmp_path, gen, _ONE_PROGRAM, max_segments=5)
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", 1.2)

    scheduler.top_up(now=datetime(2026, 6, 22, 0, 5))

    decisions = [c["flow"].continue_thread for c in calls]
    # slot1 open (fresh); slot2 tries to continue but evergreens -> thread broken;
    # slot3 must NOT continue a segment that didn't really air.
    assert decisions[0] is False
    assert decisions[2] is False


# --- D12.3: freshness (D5) reconciled with continuity (integration) ----------


def _capture_steers(monkeypatch):
    """Stub compose_segment's model/DB seams; capture the freshness steers routed in.

    `recent_topics_block` echoes its `exclude` arg and `recent_openings_block` a fixed
    marker, so the test can read what the showrunner/orchestrator each received.
    """
    from src.safety import SafetyResult
    from src.world.store import CastMember
    from src.writers.conversation import ContinuityResult

    seen = {}
    vell = CastMember("vell", "Vell", "card", "vell_night", [])
    wren = CastMember("wren", "Wren", "card", "dj_two", [])
    ctx = AssembledContext(bible="core", dynamic="now", speakers=[vell, wren])

    monkeypatch.setattr(
        convo.freshness,
        "recent_topics_block",
        lambda now, *, exclude=None: f"TOPICS|exclude={exclude}",
    )
    monkeypatch.setattr(
        convo.freshness, "recent_openings_block", lambda now, fmt: "OPENINGS"
    )

    def _showrunner(ctx, now, *, frame=None, recent_block="", flow=None):
        seen["topics"] = recent_block
        return "the beat"

    def _orchestrate(ctx, beat, now, *, recent_openings="", **kwargs):
        seen["openings"] = recent_openings
        return "Vell: hi.\nWren: hey."

    monkeypatch.setattr(convo, "showrunner", _showrunner)
    monkeypatch.setattr(convo, "orchestrate", _orchestrate)
    monkeypatch.setattr(
        convo, "safety_check", lambda t: SafetyResult(True, "OK", "llm")
    )
    monkeypatch.setattr(
        convo,
        "continuity_check",
        lambda s, c, **k: ContinuityResult(True, "sonnet", "OK"),
    )
    monkeypatch.setattr(
        convo, "_render_turns", lambda turns, seg_id, *, default_emotion=None: "/x.mp3"
    )
    monkeypatch.setattr(
        convo.guest_mod, "maybe_guest", lambda ctx, now, fmt, chance=None: None
    )
    monkeypatch.setattr(convo.memory_mod, "memory_section", lambda speakers, now: "")
    return ctx, seen


_COMPOSE_NOW = datetime(2026, 6, 22, 14, 0)


def test_continuing_thread_exempts_topic_and_drops_openings(monkeypatch):
    ctx, seen = _capture_steers(monkeypatch)
    monkeypatch.setattr(convo.settings, "convo_continuity_enabled", True)
    flow = ShowFlow(
        CONTINUE,
        handoff=Handoff(tail="Wren: more.", topic="the reclaim", open_thread=True),
        continue_thread=True,
    )
    convo.compose_segment(ctx, _COMPOSE_NOW, seg_id="talk-c", flow=flow)
    assert seen["topics"] == "TOPICS|exclude=the reclaim"  # active thread exempt
    assert seen["openings"] == ""  # a cold pickup has no opening to freshen


def test_transition_slot_keeps_both_freshness_steers(monkeypatch):
    ctx, seen = _capture_steers(monkeypatch)
    monkeypatch.setattr(convo.settings, "convo_continuity_enabled", True)
    # a continue slot that is NOT continuing (a transition) starts a new subject:
    # both steers apply so it can't loop a recent topic or opening.
    flow = ShowFlow(
        CONTINUE,
        handoff=Handoff(tail="Wren: done.", topic="the reclaim", open_thread=False),
        continue_thread=False,
    )
    convo.compose_segment(ctx, _COMPOSE_NOW, seg_id="talk-t", flow=flow)
    assert seen["topics"] == "TOPICS|exclude=None"
    assert seen["openings"] == "OPENINGS"


def test_standalone_path_keeps_both_freshness_steers(monkeypatch):
    ctx, seen = _capture_steers(monkeypatch)
    convo.compose_segment(ctx, _COMPOSE_NOW, seg_id="talk-s", flow=None)
    assert seen["topics"] == "TOPICS|exclude=None"
    assert seen["openings"] == "OPENINGS"


# --- D12.4: program sign-on / sign-off + talk-first backbone -----------------


def test_open_signs_on_by_program_name():
    got = talk_fmt._backbone_for(ShowFlow(OPEN, program_name="The Long Night"))
    assert "SIGN ON" in got and "The Long Night" in got


def test_close_signs_off_by_program_name():
    got = talk_fmt._backbone_for(ShowFlow(CLOSE, program_name="The Long Night"))
    assert "SIGN OFF" in got and "The Long Night" in got


def test_signon_suppressed_when_disabled(monkeypatch):
    monkeypatch.setattr(talk_fmt.settings, "convo_flow_signon", False)
    got = talk_fmt._backbone_for(ShowFlow(OPEN, program_name="The Long Night"))
    assert "The Long Night" not in got and "SIGN ON" not in got


def test_signon_absent_without_a_program_name():
    got = talk_fmt._backbone_for(ShowFlow(OPEN, program_name=None))
    assert "SIGN ON" not in got


def test_no_talk_backbone_assumes_a_song_follows():
    # Talk-first: nothing promises "…and now some music" (a music slot self-intros).
    flows = [
        None,
        ShowFlow(OPEN, program_name="X"),
        ShowFlow(CONTINUE),
        ShowFlow(CLOSE, program_name="X"),
    ]
    for f in flows:
        text = talk_fmt._backbone_for(f).lower()
        assert "music" not in text and "a song" not in text and "a track" not in text


def test_scheduler_stamps_the_program_name_on_the_flow(monkeypatch, tmp_path):
    calls, gen = _flow_recording_generator(tmp_path)
    _wire(monkeypatch, tmp_path, gen, _ONE_PROGRAM)
    scheduler.top_up(now=datetime(2026, 6, 22, 0, 5))
    assert calls[0]["flow"].program_name == "The Long Night"

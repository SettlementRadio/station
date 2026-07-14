"""Tests for the C1 clock-driven show framing (src/world/framing.py).

This is the fix for the afternoon-handover bug: the room must frame a segment for
its ACTUAL hour, not a hardcoded night→first-light handover. The mapping is pure,
so we pin it directly across a full day — the boundaries between night, the dawn
handover, the daylight shifts, and the dusk handover — plus the prose resolver.
"""

from __future__ import annotations

from datetime import datetime

from src.world import framing

NIGHT, DAY = "vell", "wren"


def _frame(hour: int) -> framing.ShowFrame:
    return framing.show_frame(
        datetime(2026, 6, 22, hour, 0), night_host=NIGHT, day_host=DAY
    )


def test_deep_and_late_night_are_vell_solo():
    for h in (23, 0, 2, 4):
        f = _frame(h)
        assert f.lead == NIGHT and f.companion == DAY
        assert not f.is_handover
        assert f.part_of_day == "deep night"
    assert _frame(22).part_of_day == "late night"  # 22:00 is still Vell, not handover
    assert not _frame(22).is_handover


def test_dawn_window_is_the_vell_to_wren_handover():
    for h in (5, 6):
        f = _frame(h)
        assert f.is_handover
        assert f.lead == DAY  # Wren takes over at first light
        assert f.companion == NIGHT
        assert f.part_of_day == "first light"


def test_daylight_is_wren_anchoring_no_handover():
    assert _frame(7).part_of_day == "morning"
    assert _frame(11).part_of_day == "morning"
    assert _frame(12).part_of_day == "afternoon"
    assert _frame(16).part_of_day == "afternoon"
    assert _frame(17).part_of_day == "evening"
    assert _frame(19).part_of_day == "evening"
    for h in (7, 12, 16, 19):
        f = _frame(h)
        assert f.lead == DAY and f.companion == NIGHT
        assert not f.is_handover


def test_dusk_window_is_the_wren_to_vell_handover():
    for h in (20, 21):
        f = _frame(h)
        assert f.is_handover
        assert f.lead == NIGHT  # Vell takes the night back
        assert f.companion == DAY
        assert f.part_of_day == "nightfall"


def test_resolve_situation_fills_names_and_leaves_no_placeholders():
    f = _frame(14)  # afternoon: Wren leads, Vell companion
    text = framing.resolve_situation(f, {"vell": "Vell", "wren": "Wren"})
    assert "Wren" in text and "Vell" in text
    assert "{" not in text and "}" not in text


def test_a_full_day_never_calls_an_afternoon_a_handover():
    # The bug it fixes: no daytime hour may be framed as a handover.
    for h in range(7, 20):
        assert not _frame(h).is_handover


# --- Field hosts (the audit fix): a remote presence frames as a dispatch -----


def _program(hosts, framing_hint="ensemble"):
    from types import SimpleNamespace

    return SimpleNamespace(hosts=tuple(hosts), framing=framing_hint)


def test_remote_companion_frames_as_a_dispatch_not_in_studio():
    f = framing.program_frame(
        datetime(2026, 6, 22, 10, 0), _program(["thorn", "zhe"]), remote=("zhe",)
    )
    assert f.remote == ("zhe",)
    assert "dispatch" in f.situation and "relay" in f.situation
    text = framing.resolve_situation(f, {"thorn": "Thorn", "zhe": "Zhe"})
    assert "Thorn" in text and "Zhe" in text and "{" not in text


def test_remote_lead_gives_the_hour_to_the_dispatch():
    f = framing.program_frame(
        datetime(2026, 6, 22, 3, 0),
        _program(["zhe", "the-archivist"], "solo"),
        remote=("zhe",),
    )
    assert "dispatch" in f.situation
    assert "holds the booth" in f.situation  # the studio host stays the anchor point


def test_both_hosts_remote_frames_as_carried_dispatches():
    f = framing.program_frame(
        datetime(2026, 6, 22, 17, 0), _program(["sera", "zhe"]), remote=("sera", "zhe")
    )
    assert f.remote == ("sera", "zhe")
    assert "dispatches from" in f.situation


def test_remote_ids_not_on_air_are_ignored():
    f = framing.program_frame(
        datetime(2026, 6, 22, 14, 0), _program(["vell", "wren"]), remote=("sera",)
    )
    assert f.remote == ()
    assert "dispatch" not in f.situation


def test_no_remote_keeps_the_in_studio_prose():
    for h in (3, 10, 21):
        assert "dispatch" not in _frame(h).situation

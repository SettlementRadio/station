"""Tests for D6.1 — the programming module + generalised framing.

Two things must hold:
  1. `program_for(now)` reads the weekly grid and returns the right named program
     across weekday/hour boundaries, tiles the week with no gaps, and never stalls
     (a hole, an unknown program, or a missing grid file all fall back to `default`).
  2. The generalised `framing.program_frame` preserves the two-host C1 behaviour
     EXACTLY for the shipped grid — the strongest guarantee that D1–D5 are unchanged.

The grid read is pure config, so we point `settings.programming_grid_path` at a
written fixture and pin the mapping directly (no DB, no Claude/TTS).
"""

from __future__ import annotations

from datetime import datetime

import pytest
from src.config import settings
from src.world import framing, programming

# --- Fixtures ---------------------------------------------------------------

# A small, explicit grid: weekday shows + a weekend override + a deliberate gap
# (Sun 00:00-06:00 is left untiled) so the default fallback is exercised.
_FIXTURE_GRID = """
programs:
  long_night:
    name: "The Long Night"
    hosts: [vell, wren]
    framing: solo
    clock: [talk, music x3, sting, news@:00]
  first_light:
    name: "First Light"
    hosts: [wren, vell]
    framing: handover
    clock: [talk, news@:00]
  daywatch:
    name: "Daywatch"
    hosts: [wren, vell]
    framing: solo
    clock: [talk, news@:00, talk]
  archive_hour:
    name: "Archive Hour"
    hosts: [the-archivist]
    framing: solo
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk, news]
grid:
  weekdays:
    "00:00-06:00": long_night
    "06:00-07:00": first_light
    "07:00-24:00": daywatch
  sat:
    "00:00-24:00": archive_hour
  sun:
    "06:00-24:00": daywatch
"""


@pytest.fixture()
def grid_file(tmp_path, monkeypatch):
    """Point the module at a written fixture grid + drop its cache around the test."""
    path = tmp_path / "grid.yaml"
    path.write_text(_FIXTURE_GRID, encoding="utf-8")
    monkeypatch.setattr(settings, "programming_grid_path", path)
    programming.reload()
    yield path
    programming.reload()


@pytest.fixture()
def real_grid():
    """Load the SHIPPED grid (docs/programming/grid.yaml) at its configured path.

    Its boundaries align with the canon dawn/dusk windows, so it is the grid the
    two-host parity check must run against. Drops the cache on the way out.
    """
    programming.reload()
    yield
    programming.reload()


# A Monday (weekday 0) and a Saturday (weekday 5) to pin weekday routing.
def _mon(hour: int) -> datetime:
    return datetime(2026, 6, 22, hour, 0)  # 2026-06-22 is a Monday


def _sat(hour: int) -> datetime:
    return datetime(2026, 6, 27, hour, 0)  # 2026-06-27 is a Saturday


def _sun(hour: int) -> datetime:
    return datetime(2026, 6, 28, hour, 0)  # 2026-06-28 is a Sunday


# --- program_for: the grid resolves correctly -------------------------------


def test_weekday_slots_resolve_by_hour(grid_file):
    assert programming.program_for(_mon(2)).id == "long_night"
    assert programming.program_for(_mon(5)).id == "long_night"  # up to 06:00
    assert programming.program_for(_mon(6)).id == "first_light"
    assert programming.program_for(_mon(7)).id == "daywatch"
    assert programming.program_for(_mon(19)).id == "daywatch"
    assert programming.program_for(_mon(23)).id == "daywatch"


def test_weekend_override_is_more_specific_than_weekdays(grid_file):
    # Saturday is fully tiled by the single-day `sat` slot.
    for h in (0, 8, 15, 23):
        assert programming.program_for(_sat(h)).id == "archive_hour"


def test_a_gap_falls_back_to_default_never_stalls(grid_file):
    # Sun 00:00-06:00 is untiled in the fixture -> default fallback.
    prog = programming.program_for(_sun(3))
    assert prog.id == "default"
    assert prog.framing == "legacy"
    # ...but Sun 07:00 IS tiled.
    assert programming.program_for(_sun(7)).id == "daywatch"


def test_missing_grid_file_synthesises_default_from_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "programming_grid_path", tmp_path / "nope.yaml")
    programming.reload()
    try:
        prog = programming.program_for(_mon(3))
        assert prog.id == settings.programming_default_program
        assert prog.framing == "legacy"
        assert tuple(prog.hosts) == tuple(settings.convo_speaker_ids)
        assert tuple(prog.rotation) == tuple(settings.buffer_rotation)
    finally:
        programming.reload()


# --- Clock parsing (structured, for the D6.2 scheduler) ---------------------


def test_clock_parses_runs_pins_and_markers(grid_file):
    clock = programming.program_for(_mon(2)).clock  # long_night
    kinds = [(s.format, s.count, s.pin_minute, s.is_marker) for s in clock]
    assert kinds == [
        ("talk", 1, None, False),
        ("music", 3, None, False),  # `music x3` -> run-length 3
        ("sting", 1, None, True),  # a marker: inert until D7
        ("news", 1, 0, False),  # `news@:00` -> pinned to the top of the hour
    ]


# --- The generalised frame preserves the two-host C1 behaviour EXACTLY ------


def test_shipped_grid_tiles_the_weekday_with_expected_programs(real_grid):
    expected = {
        **dict.fromkeys((22, 23, 0, 1, 2, 3, 4), "long_night"),
        **dict.fromkeys((5, 6), "first_light"),
        **dict.fromkeys(range(7, 20), "daywatch"),
        **dict.fromkeys((20, 21), "nightfall"),
    }
    for h in range(24):
        assert programming.program_for(_mon(h)).id == expected[h], f"hour {h}"


def test_program_frame_matches_legacy_show_frame_across_the_day(real_grid):
    """program_frame over the SHIPPED weekday grid == the old two-host show_frame.

    Directly asserts D6.1's hard requirement: with the two current hosts the frame
    is unchanged (same lead/companion/handover/part_of_day/situation), so the
    writers' room (D1-D5) is untouched. The shipped grid's boundaries align with the
    canon dawn/dusk windows, which is what makes the two representations agree.
    """
    for h in range(24):
        now = _mon(h)
        prog = programming.program_for(now)
        got = framing.program_frame(now, prog)
        want = framing.show_frame(now, night_host="vell", day_host="wren")
        assert got == want, f"hour {h}: {got} != {want}"


def test_legacy_framing_routes_back_through_show_frame(grid_file):
    now = _sun(3)  # the gap slot -> default program (legacy framing)
    prog = programming.program_for(now)
    assert framing.program_frame(now, prog) == framing.show_frame(
        now, night_host="vell", day_host="wren"
    )


def test_handover_hint_drives_is_handover_for_n_hosts(grid_file):
    now = _mon(6)  # first_light: framing handover, hosts [wren, vell]
    frame = framing.program_frame(now, programming.program_for(now))
    assert frame.is_handover
    assert frame.lead == "wren" and frame.companion == "vell"


def test_solo_program_with_one_host_has_no_companion(grid_file):
    now = _sat(10)  # archive_hour: solo, single host [the-archivist]
    frame = framing.program_frame(now, programming.program_for(now))
    assert not frame.is_handover
    assert frame.lead == "the-archivist"
    assert frame.companion == ""
    # a single-host situation still resolves with no dangling placeholder
    text = framing.resolve_situation(frame, {"the-archivist": "The Archivist"})
    assert "The Archivist" in text and "{" not in text and "}" not in text

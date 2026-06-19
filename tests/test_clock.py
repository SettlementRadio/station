"""Tests for the world clock (src/world/clock.py).

The +600yr mapping is load-bearing (CLAUDE.md flags "the world clock" as a thing
to test). These pin the two distinct behaviours — arithmetic vs display — and the
one calendar trap (29 Feb across the Gregorian 400-year rule).
"""

from __future__ import annotations

from datetime import datetime

from src.world import clock


def test_to_inworld_shifts_year_by_600_keeping_wall_clock():
    real = datetime(2026, 6, 19, 2, 14)
    assert clock.to_inworld(real) == datetime(2626, 6, 19, 2, 14)


def test_to_real_is_the_inverse():
    inworld = datetime(2626, 6, 24, 20, 0)
    assert clock.to_real(inworld) == datetime(2026, 6, 24, 20, 0)


def test_render_wall_clock_keeps_real_weekday_and_shifts_year():
    # 16 June 2026 is a Tuesday; the in-world line relabels the year, not the day.
    real = datetime(2026, 6, 16, 2, 14)
    assert clock.render_wall_clock(real) == "Tuesday, 16 June 2626, 02:14"


def test_leap_day_maps_to_feb_28_when_target_year_is_not_leap():
    # 2000 is a leap year; 2600 is NOT (divisible by 100, not 400) — so 29 Feb
    # has nowhere to land and we fall back to the 28th rather than raise.
    mapped = clock.to_inworld(datetime(2000, 2, 29, 12, 0))
    assert mapped == datetime(2600, 2, 28, 12, 0)

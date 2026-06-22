"""Tests for the C0 evergreen fallback's pure bits (src/evergreen.py).

Rendering needs TTS, so `evergreen_segment` is exercised via the producers. Here
we pin the script selection: it must be deterministic (stable/testable), rotate by
the hour (no back-to-back repeat across hours), and only ever return safe, marker-
free pool text — the thing the station airs when a draft fails the gates.
"""

from __future__ import annotations

from datetime import datetime

from src import evergreen


def test_pick_is_deterministic_by_hour():
    now = datetime(2026, 6, 22, 3, 14)
    assert evergreen.pick_evergreen_script(now) == evergreen.pick_evergreen_script(now)


def test_pick_rotates_across_hours():
    base = datetime(2026, 6, 22, 0, 0)
    picks = {
        evergreen.pick_evergreen_script(base.replace(hour=h))
        for h in range(len(evergreen._EVERGREEN_SCRIPTS))
    }
    # Each slot in the rotation surfaces a distinct script.
    assert len(picks) == len(evergreen._EVERGREEN_SCRIPTS)


def test_pool_is_nonempty_safe_text():
    for script in evergreen._EVERGREEN_SCRIPTS:
        assert script.strip()
        assert "[SONG]" not in script  # single block, no format markers to speak

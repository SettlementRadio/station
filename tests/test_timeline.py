"""Tests for the operator timeline page (src/timeline.py).

Light, on the assembly logic only: the page names what's ON AIR (with the
program), lists the queued entries in air order, and shows the grid's intended
program blocks ahead — all from a fixture state, no server, no generation.
The schedule maths it leans on (`split_schedule`) has its own tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src import timeline

NOW = datetime(2026, 6, 22, 14, 30, 0)  # a Monday afternoon (grid: the_workshop)


def _state(now=NOW) -> dict:
    return {
        "entries": [
            {
                "id": "talk-001",
                "format": "talk",
                "program": "the_workshop",
                "program_name": "The Workshop",
                "flow_position": "continue",
                "audio_path": "/x/talk-001.mp3",
                "air_time": (now - timedelta(minutes=1)).isoformat(),
                "actual_duration_sec": 240.0,
                "length_target_sec": 240,
            },
            {
                "id": "news-002",
                "format": "news",
                "program": "the_workshop",
                "program_name": "The Workshop",
                "audio_path": "/x/news-002.mp3",
                "air_time": (now + timedelta(minutes=3)).isoformat(),
                "actual_duration_sec": 120.0,
                "length_target_sec": 150,
            },
        ],
    }


def test_page_shows_onair_queue_and_grid(monkeypatch):
    page = timeline.render(NOW, _state())
    # ON AIR: the current entry, its program, and a live progress bar.
    assert "talk-001" in page and "The Workshop" in page
    assert 'class="fill"' in page
    # Queued next: the upcoming entry with its air time.
    assert "news-002" in page and "14:33:00" in page
    # The grid ahead names real programs from the weekly grid (independent of
    # what's generated) — at least the block that is on right now.
    assert "The grid ahead" in page
    assert page.count('class="prog"') >= 3


def test_page_degrades_with_no_schedule():
    page = timeline.render(NOW, {"entries": []})
    assert "nothing scheduled" in page
    assert "no schedule yet" in page  # the idle status line
    assert "The grid ahead" in page  # the grid still renders without a schedule

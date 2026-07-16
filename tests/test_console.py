"""Tests for D6.3 — the read-only operator status console (src/console.py).

Two promises to pin: (1) it renders the live station state — on-air/next (with the
program the D6.2 scheduler stamped), buffer runway (REUSING the health calc), the
last-run heartbeat, and the D3 story log; (2) it is STRICTLY READ-ONLY and degrades
gracefully when the DB is unavailable — the file-backed panels stand alone. Generation
+ Postgres are out of scope, so the schedule is a fixture and the store is stubbed.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime, timedelta

from src import console
from src.world import store

NOW = datetime(2026, 6, 22, 14, 30, 0)  # Monday, mid-afternoon


def _schedule(now=NOW):
    """A schedule.json with one segment ON AIR now + two queued ahead."""
    return {
        "entries": [
            {
                "id": "talk-001",
                "format": "talk",
                "program": "daywatch",
                "program_name": "Daywatch",
                "audio_path": "/x/talk-001.mp3",
                "air_time": (now - timedelta(minutes=2)).isoformat(),
                "actual_duration_sec": 300.0,
                "length_target_sec": 300,
            },
            {
                "id": "news-002",
                "format": "news",
                "program": "daywatch",
                "program_name": "Daywatch",
                "audio_path": "/x/news-002.mp3",
                "air_time": (now + timedelta(minutes=3)).isoformat(),
                "actual_duration_sec": 120.0,
                "length_target_sec": 150,
            },
            {
                "id": "talk-003",
                "format": "talk",
                "program": "daywatch",
                "program_name": "Daywatch",
                "audio_path": "/x/talk-003.mp3",
                "air_time": (now + timedelta(minutes=5)).isoformat(),
                "actual_duration_sec": None,  # probe missing -> shown as ≈target
                "length_target_sec": 300,
            },
        ],
        "last_topup_at": (now - timedelta(minutes=1)).isoformat(),
    }


def _wire(monkeypatch, tmp_path, state=None):
    """Point the scheduler/health state at a fixture schedule.json."""
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps(state or _schedule()), encoding="utf-8")
    monkeypatch.setattr(console.settings, "schedule_state_path", path)
    monkeypatch.setattr(console.health.settings, "schedule_state_path", path)
    monkeypatch.setattr(console.settings, "buffer_depth_hours", 2.0)
    monkeypatch.setattr(console.settings, "health_min_runway_minutes", 20.0)
    return path


def _no_db(monkeypatch):
    """Make store.connect raise so the DB panels degrade (hermetic default)."""

    @contextlib.contextmanager
    def _boom():
        raise RuntimeError("no database in tests")
        yield  # pragma: no cover

    monkeypatch.setattr(console.store, "connect", _boom)


# --- The file-backed panels render the live state ---------------------------


def test_on_air_and_next_show_program_and_format(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    lines = console.now_next_lines(NOW, _schedule())
    text = "\n".join(lines)
    assert "▶" in text  # the ON AIR marker
    assert "Daywatch" in text and "talk" in text
    assert "into the segment" in text  # progress into the current segment
    assert "news" in text  # an upcoming entry is listed


def test_nothing_on_air_when_the_buffer_is_empty(monkeypatch, tmp_path):
    empty = {"entries": [], "last_topup_at": NOW.isoformat()}
    _wire(monkeypatch, tmp_path, empty)
    text = "\n".join(console.now_next_lines(NOW, empty))
    assert "nothing on air" in text
    assert "nothing queued" in text


def test_buffer_panel_reuses_the_health_runway(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    # The fixture queues only a few minutes ahead of now (under the 20-min floor), so
    # the runway line prints and health flags it low — REUSED, not recomputed here.
    text = "\n".join(console.buffer_lines(NOW))
    assert "runway" in text and "target 2h" in text
    assert "low buffer" in text  # health.check_buffer's message, surfaced verbatim


def test_last_run_panel_reads_the_heartbeat(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    text = "\n".join(console.last_run_lines(NOW, _schedule()))
    assert "last top-up:" in text
    assert "generator live" in text  # 1 min ago is within the default window


# --- Read-only + graceful degradation ---------------------------------------


def test_render_mutates_nothing_and_degrades_without_a_db(monkeypatch, tmp_path):
    path = _wire(monkeypatch, tmp_path)
    _no_db(monkeypatch)
    before = path.read_text(encoding="utf-8")

    report = console.render(NOW)

    # The file-backed panels rendered...
    assert "ON AIR / NEXT" in report and "Daywatch" in report
    assert "BUFFER" in report and "LAST RUN" in report
    # ...the DB panels degraded to a single note instead of crashing...
    assert "world/story log unavailable" in report
    # ...and nothing on disk changed (strictly read-only).
    assert path.read_text(encoding="utf-8") == before


# --- The DB panels render when the store IS reachable (stubbed) -------------


def test_world_and_story_panels_render_from_the_store(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)

    story = store.Story(
        id="s1",
        title="The Relay Goes Dark",
        summary="A relay station loses contact.",
        arc_stage="developing",
        tags=["relay", "outage"],
    )
    beat = store.Event(
        id="b1",
        title="Contact lost at dusk",
        body="The last packet arrived at nightfall.",
        in_world_datetime=datetime(2626, 6, 21, 20, 0),
        status="past",
    )

    state_kv = {
        "world_tick_count": "12",
        "world_tick_last_at": (NOW - timedelta(hours=6)).isoformat(),
    }
    monkeypatch.setattr(store, "get_state", lambda conn, key: state_kv.get(key))
    monkeypatch.setattr(store, "active_stories", lambda conn, limit=None: [story])
    monkeypatch.setattr(store, "story_beats", lambda conn, sid: [beat])
    monkeypatch.setattr(store, "journal_counts", lambda conn: {"vell": 2, "wren": 1})

    @contextlib.contextmanager
    def _fake_conn():
        yield object()

    monkeypatch.setattr(console.store, "connect", _fake_conn)

    report = console.render(NOW)
    assert "ticks run: 12" in report and "active stories: 1" in report
    assert "The Relay Goes Dark" in report and "[developing]" in report
    assert "Contact lost at dusk" in report  # the newest beat
    assert "vell: 2" in report and "wren: 1" in report  # the D13.1 journal line
    assert "no usage rollup recorded yet" in report  # cost omitted gracefully

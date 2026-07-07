"""Tests for D6.4 — the public now-playing / program-info feed (src/nowplaying.py).

Two promises: (1) the feed reflects the live schedule — current program + segment,
what's next, host display names, and the AI-disclosure line; (2) it is PUBLIC-SAFE — an
explicit allow-list of fields, never leaking internal/operator state (ids, audio paths,
durations, buffer/health/story internals). Postgres is stubbed; the schedule is a
fixture (the same shape the D6.2 scheduler writes).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from src import nowplaying
from src.disclosure import DISCLOSURE_LINE

NOW = datetime(2026, 6, 22, 5, 30, 0)  # Monday first light -> the First Light program

# The internal keys the scheduler persists — the feed must expose only a safe subset.
_INTERNAL_KEYS = {"id", "audio_path", "actual_duration_sec", "length_target_sec"}


def _schedule(now=NOW):
    return {
        "entries": [
            {
                "id": "talk-001",
                "format": "talk",
                "program": "first_light",
                "program_name": "First Light",
                "audio_path": "/segments/talk-001.mp3",
                "air_time": (now - timedelta(minutes=2)).isoformat(),
                "actual_duration_sec": 300.0,
                "length_target_sec": 300,
            },
            {
                "id": "news-002",
                "format": "news",
                "program": "first_light",
                "program_name": "First Light",
                "audio_path": "/segments/news-002.mp3",
                "air_time": (now + timedelta(minutes=3)).isoformat(),
                "actual_duration_sec": 120.0,
                "length_target_sec": 150,
            },
        ],
        "last_topup_at": now.isoformat(),
    }


def _stub_names(monkeypatch, names):
    """Stub the cast lookup so display names are deterministic + DB-free."""
    monkeypatch.setattr(
        nowplaying, "_name_map", lambda ids: {i: names.get(i, i) for i in ids}
    )


# --- The feed reflects the live schedule ------------------------------------


def test_now_and_next_from_the_schedule(monkeypatch):
    _stub_names(monkeypatch, {"vell": "Vell", "wren": "Wren", "thorn": "Thorn"})
    feed = nowplaying.build_feed(NOW, _schedule())

    assert feed["station"] == nowplaying.STATION_NAME
    assert feed["disclosure"] == DISCLOSURE_LINE  # in sync with the web copy
    assert feed["now"]["program"] == "First Light"
    assert feed["now"]["format"] == "talk"
    assert feed["now"]["format_label"] == "Talk"
    # talk is two-voice: both program hosts show (First Light = wren, vell), by name.
    assert feed["now"]["hosts"] == ["Wren", "Vell"]
    # what's next is the news desk...
    assert [n["format"] for n in feed["next"]] == ["news"]
    # ...read by the DEDICATED news anchor (Thorn), not the show host (D12.4).
    assert feed["next"][0]["hosts"] == ["Thorn"]
    assert feed["next"][0]["format_label"] == "The Settlement News"


def test_nothing_on_air_yields_null_now(monkeypatch):
    _stub_names(monkeypatch, {})
    empty = {"entries": [], "last_topup_at": NOW.isoformat()}
    feed = nowplaying.build_feed(NOW, empty)
    assert feed["now"] is None
    assert feed["next"] == []
    assert feed["disclosure"] == DISCLOSURE_LINE  # disclosure always present


def test_next_count_is_bounded(monkeypatch):
    _stub_names(monkeypatch, {"vell": "Vell", "wren": "Wren"})
    monkeypatch.setattr(nowplaying.settings, "nowplaying_next_count", 1)
    # add a couple more upcoming entries
    state = _schedule()
    for i in range(3):
        state["entries"].append(
            {
                "id": f"talk-1{i}",
                "format": "talk",
                "program": "first_light",
                "program_name": "First Light",
                "audio_path": f"/segments/talk-1{i}.mp3",
                "air_time": (NOW + timedelta(minutes=10 + i)).isoformat(),
                "actual_duration_sec": 300.0,
                "length_target_sec": 300,
            }
        )
    feed = nowplaying.build_feed(NOW, state)
    assert len(feed["next"]) == 1


# --- Public-safe: an allow-list, never internal state -----------------------


def test_feed_leaks_no_internal_fields(monkeypatch):
    _stub_names(monkeypatch, {"vell": "Vell", "wren": "Wren"})
    feed = nowplaying.build_feed(NOW, _schedule())

    # D7.4 added `track` — the spun track's public lore (title/artist/album/era),
    # still an allow-listed field, None for non-music entries.
    allowed = {"program", "format", "format_label", "hosts", "air_time", "track"}
    for item in filter(None, [feed["now"], *feed["next"]]):
        assert set(item) == allowed, f"unexpected fields: {set(item) - allowed}"
        for bad in _INTERNAL_KEYS:
            assert bad not in item

    top_level = set(feed)
    assert top_level == {"station", "disclosure", "updated_at", "now", "next"}
    # a hard check that no audio path or segment id leaked anywhere in the JSON
    blob = json.dumps(feed)
    assert "audio_path" not in blob and "/segments/" not in blob
    assert "talk-001" not in blob and "news-002" not in blob


def test_ident_segment_shows_no_hosts_or_program(monkeypatch):
    _stub_names(monkeypatch, {})
    state = {
        "entries": [
            {
                "id": "ident-disclosure-01",
                "format": "ident",
                "program": None,  # idents carry no program
                "program_name": None,
                "audio_path": "/segments/ident.mp3",
                "air_time": (NOW - timedelta(seconds=5)).isoformat(),
                "actual_duration_sec": 12.0,
                "length_target_sec": 15,
            }
        ],
        "last_topup_at": NOW.isoformat(),
    }
    feed = nowplaying.build_feed(NOW, state)
    assert feed["now"]["program"] is None
    assert feed["now"]["hosts"] == []
    assert feed["now"]["format_label"] == "Station ID"


# --- write_feed is a real, re-readable file ---------------------------------


def test_write_feed_writes_valid_json(monkeypatch, tmp_path):
    _stub_names(monkeypatch, {"vell": "Vell", "wren": "Wren"})
    state_path = tmp_path / "schedule.json"
    state_path.write_text(json.dumps(_schedule()), encoding="utf-8")
    feed_path = tmp_path / "nowplaying.json"
    monkeypatch.setattr(nowplaying.settings, "schedule_state_path", state_path)
    monkeypatch.setattr(nowplaying.settings, "nowplaying_feed_path", feed_path)

    returned = nowplaying.write_feed(NOW)

    on_disk = json.loads(feed_path.read_text(encoding="utf-8"))
    assert on_disk == returned
    assert on_disk["now"]["program"] == "First Light"
    assert on_disk["disclosure"] == DISCLOSURE_LINE

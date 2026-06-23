"""Tests for the C2 rolling scheduler (src/scheduler.py).

The load-bearing C2 promises are timing + resilience: top up the buffer to a depth
measured in REAL audio seconds, place segments back-to-back in air order, prune what
has aired, and skip a failing slot without producing dead air. The generation seam
(`make_format_segment`, which would call Claude + TTS) is monkeypatched to fabricate
segments with known durations, so we test the scheduler's control flow + arithmetic,
not the models.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from src import scheduler
from src.segment import Segment

NOW = datetime(2026, 6, 22, 14, 0, 0)


def _fake_generator(tmp_path, *, duration=120.0, fail_formats=()):
    """A stand-in `make_format_segment`: writes a real (tiny) file per call.

    `fail_formats` raises for those format names (an infra failure), so we can test
    the skip-the-slot path. `duration` is the MEASURED length stamped on the segment.
    """
    counter = {"n": 0}

    def _gen(name, now_iso, *, topic=None):
        if name in fail_formats:
            raise RuntimeError(f"simulated generation failure for {name!r}")
        counter["n"] += 1
        path = tmp_path / f"{name}-{counter['n']:03d}.mp3"
        path.write_bytes(b"\x00")  # a real file so existence checks pass
        return Segment(
            id=f"{name}-{counter['n']:03d}",
            format=name,
            length_target_sec=150,
            air_time=now_iso,
            audio_path=str(path),
            actual_duration_sec=duration,
        )

    return _gen


def _wire(monkeypatch, tmp_path, *, depth_hours, rotation, generator):
    monkeypatch.setattr(scheduler, "make_format_segment", generator)
    monkeypatch.setattr(scheduler.settings, "buffer_rotation", rotation)
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", depth_hours)
    monkeypatch.setattr(scheduler.settings, "schedule_topup_max_segments", 100)
    monkeypatch.setattr(scheduler.settings, "schedule_failure_max_retries", 1)
    monkeypatch.setattr(
        scheduler.settings, "schedule_state_path", tmp_path / "schedule.json"
    )
    monkeypatch.setattr(
        scheduler.settings, "schedule_playlist_path", tmp_path / "playlist.txt"
    )


def test_top_up_fills_to_depth_in_air_order(monkeypatch, tmp_path):
    # 0.1h = 360s of depth, 120s per segment -> exactly 3 segments.
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.1,
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )

    upcoming = scheduler.top_up(now=NOW)

    assert len(upcoming) == 3
    # Placed back-to-back on MEASURED duration: each air-time = the previous end.
    starts = [datetime.fromisoformat(e["air_time"]) for e in upcoming]
    assert starts[0] == NOW
    assert starts[1] == NOW + timedelta(seconds=120)
    assert starts[2] == NOW + timedelta(seconds=240)
    # State + playlist were written; the playlist lists each audio path, in order.
    assert (tmp_path / "schedule.json").exists()
    lines = (tmp_path / "playlist.txt").read_text().splitlines()
    assert len(lines) == 3
    assert all(line.endswith(".mp3") for line in lines)


def test_top_up_is_idempotent_when_already_at_depth(monkeypatch, tmp_path):
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.1,
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )

    first = scheduler.top_up(now=NOW)
    # Same `now`: the buffer is already full, so a second run adds nothing.
    second = scheduler.top_up(now=NOW)

    assert len(first) == len(second) == 3
    assert [e["id"] for e in first] == [e["id"] for e in second]


def test_aired_entries_are_pruned(monkeypatch, tmp_path):
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.05,  # 180s -> ~2 fresh 120s segments after pruning
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )
    # Seed an entry that has already fully aired (ended well before NOW).
    old_file = tmp_path / "old.mp3"
    old_file.write_bytes(b"\x00")
    aired = {
        "id": "news-aired",
        "format": "news",
        "audio_path": str(old_file),
        "air_time": (NOW - timedelta(seconds=1000)).isoformat(),
        "actual_duration_sec": 120.0,
        "length_target_sec": 150,
    }
    (tmp_path / "schedule.json").write_text(
        json.dumps({"entries": [aired], "rotation_index": 0})
    )

    upcoming = scheduler.top_up(now=NOW)

    ids = [e["id"] for e in upcoming]
    assert "news-aired" not in ids  # the aired entry is gone
    # And it isn't in the playlist Liquidsoap would air.
    assert str(old_file.resolve()) not in (tmp_path / "playlist.txt").read_text()


def test_failing_format_is_skipped_for_the_next(monkeypatch, tmp_path):
    # `talk` always fails (infra error); `news` works. The scheduler must skip talk
    # and fill the buffer with news rather than crash or stall.
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.1,
        rotation=["talk", "news"],
        generator=_fake_generator(tmp_path, duration=120.0, fail_formats={"talk"}),
    )

    upcoming = scheduler.top_up(now=NOW)

    assert upcoming, "should still produce a buffer despite one format failing"
    assert all(e["format"] == "news" for e in upcoming)


def test_total_generation_failure_stalls_without_dead_air(monkeypatch, tmp_path):
    # Every format fails: the run must stop cleanly (no crash, no infinite loop) and
    # leave an empty playlist — playout's own fallback chain (radio.liq) covers air.
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.1,
        rotation=["talk", "news"],
        generator=_fake_generator(tmp_path, fail_formats={"talk", "news"}),
    )

    upcoming = scheduler.top_up(now=NOW)

    assert upcoming == []
    assert (tmp_path / "playlist.txt").read_text() == ""


def test_unmeasured_entry_falls_back_to_target_for_timing(tmp_path):
    # If a probe failed (actual_duration_sec is None), timing uses length_target_sec
    # rather than treating the segment as zero-length.
    entry = {
        "id": "x",
        "format": "news",
        "audio_path": str(tmp_path / "x.mp3"),
        "air_time": NOW.isoformat(),
        "actual_duration_sec": None,
        "length_target_sec": 150,
    }
    assert scheduler._duration_of(entry) == 150.0
    assert scheduler._end_of(entry) == NOW + timedelta(seconds=150)

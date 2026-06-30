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
    # Sandbox the segment disk so sidecar writes + the C2.5 prune at the end of a
    # top-up never touch the real `segments/` dir. A generous retention keeps the
    # just-generated renders out of the GC's reach in the timing/resilience tests.
    monkeypatch.setattr(scheduler.settings, "segments_dir", tmp_path)
    monkeypatch.setattr(scheduler.settings, "segment_retention_hours", 24.0)
    monkeypatch.setattr(scheduler.settings, "segment_retention_max_gb", None)
    monkeypatch.setattr(
        scheduler.settings, "schedule_state_path", tmp_path / "schedule.json"
    )
    monkeypatch.setattr(
        scheduler.settings, "schedule_playlist_path", tmp_path / "playlist.txt"
    )
    # The C2 tests are about timing/resilience; keep the C3 disclosure ident out of
    # them. The dedicated cadence tests below re-enable it.
    monkeypatch.setattr(scheduler.settings, "disclosure_enabled", False)
    # C4 — top_up refreshes the never-dead fallback assets (real TTS). Neutralize it
    # so the scheduler tests stay free of Claude/TTS; src/fallback has its own tests.
    monkeypatch.setattr(scheduler, "ensure_fallback_assets", lambda **k: {})
    # D5.1 — top_up records each placed segment in the airplay memory + sweeps it
    # (both hit the DB). Neutralize here so the scheduler tests stay hermetic and never
    # commit fabricated rows to a dev DB; src/freshness has its own tests.
    monkeypatch.setattr(scheduler, "record_airplay_features", lambda seg: False)
    monkeypatch.setattr(scheduler, "sweep_airplay", lambda now: 0)


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


def _fake_ident(tmp_path, *, duration=12.0):
    """A stand-in `disclosure_ident_segment`: writes a tiny real file per call."""
    counter = {"n": 0}

    def _gen(now, *, seg_id=None):
        counter["n"] += 1
        path = tmp_path / f"ident-{counter['n']:03d}.mp3"
        path.write_bytes(b"\x00")
        return Segment(
            id=seg_id or f"ident-{counter['n']:03d}",
            format="ident",
            length_target_sec=15,
            air_time=now.isoformat(),
            audio_path=str(path),
            actual_duration_sec=duration,
        )

    return _gen


def test_disclosure_ident_is_woven_on_cadence(monkeypatch, tmp_path):
    # C3: a spoken ident every `disclosure_every_n` CONTENT segments, in air order.
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=500 / 3600,  # 500s: room for 4 content (120s) + 2 idents (12s)
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )
    monkeypatch.setattr(scheduler.settings, "disclosure_enabled", True)
    monkeypatch.setattr(scheduler.settings, "disclosure_every_n", 2)
    monkeypatch.setattr(scheduler, "disclosure_ident_segment", _fake_ident(tmp_path))

    upcoming = scheduler.top_up(now=NOW)

    # Ident lands after every 2 content segments, never at the very start.
    assert [e["format"] for e in upcoming] == [
        "news",
        "news",
        "ident",
        "news",
        "news",
        "ident",
    ]
    # Everything is still placed back-to-back on measured duration (idents included).
    starts = [datetime.fromisoformat(e["air_time"]) for e in upcoming]
    assert starts[2] == NOW + timedelta(seconds=240)  # first ident after 2x120s
    assert starts[3] == NOW + timedelta(seconds=252)  # content resumes after +12s


def test_disclosure_cadence_persists_across_top_ups(monkeypatch, tmp_path):
    # The content-since-ident counter persists, so the cadence doesn't restart each
    # run: a shallow first run leaves the counter mid-cadence, and the next run still
    # weaves the ident once the threshold is crossed.
    monkeypatch.setattr(scheduler, "disclosure_ident_segment", _fake_ident(tmp_path))

    def run(now, depth_hours):
        _wire(
            monkeypatch,
            tmp_path,
            depth_hours=depth_hours,
            rotation=["news"],
            generator=_fake_generator(tmp_path, duration=120.0),
        )
        monkeypatch.setattr(scheduler.settings, "disclosure_enabled", True)
        monkeypatch.setattr(scheduler.settings, "disclosure_every_n", 2)
        return scheduler.top_up(now=now)

    run(NOW, depth_hours=110 / 3600)  # places 1 content (counter -> 1), no ident yet
    state = json.loads((tmp_path / "schedule.json").read_text())
    assert state["content_since_ident"] == 1  # counter carried, not reset

    # 2nd run: a deeper buffer; the carried counter means an ident is woven in.
    formats = [e["format"] for e in run(NOW + timedelta(seconds=120), depth_hours=0.1)]
    assert "ident" in formats


def test_ident_render_failure_does_not_break_the_run(monkeypatch, tmp_path):
    # If the ident render raises (TTS down), the run logs it and keeps placing
    # content rather than crashing or stalling — never dead air for a missing ident.
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.14,
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )
    monkeypatch.setattr(scheduler.settings, "disclosure_enabled", True)
    monkeypatch.setattr(scheduler.settings, "disclosure_every_n", 2)

    def _boom(now, *, seg_id=None):
        raise RuntimeError("simulated TTS failure")

    monkeypatch.setattr(scheduler, "disclosure_ident_segment", _boom)

    upcoming = scheduler.top_up(now=NOW)

    assert upcoming, "content should still fill the buffer when the ident fails"
    assert all(e["format"] == "news" for e in upcoming)


# --- C2.5: disk retention (prune) -------------------------------------------


def _wire_retention(monkeypatch, tmp_path, *, retention_hours=6.0, max_gb=None):
    """Point the retention dials + state/segments dir at a tmp sandbox."""
    monkeypatch.setattr(scheduler.settings, "segments_dir", tmp_path)
    monkeypatch.setattr(
        scheduler.settings, "schedule_state_path", tmp_path / "schedule.json"
    )
    monkeypatch.setattr(scheduler.settings, "segment_retention_hours", retention_hours)
    monkeypatch.setattr(scheduler.settings, "segment_retention_max_gb", max_gb)


def _render(tmp_path, seg_id, *, air_time, duration=120.0, sidecar=True, nbytes=1):
    """Write a fake `<id>.mp3` (+ optional sidecar) as a one-shot render on disk."""
    mp3 = tmp_path / f"{seg_id}.mp3"
    mp3.write_bytes(b"\x00" * nbytes)
    if sidecar:
        (tmp_path / f"{seg_id}.json").write_text(
            json.dumps(
                {
                    "id": seg_id,
                    "format": "news",
                    "audio_path": str(mp3),
                    "air_time": air_time.isoformat(),
                    "actual_duration_sec": duration,
                    "length_target_sec": 150,
                }
            )
        )
    return mp3


def _set_state(tmp_path, entries):
    (tmp_path / "schedule.json").write_text(json.dumps({"entries": entries}))


def test_prune_removes_aged_unreferenced_render_and_sidecar(monkeypatch, tmp_path):
    _wire_retention(monkeypatch, tmp_path, retention_hours=6.0)
    _set_state(tmp_path, [])  # nothing live -> the render is unreferenced
    # Aired 10h ago: air end (start + 120s) is well past the 6h grace window.
    mp3 = _render(tmp_path, "news-old", air_time=NOW - timedelta(hours=10))

    result = scheduler.prune(now=NOW)

    assert not mp3.exists()
    assert not (tmp_path / "news-old.json").exists()
    assert result["files"] == 1


def test_prune_keeps_referenced_upcoming_file(monkeypatch, tmp_path):
    _wire_retention(monkeypatch, tmp_path)
    mp3 = _render(tmp_path, "news-live", air_time=NOW - timedelta(hours=10))
    # Even though it aired long ago by its sidecar, it's still IN the live schedule.
    _set_state(tmp_path, [{"id": "news-live", "audio_path": str(mp3)}])

    scheduler.prune(now=NOW)

    assert mp3.exists(), "a file still in the live schedule must never be deleted"


def test_prune_keeps_file_within_grace_window(monkeypatch, tmp_path):
    _wire_retention(monkeypatch, tmp_path, retention_hours=6.0)
    _set_state(tmp_path, [])
    # Aired only 1h ago — inside the 6h grace window, so it survives.
    mp3 = _render(tmp_path, "news-recent", air_time=NOW - timedelta(hours=1))

    scheduler.prune(now=NOW)

    assert mp3.exists()


def test_prune_protects_shared_disclosure_ident(monkeypatch, tmp_path):
    _wire_retention(monkeypatch, tmp_path)
    _set_state(tmp_path, [])
    # The reused ident clip — no sidecar, very old mtime — must survive by name.
    ident = tmp_path / "ident-disclosure-kokoro-vell_night.mp3"
    ident.write_bytes(b"\x00")
    import os

    old = (NOW - timedelta(days=30)).timestamp()
    os.utime(ident, (old, old))

    scheduler.prune(now=NOW)

    assert ident.exists(), "the shared disclosure ident must never be GC'd"


def test_prune_uses_mtime_when_no_sidecar(monkeypatch, tmp_path):
    _wire_retention(monkeypatch, tmp_path, retention_hours=6.0)
    _set_state(tmp_path, [])
    # A pre-C2.5 render with no sidecar: age falls back to the file's mtime.
    mp3 = _render(tmp_path, "legacy", air_time=NOW, sidecar=False)
    import os

    old = (NOW - timedelta(hours=10)).timestamp()
    os.utime(mp3, (old, old))

    scheduler.prune(now=NOW)

    assert not mp3.exists()


def test_prune_max_gb_backstop_evicts_oldest_within_grace(monkeypatch, tmp_path):
    # Two recent (in-grace) ~1 MB renders. Cap sits between one and two of them, so
    # the backstop must evict the OLDER even though it's inside the grace window.
    one_mb = 1_000_000
    cap_bytes = 1_500_000  # room for one render, not two
    _wire_retention(
        monkeypatch, tmp_path, retention_hours=6.0, max_gb=cap_bytes / 1024**3
    )
    _set_state(tmp_path, [])
    older = _render(tmp_path, "a", air_time=NOW - timedelta(hours=2), nbytes=one_mb)
    newer = _render(tmp_path, "b", air_time=NOW - timedelta(hours=1), nbytes=one_mb)

    scheduler.prune(now=NOW)

    # The oldest is evicted to get under the cap; the newest is kept.
    assert not older.exists()
    assert newer.exists()


def test_top_up_writes_sidecar_for_each_render(monkeypatch, tmp_path):
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.05,
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )  # _wire already sandboxes segments_dir + retention onto tmp_path

    upcoming = scheduler.top_up(now=NOW)

    for e in upcoming:
        sidecar = tmp_path / f"{e['id']}.json"
        assert sidecar.exists(), f"expected a sidecar for {e['id']}"
        data = json.loads(sidecar.read_text())
        assert data["air_time"] == e["air_time"]


def test_prune_protects_evergreen_pool(monkeypatch, tmp_path):
    # C4: the pre-rendered evergreen pool clips are reused render-once fallback
    # audio (like the ident) — exempt by their `evergreen-` prefix, never GC'd.
    _wire_retention(monkeypatch, tmp_path)
    _set_state(tmp_path, [])
    pool = tmp_path / "evergreen-0-kokoro-vell_night.mp3"
    pool.write_bytes(b"\x00")
    import os

    old = (NOW - timedelta(days=30)).timestamp()
    os.utime(pool, (old, old))

    scheduler.prune(now=NOW)

    assert pool.exists(), "the evergreen fallback pool must never be GC'd"


def test_top_up_records_heartbeat(monkeypatch, tmp_path):
    # C4: every completed top-up stamps `last_topup_at` so health.check_last_run
    # can detect a generator that has stopped running.
    _wire(
        monkeypatch,
        tmp_path,
        depth_hours=0.05,
        rotation=["news"],
        generator=_fake_generator(tmp_path, duration=120.0),
    )

    scheduler.top_up(now=NOW)

    state = json.loads((tmp_path / "schedule.json").read_text())
    assert state["last_topup_at"] == NOW.isoformat()


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

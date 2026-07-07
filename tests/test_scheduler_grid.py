"""Tests for D6.2 — the scheduler wired to the programming grid.

The C2 rolling-buffer machinery (depth, back-to-back placement, prune, never-dead
skip) is covered in test_scheduler.py on the flat rollback path. Here we assert the
D6.2 additions: the scheduler airs the *grid's* programs — following each program's
CLOCK (run-lengths, pinned top-of-hour slots) and routing the program's HOSTS into
generation — with the never-dead machinery intact and a default fallback so a gap
never stalls. Generation is monkeypatched (no Claude/TTS); we inspect what the
scheduler CHOSE.
"""

from __future__ import annotations

from datetime import datetime

from src import scheduler
from src.segment import Segment
from src.world import programming

# A fixture grid: one program on a music-heavy clock with a top-of-hour news pin,
# tiling the whole week so every slot resolves (no default fallback unless asked).
_GRID = """
programs:
  test_show:
    name: "Test Show"
    hosts: [wren, vell]
    framing: solo
    clock: [talk, music x2, news@:00]
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk]
grid:
  daily:
    "00:00-24:00": test_show
"""

# A grid with a deliberate hole (Mon 13:00-15:00 untiled) to exercise the default.
_GRID_WITH_GAP = """
programs:
  daytime:
    name: "Daytime"
    hosts: [wren, vell]
    framing: solo
    clock: [talk]
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [news]
grid:
  daily:
    "00:00-13:00": daytime
    "15:00-24:00": daytime
"""


def _recording_generator(tmp_path, *, duration=120.0):
    """A stand-in `make_format_segment` that records (format, speakers) per call."""
    calls: list[dict] = []

    def _gen(name, now_iso, *, topic=None, speakers=None, flow=None):
        calls.append({"format": name, "speakers": speakers, "air_time": now_iso})
        path = tmp_path / f"{name}-{len(calls):03d}.mp3"
        path.write_bytes(b"\x00")
        return Segment(
            id=f"{name}-{len(calls):03d}",
            format=name,
            length_target_sec=150,
            air_time=now_iso,
            audio_path=str(path),
            actual_duration_sec=duration,
        )

    return calls, _gen


def _wire_grid(monkeypatch, tmp_path, *, grid_text, depth_hours, generator):
    """Wire the scheduler for a grid-driven run: fixture grid + hermetic effects."""
    grid_path = tmp_path / "grid.yaml"
    grid_path.write_text(grid_text, encoding="utf-8")
    monkeypatch.setattr(scheduler.settings, "programming_grid_path", grid_path)
    programming.reload()

    monkeypatch.setattr(scheduler, "make_format_segment", generator)
    monkeypatch.setattr(scheduler.settings, "programming_enabled", True)
    monkeypatch.setattr(scheduler.settings, "buffer_rotation", ["talk"])
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", depth_hours)
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
    # D7.2 — keep the production placements out of the D6 grid-timing tests (they
    # resolve real curated assets/ clips); the D7 placement tests cover them.
    monkeypatch.setattr(scheduler.settings, "production_ident_every_n", 0)
    monkeypatch.setattr(scheduler.settings, "production_theme_at_boundary", False)
    monkeypatch.setattr(scheduler.settings, "production_sting_before_news", False)
    monkeypatch.setattr(scheduler.settings, "production_bedded_programs", [])
    monkeypatch.setattr(scheduler, "ensure_fallback_assets", lambda **k: {})
    monkeypatch.setattr(scheduler, "record_airplay_features", lambda seg: False)
    monkeypatch.setattr(scheduler, "sweep_airplay", lambda now: 0)


def teardown_function(_):
    programming.reload()  # never leak the fixture grid into other test modules


# 2026-06-22 is a Monday. 14:15 avoids the top-of-hour pin firing immediately.
def _mon(hour, minute=0):
    return datetime(2026, 6, 22, hour, minute)


# --- The scheduler follows the program's clock ------------------------------


def test_scheduler_airs_the_program_clock_with_run_lengths(monkeypatch, tmp_path):
    calls, gen = _recording_generator(tmp_path)
    # depth 0.2h = 720s; at 120s/segment => 6 segments, all inside hour 14 (no pin).
    _wire_grid(monkeypatch, tmp_path, grid_text=_GRID, depth_hours=0.2, generator=gen)

    scheduler.top_up(now=_mon(14, 15))

    formats = [c["format"] for c in calls]
    # clock [talk, music x2, news@:00] -> sequence talk, music, music (news pinned to
    # the hour, which 14:15+ hasn't crossed), so the music sweep airs two in a row.
    assert formats == ["talk", "music", "music", "talk", "music", "music"]


def test_pinned_news_lands_at_the_top_of_the_hour(monkeypatch, tmp_path):
    calls, gen = _recording_generator(tmp_path)
    # Start at 14:50 with enough depth to cross 15:00; news must appear right after.
    _wire_grid(monkeypatch, tmp_path, grid_text=_GRID, depth_hours=0.4, generator=gen)

    scheduler.top_up(now=_mon(14, 50))

    news = [c for c in calls if c["format"] == "news"]
    assert news, "the pinned news never aired"
    first_news = news[0]
    aired = datetime.fromisoformat(first_news["air_time"])
    assert aired.hour == 15  # it landed in the new hour, not before the boundary
    assert aired.minute < 15  # ...near the top of it


def test_program_hosts_are_routed_into_generation(monkeypatch, tmp_path):
    calls, gen = _recording_generator(tmp_path)
    _wire_grid(monkeypatch, tmp_path, grid_text=_GRID, depth_hours=0.2, generator=gen)

    scheduler.top_up(now=_mon(14, 15))

    by_format = {c["format"]: c["speakers"] for c in calls}
    # test_show hosts are [wren, vell]: talk (needs 2) gets both, lead-first; the
    # single-voice music desk gets the lead only — the grid drives who's on air.
    assert by_format["talk"] == ["wren", "vell"]
    assert by_format["music"] == ["wren"]


def test_clock_cursor_persists_across_top_up_runs(monkeypatch, tmp_path):
    calls, gen = _recording_generator(tmp_path)
    # Tiny depth: one segment per run, so the sequence must advance via persisted state.
    _wire_grid(monkeypatch, tmp_path, grid_text=_GRID, depth_hours=0.03, generator=gen)

    scheduler.top_up(now=_mon(14, 15))  # -> talk (seq 0)
    n1 = len(calls)
    scheduler.top_up(now=_mon(14, 15))  # buffer already at depth from run 1
    # Force the second run to place by asking from later (buffer drained past).
    scheduler.top_up(now=_mon(14, 40))  # -> music (seq continued, not reset to talk)

    formats = [c["format"] for c in calls]
    assert formats[0] == "talk"
    assert formats[n1] == "music"  # the next placed slot continued the sequence


def test_a_gap_falls_back_to_default_and_never_stalls(monkeypatch, tmp_path):
    calls, gen = _recording_generator(tmp_path)
    _wire_grid(
        monkeypatch, tmp_path, grid_text=_GRID_WITH_GAP, depth_hours=0.2, generator=gen
    )

    # 13:00-15:00 is untiled -> program_for returns `default` (rotation [news]).
    upcoming = scheduler.top_up(now=_mon(13, 15))

    assert upcoming, "the default program must keep the buffer filled (never a stall)"
    assert all(c["format"] == "news" for c in calls)  # default rotation is [news]
    assert all(e["program"] == "default" for e in upcoming)


def test_schedule_entries_carry_the_program_for_the_console_feed(monkeypatch, tmp_path):
    calls, gen = _recording_generator(tmp_path)
    _wire_grid(monkeypatch, tmp_path, grid_text=_GRID, depth_hours=0.1, generator=gen)

    upcoming = scheduler.top_up(now=_mon(14, 15))

    assert upcoming
    assert all(e["program"] == "test_show" for e in upcoming)
    assert all(e["program_name"] == "Test Show" for e in upcoming)

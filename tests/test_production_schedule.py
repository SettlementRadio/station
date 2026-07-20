"""Tests for D7.2/D7.3 in the scheduler loop — the grid places the sonic identity.

Mirrors test_scheduler_grid.py's harness (stubbed generation, fixture grid,
hermetic paths) with the production dials ON and a fixture `assets/` tree
(conftest.assets_tree) standing in for the curated media, so the real placement
code runs without depending on real clips: a program boundary opens with the
handover sting + theme, the C8 sting precedes the news, the A1 ident airs on its
cadence, and the persisted boundary state prevents duplicate themes.
"""

from __future__ import annotations

from datetime import datetime

from src import scheduler
from src.segment import Segment
from src.world import programming

# Program ids deliberately match the D7.0 registry (PROGRAM_THEMES keys) so the
# real mapping resolves against the fixture assets tree. first_light is a
# handover program -> its boundary opens with the B6 sting then the B5 theme.
_GRID = """
programs:
  long_night:
    name: "The Long Night"
    hosts: [vell, wren]
    framing: solo
    daypart: deep night
    clock: [talk]
  first_light:
    name: "First Light"
    hosts: [wren, vell]
    framing: handover
    daypart: first light
    clock: [talk, news@:00]
    energy: bright
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk]
grid:
  daily:
    "22:00-05:00": long_night
    "05:00-22:00": first_light
"""


def _generator(tmp_path, *, duration=600.0):
    def _gen(name, now_iso, *, topic=None, speakers=None, flow=None):
        seg_id = f"{name}-{now_iso[11:19].replace(':', '')}"
        path = tmp_path / f"{seg_id}.mp3"
        path.write_bytes(b"\x00")
        return Segment(
            id=seg_id,
            format=name,
            length_target_sec=600,
            air_time=now_iso,
            audio_path=str(path),
            actual_duration_sec=duration,
        )

    return _gen


def _wire(monkeypatch, tmp_path, *, depth_hours=0.8, ident_every=0):
    grid_path = tmp_path / "grid.yaml"
    grid_path.write_text(_GRID, encoding="utf-8")
    monkeypatch.setattr(scheduler.settings, "programming_grid_path", grid_path)
    programming.reload()

    monkeypatch.setattr(scheduler, "make_format_segment", _generator(tmp_path))
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
    # The D7.2 placements UNDER TEST — on (beds stay off; they have direct tests).
    monkeypatch.setattr(scheduler.settings, "production_theme_at_boundary", True)
    monkeypatch.setattr(scheduler.settings, "production_sting_before_news", True)
    monkeypatch.setattr(scheduler.settings, "production_ident_every_n", ident_every)
    monkeypatch.setattr(scheduler.settings, "production_bedded_programs", [])
    monkeypatch.setattr(scheduler, "ensure_fallback_assets", lambda **k: {})
    monkeypatch.setattr(scheduler, "record_airplay_features", lambda seg: False)
    monkeypatch.setattr(scheduler, "sweep_airplay", lambda now: 0)


def teardown_function(_):
    programming.reload()  # never leak the fixture grid into other test modules


def test_boundary_opens_with_handover_sting_then_theme(
    monkeypatch, tmp_path, assets_tree
):
    _wire(monkeypatch, tmp_path)
    upcoming = scheduler.top_up(datetime(2026, 7, 5, 4, 40))

    ids = [e["id"] for e in upcoming]
    # No theme opened the FIRST program (a boundary is a change, not a start)…
    assert not ids[0].startswith(("theme-", "sting-"))
    # …and the 05:00 crossing opened first_light with sting -> theme, in order.
    sting_i = next(i for i, x in enumerate(ids) if x.startswith("sting-handover-"))
    theme_i = next(i for i, x in enumerate(ids) if x.startswith("theme-first_light-"))
    assert theme_i == sting_i + 1
    assert upcoming[sting_i]["air_time"].startswith("2026-07-05T05:00")
    # The clips are reused curated assets (GC-safe by location), not renders.
    assert upcoming[theme_i]["audio_path"].startswith(str(assets_tree))


def test_news_sting_immediately_precedes_the_bulletin(
    monkeypatch, tmp_path, assets_tree
):
    _wire(monkeypatch, tmp_path)
    upcoming = scheduler.top_up(datetime(2026, 7, 5, 4, 40))

    ids = [e["id"] for e in upcoming]
    news_i = next(i for i, x in enumerate(ids) if x.startswith("news-"))
    assert ids[news_i - 1].startswith("sting-news-")
    # The bulletin was re-pinned AFTER its sting (contiguous timing stays honest).
    assert upcoming[news_i]["air_time"] > upcoming[news_i - 1]["air_time"]


def test_station_ident_airs_on_its_cadence(monkeypatch, tmp_path, assets_tree):
    _wire(monkeypatch, tmp_path, ident_every=2)
    upcoming = scheduler.top_up(datetime(2026, 7, 5, 4, 40))

    ids = [e["id"] for e in upcoming]
    ident_i = next(i for i, x in enumerate(ids) if x.startswith("ident-station-"))
    content_before = [
        x for x in ids[:ident_i] if not x.startswith(("sting-", "theme-", "ident-"))
    ]
    assert len(content_before) == 2  # fired after exactly N content segments


def test_boundary_does_not_refire_within_the_same_program(
    monkeypatch, tmp_path, assets_tree
):
    _wire(monkeypatch, tmp_path)
    scheduler.top_up(datetime(2026, 7, 5, 4, 40))
    # Second run, deeper, still inside first_light: no second theme.
    monkeypatch.setattr(scheduler.settings, "buffer_depth_hours", 1.6)
    upcoming = scheduler.top_up(datetime(2026, 7, 5, 5, 15))
    themes = [e for e in upcoming if e["id"].startswith("theme-")]
    assert len(themes) <= 1


# --- R3.0: two adjacent bespoke-less programs never repeat the same fallback --

_REPEAT_GRID = """
programs:
  show_a:
    name: "Show A"
    hosts: [vell, wren]
    framing: solo
    daypart: x
    clock: [talk]
  show_b:
    name: "Show B"
    hosts: [vell, wren]
    framing: solo
    daypart: x
    clock: [talk]
  show_c:
    name: "Show C"
    hosts: [vell, wren]
    framing: solo
    daypart: x
    clock: [talk]
  default:
    name: "Settlement Radio"
    hosts: [vell, wren]
    framing: legacy
    rotation: [talk]
grid:
  daily:
    "00:00-00:10": show_a
    "00:10-00:20": show_b
    "00:20-24:00": show_c
"""


def test_boundary_theme_does_not_repeat_across_adjacent_fallback_shows(
    monkeypatch, tmp_path, assets_tree, audio_factory
):
    # None of show_a/b/c has a bespoke theme or override, so all three fall back
    # to the same c9_talk.mp3 — the FIRST boundary (a -> b) still opens on it
    # (nothing played yet to repeat), but the SECOND (b -> c) must skip it rather
    # than play the identical clip twice in a row.
    _wire(monkeypatch, tmp_path, depth_hours=0.5)
    # _wire() writes its own shared _GRID fixture — overwrite it with this test's
    # grid at the SAME path and reload again, so this grid wins.
    (tmp_path / "grid.yaml").write_text(_REPEAT_GRID, encoding="utf-8")
    programming.reload()
    clip = audio_factory(seconds=0.5)
    (assets_tree / "themes" / "c9_talk.mp3").write_bytes(clip.read_bytes())

    upcoming = scheduler.top_up(datetime(2026, 7, 5, 0, 0))

    ids = [e["id"] for e in upcoming]
    theme_ids = [x for x in ids if x.startswith("theme-")]
    assert len(theme_ids) == 1  # only the a->b boundary got one; b->c was skipped
    assert theme_ids[0].startswith("theme-show_b-")
    assert any(x.startswith("talk-") for x in ids[ids.index(theme_ids[0]) :])


# --- R2.3: the A4 sweeper joins consecutive flagship items -------------------


def test_sweeper_joins_flagship_items_energy_matched(
    monkeypatch, tmp_path, assets_tree
):
    _wire(monkeypatch, tmp_path, depth_hours=0.8)
    monkeypatch.setattr(
        scheduler.settings, "production_sweeper_programs", ["first_light"]
    )

    # 06:10, inside first_light, away from any boundary or pin: pure talk items.
    upcoming = scheduler.top_up(now=datetime(2026, 7, 5, 6, 10))

    ids = [e["id"] for e in upcoming]
    sweeps = [i for i, x in enumerate(ids) if x.startswith("sting-sweeper-")]
    assert sweeps, "no sweeper joined the fast items"
    # Never before the FIRST content item of the run (that join belongs to the
    # theme/boundary machinery), and always immediately followed by a talk item.
    content_before_first_sweep = [
        x for x in ids[: sweeps[0]] if not x.startswith(("sting-", "theme-", "ident-"))
    ]
    assert content_before_first_sweep, "a sweeper aired before any content"
    for i in sweeps:
        assert ids[i + 1].startswith("talk-"), "a sweeper must join INTO an item"
    # Energy-matched: first_light is `bright` -> the bright A4 tier.
    sweep_entries = [e for e in upcoming if e["id"].startswith("sting-sweeper-")]
    assert all("a4_sweeper_bright" in e["audio_path"] for e in sweep_entries)


def test_no_sweepers_for_programs_off_the_dial(monkeypatch, tmp_path, assets_tree):
    _wire(monkeypatch, tmp_path, depth_hours=0.8)
    monkeypatch.setattr(scheduler.settings, "production_sweeper_programs", [])

    upcoming = scheduler.top_up(now=datetime(2026, 7, 5, 6, 10))

    assert not [e for e in upcoming if e["id"].startswith("sting-sweeper-")]

"""Tests for the D7 production layer: the mixer, the clip registry, beds, GC safety.

Surgical per the repo standard: the mixing primitive's duration accounting and its
never-silence fallback (a mix failure must degrade to clean speech), the D7.0
registry's resolve-or-degrade contract, the doubly-opt-in bed selection, and the
load-bearing invariant that curated `assets/` media is never in the disk GC's
candidate set. Real (tiny, generated) audio; never the real curated media.
"""

from __future__ import annotations

import os
import time
from datetime import datetime

import pytest
from src import scheduler
from src.config import settings
from src.production import media, mix, placement
from src.providers import tts
from src.segment import Segment
from src.world.programming import ClockStep, Program

NOW = datetime(2026, 7, 5, 3, 0)


def _program(pid="long_night", framing="solo", daypart="deep night") -> Program:
    return Program(
        id=pid,
        name=pid.replace("_", " ").title(),
        hosts=("vell", "wren"),
        framing=framing,
        daypart=daypart,
        clock=(),
        rotation=(),
    )


# --- D7.1: the mixing primitive ----------------------------------------------


def test_duck_bed_output_matches_speech_duration(audio_factory, tmp_path):
    # A 1s bed must LOOP under 3s of speech and the mix must end with the speech.
    speech = str(audio_factory(seconds=3.0, rate=24_000, channels=1))
    bed = str(audio_factory(seconds=1.0))
    out = mix.duck_bed_under(speech, bed, str(tmp_path / "bedded.mp3"))
    assert out.endswith("bedded.mp3")
    assert tts.probe_duration(out) == pytest.approx(3.0, abs=0.2)


def test_duck_bed_failure_falls_back_to_clean_speech(audio_factory, tmp_path):
    speech = str(audio_factory(seconds=1.0, rate=24_000, channels=1))
    out = mix.duck_bed_under(
        speech, str(tmp_path / "no-such-bed.mp3"), str(tmp_path / "out.mp3")
    )
    assert out == speech  # the segment airs dry — never silence, never a raise


def test_attach_sting_prepends_and_appends(audio_factory, tmp_path):
    clip = str(audio_factory(seconds=2.0, rate=24_000, channels=1))
    sting = str(audio_factory(seconds=0.5))
    for position in ("before", "after"):
        out = mix.attach_sting(
            clip, sting, str(tmp_path / f"stung-{position}.mp3"), position=position
        )
        assert tts.probe_duration(out) == pytest.approx(2.5, abs=0.2)


def test_attach_sting_failure_falls_back_to_the_clip(audio_factory, tmp_path):
    clip = str(audio_factory(seconds=1.0))
    out = mix.attach_sting(clip, str(tmp_path / "gone.mp3"), str(tmp_path / "out.mp3"))
    assert out == clip


def test_attach_sting_rejects_a_bad_position(audio_factory, tmp_path):
    clip = str(audio_factory(seconds=1.0))
    with pytest.raises(ValueError):
        mix.attach_sting(clip, clip, str(tmp_path / "x.mp3"), position="middle")


def test_join_clips_joins_heterogeneous_audio_in_full(audio_factory, tmp_path):
    # Mono 24k speech + stereo 44.1k clips — the exact D7.4 stitch shape.
    parts = [
        str(audio_factory(seconds=1.0, rate=24_000, channels=1)),
        str(audio_factory(seconds=0.5)),
        str(audio_factory(seconds=2.0)),
    ]
    out = mix.join_clips(parts, str(tmp_path / "joined.mp3"))
    assert tts.probe_duration(out) == pytest.approx(3.5, abs=0.25)


def test_join_clips_refuses_an_empty_list(tmp_path):
    with pytest.raises(ValueError):
        mix.join_clips([], str(tmp_path / "x.mp3"))


# --- D7.0: the clip registry resolves or degrades ------------------------------


def test_media_resolves_registered_clips(assets_tree):
    assert media.theme_for_program("long_night").name == "b4_night.mp3"
    assert media.sting("news").name == "c8_news_sting.mp3"
    assert media.ident("signature").name == "a1_signature.mp3"


def test_media_missing_file_degrades_to_none(assets_tree):
    # advisory: a registered sting whose file is absent from the partial fixture.
    assert media.sting("advisory") is None
    # a program with neither an override nor a convention file on disk.
    assert media.theme_for_program("nonexistent_show") is None
    assert media.sting("not-a-registered-name") is None


def test_theme_resolves_by_convention(assets_tree, audio_factory):
    # A program with no override resolves themes/<program_id>.mp3 by convention —
    # the contract with JINGLE_PROMPTS_2.md: drop the clip in, it wires itself.
    clip = audio_factory(seconds=0.5)
    (assets_tree / "themes" / "the_gallery.mp3").write_bytes(clip.read_bytes())
    assert media.theme_for_program("the_gallery").name == "the_gallery.mp3"


def test_theme_override_wins_over_convention(assets_tree, audio_factory):
    # the_circuit reuses c12_games via an override — it wins even when a
    # convention file also exists on disk.
    clip = audio_factory(seconds=0.5)
    (assets_tree / "themes" / "c12_games.mp3").write_bytes(clip.read_bytes())
    (assets_tree / "themes" / "the_circuit.mp3").write_bytes(clip.read_bytes())
    assert media.theme_for_program("the_circuit").name == "c12_games.mp3"


def _prog_with_clock(*formats: ClockStep, pid="the_new_show") -> Program:
    return Program(
        id=pid,
        name="A New Show",
        hosts=("thorn", "wren"),
        framing="ensemble",
        daypart="afternoon",
        clock=tuple(formats),
        rotation=(),
    )


def test_boundary_theme_falls_back_to_format(assets_tree, audio_factory):
    # No bespoke/override theme for this program → open on its first content
    # format's theme (talk → C9, news → C7); a marker step is skipped.
    clip = audio_factory(seconds=0.5)
    (assets_tree / "themes" / "c9_talk.mp3").write_bytes(clip.read_bytes())
    (assets_tree / "themes" / "c7_news.mp3").write_bytes(clip.read_bytes())

    talk_first = _prog_with_clock(
        ClockStep(format="sting", is_marker=True), ClockStep(format="talk")
    )
    seg = placement.program_theme_segment(talk_first, NOW)
    assert seg is not None and seg.audio_path.endswith("c9_talk.mp3")

    news_first = _prog_with_clock(
        ClockStep(format="news", pin_minute=0), ClockStep(format="talk")
    )
    seg = placement.program_theme_segment(news_first, NOW)
    assert seg is not None and seg.audio_path.endswith("c7_news.mp3")

    # A music-first show uses the talk theme (music opens with a bumper sting).
    music_first = _prog_with_clock(ClockStep(format="music"))
    seg = placement.program_theme_segment(music_first, NOW)
    assert seg is not None and seg.audio_path.endswith("c9_talk.mp3")


# --- D7.3: bed selection is doubly opt-in + honest re-measurement --------------


def test_bed_selection_is_doubly_opt_in(assets_tree, monkeypatch):
    monkeypatch.setattr(settings, "production_bedded_programs", ["long_night"])
    monkeypatch.setattr(settings, "production_bedded_formats", ["talk"])
    assert placement.bed_clip_for("long_night", "talk").name == "b4_night_bed.mp3"
    assert placement.bed_clip_for("long_night", "news") is None  # news stays dry
    assert placement.bed_clip_for("morning_currents", "talk") is None  # not listed


def test_apply_bed_mixes_and_restamps_the_final_audio(
    assets_tree, audio_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    monkeypatch.setattr(settings, "production_bedded_programs", ["long_night"])
    monkeypatch.setattr(settings, "production_bedded_formats", ["talk"])
    speech = audio_factory(seconds=2.0, rate=24_000, channels=1)
    seg = Segment(
        id="talk-t1",
        format="talk",
        length_target_sec=120,
        air_time=NOW.isoformat(),
        audio_path=str(speech),
        actual_duration_sec=2.0,
    )
    seg = placement.apply_bed(seg, _program())
    assert seg.audio_path.endswith("talk-t1-bedded.mp3")
    assert seg.meta["bed"] == "b4_night_bed.mp3"
    # Honest accounting: re-measured on the FINAL mixed audio.
    assert seg.actual_duration_sec == pytest.approx(2.0, abs=0.2)


def test_apply_bed_leaves_dry_formats_untouched(assets_tree, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "production_bedded_programs", ["long_night"])
    monkeypatch.setattr(settings, "production_bedded_formats", ["talk"])
    seg = Segment(
        id="news-t1",
        format="news",
        length_target_sec=120,
        air_time=NOW.isoformat(),
        audio_path="/tmp/whatever.mp3",
    )
    out = placement.apply_bed(seg, _program())
    assert out.audio_path == "/tmp/whatever.mp3" and "bed" not in out.meta


# --- D7.0: curated media is never in the GC's path -----------------------------


def test_prune_never_touches_assets(assets_tree, audio_factory, tmp_path, monkeypatch):
    """The C2.5 GC only scans `segments_dir`; curated `assets/` audio survives any
    retention policy — even a zero-hour window that collects every aired render."""
    seg_dir = tmp_path / "segments"
    seg_dir.mkdir()
    monkeypatch.setattr(settings, "segments_dir", seg_dir)
    monkeypatch.setattr(settings, "schedule_state_path", tmp_path / "schedule.json")
    monkeypatch.setattr(settings, "segment_retention_hours", 0.0)
    monkeypatch.setattr(settings, "segment_retention_max_gb", None)

    # An aired, unreferenced one-shot render (old mtime; no sidecar) — GC bait.
    render = seg_dir / "talk-old.mp3"
    render.write_bytes(audio_factory(seconds=0.5).read_bytes())
    old = time.time() - 48 * 3600
    os.utime(render, (old, old))

    asset_clip = assets_tree / "themes" / "b4_night.mp3"
    assert asset_clip.exists()

    result = scheduler.prune(datetime.now())

    assert not render.exists()  # the one-shot render was collected…
    assert asset_clip.exists()  # …and the curated clip was never a candidate
    assert result["files"] == 1

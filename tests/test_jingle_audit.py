"""Tests for the R3.0 jingle placement audit (`src/production/audit.py`).

Two layers, mirroring how `test_acceptance.py` trusts its own gate:

* the five DYNAMIC properties are pure list-of-dicts checkers — unit-tested on
  both a clean timeline AND a PLANTED defect (a silent boundary, an unstung
  bulletin, an unbracketed break, a back-to-back repeat). A checker that can't
  fail is worthless, so the failing cases are the point.
* the STATIC mapping (`_static_theme_mapping`) is exercised against a small
  fixture grid + the `assets_tree` fixture — the real `placement`/`media` code
  path, never the operator's curated media — covering the four resolution
  kinds (override / bespoke / fallback / missing).
* one end-to-end `run_audit` call drives the real scheduler on a short,
  isolated window against a live Postgres (skipped cleanly without one).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from src.production import audit
from src.world.programming import ClockStep, Program


def _entry(seg_id, fmt, air_time, *, program=None, audio_path=None):
    return {
        "id": seg_id,
        "format": fmt,
        "program": program,
        "air_time": air_time,
        "audio_path": audio_path or f"/assets/{seg_id}.mp3",
    }


# --- _kind_of -------------------------------------------------------------


def test_kind_of_parses_theme_and_sting_ids():
    assert audit._kind_of(
        _entry("theme-the_gallery-20260701T000000", "theme", "t")
    ) == (
        "theme",
        "the_gallery",
    )
    assert audit._kind_of(_entry("sting-break_in-20260701T000000", "sting", "t")) == (
        "sting",
        "break_in",
    )
    assert audit._kind_of(
        _entry("talk-000000", "talk", "t", program="the_gallery")
    ) == ("", None)
    assert audit._kind_of(None) == ("", None)


# --- _check_boundary_themes -------------------------------------------------


def test_boundary_themes_passes_when_every_change_is_themed():
    timeline = [
        _entry("talk-0", "talk", "T0", program="show_a"),
        _entry("theme-show_b-1", "theme", "T1", audio_path="/a/show_b.mp3"),
        _entry("talk-1", "talk", "T2", program="show_b"),
    ]
    r = audit._check_boundary_themes(
        timeline, {"show_a": "show_a.mp3", "show_b": "show_b.mp3"}
    )
    assert r.ok


def test_boundary_themes_fails_on_a_silent_boundary():
    timeline = [
        _entry("talk-0", "talk", "T0", program="show_a"),
        _entry("talk-1", "talk", "T2", program="show_b"),  # no theme fired
    ]
    r = audit._check_boundary_themes(
        timeline, {"show_a": "show_a.mp3", "show_b": "show_b.mp3"}
    )
    assert not r.ok
    assert "show_a -> show_b" in r.detail


def test_boundary_themes_exempts_the_very_first_program():
    timeline = [_entry("talk-0", "talk", "T0", program="show_a")]
    r = audit._check_boundary_themes(timeline, {"show_a": "show_a.mp3"})
    assert r.ok


def test_boundary_themes_exempts_a_deliberate_repeat_skip():
    # show_a and show_b resolve to the SAME fallback clip — no theme firing at
    # that boundary is the CORRECT R3.0 behaviour (placement.py's avoid_repeat
    # guard), not a placement miss.
    timeline = [
        _entry("talk-0", "talk", "T0", program="show_a"),
        _entry("talk-1", "talk", "T2", program="show_b"),
    ]
    r = audit._check_boundary_themes(
        timeline, {"show_a": "c9_talk.mp3", "show_b": "c9_talk.mp3"}
    )
    assert r.ok


# --- _check_news_pins --------------------------------------------------------


def test_news_pins_passes_when_stung():
    timeline = [_entry("sting-news-0", "sting", "T0"), _entry("news-0", "news", "T1")]
    assert audit._check_news_pins(timeline).ok


def test_news_pins_fails_on_an_unstung_bulletin():
    timeline = [_entry("news-0", "news", "T0")]
    r = audit._check_news_pins(timeline)
    assert not r.ok


# --- _check_handover_stings ---------------------------------------------------


def _fake_all_programs(monkeypatch):
    monkeypatch.setattr(
        audit.programming,
        "all_programs",
        lambda: {
            "handoff_show": SimpleNamespace(framing="handover"),
            "show_a": SimpleNamespace(framing="solo"),
        },
    )


def test_handover_stings_passes_when_preceded(monkeypatch):
    _fake_all_programs(monkeypatch)
    timeline = [
        _entry("sting-handover-0", "sting", "T0"),
        _entry("theme-handoff_show-1", "theme", "T1", audio_path="/a/b5.mp3"),
    ]
    assert audit._check_handover_stings(timeline).ok


def test_handover_stings_fails_when_missing(monkeypatch):
    _fake_all_programs(monkeypatch)
    timeline = [
        _entry("theme-handoff_show-1", "theme", "T1", audio_path="/a/b5.mp3"),
    ]
    r = audit._check_handover_stings(timeline)
    assert not r.ok


def test_handover_stings_ignores_non_handover_themes(monkeypatch):
    _fake_all_programs(monkeypatch)
    timeline = [_entry("theme-show_a-0", "theme", "T0", audio_path="/a/show_a.mp3")]
    r = audit._check_handover_stings(timeline)
    assert r.ok and "0 handover" in r.detail


# --- _check_break_brackets ----------------------------------------------------


def test_break_brackets_passes_when_bracketed():
    timeline = [
        _entry("sting-break_in-0", "sting", "T0"),
        _entry("commercial-0", "commercial", "T1"),
        _entry("promo-0", "promo", "T2"),
        _entry("sting-break_out-0", "sting", "T3"),
    ]
    assert audit._check_break_brackets(timeline).ok


def test_break_brackets_fails_when_the_opener_is_missing():
    timeline = [
        _entry("commercial-0", "commercial", "T0"),
        _entry("sting-break_out-0", "sting", "T1"),
    ]
    assert not audit._check_break_brackets(timeline).ok


def test_break_brackets_fails_when_the_closer_is_missing():
    timeline = [
        _entry("sting-break_in-0", "sting", "T0"),
        _entry("commercial-0", "commercial", "T1"),
    ]
    assert not audit._check_break_brackets(timeline).ok


# --- _check_no_theme_repeat ----------------------------------------------------


def test_no_theme_repeat_passes_on_distinct_clips():
    timeline = [
        _entry("theme-show_a-0", "theme", "T0", audio_path="/a/show_a.mp3"),
        _entry("theme-show_b-1", "theme", "T1", audio_path="/a/show_b.mp3"),
    ]
    assert audit._check_no_theme_repeat(timeline).ok


def test_no_theme_repeat_fails_on_a_back_to_back_repeat():
    timeline = [
        _entry(
            "theme-show_a-0",
            "theme",
            "T0",
            program="show_a",
            audio_path="/a/c9_talk.mp3",
        ),
        _entry(
            "theme-show_b-1",
            "theme",
            "T1",
            program="show_b",
            audio_path="/a/c9_talk.mp3",
        ),
    ]
    r = audit._check_no_theme_repeat(timeline)
    assert not r.ok
    assert "show_a -> show_b" in r.detail


# --- _static_theme_mapping ------------------------------------------------------


def _program(pid, *, framing="solo", clock=None):
    return Program(
        id=pid,
        name=pid.replace("_", " ").title(),
        hosts=("vell", "wren"),
        framing=framing,
        daypart="x",
        clock=tuple(clock) if clock is not None else (ClockStep(format="talk"),),
        rotation=(),
    )


def test_static_mapping_classifies_every_resolution_kind(
    monkeypatch, assets_tree, audio_factory
):
    clip = audio_factory(seconds=0.5)
    (assets_tree / "themes" / "bespoke_show.mp3").write_bytes(clip.read_bytes())
    (assets_tree / "themes" / "c9_talk.mp3").write_bytes(clip.read_bytes())

    monkeypatch.setattr(
        audit.programming,
        "all_programs",
        lambda: {
            "long_night": _program("long_night"),  # PROGRAM_THEMES override -> b4_night
            "bespoke_show": _program("bespoke_show"),  # convention file on disk
            "no_clip_show": _program("no_clip_show"),  # falls back to c9_talk
            "cold_show": _program("cold_show", clock=()),  # nothing resolves at all
            "handoff_show": _program("handoff_show", framing="handover"),
        },
    )

    rows = {r["program"]: r for r in audit._static_theme_mapping()}

    assert rows["long_night"]["kind"] == "override"
    assert rows["long_night"]["clip"] == "b4_night.mp3"

    assert rows["bespoke_show"]["kind"] == "bespoke"
    assert rows["bespoke_show"]["clip"] == "bespoke_show.mp3"

    assert rows["no_clip_show"]["kind"] == "fallback"
    assert rows["no_clip_show"]["clip"] == "c9_talk.mp3"

    assert rows["cold_show"]["kind"] == "missing"
    assert rows["cold_show"]["clip"] is None

    # A handover program also carries its resolved B6 handoff sting.
    assert rows["handoff_show"]["handover_clip"] == "b6_handover.mp3"


# --- run_audit end-to-end -----------------------------------------------------


def test_run_audit_end_to_end():
    """A short isolated run on the real spine — all five properties must pass.

    Skips cleanly without Postgres/pgvector; otherwise it seeds nothing of its
    own and rolls the whole world back (the same isolation `run_acceptance`
    uses), so it never touches the operator's real DB, schedule, or media.
    """
    try:
        report = audit.run_audit(
            window_hours=3.0,
            step_minutes=60,
            tick_every_hours=2.0,
            warmup_ticks=1,
            buffer_depth_hours=0.5,
        )
    except audit.acceptance._NoDatabaseError as exc:
        pytest.skip(f"no Postgres/pgvector: {exc}")

    assert report.telemetry["total_slots"] > 0
    assert report.mapping  # every grid program got a static resolution row
    failures = [f"{r.name}: {r.detail}" for r in report.results if not r.ok]
    assert report.ok, "jingle audit properties failed:\n" + "\n".join(failures)
    assert len(report.results) == 5

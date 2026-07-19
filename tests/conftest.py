"""Shared fixtures for the test suite.

`audio_factory` renders tiny REAL mp3 tones via ffmpeg (a hard dependency of the
pipeline, so tests may shell it) — the D7 production tests need genuine audio to
probe/mix without ever depending on the real curated `assets/` media. Session-
scoped + cached: each distinct tone renders once per run.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _tone(
    path: Path, seconds: float, rate: int, channels: int, freq: int = 440
) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:duration={seconds}",
            "-ar",
            str(rate),
            "-ac",
            str(channels),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "64k",
            str(path),
        ],
        check=True,
    )


@pytest.fixture(scope="session")
def audio_factory(tmp_path_factory):
    """`audio_factory(seconds=…, rate=…, channels=…)` → a cached fixture mp3 path."""
    root = tmp_path_factory.mktemp("fixture-audio")
    cache: dict[tuple, Path] = {}

    def make(seconds: float = 1.0, rate: int = 44_100, channels: int = 2) -> Path:
        key = (seconds, rate, channels)
        if key not in cache:
            p = root / f"tone-{seconds}s-{rate}hz-{channels}ch.mp3"
            _tone(p, seconds, rate, channels)
            cache[key] = p
        return cache[key]

    return make


@pytest.fixture()
def co1_world(monkeypatch):
    """CO1 — a small FIXED fixture world for the model-input equivalence goldens.

    Mocks the bible loader + the store seam to deterministic fixture data (the
    "fixed seed"), so `context.assemble` runs DB-free and byte-reproducibly on a
    fixed clock. `speaker_sets` mirrors the B5 format registry defaults (talk =
    vell+wren, news = thorn, music/commercial = vell) — deliberately literal,
    because per-speaker-set prefix bytes are exactly what the CO pack is about.
    Shared by tests/test_context.py and tests/test_llm_cache.py.
    """
    from datetime import datetime, timedelta
    from types import SimpleNamespace

    from src.world import clock, context
    from src.world.store import CanonFact, CastMember, Event

    bible = (
        "# Settlement Radio — Series Bible\n\n"
        "Humanity is alone; the settlements keep each other company by radio."
    )
    cast = {
        "vell": CastMember(
            "vell", "Vell", "Warm night-shift host; wry, hopeful.", "voice-a"
        ),
        "wren": CastMember(
            "wren", "Wren", "Quick, curious co-host; loves the archives.", "voice-b"
        ),
        "thorn": CastMember("thorn", "Thorn", "Dry, precise news anchor.", "voice-c"),
    }
    now = datetime(2026, 7, 8, 21, 0)
    event = Event(
        "lumen",
        "Lumen Festival",
        "Lamps are lit.",
        clock.to_inworld(now) + timedelta(days=5),
        "upcoming",
        [],
    )
    facts = [CanonFact("c1", "Radio connects the settlements.", [])]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(context.canon_source, "load_bible", lambda *a: bible)
    monkeypatch.setattr(context.store, "connect", lambda: _Conn())
    monkeypatch.setattr(
        context.store, "get_cast_member", lambda conn, sid: cast.get(sid)
    )
    monkeypatch.setattr(context.store, "events_in_range", lambda conn, a, b: [event])
    monkeypatch.setattr(context.store, "all_canon", lambda conn: list(facts))
    monkeypatch.setattr(
        context.store, "attributed_quotes_near", lambda conn, a, b, limit=0: []
    )

    return SimpleNamespace(
        bible=bible,
        cast=cast,
        now=now,
        speaker_sets={
            "talk": ["vell", "wren"],
            "news": ["thorn"],
            "music": ["vell"],
            "commercial": ["vell"],
        },
    )


@pytest.fixture()
def assets_tree(tmp_path, audio_factory, monkeypatch):
    """A fixture `assets/` tree with the D7 clips the tests place, wired into settings.

    Deliberately PARTIAL (no d15_advisory etc.) so missing-clip degradation is
    testable. Tests never touch the real curated media.
    """
    from src.config import settings

    assets = tmp_path / "assets"
    clip = audio_factory(seconds=0.5)
    for rel in [
        "idents/a1_signature.mp3",
        "themes/b4_night.mp3",
        "themes/b4_night_bed.mp3",
        "themes/b5_first_light.mp3",
        "stings/b6_handover.mp3",
        "stings/c8_news_sting.mp3",
        "stings/c10_music_bumper.mp3",
        "stings/a4_sweeper_bright.mp3",  # R2.3 — the flagship item joins
        "stings/a4_sweeper_mid.mp3",
    ]:
        target = assets / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(clip.read_bytes())
    monkeypatch.setattr(settings, "assets_dir", assets)
    return assets

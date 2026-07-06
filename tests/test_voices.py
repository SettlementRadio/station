"""Tests for the D9.2 data-driven voice registry (src/providers/tts.py).

Renders need an engine; what's pinned here is the registry logic and — more
important — the CONTRACTS between the three sources of truth an operator edits
independently: the bible cast (docs/canon/90-cast.md), the voice registry
(config/voices.yaml), and the seed-time validation that refuses to let them
disagree. A silent gap here is exactly the 3 a.m. failure D9.2 exists to
prevent: a DJ airing in the wrong voice, or a slot dying on an unmapped one.
"""

from __future__ import annotations

import re

import pytest
from src.config import settings
from src.providers import tts
from src.world.seed import _validate_cast_voices
from src.world.store import CastMember

ENGINES = ("kokoro", "elevenlabs", "say")

# The legacy B4 alias for Wren — the ONE intentional shared mapping.
LEGACY_ALIASES = {"dj_two"}


def _cast_voices_from_bible() -> set[str]:
    """Every `Logical voice` named in the bible's cast file."""
    text = (settings.canon_dir / "90-cast.md").read_text(encoding="utf-8")
    return set(re.findall(r"\*\*Logical voice:\*\*\s*`([^`]+)`", text))


def test_shipped_registry_covers_the_bible_cast():
    voices = _cast_voices_from_bible()
    assert len(voices) >= 10  # the D-cast roster
    missing = voices - tts.known_voices()
    assert not missing, f"bible voices missing from voices.yaml: {sorted(missing)}"


def test_every_entry_maps_all_three_engines():
    registry = tts._voice_registry()
    for logical, engines in registry.items():
        assert set(engines) >= set(ENGINES), f"{logical} lacks an engine mapping"


def test_no_more_placeholder_aliasing():
    # The D9.2 heads-up: 9 voices used to alias onto two real presets. Now every
    # cast voice must be DISTINCT per engine (the legacy dj_two alias aside).
    registry = tts._voice_registry()
    cast_voices = _cast_voices_from_bible() - LEGACY_ALIASES
    for engine in ENGINES:
        presets = [registry[v][engine] for v in sorted(cast_voices)]
        dupes = {p for p in presets if presets.count(p) > 1}
        assert not dupes, f"shared {engine} presets across DJs: {sorted(dupes)}"


def test_unknown_logical_voice_fails_loud():
    with pytest.raises(ValueError, match="unknown logical voice"):
        tts._vendor_voice("nobody_nowhere", "kokoro")


def test_missing_engine_mapping_fails_loud(tmp_path, monkeypatch):
    path = tmp_path / "voices.yaml"
    path.write_text("solo_voice:\n  kokoro: bm_george\n", encoding="utf-8")
    monkeypatch.setattr(settings, "tts_voices_path", path)
    tts._voices_cache = None
    try:
        assert tts._vendor_voice("solo_voice", "kokoro") == "bm_george"
        with pytest.raises(ValueError, match="has no 'elevenlabs' mapping"):
            tts._vendor_voice("solo_voice", "elevenlabs")
    finally:
        tts._voices_cache = None


def test_missing_registry_file_fails_loud(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "tts_voices_path", tmp_path / "absent.yaml")
    tts._voices_cache = None
    try:
        with pytest.raises(RuntimeError, match="voice registry not found"):
            tts._voice_registry()
    finally:
        tts._voices_cache = None


# --- Seed-time validation: the bible and the registry must agree -------------


def _member(voice: str) -> CastMember:
    return CastMember("test", "Test", "card", voice, [])


def test_seed_validation_passes_on_registered_voices():
    _validate_cast_voices([_member("vell_night"), _member("zhe_observer")])


def test_seed_validation_fails_loud_on_unmapped_voice():
    with pytest.raises(ValueError, match="no entry in") as exc:
        _validate_cast_voices([_member("vell_night"), _member("ghost_voice")])
    assert "ghost_voice" in str(exc.value)

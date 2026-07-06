"""Tests for the D9.0 emotion vocabulary in the TTS seam (src/providers/tts.py).

The renders themselves need a vendor/engine, so what's pinned here is the pure
seam logic a silent bug would corrupt: the vocabulary↔registry agreement, the
mapping's validity against the REAL ElevenLabs `VoiceSettings` model, and
`resolve_emotion`'s normalise → settings-default → drop-unknown chain (a bad
tag must degrade to the engine default, never fail a render mid-buffer).
"""

from __future__ import annotations

from src.config import settings
from src.providers import tts


def test_vocabulary_matches_the_elevenlabs_registry():
    assert tts.EMOTIONS == frozenset(tts._ELEVENLABS_EMOTIONS)
    assert "somber" in tts.EMOTIONS  # the pack's named vocabulary is present
    assert "warm" in tts.EMOTIONS


def test_registry_entries_construct_real_voice_settings():
    # Every mapping must build against the actual SDK model — a typo'd field
    # would otherwise only surface on a paid render.
    from elevenlabs.types import VoiceSettings

    for emotion, params in tts._ELEVENLABS_EMOTIONS.items():
        vs = VoiceSettings(**params)
        assert vs.stability is not None, emotion
        assert 0.0 <= vs.stability <= 1.0, emotion
        assert vs.style is not None and 0.0 <= vs.style <= 1.0, emotion


def test_resolve_emotion_normalises_and_validates(monkeypatch):
    monkeypatch.setattr(settings, "tts_emotion_default", "")
    assert tts.resolve_emotion("somber") == "somber"
    assert tts.resolve_emotion("  Wry ") == "wry"
    assert tts.resolve_emotion(None) is None  # no emotion, no default
    assert tts.resolve_emotion("melodramatic") is None  # unknown: drop, don't raise


def test_resolve_emotion_falls_back_to_the_settings_default(monkeypatch):
    monkeypatch.setattr(settings, "tts_emotion_default", "warm")
    assert tts.resolve_emotion(None) == "warm"
    assert tts.resolve_emotion("urgent") == "urgent"  # an explicit value wins


def test_unknown_settings_default_degrades_to_engine_default(monkeypatch):
    monkeypatch.setattr(settings, "tts_emotion_default", "sparkly")
    assert tts.resolve_emotion(None) is None

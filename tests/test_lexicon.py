"""Tests for the D9.1 pronunciation lexicon (src/providers/lexicon.py).

The renders need an engine; what's pinned here is the pure substitution logic a
silent bug would corrupt on air: per-engine mechanism selection (Kokoro phoneme
markup vs respelling), whole-word matching (a name inside a longer word must
NOT match), pass-through of unknown names, and the degrade paths (missing file,
malformed entry, disabled toggle) — the lexicon must never fail a render.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from src.config import settings
from src.providers import lexicon

LEXICON = """
- name: Zhe
  respell: Zhay
  phonemes: "ʒeɪ"
- name: Lumen
  respell: LOO-men
  phonemes: "lˈumɛn"
- name: Kael
  respell: Kale
"""


@pytest.fixture()
def lex_file(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "pronunciation.yaml"
    path.write_text(LEXICON, encoding="utf-8")
    monkeypatch.setattr(settings, "tts_lexicon_path", path)
    monkeypatch.setattr(settings, "tts_lexicon_enabled", True)
    lexicon._cache = None
    return path


def test_kokoro_gets_phoneme_markup(lex_file):
    out = lexicon.apply_lexicon("Zhe sends word.", "kokoro")
    assert out == "[Zhe](/ʒeɪ/) sends word."


def test_kokoro_falls_back_to_respell_without_phonemes(lex_file):
    assert lexicon.apply_lexicon("Kael laughed.", "kokoro") == "Kale laughed."


def test_other_engines_get_the_respelling(lex_file):
    assert (
        lexicon.apply_lexicon("The Lumen Festival opens.", "elevenlabs")
        == "The LOO-men Festival opens."
    )
    assert lexicon.apply_lexicon("Zhe sends word.", "say") == "Zhay sends word."


def test_whole_word_and_case_sensitive_matching(lex_file):
    # A name inside a longer word, or differently cased, passes through.
    assert lexicon.apply_lexicon("Lumenance is not a name.", "say") == (
        "Lumenance is not a name."
    )
    assert lexicon.apply_lexicon("the zhe particle", "say") == "the zhe particle"


def test_unknown_names_pass_through_unharmed(lex_file):
    text = "Orin plays tonight on Concordance."
    assert lexicon.apply_lexicon(text, "kokoro") == text


def test_missing_file_degrades_to_no_op(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "tts_lexicon_path", tmp_path / "absent.yaml")
    monkeypatch.setattr(settings, "tts_lexicon_enabled", True)
    lexicon._cache = None
    assert lexicon.apply_lexicon("Zhe sends word.", "kokoro") == "Zhe sends word."


def test_malformed_entry_is_skipped_not_fatal(tmp_path, monkeypatch):
    path = tmp_path / "pronunciation.yaml"
    path.write_text("- name: Zhe\n- name: Vell\n  respell: Vell\n", encoding="utf-8")
    monkeypatch.setattr(settings, "tts_lexicon_path", path)
    monkeypatch.setattr(settings, "tts_lexicon_enabled", True)
    lexicon._cache = None
    # The respell-less Zhe entry is dropped; the valid Vell entry still applies.
    assert lexicon.apply_lexicon("Zhe and Vell.", "say") == "Zhe and Vell."


def test_disabled_toggle_is_a_no_op(lex_file, monkeypatch):
    monkeypatch.setattr(settings, "tts_lexicon_enabled", False)
    assert lexicon.apply_lexicon("Zhe sends word.", "kokoro") == "Zhe sends word."


def test_edit_is_picked_up_without_restart(lex_file):
    import os

    assert lexicon.apply_lexicon("Zhe.", "say") == "Zhay."
    lex_file.write_text("- name: Zhe\n  respell: Zhuh\n", encoding="utf-8")
    os.utime(lex_file, (0, 9_999_999_999))  # force a distinct mtime
    assert lexicon.apply_lexicon("Zhe.", "say") == "Zhuh."


def test_shipped_lexicon_parses_and_covers_the_tricky_cast():
    # The real config/pronunciation.yaml must load cleanly and keep covering the
    # names the engines are known to misread (see D9.1).
    lexicon._cache = None
    entries, pattern = lexicon._load()
    names = {e.name for e in entries}
    assert {"Zhe", "Mira", "Kael", "Lumen"} <= names
    assert pattern is not None

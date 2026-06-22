"""Tests for the C0 content-safety gate (src/safety.py).

The LLM safety pass needs Claude, so it's exercised live via the producers. Here
we pin the logic a silent bug would let through: the keyword pre-filter (it must
catch blocklisted terms and must NOT false-positive on substrings) and the
`generate_safe` regenerate-then-give-up policy (get this wrong and flagged text
airs, or a clean draft is needlessly rejected).
"""

from __future__ import annotations

from src import safety
from src.safety import SafetyResult


def test_keyword_filter_flags_blocklisted_term_without_api():
    # A blocklisted word short-circuits before any LLM call (stage == "keyword").
    result = safety.safety_check("well that's a load of shit, honestly")
    assert not result.ok
    assert result.stage == "keyword"


def test_keyword_filter_respects_word_boundaries():
    # Substring matches must NOT flag (the Scunthorpe problem).
    assert safety._keyword_hit("scunthorpe united played well") is None
    assert safety._keyword_hit("the assassin slipped away") is None
    # But a real standalone term is caught.
    assert safety._keyword_hit("you absolute fuck") == "fuck"


def test_disabled_gate_passes_everything(monkeypatch):
    monkeypatch.setattr(safety.settings, "safety_enabled", False)
    result = safety.safety_check("anything at all, even shit")
    assert result.ok
    assert result.stage == "disabled"


def test_generate_safe_regenerates_then_succeeds(monkeypatch):
    # First draft flags, second is clean: generate_safe returns the clean one.
    monkeypatch.setattr(
        safety,
        "safety_check",
        lambda text: SafetyResult(ok=(text == "good"), reason="bad", stage="llm"),
    )
    drafts = iter(["bad draft", "good"])
    text, result = safety.generate_safe(lambda: next(drafts), attempts=2)
    assert result.ok
    assert text == "good"


def test_generate_safe_gives_up_after_attempts(monkeypatch):
    # Every draft flags: generate_safe returns the last result with ok=False so the
    # caller falls back — it never silently passes flagged text.
    calls = {"n": 0}

    def _produce() -> str:
        calls["n"] += 1
        return "still bad"

    monkeypatch.setattr(
        safety,
        "safety_check",
        lambda text: SafetyResult(ok=False, reason="bad", stage="llm"),
    )
    text, result = safety.generate_safe(_produce, attempts=2)
    assert not result.ok
    assert calls["n"] == 2  # bounded: exactly `attempts` tries, no more

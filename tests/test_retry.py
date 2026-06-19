"""Tests for the bounded-retry helper (src/retry.py).

This wraps EVERY external call (Claude, TTS), so a silent bug here would mean
the station retries forever, gives up too early, or swallows failures — exactly
the kind of logic CLAUDE.md says to test. We cover the three real behaviours:
succeed-after-transient-failure, exhaust-and-re-raise, and attempt counting.
"""

from __future__ import annotations

import pytest
from src.retry import call_with_retry


def test_returns_on_first_success():
    calls = {"n": 0}

    def ok():
        calls["n"] += 1
        return "value"

    assert call_with_retry("test.ok", ok, attempts=3, backoff_sec=0) == "value"
    assert calls["n"] == 1  # no retries when the first attempt succeeds


def test_succeeds_after_transient_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "recovered"

    result = call_with_retry("test.flaky", flaky, attempts=3, backoff_sec=0)
    assert result == "recovered"
    assert calls["n"] == 3  # failed twice, succeeded on the third


def test_exhausts_then_reraises_last_exception():
    calls = {"n": 0}

    def boom():
        calls["n"] += 1
        raise ValueError(f"fail #{calls['n']}")

    with pytest.raises(ValueError, match="fail #2"):
        call_with_retry("test.boom", boom, attempts=2, backoff_sec=0)
    assert calls["n"] == 2  # exactly `attempts` tries, no more

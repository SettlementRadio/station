"""Bounded retry for external calls (Claude, TTS).

CLAUDE.md "Engineering standards": wrap external calls with sensible failure
handling and bounded retries; on failure, fail loudly into the logs — never
silently produce nothing. This is the single helper both seams use so the policy
(attempts, backoff, logging) lives in one place and reads from `settings`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from .config import settings
from .logging_setup import get_logger

T = TypeVar("T")

log = get_logger(__name__)


def call_with_retry(
    op: str,
    func: Callable[[], T],
    *,
    attempts: int | None = None,
    backoff_sec: float | None = None,
) -> T:
    """Run `func`, retrying on any exception up to `attempts` times.

    Args:
        op: short name of the operation, for the logs (e.g. "llm.generate").
        func: a zero-arg callable performing the external call.
        attempts: total attempts including the first (defaults to settings).
        backoff_sec: base linear backoff; wait grows attempt*backoff between tries.

    Returns the call's result. If every attempt fails, logs loudly at error and
    re-raises the last exception — the caller fails loudly rather than getting a
    silent empty result.
    """
    attempts = attempts if attempts is not None else settings.retry_attempts
    backoff_sec = backoff_sec if backoff_sec is not None else settings.retry_backoff_sec

    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001 — bounded retry over any failure
            last_exc = exc
            if attempt < attempts:
                wait = backoff_sec * attempt
                log.warning(
                    "external_call_retry",
                    op=op,
                    attempt=attempt,
                    max_attempts=attempts,
                    wait_sec=wait,
                    error=str(exc),
                )
                time.sleep(wait)
            else:
                log.error(
                    "external_call_failed",
                    op=op,
                    attempts=attempts,
                    error=str(exc),
                )
    assert last_exc is not None  # unreachable: loop always sets it before exit
    raise last_exc

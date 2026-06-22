"""C0 — the real content-safety gate (was a no-op placeholder in Phases A/B).

Every producer (writer, news, music, conversation) runs its generated text
through `safety_check()` before it can become audio. CLAUDE.md ("Content safety")
requires a real gate before any *public* broadcast (Phase C onward) — this is the
hard prerequisite C0 makes good on. The same gate later guards Layer 0 listener
inbound in Phase E, so it takes/returns plain text and knows nothing about
Segments.

Two stages, cheap-first:

  1. A fast keyword/profanity pre-filter (no API call) — catches the obvious.
  2. An LLM safety pass on the `haiku` tier (cheap, near-live) — catches what a
     wordlist can't, while *allowing* in-world sci-fi conflict (this is fiction,
     not a real-world feed), so it doesn't thrash on every dramatic line.

`safety_check()` returns a verdict (`SafetyResult`), not mutated text — it is a
gate, not a rewriter. The regenerate-once-then-fall-back-to-evergreen policy
lives in the producers (see `generate_safe` for the single-call shape, and
`writers/conversation.compose_segment` for the combined safety+continuity gate),
so "what to do when flagged" stays with the caller that knows how to regenerate.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .config import settings
from .logging_setup import get_logger
from .providers import llm

log = get_logger(__name__)

# The fast pre-filter wordlist — a NAMED domain constant (config.py convention:
# intrinsic data lives next to its code, not in settings). Deliberately small: it
# is a cheap first net for the unambiguous cases, NOT the whole gate — the LLM
# pass below is what catches nuance. Matched on word boundaries, case-insensitively.
# Keep entries lowercase. Extend conservatively; over-blocking fiction is a cost.
_BLOCKLIST: tuple[str, ...] = (
    # crude profanity (a public broadcast shouldn't air these casually)
    "fuck",
    "shit",
    "cunt",
    "motherfucker",
    # slurs / hate markers (any appearance is a flag for an LLM-written draft)
    "nigger",
    "faggot",
    "retard",
    # real-world unsafe-instruction markers that have no place in the fiction
    "child porn",
    "how to make a bomb",
)

_BLOCKLIST_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _BLOCKLIST) + r")\b",
    re.IGNORECASE,
)

# The LLM safety reviewer's instructions. Tuned for a FICTIONAL sci-fi station:
# allow in-world tension, danger, and loss; flag only genuinely unsafe content.
_LLM_SYSTEM = (
    "You are the content-safety reviewer for Settlement Radio, a fictional "
    "science-fiction radio station that broadcasts to the public. Review the "
    "draft below — the spoken words that would go to air. This is FICTION: "
    "in-world conflict, danger, tension, sorrow, and peril are fine and expected. "
    "FLAG it only if it contains real-world hate or slurs against a protected "
    "group, sexually explicit content, gratuitous graphic gore, content that "
    "encourages self-harm or suicide, harassment of a real person, or genuinely "
    "dangerous real-world instructions (weapons, attacks). Reply with the single "
    "word OK if it is safe to broadcast, otherwise 'FLAG:' followed by a terse "
    "reason. Do not rewrite or quote the draft."
)


@dataclass(frozen=True)
class SafetyResult:
    """The safety gate's verdict on one draft."""

    ok: bool
    reason: str  # "OK" or a terse explanation of the flag
    stage: str  # which stage decided: "keyword" | "llm" | "disabled"


def _keyword_hit(text: str) -> str | None:
    """Return the first blocklisted term found, or None."""
    m = _BLOCKLIST_RE.search(text)
    return m.group(1).lower() if m else None


def _llm_verdict(text: str) -> SafetyResult:
    """Run the cheap LLM safety pass; returns the verdict (fails closed on error)."""
    note = llm.generate(
        f"Draft to review:\n\n{text}",
        system=_LLM_SYSTEM,
        model=settings.safety_llm_tier,  # haiku: cheap, near-live (CLAUDE.md routing)
        max_tokens=settings.safety_max_tokens,
    ).strip()
    ok = note.upper().startswith("OK")
    return SafetyResult(ok=ok, reason="OK" if ok else note, stage="llm")


def safety_check(text: str) -> SafetyResult:
    """Gate `text` for broadcast: keyword pre-filter, then a cheap LLM safety pass.

    Returns a `SafetyResult`; never raises for *content* reasons (a flag is a
    verdict, not an error). The keyword stage short-circuits before any API call.
    Set `settings.safety_enabled=False` to bypass (dev only — never in production).
    """
    if not settings.safety_enabled:
        return SafetyResult(ok=True, reason="safety gate disabled", stage="disabled")

    hit = _keyword_hit(text)
    if hit is not None:
        log.warning("safety_keyword_flag", term=hit)
        return SafetyResult(
            ok=False, reason=f"blocklisted term: {hit!r}", stage="keyword"
        )

    result = _llm_verdict(text)
    log.info("safety_check_done", ok=result.ok, stage=result.stage)
    if not result.ok:
        log.warning("safety_llm_flag", reason=result.reason[:300])
    return result


def generate_safe(
    produce: Callable[[], str],
    *,
    attempts: int | None = None,
) -> tuple[str, SafetyResult]:
    """Run `produce` until the safety gate passes, up to `attempts` times.

    The single-call shape of the C0 policy ("regenerate once, then refuse"): used
    by the single-DJ producers (writer, news, music). `produce` generates one
    fresh draft per call. Returns `(text, result)` for the last attempt; when
    `result.ok` is False the caller MUST fall back to an evergreen segment rather
    than air the text. Defaults to `settings.safety_max_attempts`.
    """
    attempts = attempts if attempts is not None else settings.safety_max_attempts
    text = ""
    result = SafetyResult(ok=False, reason="not generated", stage="keyword")
    for attempt in range(1, attempts + 1):
        text = produce().strip()
        result = safety_check(text)
        if result.ok:
            return text, result
        log.warning(
            "safety_regenerate",
            attempt=attempt,
            attempts=attempts,
            reason=result.reason,
        )
    return text, result

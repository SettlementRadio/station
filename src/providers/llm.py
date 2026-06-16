"""Seam #1a — the ONLY module that imports the Anthropic SDK.

Every Claude call in the project goes through `generate(...)`. Callers pass a
*logical* model tier ("haiku" | "sonnet" | "opus"); this module maps it to the
current real model ID. Swapping models, or the whole vendor, means editing this
one file — nothing upstream changes. See docs/ARCHITECTURE.md "Seam #1".
"""

from __future__ import annotations

from collections.abc import Callable

import anthropic
from dotenv import load_dotenv

load_dotenv()  # pull ANTHROPIC_API_KEY (and friends) from .env if present

# Logical tier -> current real Claude model ID. The mapping lives here so the
# rest of the codebase only ever talks in tiers. See CLAUDE.md "Tech reality".
_MODEL_IDS = {
    "haiku": "claude-haiku-4-5-20251001",  # high-volume, low-stakes, near-live
    "sonnet": "claude-sonnet-4-6",         # DEFAULT writing brain: DJ scripts
    "opus": "claude-opus-4-8",             # hard reasoning only; runs rarely
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Lazily build the SDK client (reads ANTHROPIC_API_KEY from the env)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def generate(
    prompt: str,
    *,
    system: str | None = None,
    model: str = "sonnet",
    cached_context: str | None = None,
    max_tokens: int = 4000,
    on_token: Callable[[str], None] | None = None,
    timeout: float = 120.0,
) -> str:
    """Return Claude's text output for `prompt`.

    Args:
        prompt: the variable user turn.
        system: optional system instructions (the small, per-call part).
        model: logical tier "haiku" | "sonnet" | "opus" — mapped to a real ID.
        cached_context: large, stable text (e.g. the canon) sent as a
            prompt-cache breakpoint, so repeat calls pay ~0.1x on that input.
        max_tokens: output cap.
        on_token: optional callback invoked with each text delta as it streams.
            Lets callers show progress so a multi-second generation doesn't look
            frozen; `None` is silent.
        timeout: per-request timeout in seconds. A genuine network stall raises
            promptly instead of blocking indefinitely.

    The call is **streamed** so the first bytes arrive immediately (a 5-minute
    script takes ~25s to generate; a non-streaming call would block silently at
    the socket the whole time and look hung). The full text is still returned as
    one string — streaming is an internal implementation detail of the seam.

    The Phase A cost lever lives here: `cached_context` is placed first in the
    system prompt with a cache_control breakpoint, and the smaller `system`
    text follows it — only the part after the breakpoint pays full price on a
    cache hit. (Prefixes below the model's minimum cacheable size won't cache;
    that's fine — the path is in use and grows into Phase B for free.)
    """
    try:
        model_id = _MODEL_IDS[model]
    except KeyError:
        raise ValueError(
            f"unknown model tier {model!r}; expected one of {sorted(_MODEL_IDS)}"
        ) from None

    # Build the system prompt as cache-aware blocks: stable content first (with
    # the breakpoint), volatile content after it. Caching is a prefix match, so
    # the stable canon must physically precede the per-call instructions.
    system_blocks: list[dict] = []
    if cached_context:
        system_blocks.append(
            {
                "type": "text",
                "text": cached_context,
                "cache_control": {"type": "ephemeral"},
            }
        )
    if system:
        system_blocks.append({"type": "text", "text": system})

    kwargs: dict = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_blocks:
        kwargs["system"] = system_blocks

    client = _get_client().with_options(timeout=timeout)
    parts: list[str] = []
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            parts.append(text)
            if on_token is not None:
                on_token(text)
    return "".join(parts)

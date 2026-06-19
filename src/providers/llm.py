"""Seam #1a — the ONLY module that imports the Anthropic SDK.

Every Claude call in the project goes through `generate(...)`. Callers pass a
*logical* model tier ("haiku" | "sonnet" | "opus"); this module maps it to the
current real model ID. Swapping models, or the whole vendor, means editing this
one file — nothing upstream changes. See docs/ARCHITECTURE.md "Seam #1".
"""

from __future__ import annotations

from collections.abc import Callable

import anthropic

from ..config import settings
from ..logging_setup import get_logger
from ..retry import call_with_retry

# Logical tier -> real model id now lives in the typed settings module
# (`settings.model_id(tier)`), so the mapping is config, not a literal here.
# See CLAUDE.md "Tech reality" + "Engineering standards" (config over hardcoding).

log = get_logger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Lazily build the SDK client (api key from settings, falling back to env)."""
    global _client
    if _client is None:
        # Pass the key explicitly from settings; `or None` lets the SDK fall back
        # to its own env lookup when the key isn't set in .env.
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    return _client


def generate(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    cached_context: str | None = None,
    max_tokens: int | None = None,
    on_token: Callable[[str], None] | None = None,
    timeout: float | None = None,
) -> str:
    """Return Claude's text output for `prompt`.

    Args:
        prompt: the variable user turn.
        system: optional system instructions (the small, per-call part).
        model: logical tier "haiku" | "sonnet" | "opus" — mapped to a real ID.
            Defaults to `settings.llm_default_tier`.
        cached_context: large, stable text (e.g. the canon) sent as a
            prompt-cache breakpoint, so repeat calls pay ~0.1x on that input.
        max_tokens: output cap. Defaults to `settings.llm_max_tokens`.
        on_token: optional callback invoked with each text delta as it streams.
            Lets callers show progress so a multi-second generation doesn't look
            frozen; `None` is silent.
        timeout: per-request timeout in seconds. A genuine network stall raises
            promptly instead of blocking indefinitely. Defaults to
            `settings.llm_timeout_sec`.

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
    tier = model if model is not None else settings.llm_default_tier
    max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
    timeout = timeout if timeout is not None else settings.llm_timeout_sec
    model_id = settings.model_id(tier)  # raises ValueError on an unknown tier

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

    log.info(
        "llm_generate_start",
        tier=tier,
        model=model_id,
        max_tokens=max_tokens,
        cached=bool(cached_context),
        prompt_chars=len(prompt),
    )

    def _do_stream() -> str:
        # Re-built fresh per attempt: a retry restarts the stream cleanly (any
        # partial output from a failed attempt is discarded).
        parts: list[str] = []
        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                parts.append(text)
                if on_token is not None:
                    on_token(text)
        return "".join(parts)

    text = call_with_retry("llm.generate", _do_stream)
    log.info("llm_generate_done", tier=tier, model=model_id, output_chars=len(text))
    return text

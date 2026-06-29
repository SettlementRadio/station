"""Seam #1a — the ONLY module that imports the Anthropic SDK.

Every Claude call in the project goes through `generate(...)`. Callers pass a
*logical* model tier ("haiku" | "sonnet" | "opus"); this module maps it to the
current real model ID. Swapping models, or the whole vendor, means editing this
one file — nothing upstream changes. See docs/ARCHITECTURE.md "Seam #1".
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

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

    system_blocks = _system_blocks(cached_context, system)

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


def _system_blocks(cached_context: str | None, system: str | None) -> list[dict]:
    """Build cache-aware system blocks: stable content first (with the cache
    breakpoint), volatile content after it.

    Caching is a prefix match, so the stable canon must physically precede the
    per-call instructions. Shared by `generate` and `generate_batch` so both pay
    full price only on the small variable part once the prefix is cached.
    """
    blocks: list[dict] = []
    if cached_context:
        blocks.append(
            {
                "type": "text",
                "text": cached_context,
                "cache_control": {"type": "ephemeral"},
            }
        )
    if system:
        blocks.append({"type": "text", "text": system})
    return blocks


# --- Batch path (D3: the nightly tick's cost lever) -------------------------
# The Message Batches API processes many requests asynchronously at 50% of
# standard price. It is the ONLY other place the vendor SDK is touched, and the
# ONLY place the batch API is imported — callers (the world tick) go through
# `generate_batch` exactly as they go through `generate`, never the vendor batch
# API directly (the seam rule). Batch is async (submit → poll → collect), which
# is fine for a nightly, non-live job. Prompt caching rides along via the same
# cache-aware system blocks, so the stable bible is cached across the batch.


@dataclass(frozen=True)
class BatchRequest:
    """One request in a batch. `custom_id` keys the result back to the caller.

    Mirrors `generate`'s arguments: `prompt` is the variable user turn, `system`
    the small per-call instructions, `cached_context` the large stable prefix
    (cached), `model` the logical tier, `max_tokens` the output cap. Defaults fall
    back to the same settings `generate` uses.
    """

    custom_id: str
    prompt: str
    system: str | None = None
    cached_context: str | None = None
    model: str | None = None
    max_tokens: int | None = None


@dataclass(frozen=True)
class BatchResult:
    """One result, keyed to its request by `custom_id`.

    `ok` is True only on a succeeded result with text; `error` carries the reason
    otherwise (errored/canceled/expired/missing). `usage` holds the token counts
    for cost telemetry (empty when unavailable). Results are returned in REQUEST
    order regardless of the API's arrival order, so callers can zip them with their
    inputs — but keying on `custom_id` is the contract.
    """

    custom_id: str
    text: str | None
    ok: bool
    error: str | None = None
    usage: dict[str, int] = field(default_factory=dict)


def generate_batch(
    requests: Sequence[BatchRequest],
    *,
    poll_interval: float | None = None,
    max_wait: float | None = None,
) -> list[BatchResult]:
    """Run many Claude requests as one batch; return a `BatchResult` per request.

    Submits the batch, polls until it ends, and collects results keyed by
    `custom_id` (the API returns them in any order — we re-key and return them in
    REQUEST order). This is the cost lever for the nightly world tick: 50% off plus
    prompt caching on the shared bible.

    When `settings.llm_batch_enabled` is False, each request is run SYNCHRONOUSLY
    through `generate` instead (no async wait, full price) — the fast local-dev path;
    the call signature and return shape are identical, so callers don't branch.

    A request that errors/expires comes back as a `BatchResult(ok=False, error=…)`
    rather than raising, so one bad item never sinks the whole run; the submit/poll
    calls themselves are retried + fail loud via `call_with_retry`.
    """
    reqs = list(requests)
    if not reqs:
        return []
    poll_interval = (
        poll_interval
        if poll_interval is not None
        else settings.llm_batch_poll_interval_sec
    )
    max_wait = max_wait if max_wait is not None else settings.llm_batch_max_wait_sec

    if not settings.llm_batch_enabled:
        return _generate_batch_sync(reqs)

    return _generate_batch_api(reqs, poll_interval=poll_interval, max_wait=max_wait)


def _generate_batch_sync(reqs: list[BatchRequest]) -> list[BatchResult]:
    """Local/dev path: run each request through `generate` (synchronous, full price)."""
    log.info("llm_batch_sync_start", count=len(reqs))
    results: list[BatchResult] = []
    for r in reqs:
        try:
            text = generate(
                r.prompt,
                system=r.system,
                model=r.model,
                cached_context=r.cached_context,
                max_tokens=r.max_tokens,
            )
            results.append(BatchResult(custom_id=r.custom_id, text=text, ok=True))
        except Exception as exc:  # noqa: BLE001 — one bad item shouldn't sink the run
            log.error(
                "llm_batch_sync_item_failed", custom_id=r.custom_id, error=str(exc)
            )
            results.append(
                BatchResult(custom_id=r.custom_id, text=None, ok=False, error=str(exc))
            )
    return results


def _generate_batch_api(
    reqs: list[BatchRequest], *, poll_interval: float, max_wait: float
) -> list[BatchResult]:
    """Real Batch API path: submit → poll → collect. Vendor batch SDK lives here."""
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = _get_client()

    api_requests: list[Request] = []
    for r in reqs:
        params: dict = {
            "model": settings.model_id(r.model or settings.llm_default_tier),
            "max_tokens": r.max_tokens
            if r.max_tokens is not None
            else settings.llm_max_tokens,
            "messages": [{"role": "user", "content": r.prompt}],
        }
        blocks = _system_blocks(r.cached_context, r.system)
        if blocks:
            params["system"] = blocks
        api_requests.append(
            Request(
                custom_id=r.custom_id,
                params=MessageCreateParamsNonStreaming(**params),
            )
        )

    log.info("llm_batch_submit", count=len(api_requests))
    batch = call_with_retry(
        "llm.generate_batch.create",
        lambda: client.messages.batches.create(requests=api_requests),
    )

    waited = 0.0
    while True:
        status = call_with_retry(
            "llm.generate_batch.retrieve",
            lambda: client.messages.batches.retrieve(batch.id),
        ).processing_status
        if status == "ended":
            break
        if waited >= max_wait:
            raise TimeoutError(
                f"batch {batch.id} did not end within {max_wait}s (status={status})"
            )
        log.info("llm_batch_poll", batch_id=batch.id, status=status, waited_sec=waited)
        time.sleep(poll_interval)
        waited += poll_interval

    by_id: dict[str, BatchResult] = {}
    for result in client.messages.batches.results(batch.id):
        by_id[result.custom_id] = _map_batch_result(result)

    out = [
        by_id.get(
            r.custom_id,
            BatchResult(r.custom_id, None, ok=False, error="no result returned"),
        )
        for r in reqs
    ]
    ok = sum(1 for r in out if r.ok)
    log.info(
        "llm_batch_done", batch_id=batch.id, total=len(out), ok=ok, failed=len(out) - ok
    )
    return out


def _map_batch_result(result) -> BatchResult:
    """Map one vendor batch result object to a `BatchResult`."""
    rtype = result.result.type
    if rtype != "succeeded":
        return BatchResult(result.custom_id, None, ok=False, error=rtype)
    message = result.result.message
    text = "".join(b.text for b in message.content if b.type == "text").strip()
    usage: dict[str, int] = {}
    if getattr(message, "usage", None) is not None:
        u = message.usage
        usage = {
            "input_tokens": getattr(u, "input_tokens", 0) or 0,
            "output_tokens": getattr(u, "output_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
        }
    return BatchResult(result.custom_id, text, ok=True, usage=usage)

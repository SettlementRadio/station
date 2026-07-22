"""R5.1 (=E1.8) — the usage ledger: turn logged token/TTS spend into dollars.

The pipeline already emits a `usage` event on every `llm.generate` call (the CO0
cache-economics split) via `llm.add_usage_listener`. This module listens on that
seam, prices each call from `settings.model_prices`, buckets the spend by the
**job** on air (talk / news / tick / micro-tick / …) via a context var the call
sites set, and — at each job's end — FLUSHES the in-process tally into the durable
`usage_rollup` world-state row. The panel's Budgets screen (and the dashboard bar)
read that rollup back; nothing in the pipeline reads it.

Design notes:
- **Attribution is by job scope, not per call.** `job("talk")` sets a context var;
  the LLM listener records under it (default "other"). TTS + embeddings record under
  their own kinds. Recording is best-effort and wrapped so a ledger bug can NEVER
  break generation (same rule as the existing usage listener).
- **Flush, don't write-per-call.** The accumulator lives in-process; `flush()` merges
  it into `usage_rollup` once, at a job boundary (top-up / tick / micro-tick end).
  This keeps the hot path free of DB writes and the rollup a single small JSON blob.
- **Estimates, not billing.** Prices are operator-editable dials; Kokoro/local TTS
  and local embeddings are free, so their dollar figure is 0 while their volume
  (TTS seconds, embed count) is still tracked for the operator's eye.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime

from .config import settings
from .logging_setup import get_logger
from .providers import llm

log = get_logger(__name__)

USAGE_ROLLUP_KEY = "usage_rollup"

# The job on air right now (set by the format dispatch / tick entrypoints). LLM
# spend records under this; unset = "other" (direct scripts, the flat path, probes).
_current_job: ContextVar[str] = ContextVar("usage_job", default="other")

# The token fields the CO0 usage event carries — the ones the cache economics turn on.
_TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


# --- Pricing (pure) ----------------------------------------------------------


def llm_cost_usd(tier: str, fields: dict) -> float:
    """Dollar cost of one LLM call's token split, per `settings.model_prices`.

    input at full rate, cache-write at `price_cache_write_mult`x input, cache-read at
    `price_cache_read_mult`x input, output at the output rate. Unknown tier → 0.0.
    """
    price = settings.model_prices.get(tier)
    if not price:
        return 0.0
    inp = float(price.get("input", 0.0))
    out = float(price.get("output", 0.0))
    it = fields.get("input_tokens", 0) or 0
    ot = fields.get("output_tokens", 0) or 0
    cw = fields.get("cache_creation_input_tokens", 0) or 0
    cr = fields.get("cache_read_input_tokens", 0) or 0
    usd = (
        it * inp
        + cw * inp * settings.price_cache_write_mult
        + cr * inp * settings.price_cache_read_mult
        + ot * out
    )
    return usd / 1_000_000.0


# Rough speech rate to turn a synthesized character count into a "minutes" figure
# for the operator's eye (Kokoro reports no duration at synthesis time). Estimate
# only — TTS volume, not billing (Kokoro/local is free anyway).
_TTS_CHARS_PER_SEC = 15.0


def tts_cost_usd(seconds: float, provider: str) -> float:
    """Dollar cost of `seconds` of TTS. Only the flagship (elevenlabs) is priced."""
    if provider == "elevenlabs":
        return (seconds / 60.0) * settings.tts_elevenlabs_per_min
    return 0.0  # kokoro / say / local are free


# --- The in-process accumulator ----------------------------------------------

_lock = threading.Lock()
# {(day_iso, category): {usd, calls, tts_sec, emb_count, <token fields>}}
_accum: dict[tuple[str, str], dict[str, float]] = {}


def _bucket(day_iso: str, category: str) -> dict[str, float]:
    key = (day_iso, category)
    b = _accum.get(key)
    if b is None:
        b = {"usd": 0.0, "calls": 0.0, "tts_sec": 0.0, "emb_count": 0.0}
        for f in _TOKEN_FIELDS:
            b[f] = 0.0
        _accum[key] = b
    return b


@contextmanager
def job(name: str) -> Iterator[None]:
    """Attribute all LLM spend inside this block to job `name` (talk/news/tick/…)."""
    token = _current_job.set(name)
    try:
        yield
    finally:
        _current_job.reset(token)


# --- Recording (best-effort; never raises into the caller) -------------------


def _on_llm_usage(event: dict) -> None:
    """Usage-listener callback: price one `generate`/`batch` call under the job."""
    try:
        tier = event.get("tier") or settings.llm_default_tier
        day_iso = date.today().isoformat()
        category = _current_job.get()
        with _lock:
            b = _bucket(day_iso, category)
            b["calls"] += 1
            for f in _TOKEN_FIELDS:
                b[f] += event.get(f, 0) or 0
            b["usd"] += llm_cost_usd(tier, event)
    except Exception as exc:  # noqa: BLE001 — the ledger must never break generation
        log.warning("usage_record_llm_failed", error=str(exc))


def record_tts(chars: int, provider: str) -> None:
    """Record one TTS synthesis (volume by chars → estimated seconds + flagship cost).

    Kokoro doesn't report a duration at synthesis time, so seconds are ESTIMATED from
    the character count — a volume figure for the operator, not a billed quantity
    (Kokoro/local is free; only the flagship path carries a dollar cost).
    """
    try:
        seconds = max(0, int(chars)) / _TTS_CHARS_PER_SEC
        day_iso = date.today().isoformat()
        with _lock:
            b = _bucket(day_iso, "tts")
            b["calls"] += 1
            b["tts_sec"] += seconds
            b["usd"] += tts_cost_usd(seconds, provider)
    except Exception as exc:  # noqa: BLE001
        log.warning("usage_record_tts_failed", error=str(exc))


def record_embeddings(count: int) -> None:
    """Record `count` embedded texts (local model = free, volume tracked)."""
    try:
        day_iso = date.today().isoformat()
        with _lock:
            b = _bucket(day_iso, "embeddings")
            b["calls"] += 1
            b["emb_count"] += max(0, int(count))
    except Exception as exc:  # noqa: BLE001
        log.warning("usage_record_embeddings_failed", error=str(exc))


# Register the LLM listener once, at import. Any process that imports `usage`
# (a job entrypoint, the panel) records — jobs additionally call `flush()`.
llm.add_usage_listener(_on_llm_usage)


# --- Flush: merge the accumulator into the durable rollup --------------------


def _merge(rollup: dict, accum: dict[tuple[str, str], dict[str, float]]) -> dict:
    """Fold the accumulator into a rollup dict ({days: {day: {category: agg}}})."""
    days = rollup.setdefault("days", {})
    for (day_iso, category), b in accum.items():
        day = days.setdefault(day_iso, {})
        cur = day.setdefault(
            category,
            {
                "usd": 0.0,
                "calls": 0.0,
                "tts_sec": 0.0,
                "emb_count": 0.0,
                **dict.fromkeys(_TOKEN_FIELDS, 0.0),
            },
        )
        for k, v in b.items():
            cur[k] = cur.get(k, 0.0) + v
    return rollup


def flush(conn=None) -> bool:  # noqa: ANN001
    """Persist the in-process tally into `usage_rollup`, then clear it.

    Read-modify-write under one transaction (SELECT … FOR UPDATE on the state row) so
    concurrent job processes don't clobber each other's spend. Best-effort: a DB error
    is logged and the accumulator is KEPT (so a later flush can still persist it),
    never raised into the job. Returns True when something was written.
    """
    with _lock:
        if not _accum:
            return False
        snapshot = {k: dict(v) for k, v in _accum.items()}

    from .world import store

    def _do(c) -> None:  # noqa: ANN001
        row = c.execute(
            "SELECT value FROM state WHERE key = %s FOR UPDATE", (USAGE_ROLLUP_KEY,)
        ).fetchone()
        rollup = json.loads(row[0]) if row and row[0] else {}
        merged = _merge(rollup, snapshot)
        store.set_state(c, USAGE_ROLLUP_KEY, json.dumps(merged))

    try:
        if conn is not None:
            _do(conn)
        else:
            with store.connect() as c:
                _do(c)
    except Exception as exc:  # noqa: BLE001 — keep the accum, surface loudly, don't crash
        log.warning("usage_flush_failed", error=str(exc))
        return False

    with _lock:  # drop exactly what we persisted; new spend since stays
        for k in snapshot:
            _accum.pop(k, None)
    log.info("usage_flushed", buckets=len(snapshot))
    return True


# --- Read side: the rollup + budget status (for the panel) -------------------


def load_rollup(conn) -> dict:  # noqa: ANN001
    """The persisted `usage_rollup` ({days: {day: {category: agg}}}) or empty."""
    raw = None
    try:
        from .world import store

        raw = store.get_state(conn, USAGE_ROLLUP_KEY)
    except Exception as exc:  # noqa: BLE001
        log.warning("usage_load_failed", error=str(exc))
    if not raw:
        return {"days": {}}
    try:
        data = json.loads(raw)
        data.setdefault("days", {})
        return data
    except ValueError:
        return {"days": {}}


def day_total_usd(rollup: dict, day_iso: str) -> float:
    """Total dollars spent on `day_iso` across every category."""
    day = rollup.get("days", {}).get(day_iso, {})
    return sum(float(cat.get("usd", 0.0)) for cat in day.values())


def budget_status(rollup: dict, now: datetime | None = None) -> dict:
    """Today's spend vs `budget_daily_usd`, with the alert flag (R5.1)."""
    now = now or datetime.now()
    day_iso = now.date().isoformat()
    spent = day_total_usd(rollup, day_iso)
    limit = float(settings.budget_daily_usd)
    pct = (spent / limit * 100.0) if limit > 0 else 0.0
    alert = pct >= settings.budget_alert_pct
    return {
        "day": day_iso,
        "spent_usd": round(spent, 4),
        "limit_usd": limit,
        "pct": round(pct, 1),
        "alert_pct": settings.budget_alert_pct,
        "alert": alert,
        "over": spent > limit,
    }

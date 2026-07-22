"""R5.1 (=E1.8) — the Budgets screen's read side: spend by job, by day/week.

A pure view over the durable `usage_rollup` world-state row the pipeline flushes
(see `src/usage.py`). It never writes and never generates — it reads the rollup,
sums by category and by day, and hands the panel a budget bar (today's spend vs
`budget_daily_usd`, red past `budget_alert_pct`) plus today + last-7-days tables.

DB-backed, so it degrades to a readable note (never a 500) when the store is down —
same discipline as the dashboard's world panels.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .. import usage
from ..config import settings
from ..logging_setup import get_logger
from ..world import store

log = get_logger(__name__)

# The category order the screen prefers (jobs first, then the utility kinds); any
# category not listed sorts after these, by spend.
_CATEGORY_ORDER = (
    "tick",
    "micro-tick",
    "news",
    "talk",
    "music",
    "commercial",
    "promo",
    "other",
    "tts",
    "embeddings",
)

# Human labels for the categories the ledger buckets under.
_LABELS = {
    "tick": "World tick",
    "micro-tick": "Micro-tick",
    "news": "News desk",
    "talk": "Talk",
    "music": "Music",
    "commercial": "Commercials",
    "promo": "Promos",
    "other": "Other / direct",
    "tts": "TTS (voice)",
    "embeddings": "Embeddings",
}


def _category_row(category: str, agg: dict) -> dict:
    """One category's aggregates as a template-friendly row."""
    return {
        "category": category,
        "label": _LABELS.get(category, category),
        "usd": round(float(agg.get("usd", 0.0)), 4),
        "calls": int(agg.get("calls", 0) or 0),
        "input_tokens": int(agg.get("input_tokens", 0) or 0),
        "output_tokens": int(agg.get("output_tokens", 0) or 0),
        "cache_read_input_tokens": int(agg.get("cache_read_input_tokens", 0) or 0),
        "tts_min": round(float(agg.get("tts_sec", 0.0)) / 60.0, 1),
        "emb_count": int(agg.get("emb_count", 0) or 0),
    }


def _sort_key(category: str) -> tuple[int, str]:
    try:
        return (_CATEGORY_ORDER.index(category), category)
    except ValueError:
        return (len(_CATEGORY_ORDER), category)


def _day_rows(rollup: dict, day_iso: str) -> list[dict]:
    """Per-category rows for one day, ordered by the preferred category order."""
    day = rollup.get("days", {}).get(day_iso, {})
    rows = [_category_row(c, agg) for c, agg in day.items()]
    rows.sort(key=lambda r: _sort_key(r["category"]))
    return rows


def view(now: datetime | None = None) -> dict:
    """Assemble the Budgets view model (DB-backed; degrades to a note if store down)."""
    now = now or datetime.now()
    today = now.date()
    try:
        with store.connect() as conn:
            rollup = usage.load_rollup(conn)
    except Exception as exc:  # noqa: BLE001 — the page degrades, never 500s
        log.warning("panel_budgets_unavailable", error=str(exc))
        return {"available": False, "error": str(exc)}

    budget = usage.budget_status(rollup, now)
    today_iso = today.isoformat()
    today_rows = _day_rows(rollup, today_iso)
    today_total = round(sum(r["usd"] for r in today_rows), 4)

    # Last 7 days (oldest → newest), each with its own total; grand total across them.
    week: list[dict] = []
    week_total = 0.0
    for i in range(6, -1, -1):
        d_iso = (today - timedelta(days=i)).isoformat()
        d_total = round(usage.day_total_usd(rollup, d_iso), 4)
        week_total += d_total
        week.append({"day": d_iso, "usd": d_total, "is_today": d_iso == today_iso})

    return {
        "available": True,
        "error": None,
        "budget": budget,
        "today": today_iso,
        "today_rows": today_rows,
        "today_total": today_total,
        "week": week,
        "week_total": round(week_total, 4),
        "empty": not rollup.get("days"),
    }


def dashboard_bar(now: datetime | None = None) -> dict:
    """The compact budget bar for the dashboard (today's spend vs the daily line)."""
    now = now or datetime.now()
    try:
        with store.connect() as conn:
            rollup = usage.load_rollup(conn)
        status = usage.budget_status(rollup, now)
        status["available"] = True
        return status
    except Exception as exc:  # noqa: BLE001 — the dashboard must never crash on a read
        log.warning("panel_budget_bar_unavailable", error=str(exc))
        return {
            "available": False,
            "spent_usd": 0.0,
            "limit_usd": float(settings.budget_daily_usd),
            "pct": 0.0,
            "alert": False,
        }

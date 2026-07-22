"""E1.0 — the dashboard's read side: gather the same state the console shows.

Every number here comes from the SAME reads the terminal tools use, so the panel
and `make console` / `make health` / `make now-playing` / `make costprobe` can
never disagree:

  * on-air / next   → scheduler.split_schedule (+ onair_hosts, the shared slice)
  * buffer runway   → health._runway_seconds / check_buffer (never recomputed)
  * last top-up     → the scheduler's `last_topup_at` heartbeat + check_last_run
  * health          → the PURE check_* reads (never health.run_checks — that pings
                      the dead-man's switch and POSTs alerts; the console avoids it
                      for the same reason, and the dashboard auto-refreshes)
  * world / stories → the D3 store reads (world_tick heartbeat, active_stories)
  * cost            → the persisted `usage_rollup` (OVERVIEW §2)
  * public feed     → nowplaying.json as-written (what the world actually sees)

STRICTLY READ-ONLY: nothing here opens a write, runs generation, or sends a ping.
Every DB-backed section degrades to a readable note (never a 500) when the DB is
down — the schedule/buffer/heartbeat sections stand alone without it.
"""

from __future__ import annotations

import json
from datetime import datetime

from .. import health
from ..config import settings
from ..logging_setup import get_logger
from ..scheduler import (
    _duration_of,
    _load_state,
    onair_hosts,
    split_schedule,
)
from ..world import events, programming, store

log = get_logger(__name__)


# --- Small helpers -----------------------------------------------------------


def _hhmm(iso: str | None) -> str:
    """`2026-07-21T09:38:00` → `09:38` (the HH:MM off an ISO air stamp)."""
    if not iso or len(iso) < 16:
        return iso or "—"
    return iso[11:16]


def _dur(sec: float) -> str:
    """A length in compact `m:ss`."""
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _age(sec: float) -> str:
    """An elapsed span in human units — `42m`, `6h03m`, `2d05h` (console._age)."""
    sec = int(round(sec))
    if sec < 3600:
        return f"{sec // 60}m"
    if sec < 86400:
        return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"
    return f"{sec // 86400}d{(sec % 86400) // 3600:02d}h"


def _hosts_for(entry: dict) -> str:
    """The hosts on air for an entry — the SAME slice the console + feed show."""
    if not entry.get("program"):  # idents etc. carry no program → no hosts
        return "—"
    try:
        prog = programming.program_for(datetime.fromisoformat(entry["air_time"]))
    except Exception:  # noqa: BLE001 — a display lookup never breaks the dashboard
        return "—"
    return ", ".join(onair_hosts(prog, entry.get("format"))) or "—"


def _entry_row(entry: dict) -> dict:
    """One schedule entry as a template-friendly row."""
    measured = entry.get("actual_duration_sec")
    dur = _dur(_duration_of(entry))
    return {
        "when": _hhmm(entry.get("air_time")),
        "program": entry.get("program_name") or entry.get("program") or "—",
        "format": entry.get("format") or "—",
        "hosts": _hosts_for(entry),
        "dur": dur if measured else f"≈{dur}",
        "id": entry.get("id") or "—",
        "track": (entry.get("track") or {}).get("title"),
    }


# --- The dashboard sections (each defensive; the DB ones may report unavailable) --


def now_next(now: datetime, state: dict) -> dict:
    """ON AIR now + the upcoming queue (the scheduler's live answer)."""
    current, upcoming = split_schedule(now, state)
    cur = None
    if current is not None:
        row = _entry_row(current)
        into = (now - datetime.fromisoformat(current["air_time"])).total_seconds()
        row["into"] = _dur(max(0.0, into))
        cur = row
    limit = settings.programming_console_upcoming
    return {
        "current": cur,
        "upcoming": [_entry_row(e) for e in upcoming[:limit]],
        "upcoming_total": len(upcoming),
    }


def buffer(now: datetime) -> dict:
    """Buffer runway — REUSING the health runway calc (console + health agree)."""
    runway, count = health._runway_seconds(now)
    issue = health.check_buffer(now)  # pure read; no alert/ping side effects
    return {
        "runway_hours": round(runway / 3600, 2),
        "count": count,
        "target_hours": settings.buffer_depth_hours,
        "issue": issue,
        "ok": issue is None,
    }


def last_run(now: datetime, state: dict) -> dict:
    """Scheduler heartbeat — when the last top-up completed (health.check_last_run)."""
    last = state.get("last_topup_at")
    when = "never (no top-up recorded yet)"
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
            when = f"{last[:19]} ({_age(age)} ago)"
        except ValueError:
            when = f"{last!r} (unparseable)"
    issue = health.check_last_run(now)  # pure read
    return {"when": when, "issue": issue, "ok": issue is None}


def health_checks(now: datetime) -> dict:
    """The three PURE health checks (never run_checks — no pings/alerts fired)."""
    checks = [
        ("buffer depth", health.check_buffer(now)),
        ("last run", health.check_last_run(now)),
        ("stream", health.check_stream()),
    ]
    rows = [{"name": n, "issue": issue, "ok": issue is None} for n, issue in checks]
    return {"rows": rows, "ok": all(r["ok"] for r in rows)}


def public_feed() -> dict:
    """The public now-playing feed as-WRITTEN (what the world actually sees)."""
    path = settings.nowplaying_feed_path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"path": str(path), "feed": data, "error": None}
    except FileNotFoundError:
        return {"path": str(path), "feed": None, "error": "not written yet"}
    except Exception as exc:  # noqa: BLE001 — a bad feed file never breaks the page
        return {"path": str(path), "feed": None, "error": str(exc)}


def world_panels(now: datetime) -> dict:
    """The D3 world panels (tick heartbeat, story log, journal, cost) — DB-backed.

    Returns `{"available": False, "error": ...}` (a readable note, not a raise) when
    the DB is unreachable, so the dashboard degrades instead of 500-ing.
    """
    from ..world.world_tick import _TICK_COUNT_KEY, _TICK_LAST_AT_KEY

    try:
        with store.connect() as conn:
            last = store.get_state(conn, _TICK_LAST_AT_KEY)
            tick_when = "never"
            if last:
                tick_when = last[:19]
                try:
                    age = (now - datetime.fromisoformat(last)).total_seconds()
                    tick_when += f" ({_age(age)} ago)"
                except ValueError:
                    pass

            stories = []
            for s in store.active_stories(conn, limit=settings.console_story_limit):
                beats = store.story_beats(conn, s.id)
                beat_rows = []
                for beat in beats[-settings.console_beats_per_story :]:
                    beat_rows.append(
                        {
                            "when": beat.in_world_datetime.strftime("%Y-%m-%d %H:%M"),
                            "title": beat.title,
                            "planned": not events.has_landed(beat, now),
                        }
                    )
                stories.append(
                    {
                        "stage": s.arc_stage,
                        "title": s.title,
                        "tags": list(s.tags),
                        "beats": beat_rows,
                    }
                )

            rollup = store.get_state(conn, "usage_rollup")
            return {
                "available": True,
                "error": None,
                "tick": {
                    "when": tick_when,
                    "count": store.get_state(conn, _TICK_COUNT_KEY) or 0,
                    "active": len(store.active_stories(conn)),
                },
                "stories": stories,
                "journal": store.journal_counts(conn),
                "cost": rollup,
            }
    except Exception as exc:  # noqa: BLE001 — the dashboard must never crash on a read
        log.warning("panel_world_panel_unavailable", error=str(exc))
        return {"available": False, "error": str(exc)}


def dashboard(now: datetime | None = None) -> dict:
    """Assemble the whole dashboard view model (read-only; mutates nothing)."""
    now = now or datetime.now()
    state = _load_state()
    return {
        "now": now,
        "programming_on": settings.programming_enabled,
        "refresh_sec": settings.panel_refresh_sec,
        "host": settings.panel_host,
        "port": settings.panel_port,
        "now_next": now_next(now, state),
        "buffer": buffer(now),
        "last_run": last_run(now, state),
        "health": health_checks(now),
        "feed": public_feed(),
        "world": world_panels(now),
        "budget": _budget_bar(now),
    }


def _budget_bar(now: datetime) -> dict:
    """The dashboard's compact budget bar (R5.1) — today's spend vs the daily line."""
    from .budgets import dashboard_bar

    return dashboard_bar(now)

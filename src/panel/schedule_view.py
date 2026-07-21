"""R5.0 (=E1.7) — the schedule screen: history, on-air, the upcoming queue + retry.

The READ side is a pure view over the SAME `schedule.json` + segment sidecars the
scheduler writes and Liquidsoap plays — `scheduler.split_schedule` is the shared
"what's on now / next" source (so this page and `make console` can never disagree),
and the per-segment `<id>.json` sidecars are the durable record of what aired (with
its script + audio), bounded by the C2.5 retention window.

The WRITE side is deliberately thin and NEVER edits a rendered file (E1 principle
#1): "skip" drops an upcoming entry from the schedule state and rewrites the playout
playlist so playout stops trying to play it; "regenerate" drops it and re-runs the
EXISTING top-up path (the actions page's `schedule` job), which re-renders fresh
audio and re-enters the queue. Both act ONLY on entries that have not started airing
— the on-air segment and the aired history are immutable here. Playout start/stop/
restart live in `actions.py` (the E1.1 mutation lock), wrapping the service commands.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .. import scheduler
from ..config import settings
from ..logging_setup import get_logger
from . import views

log = get_logger(__name__)


# --- Shared normalisation ----------------------------------------------------


def _load_state() -> dict:
    """The live schedule state — the same read the scheduler + dashboard use."""
    return scheduler._load_state()


def _entry_from_sidecar(data: dict) -> dict:
    """A segment sidecar (raw `Segment` asdict) → the flattened schedule-entry shape.

    The sidecar nests program/track under `meta`; the scheduler's live entries have
    them hoisted to the top level (see `scheduler._entry`). Normalise so the same
    `views._entry_row` renders both, and carry the `script` through for history.
    """
    meta = data.get("meta") or {}
    return {
        "id": data.get("id"),
        "format": data.get("format"),
        "program": meta.get("program"),
        "program_name": meta.get("program_name"),
        "track": meta.get("track"),
        "flow_position": meta.get("flow_position"),
        "audio_path": data.get("audio_path"),
        "air_time": data.get("air_time"),
        "actual_duration_sec": data.get("actual_duration_sec"),
        "length_target_sec": data.get("length_target_sec"),
        "script": data.get("script"),
    }


# --- On air + the upcoming queue (the live schedule) -------------------------


def queue_view(now: datetime, state: dict) -> dict:
    """ON AIR now + the upcoming queue with runway (the scheduler's live answer)."""
    current, upcoming = scheduler.split_schedule(now, state)

    cur = None
    if current is not None:
        cur = views._entry_row(current)
        into = (now - datetime.fromisoformat(current["air_time"])).total_seconds()
        cur["into"] = views._dur(max(0.0, into))

    rows = []
    for e in upcoming:
        row = views._entry_row(e)
        try:
            start = datetime.fromisoformat(e["air_time"])
            row["airs_in"] = views._age(max(0.0, (start - now).total_seconds()))
        except (KeyError, ValueError):
            row["airs_in"] = "—"
        rows.append(row)

    if upcoming:
        end = max(scheduler._end_of(e) for e in upcoming)
        runway_sec = max(0.0, (end - now).total_seconds())
    else:
        runway_sec = 0.0

    return {
        "current": cur,
        "upcoming": rows,
        "runway_hours": round(runway_sec / 3600, 2),
        "count": len(rows),
        "target_hours": settings.buffer_depth_hours,
    }


# --- Aired history (from the durable segment sidecars) -----------------------


def _iter_sidecars() -> list[dict]:
    """Every readable segment sidecar (`segments/<id>.json`) as a dict."""
    seg_dir = settings.segments_dir
    if not seg_dir.exists():
        return []
    out: list[dict] = []
    for path in seg_dir.glob("*.json"):
        if path.name == settings.schedule_state_path.name:
            continue  # the schedule state lives here too — not a segment sidecar
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("id"):
            out.append(data)
    return out


def aired_history(now: datetime, *, page: int = 0, per_page: int | None = None) -> dict:
    """The paginated aired history — segments whose air window has fully passed.

    Sourced from the per-segment sidecars (the durable record, kept until the C2.5
    GC prunes the render), newest first. Each row carries its script + an audio link
    if the render still exists on disk.
    """
    per_page = per_page or settings.panel_schedule_history_per_page
    page = max(0, page)

    aired: list[dict] = []
    for data in _iter_sidecars():
        entry = _entry_from_sidecar(data)
        at = entry.get("air_time")
        if not at:
            continue
        try:
            end = scheduler._end_of(entry)
        except (KeyError, ValueError):
            continue
        if end > now:
            continue  # still on air or upcoming — not history
        aired.append(entry)

    aired.sort(key=lambda e: e.get("air_time") or "", reverse=True)
    total = len(aired)
    start = page * per_page
    page_items = aired[start : start + per_page]

    rows = []
    for entry in page_items:
        row = views._entry_row(entry)
        at = entry.get("air_time") or ""
        row["date"] = at[:16].replace("T", " ") if len(at) >= 16 else at
        row["script"] = (entry.get("script") or "").strip()
        row["has_audio"] = _audio_path_for(entry.get("id") or "") is not None
        rows.append(row)

    pages = max(1, -(-total // per_page))  # ceil
    return {
        "rows": rows,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": pages,
        "has_prev": page > 0,
        "has_next": start + per_page < total,
    }


# --- Audio serving (guarded: only a sidecar-backed segment id maps to a file) --


def _audio_path_for(seg_id: str) -> Path | None:
    """`seg_id` → its `segments/<id>.mp3` path, or None (traversal-safe, must exist)."""
    seg_id = (seg_id or "").strip()
    if not seg_id or Path(seg_id).name != seg_id:  # reject any path separator
        return None
    seg_dir = settings.segments_dir.resolve()
    path = (seg_dir / f"{seg_id}.mp3").resolve()
    if path.parent != seg_dir or not path.exists():
        return None
    return path


def audio_path_for(seg_id: str) -> Path | None:
    """Public wrapper for the route (the guard lives in `_audio_path_for`)."""
    return _audio_path_for(seg_id)


# --- Write side: drop an upcoming entry (skip) or drop-and-refill (regenerate) --


def drop_upcoming(seg_id: str, now: datetime | None = None) -> dict | None:
    """Remove an UPCOMING entry from the schedule state; rewrite the playlist.

    Returns the removed entry, or None when `seg_id` is unknown or has already
    started airing (the on-air/aired slots are immutable — never edit a rendered
    file). The audio render is left on disk for the C2.5 GC to reclaim; only the
    schedule pointer is dropped, so playout stops queuing it on the next reload.
    """
    now = now or datetime.now()
    state = _load_state()
    entries = state.get("entries", [])

    target: dict | None = None
    for e in entries:
        if e.get("id") != seg_id:
            continue
        try:
            start = datetime.fromisoformat(e["air_time"])
        except (KeyError, ValueError):
            break
        if start > now:  # only a not-yet-started slot may be dropped
            target = e
        break

    if target is None:
        return None

    state["entries"] = [e for e in entries if e is not target]
    scheduler._save_state(state)
    # Rewrite the playout playlist immediately so a live playout stops queuing the
    # dropped render on its next watch-reload (the same helper the scheduler uses).
    scheduler._write_playlist(state["entries"], now)
    log.info(
        "panel_schedule_drop",
        seg_id=seg_id,
        program=target.get("program"),
        air_time=target.get("air_time"),
    )
    return target

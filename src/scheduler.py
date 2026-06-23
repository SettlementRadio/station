"""C2 — the rolling scheduler (Layer 5): what airs, when, on real durations.

The real 24/7 replacement for the one-shot B6 `build_buffer`. Where `make buffer`
generated a fixed block once and trusted `length_target_sec`, the scheduler keeps a
*rolling* buffer of upcoming audio at `settings.buffer_depth_hours` of MEASURED
duration, decides the airing order, regenerates/skips a failed slot without leaving
dead air, and writes an ordered playlist Liquidsoap re-reads — the Layer 5 <-> playout
seam that turns "a folder of clips" into "a programmed station".

How a top-up run works (one call to `top_up`, run periodically — cron/systemd in C5):

  1. Load the persisted schedule (`settings.schedule_state_path`): the ordered list
     of segments already placed, with their air-time and measured duration.
  2. PRUNE entries that have fully aired (their air window ends at/before now) or whose
     audio file has vanished. What's left is the buffer still ahead of the needle.
  3. Measure the remaining runway = (end of the last upcoming segment) − now. Because
     segments are placed back-to-back, that span IS the un-aired audio depth.
  4. While the runway is shorter than `buffer_depth_hours`, GENERATE the next segment
     (cycling `settings.buffer_rotation`), placing it at the running air-cursor; advance
     the cursor by the segment's MEASURED duration (`make_format_segment` stamps it).
  5. On a generation error, retry the slot (`schedule_failure_max_retries`) then SKIP to
     the next format — never write a dead slot. If a whole rotation fails, stop this run
     (the existing buffer/fallback keeps the air live) and let the next run retry.
  6. Persist the schedule and write the ordered playlist
     (`settings.schedule_playlist_path`) of upcoming audio paths, in air order.

`buffer_depth_hours` is the lead-time dial: a deeper buffer is more resilient to a slow
or failed generation run; driving it toward ~0 (plus streaming TTS) is what later
enables near-live (Phase E). The scheduler never airs anything — it only decides and
records; Liquidsoap (config/radio.liq) airs the playlist and owns the never-dead
fallback chain.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings
from .formats import make_format_segment
from .logging_setup import get_logger
from .segment import Segment

log = get_logger(__name__)


# --- Schedule state (the on-disk record of what airs when) ------------------


def _load_state() -> dict:
    """Read the persisted schedule, or a fresh empty one on first run."""
    path = settings.schedule_state_path
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"entries": [], "rotation_index": 0}


def _save_state(state: dict) -> None:
    """Persist the schedule so the next top-up continues where this one left off."""
    settings.schedule_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.schedule_state_path.write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def _entry(seg: Segment) -> dict:
    """The schedule record for a placed segment — the timing-relevant slice."""
    return {
        "id": seg.id,
        "format": seg.format,
        "audio_path": seg.audio_path,
        "air_time": seg.air_time,
        # Schedule on MEASURED duration; fall back to the target only if a probe
        # failed (actual_duration_sec is None) so timing never silently breaks.
        "actual_duration_sec": seg.actual_duration_sec,
        "length_target_sec": seg.length_target_sec,
    }


def _duration_of(entry: dict) -> float:
    """A schedule entry's airtime length: measured if known, else the target."""
    measured = entry.get("actual_duration_sec")
    if measured:
        return float(measured)
    return float(entry.get("length_target_sec") or 0)


def _end_of(entry: dict) -> datetime:
    """When an entry finishes airing (its air-time plus its duration)."""
    return datetime.fromisoformat(entry["air_time"]) + timedelta(
        seconds=_duration_of(entry)
    )


def _write_playlist(entries: list[dict]) -> Path:
    """Write the ordered upcoming audio paths for Liquidsoap to re-read.

    One absolute path per line, in air order — the Layer 5 <-> playout seam. Only
    files that actually exist are listed (a vanished render is skipped, never aired
    as a gap). Always written, even empty, so playout has a stable file to watch.
    """
    path = settings.schedule_playlist_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        str(Path(e["audio_path"]).resolve())
        for e in entries
        if e.get("audio_path") and Path(e["audio_path"]).exists()
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


# --- Generation (with bounded retry) ----------------------------------------


def _generate_slot(name: str, air_cursor: datetime) -> Segment | None:
    """Produce one segment for `name` at `air_cursor`, bounded-retrying on error.

    `make_format_segment` already handles *content* failure internally (the safety /
    continuity gates fall back to an evergreen), so a raise here is an INFRASTRUCTURE
    failure (Claude/TTS/DB). We retry it `schedule_failure_max_retries` times, then
    give up on this slot (the caller skips it — never dead air).
    """
    attempts = settings.schedule_failure_max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            seg = make_format_segment(name, air_cursor.isoformat())
            seg.air_time = air_cursor.isoformat()  # pin the slot's air-time
            return seg
        except Exception as exc:
            log.error(
                "schedule_generate_error",
                format=name,
                attempt=attempt,
                of=attempts,
                error=str(exc),
            )
    return None


# --- The top-up: refill the rolling buffer to depth -------------------------


def top_up(now: datetime | None = None) -> list[dict]:
    """Refill the rolling buffer to `buffer_depth_hours`; return the upcoming entries.

    Idempotent and safe to run on any cadence: if the buffer is already at depth it
    generates nothing and just rewrites the (pruned) playlist. Returns the upcoming
    schedule entries in air order.
    """
    now = now or datetime.now()
    rotation = settings.buffer_rotation
    if not rotation:
        raise ValueError("buffer_rotation is empty — nothing to schedule")
    depth_target_sec = settings.buffer_depth_hours * 3600

    state = _load_state()
    # 1-2. Keep only entries still ahead of the needle whose audio still exists.
    upcoming = [
        e
        for e in state["entries"]
        if _end_of(e) > now and e.get("audio_path") and Path(e["audio_path"]).exists()
    ]

    # 3. Runway = how much un-aired audio is queued ahead (segments are contiguous).
    if upcoming:
        air_cursor = max(_end_of(e) for e in upcoming)
        runway_sec = (air_cursor - now).total_seconds()
    else:
        air_cursor = now
        runway_sec = 0.0

    rot_i = state.get("rotation_index", 0)
    log.info(
        "schedule_topup_start",
        now=now.isoformat(),
        upcoming=len(upcoming),
        runway_sec=round(runway_sec),
        depth_target_sec=round(depth_target_sec),
        rotation=rotation,
    )

    added = 0
    consecutive_skips = 0
    while (
        runway_sec < depth_target_sec and added < settings.schedule_topup_max_segments
    ):
        name = rotation[rot_i % len(rotation)]
        seg = _generate_slot(name, air_cursor)
        if seg is None:
            # This slot's format failed even after retries — skip it, advance the
            # rotation, and try the next format. If the WHOLE rotation fails in a
            # row, the generator is down: stop this run and let playout keep airing
            # the existing buffer/fallback (never dead air); the next run retries.
            rot_i += 1
            consecutive_skips += 1
            if consecutive_skips >= len(rotation):
                log.error(
                    "schedule_topup_stalled",
                    added=added,
                    runway_sec=round(runway_sec),
                )
                break
            continue
        consecutive_skips = 0

        entry = _entry(seg)
        duration = _duration_of(entry)
        upcoming.append(entry)
        air_cursor += timedelta(seconds=duration)
        runway_sec += duration
        rot_i += 1
        added += 1
        log.info(
            "schedule_slot_added",
            seg_id=seg.id,
            format=seg.format,
            air_time=entry["air_time"],
            duration_sec=round(duration, 1),
            runway_sec=round(runway_sec),
        )

    state["entries"] = upcoming
    state["rotation_index"] = rot_i % len(rotation)
    _save_state(state)
    playlist_path = _write_playlist(upcoming)

    log.info(
        "schedule_topup_done",
        added=added,
        upcoming=len(upcoming),
        runway_sec=round(runway_sec),
        playlist=str(playlist_path),
    )
    return upcoming


def main(argv: list[str]) -> int:
    """CLI: run one top-up, or loop every N seconds with `--interval N`.

    .venv/bin/python -m src.scheduler                 (one top-up; cron/systemd in C5)
    .venv/bin/python -m src.scheduler --interval 300  (local: top up every 5 min)

    Needs `make seed` + a populated .env (live Claude + TTS).
    """
    interval: float | None = None
    if len(argv) >= 2 and argv[0] == "--interval":
        try:
            interval = float(argv[1])
        except ValueError:
            print(
                f"usage: python -m src.scheduler [--interval SECONDS]; got {argv[1]!r}"
            )
            return 2

    def _run_once() -> None:
        upcoming = top_up()
        total = sum(_duration_of(e) for e in upcoming)
        print(f"\n----- SCHEDULE: {len(upcoming)} segment(s) upcoming -----")
        for e in upcoming:
            dur = _duration_of(e)
            measured = "≈" if not e.get("actual_duration_sec") else " "
            print(
                f"  {e['air_time']}  {e['format']:9}  {measured}{dur:>5.0f}s  {e['id']}"
            )
        print(
            f"\n  runway ~{total / 3600:.2f}h (target {settings.buffer_depth_hours}h) "
            f"-> {settings.schedule_playlist_path}"
        )

    _run_once()
    if interval is not None:
        print(f"\n(looping: topping up every {interval:.0f}s — Ctrl-C to stop)")
        try:
            while True:
                time.sleep(interval)
                _run_once()
        except KeyboardInterrupt:
            print("\nstopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

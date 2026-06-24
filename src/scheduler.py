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
  7. PRUNE the disk (C2.5): delete aired, unreferenced one-shot renders whose air
     end is past the `settings.segment_retention_hours` grace window, so a 24/7
     station can't fill the box. The shared disclosure ident clip, the C4 evergreen
     pool, and everything under `assets/` are never collected (see `prune()`).

Each run also (C4) refreshes the never-dead playout fallback assets up front
(`ensure_fallback_assets` — evergreen pool + ident, rendered while healthy) and
records a `last_topup_at` heartbeat so `src/health.py` can detect a dead generator.

As it places content, the scheduler also weaves a spoken AI-disclosure ident
(src/disclosure.py) into the order every `settings.disclosure_every_n` content
segments (C3), so the live stream audibly discloses on a regular cadence — the
ident is just another entry in the ordered playlist, so playout needs no change.

`buffer_depth_hours` is the lead-time dial: a deeper buffer is more resilient to a slow
or failed generation run; driving it toward ~0 (plus streaming TTS) is what later
enables near-live (Phase E). The scheduler never airs anything — it only decides and
records; Liquidsoap (config/radio.liq) airs the playlist and owns the never-dead
fallback chain.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings
from .disclosure import disclosure_ident_segment
from .evergreen import EVERGREEN_NAME_PREFIX
from .fallback import ensure_fallback_assets
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


def _write_sidecar(seg: Segment) -> None:
    """Write `segments/<id>.json` next to the render so it self-describes (C2.5).

    Parity with the B6 buffer's sidecar: it records the segment's `air_time` and
    measured duration, which is what `prune()` reads to compute a render's air end
    *after* it has aired and left the live schedule. Best-effort — a sidecar write
    failure is logged, never fatal (the audio aired fine; the GC just falls back to
    the file's mtime for that one render). The shared disclosure ident has no
    per-id sidecar: its audio is one reused clip, protected by name, not by age.
    """
    if not seg.audio_path:
        return
    path = settings.segments_dir / f"{seg.id}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dataclasses.asdict(seg), indent=2), encoding="utf-8")
    except OSError as exc:  # disk full / perms — don't kill a segment that rendered
        log.warning("schedule_sidecar_write_failed", seg_id=seg.id, error=str(exc))


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

    # C4 — refresh the never-dead playout fallback assets (evergreen pool + ident +
    # the evergreen playlist Liquidsoap watches) WHILE the system is healthy, so a
    # clean spoken segment is ready if a later outage drains the buffer. Best-effort
    # and cached after the first run; a failure here must never block a top-up.
    try:
        ensure_fallback_assets()
    except Exception as exc:  # noqa: BLE001 — fallback prep is housekeeping, not air
        log.error("fallback_assets_error", error=str(exc))

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
    # C3: count CONTENT segments placed since the last disclosure ident, persisted
    # across runs so the spoken-disclosure cadence is steady regardless of pruning.
    content_since_ident = state.get("content_since_ident", 0)
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
        # C3 — weave the spoken AI-disclosure ident on a regular cadence: every
        # `disclosure_every_n` CONTENT segments, place one ident at the cursor so
        # the live stream audibly discloses. The ident is static + cached (no
        # gates, rendered once and reused), so this is cheap. Reset the counter
        # first so a render failure (logged) skips this ident rather than blocking
        # content or spinning; the next cadence still fires.
        if (
            settings.disclosure_enabled
            and settings.disclosure_every_n > 0
            and content_since_ident >= settings.disclosure_every_n
        ):
            content_since_ident = 0
            try:
                ident = disclosure_ident_segment(air_cursor)
                ident.air_time = air_cursor.isoformat()
                entry = _entry(ident)
                duration = _duration_of(entry)
                upcoming.append(entry)
                air_cursor += timedelta(seconds=duration)
                runway_sec += duration
                added += 1
                log.info(
                    "schedule_ident_added",
                    seg_id=ident.id,
                    air_time=entry["air_time"],
                    duration_sec=round(duration, 1),
                    runway_sec=round(runway_sec),
                )
            except Exception as exc:
                log.warning("schedule_ident_error", error=str(exc))
            continue

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

        # Self-describing sidecar so prune() can read this render's air end once it
        # has aired out of the live schedule (C2.5). Written with the pinned slot
        # air_time already set on the segment by `_generate_slot`.
        _write_sidecar(seg)
        entry = _entry(seg)
        duration = _duration_of(entry)
        upcoming.append(entry)
        air_cursor += timedelta(seconds=duration)
        runway_sec += duration
        rot_i += 1
        added += 1
        content_since_ident += 1
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
    state["content_since_ident"] = content_since_ident
    # C4 — heartbeat: record that a top-up ran to completion. `src/health.py`
    # check_last_run() reads this to detect a generator that has stopped running.
    state["last_topup_at"] = now.isoformat()
    _save_state(state)
    playlist_path = _write_playlist(upcoming)

    log.info(
        "schedule_topup_done",
        added=added,
        upcoming=len(upcoming),
        runway_sec=round(runway_sec),
        playlist=str(playlist_path),
    )

    # C2.5 — bound the segment disk: GC aired, unreferenced renders. Runs on the
    # freshly-saved state so it sees the same `upcoming` set as protected. Failures
    # here must never break a top-up (the air is fed; disk GC is housekeeping).
    try:
        prune(now)
    except Exception as exc:  # noqa: BLE001 — housekeeping must not break playout
        log.error("prune_error", error=str(exc))

    return upcoming


# --- C2.5: disk retention — GC aired, unreferenced one-shot renders ----------
# The shared disclosure ident clip is rendered once and reused by EVERY ident slot
# (src/disclosure.py), so it must survive even when an ident entry ages out. We
# exempt it by the stable name prefix `disclosure.render_ident_audio` writes.
# Likewise the C4 evergreen POOL (src/evergreen.py): render-once, reuse-forever
# clips for the never-dead playout fallback — exempt by their `evergreen-` prefix.
# (The C0 on-demand evergreen renders into a slot's <id>.mp3, NOT this prefix, so
# those are still GC'd like any one-shot.)
_IDENT_NAME_PREFIX = "ident-disclosure-"
_GC_EXEMPT_PREFIXES = (_IDENT_NAME_PREFIX, EVERGREEN_NAME_PREFIX)


def _referenced_audio(state: dict) -> set[str]:
    """Resolved audio paths still in the live schedule — never deleted by prune."""
    referenced: set[str] = set()
    for e in state.get("entries", []):
        ap = e.get("audio_path")
        if ap:
            referenced.add(str(Path(ap).resolve()))
    return referenced


def _air_end_from_sidecar(sidecar: Path) -> datetime | None:
    """A render's air end from its `<id>.json` sidecar (air_time + duration), or None.

    Returns None when the sidecar is missing or unparseable so the caller can fall
    back to the file's mtime — the sidecar is the precise signal (it survives the
    schedule-entry pruning), mtime is the safety net for pre-C2.5 renders.
    """
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not data.get("air_time"):
        return None
    try:
        return _end_of(data)  # reuses air_time + measured/target duration
    except (KeyError, ValueError):
        return None


def prune(now: datetime | None = None) -> dict:
    """Delete aired, unreferenced one-shot renders from `segments_dir` (C2.5).

    A `<id>.mp3` (and its `<id>.json` sidecar) is removed only when ALL hold:
      (a) it is NOT referenced by any live schedule entry's audio (the live state);
      (b) its air end is more than `segment_retention_hours` in the past — the grace
          window (from the sidecar; mtime if no sidecar);
      (c) it is a per-segment render under `segments_dir` (the glob's scope).

    NEVER touched: the shared, reused clips — the disclosure ident
    (`ident-disclosure-*.mp3`) and the C4 evergreen pool (`evergreen-*.mp3`),
    both render-once/reuse-forever; anything under `assets/` (this only ever scans
    `segments_dir`); and any file still in the live playlist/schedule. An optional
    `segment_retention_max_gb` backstop then deletes the oldest aired renders —
    ignoring the grace window — if the directory is still over the cap. Returns a
    summary `{files, bytes}` for the caller/log.
    """
    now = now or datetime.now()
    seg_dir = settings.segments_dir
    if not seg_dir.exists():
        return {"files": 0, "bytes": 0}

    referenced = _referenced_audio(_load_state())
    retention_sec = settings.segment_retention_hours * 3600

    removed_files = 0
    removed_bytes = 0
    # Survivors that COULD be GC'd later (aired one-shot renders kept only by the
    # grace window) — the candidate pool the size backstop draws from, oldest first.
    survivors: list[tuple[datetime, Path, Path | None]] = []

    for mp3 in sorted(seg_dir.glob("*.mp3")):
        # Protect the shared, reused clips (the disclosure ident + the C4 evergreen
        # pool): deleting one because an entry aged out would break a future
        # fallback/ident or force a needless re-render.
        if mp3.name.startswith(_GC_EXEMPT_PREFIXES):
            continue
        # Protect anything still in the live schedule/playlist.
        if str(mp3.resolve()) in referenced:
            continue

        sidecar = mp3.with_suffix(".json")
        sidecar = sidecar if sidecar.exists() else None
        air_end = _air_end_from_sidecar(mp3.with_suffix(".json"))
        if air_end is None:
            air_end = datetime.fromtimestamp(mp3.stat().st_mtime)

        if (now - air_end).total_seconds() <= retention_sec:
            survivors.append((air_end, mp3, sidecar))  # within grace — keep for now
            continue

        removed_files += 1
        removed_bytes += _delete_render(mp3, sidecar, "aged_out", now - air_end)

    # Optional emergency backstop: if still over the cap, delete oldest aired
    # renders that were spared only by the grace window, oldest first, until under.
    cap_gb = settings.segment_retention_max_gb
    if cap_gb is not None and cap_gb > 0:
        cap_bytes = int(cap_gb * 1024**3)
        total = sum(f.stat().st_size for f in seg_dir.glob("*") if f.is_file())
        if total > cap_bytes:
            log.warning("prune_over_cap", total_bytes=total, cap_bytes=cap_bytes)
            for air_end, mp3, sidecar in sorted(survivors, key=lambda s: s[0]):
                if total <= cap_bytes:
                    break
                freed = _delete_render(mp3, sidecar, "over_cap", now - air_end)
                total -= freed
                removed_files += 1
                removed_bytes += freed

    log.info("prune_done", files=removed_files, bytes=removed_bytes)
    return {"files": removed_files, "bytes": removed_bytes}


def _delete_render(mp3: Path, sidecar: Path | None, reason: str, age) -> int:
    """Delete a render's `<id>.mp3` (+ sidecar); return bytes reclaimed. Best-effort."""
    freed = 0
    for f in (mp3, sidecar):
        if f is None:
            continue
        try:
            size = f.stat().st_size
            f.unlink()
            freed += size  # count only what was actually removed
        except OSError as exc:
            log.warning("prune_unlink_failed", file=str(f), error=str(exc))
    log.info(
        "prune_removed",
        seg=mp3.stem,
        reason=reason,
        age_sec=round(age.total_seconds()),
        bytes=freed,
    )
    return freed


def main(argv: list[str]) -> int:
    """CLI: run one top-up, or loop every N seconds with `--interval N`.

    .venv/bin/python -m src.scheduler                 (one top-up; cron/systemd in C5)
    .venv/bin/python -m src.scheduler --interval 300  (local: top up every 5 min)
    .venv/bin/python -m src.scheduler --prune         (C2.5: run only the disk GC)

    Needs `make seed` + a populated .env (live Claude + TTS).
    """
    if argv and argv[0] == "--prune":
        # Just the C2.5 GC — no generation, so no Claude/TTS needed. Handy for
        # verifying retention against the segments already on disk.
        result = prune()
        print(
            f"\n----- PRUNE: removed {result['files']} file(s), "
            f"{result['bytes'] / 1024**2:.1f} MB "
            f"(retention {settings.segment_retention_hours}h) "
            f"from {settings.segments_dir} -----"
        )
        return 0

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

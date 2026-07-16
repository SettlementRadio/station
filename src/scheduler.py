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

D7.2 extends the same weave to the production layer (src/production/placement.py):
a program's theme (plus the handover sting for handover shows) opens each program
BOUNDARY the grid crosses, the C8 sting fires immediately before every news
bulletin, and the A1 sung station ident airs every
`settings.production_ident_every_n` content segments — all static, curated
`assets/` clips placed as ordered entries (reused, gate-free, GC-safe by
location), never re-rendered. D7.3 adds beds: where the grid calls for it
(production_bedded_programs × _formats), the slot's speech is re-baked over a
ducked bed at render time (placement.apply_bed) and re-measured on the final
mixed audio.

D8.1 weaves sparse AD BREAKS the same way: the GRID decides the cadence (a
program's `break_every: N` = one break per N content segments while it's on
air; most shows take none), and when it fires the scheduler generates 1..
`commercial_break_max_segments` fresh `commercial`/`promo` spots (never a
prerecorded reel; every `commercial_break_promo_every_n`-th spot is a promo)
and brackets them with the D18 break_in/break_out stings — ordered entries,
playout unchanged, no program-clock atom consumed.

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

from . import flow as flow_mod
from .config import settings
from .disclosure import disclosure_ident_segment
from .evergreen import EVERGREEN_NAME_PREFIX
from .fallback import ensure_fallback_assets
from .flow import ShowFlow
from .formats import FORMATS, make_format_segment
from .formats.sponsor import pick_sponsor, sponsor_read_segment
from .freshness import record_segment as record_airplay_features
from .freshness import sweep as sweep_airplay
from .logging_setup import get_logger
from .production.placement import (
    apply_bed,
    boundary_segments,
    break_sting_segment,
    news_sting_segment,
    station_ident_segment,
)
from .segment import Segment
from .world import programming, store
from .world.programming import Program
from .writers.journal import capture_segment as capture_journal

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
        # D6.2 — the program that placed this slot (None for idents / the flat path),
        # so the D6.3 console + D6.4 now-playing feed can name what's on without
        # recomputing the grid. Read from the segment meta the scheduler stamped.
        "program": seg.meta.get("program"),
        "program_name": seg.meta.get("program_name"),
        # D7.4 — the spun track's PUBLIC lore (title/artist/album/era), set by the
        # music format; None elsewhere. The now-playing feed shows it (D6.4).
        "track": seg.meta.get("track"),
        # D12 — the talk slot's show position (open/continue/close), stamped by the
        # writers' room; None for non-talk / the flat path. Lets the acceptance flow
        # check and any inspector see that a show opens once, not every segment.
        "flow_position": seg.meta.get("flow_position"),
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


def split_schedule(now: datetime, state: dict) -> tuple[dict | None, list[dict]]:
    """Partition the live schedule at `now`: (current on-air entry, upcoming entries).

    A pure read over a loaded state dict — the SHARED source for the D6.3 operator
    console and the D6.4 public now-playing feed, so both agree on what's "on now" vs
    "next". Entries whose air window has fully passed are dropped; the current one is
    the entry whose `[air_time, end)` contains `now`; upcoming are those starting at/
    after `now`, in air order.
    """
    entries = sorted(state.get("entries", []), key=lambda e: e.get("air_time") or "")
    current: dict | None = None
    upcoming: list[dict] = []
    for e in entries:
        try:
            start = datetime.fromisoformat(e["air_time"])
            end = _end_of(e)
        except (KeyError, ValueError):
            continue
        if start <= now < end and current is None:
            current = e
        elif start >= now:
            upcoming.append(e)
    return current, upcoming


def _write_playlist(entries: list[dict], now: datetime | None = None) -> Path:
    """Write the ordered upcoming audio paths for Liquidsoap to re-read.

    One absolute path per line, in air order — the Layer 5 <-> playout seam. Only
    files that actually exist are listed (a vanished render is skipped, never aired
    as a gap). Always written, even empty, so playout has a stable file to watch.

    When `now` is given, entries whose air window has already fully passed are
    dropped, so the FIRST line is always the segment that should be playing now.
    Liquidsoap watches this file and resets to the top of the list on every reload
    (`reload_mode="watch"`), so a stale already-aired entry at the head would make a
    reload snap playout back to it — the head must stay current.
    """
    path = settings.schedule_playlist_path
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        str(Path(e["audio_path"]).resolve())
        for e in entries
        if e.get("audio_path")
        and Path(e["audio_path"]).exists()
        and (now is None or _end_of(e) > now)
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return path


# --- Generation (with bounded retry) ----------------------------------------


def _generate_slot(
    name: str,
    air_cursor: datetime,
    speakers: list[str] | None = None,
    flow: ShowFlow | None = None,
) -> Segment | None:
    """Produce one segment for `name` at `air_cursor`, bounded-retrying on error.

    `make_format_segment` already handles *content* failure internally (the safety /
    continuity gates fall back to an evergreen), so a raise here is an INFRASTRUCTURE
    failure (Claude/TTS/DB). We retry it `schedule_failure_max_retries` times, then
    give up on this slot (the caller skips it — never dead air). `speakers` (D6.2) is
    the active program's hosts routed into the format; None keeps the format default.
    `flow` (D12.0) is the slot's show-position + talk hand-off substrate (only the
    talk format reads it); None keeps the standalone shape.
    """
    attempts = settings.schedule_failure_max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            seg = make_format_segment(
                name, air_cursor.isoformat(), speakers=speakers, flow=flow
            )
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


def _program_speakers(program: Program, name: str) -> list[str] | None:
    """The active program's hosts, sliced to what format `name` needs (D6.2).

    A format declares how many voices it wants via `FORMATS[name].speaker_ids()` (news
    = 1 anchor, talk = 2). We take that many of the program's hosts, lead-first — so
    the grid drives who's on air (day news anchored by the day host, etc.). When the
    program under-specifies (fewer hosts than the format needs, e.g. a solo program
    carrying a talk step), we fall back to the format's own default cast (None) so
    generation never breaks on an authoring gap.
    """
    default = list(FORMATS[name].speaker_ids())
    need = len(default)
    # D12.4 — the news bulletin is read by the DEDICATED news desk, not the show's
    # lead: a real station cuts to a fixed newsreader (consistent register) and hands
    # back. `news_anchor_ids` empty = the pre-D12.4 program-lead read (the rollback).
    if name == "news" and settings.news_anchor_ids:
        return list(settings.news_anchor_ids)[:need] or None
    hosts = list(program.hosts)
    if need > 0 and len(hosts) >= need:
        return hosts[:need]
    return None


def _show_flow(
    program: Program,
    air_cursor: datetime,
    last_content_program: str | None,
    handoff: flow_mod.Handoff | None,
    thread_run: int,
) -> ShowFlow:
    """The `ShowFlow` for a grid content slot: position, hand-off, thread decision.

    D12.0 — `open` when this is the first content slot of a NEW program instance (the
    program differs from the last placed content slot); `close` when the NEXT content
    slot is estimated to fall in a different program; `continue` otherwise. The `close`
    look-ahead uses the default slot length as the horizon — best-effort, since a
    slot's real duration isn't known until it renders (flow is advisory, never a hard
    dependency, per the D12 principles).

    D12.2 — decide whether this slot CONTINUES the carried thread: only mid-show
    (`continue`/`close`, never a fresh program `open`), with a live hand-off whose
    thread is still open, and within the `convo_continuity_max_segments` pacing budget.
    A new program always opens fresh; a spent or over-budget thread transitions.

    Audit fix 4 — a STALE hand-off (older than `convo_continuity_handoff_max_age_min`
    of air time: the scheduler was down, the buffer jumped) is dropped here, so a
    restart inside the same daily program never resumes yesterday's conversation.
    """
    is_first = program.id != last_content_program
    est_end = air_cursor + timedelta(seconds=settings.segment_default_length_target_sec)
    is_last = programming.program_for(est_end).id != program.id
    position = flow_mod.show_position(is_first=is_first, is_last=is_last)
    handoff = flow_mod.live_handoff(
        handoff, air_cursor, settings.convo_continuity_handoff_max_age_min
    )
    continue_thread = (
        settings.convo_continuity_enabled
        and position != flow_mod.OPEN
        and handoff is not None
        and handoff.open_thread
        and thread_run < settings.convo_continuity_max_segments
    )
    return ShowFlow(
        position=position,
        handoff=handoff,
        thread_run=thread_run,
        continue_thread=continue_thread,
        program_name=program.name,  # D12.4 — for the spoken sign-on/sign-off by name
        guest_chance=program.guest_chance,  # D12.4 — this show's interview cadence
    )


def onair_hosts(program: Program, fmt: str) -> list[str]:
    """The cast ids actually on air for `fmt` under `program` — the DISPLAY answer.

    The single source the D6.3 console and the D6.4 feed both use to name who's on air,
    so they never disagree. Same routing as `_program_speakers` (talk = both hosts, a
    single-voice news/music desk = the lead), but always returns concrete ids: it falls
    back to the format's own default cast when the program under-specifies, and to the
    program's hosts for a non-registry format.
    """
    if fmt not in FORMATS:  # a non-registry slot (e.g. an ident) -> the show's cast
        return list(program.hosts)
    routed = _program_speakers(program, fmt)
    return routed if routed is not None else list(FORMATS[fmt].speaker_ids())


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
    # D6.2 — per-program clock cursors (`{pid: {seq, rot}}`) plus one GLOBAL previous
    # air-cursor (`_last_cursor`), both persisted so each program's sequence advances
    # across top-up runs and pinned top-of-hour slots fire on the continuous timeline
    # (even across program boundaries), not per-program.
    clock_state: dict = state.get("clock_state", {})
    prev_cursor: datetime | None = None
    if clock_state.get("_last_cursor"):
        try:
            prev_cursor = datetime.fromisoformat(clock_state["_last_cursor"])
        except ValueError:
            prev_cursor = None
    # D12.0 — the talk-continuity substrate, persisted in clock_state alongside the
    # clocks so it survives across top-up runs: the program of the last placed
    # CONTENT slot (→ is this slot the OPEN of a new program instance?) and the last
    # talk hand-off (the thread the next talk segment can pick up). Both live under
    # the underscore-keyed `_flow`, so they never collide with a program id.
    flow_state = clock_state.get("_flow") or {}
    flow_last_program: str | None = flow_state.get("last_content_program")
    flow_handoff: flow_mod.Handoff | None = (
        flow_mod.Handoff.from_dict(flow_state["handoff"])
        if isinstance(flow_state.get("handoff"), dict)
        else None
    )
    # D12.2 — how many talk segments the current thread has already aired (the pacing
    # budget counter); persisted so a thread paces correctly across top-up runs.
    flow_thread_run: int = int(flow_state.get("thread_run", 0))
    # C3: count CONTENT segments placed since the last disclosure ident, persisted
    # across runs so the spoken-disclosure cadence is steady regardless of pruning.
    content_since_ident = state.get("content_since_ident", 0)
    # D7.2: the production-layer counterparts, persisted the same way — the A1
    # station-ident cadence and the program whose boundary was last opened (so a
    # boundary that falls BETWEEN two top-up runs still gets its theme).
    content_since_station_ident = state.get("content_since_station_ident", 0)
    last_program_id: str | None = state.get("last_program_id")
    # D8.1: the ad-break cadence — content placed since the last break (reset at
    # each program boundary so every show's ad load starts fresh), plus a running
    # total of break spots ever placed (drives the commercial-vs-promo rotation
    # across breaks). Both persisted so the cadence is steady across top-ups.
    content_since_break = state.get("content_since_break", 0)
    break_spots_total = state.get("break_spots_total", 0)
    # D8.2: breaks placed (drives the every-Nth-break sponsor-read cadence) and
    # sponsor reads placed (drives the weighted rotation among active sponsors).
    breaks_total = state.get("breaks_total", 0)
    sponsor_reads_total = state.get("sponsor_reads_total", 0)

    def _place_clip(seg: Segment) -> None:
        """Weave one curated production clip (D7.2) into the order at the cursor.

        The clip's audio is a REUSED `assets/` file (GC-safe by location, no
        sidecar, not airplay-recorded — it is meant to repeat), so placing it is
        pure bookkeeping: pin, append, advance the cursor by its measured length.
        """
        nonlocal air_cursor, runway_sec, added
        seg.air_time = air_cursor.isoformat()
        entry = _entry(seg)
        duration = _duration_of(entry)
        upcoming.append(entry)
        air_cursor += timedelta(seconds=duration)
        runway_sec += duration
        added += 1
        log.info(
            "schedule_clip_added",
            seg_id=seg.id,
            format=seg.format,
            air_time=entry["air_time"],
            duration_sec=round(duration, 1),
            runway_sec=round(runway_sec),
        )

    def _place_break(program: Program) -> None:
        """Weave one sparse ad break at the cursor (D8.1): sting → spot(s) → sting.

        The spots are GENERATED fresh each break (never a rotating reel — the
        D8 load-bearing principle) via the normal slot path, so the C0 gates +
        evergreen fallback apply; every `commercial_break_promo_every_n`-th
        spot (counted across breaks) is a station promo. Spots generate FIRST:
        if none does, nothing is placed (a lone sting bracket would be noise).
        Placed spots ride the normal entry mechanism (sidecar, airplay memory,
        honest measured duration) but consume no program-clock atom — a break
        interrupts the show, it isn't part of its clock. The D18 break stings
        bracket the spots; a missing sting clip degrades to an unbracketed
        break (media logs it), never a lost break.
        """
        nonlocal air_cursor, runway_sec, added, break_spots_total
        nonlocal content_since_ident, content_since_station_ident
        nonlocal breaks_total, sponsor_reads_total
        spots: list[Segment] = []
        promo_n = settings.commercial_break_promo_every_n
        for _ in range(max(settings.commercial_break_max_segments, 1)):
            is_promo = promo_n > 0 and (break_spots_total + 1) % promo_n == 0
            mode = "promo" if is_promo else "commercial"
            spot = _generate_slot(mode, air_cursor, _program_speakers(program, mode))
            if spot is None:
                break  # infra failure — air whatever already generated
            break_spots_total += 1
            spots.append(spot)
        if not spots:
            log.warning("schedule_break_skipped", program=program.id)
            return

        sting_in = break_sting_segment("break_in", air_cursor)
        if sting_in is not None:
            _place_clip(sting_in)
        for spot in spots:
            spot.air_time = air_cursor.isoformat()  # re-pin after the opener sting
            spot.meta["program"] = program.id
            spot.meta["program_name"] = program.name
            _write_sidecar(spot)
            record_airplay_features(spot)
            entry = _entry(spot)
            duration = _duration_of(entry)
            upcoming.append(entry)
            air_cursor += timedelta(seconds=duration)
            runway_sec += duration
            added += 1
            # A spot is content the listener hears — it counts toward the C3/D7.2
            # ident cadences like any content slot.
            content_since_ident += 1
            content_since_station_ident += 1
            log.info(
                "schedule_break_spot_added",
                seg_id=spot.id,
                format=spot.format,
                program=program.id,
                air_time=entry["air_time"],
                duration_sec=round(duration, 1),
                runway_sec=round(runway_sec),
            )

        # D8.2 — every Nth break also carries ONE real "Powered by" read, inside
        # the sting bracket (an acknowledgement rides the break, it never gets
        # its own interruption). Only sponsors inside their run window at the
        # slot's AIR time qualify; the table ships empty (pre-CM), so this whole
        # branch places nothing until donations are live. Any failure (DB down,
        # flagged blurb, TTS error) skips the read — never the break.
        breaks_total += 1
        n_breaks = settings.sponsor_read_every_n_breaks
        if n_breaks > 0 and breaks_total % n_breaks == 0:
            try:
                with store.connect() as conn:
                    active = store.active_sponsors(conn, air_cursor)
                if active:
                    chosen = pick_sponsor(active, sponsor_reads_total)
                    read = sponsor_read_segment(air_cursor, chosen)
                    if read is not None:
                        sponsor_reads_total += 1
                        _place_clip(read)
                        if read.meta.get("kind") == "read":
                            # A one-shot TTS render — sidecar so the C2.5 GC can
                            # age it out (a supplied clip is reused assets/ audio).
                            _write_sidecar(read)
            except Exception as exc:  # noqa: BLE001 — a read must never cost the break
                log.warning("schedule_sponsor_read_error", error=str(exc))

        sting_out = break_sting_segment("break_out", air_cursor)
        if sting_out is not None:
            _place_clip(sting_out)

    # Consecutive-failure stall threshold: the whole format set failing in a row means
    # the generator is down. Grid mode spans all formats; flat mode is the rotation.
    stall_cap = len(FORMATS) if settings.programming_enabled else len(rotation)
    log.info(
        "schedule_topup_start",
        now=now.isoformat(),
        upcoming=len(upcoming),
        runway_sec=round(runway_sec),
        depth_target_sec=round(depth_target_sec),
        programming=settings.programming_enabled,
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

        # D7.2 — the A1 sung station ident on its own (slower) cadence, mirroring
        # the C3 weave above. Additive: the disclosure ident keeps airing as-is.
        # Reset-first for the same reason; a missing/unreadable clip skips this
        # firing (placement returns None / stamp guards the probe), never blocks.
        if (
            settings.production_ident_every_n > 0
            and content_since_station_ident >= settings.production_ident_every_n
        ):
            content_since_station_ident = 0
            try:
                station_ident = station_ident_segment(air_cursor)
                if station_ident is not None:
                    _place_clip(station_ident)
            except Exception as exc:
                log.warning("schedule_station_ident_error", error=str(exc))
            continue

        # D6.2 — pick the next format from the programming GRID: the active program's
        # clock at the air-cursor (run-lengths, pinned top-of-hour slots, markers
        # skipped), routing that program's hosts into generation so the grid drives
        # WHO's on air. `programming_enabled=False` is the rollback to the flat
        # buffer_rotation (the pre-D6 behaviour), so buffer_rotation is never a second
        # source of truth silently fighting the grid — it's the default program's mix.
        program: Program | None = None
        new_pstate: dict | None = None
        speakers: list[str] | None = None
        slot_flow: ShowFlow | None = None
        if settings.programming_enabled:
            program = programming.program_for(air_cursor)
            # D7.2 — program boundary: when the show at the cursor CHANGES, open it
            # with its sonic identity (a handover program gets the B6 sting, then
            # the theme — placement.boundary_segments) before any content. First
            # run just records the program (a boundary is a CHANGE, not a start);
            # the id persists so a boundary falling between top-ups still fires.
            if program.id != last_program_id:
                if (
                    settings.production_theme_at_boundary
                    and last_program_id is not None
                ):
                    try:
                        for clip_seg in boundary_segments(program, air_cursor):
                            _place_clip(clip_seg)
                    except Exception as exc:
                        log.warning("schedule_boundary_error", error=str(exc))
                last_program_id = program.id
                # D8.1 — each show's ad load starts fresh: no instant break at
                # the top of a show because the previous one ran long.
                content_since_break = 0

            # D8.1 — the ad-break cadence: the GRID decides (program.break_every
            # content segments between breaks; 0 = this show takes none), the
            # scheduler weaves. Reset-first so a failed break skips this firing
            # rather than blocking content or spinning; the next cadence still
            # fires. Grid mode only — the flat rotation carries no ad load.
            if (
                settings.commercial_break_enabled
                and program.break_every > 0
                and content_since_break >= program.break_every
            ):
                content_since_break = 0
                try:
                    _place_break(program)
                except Exception as exc:
                    log.warning("schedule_break_error", error=str(exc))
                continue

            name, new_pstate = programming.next_format(
                program, air_cursor, clock_state.get(program.id, {}), prev_cursor
            )
            if name is not None:
                speakers = _program_speakers(program, name)
                # D12.0/D12.2 — where this slot sits in the show, the thread to carry
                # in, and whether to continue it. Grid mode only; the flat rotation
                # stays standalone (flow=None).
                slot_flow = _show_flow(
                    program,
                    air_cursor,
                    flow_last_program,
                    flow_handoff,
                    flow_thread_run,
                )
        else:
            name = rotation[rot_i % len(rotation)]

        seg = _generate_slot(name, air_cursor, speakers, slot_flow) if name else None
        if seg is None:
            # The slot failed (infra error) or the program yielded nothing airable —
            # advance past it (commit the clock/rotation step so we don't retry the
            # same atom forever) and try the next format. If the whole format set
            # fails in a row, the generator is down: stop this run and let playout
            # keep airing the existing buffer/fallback (never dead air); next run
            # retries.
            if program is not None and new_pstate is not None:
                clock_state[program.id] = new_pstate
                # Consume the crossing so a failed pin doesn't re-fire in a spin (the
                # cursor didn't advance, so mark this instant as processed).
                prev_cursor = air_cursor
                clock_state["_last_cursor"] = air_cursor.isoformat()
            else:
                rot_i += 1
            consecutive_skips += 1
            if consecutive_skips >= stall_cap:
                log.error(
                    "schedule_topup_stalled",
                    added=added,
                    runway_sec=round(runway_sec),
                )
                break
            continue
        consecutive_skips = 0

        # D7.3 — bake the slot's bed under the speech where the grid calls for it
        # (doubly opt-in via production_bedded_programs/_formats — e.g. the night
        # show's talk gets the soft B4 bed, news stays dry). The segment is
        # re-measured on the FINAL mixed audio inside apply_bed, and a mix failure
        # already degraded to the dry render there; this outer guard only keeps an
        # unexpected error from costing the slot.
        if program is not None:
            try:
                seg = apply_bed(seg, program)
            except Exception as exc:
                log.warning("schedule_bed_error", seg_id=seg.id, error=str(exc))

        # D7.2 — the C8 sting fires immediately BEFORE a news bulletin (the pinned
        # news@:00 moment). Placed only once the bulletin actually generated (a
        # lone sting before a skipped slot would be noise), then the bulletin is
        # re-pinned after it. Works in grid and flat mode alike; a missing clip
        # skips silently (media logs it).
        if name == "news" and settings.production_sting_before_news:
            try:
                sting = news_sting_segment(air_cursor)
                if sting is not None:
                    _place_clip(sting)
                    seg.air_time = air_cursor.isoformat()
            except Exception as exc:
                log.warning("schedule_news_sting_error", error=str(exc))

        # Commit the advanced clock/rotation state now that the slot has aired, and
        # stamp the program onto the segment (for the D6.3 console / D6.4 feed). Advance
        # the global pin cursor to this slot's time so the next slot's crossing is
        # measured from here (content only — idents don't consume a top-of-hour pin).
        if program is not None and new_pstate is not None:
            clock_state[program.id] = new_pstate
            prev_cursor = air_cursor
            clock_state["_last_cursor"] = air_cursor.isoformat()
            seg.meta["program"] = program.id
            seg.meta["program_name"] = program.name
        else:
            rot_i += 1

        # D12.0 — advance the talk-continuity substrate on a placed CONTENT slot:
        # remember this program as the last content program (so the next new program
        # OPENs), and refresh the talk hand-off. A talk atom that succeeded yields a
        # real hand-off; one that fell to an evergreen (or parsed empty) yields None
        # → the thread clears so the next talk opens fresh. A non-talk slot leaves
        # the hand-off intact, so the thread carries across it (real radio keeps a
        # thread over a song). Grid mode only; the flat rotation carries no thread.
        if program is not None:
            flow_last_program = program.id
            if name == "talk":
                # Audit fixes 1+3: open_thread is POSITIONAL (an open/continue slot
                # was told not to sign off — no more regex guessing), and a continuing
                # slot extends the thread's covered-beats memory from the prior
                # hand-off so the showrunner can steer off already-aired beats.
                continued = slot_flow is not None and slot_flow.continue_thread
                flow_handoff = flow_mod.handoff_from_segment(
                    seg,
                    program.id,
                    position=slot_flow.position if slot_flow is not None else None,
                    prev=slot_flow.handoff if slot_flow is not None else None,
                    continued=continued,
                )
                # D12.2 — advance the thread pacing counter. A slot that fell to an
                # evergreen (no hand-off) breaks the thread → 0; a slot that CONTINUED
                # the thread grows it; any other talk slot starts a fresh thread at 1.
                if flow_handoff is None:
                    flow_thread_run = 0
                elif continued:
                    flow_thread_run += 1
                else:
                    flow_thread_run = 1

        # Self-describing sidecar so prune() can read this render's air end once it
        # has aired out of the live schedule (C2.5). Written with the pinned slot
        # air_time already set on the segment by `_generate_slot`.
        _write_sidecar(seg)
        # D5.1 — record this placed segment's salient features in the airplay memory
        # (anti-repetition): one chokepoint sees every content slot, so producers don't
        # each need wiring. Best-effort + filters static idents/evergreen internally;
        # the memory persists past the C2.5 disk GC (the point — freshness.py).
        record_airplay_features(seg)
        # D13.1 — the hosts' journal: one cheap post-render extraction distills what
        # the hosts said about THEMSELVES (opinions/details/jokes/exchanges) into
        # durable memory. Best-effort + filters non-talk/evergreen internally; only
        # AIRED segments become memory (the direct CLI paths never reach here).
        capture_journal(seg)
        entry = _entry(seg)
        duration = _duration_of(entry)
        upcoming.append(entry)
        air_cursor += timedelta(seconds=duration)
        runway_sec += duration
        added += 1
        content_since_ident += 1
        content_since_station_ident += 1
        content_since_break += 1
        log.info(
            "schedule_slot_added",
            seg_id=seg.id,
            format=seg.format,
            program=program.id if program is not None else None,
            air_time=entry["air_time"],
            duration_sec=round(duration, 1),
            runway_sec=round(runway_sec),
            flow_position=slot_flow.position if slot_flow is not None else None,
            continue_thread=slot_flow.continue_thread if slot_flow else None,
            thread_run=flow_thread_run,
        )
        # Refresh the playout playlist so a first, cold `make schedule` can START
        # airing on the first ready segment (and survive an interrupt) rather than
        # wait for the whole multi-hour buffer + the end-of-run write. But do NOT
        # rewrite on EVERY segment: Liquidsoap watches this file and resets to the top
        # of the list on each reload, so churning it during a long cold fill pins
        # playout to the first entry. Write once when audio first lands, then only
        # every `schedule_playlist_write_every` segments — and drop already-aired
        # entries (real wall clock) so a reload lands on what's playing now.
        if added == 1 or added % settings.schedule_playlist_write_every == 0:
            _write_playlist(upcoming, now)

    # D12.0 — persist the talk-continuity substrate so the next top-up resumes the
    # thread and the OPEN detection (JSON-serialisable, like `_last_cursor`).
    clock_state["_flow"] = {
        "last_content_program": flow_last_program,
        "handoff": flow_handoff.to_dict() if flow_handoff is not None else None,
        "thread_run": flow_thread_run,
    }
    state["entries"] = upcoming
    state["rotation_index"] = rot_i % len(rotation)
    state["clock_state"] = clock_state
    state["content_since_ident"] = content_since_ident
    state["content_since_station_ident"] = content_since_station_ident
    state["content_since_break"] = content_since_break
    state["break_spots_total"] = break_spots_total
    state["breaks_total"] = breaks_total
    state["sponsor_reads_total"] = sponsor_reads_total
    state["last_program_id"] = last_program_id
    # C4 — heartbeat: record that a top-up ran to completion. `src/health.py`
    # check_last_run() reads this to detect a generator that has stopped running.
    state["last_topup_at"] = now.isoformat()
    _save_state(state)
    playlist_path = _write_playlist(upcoming, now)

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

    # D5.1 — bound the airplay memory the same way: drop rows older than its (much
    # wider) keep window. This is NOT the disk GC above — the freshness memory must
    # OUTLIVE the audio it describes; it just can't grow forever on a 24/7 station.
    sweep_airplay(now)

    # D6.4 — refresh the PUBLIC now-playing feed from the freshly-saved schedule, so
    # the web player tracks the air as it advances. Best-effort: a failure here must
    # never break a top-up (the air is fed; the feed is a read-side convenience).
    try:
        from . import nowplaying

        nowplaying.write_feed(now)
    except Exception as exc:  # noqa: BLE001 — the feed must not break playout
        log.error("nowplaying_write_error", error=str(exc))

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

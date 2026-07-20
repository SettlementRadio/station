"""D6.3 — the read-only operator STATUS CONSOLE (private; CLI/SSH only).

A human (or an uptime view) can see the station's state at a glance without touching
files: what's on air and next, how deep the rolling buffer is, whether the generator +
nightly tick are running, the living-world story log, and a cost rollup. It reads the
same state the running station writes — nothing more:

  * ON AIR / NEXT   — `schedule.json` (the scheduler's live schedule; D6.2 stamps each
                      entry with its program), framed by the programming grid.
  * BUFFER          — `health._runway_seconds` (REUSED, never recomputed, so console
                      and health can never disagree) + `health.check_buffer`.
  * LAST RUN        — the scheduler's `last_topup_at` heartbeat (health.check_last_run).
  * WORLD TICK      — the D3 tick heartbeat/counter in the `state` kv table.
  * STORY LOG       — active stories + their newest beats (D3 store reads).
  * COST            — the usage rollup (OVERVIEW §2), omitted gracefully until the jobs
                      persist one.

STRICTLY READ-ONLY: it opens no write, runs no generation, sends no alert/ping (unlike
`health.run_checks`, it calls the pure `check_*` reads, never the alerting path). The
write/management surface is Phase E.

PRIVATE / OPERATOR-ONLY (audit fix): this exposes internal state (story log, buffer
internals, health, cost) and must NEVER be internet-reachable — it is a CLI over SSH
(and, in Phase E, the private VPS-only admin panel). It is the OPPOSITE surface from the
public now-playing feed (D6.4), which carries only a public-safe subset. Keep them
separate: internal state → this console (private); public subset → the feed (public).

    .venv/bin/python -m src.console      # or: make console
"""

from __future__ import annotations

import sys
from datetime import datetime

from . import health
from .config import settings
from .logging_setup import get_logger
from .scheduler import _duration_of, _load_state, onair_hosts, split_schedule
from .world import events, programming, store

log = get_logger(__name__)


# --- Small formatting helpers -----------------------------------------------


def _dur(sec: float) -> str:
    """A segment length in a compact `m:ss` (or `≈` when only a target is known)."""
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _age(sec: float) -> str:
    """An elapsed span in human units — `42m`, `6h03m`, `2d05h` — for heartbeats."""
    sec = int(round(sec))
    if sec < 3600:
        return f"{sec // 60}m"
    if sec < 86400:
        return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"
    return f"{sec // 86400}d{(sec % 86400) // 3600:02d}h"


def _hosts_for(entry: dict) -> str:
    """The hosts actually on air for an entry (the SAME slice the D6.4 feed shows)."""
    if not entry.get("program"):  # idents etc. carry no program -> no hosts
        return "—"
    try:
        prog = programming.program_for(datetime.fromisoformat(entry["air_time"]))
    except Exception:  # noqa: BLE001 — the console never fails on a display lookup
        return "—"
    return ", ".join(onair_hosts(prog, entry.get("format"))) or "—"


def _entry_line(entry: dict, *, marker: str = "  ") -> str:
    """One schedule entry as a console row: time · program · format · hosts · dur."""
    at = entry.get("air_time") or "—"
    when = at[11:16] if len(at) >= 16 else at  # HH:MM off the ISO stamp
    program = entry.get("program_name") or entry.get("program") or "—"
    fmt = entry.get("format") or "—"
    measured = entry.get("actual_duration_sec")
    dur = _dur(_duration_of(entry))
    dur = dur if measured else f"≈{dur}"  # ≈ = target only (probe missing)
    return f"{marker}{when}  {program:<16} {fmt:<8} [{_hosts_for(entry)}]  {dur}"


# --- The panels (each returns a list of lines) ------------------------------


def now_next_lines(now: datetime, state: dict) -> list[str]:
    """ON AIR now + the next N upcoming entries, from the live schedule."""
    current, upcoming = split_schedule(now, state)

    lines: list[str] = []
    if current is not None:
        into = (now - datetime.fromisoformat(current["air_time"])).total_seconds()
        lines.append(_entry_line(current, marker="▶ "))
        lines.append(f"    ({_dur(into)} into the segment)")
    else:
        lines.append("  (nothing on air — buffer empty or between segments)")

    limit = settings.programming_console_upcoming
    if upcoming:
        lines.append(f"  next {min(limit, len(upcoming))} of {len(upcoming)} queued:")
        lines += [_entry_line(e) for e in upcoming[:limit]]
    else:
        lines.append("  (nothing queued ahead)")
    return lines


def buffer_lines(now: datetime) -> list[str]:
    """Buffer runway — REUSING the health runway calc so the two never disagree."""
    runway, count = health._runway_seconds(now)
    target_h = settings.buffer_depth_hours
    line = f"  runway {runway / 3600:.2f}h in {count} segment(s) (target {target_h:g}h)"
    issue = health.check_buffer(now)  # pure read; no alert/ping side effects
    return [line, f"  ⚠ {issue}" if issue else "  ✓ above the safe floor"]


def last_run_lines(now: datetime, state: dict) -> list[str]:
    """Scheduler heartbeat — when the last top-up completed (health.check_last_run)."""
    last = state.get("last_topup_at")
    if last:
        try:
            age = (now - datetime.fromisoformat(last)).total_seconds()
            when = f"{last[:19]} ({_age(age)} ago)"
        except ValueError:
            when = f"{last!r} (unparseable)"
    else:
        when = "never (no top-up recorded yet)"
    issue = health.check_last_run(now)  # pure read
    return [f"  last top-up: {when}", f"  ⚠ {issue}" if issue else "  ✓ generator live"]


def world_lines(conn, now: datetime) -> list[str]:
    """World-tick heartbeat (D3): last run, tick count, and active-story count."""
    from .world.world_tick import _TICK_COUNT_KEY, _TICK_LAST_AT_KEY

    count = store.get_state(conn, _TICK_COUNT_KEY)
    last = store.get_state(conn, _TICK_LAST_AT_KEY)
    active = len(store.active_stories(conn))
    when = "never" if not last else f"{last[:19]}"
    if last:
        try:
            when += (
                f" ({_age((now - datetime.fromisoformat(last)).total_seconds())} ago)"
            )
        except ValueError:
            pass
    return [
        f"  last tick: {when}  ·  ticks run: {count or 0}  ·  active stories: {active}"
    ]


def story_log_lines(conn, now: datetime) -> list[str]:
    """Active stories + their newest beat(s) — the living world at a glance (D3)."""
    stories = store.active_stories(conn, limit=settings.console_story_limit)
    if not stories:
        return ["  (no active stories — run the world tick to grow the world)"]
    lines: list[str] = []
    for s in stories:
        tags = f" #{' #'.join(s.tags)}" if s.tags else ""
        lines.append(f"  • [{s.arc_stage}] {s.title}{tags}")
        beats = store.story_beats(conn, s.id)
        for beat in beats[-settings.console_beats_per_story :]:
            when = beat.in_world_datetime.strftime("%Y-%m-%d %H:%M")
            # R4.0: the operator sees the whole arc, plan included — unlike the news
            # desk, which only ever sees the beats that have landed.
            plan = "" if events.has_landed(beat, now) else "  (planned)"
            lines.append(f"      ↳ {when}: {beat.title}{plan}")
    return lines


def journal_lines(conn) -> list[str]:
    """The hosts' journal at a glance (D13.1): entries accrued per host."""
    per_host = store.journal_counts(conn)
    if not per_host:
        return ["  (no journal entries yet — talk segments accrue them as they air)"]
    parts = "  ·  ".join(f"{host}: {n}" for host, n in per_host.items())
    return [f"  {parts}"]


def cost_lines(conn) -> list[str]:
    """Cost rollup (OVERVIEW §2) — omitted gracefully until the jobs persist one."""
    rollup = store.get_state(conn, "usage_rollup")
    if not rollup:
        return [
            "  (no usage rollup recorded yet — jobs log usage to the structured logs; "
            "a persisted rollup surfaces here once emitted)"
        ]
    return [f"  {rollup}"]


# --- Assemble + render -------------------------------------------------------


def render(now: datetime | None = None) -> str:
    """Build the full console report as one string (read-only; mutates nothing)."""
    now = now or datetime.now()
    state = _load_state()

    out: list[str] = [
        "===== SETTLEMENT RADIO — STATUS CONSOLE (D6.3, read-only) =====",
        f"  as of {now:%Y-%m-%d %H:%M:%S}"
        f"  ·  programming {'ON' if settings.programming_enabled else 'OFF (flat)'}",
        "",
        "── ON AIR / NEXT ──",
        *now_next_lines(now, state),
        "",
        "── BUFFER ──",
        *buffer_lines(now),
        "",
        "── LAST RUN ──",
        *last_run_lines(now, state),
    ]

    # The D3 world panels need the DB; degrade gracefully (one note) if it's down —
    # the schedule/buffer/heartbeat panels above stand alone without it.
    out += ["", "── WORLD TICK ──"]
    try:
        with store.connect() as conn:
            out += world_lines(conn, now)
            out += ["", "── STORY LOG ──", *story_log_lines(conn, now)]
            out += ["", "── HOST JOURNAL ──", *journal_lines(conn)]
            out += ["", "── COST ──", *cost_lines(conn)]
    except Exception as exc:  # noqa: BLE001 — the console must never crash on a read
        out += [f"  (world/story log unavailable: {exc})"]
        log.warning("console_world_panel_unavailable", error=str(exc))

    out += ["", "=" * 62]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    """CLI entry point: print the read-only status console. Exit 0 (it only reads)."""
    print(render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

"""D6.1 — the programming module: which show is on air at a given datetime.

Reads the weekly programming grid (`docs/programming/grid.yaml` — the human-edited
source of truth, D6.0) and answers `program_for(now) -> Program`: the named show, its
hosts, its framing hint, and its format CLOCK for the in-world wall-clock slot. This is
the seam that replaces the scheduler's flat `buffer_rotation` (D6.2) and generalises
`world/framing.py` beyond two hardcoded hosts (via `framing.program_frame`).

The in-world wall clock equals the real wall clock (the world clock shifts the *year*
only — `clock.render_wall_clock`), so grid slots are plain weekday + `HH:MM-HH:MM`
ranges, matched against `now`. Time ranges may wrap past midnight (`22:00-05:00`).

Storage (D6.0 decision): the YAML is the version-controlled source of truth. D6.1 reads
it directly through this module (a small mtime-cached loader) — the config-file read
path — so an operator edit is picked up on the next load without a restart. The DB-table
projection (`programs`/`program_grid` + `make seed-grid`) that the Phase E web grid
editor will write to is additive behind this same `program_for` seam and lands with the
scheduler wiring; callers never change.

The grid must tile the week with no gaps; a reserved **default** program (`legacy`
framing, the weighted-rotation fallback) backstops any hole — and is synthesised from
`settings` when the grid file is absent entirely — so `program_for` never returns None
and the scheduler never stalls.

Pure, dependency-light, unit-testable the way `framing.py`/`clock.py` are: no DB, no
model calls, only a cached read of the YAML config.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from ..config import settings
from ..logging_setup import get_logger

log = get_logger(__name__)

# Sound-design markers (D7 wires them to real audio; inert placeholders today —
# the scheduler skips a marker step). A clock token that is neither a known format
# nor one of these is still treated as a format name and left for the scheduler to
# validate/skip at air time (D6.2), so this module needs no `formats` import.
_MARKERS = frozenset({"sting", "bed", "ident"})

_WEEKDAYS = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}
_WEEKDAY_ALIASES: dict[str, frozenset[int]] = {
    "daily": frozenset(range(7)),
    "everyday": frozenset(range(7)),
    "weekdays": frozenset(range(5)),  # mon-fri
    "weekends": frozenset({5, 6}),  # sat-sun
}


# --- The model (Program · Clock step · grid slot) ---------------------------


@dataclass(frozen=True)
class ClockStep:
    """One step of a program's hour-clock (D6.0): a format run, pin, or marker.

    `format` is a `formats.FORMATS` key (talk/news/music) or a marker name; `count`
    is the run-length (`music x3` → 3); `pin_minute` pins the step to `:MM` of the
    hour (`news@:00` → 0) so the scheduler airs it when the air-cursor crosses that
    minute (D6.2); `is_marker` flags a D7 sound-design placeholder the scheduler
    skips today.
    """

    format: str
    count: int = 1
    pin_minute: int | None = None
    is_marker: bool = False


@dataclass(frozen=True)
class Program:
    """A named show placed on the grid (D6.0).

    `hosts` are cast ids in lead-first order (`hosts[0]` anchors; at a `handover`,
    `hosts[0]` is the incoming lead and `hosts[1]` the outgoing companion). `framing`
    is one of `solo` | `handover` | `ensemble` | `legacy` (the last reserved for the
    default program — the hour-derived frame). `clock` is the explicit format
    sequence; `rotation` is the weighted-rotation fallback used when `clock` is empty.
    """

    id: str
    name: str
    hosts: tuple[str, ...]
    framing: str
    daypart: str  # optional display label ("" if none) — does not set part_of_day
    clock: tuple[ClockStep, ...]
    rotation: tuple[str, ...]


@dataclass(frozen=True)
class _Slot:
    """One grid tiling entry: a weekday set × time range → a program id."""

    weekdays: frozenset[int]
    start_min: int  # minutes past midnight, inclusive
    end_min: int  # minutes past midnight, exclusive (wraps when <= start_min)
    program_id: str
    order: int  # file order, for a stable tie-break among equally-specific matches


# --- Parsing ----------------------------------------------------------------


def _parse_clock_token(token: str) -> ClockStep:
    """Parse one clock string — `talk`, `music x3`, `news@:00`, `sting` — to a step."""
    s = token.strip()
    pin_minute: int | None = None
    if "@" in s:
        fmt_part, _, at = s.partition("@")
        at = at.strip().lstrip(":").strip()
        try:
            pin_minute = int(at) if at else 0
        except ValueError:
            log.warning("programming_bad_pin", token=token)
            pin_minute = 0
        s = fmt_part.strip()

    count = 1
    m = re.match(r"^(?P<fmt>[A-Za-z_]+)\s*[x*]\s*(?P<n>\d+)$", s)
    if m:
        s = m.group("fmt")
        count = max(1, int(m.group("n")))

    fmt = s.lower()
    return ClockStep(
        format=fmt,
        count=count,
        pin_minute=pin_minute,
        is_marker=fmt in _MARKERS,
    )


def _parse_program(pid: str, data: dict) -> Program:
    """Build a `Program` from its `grid.yaml` mapping."""
    hosts = tuple(str(h).strip() for h in (data.get("hosts") or []))
    framing = str(data.get("framing") or "solo").strip().lower()
    daypart = str(data.get("daypart") or "").strip()
    clock = tuple(_parse_clock_token(str(t)) for t in (data.get("clock") or []))
    rotation = tuple(str(r).strip() for r in (data.get("rotation") or []))
    name = str(data.get("name") or pid).strip()
    return Program(
        id=pid,
        name=name,
        hosts=hosts,
        framing=framing,
        daypart=daypart,
        clock=clock,
        rotation=rotation,
    )


def _parse_weekday_key(key: str) -> frozenset[int]:
    """Parse a grid weekday key — `daily`, `weekdays`, `mon-fri`, `sat`, `mon,wed`."""
    k = key.strip().lower()
    if k in _WEEKDAY_ALIASES:
        return _WEEKDAY_ALIASES[k]
    days: set[int] = set()
    for part in k.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            start = _WEEKDAYS.get(a.strip())
            end = _WEEKDAYS.get(b.strip())
            if start is None or end is None:
                log.warning("programming_bad_weekday", key=key, part=part)
                continue
            # Inclusive range, wrapping through the week (fri-mon -> fri,sat,sun,mon).
            i = start
            while True:
                days.add(i)
                if i == end:
                    break
                i = (i + 1) % 7
        else:
            d = _WEEKDAYS.get(part)
            if d is None:
                log.warning("programming_bad_weekday", key=key, part=part)
                continue
            days.add(d)
    return frozenset(days)


def _parse_hm(value: str) -> int:
    """`"HH:MM"` / `"HH"` → minutes past midnight."""
    h, _, m = value.strip().partition(":")
    return int(h) * 60 + (int(m) if m.strip() else 0)


def _parse_time_range(rng: str) -> tuple[int, int]:
    """`"22:00-05:00"` → (1320, 300); an end <= start means a midnight wrap."""
    start, _, end = rng.strip().partition("-")
    return _parse_hm(start), _parse_hm(end)


# --- The mtime-cached grid load ---------------------------------------------


@dataclass
class _Grid:
    """The parsed grid: programs by id, and the ordered tiling slots."""

    programs: dict[str, Program] = field(default_factory=dict)
    slots: list[_Slot] = field(default_factory=list)


_cache: dict[str, object] = {"key": None, "grid": None}


def _load_grid() -> _Grid:
    """Load + parse `grid.yaml`, cached by (path, mtime); empty grid if absent."""
    path: Path = settings.programming_grid_path
    if not path.exists():
        return _Grid()
    key = (str(path), path.stat().st_mtime)
    if _cache["key"] == key and isinstance(_cache["grid"], _Grid):
        return _cache["grid"]

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    programs = {
        pid: _parse_program(pid, dict(data or {}))
        for pid, data in (raw.get("programs") or {}).items()
    }
    slots: list[_Slot] = []
    order = 0
    for wk_key, ranges in (raw.get("grid") or {}).items():
        weekdays = _parse_weekday_key(str(wk_key))
        for rng, program_id in (ranges or {}).items():
            start_min, end_min = _parse_time_range(str(rng))
            slots.append(_Slot(weekdays, start_min, end_min, str(program_id), order))
            order += 1

    grid = _Grid(programs=programs, slots=slots)
    _cache["key"] = key
    _cache["grid"] = grid
    log.info("programming_grid_loaded", programs=len(programs), slots=len(slots))
    return grid


def reload() -> None:
    """Drop the cached grid so the next `program_for` re-reads the file (tests/ops)."""
    _cache["key"] = None
    _cache["grid"] = None


# --- Slot matching + the public lookup --------------------------------------


def _slot_matches(slot: _Slot, now: datetime) -> bool:
    """Does `now` fall in this slot's weekday × time range (midnight-wrap aware)?"""
    m = now.hour * 60 + now.minute
    weekday = now.weekday()
    s, e = slot.start_min, slot.end_min
    if s == e:  # a full-day slot (start == end) — matches the whole weekday
        return weekday in slot.weekdays
    if s < e:  # ordinary same-day range
        return s <= m < e and weekday in slot.weekdays
    # Wrap past midnight: the [start, midnight) part is today; the [midnight, end)
    # part belongs to the slot that started the PREVIOUS day.
    if m >= s:
        return weekday in slot.weekdays
    if m < e:
        return (weekday - 1) % 7 in slot.weekdays
    return False


def program_for(now: datetime) -> Program:
    """The `Program` active at `now` (in-world wall clock); never None.

    Returns the most specific matching grid slot's program (a narrower weekday set
    wins over `daily`, then file order breaks ties). Falls back to the reserved
    default program — from the grid if defined, else synthesised from `settings` —
    when no slot matches or the grid file is absent, so callers never stall.
    """
    grid = _load_grid()
    matches = [s for s in grid.slots if _slot_matches(s, now)]
    if matches:
        matches.sort(key=lambda s: (len(s.weekdays), s.order))
        best = matches[0]
        prog = grid.programs.get(best.program_id)
        if prog is not None:
            return prog
        log.warning(
            "programming_unknown_program",
            program_id=best.program_id,
            at=now.isoformat(),
        )
    else:
        log.warning("programming_no_slot", at=now.isoformat())
    return _default_program(grid)


def _default_program(grid: _Grid) -> Program:
    """The reserved fallback program — from the grid, else synthesised from settings.

    The synthesised form (grid file missing/empty, or no `default` defined) carries
    `legacy` framing + the `buffer_rotation` fallback clock over `convo_speaker_ids`,
    so an absent grid reproduces today's flat, hour-framed behaviour exactly.
    """
    prog = grid.programs.get(settings.programming_default_program)
    if prog is not None:
        return prog
    return Program(
        id=settings.programming_default_program,
        name="Settlement Radio",
        hosts=tuple(settings.convo_speaker_ids),
        framing="legacy",
        daypart="",
        clock=(),
        rotation=tuple(settings.buffer_rotation),
    )


__all__ = ["ClockStep", "Program", "program_for", "reload"]

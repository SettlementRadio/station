"""Programming-backbone demo (PHASE_D_PROGRAMMING_TASKS.md D6.5).

Makes the D6 payoff visible WITHOUT spending a token: the station is now a *programmed*
grid, not a flat rotation. Four parts, all pure reads (no Claude/TTS; the grid is the
YAML config, framing/clock are pure functions):

  1. THE WEEK BY DAYPART — `program_for(now)` across a day, so you SEE the named
     programs + hosts + framing change hour to hour (the shipped grid).
  2. THE CLOCK, ON AIR — walk the shipped grid's clock across the dawn boundary, so you
     SEE the format sequence, the pinned top-of-hour news landing, and the program's
     hosts routed into each slot (First Light → Daywatch).
  3. RUN-LENGTHS (illustrative) — two hand-built clocks show the D6.0 distinction a
     weighted ratio can't: a dedicated MUSIC BLOCK (a 3-song sweep) vs music
     INTERSPERSED with talk. (Music airs from D7; the clock machinery is here now.)
  4. CONSOLE + NOW-PLAYING — build a schedule from part 2 and render the D6.3 operator
     console panel + the D6.4 public now-playing feed from it, so both reflect live
     state (read-only).

Run:  .venv/bin/python -m src.programming_demo    (or: make programming-demo)

Token-free and DB-optional: host display names in the feed resolve from the cast if a
DB is reachable, else fall back to readable ids — the demo runs either way.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from . import console, nowplaying
from .scheduler import _program_speakers
from .world import framing, programming
from .world.programming import ClockStep, Program

# A Monday, so weekday routing is unambiguous; the shipped grid is `daily`, so the
# daypart map repeats every day.
_MON = datetime(2026, 6, 22)
_SLOT = timedelta(minutes=6)  # a representative segment length for the clock walks


def _hosts(program: Program, fmt: str) -> str:
    """The cast ids actually on air for `fmt` under `program` (the scheduler slice)."""
    return ", ".join(_program_speakers(program, fmt) or program.hosts)


def part1_daypart_map() -> None:
    print("\n1) THE WEEK BY DAYPART  —  program_for(now) over a day (shipped grid)\n")
    print("   hour   program        framing    part-of-day   hosts")
    last = None
    for h in range(24):
        now = _MON.replace(hour=h)
        prog = programming.program_for(now)
        frame = framing.program_frame(now, prog)
        mark = "" if prog.id == last else f"   ← {prog.name}"
        last = prog.id
        print(
            f"   {h:02d}:00  {prog.id:<13} {prog.framing:<9}  "
            f"{frame.part_of_day:<12}  {frame.lead}"
            f"{' + ' + frame.companion if frame.companion else ''}{mark}"
        )


def _walk(program_of, cursor: datetime, n: int) -> list[dict]:
    """Walk `n` slots from `cursor`, one call to next_format per slot; return entries.

    `program_of(cursor)` yields the active program (so a walk can span a boundary).
    Mirrors the scheduler: per-program clock cursors + one global pin cursor.
    """
    seq: dict[str, dict] = {}
    prev: datetime | None = None
    entries: list[dict] = []
    for _ in range(n):
        prog = program_of(cursor)
        name, pstate = programming.next_format(prog, cursor, seq.get(prog.id, {}), prev)
        seq[prog.id] = pstate
        prev = cursor
        entries.append(
            {
                "id": f"{name}-{cursor:%H%M}",
                "format": name,
                "program": prog.id,
                "program_name": prog.name,
                "audio_path": f"/segments/{name}-{cursor:%H%M}.mp3",
                "air_time": cursor.isoformat(),
                "actual_duration_sec": _SLOT.total_seconds(),
                "length_target_sec": int(_SLOT.total_seconds()),
                "_program": prog,  # demo-only; stripped before it becomes state
            }
        )
        cursor += _SLOT
    return entries


def part2_clock_on_air() -> list[dict]:
    print("\n\n2) THE CLOCK, ON AIR  —  the shipped grid across the dawn boundary\n")
    entries = _walk(programming.program_for, _MON.replace(hour=5, minute=48), 22)
    print("   time   program      fmt     hosts        note")
    last = None
    for e in entries:
        prog = e["_program"]
        when = e["air_time"][11:16]
        note = "← NEWS @ top of hour" if e["format"] == "news" else ""
        boundary = "" if prog.id == last else f"  ({prog.name} begins)"
        last = prog.id
        print(
            f"   {when}  {prog.id:<12} {e['format']:<6}  "
            f"{_hosts(prog, e['format']):<11}  {note}{boundary}"
        )
    return entries


def _clock(*tokens: str) -> tuple[ClockStep, ...]:
    return tuple(programming._parse_clock_token(t) for t in tokens)


def part3_run_lengths() -> None:
    print("\n\n3) RUN-LENGTHS (illustrative — music airs from D7; the clock is here)\n")
    block = Program(
        id="music_block",
        name="Music Block",
        hosts=("vell",),
        framing="solo",
        daypart="",
        clock=_clock("talk", "music x3", "sting", "news@:00"),
        rotation=(),
    )
    interspersed = Program(
        id="mixed",
        name="Mixed",
        hosts=("wren",),
        framing="solo",
        daypart="",
        clock=_clock("talk", "music", "talk", "music"),
        rotation=(),
    )
    for prog in (block, interspersed):
        cursor = _MON.replace(
            hour=10, minute=1
        )  # just past the hour (no immediate pin)
        seq, prev, out = {}, None, []
        for _ in range(8):
            name, seq = programming.next_format(prog, cursor, seq, prev)
            prev = cursor
            cursor += _SLOT
            out.append(name)
        print(f"   {prog.name:<12} clock → {'  '.join(out)}")
    print(
        "   (Music Block airs a 3-song sweep then a break; Mixed alternates "
        "talk/music — one\n    clock expresses both, which a weighted ratio cannot.)"
    )


def part4_console_and_feed(entries: list[dict]) -> None:
    # Strip the demo-only program object -> a real schedule.json-shaped state dict.
    state = {
        "entries": [{k: v for k, v in e.items() if k != "_program"} for e in entries],
        "last_topup_at": entries[0]["air_time"],
    }
    now = datetime.fromisoformat(entries[len(entries) // 2]["air_time"]) + timedelta(
        minutes=2
    )

    print("\n\n4a) OPERATOR CONSOLE (D6.3, read-only) — on-air / next from schedule\n")
    for line in console.now_next_lines(now, state):
        print("   " + line)

    print(
        "\n4b) PUBLIC NOW-PLAYING FEED (D6.4) — the public-safe subset for the player\n"
    )
    feed = nowplaying.build_feed(now, state)
    for line in json.dumps(feed, indent=2, ensure_ascii=False).splitlines():
        print("   " + line)


def main(argv: list[str]) -> int:
    print("=" * 70)
    print("  SETTLEMENT RADIO — programming backbone demo (D6; token-free)")
    print("=" * 70)
    part1_daypart_map()
    entries = part2_clock_on_air()
    part3_run_lengths()
    part4_console_and_feed(entries)
    print("\n" + "=" * 70)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))

"""R3.0 — the jingle placement audit: proof, not assumption.

Two passes over the SAME production code the scheduler calls (`placement.py` /
`media.py`), never a reimplementation of their resolution logic:

1. **The static mapping** (`_static_theme_mapping`) — every grid program's boundary
   theme, resolved by calling `placement.program_theme_segment` directly, so the
   report shows exactly what the CODE maps (override / bespoke-by-convention /
   format-fallback / missing), not what a doc claims. Covers every program in
   `grid.yaml`, whether or not the simulated window below happens to air it (the
   five rotating verticals + the weekly belt mean a short window won't visit them
   all).
2. **The dynamic run** — a simulated window driven through the REAL scheduler
   (`src.acceptance`'s mocked-LLM/TTS harness, the same isolation the D11.3 gate
   uses: one rolled-back Postgres transaction, temp `segments/`), asserting the
   properties that only a live schedule proves: every program boundary that
   actually fired got its theme, every `news@` pin got the C8 sting immediately
   before it, every handover boundary got the B6 sting before its theme, every ad
   break got the D18 in/out bracket, and no theme repeats back-to-back.

Run it:  `make jingle-audit`  ·  `python -m src.production.audit --hours 48`
It exits non-zero if any property fails, and always prints the mapping table so
the operator can eyeball reuse choices and spot programs still falling back
(R3.1's todo list).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from .. import acceptance
from ..logging_setup import get_logger
from ..world import programming
from . import media, placement

log = get_logger(__name__)

_CONTENT_FORMATS = frozenset({"talk", "news", "music", "commercial", "promo"})
_BREAK_FORMATS = frozenset({"commercial", "promo"})


# --- The report ---------------------------------------------------------------
@dataclass
class AuditReport:
    """The five placement verdicts + the per-program mapping table they draw on."""

    window_hours: float
    results: list[acceptance.PropertyResult] = field(default_factory=list)
    mapping: list[dict] = field(default_factory=list)
    telemetry: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def summary(self) -> str:
        lines = [f"===== JINGLE PLACEMENT AUDIT — {self.window_hours:g}h window ====="]
        for r in self.results:
            mark = "✅ PASS" if r.ok else "❌ FAIL"
            lines.append(f"  {mark}  {r.name}")
            lines.append(f"          {r.detail}")
        t = self.telemetry
        lines.append(
            "  telemetry: " + ", ".join(f"{k}={v}" for k, v in sorted(t.items()))
        )
        lines.append(
            "  RESULT: " + ("ALL PROPERTIES PASSED ✅" if self.ok else "FAILURES ❌")
        )
        lines.append("")
        lines.append("  --- mapping table: program -> clip actually resolved ---")
        for row in self.mapping:
            clip = row["clip"] or "MISSING"
            extra = (
                f"  handover={row['handover_clip']}" if "handover_clip" in row else ""
            )
            lines.append(f"  {row['program']:<20} [{row['kind']:<8}] {clip}{extra}")
        return "\n".join(lines)


# --- Pass 1: the static mapping (every program, straight from placement.py) ---
def _static_theme_mapping(now: datetime | None = None) -> list[dict]:
    """Every grid program's boundary resolution, via the real `placement` code path.

    `kind` is "override" (an explicit `media.PROGRAM_THEMES` reuse entry, e.g.
    `the_circuit` -> c12 games), "bespoke" (the convention path resolved a file
    named for the program itself), "fallback" (neither exists yet — the program
    opens on its FORMAT's theme, per `_first_content_format`), or "missing"
    (nothing resolved at all — genuinely cold, should not happen while the C7/C9
    format themes exist).
    """
    now = now or datetime.now()
    rows: list[dict] = []
    for pid, program in sorted(programming.all_programs().items()):
        seg = placement.program_theme_segment(program, now)
        if seg is None or not seg.audio_path:
            kind, clip = "missing", None
        else:
            clip = Path(seg.audio_path).name
            if pid in media.PROGRAM_THEMES:
                kind = "override"
            elif clip == f"{pid}.mp3":
                kind = "bespoke"
            else:
                kind = "fallback"
        row = {
            "program": pid,
            "name": program.name,
            "framing": program.framing,
            "kind": kind,
            "clip": clip,
        }
        if program.framing == "handover":
            hseg = placement.handover_sting_segment(program, now)
            row["handover_clip"] = (
                Path(hseg.audio_path).name if hseg and hseg.audio_path else "MISSING"
            )
        rows.append(row)
    return rows


# --- Pass 2: the dynamic run (the real scheduler, over a simulated window) ----
def run_audit(
    *,
    window_hours: float = 48.0,
    step_minutes: int = 60,
    tick_every_hours: float = 24.0,
    warmup_ticks: int = 2,
    buffer_depth_hours: float = 1.0,
    start: datetime | None = None,
    dump_path: str | None = None,
) -> AuditReport:
    """Walk a simulated window through the real scheduler and audit every clip join.

    Reuses the D11.3 acceptance harness verbatim (`acceptance._sim_environment`):
    the two provider seams mocked, everything else — the grid, the clock cursor,
    D7.2 boundary/pin/handover placement, D8.1 breaks — real, isolated inside one
    rolled-back Postgres transaction so it never touches the operator's world.
    """
    start = start or acceptance._DEFAULT_START
    step_minutes = min(step_minutes, int(buffer_depth_hours * 60 * 0.8) or 1)
    tmp = Path(tempfile.mkdtemp(prefix="sr-jingle-audit-"))
    log.info("jingle_audit_start", window_hours=window_hours, step_minutes=step_minutes)

    with acceptance._sim_environment(tmp, buffer_depth_hours=buffer_depth_hours):
        from .. import scheduler  # lazy: seams patched before any generation
        from ..world import world_tick

        for _ in range(warmup_ticks):
            world_tick.run_tick(now=start)

        entries: dict[str, dict] = {}
        next_tick = start + timedelta(hours=tick_every_hours)
        now = start
        end = start + timedelta(hours=window_hours)
        while now <= end:
            if now >= next_tick:
                world_tick.run_tick(now=now)
                next_tick += timedelta(hours=tick_every_hours)
            for e in scheduler.top_up(now=now):
                key = e.get("id") or f"{e.get('audio_path')}@{e.get('air_time')}"
                entries[key] = e
            now += timedelta(minutes=step_minutes)

    timeline = sorted(entries.values(), key=lambda e: e.get("air_time") or "")
    if dump_path:
        Path(dump_path).write_text(json.dumps(timeline, indent=2))

    mapping = _static_theme_mapping()
    clip_by_program = {row["program"]: row["clip"] for row in mapping}
    report = AuditReport(window_hours=window_hours, mapping=mapping)
    report.results = [
        _check_boundary_themes(timeline, clip_by_program),
        _check_news_pins(timeline),
        _check_handover_stings(timeline),
        _check_break_brackets(timeline),
        _check_no_theme_repeat(timeline),
    ]
    report.telemetry = {
        "total_slots": len(timeline),
        "content_slots": sum(
            1 for e in timeline if e.get("format") in _CONTENT_FORMATS
        ),
        "theme_fires": sum(1 for e in timeline if e.get("format") == "theme"),
        "sting_fires": sum(1 for e in timeline if e.get("format") == "sting"),
    }
    log.info("jingle_audit_done", ok=report.ok, **report.telemetry)
    return report


def _kind_of(entry: dict | None) -> tuple[str, str | None]:
    """(clip-kind, key) from a clip entry's id: `theme-<program_id>-<ts>` or
    `sting-<moment>-<ts>` (`moment` is news/handover/sweeper/break_in/break_out).
    Non-clip entries (talk/news/music/commercial/promo content) return `("", None)`.
    """
    if entry is None:
        return "", None
    fmt = entry.get("format")
    if fmt not in ("theme", "sting"):
        return "", None
    parts = (entry.get("id") or "").split("-")
    return (fmt, parts[1]) if len(parts) >= 2 else (fmt, None)


# --- The five dynamic properties ----------------------------------------------
def _check_boundary_themes(
    timeline: list[dict], clip_by_program: dict[str, str | None]
) -> acceptance.PropertyResult:
    """Every program CHANGE in the aired content stream got a theme first.

    The very first program of the run is exempt — D7.2 fires boundary clips only
    on a CHANGE, not a cold start (there's no previous show to hand off from), so
    that opener is expected to carry no theme. A boundary between two programs
    that both resolve (per the static mapping) to the SAME fallback clip is also
    exempt — R3.0's repeat-avoidance fix (`avoid_repeat`) deliberately skips that
    theme rather than play it twice in a row; that's a hole in the batch-3
    coverage (R3.1), not a placement bug.
    """
    content = [
        e for e in timeline if e.get("format") in _CONTENT_FORMATS and e.get("program")
    ]
    misses: list[str] = []
    checked = 0
    prev_program: str | None = None
    prev_air_time = ""
    for e in content:
        pid = e["program"]
        if pid != prev_program:
            if prev_program is not None:
                checked += 1
                window_start, window_end = prev_air_time, e["air_time"]
                has_theme = any(
                    _kind_of(t) == ("theme", pid)
                    and window_start <= (t.get("air_time") or "") <= window_end
                    for t in timeline
                )
                same_fallback = clip_by_program.get(
                    pid
                ) is not None and clip_by_program.get(pid) == clip_by_program.get(
                    prev_program
                )
                if not has_theme and not same_fallback:
                    misses.append(f"{prev_program} -> {pid} at {e['air_time']}")
            prev_program = pid
        prev_air_time = e["air_time"]
    ok = not misses
    detail = (
        f"{checked} program boundaries checked, every one themed"
        if ok
        else f"{len(misses)}/{checked} boundaries fired with no theme: {misses[:5]}"
    )
    return acceptance.PropertyResult("boundary_themes", ok, detail)


def _check_news_pins(timeline: list[dict]) -> acceptance.PropertyResult:
    """Every aired news bulletin has the C8 sting as the entry immediately before it."""
    misses: list[str] = []
    checked = 0
    for i, e in enumerate(timeline):
        if e.get("format") != "news":
            continue
        checked += 1
        prev = timeline[i - 1] if i > 0 else None
        if _kind_of(prev) != ("sting", "news"):
            misses.append(e.get("air_time") or "?")
    ok = not misses
    detail = (
        f"{checked} news bulletins checked, every one pinned with the C8 sting"
        if ok
        else f"{len(misses)}/{checked} bulletins missing the C8 pre-sting: {misses[:5]}"
    )
    return acceptance.PropertyResult("news_pin_stings", ok, detail)


def _check_handover_stings(timeline: list[dict]) -> acceptance.PropertyResult:
    """Every handover-framed boundary got the B6 sting immediately before its theme."""
    handover_ids = {
        pid for pid, p in programming.all_programs().items() if p.framing == "handover"
    }
    misses: list[str] = []
    checked = 0
    for i, e in enumerate(timeline):
        kind, key = _kind_of(e)
        if kind != "theme" or key not in handover_ids:
            continue
        checked += 1
        prev = timeline[i - 1] if i > 0 else None
        if _kind_of(prev) != ("sting", "handover"):
            misses.append(f"{key} at {e.get('air_time')}")
    ok = not misses
    detail = (
        f"{checked} handover themes checked, every one preceded by the B6 sting"
        if ok
        else f"{len(misses)}/{checked} handover boundaries missing B6: {misses[:5]}"
    )
    return acceptance.PropertyResult("handover_stings", ok, detail)


def _check_break_brackets(timeline: list[dict]) -> acceptance.PropertyResult:
    """Every ad break (a run of commercial/promo spots) is D18-bracketed in/out."""
    misses: list[str] = []
    checked = 0
    i, n = 0, len(timeline)
    while i < n:
        if timeline[i].get("format") not in _BREAK_FORMATS:
            i += 1
            continue
        start = i
        while i < n and timeline[i].get("format") in _BREAK_FORMATS:
            i += 1
        end = i - 1
        checked += 1
        before = timeline[start - 1] if start > 0 else None
        after = timeline[end + 1] if end + 1 < n else None
        has_in = _kind_of(before) == ("sting", "break_in")
        has_out = _kind_of(after) == ("sting", "break_out")
        if not (has_in and has_out):
            missing = [m for m, ok in (("in", has_in), ("out", has_out)) if not ok]
            misses.append(f"break at {timeline[start]['air_time']}: missing {missing}")
    ok = not misses
    detail = (
        f"{checked} ad breaks checked, every one bracketed"
        if ok
        else f"{len(misses)}/{checked} breaks missing a D18 bracket: {misses[:5]}"
    )
    return acceptance.PropertyResult("break_brackets", ok, detail)


def _check_no_theme_repeat(timeline: list[dict]) -> acceptance.PropertyResult:
    """No two consecutive boundary themes play the literal same clip back-to-back."""
    themes = [e for e in timeline if e.get("format") == "theme"]
    dupes: list[str] = []
    for a, b in zip(themes, themes[1:], strict=False):
        ca = Path(a["audio_path"]).name if a.get("audio_path") else None
        cb = Path(b["audio_path"]).name if b.get("audio_path") else None
        if ca is not None and ca == cb:
            dupes.append(f"{a.get('program')} -> {b.get('program')} both {ca}")
    ok = not dupes
    detail = (
        f"{len(themes)} theme fires, no back-to-back repeats"
        if ok
        else f"{len(dupes)}/{len(themes)} back-to-back repeats: {dupes[:5]}"
    )
    return acceptance.PropertyResult("no_theme_repeat", ok, detail)


# --- CLI ------------------------------------------------------------------
def main(argv: list[str]) -> int:
    """Run the audit; exit non-zero if any property fails (the R3.1 batch gate)."""
    ap = argparse.ArgumentParser(description="R3.0 jingle placement audit.")
    ap.add_argument("--hours", type=float, default=48.0, help="window length (h)")
    ap.add_argument("--step-minutes", type=int, default=60, help="clock step (min)")
    ap.add_argument(
        "--tick-every-hours", type=float, default=24.0, help="world-tick cadence (h)"
    )
    ap.add_argument(
        "--buffer-depth-hours", type=float, default=1.0, help="rolling buffer depth (h)"
    )
    ap.add_argument(
        "--dump", default=None, help="write the placed timeline JSON here (debug aid)"
    )
    args = ap.parse_args(argv)

    try:
        report = run_audit(
            window_hours=args.hours,
            step_minutes=args.step_minutes,
            tick_every_hours=args.tick_every_hours,
            buffer_depth_hours=args.buffer_depth_hours,
            dump_path=args.dump,
        )
    except acceptance._NoDatabaseError as exc:
        print(
            f"jingle-audit: needs a reachable Postgres/pgvector — {exc}",
            file=sys.stderr,
        )
        return 2

    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

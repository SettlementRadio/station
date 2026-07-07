"""D12 — the talk-continuity substrate: show position + the talk hand-off.

Consecutive talk segments in one program should read as ONE flowing show, not N
independent mini-shows back-to-back (see docs/PHASE_D_CONTINUITY_TASKS.md). This
module is the thin, pure substrate both later layers read; it changes no output on
its own (D12.0):

  * `ShowFlow` — where a content slot sits in its program run: `open` (the first
    content slot of a program instance), `continue` (a middle slot), or `close`
    (the last content slot before the program changes). Threaded into generation as
    the optional `flow` param on `formats.make_format_segment`; `None` = today's
    standalone open→close shape, so the direct B4/B5 CLI paths are unchanged.
  * `Handoff` — a compact record of how the PREVIOUS talk segment left off: its last
    spoken line(s), the active beat/topic handle, and an `open_thread` flag (is there
    more to say, or did it wrap?). The scheduler captures it after a talk render and
    persists it in `clock_state` (JSON, like `_last_cursor`) so the next slot — this
    top-up run or the next — can pick the thread up (D12.2).

Best-effort by design: a missing/short/failed hand-off just means the next segment
opens standalone (as today). Nothing here may block or fail generation.

Pure and dependency-light (only reads a `Segment`), unit-testable the way
`world/framing.py` and `world/clock.py` are.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .segment import Segment

# The three positions a content slot can hold in its program run. A slot that is
# both first AND last (a program with a single content slot) reads as `OPEN` — it
# still opens the show; a lone slot's clean close is handled by the standalone
# (`flow=None`) shape.
OPEN = "open"
CONTINUE = "continue"
CLOSE = "close"

# How many trailing spoken lines the hand-off carries as "where we left off". Small
# on purpose: enough for the next segment to reference, not a transcript. A domain
# constant (config.py convention #1), not an operator dial.
_HANDOFF_TAIL_LINES = 2

# A light sign-off heuristic for `open_thread` (D12.0): a tail that reads like an
# on-air sign-off means the thread wrapped (a standalone or `close` slot signs off).
# D12.2 replaces this heuristic with an orchestrator-emitted flag.
_SIGNOFF_RE = re.compile(
    r"\b(good ?night|good ?morning|see you|catch you|that's (all|it)|until (next|then)|"
    r"back (after|in a|soon)|take care|stay (safe|warm|with us)|signing off|"
    r"we'll leave (it|you)|from (all of )?us)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Handoff:
    """How the previous talk segment left off — the thread the next one can continue.

    JSON-serialisable (persisted in `clock_state`): `tail` is the last spoken line(s)
    verbatim, `topic` the beat/angle handle (the showrunner's brief), `open_thread`
    whether there is more to say (vs. a wrapped sign-off). `program`/`air_time` mark
    which slot it came from so a stale hand-off can be recognised.
    """

    tail: str
    topic: str
    open_thread: bool
    program: str | None = None
    air_time: str | None = None

    def to_dict(self) -> dict:
        """A plain dict for persistence in `clock_state` (JSON round-trips)."""
        return {
            "tail": self.tail,
            "topic": self.topic,
            "open_thread": self.open_thread,
            "program": self.program,
            "air_time": self.air_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Handoff:
        """Rebuild a `Handoff` persisted by `to_dict` (tolerant of missing keys)."""
        return cls(
            tail=str(data.get("tail", "")),
            topic=str(data.get("topic", "")),
            open_thread=bool(data.get("open_thread", False)),
            program=data.get("program"),
            air_time=data.get("air_time"),
        )


@dataclass(frozen=True)
class ShowFlow:
    """Where a content slot sits in its program run, plus the thread to carry in.

    `position` is `open`/`continue`/`close`; `handoff` is the previous talk segment's
    hand-off (None on a cold start or after the thread was cleared).

    D12.2 thread pacing: `thread_run` is how many talk segments the CURRENT thread has
    already aired (before this slot), and `continue_thread` is whether this slot should
    CONTINUE that thread (deepen the prior beat, pick up cold) rather than open or
    transition to a fresh one. The scheduler owns the counter and makes the decision
    (position + `open_thread` + the `convo_continuity_max_segments` budget); the
    writers' room just reads `continue_thread` + `handoff`.
    """

    position: str
    handoff: Handoff | None = None
    thread_run: int = 0
    continue_thread: bool = False
    # D12.4 — the on-air program's display name, so an `open`/`close` slot can sign
    # ON/OFF by name ("welcome to The Long Night" / "that's The Long Night for now").
    # None on the direct paths, keeping a generic open/close.
    program_name: str | None = None
    # D12.4 — the program's guest/interview cadence (0..1): how often this show
    # brings in a non-host voice — a played soundbite/record from a story figure, or
    # an invited interviewee. None = the global `convo_guest_chance`. Lets an
    # interview-forward show (culture, politics) run guests often and a solo-desk
    # show run none, straight from the grid.
    guest_chance: float | None = None


def show_position(*, is_first: bool, is_last: bool) -> str:
    """The `ShowFlow.position` for a content slot, given its program-run boundaries.

    `open` wins when a slot is both first and last (a single-content-slot program),
    so a program always opens; a lone slot's clean close rides the standalone shape.
    """
    if is_first:
        return OPEN
    if is_last:
        return CLOSE
    return CONTINUE


def _is_signoff(text: str) -> bool:
    """True when a tail reads like an on-air sign-off (the D12.0 open_thread guess)."""
    return bool(_SIGNOFF_RE.search(text))


def handoff_from_segment(seg: Segment, program: str | None = None) -> Handoff | None:
    """Capture the talk hand-off from a rendered segment, or None if there isn't one.

    Returns None for anything that isn't a real talk render (an evergreen fallback
    has `format="evergreen"`; a parse-empty draft has no script) — the caller then
    persists an EMPTY hand-off so the next segment opens fresh (D12.0 resilience).
    The tail is the last `_HANDOFF_TAIL_LINES` non-empty script lines verbatim; the
    topic is the showrunner's beat brief (`meta["beat"]`).
    """
    if seg.format != "talk" or not seg.script:
        return None
    lines = [ln.strip() for ln in seg.script.splitlines() if ln.strip()]
    if not lines:
        return None
    tail = "\n".join(lines[-_HANDOFF_TAIL_LINES:])
    topic = str(seg.meta.get("beat") or "").strip()
    return Handoff(
        tail=tail,
        topic=topic,
        open_thread=not _is_signoff(tail),
        program=program,
        air_time=seg.air_time,
    )


__all__ = [
    "CLOSE",
    "CONTINUE",
    "OPEN",
    "Handoff",
    "ShowFlow",
    "handoff_from_segment",
    "show_position",
]

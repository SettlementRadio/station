"""Talk-continuity demo (PHASE_D_CONTINUITY_TASKS.md D12.5).

Generates a program's worth of CONSECUTIVE talk segments at an advancing `now` and
prints the scripts back-to-back, so the single-show FLOW (D12) is visible on the page:

  * ONE real open at the top (a sign-on by program name), then COLD middles that pick
    up the prior exchange, then ONE close/sign-off at the end — not N mini-shows;
  * a settlement-time check only at the open/handover, never every segment;
  * the SAME thread carried forward (the showrunner continues the beat, the room opens
    by referencing the last lines) until the pacing budget forces a fresh subject.

It reproduces exactly what the scheduler does per slot: derive the show POSITION
(open/continue/close), carry the hand-off + thread-run forward, and hand the writers'
room the `ShowFlow`. The positional backbone comes from the real talk format.

Cost: a few Claude calls per segment (showrunner + orchestrator) — NO TTS (script
only) and NO gates, so it is far cheaper than `make buffer`. Needs `ANTHROPIC_API_KEY`
+ a seeded world (`make seed`). Writes NOTHING (no airplay, no schedule), so there is
nothing to roll back.

Run:  .venv/bin/python -m src.continuity_demo   (or: make continuity-demo)
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import flow as flow_mod
from .config import settings
from .flow import CLOSE, CONTINUE, OPEN, ShowFlow
from .formats import talk as talk_fmt
from .logging_setup import get_logger
from .segment import Segment
from .world import context, programming
from .writers import conversation as convo

log = get_logger(__name__)

_N_SEGMENTS = 5  # consecutive talk slots to generate in the show
_GAP = timedelta(minutes=12)  # advance `now` this much between slots


def _position(i: int, n: int) -> str:
    """Where slot `i` of `n` sits in the show: open first, close last, else continue."""
    if i == 0:
        return OPEN
    if i == n - 1:
        return CLOSE
    return CONTINUE


def main() -> int:
    """Generate the show, printing each positional script; writes nothing."""
    base = datetime.now()
    program = programming.program_for(base)
    hosts = list(program.hosts)
    if len(hosts) < 2:  # a solo/music program -> fall back to the two default hosts
        hosts = list(settings.convo_speaker_ids)

    print(
        f"\nTalk-continuity demo (D12) — {_N_SEGMENTS} consecutive talk slots of "
        f'"{program.name}" at an\nadvancing clock. Watch: ONE open (sign-on), COLD '
        "middles that pick up the thread,\nONE close — and a time-check only at the "
        "open. (Writes nothing.)\n"
        f"convo_continuity_enabled={settings.convo_continuity_enabled}  "
        f"timecheck={settings.convo_flow_timecheck}  "
        f"max_thread={settings.convo_continuity_max_segments}\n"
    )

    ctx = context.assemble(base, speakers=hosts)
    if len(ctx.speakers) < 2:
        print(
            "  needs two seeded hosts — run `make seed` first "
            f"(got {[c.id for c in ctx.speakers]}).\n"
        )
        return 1

    handoff: flow_mod.Handoff | None = None
    thread_run = 0
    for i in range(_N_SEGMENTS):
        now = base + i * _GAP
        position = _position(i, _N_SEGMENTS)
        continue_thread = (
            settings.convo_continuity_enabled
            and position != OPEN
            and handoff is not None
            and handoff.open_thread
            and thread_run < settings.convo_continuity_max_segments
        )
        show_flow = ShowFlow(
            position=position,
            handoff=handoff,
            thread_run=thread_run,
            continue_thread=continue_thread,
            program_name=program.name,
        )

        beat = convo.showrunner(ctx, now, flow=show_flow)
        backbone = talk_fmt._backbone_for(show_flow)
        script = convo.orchestrate(
            ctx, beat, now, extra_directive=backbone, flow=show_flow
        )

        tag = position.upper()
        if continue_thread:
            tag += " · continuing the thread"
        print(f"===== slot {i + 1}/{_N_SEGMENTS} — {now:%H:%M} — {tag} =====")
        print(f"  beat: {beat.strip()[:120]}")
        print(script.strip() + "\n")

        # Carry the hand-off + thread-run forward exactly as the scheduler does.
        seg = Segment(
            id=f"demo-continuity-{i}",
            format="talk",
            length_target_sec=settings.segment_default_length_target_sec,
            air_time=now.isoformat(),
            script=script,
            meta={"beat": beat},
        )
        new_handoff = flow_mod.handoff_from_segment(seg, program.id)
        if new_handoff is None:
            thread_run = 0
        elif continue_thread:
            thread_run += 1
        else:
            thread_run = 1
        handoff = new_handoff

    print(
        "Read top to bottom: it should play as ONE show — the middles come in cold and "
        "carry\nthe subject forward, and only the top signs on / time-checks. "
        "For voiced output: make buffer\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

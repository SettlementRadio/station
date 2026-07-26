"""Fast contrastive probe: one talk segment per programme.

Script only — no TTS, no writes. See scripts/audit_seed/README.md.
"""

from __future__ import annotations

import sys
from datetime import datetime

sys.path.insert(0, "/Users/pavel/station")

from src.flow import OPEN, ShowFlow  # noqa: E402
from src.formats import talk as talk_fmt  # noqa: E402
from src.world import context, programming  # noqa: E402
from src.writers import conversation as convo  # noqa: E402

SLOTS = [
    ("2026-07-27T10:12", OPEN),  # The Exchange (economy)
    ("2026-07-27T16:12", OPEN),  # The Circuit (sport)
    ("2026-07-27T22:12", OPEN),  # The Long Night (night)
    ("2026-07-27T07:12", OPEN),  # Morning Currents (flagship)
]

for iso, pos in SLOTS:
    now = datetime.fromisoformat(iso)
    prog = programming.program_for(now)
    hosts = list(prog.hosts)[:2] or ["vell", "wren"]
    ctx = context.assemble(now, speakers=hosts, domains=prog.domains)
    flow = ShowFlow(
        position=pos,
        handoff=None,
        thread_run=0,
        continue_thread=False,
        program_name=prog.name,
    )
    beat = convo.showrunner(ctx, now, flow=flow, program=prog)
    script = convo.orchestrate(
        ctx,
        beat,
        now,
        extra_directive=talk_fmt._backbone_for(flow),
        flow=flow,
        program=prog,
        length_target_sec=prog.talk_length_sec,
    )
    print("=" * 90)
    print(
        f"{iso}  {prog.id}  ({prog.name})  energy={prog.energy} "
        f"len={prog.talk_length_sec} hosts={hosts} domains={prog.domains}"
    )
    print(f"events_in_ctx={len(ctx.events)} dynamic_chars={len(ctx.dynamic)}")
    print("-" * 90)
    print("BEAT:", beat.strip())
    print("-" * 90)
    print(script.strip())
    print()
    sys.stdout.flush()

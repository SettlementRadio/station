"""Self-memory demo (PHASE_D_SELF_MEMORY_TASKS.md D13.4) — the journal loop on paper.

Makes the whole D13 loop — **air → journal → recall → callback** — visible without
TTS, across a program boundary AND a simulated day:

  * "Day 1": two talk slots generate real scripts (showrunner + orchestrator, no
    gates, no audio), and the REAL post-air extraction (D13.1, one `haiku` call per
    slot) distills each into journal entries — printed as captured.
  * "Day 2" (+1 day): the recall blocks (D13.2) are rendered from those rows and
    printed — the pair line the showrunner sees and the per-host history the
    orchestrator sees — then one more talk script is generated WITH the journal in
    hand. Read it for the callback: a held opinion, a remembered detail, a bit
    called back in passing — never re-run as the topic.

Cost: ~5 sonnet calls (scripts) + 2 haiku calls (extraction) — NO TTS, NO gates.
Needs `ANTHROPIC_API_KEY` + a seeded world (`make seed`). The demo's journal rows
are DELETED at the end (with their vectors): demo slots never aired, and only
aired segments may become memory (the D13 capture rule) — so the real journal is
left exactly as found.

    make journal-demo                          # whatever program is on now
    .venv/bin/python -m src.journal_demo 10:00 # preview a daytime pairing
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

from .config import settings
from .logging_setup import get_logger
from .segment import Segment
from .world import context, programming, store
from .writers import conversation as convo
from .writers import journal as journal_mod

log = get_logger(__name__)

_DAY1_SLOTS = 2  # talk slots that "air" (and journal) on day 1
_GAP = timedelta(minutes=12)
_SEG_PREFIX = "demo-journal-"  # the cleanup key: these rows never really aired


def _base_time(argv: list[str]) -> datetime:
    """The demo's start time: an optional `HH:MM` arg (today), else now."""
    if argv:
        try:
            hh, _, mm = argv[0].partition(":")
            return datetime.now().replace(
                hour=int(hh), minute=int(mm or 0), second=0, microsecond=0
            )
        except ValueError:
            print(f"  (ignoring bad time {argv[0]!r}; expected HH:MM)\n")
    return datetime.now()


def _print_captured(seg_id: str) -> None:
    """Print the journal rows the extraction just left behind for one slot."""
    with store.connect() as conn:
        rows = conn.execute(
            "SELECT host_id, kind, text, other_host FROM host_journal "
            "WHERE segment_id = %s ORDER BY id",
            (seg_id,),
        ).fetchall()
    if not rows:
        print("  (nothing durable captured — that's a valid outcome)")
    for host, kind, text, other in rows:
        pair = f" ↔ {other}" if other else ""
        print(f"  [{kind}{pair}] {host}: {text}")


def _cleanup() -> None:
    """Delete the demo's journal rows + their vectors (demo slots never aired)."""
    with store.connect() as conn:
        ids = [
            str(r[0])
            for r in conn.execute(
                "DELETE FROM host_journal WHERE segment_id LIKE %s RETURNING id",
                (_SEG_PREFIX + "%",),
            ).fetchall()
        ]
        if ids:
            conn.execute(
                "DELETE FROM embeddings WHERE corpus = %s AND entity_id = ANY(%s)",
                (store.JOURNAL_CORPUS, ids),
            )
    log.info("journal_demo_cleanup", removed=len(ids))


def main(argv: list[str] | None = None) -> int:
    """Run the loop; prints scripts, captures, recall blocks, and the callback."""
    base = _base_time(argv if argv is not None else sys.argv[1:])
    program = programming.program_for(base)
    hosts = list(program.hosts)
    if len(hosts) < 2:
        hosts = list(settings.convo_speaker_ids)

    print(
        f"\nSelf-memory demo (D13) — {_DAY1_SLOTS} talk slots of "
        f'"{program.name}" air on day 1 and are journaled; a day later the hosts '
        "write WITH that journal.\nWatch day 2 for a sparing CALLBACK — never a "
        "re-run. (Demo journal rows are removed at the end.)\n"
        f"convo_journal_enabled={settings.convo_journal_enabled}  "
        f"per_host={settings.convo_journal_per_host}  "
        f"window_days={settings.convo_journal_window_days}\n"
    )
    if not settings.convo_journal_enabled:
        print("  convo_journal_enabled is FALSE — nothing to demo.\n")
        return 1

    ctx = context.assemble(base, speakers=hosts)
    if len(ctx.speakers) < 2:
        print(
            "  needs two seeded hosts — run `make seed` first "
            f"(got {[c.id for c in ctx.speakers]}).\n"
        )
        return 1

    try:
        # --- Day 1: slots air; the archivist listens -------------------------
        for i in range(_DAY1_SLOTS):
            now = base + i * _GAP
            beat = convo.showrunner(ctx, now)
            script = convo.orchestrate(ctx, beat, now)
            print(f"===== day 1 · slot {i + 1}/{_DAY1_SLOTS} — {now:%H:%M} =====")
            print(script.strip() + "\n")

            seg = Segment(
                id=f"{_SEG_PREFIX}{i}",
                format="talk",
                length_target_sec=settings.segment_default_length_target_sec,
                air_time=now.isoformat(),
                script=script,
                meta={"speakers": [c.id for c in ctx.speakers], "beat": beat},
            )
            n = journal_mod.capture_segment(seg)  # the REAL D13.1 extraction
            print(f"----- journaled ({n} entries) -----")
            _print_captured(seg.id)
            print()

        # --- Day 2: the hosts remember themselves ----------------------------
        later = base + timedelta(days=1)
        pair = journal_mod.pair_section(ctx.speakers, later)
        print(f"===== day 2 — {later:%H:%M} +1d — what the room is handed =====")
        print("----- the showrunner's pair line (D13.2) -----")
        print((pair.strip() or "(no shared history in the window)") + "\n")

        beat = convo.showrunner(ctx, later, pair_block=pair)
        journal_block = journal_mod.journal_section(ctx.speakers, later, topic=beat)
        print("----- the orchestrator's journal block (D13.2) -----")
        print((journal_block.strip() or "(empty journal)") + "\n")

        script = convo.orchestrate(ctx, beat, later, journal=journal_block)
        print("===== day 2 — the script written WITH the journal =====")
        print(script.strip() + "\n")
        print(
            "Read day 2 against day 1's captures: a held opinion holds, a detail "
            "or bit may come back\nin passing — and yesterday's topic is not "
            "re-run. The continuity editor sees the same block\n(D13.3), so a "
            "reversal would be flagged before air.\n"
        )
        return 0
    finally:
        _cleanup()


if __name__ == "__main__":
    raise SystemExit(main())

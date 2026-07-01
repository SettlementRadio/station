"""Anti-repetition demo (PHASE_D_FRESHNESS_TASKS.md D5.3).

Generates a short run of talk segments at an ADVANCING `now` and shows the openings +
beats stay VARIED instead of looping — the D5 payoff, made visible. Each iteration:

  1. reads the recent-airplay memory (D5.0) and builds the "recently on air" steer
     blocks the writers' room gets (D5.2) — printed, so you SEE the growing avoid-list;
  2. runs the real showrunner → orchestrator (D5.2 wiring) with those steers;
  3. records the new segment's features (D5.1) so the NEXT iteration must avoid them.

At the end it prints a simple DISTINCTNESS check over the openings/beats it produced.

Cost: this spends a few Claude calls per segment (showrunner + orchestrator) — but NO
TTS (script only) and NO gates (safety/continuity), so it is far cheaper than `make
buffer`. Needs `ANTHROPIC_API_KEY` + a seeded world (`make seed`). It is richer after
`make world-tick` (a living world gives more topics to glance off).

Safe to run against a live dev DB: it records its airplay rows inside a single
transaction that is ROLLED BACK at the end, so nothing it writes persists (and, being
uncommitted, it drives the steer reads on its OWN connection — the real pipeline reads
committed rows across connections instead).

Run:  .venv/bin/python -m src.freshness_demo   (or: make freshness-demo)
"""

from __future__ import annotations

from datetime import datetime, timedelta

from . import freshness
from .config import settings
from .logging_setup import get_logger
from .segment import Segment
from .world import context, store
from .writers import conversation as convo

log = get_logger(__name__)

_N_SEGMENTS = 4  # how many talk segments to generate in the run
_GAP = timedelta(minutes=20)  # advance `now` this much between segments


def _steer(conn, now: datetime) -> tuple[str, str]:
    """Build the topic + opening steer blocks from THIS txn's airplay rows (D5.2).

    Mirrors `freshness.recent_topics_block` / `recent_openings_block`, but reads on the
    demo's own connection so it sees the rows this run just recorded (uncommitted). It
    reuses the same formatter the real path uses, so the printed steer matches prod.
    """
    within = timedelta(hours=settings.freshness_window_hours)
    limit = settings.freshness_recent_limit
    topic_recs = store.recent_airplay(conn, now, within=within)
    opening_recs = store.recent_by_format(conn, now, "talk", within=within)
    topics = freshness._distinct((r.topic for r in topic_recs), limit)
    openings = freshness._distinct((r.opening for r in opening_recs), limit)
    return (
        freshness._avoid_block("topic", topics),
        freshness._avoid_block("opening", openings),
    )


def _distinctness(label: str, items: list[str]) -> None:
    """Print a simple unique/total ratio for a list of fingerprints/handles."""
    kept = [i for i in items if i]
    unique = len({i.lower() for i in kept})
    total = len(kept)
    ratio = f"{unique}/{total}" if total else "0/0"
    verdict = "all distinct ✅" if total and unique == total else "some repeats ⚠"
    print(f"  {label:<10} {ratio:<7} {verdict}")


def main() -> int:
    """Generate the run, printing the steer + result each step; roll back the writes."""
    print(
        "\nAnti-repetition demo (D5) — four talk segments at an advancing clock, each "
        "steered\noff what aired before it. Watch the openings + beats stay varied. "
        "(Writes are rolled back.)\n"
        f"freshness_enabled={settings.freshness_enabled}  "
        f"mode={settings.freshness_mode}  "
        f"window={settings.freshness_window_hours}h\n"
    )

    base = datetime.now()
    openings: list[str] = []
    beats: list[str] = []

    with store.connect() as conn:
        try:
            # One assemble is enough for the demo — the world slice barely moves across
            # ~an hour; only `now` (the clock framing + the steer) advances each step.
            ctx = context.assemble(base, speakers=settings.convo_speaker_ids)
            if len(ctx.speakers) < 2:
                print(
                    "  needs two seeded hosts — run `make seed` first "
                    f"(got {[c.id for c in ctx.speakers]}).\n"
                )
                return 1

            for i in range(_N_SEGMENTS):
                now = base + i * _GAP
                topic_block, opening_block = _steer(conn, now)

                print(f"=== segment {i + 1} — {now:%H:%M} ===")
                if opening_block:
                    print("  steer (recent openings to avoid):")
                    for line in opening_block.splitlines()[1:]:
                        print(f"    {line}")
                else:
                    print("  steer: (cold start — nothing aired yet)")

                beat = convo.showrunner(ctx, now, recent_block=topic_block)
                script = convo.orchestrate(
                    ctx, beat, now, recent_openings=opening_block
                )

                seg = Segment(
                    id=f"demo-fresh-{i}",
                    format="talk",
                    length_target_sec=settings.segment_default_length_target_sec,
                    air_time=now.isoformat(),
                    script=script,
                    meta={"beat": beat},
                )
                rec = freshness.extract_features(seg)
                if rec is not None:
                    store.record_airplay(conn, rec)
                    openings.append(rec.opening or "")
                    beats.append(rec.topic or "")
                    print(f"  → beat:    {(rec.topic or '(none)')[:72]}")
                    print(f"  → opening: {rec.opening or '(none)'}\n")

            print("Distinctness across the run (unique / total):")
            _distinctness("openings", openings)
            _distinctness("beats", beats)
        finally:
            conn.rollback()  # the demo's airplay rows never persist

    print(
        "\nEach segment was handed the ones before it and told to open differently — "
        "that's the\nairplay memory (D5.0/D5.1) steering the writers' room (D5.2). "
        "For voiced output: make buffer\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

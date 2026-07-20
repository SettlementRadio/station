"""CLI for the intra-day micro-tick (PHASE_R_TASKS.md R4.1) — `make micro-tick`.

The light, near-live counterpart to the nightly world tick: fired by the C5 cron
every 2-4h, it may nudge ONE of today's live stories a small beat (a detail, a
reaction, a complication) or do nothing — a "quiet run" is the common, valid outcome.
The real logic lives in `world_tick.run_micro_tick` (which reuses the nightly advance
machinery — gate, materialise, embed); this module is just the process entry point,
kept as its own `python -m` target so the cron line is a plain one-liner separate from
the nightly `python -m src.world.world_tick`.

Unlike the nightly tick this is deliberately NOT a Batch job (latency matters, volume
is one call), so it runs on the direct haiku path regardless of `LLM_BATCH_ENABLED`.
Fails loud + non-zero for the timer; writes are transactional, so a failure never
corrupts the store.
"""

from __future__ import annotations

from ..logging_setup import get_logger
from . import world_tick

log = get_logger(__name__)


def main() -> int:
    """Run one micro-tick from the CLI; print a one-line summary; return exit code."""
    try:
        r = world_tick.run_micro_tick()
    except Exception as exc:  # noqa: BLE001 — fail loud for the timer; store rolled back
        log.error("micro_tick_failed", error=str(exc))
        print(f"Micro-tick FAILED (store unchanged): {exc}")
        return 1

    if r.acted:
        print(
            f"\nMicro-tick #{r.micro_tick}: advanced {r.story_id} "
            f"with a new beat ({r.beat_id})."
        )
    else:
        print(f"\nMicro-tick: quiet run — {r.reason} (nothing written).")
    return 0


if __name__ == "__main__":
    # .venv/bin/python -m src.world.micro_tick   (or: make micro-tick)
    # Needs `make seed` + a populated .env. Runs in seconds; safe to fire often.
    raise SystemExit(main())

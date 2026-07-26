"""The audit harness (PHASE_Q_TASKS.md §2) — measure the station, don't judge it.

Phase Q's whole premise is that the station's problems are *measured*, not felt: the
2026-07-26 external audit produced §1's baseline table, and every fix in the pack has to
prove itself as a numeric diff against it. This package is that loop:

  * `metrics.py`  — `collect_free()`: every §1 number readable from the DB, the grid and
                    the code. No API calls, no writes, seconds to run (Q0.0).

Two rules bind everything here (§2d):

1. **Pure reads.** The harness never writes world state, never generates, never mutates
   a dial. Measuring the station must be safe to do while it is on air.
2. **The building agent never judges its own work.** This package emits numbers; the
   gate (Q0.2) turns them into a pass/fail exit code, and the operator or the Q8
   auditor resolves everything a number cannot.

    .venv/bin/python -m src.audit          # or: make audit
"""

from __future__ import annotations

from .metrics import GROUP_KEYS, collect_free, render_table

__all__ = ["GROUP_KEYS", "collect_free", "render_table"]

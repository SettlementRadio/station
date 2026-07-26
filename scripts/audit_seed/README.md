# scripts/audit_seed/ — reference implementation for Q0

**These are not production code.** They are the throwaway scripts the external audit of
**2026-07-26** actually ran to produce every number in `docs/PHASE_Q_TASKS.md` §1. They are kept
so that **Q0** builds `src/audit/` from working code rather than from prose — and, more
importantly, so the baseline is measured **the same way** the original findings were.

Read `docs/PHASE_Q_TASKS.md` Q0 for the spec these become. Delete this directory once `src/audit/`
exists and its numbers match.

## The files

| File | Produces | Becomes (Q0) | API cost |
|---|---|---|---|
| `free_metrics.py` | §1a/§1b/§1c/§1f/§1g/§1h — world supply, title + quote register, grid format share, host load, context size, freshness dials, model tiers, $/segment | `src/audit/metrics.py::collect_free()` | **none** |
| `contrastive_probe.py` | §1a — the cross-run beat-identity test: 4 fixed slots on 4 contrasting shows, generated in independent contexts | `src/audit/probe.py`, part 1 | ~8 calls per run |
| `text_metrics.py` | §1d — register maths over any transcript (turn length, contractions, hedges, proper-noun footprint) | `src/audit/probe.py`, part 2 | none (post-processing) |
| `day_probe.py` | a contiguous scheduler day through the **real** `top_up()` — the "does an hour have shape" probe | `src/audit/probe.py`, the Q8 hour-listen | expensive; see below |

## Running them

```bash
.venv/bin/python scripts/audit_seed/free_metrics.py            # free, seconds
.venv/bin/python scripts/audit_seed/contrastive_probe.py       # ~8 real calls
.venv/bin/python scripts/audit_seed/text_metrics.py out.txt    # free
.venv/bin/python scripts/audit_seed/day_probe.py \
    --start 2026-07-27T06:50 --hours 3.5 --out day.json        # SLOW — read below
```

## What Q0 must preserve

1. **Isolation.** `contrastive_probe.py` and `day_probe.py` mock TTS and wrap every DB write in a
   rolled-back transaction (the `src/acceptance.py::_sim_environment` pattern) while leaving
   `llm.generate` **real**. A probe that mocks the LLM measures nothing. Verify the world is
   unchanged afterwards.
2. **The fixed slot list.** `2026-07-27` (a Monday) at `07:12` morning_currents, `10:12`
   the_exchange, `16:12` the_circuit, `22:12` long_night. Q8 must reproduce these exactly or the
   comparison is meaningless.
3. **Two independent runs.** The cross-run beat-identity finding only exists because the four slots
   were generated twice in separate processes with no shared state. One run cannot show it.
4. **The two-count distinction.** `active_stories` (what the tick and the room see) vs
   `stories_status_active_rows` (raw rows) — 23 vs 40 at baseline. Conflating them misreads the
   supply problem by ~2x.

## Known rough edges (fix them in Q0, don't copy them)

- Hardcoded `sys.path.insert(0, "/Users/pavel/station")` — Q0's version lives in `src/` and imports
  normally.
- `day_probe.py` took **>1 hour for 2 of 8 top-ups** at baseline (~25s/call × ~29k uncached tokens).
  It was killed mid-run during the audit. It becomes usable after Q2 cuts the context; until then,
  prefer `contrastive_probe.py`.
- `text_metrics.py`'s proper-noun regex catches sentence-initial words ("That", "Because") as
  well as names. Good enough to spot a 23-vs-7 dominance gap; too crude for a threshold. Q0 should
  use a real entity list (the `figures` + `stories` tables give you one for free).
- No `--dry-run`, no spend estimate, no JSON schema. Q0.1 requires all three.
- `free_metrics.py` pins a Monday (`2026-07-27`) for the grid walk so the week is deterministic —
  keep that, or format share drifts with the day you happen to run it.

# docs/audit/ — the Phase Q measurements

Everything here is a **measurement**, not an opinion. `docs/PHASE_Q_TASKS.md` §2 explains
why the loop is built this way; this file says what each artifact is and which rules bind
it.

## The one rule that matters

**`2026-07-26-baseline.json` is never edited.** It is the measurement of the station as it
stood before Phase Q touched anything, and it is named for **the date of the external
audit** (2026-07-26), not for the day it happened to be generated. Every relative
threshold in `gates.yaml` ("within ±5% of baseline", "≥ 1.5× baseline") is read against
it, and Q8 re-measures the same keys to produce its delta table. Editing it — even to
"correct" a number — silently rewrites the past and invalidates every gate that has run
since. If it is wrong, add a *new* run and say so in `docs/DEVLOG.md`.

## What is in here

| File | What it is |
|---|---|
| `2026-07-26-baseline.json` | **The committed baseline.** Never edited. |
| `gates.yaml` | Every §2b guard + every §3 pack threshold, transcribed. What `make gate` reads. |
| `<date>-<label>.json` | One audit run. `make audit` writes `-free`, `make audit-full` writes `-full` (or your `LABEL=`). |
| `<date>-<label>.transcripts.txt` | The scripts a probe run generated — the evidence behind its `register.*` and `continuity.*` numbers. |
| `blind/` | Q8's shuffled, unlabelled script pool (`make audit-blind`). `blind/key.json` is **gitignored** — it is the answer key. |

## The commands

```bash
make audit                          # free metrics, seconds, no tokens
make audit-full LABEL=q1            # + the API probe + the §2b checks (real calls)
make audit-full DRY=1               # price the probe without running it
make audit-compare BASE=baseline HEAD=q1
make gate PACK=Q1 ; echo "exit=$?"  # 0 = passed, 1 = failed
```

## How to read a gate

`make gate` prints one row per threshold and **exits non-zero if any of them miss**. The
exit code is the answer — not a summary of it, and not something to weigh up.

One wrinkle on the exit code itself: GNU make exits **2** when a recipe fails, so
`make gate PACK=Q1 ; echo "exit=$?"` prints `exit=2` on a miss, not the `exit=1` the pack's
§2a sketch shows. Non-zero is non-zero, but if you want the exact code (for CI, say), call
the module directly:

```bash
.venv/bin/python -m src.audit.gate --pack Q1 ; echo "exit=$?"   # 0 or 1, exactly
```

Two behaviours that look like bugs and are not:

- **A missing or null metric FAILS.** Gating a pack on a free-only `make audit` run fails
  every probe-measured threshold, because that run never measured them. Gating a pack
  before it has built its own metric fails too. "Not measured" is never green.
- **A pack's own rule replaces the global guard for the same key.** That is how §2b's
  "`cost.usd_per_talk_segment` ≤ 0.40 until Q2, ≤ 0.12 after" is expressed.

A gate is never "passed on balance". If the operator decides to accept a miss anyway, that
decision goes in `docs/DEVLOG.md` where the Q8 auditor will see it — §2a's "accept and
record".

## Two measurement notes worth knowing before you read a number

- **`register.contractions_per_100w` is noisy at these sample sizes.** Four measurements
  over the identical pinned slots on *unchanged* code gave 3.7, 3.7, 5.1 and 5.4. The
  guard floor is 3.5 by operator ruling (2026-07-26) rather than §2b's tabled 5.0; the
  reasoning is in `gates.yaml` beside the rule. Its siblings held steady across the same
  passes (`banned_abstractions_daytime` 0 every time, `hedges_per_1000w` 2.3–2.4).
- **`topic.top_entity_mentions` is per probe run, not per probe.** §1a's "named 23 times"
  counted one pass of the four pinned slots, so an absolute total would double under
  `--runs 2` and the ≤12 gate would be measuring the probe's size rather than the
  station's concentration. `top_entity_mentions_total` carries the raw count.

# PHASE_Q_TASKS.md — "Quality": the supply, form and register pack

> **What this is.** The external audit of **2026-07-26** (probes against the live world, real
> Anthropic calls, TTS mocked, writes rolled back) found that Phase R's register fix *worked* —
> the DJs no longer talk like academics — but that the station still doesn't read as a real
> station, for reasons that are **structural, not prompt-level**. The headline: the station
> consumes ~150 content slots a day and the world engine produces **2–4 stories a night**.
> Everything else on the list falls out of that ratio, or out of the fact that **63.5% of the
> station is one code path**.
>
> This pack carries the **measured baseline (§1)**, **every fix (§3, Q0–Q7)**, and a
> **reproducible feedback loop (§2)** so each task can prove itself against that baseline before
> the next one starts. The **final audit (Q8) is executed by a separate, unbriefed session** —
> see `docs/PHASE_Q_AUDIT_BRIEF.md`, which is written to stand alone.
>
> **Read first:** `CLAUDE.md`; `docs/PHASE_D_OVERVIEW.md` §2 (standing principles) + §2a (the
> state/seed/backup matrix — Q1 adds a table, so the matrix gains a row); `docs/PHASE_R_TASKS.md`
> (R1's register work and R2's grid stand — Q does not undo them); `src/world/world_tick.py`,
> `src/world/context.py`, `src/formats/__init__.py`, `src/writers/conversation.py`.
>
> **Standing rule for this pack — never regress R1.** R1.2/R1.3's plain-speech register and the
> `plain_register` acceptance property are load-bearing. Every Q task must leave
> `make acceptance` green (9 properties) *and* the Q0 register metrics no worse than baseline.
>
> **Sequencing vs the server track:** Q1–Q7 are local code/content work and must land **before the
> C9 soak** — they change what the soak listens to. Q8's audit is the gate that says the soak is
> worth running.

---

## 0. Decisions locked (from the audit)

1. **The feedback loop is a committed script, not a prose instruction.** `make audit` computes the
   metrics; the baseline is a checked-in JSON file; every gate is a numeric diff. Agent judgment is
   used only where it belongs — the blind qualitative read in Q8.
2. **Supply before steering.** Widening the anti-repetition window (Q6) or ranking events (Q2)
   before the world produces more stories would *starve* the showrunner. Q1 comes first among the
   content fixes.
3. **New formats, not new programmes.** R2 already shipped 35 programme names. The station needs
   more *forms*, and `formats/__init__.py` already takes a new format as a registry entry.
4. **Don't rewrite the canon.** It is the strongest artefact in the repo. Q5 *adds* one cornerstone
   (the ordinary and the petty) and puts a register instruction where generation can actually see
   it — the tick's own prompt.
5. **Per-task API validation is authorised.** The operator has approved real token spend on each
   task's gate. Budget guidance in §2c.

---

## 1. THE BASELINE — what the 2026-07-26 audit measured

*Everything in this section is a measurement, not an impression. Q0 turns it into a machine-checked
file; Q8 re-measures the same numbers. Where a number is marked **(probe)** it came from real
Anthropic calls against the live world; the rest are free reads of the DB, the grid, or the code.*

### 1a. World supply — the root cause

| Metric | Baseline | Source |
|---|---|---|
| New stories per nightly tick | **2–4** (`world_tick_new_stories_min/max`) | `src/config.py` |
| Max active stories | **24** (`world_tick_max_active_stories`) | `src/config.py` |
| Active stories the tick + the room actually see (`store.active_stories`, excludes `arc_stage='past'`) | **23** | DB |
| Raw rows with `status='active'` (a bigger number, **not** the supply figure) | **40** | DB |
| Events in the ±14d context window | **74–82** | probe |
| Content slots the grid consumes per day | **~150** (~130 talk + ~24 news) | grid tiling |
| **Airings available per story per day** | **~6** | derived |

**Consequence, proved.** The same four shows were generated **twice, in separate processes, with no
shared state**. Three of four picked the *identical* beat:

| Show | Run 1 | Run 2 |
|---|---|---|
| The Exchange 10:12 | Meridian Accords / Cold Harbor opt-in | Meridian Accords / Cold Harbor opt-in |
| The Circuit 16:12 | Cold Harbor beacon failure; Sola Pitch "characteristically composed" | Cold Harbor rescue; Sola Pitch "characteristically composed" |
| Morning Currents 07:12 | Meridian Accords / Cold Harbor | Meridian Accords / Cold Harbor |
| The Long Night 22:12 | Sael's Reach log | Theta-9 |

Across those four segments — four programmes, four host pairs, four dayparts — **"Cold Harbor" is
named 23 times**; the next most-named proper noun is "Accords" at 7. **(probe)**

### 1b. Form — 63.5% of the station is one function

Measured across the week by clock composition × hours on air:

| Format | Share of content slots |
|---|---|
| `talk` | **63.5%** |
| `news` | **23.6%** |
| `music` | 10.8% |
| `chart` | 2.1% |

35 programme names; **6 registered formats** (`talk`, `news`, `music`, `chart`, `commercial`,
`promo`) — but only **4 ever appear in a grid clock**, and `commercial`/`promo` are break-fillers,
not programme forms. So: effectively **two forms** carrying 87% of the station. Every non-news,
non-music slot runs the identical path: showrunner picks one beat → two hosts banter 550–750 words.

### 1c. News and rota

| Metric | Baseline |
|---|---|
| Bulletin word budget | **800–1000 words, every bulletin** (`format_news_words_low/high`) — no per-programme override exists |
| Bulletin length target | **300s** (`format_news_length_target_sec`), global |
| Bulletins per day | ~24 → **~2h/day of one anchor reading** |
| News anchors | **1** (`news_anchor_ids = ['thorn']`) |
| Host load (lead+second, 15-min resolution) | vell **8.3 h/day**, the-archivist **7.8**, wren **7.7**, joss 4.6, zhe 4.3, thorn 3.1 (+ all news pins), mira 3.0, sera 2.6, kael 2.6, orin 1.6 |

GRID_V2's own design brief set "nobody carries 6h/day". Missed by ~40%.

### 1d. Register — plain, but not spoken

| Metric | Baseline | Reference |
|---|---|---|
| Contractions per 100 words | **5.4** | healthy — R1 worked, do not regress |
| Banned house-poetry abstractions on daytime shows | **0** | R1 holding |
| Hedges / fillers / false starts per 1000 words | **1.7** | real speech transcripts run **30–60** |
| Median turn length | **16 words** | |
| Turns ≥ 40 words | **20%** (The Circuit: median turn **36 words**) | monologue, not banter |
| Stored world quotes containing *any* hedge or filler | **1 of 120** | every source in the world is an aphorist |
| Stored world quotes containing any contraction | **41%** | |
| Story titles matching `The Noun Phrase: A Clause` | **92% of 40** (78% of subtitles open with an article) | one schema |

### 1e. Continuity — the D12 verbatim repeat is still live

Consecutive-slot run, "The Far Towns". Slot 1 closed:

> **Sera:** By the time this airs they'll have eaten. I hope it tasted the way you said it would.
> **Mira:** Good. That's the right answer.

Slot 2 closed:

> **Sera:** By the time this airs, they'll have eaten. I hope it tasted like Mira said it would.
> **Mira:** Good. That's the right answer.
> **Sera:** It is, isn't it. By the time you read this I am recovered.

Verbatim replay of the previous segment's close, plus a garbled line. Mira also told the **same
anecdote** (Hale at Anchor-7, the life-support drone as tonic note) in two consecutive segments.
Three slots — 18 minutes — on one story about a cook who won't stop using a small measure. **(probe)**

### 1f. Prompt shape, cost and speed

| Metric | Baseline | Source |
|---|---|---|
| `cache_read_input_tokens` per call | **40,291** | probe — the CO0–CO4 bible cache works |
| `input_tokens` (uncached) per call | **28,342** | probe — the *dynamic* half was never bounded |
| Dynamic block | **~131,000 chars** (~81k events + ~50k canon) | `context.assemble` |
| Events rendered per call | **74–82**, full bodies, **no cap, no ranking** | `store.events_in_range` has no limit |
| Canon facts rendered per call | **all 267, uncached, every call** | `_select_canon` falls back to `all_canon` when `topic is None` |
| `topic` passed on the live path | **never** (`scheduler.py:267`) — so **D2's semantic RAG never runs in production** | code |
| Measured cost per talk segment | **$0.372** (4 calls) | usage ledger, 2026-07-26 |
| Implied text cost | **~$30–55/day, ~$1–1.6k/month** | derived — against CLAUDE.md's "near-trivial" |
| Wall-clock per LLM call | **~25s** | probe |

### 1g. Freshness and the acceptance gate

| Metric | Baseline |
|---|---|
| `freshness_window_hours` | **6.0** — a topic may legitimately return every 6h, forever |
| `freshness_recent_limit` | **10** |
| `freshness_mode` | `prefer` (soft steer, not a ban) |
| `make acceptance` | **9/9 green** while every finding above is true |

The acceptance properties run against a **mocked** `llm.generate`, so they measure mechanism, not
writing. `no_repetition` checks opening fingerprints and adjacent duplicates — it passes cleanly on
a day where three of four shows lead on Cold Harbor. This is not a bug in the properties; it is
their scope. Q0 adds the missing measurement alongside them, it does not replace them.

### 1h. Model routing

| Tier | Baseline | Note |
|---|---|---|
| `sonnet` | `claude-sonnet-4-6` | one generation behind |
| `opus` | `claude-opus-4-8` | one generation behind |
| `haiku` | `claude-haiku-4-5-20251001` | current |
| Batch API | used by the **tick only** — the scheduler's generation path never batches | 50% left unclaimed |

`src/providers/llm.py` sends no `temperature`, `top_p` or `thinking`, so a model swap is a
config-only change with no breaking-parameter risk.

---

## 2. THE FEEDBACK LOOP

### 2a. How it works

```
Q0 builds  ──▶  make audit            free metrics (DB + grid + code)   ~0 tokens, seconds
                make audit-full       + the API probe                    ~16 calls
                        │
                        ▼
        docs/audit/2026-07-26-baseline.json      (committed, never edited)
                        │
   each task ──▶ make audit-full --label qN.M  ──▶ docs/audit/<date>-qN.M.json
                        │
                        ▼
              make audit-compare BASE=…baseline HEAD=…qN.M
                        │
                        ▼
        a delta table — the task's "Done when" is a numeric assertion on it
```

**The rule: a task is not done until its own gate metric moved and no guarded metric regressed.**
Each task below names both.

**How you know a gate failed.** Every threshold in §3 is transcribed into
`docs/audit/gates.yaml` (Q0.2), and **`make gate PACK=Q1`** exits **non-zero** if any check misses.
That is the answer — not the agent's summary of it. Run it yourself; it takes seconds and needs no
tokens:

```bash
make gate PACK=Q1 ; echo "exit=$?"      # exit=0 passed, exit=1 failed
```

A gate is never "passed on balance". Any ✗ means the pack is not done — either iterate, or say
explicitly "accept and record", which puts the miss in the DEVLOG where the Q8 auditor will see it.

### 2b. The guarded metrics (must never regress, any task)

| Metric | Floor |
|---|---|
| `register.contractions_per_100w` | ≥ 5.0 (baseline 5.4) |
| `register.banned_abstractions_daytime` | = 0 |
| `acceptance.properties_passed` | = 9 |
| `tests.passed` | ≥ current count (661 at pack start), 0 failures |
| `cost.usd_per_talk_segment` | ≤ 0.40 until Q2, ≤ 0.12 after |

### 2c. Token budget

| Gate | Calls | Approx. cost pre-Q2 | Post-Q2 |
|---|---|---|---|
| `make audit` (free metrics) | 0 | $0 | $0 |
| `make audit-full` (adds the probe) | ~16 | $2–3 | ~$0.60 |
| Q8 full audit (probe ×2 runs + continuity run + a 4h scheduler day) | ~220 | — | ~$12–20 |

Running the full probe after **every** task is affordable and is the recommended default.

### 2d. Who decides a gate — and who never does

**The building agent never judges whether its own work succeeded.** Every gate in this pack resolves
one of exactly three ways:

| Kind | Resolved by | Example |
|---|---|---|
| **Numeric** | the harness, mechanically | `topic.top_entity_mentions ≤ 10` |
| **Operator** | the human, on a blind or labelled sample, against a stated rubric | Q1.1's "8 of 20 items are genuinely mundane" |
| **Deferred** | the Q8 auditor, from committed artifacts | Q7.1 when the A/B is marginal |

If a "Done when" cannot be written as one of those three, it is not a gate — rewrite it or delete
it. In particular:

- **A default must be stated for every judgment call, and the default is always "no change".**
  Ambiguity, noise, and "it reads better to me" all resolve to the status quo. This is what stops
  a task from being marked done because work was done.
- **Any criterion containing "a human reading…" means the operator, not the agent.** Print the
  sample, stop, and ask. Do not self-score.
- **Pre-register before you look.** Where a task compares two options (Q7.1), the decision rule goes
  into the DEVLOG *before* the results exist.
- **A null result is a completed task.** "Measured, no improvement, reverted" is a real outcome and
  must be recorded as success, not retried until the number moves.

---

## 3. THE TRACKER

Work in order. Q0 is mandatory first — without it nothing else has a gate.

| Pack | What | Baseline finding it fixes | Depends on | Built? |
|---|---|---|---|---|
| **Q0** | The audit harness + the committed baseline | §2 (there is no loop today) | — | ✅ |
| **Q1** | Story supply: the small-items generator | §1a — 3 stories/day vs 150 slots | Q0 | ✅ (gate accepted with a miss — DEVLOG 2026-07-27) |
| **Q2** | Bounded, ranked context + wire the RAG | §1f — 28k uncached tokens, dead RAG | Q0 (Q1 makes ranking load-bearing) | 🔨 built, **gate unresolved** — probe blocked on API credit (DEVLOG 2026-07-28) |
| **Q3** | Three new formats (round-up / letters / interview) | §1b — 63.5% one code path | Q1 (the round-up eats Q1's supply) | ☐ |
| **Q4** | News word budget per programme + 2nd anchor + rota | §1c | Q0 | ☐ |
| **Q5** | Register at the source: tick quotes/titles, permission to be boring, the ordinary cornerstone | §1d | Q0 | ☐ |
| **Q6** | Continuity pickup fix + widen freshness | §1e, §1g | **Q1** (freshness needs supply) | ☐ |
| **Q7** | Model routing refresh + batch the scheduler path | §1h | Q0 | ☐ |
| **Q8** | **The post-fix audit — separate, unbriefed session** | all | Q1–Q7 | ☐ |

**Build order (one line):**
**Q0 → Q1 → Q2 → Q3 → Q4 → Q5 → Q6 → Q7 → Q8.**
*Q2 may be pulled ahead of Q1 if iteration speed is painful — it takes ~25s/call down to ~5s and
80% off the per-call cost, which makes every later gate cheaper. Q6's freshness widening must
never precede Q1.*

---

## Q0 — The audit harness + the committed baseline

*Everything else in this pack is gated on this. Build it first, exactly, and do not tune any dial
while building it — Q0 must capture the world **as it is today**.*

### Q0.0 — The free metrics (`src/audit/metrics.py`)
**Goal:** every §1 number that needs no API call, computed from the DB, the grid and the code.
**Do:** a module exposing `collect_free() -> dict`, with these groups (keys are the contract — Q8
reads them by name, so do not rename them later):

- `world.*` — `new_stories_per_tick_min/max`, `max_active_stories`, `active_stories`,
  `events_in_window`, `stories_total`, `domains_covered`, and the title-schema pair
  `title_colon_schema_pct`, `title_subtitle_article_pct`.
- `quotes.*` — `count`, `mean_words`, `median_words`, `pct_with_contraction`,
  `hedges_per_1000w`, `pct_under_12w`.
- `grid.*` — `format_share` (a dict: talk/news/music/chart, weighted by clock composition ×
  hours on air across the full week), `programs`, `registered_formats`,
  `host_hours_per_day` (a dict), `max_host_hours_per_day`, `news_anchor_count`,
  `news_words_low/high`, `news_words_distinct_per_program` (int — 1 today, >1 once Q4 lands).
- `context.*` — `bible_chars`, `dynamic_chars`, `events_rendered`, `canon_rendered`,
  `topic_passed_on_live_path` (bool — grep the scheduler's call site, or assert via a spy).
- `freshness.*` — `window_hours`, `recent_limit`, `mode`.
- `models.*` — the three tier ids, `batch_enabled_paths` (list).
- `cost.*` — `usd_per_talk_segment` read from the `usage` ledger (last 7 days, `job='talk'`).

**Constraints:** pure reads. No writes, no API calls, no mutation of world state. Must run in
seconds against a live Postgres, and degrade with an explicit `null` (never a crash) if the DB is
unreachable.
**Done when:** `make audit` prints a readable table and writes
`docs/audit/<YYYY-MM-DD>-<label>.json`; re-running it twice in a row produces identical values for
every key except timestamps.

### Q0.1 — The API probe (`src/audit/probe.py`)
**Goal:** the §1a / §1d / §1e / §1f numbers that need real generation.
**Do:** `collect_probe(runs: int = 2) -> dict`. It must reuse the **real** pipeline
(`context.assemble` → `conversation.showrunner` → `conversation.orchestrate`) with **TTS mocked and
every DB write inside one rolled-back transaction**, exactly as `src/acceptance.py::_sim_environment`
does — but with `llm.generate` **left real**. Three parts:

1. **Contrastive probe** — a FIXED slot list (pin these; Q8 must be able to reproduce them byte for
   byte): `2026-07-27T07:12` morning_currents, `10:12` the_exchange, `16:12` the_circuit,
   `22:12` long_night. Generate all four, `runs` times, in independent contexts.
   Emit `topic.*`: `cross_run_beat_identity_pct` (share of slots whose two runs name the same
   dominant entity), `top_entity_mentions`, `top_entity_share`, `distinct_entities_per_segment`.
2. **Register probe** — over every generated script, emit `register.*`:
   `median_turn_words`, `pct_turns_over_40w`, `pct_turns_under_4w`,
   `contractions_per_100w`, `hedges_per_1000w`, `banned_abstractions_daytime`.
3. **Continuity probe** — 5 consecutive slots of one programme with the real `ShowFlow`
   (the `src/continuity_demo.py` shape). Emit `continuity.*`:
   `max_verbatim_overlap_chars` (longest common substring between consecutive segments' scripts),
   `repeated_ngram_rate` (share of 8-grams in segment *n* that also appear in *n−1*),
   `distinct_beats_in_run`.
4. **Prompt probe** — one throwaway generation, emit `context.cached_tokens`,
   `context.uncached_tokens`, `context.seconds_per_call`.

**Constraints:** the probe must never touch `segments/`, the real schedule, airplay, or the journal.
It must print its own estimated token spend before starting and honour a `--dry-run` that reports
the plan and spends nothing.
**Done when:** `make audit-full` runs end to end, the four numbers in §1f reproduce within ±10%, and
`psql` shows the world unchanged afterwards (story/quote/journal counts identical).

### Q0.2 — Compare, the machine-readable gates, and the committed baseline
**Goal:** a gate that **fails by itself**, in the terminal, without anyone's opinion.

**Do:**
- `make audit-compare BASE=… HEAD=…` prints one row per metric — value, delta, `✓ / ✗ / —`.
- **`docs/audit/gates.yaml`** — a committed file holding **every threshold in §3 of this pack**,
  transcribed verbatim, plus the §2b guards that apply to all packs:

  ```yaml
  guards:                                   # checked on EVERY pack
    register.contractions_per_100w: {min: 5.0}
    register.banned_abstractions_daytime: {max: 0}
    acceptance.properties_passed: {min: 9}
  packs:
    Q1:
      world.items_per_night: {min: 30}
      topic.cross_run_beat_identity_pct: {max: 40}
      topic.top_entity_mentions: {max: 12}
    Q2:
      context.uncached_tokens: {max: 8000}
      context.seconds_per_call: {max: 12}
      cost.usd_per_talk_segment: {max: 0.12}
      context.topic_passed_on_live_path: {equals: true}
    # …one block per pack, transcribed from §3
  ```

- **`make gate PACK=Q1`** — reads `gates.yaml` + the newest audit JSON, prints a pass/fail table,
  and **exits non-zero on any failure**. This is the command the operator runs; the exit code is
  the answer, not a summary. Output shape:

  ```
  Q1 GATE  (docs/audit/2026-08-02-q1.json vs 2026-07-26-baseline.json)
    ✓ world.items_per_night                 41      ≥ 30
    ✗ topic.top_entity_mentions             14      ≤ 12          FAIL
    ✓ topic.cross_run_beat_identity_pct     25.0    ≤ 40
    ✓ register.contractions_per_100w        5.6     ≥ 5.0   guard
  GATE FAILED — 1 of 4 checks.  exit 1
  ```

- A metric that is **missing** from the audit JSON counts as **FAIL**, never as pass. "Not
  measured" must never be silently green.

- Then run the harness on the untouched world and commit the result as
  **`docs/audit/2026-07-26-baseline.json`** (name it for the audit date, not today's, and never
  edit it afterwards). Add `docs/audit/README.md` saying exactly that.

**Done when:** the baseline file is committed; `make audit-compare BASE=baseline HEAD=baseline`
prints all-zero deltas and exits 0; `make gate PACK=Q0` exits 0; **and a deliberately broken
threshold in `gates.yaml` makes `make gate` exit 1** (prove the failure path works — a gate that
cannot fail is not a gate); the numbers match §1 within ±10%.

### Q0.3 — Wire it into the gate
**Do:** `make audit` in `ADMIN_MANUAL.md` (+ a `→ Phase E panel` tag), the Makefile help block, and
a DEVLOG entry recording the baseline. Add the topic-concentration metric to the `acceptance`
summary output as an **informational line** (not a 10th property — acceptance stays mocked and
mechanism-only; §1g explains why).
**Done when:** docs match as-built; `make acceptance` still green at 9.

---

## Q1 — Story supply: the small-items generator *(the keystone)*

*The station needs ~150 things to talk about a day and the world makes 3. A real newsroom's day is
a handful of arc'd stories plus **dozens of small ones that get thirty seconds each** — a price, a
result, a delay, a fine, a queue, a complaint, a birth. That second class does not exist.*

### Q1.0 — The `items` class: schema + store
**Goal:** a cheap, high-volume, arc-less companion to `stories`.
**Do:** a new `items` table behind `src/world/store.py` — `id`, `text` (ONE sentence),
`domain`, `in_world_datetime`, `tags[]`, `source` (`'tick'`), `created_tick`, `status`. No figures,
no quotes, no beats, no arc stage. Add `store.insert_items`, `store.items_in_range`,
`store.prune_items`. Items **expire**: they are read only within `settings.item_window_hours`
(default 36) and GC'd past `item_retention_days` (default 7) — unlike stories, world history does
not need to keep "the grain price moved".
**§2a matrix:** add the `items` row — *tick-owned, survives `seed-canon`, cleared by `reset-world`,
not backed up* (they are disposable by design). Update `docs/PHASE_D_OVERVIEW.md` §2a.
**Done when:** migration applies cleanly on the live DB (**migration, not truncate-reseed** — the
world is alive, OVERVIEW §2); unit tests cover insert/read/prune; `reset-world` clears them and
`seed-canon` does not.

### Q1.1 — The generator: `run_item_tick()`
**Goal:** 30–60 believable small items a night, for near-nothing.
**Do:** a sibling of `run_tick()` in `src/world/world_tick.py` (or `world/items.py` — your call, keep
it behind the same module boundary). It must:
- run on the **`haiku` tier through the Batch API** (`settings.item_tick_tier = "haiku"`) — this is
  exactly the high-volume/low-stakes job CLAUDE.md routes to haiku, and the nightly batch is where
  the 50% discount lives;
- share the **cached bible block** (`bible=ctx.bible`) so the per-call cost is the small variable
  part only;
- ask for one line each, no arc, no figures, spread across `DOMAINS` **plus** the everyday
  categories the world currently has no vocabulary for: **prices, delays, results, weather,
  rosters, repairs, fines, queues, births/deaths, arrivals, complaints, small crime, lost property,
  what's cheap this week, what broke again**;
- pass the **safety gate** per item (cheap) but **not** the full continuity escalation — an item
  that flags is dropped, not regenerated (they are disposable and there are dozens);
- dedupe against the last `item_dedup_window_days` of items by the existing Jaccard helper.
**New dials:** `item_tick_enabled` (True), `item_tick_min` (30), `item_tick_max` (60),
`item_tick_tier` ("haiku"), `item_tick_max_tokens`, `item_window_hours` (36),
`item_retention_days` (7), `item_dedup_window_days` (3).
**Register instruction (load-bearing — do not skip):** the prompt must say these are **ordinary,
often boring, sometimes petty**; that a good night's batch includes things nobody would write a
story about; and must ban the epigram register outright (see Q5.0, which fixes the same failure in
the story prompt — write the two instructions to match).
**Done when:** `make item-tick` produces 30–60 items in one batch run in under a few minutes;
logged cost for the run is **under $0.15**; `make console` shows the item count; and — **operator
gate, §2d** — the agent prints 20 randomly sampled items and stops, and the operator confirms **at
least 8 are genuinely mundane** (something no one would write a story about). The agent does not
score this itself; if the operator is unavailable, the task is blocked, not passed.

### Q1.2 — Items reach the room
**Goal:** the writers' room and the news desk can actually use them.
**Do:**
- `context.assemble` gains an `items` slice, rendered as its own compact section —
  *"Small things happening right now (a line each — use one in passing, or build a short item
  around it):"* — **one line per item, never a paragraph**. Domain-filtered by the programme's
  `domains` exactly as R4.3 does for events.
- The showrunner's fresh-pick task gains the option: *a small item is a legitimate beat for a short
  slot* — so a 4-minute flagship item can be a price move, not a constitutional convention.
- `news_select.py` gains an **items tail**: after the selected stories, 2–4 items as the bulletin's
  short back-half (the "and briefly…" run real bulletins close on).
**Done when:** a generated flagship talk item and a generated bulletin each reference at least one
item; `make context` shows the items section; existing news tests green.

### Q1.3 — Cron + docs
**Do:** `make item-tick` in the Makefile; wire into the C5 cron docs beside `world-tick`
(same nightly job, run it *before* the story tick so the story tick sees the day's texture);
`ADMIN_MANUAL.md` (+ panel tag: items count on the World screen); DEVLOG.

### **Q1 GATE**
Run `make audit-full --label q1`. **Required:**
- `world.items_per_night` ≥ 30 *(new metric — add it to `collect_free` in this task)*
- `topic.cross_run_beat_identity_pct` **≤ 40%** (baseline 75%)
- `topic.top_entity_mentions` **≤ 12** (baseline 23)
- `topic.distinct_entities_per_segment` **≥ 1.5×** baseline
- No §2b guarded metric regressed.

---

## Q2 — Bounded, ranked context + wire the RAG

*The cached half of CO0–CO4 works perfectly (40,291 tokens read at 0.1×). The dynamic half was never
bounded and is now 28,342 uncached tokens per call. That is the cost, the 25s latency, **and** the
reason the beat-picker sees 80 equally-weighted paragraphs.*

### Q2.0 — Cap and rank the event block
**Goal:** the room reads the 15 things that matter, not 80 things flat.
**Do:** in `src/world/context.py`, a pure, unit-testable `rank_events(events, now, domains) ->
list[Event]` scoring on **recency × arc stage × domain match × breaking-ness**, then truncating to
`settings.context_events_max` (default **15**; programme-domain matches get a reserved sub-quota,
`context_events_domain_min`, default 5, so a vertical never loses its own field to a louder story).
Render the top N with bodies and — this matters for continuity — the next `context_events_tail`
(default 10) as **title-only one-liners**, so the room still knows they exist.
**Constraints:** `rank_events` is pure (no DB, no clock reads beyond the passed `now`), tested the
way `world/framing.py` is. **Set the cap generously at first** and tighten it only after Q1's
supply lands — a tight cap on a thin world starves the picker.
**Done when:** unit tests cover ranking and the domain quota; `make context` shows ≤15 bodied events
+ a titles tail; `context.uncached_tokens` drops materially.

### Q2.1 — Wire the semantic RAG that already exists
**Goal:** stop shipping all 267 canon facts uncached on every call.
**Do:** the live path never passes a `topic`, so `_select_canon` falls through to `all_canon`.
Fix it at the source: `scheduler.py`'s `make_format_segment(...)` call passes the **active
programme's brief** (or its `tagline`) as `topic`, and `formats/__init__.py` threads it through.
Then `_select_canon`'s existing hybrid semantic+tag path runs for real, bounded by
`settings.context_canon_top_k`. **Keep the whole-canon fallback** for when vectors are unavailable —
that guard is correct, it was just always firing.
**Done when:** `context.topic_passed_on_live_path` is `true` in the audit; `canon_rendered` is
`context_canon_top_k`, not 267; a `context_canon_hybrid` debug line appears in a real scheduler run;
segments still reference correct canon (spot-check 3).

### Q2.2 — Prove the cache is still whole
**Goal:** the CO1 equivalence invariant survives the change.
**Do:** re-run `make costprobe` and `make costprobe-ab`. The bible/cards blocks must be untouched
(they are the cached prefix — only the per-call section changes).
**Done when:** `cache_read_input_tokens` is unchanged (~40k) while `input_tokens` falls; the A/B
probe shows no quality divergence.

### **Q2 GATE**
Run `make audit-full --label q2`. **Required:**
- `context.uncached_tokens` **≤ 8,000** (baseline 28,342)
- `context.cached_tokens` unchanged within ±5% (the bible cache must not break)
- `context.seconds_per_call` **≤ 12s** (baseline ~25s)
- `cost.usd_per_talk_segment` **≤ 0.12** (baseline 0.372)
- `context.topic_passed_on_live_path` = `true`
- `topic.*` metrics no worse than after Q1.

---

## Q3 — Three new formats

*35 programme names, 4 registered formats, effectively two forms. `formats/__init__.py` is the right
seam and it is clean: a format is a `FormatSpec` entry. Build three.*

### Q3.0 — `roundup` — one host, 6–8 short items, ~90 seconds
**Goal:** the form that consumes Q1's supply and finally varies the pace.
**Do:** `src/formats/roundup.py` — a **single** host reads 6–8 Q1 items as a rapid list, one or two
sentences each, no discussion, a one-line top and tail. Register: brisk and plain, closer to the
news desk than to the talk show, but with the host's own voice. `talk_length_sec`-style dial
`format_roundup_length_target_sec` (default **90**) and its own word budget. Register in `FORMATS`;
add `roundup` to grid clocks (Q4 does the placement).
**Done when:** a rendered round-up runs 80–110s, names 6+ distinct items, and repeats nothing from
the bulletin that preceded it in the same hour.

### Q3.1 — `letters` — the mailbag
**Goal:** the station acquires an audience.
**Do:** `src/formats/letters.py` — 3–4 invented in-world listener letters (name, world, a real
question or complaint or correction), read and answered by the hosts. Letters are **generated,
gated, and stored** (a small `letters` table, same disposable posture as `items`) so a letter can be
referenced later and a running correspondent can recur. Must draw on the world (items and stories)
so the letters are *about* something. Bans: no meta-jokes about the station being AI; the disclosure
posture is handled by the ident, not the fiction.
**Done when:** letters persist and are re-readable; `make format FMT=letters` works; the letters'
register is **measurably plainer than the hosts'** in the same segment (shorter median turn, higher
hedges/1000w — assert it, don't eyeball it); and — **operator gate, §2d** — the operator reads one
rendered mailbag and confirms it sounds like listeners rather than hosts inventing prompts.

### Q3.2 — `interview` — one guest, 8 minutes, real questions
**Goal:** a form where the hosts are not agreeing with each other.
**Do:** extend the D9.3 guest machinery into a *format*, not a garnish: one invited in-world figure
(preferably a `figures` row attached to a live story), 8 minutes, host asks and **pushes back**,
guest is plainer-spoken than the hosts and is allowed to be evasive, boring, or wrong. This is the
single best place in the station to break the "everyone is equally articulate" flatness (§1d) —
the prompt must say so explicitly.
**Done when:** a rendered interview has ≥6 genuine question-answer exchanges, the guest's register
is measurably plainer than the hosts' (shorter median turn, fewer subordinate clauses), and the
guest declines to answer at least sometimes.

### Q3.3 — Place them in the grid
**Do:** `docs/programming/grid.yaml` — round-up into the flagship clocks and the 15-minute desks;
letters into The Mailbag and one weekend slot; interview into the `[interview]`-tagged programmes
(Morning Currents, Evening Currents, The Long View). Update `docs/programming/README.md`,
`docs/programming/GRID_V2.md` (a v2.1 note), and re-run `make jingle-audit` — new formats need
their fallback clips to resolve.
**Done when:** the tiling test is green, `make jingle-audit` shows zero unresolved boundaries, and
`make console` shows the new day.

### **Q3 GATE**
Run `make audit-full --label q3`. **Required:**
- `grid.format_share['talk']` **≤ 45%** (baseline 63.5%)
- `grid.registered_formats` **≥ 9** (baseline **6**; +roundup +letters +interview)
- `grid.formats_in_clocks` **≥ 7** (baseline **4** — the number that actually matters: a format
  nothing schedules is not a form. Add this key to `collect_free` in this task.)
- No format below 3% except `chart` (i.e. the new forms actually air)
- `register.median_turn_words` unchanged or lower; guarded metrics green.

---

## Q4 — News budget, a second anchor, and the rota

### Q4.0 — Per-programme bulletin length
**Goal:** an hourly bulletin is 2 minutes, not 5.
**Do:** the plumbing already exists — `conversation._word_budget` scales the talk word budget from a
programme's `talk_length_sec`. Do the same for news: a grid field `news_length_sec` (absent = the
global default), threaded through `formats/news.py::_build_system` so
`format_news_words_low/high` scale proportionally. Set hourly shorts to **~250 words / 120s**;
midday `settlement_desk` and the two flagship desks keep the full read.
**Done when:** `grid.news_words_distinct_per_program` > 1 in the audit; a rendered hourly bulletin is
100–140s and a rendered midday desk is ~300s; news tests green.

### Q4.1 — A second anchor
**Do:** `news_anchor_ids` gains a second cast member (Mira or Orin — operator's call; whoever gets
it needs a `Public bio:` line and a news-appropriate card note). Alternate by daypart, deterministic
from the hour so the rota is predictable and testable.
**Done when:** a simulated day shows both anchors; the R7 `djs-public.json` feed reflects it.

### Q4.2 — Rebalance the rota
**Goal:** nobody carries 6h/day — GRID_V2's own target.
**Do:** grid edit only. Widen the pairings; give Orin, Kael, Sera and Mira real load; pull Vell,
the Archivist and Wren down. Keep the night's identity intact — that is the best thing on the
station and it is Vell/Archivist-shaped, so trim their *daytime* presence, not their nights.
**Done when:** `grid.max_host_hours_per_day` **≤ 6.0** (baseline 8.3) and no host below 2.0.

### **Q4 GATE**
`grid.max_host_hours_per_day ≤ 6.0`; `grid.news_anchor_count ≥ 2`;
`grid.news_words_distinct_per_program ≥ 2`; guarded metrics green.

---

## Q5 — Register at the source

*R1 fixed the DJs. It never reached the **world**: the tick's proposal prompt has no register
instruction at all, so Sonnet defaults to literary and every figure in the world speaks in epigrams
(1 hedge in 120 quotes; 92% of titles share one schema).*

### Q5.0 — Teach the tick how people actually talk
**Goal:** quotes that sound like sources, titles that sound like headlines.
**Do:** in `src/world/world_tick.py`'s `_propose_system` (and the matching `_advance_system` and the
R4.1 micro-tick prompt — **all three**, or the register leaks back in on advancement):
- **Quotes:** state the target explicitly — most people quoted in the news are not eloquent. Mostly
  flat and factual; often hedged (*"I think"*, *"probably"*, *"we'll have to see"*); sometimes
  graceless or repetitive; **ban the aphorism shape outright** (the *"X is one thing. Y is another.
  Those are not the same"* construction, and the two-sentence summation that lands a moral). Let
  roughly one in five be genuinely unquotable — the flat, useless quote a real bulletin still runs.
- **Titles:** ban the `The Noun Phrase: A Clause Explaining It` schema as the default. Ask for
  varied shapes — a plain statement, a fragment, a number, a name.
**Done when:** `quotes.hedges_per_1000w` and `world.title_colon_schema_pct` both move (see gate);
and — **operator gate, §2d** — the agent prints 20 new quotes **with the speaker's name and role
hidden**, and the operator can correctly attribute at least 12 to the right *kind* of person
(technician / official / artist / trader) from voice alone. Below 12, the register fix is cosmetic
and the task is not done.

### Q5.1 — Permission to be boring
**Goal:** dialogue that sounds *spoken*, not merely plain.
**Do:** in `src/writers/conversation.py::orchestrate`'s delivery block, add — **beside**, never
replacing, the R1.2 rules: real talk contains dead weight. Licence a line that goes nowhere; a host
who isn't interested in this one; a half-thought abandoned; a repeat because someone didn't hear;
the occasional filler. Explicitly: **not every line needs to land**, and a segment where one host
carries it is more real than two people trading perfect beats.
**Guard:** this is the highest-risk change in the pack — it pushes against R1's plainness. Run the
`plain_register` acceptance property and the Q0 register metrics on **both sides** and stop if
contractions fall or the banned list is touched.
**Done when:** `register.hedges_per_1000w` rises toward 10+ while
`register.contractions_per_100w` ≥ 5.0 and `banned_abstractions_daytime` = 0.

### Q5.2 — The missing cornerstone: the ordinary and the petty
**Goal:** give the tick a vocabulary for a world where not everything is dignified.
**Do:** a new `docs/canon/51-ordinary.md` cornerstone — bad food, price gouging, the paperwork
everyone hates, a rivalry between two stations that is simply petty, a fashion everyone agrees is
ugly, the beloved local idiot, what breaks constantly, what is embarrassing, what is cheap. Written
in the register it should produce: concrete, everyday, unsentimental — per SPIRIT §5a's instruction
to canon authors. Tag from `TAGS.md`; extend the palette if needed. Add `ordinary` to the tick's
`DOMAINS` and to two or three cast cards' affinity tags (the D9.4 lesson).
**Do NOT** rewrite the existing cornerstones. They are the strongest artefact in the repo.
**Done when:** `make seed-canon` + re-embed; canon fact count grows; a few ticks later at least one
story or item lands in the `ordinary` domain; `docs/canon/AUDIT.md` updated.

### **Q5 GATE**
Run `make audit-full --label q5`. **Required:**
- `quotes.hedges_per_1000w` **≥ 8** (baseline ~1 across 120 quotes)
- `quotes.pct_with_contraction` **≥ 60%** (baseline 41%)
- `world.title_colon_schema_pct` **≤ 55%** (baseline 92%)
- `register.hedges_per_1000w` **≥ 8** (baseline 1.7)
- `register.contractions_per_100w` **≥ 5.0** and `banned_abstractions_daytime` = 0 — **hard**.

---

## Q6 — Continuity pickup + freshness

### Q6.0 — Stop the verbatim replay
**Goal:** a continuing slot moves forward instead of re-reading the last one's close.
**Do:** `_pickup_section` in `src/writers/conversation.py` currently hands the room the previous
segment's **tail verbatim** and says "carry that forward" — the model treats quoted dialogue as text
to continue. Two changes:
- pass the tail as a **third-person summary** (*"you just finished saying that the cook still
  reaches for the small measure"*), generated once by the cheap tier at hand-off capture time and
  stored on the `Handoff` (a new `tail_summary` field beside `tail`), **not** as quoted lines;
- move the `covered` beats list **above** the summary in the prompt, and add the anecdote-level
  ban: a story, comparison or example already used in this thread may not be re-used.
Keep `tail` on the `Handoff` for back-compat and logging; a missing summary degrades to today's
behaviour (best-effort, per D12's rule that nothing here may block generation).
**Done when:** `continuity.max_verbatim_overlap_chars` and `continuity.repeated_ngram_rate` both
fall sharply (see gate); the D12 tests still pass.

### Q6.1 — Widen the freshness window *(only after Q1)*
**Goal:** a topic can't legitimately return every 6 hours.
**Do:** `freshness_window_hours` 6 → **48**; `freshness_recent_limit` 10 → **40**; keep
`freshness_mode = prefer` (a hard ban risks starving a thin domain). Check
`freshness_retention_margin` still bounds the airplay table sensibly at the new window, and that
`sweep()` isn't now deleting rows the block still needs.
**Blocked on Q1** — widening this against a 23-story world removes the showrunner's options
entirely. Do not land it early.
**Done when:** `freshness.window_hours` = 48 in the audit; a simulated 48h run shows no topic
airing more than 3×; `no_repetition` acceptance property still green.

### **Q6 GATE**
- `continuity.max_verbatim_overlap_chars` **≤ 60** (baseline: a full two-line exchange, ~120+)
- `continuity.repeated_ngram_rate` **≤ 2%**
- `continuity.distinct_beats_in_run` **≥ 4 of 5** (baseline: 3 slots on one beat)
- `topic.*` no worse than Q1.

---

## Q7 — Model routing + the unclaimed batch discount

### Q7.0 — Refresh the tiers
**Do:** in `src/config.py` — `model_sonnet` → **`claude-sonnet-5`**, `model_opus` →
**`claude-opus-5`**, `model_haiku` unchanged. Update the `_PRICES` table (Sonnet 5 is $3/$15, with
$2/$10 intro pricing through 2026-08-31; Opus 5 is $5/$25, same as 4.8).
**Watch for:** Sonnet 5's tokenizer produces **~30% more tokens for the same text**, so re-baseline
with `count_tokens` before believing any cost delta, and check `convo_max_tokens` /
`format_news_max_tokens` still fit their outputs. Adaptive thinking is **on by default** on both —
set `thinking={"type": "disabled"}` explicitly in `llm.generate` to preserve current behaviour and
cost, or leave it on at `effort: "low"` and measure. `llm.py` sends no sampling parameters, so
nothing else breaks. **Read the `claude-api` skill before editing** — do not write model ids or
thinking config from memory.
**Done when:** a full `make audit-full` runs green on the new tiers; cost per segment re-measured
and recorded; `make costprobe` shows the cache still hitting.

### Q7.1 — The world tick on the better brain *(pre-registered A/B — the agent does NOT decide)*
**Goal:** the tick runs once a night and is the source of everything on air — the one place where a
better model could compound across ~150 segments. **This is a hypothesis, not a plan.** The default
outcome is "stay on sonnet"; opus has to earn the swap.

**Do — in this order, and write step 3 down before step 2 produces any output:**

1. **Freeze the design.** 5 tick runs per arm (≈15–20 stories each — one night per arm is
   statistically meaningless), from the **identical starting world snapshot** (the rolled-back-txn
   pattern), with the **identical post-Q5.0 prompt**. The *only* variable is
   `world_tick_propose_tier`. Save both arms' raw JSON to `docs/audit/q7-ab/{sonnet,opus}/`.
   **Keep `item_tick_tier = "haiku"`** — volume there, quality here.
   *Do not compare either arm against `2026-07-26-baseline.json`: that was measured on the old
   prompt, so the comparison would price Q5.0's work as a model difference.*
2. **Measure.** Run the Q0 metrics over each arm's stories and quotes:
   `world.title_colon_schema_pct`, `quotes.hedges_per_1000w`, `quotes.pct_with_contraction`,
   `world.domains_covered`. Record actual USD per arm from the usage ledger.
3. **Pre-register the decision rule** — commit it to the DEVLOG **before** looking at step 2's
   output, so the goalposts cannot move:
   - **Adopt opus** only if **both** hold: (a) ≥2 of the 4 metrics improve by ≥20% with **none**
     regressing, **and** (b) the blind read (step 4) favours opus by **≥0.7 mean points**.
   - **Exactly one holds** → marginal. **Do not decide.** Leave the tier on sonnet, keep the
     artifacts, and hand the call to Q8 (the brief already tells the auditor to look).
   - **Neither holds** → record the null result and stay on sonnet.
4. **Blind read.** Pool both arms' story titles + summaries into one shuffled, unlabelled file;
   the **operator** (not the building agent) scores each 1–5 on *"would this be interesting on
   air?"* and *"does this read like something that actually happened?"*. Reveal the key after.

**Who decides:** not the agent that built it. The rule fires mechanically, or the operator's blind
scores decide, or it defers to Q8. The agent's job here is to produce numbers, not a verdict.
"It felt better" resolves to sonnet.

**Cost note:** if adopted, record the per-night delta. Opus 5 is $5/$25 vs Sonnet 5's $3/$15, and
the tick is ~28 calls/night — a small absolute number, but a quality claim still has to be worth it.

**Done when:** the pre-registered rule is in the DEVLOG with a timestamp **earlier than** the
results; both arms' raw output is committed under `docs/audit/q7-ab/`; the rule was applied
mechanically; and the DEVLOG entry states plainly which arm won and by what margin — or records the
null or deferred result. **A null result is a successful completion of this task.**

### Q7.2 — Batch the scheduler's generation path
**Goal:** claim the 50% that CLAUDE.md calls mandatory.
**Do:** the scheduler's top-up is a *near-live* path, so it cannot block on a batch round-trip —
but the **deep end of the buffer** can. Where the buffer is being filled more than
`settings.schedule_batch_lead_hours` (default 3) ahead of air, route generation through the existing
`providers/llm` batch path; keep the near-air slots direct. Batch must not leak into the tick's
semantics or the near-live path (OVERVIEW §2).
**Done when:** a top-up filling 3h+ of runway logs batch usage; the never-dead fallback still covers
a batch failure; `cost.usd_per_talk_segment` falls again.

### **Q7 GATE**
`cost.usd_per_talk_segment` **≤ 0.08**; `models.*` reflect the new tiers; all guarded metrics green;
`make acceptance` 9/9.

---

## Q8 — The post-fix audit *(separate, unbriefed session)*

**This task is not executed by the agent that built Q0–Q7.** Open a **fresh session** and hand it
one thing: **`docs/PHASE_Q_AUDIT_BRIEF.md`**. That brief is written to stand alone — it carries the
baseline, the harness commands, the blind-scoring protocol, and an explicit instruction **not to
read this file** until after its qualitative scores are recorded.

**Why it is structured that way.** Two different guards against bias:
1. **The numbers are script-computed, not agent-judged.** An agent cannot rationalise
   `topic.cross_run_beat_identity_pct`.
2. **The qualitative read is blind.** The auditor scores a shuffled pool of pre-fix and post-fix
   scripts against a fixed rubric, without labels, and only learns which is which after scoring.

**Before opening that session, the builder must:**
- have `docs/audit/2026-07-26-baseline.json` committed and unmodified;
- run `make audit-full --label pre-q8` and commit it;
- generate the blind pool: `make audit-blind` writes ~20 scripts — half regenerated from the
  **baseline git tag** (`git worktree` at the pre-Q0 commit), half from HEAD — into
  `docs/audit/blind/<uuid>.txt` with a **separate, gitignored** key file. *(Build this small
  helper as part of Q0.2 so it exists when needed.)*
- **not** summarise the fixes anywhere the auditor will read first.

**Done when:** the audit session has produced `docs/audit/2026-XX-XX-q8-report.md` containing the
delta table, the blind scores with the key revealed, and a plain verdict on the question this whole
pack exists to answer: **does it read like a real station now?** — plus what it would take if the
answer is still no.

---

## 4. What this pack deliberately does NOT do

Recorded so a later reader doesn't "fix" them by accident:

- **No canon rewrite.** Q5.2 *adds* a cornerstone. The existing 25 are the strongest asset here.
- **No DJ prompt re-tune beyond Q5.1.** R1 already fixed the register; the measured problem is
  supply and form, not voice.
- **No new programmes.** There are 35 names and were 4 forms. Q3 adds forms.
- **No 10th acceptance property.** Acceptance stays mocked and mechanism-only (§1g); real-text
  quality is `make audit`'s job. Conflating them would make both worse.
- **No change to the two seams.** Every fix here is a registry entry, a dial, a prompt, or a
  bounded query. If a task starts wanting to change `llm.generate` or `Segment`, stop and re-read.

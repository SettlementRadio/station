# PHASE_Q_AUDIT_BRIEF.md — the independent post-fix audit

> **You are the auditor. Read this file and nothing else first.**
>
> This brief is self-contained on purpose. You have been opened in a fresh session so that you
> arrive without knowing what was changed or why. That is the point: your job is to **measure the
> station as it is now**, compare it against a recorded baseline, and say plainly whether it reads
> like a real radio station.
>
> **Do not read `docs/PHASE_Q_TASKS.md`, `docs/DEVLOG.md`, or the recent git log until you have
> completed Part 3 and written your blind scores to disk.** Those documents describe the intended
> fixes and will bias your qualitative read. You may read them in Part 4, when you write up.
>
> Reading `CLAUDE.md`, `docs/ARCHITECTURE.md` and the code you need to run things is fine and
> expected.

---

## 0. What this station is, in one paragraph

Settlement Radio is a continuously broadcasting fictional sci-fi radio station set 600 years ahead
of the present, written end to end by Claude. A nightly **world tick** generates in-world happenings
into a Postgres world-store; a **scheduler** fills a rolling audio buffer from a weekly programming
**grid**; each slot is produced by a **format** (talk / news / music / …) that assembles world
context and generates a spoken script. The product is the *writing* and the *composition* — whether
it sounds like a station a person would leave on.

**Ignore TTS quality entirely.** Voice is a known limitation and is out of scope. Judge text only.

---

## 1. Your deliverable

`docs/audit/<today>-q8-report.md`, containing:

1. **The delta table** — every metric, baseline vs now, with a pass/fail against §3 below.
2. **The blind scores** — your rubric scores on an unlabelled script pool, *then* the key revealed.
3. **A verdict**, in plain words: does it read like a real station? If not, what is still missing,
   ranked, with evidence.
4. **Anything the numbers missed.** The metrics are a proxy. If you hear something wrong that no
   metric captures, that is the most valuable thing you can report — say it.

---

## 2. Part 1 — Run the harness (objective, ~20 min)

A measurement harness is committed. It computes free metrics from the DB/grid/code, and probe
metrics from real Anthropic calls with **TTS mocked and all writes rolled back** — it will not
disturb the live world.

```bash
# free metrics only — no tokens
make audit

# adds the real-API probe (~16 calls). Check the printed spend estimate first.
make audit-full --label q8

# the diff you will report
make audit-compare BASE=docs/audit/2026-07-26-baseline.json \
                   HEAD=docs/audit/<today>-q8.json

# every pack's own thresholds, applied mechanically (exit != 0 means a miss)
for p in Q1 Q2 Q3 Q4 Q5 Q6 Q7; do make gate PACK=$p ; echo "$p exit=$?"; done
```

`docs/audit/gates.yaml` holds the thresholds. **Report the exit codes, not a narrative summary of
them.** If a pack's gate exits non-zero, that pack did not meet its own stated bar — say so plainly,
and check whether the DEVLOG records it as knowingly accepted or silently passed. A miss recorded
honestly is fine; a miss reported as a pass is the more serious finding.

`docs/audit/2026-07-26-baseline.json` is the pre-fix snapshot. It is committed and must not be
edited. If `make audit` does not exist or does not run, **stop and report that** — the feedback loop
itself has failed, which is a finding.

**Verify the harness is honest before trusting it.** Do not skip this:
- Run `make audit-full` twice; free metrics must be identical, probe metrics within ~10%.
- Before and after, check the world is untouched:
  `psql settlement_radio -c "select count(*) from stories; select count(*) from quotes; select count(*) from host_journal;"`
- Read `src/audit/probe.py` and confirm `llm.generate` is **real** (not mocked) and that TTS and DB
  writes are isolated. A probe that mocks the LLM measures nothing.

---

## 3. Part 2 — The baseline and the thresholds

These are the numbers measured on **2026-07-26**, before any of the work you are auditing. Report
each as improved / unchanged / regressed.

### 3a. Topic variety — *the headline*

| Metric | Baseline | Target |
|---|---|---|
| `topic.cross_run_beat_identity_pct` | **75%** (3 of 4 shows picked the identical beat on two independent runs) | ≤ 30% |
| `topic.top_entity_mentions` | **23** ("Cold Harbor", across 4 segments on 4 different shows) | ≤ 10 |
| `topic.distinct_entities_per_segment` | *(recorded in the baseline file)* | ≥ 2× baseline |
| `world.active_stories` | **23** (`store.active_stories` — excludes `arc_stage='past'`; the raw `status='active'` row count was 40, which is *not* the supply figure — do not confuse them) | — |
| `world.items_per_night` | **0** (the concept did not exist) | ≥ 30 |

### 3b. Form

| Metric | Baseline | Target |
|---|---|---|
| `grid.format_share['talk']` | **63.5%** | ≤ 45% |
| `grid.format_share['news']` | **23.6%** | ≤ 20% |
| `grid.registered_formats` | **6** (`talk`,`news`,`music`,`chart`,`commercial`,`promo`) | ≥ 9 |
| `grid.formats_in_clocks` | **4** — only 4 of the 6 are ever scheduled; this is the number that matters | ≥ 7 |
| `grid.max_host_hours_per_day` | **8.3** | ≤ 6.0 |
| `grid.news_anchor_count` | **1** | ≥ 2 |
| `grid.news_words_distinct_per_program` | **1** (every bulletin 800–1000 words) | ≥ 2 |

### 3c. Register

| Metric | Baseline | Target |
|---|---|---|
| `register.contractions_per_100w` | **5.4** | **≥ 5.0 — must not regress** |
| `register.banned_abstractions_daytime` | **0** | **= 0 — must not regress** |
| `register.hedges_per_1000w` | **1.7** (real speech transcripts: 30–60) | ≥ 8 |
| `register.median_turn_words` | **16** | ≤ 16 |
| `register.pct_turns_over_40w` | **20%** | ≤ 12% |
| `quotes.hedges_per_1000w` | **~1** (1 of 120 stored quotes had any hedge) | ≥ 8 |
| `quotes.pct_with_contraction` | **41%** | ≥ 60% |
| `world.title_colon_schema_pct` | **92%** (one title schema) | ≤ 55% |

### 3d. Continuity

| Metric | Baseline | Target |
|---|---|---|
| `continuity.max_verbatim_overlap_chars` | a full two-line exchange replayed verbatim between consecutive segments (~120+) | ≤ 60 |
| `continuity.repeated_ngram_rate` | *(recorded in the baseline file)* | ≤ 2% |
| `continuity.distinct_beats_in_run` | **3 beats across 5 slots** — 18 minutes on one small story | ≥ 4 of 5 |

### 3e. Cost, speed and plumbing

| Metric | Baseline | Target |
|---|---|---|
| `context.uncached_tokens` per call | **28,342** | ≤ 8,000 |
| `context.cached_tokens` per call | **40,291** | unchanged ±5% (this cache working is a *good* thing) |
| `context.seconds_per_call` | **~25s** | ≤ 12s |
| `context.topic_passed_on_live_path` | **false** (semantic recall was dead code in production) | true |
| `cost.usd_per_talk_segment` | **$0.372** | ≤ 0.08 |
| `acceptance.properties_passed` | **9/9** | 9/9 |

---

## 4. Part 3 — The blind qualitative read *(do this before reading anything else)*

The numbers are proxies. This part is where your judgment earns its keep — so it is deliberately
blind.

`docs/audit/blind/` contains ~20 unlabelled scripts. Roughly half were generated **before** the work
you are auditing and half **after**, shuffled. The key is **not** in the repo — ask the operator for
it, or find it at the path the harness prints, **only after your scores are written to disk**.

### The rubric — score each script 1–5, and write one line of evidence per score

| # | Dimension | 1 | 5 |
|---|---|---|---|
| 1 | **Sounds spoken, not written** | every line is well-formed and lands; no filler, no dead weight | hesitations, repeats, a line that goes nowhere, someone not interested |
| 2 | **The hosts are distinct people** | interchangeable, equally articulate, equally witty | different competence, different density, one carries it |
| 3 | **The world feels inhabited** | dignified, civic, tasteful; everything is meaningful | prices, complaints, someone's bad day, things that are simply annoying |
| 4 | **It is radio, not an essay** | two people discussing one idea at length | pace changes, items move, something happens |
| 5 | **Would you leave it on?** | admirable but tiring | you'd keep listening |

Also record, per script, **the one sentence that most sounds like a person actually said it** and
**the one that most sounds authored**. Those two quotes are usually more informative than the score.

### Then, and only then

Reveal the key. Report mean score per dimension for the pre-set and the post-set. **A rise of less
than 1.0 on dimensions 1, 3 and 4 means the changes did not land where they mattered**, whatever the
quantitative table says — report that plainly.

---

## 5. Part 4 — Your own investigation (the part no rubric covers)

The harness measures what the previous audit thought to measure. You should now look for what it
missed. Spend real tokens here; the operator has authorised it.

Suggested probes — do these, and anything else your judgment says:

1. **Listen to an hour.** Generate a contiguous scheduler hour (news → items → talk → …) text-only
   and read it top to bottom as a listener would. Does the *hour* have a shape, or is it a
   sequence of unrelated well-written pieces? This is the question a per-segment metric cannot ask.
2. **Two days apart.** Sample the same programme on two simulated days a week apart. Is it
   recognisably the same show with different content, or a different show?
3. **The seams.** Read three programme boundaries and one handover. Do the joins work, or does each
   segment behave as if it were the only thing on air?
4. **The world's own voice.** Pull 20 fresh `quotes` rows and 20 `items` rows straight from the DB.
   Could you tell a racing steward from an archivist from a tailor? If everyone still sounds the
   same, the register fix was cosmetic.
5. **The night.** The night shows were the strongest thing on the station at baseline. Confirm they
   were not damaged by changes aimed at the daytime — a regression there would be a real loss.
6. **Cost reality.** Read the `usage` ledger for the last 7 days and compute the actual daily text
   spend. `CLAUDE.md` requires it to stay near-trivial. Baseline was ~$30–55/day.
7. **Any deferred decision.** If `docs/audit/q7-ab/` exists, an A/B was run and deliberately left
   undecided because the result was marginal. Its pre-registered decision rule is in the DEVLOG,
   timestamped before the results. **You are the tie-breaker.** Score the two arms' output blind
   (the directory names give the arms away — shuffle and strip before you read), apply the rule as
   written, and record the call. If it is still genuinely too close, say "no measurable difference,
   stay on the cheaper option" — that is a real answer, not a failure to decide.

You may read `docs/PHASE_Q_TASKS.md`, the DEVLOG and the git log **now** — after your blind scores
are on disk — to check whether anything claimed as done is actually done, and whether anything was
done that shouldn't have been.

---

## 6. How to report

Be blunt. The operator's standing brief to the previous auditor was: *"I need to understand if
there are any real improvements pending, or there's a dead end and we better drop, or we've achieved
the quality I wanted."* Answer that question directly, in that shape.

Specifically, do not:
- grade on effort, or on how much was built;
- soften a regression because the intent was good;
- report a metric as passed if you did not run it (say "not measured");
- accept a number you could not reproduce twice.

If the honest answer is "the numbers moved and it still doesn't sound like a station," that is the
single most useful sentence you can write, and you should write it first.

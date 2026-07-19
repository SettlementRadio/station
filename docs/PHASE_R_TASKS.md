# PHASE_R_TASKS.md — "Real Radio" refresh (the six-topic improvement pack)

> **What this is.** The operator's 2026-07-19 audit named six problems: (1) the grid runs long,
> slow blocks instead of many short programs; (2) jingles need validation + specs for whatever the
> new grid adds; (3) there is no admin panel for the things an operator actually does daily;
> (4) news doesn't evolve *during* the day; (5) the DJs talk like academics, not people;
> (6) program content drifts to philosophy ("the light", "the distance") instead of a living
> world with problems. Plus a seventh ask (2026-07-19 follow-up): the public web player should
> look and work like a real station's site — grid, current program, up next, the DJs (R7,
> which absorbs and supersedes the thin C8 player task). This pack is the researched plan for
> all of it — **one task at a time, each buildable + verifiable in one go**, same discipline
> as the D packs.
>
> **Read first:** `CLAUDE.md`, `docs/PHASE_D_OVERVIEW.md` (§2 principles + §2a matrix — they all
> still bind), `docs/programming/README.md` + `grid.yaml` (the grid model),
> `docs/PHASE_E_PANEL_TASKS.md` (R5 extends it, doesn't replace it), `docs/JINGLE_PROMPTS.md` +
> `JINGLE_PROMPTS_2.md` (the jingle conventions R3 extends), `src/writers/conversation.py`
> (the prompts R1 retunes), `src/world/world_tick.py` + `src/formats/news_select.py` (the story
> machinery R4 extends).
>
> **Sequencing vs the server track:** R1–R4 are local code/content work and should land **before
> the C9 soak** (they change what the soak listens to). R5 is the E1 panel's natural build slot
> (the soak week). R6 is human-paced Suno work, parallel to everything.

---

## 0. Decisions locked (operator, 2026-07-19)

1. **Grid shape — flagships stay long.** Breakfast (07:00–09:00) and drive (18:00–20:00) remain
   2-hour branded shows, restructured internally into fast 5–15-minute items (the real-radio
   flagship model — BBC's *Today* is 3h but never sits on one item). **Everything else becomes a
   ≤30-minute named program.**
2. **News engine — day-plan + micro-ticks.** The nightly tick plans same-day multi-beat arcs
   (hour-stamped beats through the coming day) AND a light haiku-tier intra-day micro-tick
   (every 2–4h) advances today's stories. Both gated, both cost-logged.
3. **Admin — major-events-only approval.** The tick stays autonomous; stories it marks **major**
   queue for operator approval before the news desk airs them. Routine stories flow as today.
   The full per-story queue stays deferred (OVERVIEW's standing position).
4. **Music — big batch.** A MEDIA_LIBRARY v3 brief (~40–60 new tracks, energy-tiered) so real
   music blocks and a daily chart show become possible.

## 0a. Research findings this plan is built on

**Repo (as-built) findings:**

- **The missing editorial seam (root cause of topics 5+6):** `Program`
  (`src/world/programming.py`) carries no *brief* — the showrunner/orchestrator prompts never
  learn which show is on air or what it covers. "The Exchange" (economy) and "The Gallery"
  (arts) produce the same generic Settlement Radio talk, and the beat-picker's only steer is
  "one event + a human angle", which drifts to the house register: contemplative wonder.
  Fixing this one seam (R1.0) unlocks per-program content, tone, and energy.
- **The register lives in three places:** the orchestrator's delivery block
  (`conversation.py` `orchestrate`, already asks for "spoken, not written" — necessary but not
  sufficient), the **cast cards** (`docs/canon/90-cast.md` — several cards are written poetic,
  and sample lines steer generations hard), and the **canon SPIRIT/domain prose** (lyrical
  register that the bible cache injects into every call). All three need one coordinated pass
  (R1), or the model keeps averaging back to "radio poetry."
- **Intra-day evolution is half-built:** tick beats already carry `day_offset` + `hour`, and
  `news_select.py` already classifies `breaking/trailed/ongoing` × `new/repeat/evolve` against
  the in-world clock. What's missing: the tick isn't *asked* for same-day multi-beat arcs, and
  nothing advances a story between nightly ticks. R4 is therefore an extension, not a rebuild.
- **Jingles:** ~35 curated assets exist and the per-program convention
  (`assets/themes/<program_id>.mp3`) + format fallback works. New programs need a
  JINGLE_PROMPTS_3 batch; the audit (R3.0) must verify the placement path end-to-end (themes at
  boundaries, C8 sting at `news@:00` pins, sweepers between items) against the *new* grid.
- **Admin:** `PHASE_E_PANEL_TASKS.md` (E1.0–E1.6) already covers dashboard, actions, grid
  editor, catalog editors, cast manager, dials. The operator's new asks NOT covered there:
  queue/history + per-segment retry, playout start/stop, budgets, the post-tick "what happened
  / what's coming" digest, and the major-event gate. R5 adds them as E1.7–E1.11.
- **Canon coverage for new verticals:** strong for daily life, sports, economy, law, travel,
  arts, tech; **thin for medicine/health and style/fashion** (mentioned only in passing).
  The tick's `DOMAINS` tuple has no health/style entry either — a program without a domain
  starves, because no stories are generated for it (the D9.4 lesson that added `sports`).

**Real-radio practice (web research, 2026):**

- Speech stations run a **fixed spine of short fixtures** — BBC R4: *Today* 06–09, fixed
  10:00/12:00/13:00/17:00 fixtures, 30-min news at 18:00, a **15-min drama** and a **30-min
  comedy slot** daily; almost nothing outside the flagships exceeds 45 min. Predictable fixture
  times are what make a station feel "programmed."
- **Hour clocks rule everything**; talk links on music radio run 30s–3min; the "newshole" is
  typically :00/:01–:06. Energy comes from *variation* — pace, item length, and register changes
  inside the hour — monotony (one register, one length) is the thing that reads as "boring."
- **News stories are updated, not re-read:** a real newsroom upgrades the same story across the
  day (reader → update with new facts → wrap/package by drive), always marking the delta
  ("UPDATE", "as we reported this morning"). Future events get countdown coverage that
  intensifies as the date nears. This maps exactly onto the built `evolve`/`trailed` machinery.

*(Sources:
[R4 schedule structure](https://www.liquisearch.com/bbc_radio_4/programmes_and_schedules/daily_schedule),
[broadcast clock](https://www.radio.co/blog/broadcast-clock-explained),
[format clock consistency](https://radioiloveit.com/radio-programming-radio-formats/radio-programming-success-format-clock-consistency-and-balance/),
[story evolution stages](https://journalism.university/broadcast-and-online-journalism/evolution-television-news-stages/),
[news updates](https://mediahelpingmedia.org/advanced/old-news-is-no-news-updates-are-essential),
[engaging presentation](https://journalism.university/broadcast-and-online-journalism/effective-radio-presentation-dos-donts/).)*

---

## 1. The tracker

Work the packs roughly in order; R1 is foundational (R2's new programs are only worth airing
once briefs steer them). R3.1/R6.0 are human Suno batches — start them early, they gate nothing.

| Pack | What | Topics served | Depends on | Built? |
|---|---|---|---|---|
| R1 | Editorial briefs + register overhaul | 5, 6 (foundation for 1) | — | ✅ |
| R2 | The 24-hour grid rebuild | 1, 6 | R1.0 (brief field) | ✅ |
| R3 | Jingle validation + batch 3 | 2 | R2.0 (the new program list) | ☐ |
| R4 | The living day (news arcs + micro-ticks) | 4 | — (parallel to R1/R2) | ☐ |
| R5 | Panel extensions E1.7–E1.11 | 3 | E1.0–E1.6 as planned | ☐ |
| R6 | Music expansion + the chart show | 1, 6 | R2.0 (slot exists) | ☐ |
| R7 | The public web player, made a real station front | (operator add-on) | R2.2 (the new grid), C7/C8 (a stream to play) | ☐ |

---

## R1 — Editorial briefs + the register overhaul (do first)

*The fix for "academic professors discussing the light and the distance." One seam change, one
prompt pass, one canon pass — coordinated, because the register is set in three places at once.*

### R1.0 — The `brief` field: programs get an editorial identity
**Goal:** every program can carry a short editorial brief that reaches the writers' room.
**Do:**
- Add optional fields to `Program` + the grid parser (`src/world/programming.py`):
  `brief: str` (2–4 sentences: what this show covers, what a good item looks like, what it
  never does) and `energy: str` (`calm | steady | bright` — the delivery pace hint).
- Thread them into the prompts: `compose_segment` passes the active program to `showrunner` and
  `orchestrate`; both prompts gain an "ON THIS SHOW" block (program name + brief + energy) in
  the **per-call** system section (never the cached core, so the bible cache still hits).
- The showrunner's fresh-pick task gains: *"pick a beat that belongs on THIS show"* — the brief,
  not the whole world, scopes the topic.
- Absent `brief` = today's behaviour exactly (back-compat; the `default` program has none).
**Done when:** a unit test shows two different programs' briefs landing in their prompts; a
`make continuity-demo`-style run on two programs yields visibly on-brief beats; ruff+pytest green.

### R1.1 — Write the briefs (all current programs)
**Goal:** every program in `grid.yaml` gets its brief + energy, written for *interest*, not theme.
**Do:** for each program write the brief around **concrete stakes** — prices, disputes, matches,
verdicts, arrivals, weather, someone's bad day — with an explicit "never" line (e.g. *"never
muse about distance or light; the listener lives here, don't explain their world to them"*).
News/flagship briefs state the item cadence ("move every few minutes"). Keep briefs in
`grid.yaml` beside each program (git-diffable; the E1.2 editor will round-trip them).
**Done when:** every non-default program has `brief` + `energy`; generated sample segments for
3 contrasting shows (economy / sport / night) are recognisably different shows.

### R1.2 — The register pass: normal people, not a lecture
**Goal:** talk sounds like real people at work; news stays formal.
**Do:**
- `conversation.py` orchestrator: strengthen the delivery block — everyday vocabulary,
  short declaratives, opinions and mild complaints allowed, humour from the card's `Humour:`
  line, **ban the house-poetry register** (an explicit "avoid abstractions like 'the light
  between worlds', 'what the dark says back' outside the deep-night shows" line, driven by the
  program's `energy` so Nightfall/Deep Hours keep their soul).
- Showrunner: the "human angle" instruction becomes "a concrete, everyday stake — money, time,
  weather, a queue, a rivalry, a plan gone wrong — not a meditation."
- `formats/news.py`: verify the anchor register stays formal (it should — confirm, don't touch
  unless drifted).
**Done when:** a 5-segment sample run reads noticeably plainer (spot-check against a written
checklist: contractions, sentence length, zero banned abstractions on daytime shows); the
existing acceptance properties still pass.

### R1.3 — The cast-card pass
**Goal:** the cards themselves stop steering toward the academy.
**Do:** one editing pass over `docs/canon/90-cast.md` — keep every persona distinct, but ground
the **sample lines** (they steer hardest) in everyday speech; Mira loses the remaining lecture
cadence on daytime shifts; Joss/Kael/Wren gain a "talks about ordinary things" beat; the
Archivist/Vell keep their registers (they ARE the night). Re-seed (`make seed-canon` — safe).
**Done when:** re-seeded; a generated Common Ground + Gallery segment sounds like people, not
a seminar; card diffs reviewed by the operator.

### R1.4 — SPIRIT/canon register note + acceptance
**Goal:** the bible stops re-teaching the poetry register to every call; the change is guarded.
**Do:** add a short "HOW THE STATION TALKS" section to `docs/canon/SPIRIT.md` (plain speech is
the default; lyricism is the night's dialect, not the station's); add an **eighth acceptance
property** (`plain_register`): generate N daytime talk segments, assert a banned-phrase list is
absent and a contraction floor is met (crude but catches regressions). Wire into `make acceptance`.
**Done when:** `make acceptance` runs 8 properties green; DEVLOG entry appended.

---

## R2 — The 24-hour grid rebuild

*From eight 1–2h blocks to a real speech-station day: two long flagships + ~20 short fixtures.*

### R2.0 — Design the new week (paper task, the keystone)
**Goal:** a written v2 grid design the operator signs off before any YAML moves.
**Do:** draft `docs/programming/GRID_V2.md` with the full 7-day tiling under these rules:
- **Flagships:** `morning_currents` 07–09 and `evening_currents` 18–20 stay 2h, but their clocks
  become fast item sequences (see R2.2).
- **Everything else ≤30 min.** Current 1–2h verticals become 30-min editions (The Assembly,
  The Exchange, …), which frees slots for **new fixtures**, e.g. (names in-world, final at
  operator review): **The Ward** (health & medicine), **The Fit** (style/fashion/what people
  wear across the worlds), **The Table** (food), **Conditions** (the D14 space-weather slot,
  finally scheduled), **The Count** (daily chart show, R6), **The Ledger** (5–10-min markets
  brief), a **15-min serialized story slot** (the R4 world's long arcs, told nightly — the
  radio-drama fixture real stations run), plus the existing Circuit/Mailbag/New Signal.
- **Fixture discipline:** same slot every day for the dailies (the R4 recurrence hooks depend
  on it); hourly news pins stay `news@:00` everywhere; short bulletins hourly, long bulletins
  inside flagships + a 30-min `settlement_desk` at midday.
- **Energy curve:** bright 07–09, steady with bright spikes through the day, chart + sport
  late-afternoon, warm evening, night unchanged (the night is already good).
- For every program: hosts (rotate pairs so nobody carries 6h/day), brief (R1.1 style),
  `energy`, clock, `break_every`, `guest_chance`, theme status (existing / needs R3.1 spec),
  and **canon support** (which cornerstone file feeds it; gaps go to R2.1's list).
**Done when:** GRID_V2.md tiles all 168 hours with no gaps, every program has all fields, the
operator has reviewed and signed off the doc.

### R2.1 — Canon + domain support for the new verticals
**Goal:** every new program has world to draw on, and the tick generates stories for it.
**Do:**
- New/extended cornerstone files for the thin domains: `docs/canon/54-health.md` (medicine,
  clinics, the physician-correspondence network, what illness means across the lag) and a
  style/dress section (extend `50-daily-life.md` or a small `56-style.md`); extend food if the
  Table needs more than 50-daily-life §Food.
- Extend the tick's `DOMAINS` (world_tick.py) with `health` (and `style` if a file lands) so
  stories actually happen there; add matching tags to relevant cast cards (the D9.4 affinity).
- `make seed-canon`; re-embed.
**Done when:** seeded + embedded; a test tick run (dev DB) produces at least one story in a new
domain across a few ticks (the quiet-domain weighting will pull them in); AUDIT.md updated.

### R2.2 — Implement the grid + flagship clocks
**Goal:** GRID_V2 becomes the live `grid.yaml`.
**Do:**
- Rewrite `grid.yaml` from the signed-off design (30-min slots are already legal — the loader
  takes `HH:MM`). Flagship clocks become fast sequences, e.g.
  `[news@:00, talk, talk, news@:30, talk, talk]` with shorter talk targets.
- Add a per-program `talk_length_sec` (or reuse segment `length_target` plumbing) so a flagship
  item runs ~3–5 min while a 30-min specialist runs ~6–8 — **length stays a parameter** (the
  Segment seam rule).
- Check the scheduler's clock-cursor + pin logic against 30-min programs (a program whose whole
  life is <1h must still hit its `news@:00`/`@:30` pins correctly — add a regression test).
- Retire/bench replaced programs (keep definitions, D12.4 style); update briefs per R1.1 for
  every new program.
**Done when:** grid loads (the programming loader validates), tiling test green, `make console`
shows the new day, a 24h simulated top-up (the D11 harness) runs with no gaps and sane
durations; pins fire inside 30-min shows.

### R2.3 — Pace + interstitials for the short grid
**Goal:** more programs/hour must *sound* like motion, not churn.
**Do:** program-boundary behaviour review at the new density — themes open every show (R3.0
verifies clips), A4 sweepers between items inside flagships (energy-matched via program
`energy`), sign-on/sign-off (D12.4) stays but tightens for 30-min shows (a one-line open, not a
ceremony — dial or prompt tweak), handover stings only at real handovers.
**Done when:** listening to a rendered flagship hour + two short shows back-to-back: every join
has the right clip, no double-themes, opens are one breath long; `talk_flow` acceptance still green.

### R2.4 — Docs + tracker
**Do:** update `docs/programming/README.md` (new fields, flagship model), `ADMIN_MANUAL.md`
grid section (+ `→ Phase E panel` tags for new fields so E1.2 picks them up), DEVLOG, this
tracker.
**Done when:** docs match as-built; `make acceptance` green.

---

## R3 — Jingles: validate the set, spec batch 3

### R3.0 — The placement audit (validate what exists)
**Goal:** proof, not assumption, that every clip fires where and when it should.
**Do:** build a small audit script (`python -m src.production.audit` or a pytest marked slow):
walk a simulated 48h schedule and assert — every program boundary got its theme (bespoke else
format fallback, per `placement.program_theme_segment`), every `news@` pin got C8, handovers got
B6, breaks got the D18 pair, no theme repeats back-to-back, and **report the mapping table**
(program → clip actually resolved) so the operator can eyeball reuse choices (`the_circuit` →
c12 games, `the_mailbag` → c11 letters — confirm the code maps these, not just the doc). Fix
any misses it finds (e.g. programs silently falling back that were meant to have bespoke clips).
**Done when:** the audit runs green on the *current* grid and is re-run green after R2.2; its
mapping table is committed as part of the DEVLOG entry.

### R3.1 — JINGLE_PROMPTS_3.md (the batch-3 brief) *(human Suno work follows)*
**Goal:** every new R2 program opens on its own theme; new utility stings exist.
**Do:** write the batch-3 doc in the JINGLE_PROMPTS_2 format (filename = program id, motif +
palette + tier rules inherited): themes for every new program (Ward/Fit/Table/Count/Ledger/
serial-drama slot/…), plus utility: a **chart-countdown sting set** (position ramp for The
Count), a **quiz/game sting** if R2 adds one, and re-check the three A4 sweepers cover the new
energy range. List reuse (Conditions → existing `d14_conditions.mp3` — no new clip).
**Done when:** the doc is complete with exact paths + styles; the operator generates and drops
files; `media` resolves each (R3.0 audit re-run shows zero format-fallbacks for programs meant
to have bespoke themes).

---

## R4 — The living day: same-day arcs + micro-ticks

### R4.0 — Day-planning in the nightly tick
**Goal:** the tick writes stories whose beats *unfold across the coming day*.
**Do:** extend the proposal/advancement prompts + schema (`world_tick.py`): each story may carry
a **same-day arc** — 2–4 beats at distinct hours of day 0/1 (missing at 07:00 → located 13:00 →
resolved 19:00), with the later beats marked `planned` (a new beat flag/`source` value) so the
news desk can *report them only once their hour passes* (they're the plan, not the record).
Dials: `world_tick_dayarc_stories_max`, `world_tick_dayarc_beats_max`. Beats stay gated as today.
**Done when:** a dev tick produces at least one multi-beat same-day story; `news_select` (frozen
clock test) shows the same story tagged `breaking→evolve→evolve` across three simulated hours;
beats after "now" never air early.

### R4.1 — The intra-day micro-tick
**Goal:** the day can react and surprise between nightly ticks.
**Do:** `run_micro_tick()` in `world_tick.py` (or a sibling module) — haiku-tier, every 2–4h via
the C5 cron (`make micro-tick`): reads today's active stories, may (a) advance ONE story a small
beat (a detail, a reaction quote, a complication), (b) confirm/adjust the next `planned` beat,
or (c) do nothing (a "quiet run" is a valid outcome — dial the advance probability). Same
safety+continuity gates, same usage logging; hard-capped tokens; never touches the schedule.
Dials: `micro_tick_*`. **Batch API not used here** (latency matters, volume is tiny).
**Done when:** `make micro-tick` runs in seconds on a dev DB, logs usage, and a bulletin
generated after it reports the new beat as an update; two consecutive quiet runs change nothing.

### R4.2 — News desk: updates that sound like updates, countdowns that count
**Goal:** the on-air language matches the machinery — evolving stories and approaching events.
**Do (in `formats/news.py` / `news_select.py`):**
- `evolve` items: the brief explicitly gets "what we said last time" (prior coverage angle) and
  must frame the delta ("as we reported this morning… the crew has now been reached").
- `trailed` items: multi-day countdown framing — the relative-phrase renderer already gives
  "in three days"; ensure a future event can recur across days without going cold
  (`news_repeat_max_stale_hours` interacts — add a trailed-specific staleness rule) and that
  proximity raises its rank (closer = more coverage, the Olympics-in-a-week pattern).
- Flagship vs short bulletins: bulletin length/story count driven per-program (the R2 clocks) —
  hourly shorts run 2–3 items, flagship + midday desks run the full mix + day-summary at drive
  ("the day so far" wrap, a distinct brief flavour for the 18:00 bulletin).
**Done when:** a simulated day (frozen clocks at 07/10/13/16/18) renders: same story upgraded
with delta language, a future event counted down across two simulated days, drive wrap
summarises; news tests green.

### R4.3 — The verticals read their domain
**Goal:** The Exchange talks about *this week's* trade story, not trade in general.
**Do:** the showrunner's dynamic context, when a program brief exists (R1.0), prefers story-log
items matching the program's domains (map program → domain tags in the grid; filter/boost in
`context.assemble` or the showrunner block). Sport talks the circuit stories, the Ward talks the
health stories, general shows keep the full mix.
**Done when:** with a seeded multi-domain story log, sampled segments for two verticals each
glance off a story from their own domain (log-assertable via the chosen beat's story id, or
spot-checked across N runs).

### R4.4 — Acceptance: the living-day property
**Do:** a ninth acceptance property (`living_day`): run tick → simulate bulletins across a
compressed day → assert at least one story evolves with correct framing and no `planned` beat
airs early. Wire the micro-tick into the C5 cron docs + ADMIN_MANUAL (+ panel tag).
**Done when:** `make acceptance` green (9 properties); DEVLOG + manual updated.

---

## R5 — Admin panel: extend E1 (build during the soak week, as planned)

*E1.0–E1.6 stand as written (`docs/PHASE_E_PANEL_TASKS.md`) — dashboard, actions, grid editor,
catalog editors, cast manager, dials, deploy. These are the operator's additional asks, kept to
the same principles (files stay truth; loopback-only; destructive keeps friction).*

### R5.0 (=E1.7) — Queue, history & retry
**Goal:** see the air queue and history; regenerate what's wrong.
**Do:** a schedule screen over `schedule.json` + segments: aired history (with scripts +
audio links), on-air now, the upcoming queue with runway; per-upcoming-segment **"regenerate"**
(drop + re-top-up that slot via the existing scheduler path — never edit a rendered file) and
**"skip"**; playout **start/stop/restart** buttons wrapping the existing service commands
(systemd/liquidsoap), with the same concurrency lock as E1.1.
**Done when:** a regenerated segment re-renders and re-enters the queue; history paginates;
stop/start round-trips and the never-dead fallback behaviour is documented on the page.

### R5.1 (=E1.8) — Budgets
**Goal:** cost visibility with a line to not cross.
**Do:** a budgets screen on the usage telemetry (the costprobe/logged `usage` fields): spend by
job (tick, micro-tick, news, talk, TTS minutes, embeddings) by day/week; dials
`budget_daily_usd` / `budget_alert_pct`; the dashboard shows a budget bar; breaching the alert
threshold logs loudly + shows red (no auto-shutoff in R5 — visibility first, the kill-switch is
an operator call).
**Done when:** the rollup matches costprobe's numbers on a seeded day; the alert state renders
at a forced low threshold.

### R5.2 (=E1.9) — The world screen (post-tick digest)
**Goal:** "what happened last night, and how today should unfold" — at a glance.
**Do:** after each tick/micro-tick, generate + store a short **tick digest** (haiku-tier, from
the tick's own result: new stories, advanced arcs, planned same-day beats, new figures/quotes,
gate drops). The world screen shows: the latest digest, arcs in flight (story → stage → next
planned beat), today's expected beat timeline, and tick/micro-tick run buttons (E1.1 machinery).
**Done when:** running a tick from the panel produces a digest the operator can read in 30s;
the timeline matches the story log.

### R5.3 (=E1.10) — The major-event gate
**Goal:** world-changing stories wait for the operator; everything else flows.
**Do:** the tick's proposal schema gains a `major: bool` (prompt: wars, deaths of named canon
figures, discoveries that alter the premise, anything the bible would need to absorb); major
stories land with `status=pending` — `news_select` + the showrunner context **exclude pending
stories**; a panel queue shows them with approve (→ active) / reject (→ archived, embeddings
removed); a dial caps how long a pending major waits before the tick stops proposing similar
(so the log doesn't jam). §2a matrix gains the status column note; `seed`/`reset` semantics
unchanged.
**Done when:** a forced-major dev story never airs while pending, airs after approve, vanishes
after reject; non-major flow is byte-identical to today with the queue empty.

### R5.4 (=E1.11) — DJ pages
**Goal:** the cast manager (E1.4) grows the "who is this host *now*" view.
**Do:** per-DJ page joining the card (E1.4's editor) with the *lived* state: recent journal
entries (D13 `host_journal`), world-memory affinities (D9.4 tags), shows they're scheduled on
(grid usage), recent segments. Read-only beside the card editor.
**Done when:** each host's page renders card + journal + schedule accurately; the E1.6 test
pattern covers the new routes; ADMIN_MANUAL tags updated.

---

## R6 — Music expansion + The Count (the chart show)

### R6.0 — MEDIA_LIBRARY_V3 brief *(human Suno work follows)*
**Goal:** the catalogue can carry real music blocks and a moving chart.
**Do:** write the v3 brief in the MEDIA_LIBRARY house style: **40–60 tracks**, energy-tiered
(heavier on bright/day tier — the current set skews contemplative), reusing existing artists for
**new singles** (a chart needs new releases from known names) plus a handful of new acts;
every track gets the usual lore row for `config/tracks.yaml`. Tag chart candidates.
**Done when:** the brief is written; the operator generates + drops files; `make seed-tracks`
loads them; playable count reported.

### R6.1 — The chart machinery + The Count
**Goal:** a daily "top hits" show whose chart actually moves.
**Do:** a small `chart` state (kv or table, §2a: runtime, survives seed-canon, cleared by
reset-world): N ranked track ids; a daily chart update step (in the nightly tick job, cheap +
deterministic-ish: weighted shuffle biased by `featured`, recency of entry, and a random walk —
optionally one haiku call to pick a "story" of the day's chart: climber, new entry, holdout).
A `chart` clock step / program (`The Count`, R2 slot): DJ counts down the top N with the R3
countdown stings, intro lines drawn from each track's `story_blurb` + chart movement ("up three
places"). Airplay history (D5) keeps chart plays from looping outside the show.
**Done when:** two consecutive dev days produce different, plausibly-moving charts; a rendered
Count episode counts down with correct movement language; tests on the chart-update logic.

### R6.2 — Docs + seed
**Do:** ADMIN_MANUAL music section (+ panel tag: chart visible on the world screen or tracks
page), README, DEVLOG, tracker flip.

---

## R7 — The public web player: a real station front

*Today `/web` is still the A2 coming-soon page; C8 planned only a thin "audio tag + disclosure"
player. R7 **absorbs and supersedes C8**: the site becomes what a listener expects from a real
station — listen live, see what's on and what's next, browse the day's grid, meet the DJs.
Public + read-only stays a hard rule; `/web` keeps its pragmatic standards (not the backend's).*

**The canon-derived design brief (read `docs/canon/00-station.md`, `SPIRIT.md`,
`JINGLE_PROMPTS.md` §0 — the visual identity is already written, just not as pixels):**

- **"A lit window seen across the dark."** The existing A2 palette is right and stays: deep
  night blue (`--color-night #081b45`), warm amber (`--color-amber #f2c04d`), warm off-white.
  The page is mostly dark, vast, and calm, with ONE warm glowing focus — the on-air card. Subtle
  starfield/drift, never busy.
- **Warm analog retro-futurism** (the jingle brand, visualised): soft-glow dials, a gentle VU /
  signal-strength animation while playing, rounded corners, faint tape-grain texture — cozy, not
  neon cyberpunk, not sterile dashboard.
- **DJs are voices, not faces** (canon fact 8: listeners know only their voices). No portraits,
  ever: each host gets an abstract **waveform/signal mark** in their accent tone — a strong,
  canon-true identity device that also sidesteps AI-face weirdness.
- **The station's humane props** are the decoration vocabulary: the photograph wall
  (hand-labelled captions), the observatory dome, the relay thread — use as small touches
  (e.g. the schedule rail drawn as a relay thread with node dots per program).
- **The disclosure line stays visible on every page** (hard rule) — styled as the station's
  honest voice, not buried in a footer.

### R7.0 — Public data: the feeds the player needs
**Goal:** the site can render grid/now/next/DJs from public-safe, read-only JSON.
**Do (station backend, allow-list discipline of `src/nowplaying.py`):**
- Extend the now-playing feed: it already carries `now`/`next` with program, hosts, format
  label, track lore — add the program's public one-liner (from the R1 `brief`, first sentence
  or a dedicated `tagline` field in `grid.yaml`) and the program's scheduled end time (so the
  player can show "until :30").
- New `schedule` public feed (`segments/schedule-public.json`, or one combined `station.json`):
  today's resolved grid + the week's tiling — per program: id, name, tagline, hosts (display
  names), time ranges. Built from `program_for`/the grid loader, written beside the now-playing
  feed on the same cadence (cheap — the grid changes rarely, the "now" pointer hourly).
- New `djs` public feed: the public-safe cast slice — name, role line, a short public bio
  (add an explicit `Public bio:` bullet to the `90-cast.md` card format so the *operator*
  chooses the public text; never publish the full card/prompt), shows they host (derived from
  the grid), field-vs-station. Tech staff excluded.
- Serving: the VPS publishes these JSONs at a public read-only URL next to the stream (C7's
  nginx/icecast box); `/web` fetches client-side with polling. Document CORS + cache headers.
**Done when:** all feeds validate against a checked-in TS type (`web/src/lib/types.ts` shared
by the fetchers); nothing non-allow-listed appears (test: feed builder unit test asserting the
key set); feeds regenerate on the top-up cadence.

### R7.1 — The player page (the "lit window")
**Goal:** settlementradio.com IS the station: press play, see what you're hearing.
**Do (in `/web`):**
- The hero: the **on-air card** — glowing amber-on-night; program name + tagline, host marks +
  names, format label ("The Settlement News"), and for music the track lore (title/artist/era/
  one-line story — the D7 lore finally *visible*); a large play/stop control on the live stream
  (`<audio>`, HLS/icecast URL from env), volume, a "LIVE · settlement time HH:MM" line.
- The signal animation: a small VU/waveform pulse while playing (CSS/canvas, no heavy deps);
  still and dim when paused — the window lit vs unlit.
- **Up next** rail: the next 2–3 entries from the feed (program, time, hosts).
- The disclosure line, styled per the brief; the support/follow links (MARKETING M1);
  graceful degradation — feed unreachable → the player still plays with a static
  "Settlement Radio — live" card (never a broken page).
**Done when:** the page plays the live stream on desktop + phone, updates now/next within a
poll cycle of a program change, shows track lore during a music slot, and Lighthouse
accessibility ≥ 90 (it's a radio for everyone).

### R7.2 — The grid page ("Programmes")
**Goal:** a listener can see the station's whole day — the thing that makes it read as a real
station and not a generated stream.
**Do:** a `/schedule` route from the R7.0 schedule feed: **today view** (a vertical rail of the
day's programs — time, name, tagline, hosts — with "on air now" highlighted and auto-scrolled
into view) + a **week view** (the 7-day tiling, the two rotating specialist windows visible so
the "Tuesday economy hour" rhythm is legible). Each program row expands to its tagline + hosts
+ next airing. Times shown in **settlement time = the listener's local time** (they're equal by
construction — say so with a small wink: "settlement time (yours)").
**Done when:** the page matches `make console`'s answer for any spot-checked hour; now-highlight
moves without reload; renders cleanly on a phone.

### R7.3 — The voices page ("The DJs")
**Goal:** the cast becomes real to listeners — by voice, per canon.
**Do:** a `/voices` route from the `djs` feed: one card per host — the waveform mark, name,
role line, public bio, their shows (with next-on-air time), a field-correspondent badge for
Sera/Orin/Zhe ("reports across the relay — dispatches arrive with the lag"). Optional stretch
(behind a flag): a 5–10s voice sample clip per host (operator-curated files in `/web/public`,
NOT auto-published segments).
**Done when:** every grid-scheduled host renders with correct shows; no non-public card text
appears anywhere in the payload or page source; the page reads as canon (voices, not faces).

### R7.4 — Ship it: nav, polish, deploy
**Goal:** one coherent site replacing coming-soon, live on Vercel.
**Do:** shared layout + nav (Listen / Programmes / Voices), the signup form kept (footer or
"letters" box), favicon/OG images in the brand look, Plausible on the player (M1), Vercel env
vars for the stream + feeds URLs, `web/README` updated; keep a `COMING_SOON` env flag so the
old page can be restored instantly if the stream isn't public yet.
**Done when:** deployed on the production domain behind the flag; all three pages live against
the real VPS feeds; disclosure visible on every route; DEVLOG + MARKETING M1 checklist updated.

---

## 2. Suggested build order (one line)

**R1.0 → R1.1–R1.4 → R2.0 (sign-off) → R2.1 → R2.2–R2.4 → R3.0 → R3.1 (human) →
R4.0–R4.4 → R6.0 (human, parallel from R2.0) → R6.1–R6.2 → R5 + R7 during the C9 soak week.**

Everything before the soak changes what the soak hears — soak after R1–R4 land, with R3/R6
audio arriving as the human batches complete. R7.0 (the feeds) can land with R2.2; the site
itself (R7.1–R7.4) needs the C7 stream and pairs naturally with the soak week, going public
at the M1 soft launch.

# PHASE_D_WORLD_ENGINE_TASKS.md — D3: The World Engine (the keystone)

> Sub-pack **D3** of Phase D (see `docs/PHASE_D_OVERVIEW.md`) — the keystone: it makes the +600y world
> *move on its own*. Work in order, one task at a time: implement → show + how to verify → stop for
> review. Respect `CLAUDE.md` and the Phase D standing principles (OVERVIEW §2), especially **"the
> world-tick is generative — Layer 3 machinery writing Layer 1 state"** and the **cost levers**
> (Batch API + prompt caching) which D3's volume re-justifies. Written against the **as-built code**:
> the `events` table + `store.insert_events`/`events_in_range`/`events_by_status`; `events.status_of`/
> `progressed`/`relative_phrase` (the upcoming/today/past framing); `clock.to_inworld`; the C0 gates
> (`safety.safety_check`, `conversation.continuity_check` → `ContinuityResult`); and `embeddings.
> retrieve` (D2) for consistency recall.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §2–§3 (D3 brief); `docs/ROADMAP.md` (Phase D
> "world-simulation engine" bullet — the canonical arc model); `docs/ARCHITECTURE.md` (Layer 1 state;
> "the tick is generative … uses Layer 3's machinery to write into this layer's state"); `src/world/
> events.py` + `src/world/clock.py`; `src/world/store.py` (events table); the C0 gate seams; the
> **`claude-api` skill** (Batch API for the nightly run, model routing, caching).
>
> **Depends on:** **D1** (a real bible to stay consistent with). **D2 strongly recommended** — semantic
> recall is how the tick checks new happenings against canon and prior beats; the tick can write events
> without it, but consistency is weaker. If building D3 before D2 lands, gate the recall step behind a
> capability check so it degrades to structured (date/tag) recall.

**What D3 delivers (ROADMAP, verbatim intent).** A nightly **world tick** that:
1. generates plausible new happenings consistent with the bible — large (a new festival, a political
   shift, an economic swing) and small (a cruise liner goes missing, a moon-president's son marries);
2. models each as a **story with an arc**, not a one-shot fact: *rumoured → upcoming → happening →
   developing → past*, each beat with an in-world datetime so the B2 clock frames it
   future/now/past automatically;
3. **advances** running stories over subsequent ticks (new beats, consequences, resolutions) so the
   world has real day-to-day continuity; writes it all to the story/event log.

**Key design point — two status concepts, kept distinct.** `events.status_of()` already computes
*temporal* status (`upcoming`/`today`/`past`) from a datetime vs the clock — that stays and is reused.
The **arc stage** (`rumoured`/`upcoming`/`happening`/`developing`/`past`) is a *narrative* property the
tick authors and advances. Don't conflate them: a story can be temporally `past` but narratively still
`developing` (consequences unfolding). Model arc stage explicitly; derive temporal framing from the
datetime as today.

**Definition of done for D3:** running the tick generates new bible-consistent stories with dated,
arced beats in the store; a second tick advances at least some running stories (new beats / stage
transitions) without contradicting canon or prior beats; flagged output is regenerated or dropped
(never written); the tick is a callable job the C5 cron will run (and a `make world-tick` CLI); it's
batched + cached for cost; `ruff` + `pytest` green. **The news desk that *reports* this is D4** — D3
only makes the world move and writes the log.

---

## D3.0 — Story-log schema (stories + beats + arc stage) in `store.py`
**Goal:** a place to record stories that progress, on top of (not replacing) the `events` table.
**Do:**
- Design the story log in `store.py` (the only SQL). Recommended shape — a `stories` table (id,
  title, summary, arc_stage, tags, created_tick/created_at, last_advanced_tick) plus the existing
  `events` rows linked to a story (add `story_id` + an optional `beat_kind` to `events`, so each beat
  *is* an event with an in-world datetime the clock already frames — reuse, don't duplicate, the
  events machinery). Decide stories-table vs beats-table-vs-events with that reuse in mind and write
  the choice down.
- Define the **arc stages** as a named module constant (intrinsic domain data, not config):
  `rumoured → upcoming → happening → developing → past`, with the legal transitions.
- Add row dataclasses (`Story`, and an extended `Event`/`Beat`) + reads/writes:
  `insert_story`/`insert_beats`, `advance_story` (update stage/last_advanced), `active_stories`
  (stories not yet resolved), `story_beats(story_id)`, and the joins the news desk (D4) will need.
- **The story log is DYNAMIC, tick-owned state — a canon refresh must NOT wipe it (load-bearing).**
  The `stories`/beats tables and the tick-generated `events` are written by the nightly tick, NOT by the
  human's folder, so they must **survive a `make seed-canon` refresh** (D1.2 split the seed into
  `seed-canon` vs `reset-world` exactly for this; see the OVERVIEW §2a ownership matrix). Concretely:
  - `counts` includes the new tables, but the **scoped** `clear_world` (D1.2) clears them **only** on
    `reset-world`, **never** on `seed-canon`. A bible edit + `seed-canon` must leave the living world
    standing. These tables are **backed up** (§2a — irreplaceable).
  - Honour D1.2's seed-vs-generated `source` split: the tick writes `source="tick"`; `seed-canon` replaces
    only `source="seed"`. Reuse the same convention D1.2 picked — do not invent a second one.
  - Embed new beats into the **D2 polymorphic `embeddings` table** (`store.insert_embeddings(conn,
    "event"/"story", rows)`, `source="tick"`) if D2 is built — reuse, don't add a `*_embeddings` table.
  - **Schema lands via idempotent migration / backfill, not truncate-reseed** (OVERVIEW §2), since the
    story log holds irreplaceable state once the tick runs.
  - Keep a **full reset** path that *does* clear the story log (dev / a deliberate world wipe) — the
    point is that the *default canon-edit workflow* doesn't trigger it.
- Idempotency: schema init creates the new tables idempotently; fold them into `counts`. If D2 embeds
  events, embed new beats on write too (reuse the D2 helper).
**Done when:** schema init creates the story log idempotently; a story + its beats can be inserted and
read back; arc stages + transitions are a documented constant; events remain the dated, clock-framed
unit; **a canon refresh leaves all `stories`/beats/tick-events intact, while a full reset clears them**
(verify both paths). Unit-tested.
**Note — history persists; it is never pruned like audio.** The story log is the world's *memory*: a
resolved (`past`) story stops advancing but **stays in the store forever** (it's the irreplaceable
asset C5 backs up; the C2.5 `prune` only ever GCs regenerable *audio* under `segments/`, never DB world
state). The news desk, DJ memory (D9), and the tick all read past stories as history — so do not delete
"used" events. Text rows are tiny (nothing like audio cost), so unbounded growth is not a storage
worry; relevance is kept in check by **recency windows** (the tick/DJ memory read *near* now) and
**semantic recall** (D2 surfaces only the *relevant* old stories). If the world ever gets genuinely
deep, the answer is a far-future **history-summarization / archival** layer ("remember the *gist* of old
eras, not every beat") — still *keeping* history, just compressed, **never deletion**. Out of scope here;
noted so the schema isn't designed as if old events are disposable.

## D3.1 — The generative tick: propose new happenings (gated, bible-consistent)
**Goal:** one tick run invents plausible new stories consistent with the bible and writes them as
arced, dated beats — never airing/writing unsafe or contradictory content.
**Do:**
- Add `src/world/world_tick.py` (Layer 3 machinery): `run_tick(now=None) -> TickResult`. It:
  - assembles context (the bible via `context`/RAG recall, the current active stories, the clock) and
    asks Claude (the `sonnet` writing brain; `opus` only for gnarly world calls) to propose a bounded
    number of new happenings — a mix of large and small (config dials:
    `world_tick_new_stories_min/max`, a large/small ratio).
  - For each proposed story, generate its **initial arc** — a stage + one or more beats with in-world
    datetimes (anchored off `clock.to_inworld(now)`), so the clock frames them future/now/past.
  - **Gate every proposal:** `safety.safety_check` on the text; a **continuity check against canon +
    existing stories** (reuse `conversation.continuity_check`'s pattern, or a world-specific editor
    pass) so a new happening can't contradict the bible or a running story. On a flag: regenerate
    once, then drop that story (log loudly) — **never write flagged/contradictory content** (the C0
    discipline, applied to world state).
  - Use **RAG recall (D2)** to pull the canon + prior beats most relevant to each proposal, so the
    consistency check and the generation are grounded by meaning, not just recency.
  - Write accepted stories + beats via the D3.0 store writes; embed new beats on write into the **D2
    polymorphic `embeddings` table** via `store.insert_embeddings(conn, "event"/"story", rows)` (with
    `source="tick"`), if D2 is built — so the new world is semantically recall-able like canon.
- **Build the BATCH path in the `llm` seam FIRST (audit fix — Batch must NOT leak into `world_tick`).**
  The overview makes Batch mandatory for the tick, but the seam today is single-call streaming only
  (`llm.generate`). So **extend `providers/llm` with a batch abstraction** — e.g. `llm.generate_batch(
  requests) -> results` (submit → poll → collect; Batch is async, which is fine for a nightly job) — the
  **only** place the vendor Batch SDK is imported. `world_tick` calls `llm.generate_batch(...)`; it never
  touches the vendor batch API directly (seam rule, like `generate`). Consult the `claude-api` skill for
  the current Batch + caching APIs and model IDs.
- **Cost levers (mandatory here — this is the new high-volume job):** run the proposal/continuity calls
  through that **Batch path (50% off)** where latency allows (the tick is nightly, not live), and
  **cache the stable bible/cards** so each call pays full price only for the variable part.
- **Cost telemetry (OVERVIEW §2):** the run logs its usage — proposal/continuity calls, tokens,
  regenerations/drops, embeddings written — as structured fields for the D6 console rollup.
**Done when:** the **batch path exists behind `providers/llm`** and `world_tick` uses it (no vendor batch
SDK imported in `world_tick`); `run_tick()` writes N new bible-consistent stories with dated, arced
beats; a deliberately contradictory proposal is regenerated or dropped (nothing contradictory lands in
the store); the run logs each proposal's gate outcome **+ a usage summary**; calls are batched + cached.
**Note — music & culture are valid happenings, but the tick never makes a playable song.** The culture
domain (D3.3) includes **music**: a new album, an award, a tour, a scene — the tick can generate these as
*events/stories*, and the news/DJs then reference and *promote* them, exactly like real radio ("the
festival's headline act just dropped a record"). **Scope line (audit fix):** before **D10** is built, the
tick writes **plain story entities only — no figure/quote rows**; *once D10 exists*, the same music
happening also gets its artist as a D10 figure + quotes. D3 does not create figures/quotes itself. **Hard
boundary:** the tick invents the *happening + lore*, **never a playable audio file** — only D7's curated
`tracks` (a human-cleared file + its lore) are *playable*. So the world can have a rich music culture the
station talks about, while only the cleared subset actually airs. (D7 plays the files; D3 supplies the
culture moving around them; D10 makes the artists people; D1's culture cornerstone holds the canon
artists/eras.)

## D3.2 — Advance running stories across ticks
**Goal:** the world has day-to-day continuity — stories move through their arc over successive ticks.
**Do:**
- In the tick, after proposing new stories, select a bounded set of `active_stories` and generate the
  **next beat** for each: a new development, a consequence, or a resolution — advancing the arc stage
  (`upcoming → happening → developing → past`) with a new dated beat. Gate it the same way (safety +
  continuity against canon *and the story's own prior beats* — a beat must not contradict its history).
- Decide selection + pacing dials (`world_tick_advance_max`, how stage transitions are chosen) so the
  world moves at a believable rate and old stories resolve rather than accumulating forever.
- Ensure resolved (`past`) stories stop being advanced but remain in the log (the news desk + DJs
  reference them as history; D9 DJ memory draws on them).
**Done when:** a second `run_tick()` advances at least some running stories (new beats + stage
transitions) consistent with their prior beats and canon; stories reach resolution and stop
advancing; pacing is config-driven.

## D3.3 — World variety, balance & de-duplication
**Goal:** the *generated world* stays varied, balanced, and non-repetitive — it doesn't keep inventing
the same kind of thing or circle the same few topics. (This is **world**-level variety — distinct from
**D5**'s *on-air* anti-repetition: D3 keeps the world from looping, D5 keeps the *output about it* from
looping. Both are needed.)
**Do:**
- **Domain-balanced generation.** Tag each story/event by **domain** — the D1 cornerstones *are* the
  domains (history, literature, finance, war, nations, peoples/aliens, geography, religion, culture,
  tech). Spread the tick's new happenings across them, weighted toward domains that have been quiet
  lately, so the world isn't all politics or all festivals. Per-domain weighting dials.
- **De-duplication via similarity.** Before saving a proposed happening, use **RAG (D2)** to compare it
  against recent + active stories; if it's too close to one that already exists, **reject it or fold it
  into that story as a new beat** (don't invent the same event twice). A similarity-threshold dial.
- **Anti-clustering / rotation.** Track which domains/topics the world has leaned on over recent ticks
  and deliberately rotate, so successive nights don't circle the same ground (the world-generation
  analog of D5's airplay memory).
- **New-vs-advance pacing.** A dial balancing how much each tick *introduces new* stories vs *advances
  existing* ones (D3.2), so the world neither stagnates (all advance) nor churns (all new). Keep the
  large/small scale spread from D3.1.
- Degrade cleanly if D2 isn't built yet: fall back to tag/date-based de-dup + domain tags (weaker, but
  functional), so D3 doesn't hard-block on D2.
**Done when:** across several ticks the generated world shows a spread across domains (not one topic),
no near-duplicate stories, and a believable new/advance balance; the per-domain weights + similarity
threshold + pacing are dials; with D2 off it still de-dups structurally. Unit-tested (domain spread,
dedup rejects a near-duplicate, pacing respects the dial).

## D3.4 — Wire the tick into the periodic job + a CLI
**Goal:** the tick is the "nightly batch" the C5 cron/systemd will run, and is runnable locally now.
**Do:**
- Expose `run_tick` as `python -m src.world.world_tick` / `make world-tick` (CLI prints a summary:
  stories created, stories advanced, gate drops). Needs `make seed` + populated `.env`.
- Decide its relationship to the C2 scheduler's `top_up`: the tick writes **world state**; the
  scheduler reads it to make audio. Keep them separate jobs (the tick is nightly/world-state; the
  scheduler is the rolling-buffer top-up). Note for C5: both run on the box's timer; the tick feeds
  the buffer the scheduler fills. Don't fold the tick into `top_up`.
- Make cadence + bounds config (`world_tick_*`), and ensure a tick failure is loud (logged) but never
  corrupts the store (transactional via `store.connect`).
**Done when:** `make world-tick` runs end-to-end on the seeded local stack; a summary is printed and
logged; the job is C5-schedulable (a callable + CLI) and independent of the scheduler.

## D3.5 — Tests + verification + docs
**Goal:** the engine's real logic is covered, and the run is reproducible.
**Do:**
- Tests (surgical): arc-stage transition legality; beats carry in-world datetimes that the clock
  frames correctly (reuse the `events` framing tests' shape); the gate path drops a contradictory
  proposal (mock the LLM to return a known-bad draft → assert nothing is written); `advance_story`
  moves stage + appends a beat; resolved stories stop advancing. Mock `llm.generate` (don't spend
  tokens in unit tests); exercise the store against a test DB/fixture.
- Update `README.md` (the world tick: what it does, `make world-tick`, that C5 schedules it),
  `.env.example` (`WORLD_TICK_*`), and the DEVLOG (Phase D — D3). Consider seeding a handful of dated
  example stories so a fresh run has something to advance (ties to the C9 "give the soak a living
  now" note).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; a manual two-tick run
shows the world visibly moving (new stories, then advanced ones) with correct framing and no
contradictions.

---

## Explicitly NOT in D3 (→ later sub-packs)
- **Reporting the living world on air** (recurrence, evolution across the day, cross-segment
  continuity in news) → **D4** (the news desk). D3 only *writes* the log; D4 *broadcasts* it.
- **Anti-repetition / recent-airplay memory** → **D5** (D3 makes the world move; D5 keeps the
  *output about it* from looping).
- **In-world figures + attributable quotes** (the *people* in a story and what they *said*, so news can
  attribute and DJs can reference "what someone said") → **D10** (Figures & Quotes). D3 generates the
  *happenings*; D10 gives them *people with voices/opinions*. (D10 builds directly on D3's story log.)
- **DJ memory drawn from the event log** → **D9** (D3 provides the log; D9 gives DJs history/memory
  from it).
- **The pgvector/embeddings machinery itself** → **D2** (D3 *uses* `embeddings.retrieve` for
  consistency recall and embeds new beats via D2's helper; it doesn't build the vector seam).
- **Programming/dayparts deciding when world content airs** → **D6**.

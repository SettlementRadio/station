# PHASE_D_FRESHNESS_TASKS.md — D5: Freshness / Anti-repetition

> Sub-pack **D5** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the scheduler placement chokepoint
> `scheduler.top_up` (where every segment is generated + recorded, and `_write_sidecar` already dumps
> the full `Segment`), the writers' room `writers/conversation.py` (`showrunner` picks ONE beat;
> `orchestrate` writes the opening; `meta` carries `beat`/`part_of_day`), the news desk
> `formats/news.py` (post-D4: story-log-driven with per-story coverage memory), and `context.assemble`.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D5 brief); `docs/ROADMAP.md` (Phase D "freshness /
> anti-repetition" bullet); `src/scheduler.py` (the `schedule.json` upcoming state + the placement loop
> + `prune`); `src/writers/conversation.py` (`showrunner`/`orchestrate` — the read sites); `docs/
> PHASE_D_NEWS_DESK_TASKS.md` (D4 — its **per-story coverage memory**, which D5 complements, not
> duplicates).
>
> **Depends on:** buildable any time after **D1** against the current scheduler + writers. **Most
> valuable after D3/D4** — once the world moves (D3) and stories recur on purpose (D4), D5 is what
> keeps the *unintentional* looping (same opening, same beat, same phrasing) from creeping back in. If
> built before D3/D4, it still earns its keep against today's writers; the world just has less variety
> to preserve.

**What D5 delivers (ROADMAP, verbatim intent).** Track what aired recently — topics, openings, beats —
so 24/7 output never loops: a recent-airplay memory plus the moving world keep talk and news feeling
fresh.

**The crucial distinction — D5 vs D4's coverage memory.** D4 tracks *intended* recurrence: the news
desk *deliberately* re-reports a running story across the day, evolving it. D5 prevents *unintended*
repetition: the station opening three talk segments with the same line, the showrunner re-picking last
hour's beat, the same stock phrasing every bulletin. They're complementary — D4's coverage memory is
per-story and news-specific; D5's airplay memory is broad and cross-format (openings, beats, topics
across talk/news/everything). D5 reads D4's coverage where useful but owns the *output-phrasing*
freshness layer.

**Why a dedicated memory (not `schedule.json` / sidecars).** `schedule.json` holds only the **upcoming**
buffer (aired entries are pruned out), and the per-segment `<id>.json` sidecars are **GC'd** by C2.5's
`prune` after the retention window. Neither is a reliable record of "what aired over the last day." D5
needs its own small, persistent, recency-queryable store of *salient features* (not the audio).

**Definition of done for D5:** a recent-airplay memory records the salient features of each generated
segment and survives pruning; the showrunner avoids re-picking a recently-used beat/topic; producers
avoid recently-used openings/phrasings; generating a long run (or many segments at one `now`) shows
visibly varied openings/beats instead of loops; `ruff` + `pytest` green; README/DEVLOG updated.

---

## D5.0 — Recent-airplay memory store (record + recency read)
**Goal:** a persistent, recency-queryable record of *what* aired — features only, not audio — that
survives the C2.5 prune.
**Do:**
- Add an airplay-history store in `store.py` (the only SQL): per generated segment — `seg_id`,
  `format`, `aired_at` (the segment's `air_time`), and a small set of **salient features** (see D5.1):
  e.g. `topic`/`beat` handle, an `opening` fingerprint, and a few `key_phrases`/`beats`. Recommended:
  `airplay_history(seg_id, format, aired_at, topic, opening, features text[])` (or a jsonb column).
- Add writes `record_airplay(...)` and reads `recent_airplay(now, *, within)` /
  `recent_by_format(now, fmt, *, within)` returning the last window's features. Window is a config
  dial (`freshness_window_segments` or `freshness_window_hours` — pick one, document it).
- Bound the table (a 24/7 station accumulates rows forever): either a retention sweep (drop rows older
  than the window × a margin) folded into the scheduler housekeeping, or a capped read. Fold into the
  `clear_world`/`counts` flow. **This memory must NOT be GC'd with the audio** — it's the point.
- Keep it **distinct from D4's `news_coverage`** (per-story recurrence). Cross-reference in the code so
  the two memories aren't confused or merged.
**Done when:** features for a segment can be recorded and the recent window read back by time/format;
the table survives a `prune` run; the window is a dial. Unit-tested.

## D5.1 — Feature extraction at the placement chokepoint
**Goal:** record each generated segment's salient features once, from one place, reading what the
producers already put on the `Segment`.
**Do:**
- Record airplay at the scheduler chokepoint: in `top_up`, after a slot is generated (next to the
  existing `_write_sidecar(seg)` call), extract features from `seg` and call `record_airplay(...)`.
  One chokepoint sees every placed segment, so producers don't each need wiring. (Alternative:
  record inside each producer — note the trade-off; prefer the chokepoint.)
- Define the **salient feature set** to extract (intrinsic domain data, named constant where it's a
  list):
  - **topic / beat** — for `talk`, `seg.meta["beat"]` (already there); for `news` (D4), the covered
    story ids/angles from `meta`; for `music` (D7), the piece. A normalized handle, not the full text.
  - **opening** — a fingerprint of how the segment opened (first turn/line of `seg.script`, normalized
    — e.g. first ~8 words lowercased, or a short hash) so near-identical openings are detectable.
  - **key phrases / beats** — a few distinctive phrases or structural beats, optionally extracted
    cheaply (string heuristics; only reach for an LLM pass if heuristics prove insufficient — and then
    `haiku`, per routing).
- Idents/evergreen/disclosure segments are static and exempt — don't record them (they're *meant* to
  repeat). Filter by format/meta.
**Done when:** every generated content segment lands a feature row at placement; static/ident/evergreen
segments are skipped; features are normalized handles/fingerprints, not raw scripts.

## D5.2 — Read freshness into the writers' room + news desk
**Goal:** generation actively avoids recently-used beats, topics, and openings.
**Do:**
- **Showrunner (talk):** before picking the beat, load `recent_airplay(now, within=…)` and pass the
  recent beats/topics into the showrunner prompt as a "recently on air — pick something different"
  block, so it doesn't re-select last hour's angle. (The showrunner already chooses ONE beat — this
  just constrains the choice.)
- **Orchestrator / single-DJ producers:** pass recent **openings** into the prompt as "don't open like
  these," so consecutive segments don't start the same way.
- **News desk (D4):** complement, don't fight, D4's intended recurrence — D5 supplies recent
  *openings/phrasings* to vary (so a repeated story is told *freshly*), while D4's coverage memory
  still drives *which* stories recur and *how they evolve*. Make clear in the prompt that repeating a
  *story* (D4) is fine; repeating the *wording* (D5) is not.
- Keep the cached-core lever intact: the recent-airplay block is small and variable — put it in the
  per-call dynamic part, not the cached bible, so the cache still hits.
- Make the influence tunable (the window, how many recent items to show, whether it's a hard "avoid"
  or a soft "prefer different"). Defaults conservative — over-constraining can starve a small canon.
**Done when:** the showrunner's prompt includes recent beats/topics to avoid; producers' prompts
include recent openings to avoid; news varies wording across repeats while D4 still drives recurrence;
all reads degrade cleanly when the memory is empty (cold start).

## D5.3 — Tests + verification + docs
**Goal:** the anti-repetition logic is covered, and the freshness is demonstrable.
**Do:**
- Tests (surgical; mock `llm.generate`): `record_airplay` + `recent_airplay` round-trip and window
  bounding; the opening fingerprint detects near-identical openings and ignores different ones; the
  recent block is injected into the showrunner/producer prompts (assert the prompt contains the recent
  items); static/ident segments are not recorded; the read degrades on an empty memory. Exercise the
  store against a test DB/fixture.
- Add a demo that generates a run of several segments at advancing `now` and shows the openings/beats
  are varied (eyeball + a simple distinctness check). Pair with a D3 tick / seeded stories for topic
  variety.
- Update `README.md` (the freshness memory; the window dial), `.env.example` (`FRESHNESS_*`), and the
  DEVLOG (Phase D — D5).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the multi-segment demo
shows visibly varied openings/beats rather than loops.

---

## Explicitly NOT in D5 (→ other sub-packs)
- **Intended per-story recurrence + evolution in the news** → **D4** (D5 only keeps the *wording* fresh
  across those intended repeats; D4 owns *which* stories recur and *how they evolve*).
- **Generating new world variety (the actual source of freshness)** → **D3** (anti-repetition preserves
  variety; the world tick *creates* it — the two together are what make the station feel live).
- **DJ memory of past stories as personal history** → **D9** (that's a presenter *remembering* on
  purpose; D5 is avoiding accidental loops).
- **Programming variety across dayparts (different shows at different hours)** → **D6**.

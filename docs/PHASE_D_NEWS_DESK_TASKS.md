# PHASE_D_NEWS_DESK_TASKS.md — D4: The News Desk (reports the living world)

> Sub-pack **D4** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the current one-shot desk
> `src/formats/news.py` (single DJ, `generate_safe(...)` + evergreen fallback, `_headlines_block`
> from `ctx.events`), the format registry `formats.FORMATS` + `make_format_segment` + `stamp_duration`,
> `events.relative_phrase`/`status_of`/`progressed` (the temporal framing), `clock.to_inworld`, the
> safety gate (`safety.safety_check`/`generate_safe`), and `embeddings.retrieve` (D2).
>
> **Naturalness — carry the route-A pass into the desk.** The talk prompts got a "natural register"
> pass (2026-06-29, `writers/conversation.py`): lead with the host's card voice + verbal tics, use
> POSITIVE style guidance (contractions, varied rhythm, react-and-build), and treat canon as shared
> knowledge. Do the same here: the old `news.py` `_build_system` ("clear, measured… a trusted settlement
> desk" + a rigid "exactly N headlines" skeleton) is exactly the stiffness to drop. News is reportage —
> state things plainly — but in the **anchor's actual voice**, not officialese; loosen the word budget if
> it reads clipped.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D4 brief); `docs/ROADMAP.md` (Phase D "news desk"
> bullet — the canonical spec); `src/formats/news.py` (the one-shot desk to replace — **keep its
> `generate_safe` + evergreen pattern and its `Segment` shape**); `src/world/events.py`
> (`relative_phrase`); `docs/PHASE_D_WORLD_ENGINE_TASKS.md` (D3 — the story-log schema + reads this
> desk consumes: `active_stories`, `story_beats`, the arc stages, beats-as-dated-events).
>
> **Depends on:** **D3** (the story log it reports — `stories` + arced, dated beats). **D2** (semantic
> recall to keep each bulletin relevant to canon AND to now). If D2 isn't built, gate the recall step
> behind a capability check and fall back to structured (date/tag) selection.

**What D4 delivers (ROADMAP, verbatim intent).** Replace the one-shot bulletin with a desk that reads
the story log and broadcasts it like a real station:
- every hour's news is **relevant to canon AND to what's happening now**;
- stories **recur across the day** — some simply repeated, some **repeated-and-evolved** (a fresh
  development since the last bulletin);
- **correct temporal framing** — trailed as upcoming, covered as now, referenced as past (the B2
  relative-time renderer);
- **continuity** — the same story is referred to consistently across segments, hours, and days.

**The shift from today's desk.** `news.py` currently pulls `ctx.events` (a flat date-window list) and
asks Claude for N headlines in one shot — no memory of what it said last hour, no story arcs, no
recurrence/evolution. D4 makes the desk *story-log-driven and stateful*: it selects from D3's running
stories, frames each by its arc + datetime, decides repeat-vs-evolve from what it already aired, and
stays self-consistent across bulletins.

**Definition of done for D4:** generating news at successive hours over a simulated day yields
bulletins that (a) report D3's stories with correct upcoming/now/past framing, (b) recur — some
stories repeated, some repeated-and-evolved when a new beat landed since last coverage, (c) stay
internally consistent (same story named/framed consistently across bulletins), and (d) pass the
safety/continuity gates with an evergreen fallback. `ruff` + `pytest` green; README/DEVLOG updated.

---

## D4.0 — News coverage memory (what aired, which story, at what beat)
**Goal:** a persistent record of how each story has been covered, so the desk can repeat, evolve, and
stay consistent across bulletins — the substrate the rest of D4 reads.
**Do:**
- Add a small coverage store (in `store.py`, the only SQL): per (story, bulletin) — when it was
  covered, the **arc stage + latest beat** reported, and a short handle/angle used (for consistent
  naming). Recommended: a `news_coverage(story_id, covered_at, arc_stage, last_beat_id, angle)` table,
  plus reads `last_coverage(story_id)` and `coverage_since(t)`.
- Keep this **distinct from D5's anti-repetition memory** (OVERVIEW §3): D4's coverage memory is
  *per-story, news-specific* ("how have I been telling this story?"); D5 is *broad* output-level
  anti-repetition ("don't reuse this opening/beat"). Note the relationship in the code; D5 will layer
  on top, not duplicate.
- Fold the table into the `clear_world`/re-seed flow + `counts`.
**Done when:** a bulletin can record its coverage of each story and read back the last coverage
(stage + beat) for any story. Unit-tested.

## D4.1 — Story selection for the hour (relevant to canon AND to now)
**Goal:** pick which stories this hour's bulletin reports, balancing now-relevance, canon-relevance,
and recurrence.
**Do:**
- Add a selection step (in the desk module, reading the D3 log): from `active_stories` + beats near
  `clock.to_inworld(now)`, choose a bounded set (config: `news_story_count` ~ the old
  `format_news_headline_count`) that mixes:
  - **breaking/now** — stories with a beat at/near now (temporal `today`/`happening`);
  - **trailed** — notable `upcoming` beats worth previewing;
  - **ongoing** — stories covered before that have a **new beat since last coverage** (→ evolve), or
    are significant enough to **repeat** even without a new beat;
  - grounded by **canon relevance** via `embeddings.retrieve` (D2) so the bulletin connects to the
    bible, not just the calendar.
- Use the D4.0 coverage memory to mark each selected story as `new` / `repeat` / `evolve` (evolve =
  covered before AND a newer beat exists). This tag drives D4.2's framing.
- Make the mix tunable (dials for how many breaking vs ongoing vs trailed; how stale a repeat may be).
**Done when:** selection returns a ranked, tagged set of stories for a given `now`, mixing breaking /
ongoing / trailed, grounded in canon recall, with each tagged new/repeat/evolve from coverage memory.

## D4.2 — The story-log-driven desk producer (framing + recurrence + evolution + gates)
**Goal:** rebuild the `news` producer to broadcast the selected stories like a real desk — correctly
framed, recurring, evolving — without losing the safety/evergreen discipline.
**Do:**
- Rewrite `src/formats/news.py`'s builder to consume the D4.1 selection instead of the flat
  `_headlines_block`. For each selected story, build a desk-ready brief: its title/angle, its
  **relative temporal phrase** (`events.relative_phrase` on the relevant beat — "tomorrow", "tonight",
  "yesterday"), its **arc stage**, and — for `evolve` stories — the **delta since last coverage** (the
  new beat), so the anchor can say "an update on …" rather than re-reading the same item.
- Drive the script generation (Claude, `sonnet` per routing) from that brief: a desk open → the
  selected items framed by their tags (trail upcoming, report now, reference past; "still developing"
  for ongoing; "an update on" for evolve) → sign-off. Keep it **reportage** (the anti-recitation rule
  is for talk, not news — the current `news.py` note stands).
- **Keep the gate + fallback exactly as the pattern is today:** wrap generation in `generate_safe(...)`;
  on a persistent safety flag, return `evergreen.evergreen_segment(...)` (never air a flagged
  bulletin). Return through `make_format_segment` → `stamp_duration` so duration accounting is honest.
  Keep `Segment.format="news"`, `disclosure=True`, and enrich `meta` (the covered story ids, their
  tags new/repeat/evolve, the beats referenced) so coverage is auditable.
- After a successful render, **record coverage** (D4.0) for each reported story (stage + beat + angle),
  so the next bulletin knows what was said.
**Done when:** the desk produces a bulletin from the story log with correct temporal framing; evolve
stories are reported as updates (delta), repeats as repeats; the safety gate + evergreen fallback work
unchanged; coverage is recorded; the segment carries auditable `meta`.
**Note — the cached-core lever.** The bible/anchor card is stable; pass it as `cached_context` (as the
writers' room does) so each bulletin pays full price only for the small variable brief.

## D4.3 — Continuity across segments, hours, and days
**Goal:** the same story is referred to consistently over time — naming, facts, and framing don't
drift between bulletins.
**Do:**
- Feed the desk the **prior coverage** (D4.0) of each story it's about to re-report (the angle/handle
  it used, the last stage/beat) so it reuses consistent naming and doesn't contradict what it already
  aired.
- Run a **continuity check** on the bulletin against canon + the story's prior beats/coverage (reuse
  the continuity-gate pattern, or a desk-specific editor pass): catch a bulletin that renames a story,
  contradicts an earlier report, or mis-frames an arc. On a flag: regenerate once with the note fed
  back, then fall back to evergreen (the C0 discipline). Bound by a `news_continuity_max_attempts`
  dial.
- Verify across a simulated day: generate several bulletins at successive hours and confirm a recurring
  story keeps a consistent identity and a coherent past→now→future progression.
**Done when:** across multiple bulletins, a recurring story is named/framed consistently and never
contradicts earlier coverage; a deliberately inconsistent draft is caught and regenerated or replaced.

## D4.4 — Tests + verification + docs
**Goal:** the desk's real logic is covered, and the behaviour is demonstrable.
**Do:**
- Tests (surgical, real logic; mock `llm.generate` — don't spend tokens): selection tags stories
  new/repeat/evolve correctly from coverage + new beats; the temporal framing uses the right
  `relative_phrase` for upcoming/now/past beats; a story with a new beat since last coverage is
  selected as `evolve`; the safety-flag path falls back to evergreen and writes nothing flagged;
  coverage is recorded after a successful bulletin. Exercise the store against a test DB/fixture with
  a small seeded story log.
- Add a CLI/`make` demo that generates a sequence of bulletins across a simulated day (advancing
  `now`) so the recurrence/evolution/framing is visible end-to-end (needs `make seed` + a D3 tick or
  seeded stories).
- Update `README.md` (the news desk now reads the story log; how to run the demo), `.env.example`
  (`NEWS_*` dials), and the DEVLOG (Phase D — D4).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the multi-bulletin demo
visibly shows breaking → repeated → repeated-and-evolved → referenced-as-past over a simulated day.

---

## Explicitly NOT in D4 (→ later sub-packs)
- **Broad anti-repetition of openings/beats/topics across *all* formats** → **D5** (D4 owns per-story
  *coverage* memory for recurrence/evolution; D5 owns output-level freshness so talk and news don't
  loop their phrasing). D4.0's coverage table is the news-specific complement D5 builds on.
- **Generating/advancing the stories themselves** → **D3** (D4 only *reports* the log; if there's no
  story movement, that's a D3 concern).
- **When/where the news airs in the schedule (dayparts, top-of-hour cadence)** → **D6** (programming
  backbone). D4 produces a bulletin on demand; D6 decides the grid that calls it.
- **Stings/beds around the bulletin (sound design)** → **D7**.
- **DJ/anchor memory of past stories as personal history** → **D9** (D4 is desk continuity; D9 is a
  presenter remembering what they lived through).

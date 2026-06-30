# PHASE_D_OVERVIEW.md — "The Living World" (deep · alive · build)

> The master plan for Phase D. Phase D is large, so it is **split into sub-packs** — each its own
> `docs/PHASE_D_<NAME>_TASKS.md` file, executed task-by-task like the C0–C9 pack. This file is the
> map: what each sub-pack achieves, which docs to read for it, the seams it touches, and how the
> sub-packs depend on each other. **Work from the tracker (§4): pick the next `Ready` sub-pack, ask
> Claude (chat) to generate its `_TASKS.md` if it doesn't exist yet, then build it.**
>
> Read first: `docs/PHASE_C_ORIENTATION.md` (the as-built C0–C4 seams + §9's workstream→seam map —
> this whole phase plugs into those), `docs/ROADMAP.md` (Phase D section — the source of this
> breakdown), `docs/ARCHITECTURE.md` (the two seams + the layered design), `CLAUDE.md` (constitution:
> seams, model routing, cost levers, engineering standards, hard rules).

## 1. What Phase D is

Phase C made the station *safe, continuous, and public-capable* (a body). Phase D makes it *deep and
alive* — the fix for "thin conversations," and what makes it worth featuring. The heart of the phase:
**a world that moves on its own** and **a news desk that reports it like a real station**, on top of a
**real world bible** the human authors. Everything rides the seams that already exist and are green
(see `docs/PHASE_C_ORIENTATION.md` §9): the `store` SQL seam, `context.assemble`, the `events`/clock
machinery, the `formats` registry + `make_format_segment`, the C2 scheduler, and the stubbed
`embeddings`/pgvector seam waiting to be switched on.

**Division of labor (from ROADMAP):** **YOU** author the world bible (yours to write) and approve the
**bible + the patterns/examples** the generators follow — **NOT every nightly story.** The world tick
runs **autonomously behind the safety + continuity gates**: accepted generated stories/figures/quotes are
written straight to the store (no per-story human sign-off). You control the world by controlling the
bible; a per-story *approval queue* (`pending/approved/rejected`) is a **Phase-E opt-in**, deliberately
not built now. You also make the voice-engine call and set the music policy. **CLAUDE (chat)**
sequences the pack, drafts bible scaffolding + story examples. **CLAUDE CODE** builds each sub-pack.

## 2. Standing principles for the whole phase

These hold across every sub-pack — restate them at the top of each `_TASKS.md`, don't re-derive them:

- **The seams are law.** All SQL stays in `src/world/store.py`; all model calls go through
  `providers/llm.py`; all voice through `providers/tts.py`; all embeddings through
  `providers/embeddings.py`. A new format is a `FORMATS` registry entry, not a scheduler change. A new
  segment kind still flows through `make_format_segment` → `stamp_duration` so it gets honest
  duration accounting for free.
- **The world-tick is generative.** The nightly world simulation (D3) is **Layer 3 machinery writing
  Layer 1 state** (ARCHITECTURE.md): it uses the same `llm.generate` + gates as the writers' room to
  *write events into the store*, then the writers read them back. It is not a separate engine outside
  the seams.
- **The folder is re-seedable; the living world persists.** `docs/canon/` is the hand-authored *static
  substrate* (re-seeded from source); the *moving present* — the tick's generated events + story log —
  is dynamic DB state the human never edits. **A canon refresh (re-seeding to pick up a bible edit)
  must NOT wipe the tick-generated world.** The seed has two modes: a *full reset* (clears everything,
  dev) and a *canon refresh* (re-loads/re-embeds only the folder-owned `canon`/`cast`/bible, leaving
  `stories`/beats/tick-`events` intact). The seed-vs-generated `events` split (a `source` column or id
  namespace) is decided in **D1.2** and honoured by **D3.0** — and by any sub-pack that touches the
  seed (e.g. D9 roster edits are a canon refresh). RAG re-embeds on re-seed, not live.
- **Cost levers stay mandatory.** Text is near-trivial today (Kokoro is the real ceiling — see
  PHASE_C_ORIENTATION §8), but D adds high-volume generation (the world tick, RAG embedding, the news
  desk). Route by job (`haiku` for volume/low-stakes, `sonnet` for the writing brain, `opus` only for
  gnarly calls), **run the nightly tick through the Batch API (50% off)**, and **cache the stable
  canon/cards** so each call pays full price only for the small variable part. The Batch API was
  weakened in Phase B (trivial text bill); D's volume **re-justifies it** — revisit per sub-pack. For
  current model IDs, pricing, and the Batch/caching APIs, consult the `claude-api` skill — do not
  answer model questions from memory.
- **Gates apply to all new generated content.** Every new producer (news desk, world tick,
  commercials, sponsor reads) runs `safety.safety_check` and, where it's dialogue/canon-bound, the
  continuity gate — falling back to evergreen, never airing flagged or self-contradictory text. This
  is the same gate Phase E points at listener inbound.
- **Hard rules unchanged.** Tribute, not derivative (no real franchises/people/trademarks); AI
  disclosure stays on; secrets only in `.env`; ask before destructive actions. The in-world year is
  always `real year + 600` — never hardcode it (`settings.world_years_ahead`).
- **Engineering standards unchanged.** Config over hardcoding (`settings.X`, area-prefixed, one typed
  module), structured logging (no `print` in the backend), bounded retries on every external call,
  ruff + pre-commit green, surgical tests on real logic. Each sub-pack adds its own `# --- <Area>
  (D?) ---` config section and `tests/test_*.py`.
- **Feed the operator manual as you go.** Each functional sub-pack (D1–D10), in its docs task, **appends
  its admin how-tos to a living `docs/ADMIN_MANUAL.md`** — terse, *what it does + the exact
  command/file/steps* — while the operations are fresh. The closing capstone **D11** consolidates,
  simplifies, gap-fills, and *verifies* these into one clean operator manual; capturing them per-pack is
  what makes D11 an assembly job, not archaeology.
- **Migrations, not truncate-reseed, once the world is alive.** Phase D adds many tables + columns. While
  the world is hand-seeded this is fine via `init_schema` + `clear_world`. But once the tick has written
  irreplaceable state (and on the VPS), **you cannot add a column by wiping and re-seeding.** So new
  schema lands via **idempotent migrations / explicit backfill scripts** (additive `CREATE ... IF NOT
  EXISTS`, `ADD COLUMN ... DEFAULT`, a one-off backfill), never a destructive rebuild. Any sub-pack that
  adds a table/column ships its migration + backfill, and the seed/reset matrix below says what each
  destructive command is allowed to clear.
- **Cost visibility, not just cost levers.** The levers (Batch, caching, routing) keep cost low; *seeing*
  it keeps it honest. Every generating job logs its **usage** — tick calls, news calls, TTS minutes,
  embeddings count, gate regenerations/drops, failures — as structured fields, and the D6 status console
  surfaces a rollup. A run whose cost you can't see is a run you can't trust unattended.

## 2a. State ownership, seed modes & backup — the matrix

The single contract for *who owns each table, what each seed/reset command may touch, and what must be
backed up.* Every sub-pack that adds a table conforms to a row here; destructive commands clear **only**
their declared scope. (Confirmed decisions: **`reset-world` wipes world+canon only — never the station
config/catalog**; **backups cover the tick-generated world + hand-entered sponsors** — everything else is
recoverable from git/manifests or is regenerable.)

| Table | Owned by | Seed/refresh cmd | Canon refresh (`seed-canon`) | Grid refresh (`seed-grid`) | `reset-world` (destructive) | Backup |
|---|---|---|---|---|---|---|
| `canon`, `"cast"` | folder (`docs/canon/`) | `seed-canon` | re-seeded | survives | **cleared + reseeded** | git (folder) |
| `events` (`source=seed`) | folder | `seed-canon` | replaced | survives | **cleared** | git |
| `events` (`source=tick`), `stories`, beats | **world tick** | (generated) | **survives** | survives | **cleared** | **YES — irreplaceable** |
| `figures`/`quotes` (`source=bible`) | folder | `seed-canon` | re-seeded | survives | **cleared** | git |
| `figures`/`quotes` (`source=tick`) | **world tick** | (generated) | **survives** | survives | **cleared** | **YES — irreplaceable** |
| `embeddings` (polymorphic, D2) | derived | re-embedded at seed | re-embedded (affected rows) | survives | cleared + re-embedded | no (regenerable) |
| `news_coverage` (D4) | runtime | (accrues) | survives | survives | **cleared** | optional |
| `airplay_history` (D5) | runtime (bounded) | (accrues) | survives | survives | **cleared** | no |
| `programs`/grid (D6) | YAML manifest | `seed-grid` | survives | re-seeded | **survives** (config, not world) | git (YAML) |
| `tracks` (D7) | music-lore manifest | `seed-tracks` | survives | survives | **survives** (catalog, not world) | git (manifest) + `assets/` backup |
| `sponsors` (D8) | human-entered | `seed-sponsors`/console | survives | survives | **survives** (config, not world) | **YES — hand-entered** |
| `state` (kv) | runtime/world | — | by key | by key | mostly cleared | maybe |

**The seed/reset commands** (D1.2 owns the naming; the destructive one is renamed + warned):
- **`make seed-canon`** — the everyday command: re-load the bible/cast/seed-events + re-embed, **leaving
  the living world (tick state) and the station config/catalog intact.**
- **`make seed-grid`** / **`make seed-tracks`** / **`make seed-sponsors`** — refresh one config/catalog
  area from its manifest, scoped to its own tables only.
- **`make reset-world`** — the **destructive** full world+canon wipe (loud warning + confirmation). Clears
  the "cleared" column above; **never** touches grid/tracks/sponsors. (A `reset-all` that also drops
  config/catalog is an optional future convenience, not the default.)

## 3. The sub-packs

Each entry: **Goal**, **Builds**, **Docs to read**, **Seams it touches** (from PHASE_C_ORIENTATION
§9), **Depends on**. The detailed task list lives in each sub-pack's own `_TASKS.md` (generated on
demand). Order below is roughly the build order; the dependency graph is in §4.

### D1 — Canon → Folder (`PHASE_D_CANON_FOLDER_TASKS.md`)
- **Goal:** turn the single `docs/CANON.md` stub into a real, growable **world bible** — a
  `docs/canon/` folder of cornerstone files the seeder reads whole. The *static substrate*: large,
  slow-changing, RAG-able.
- **Builds:** the folder layout + authoring conventions (so the human can write the bible); a
  folder-loading canon parser with globally-unique fact ids; config + seed + context wired to the
  folder; migration of the existing stub into it.
- **Docs:** `docs/CANON.md` (current stub), `src/world/canon_source.py` + `src/world/seed.py` +
  `src/world/context.py` (the parse/seed/assemble path), CLAUDE.md ("the canon lives in docs/CANON.md").
- **Seams:** `canon_source.load`/`load_series_bible`, `store.insert_canon/insert_cast/insert_events`,
  `context.assemble`, `settings.canon_path`.
- **Depends on:** nothing (C complete). **Foundational — do first.**

### D2 — Semantic Retrieval / RAG (`PHASE_D_RAG_TASKS.md`)
- **Goal:** activate the stubbed vector seam so the writers' room recalls canon by **meaning**, not
  just date/tag — necessary once the bible (D1) is too big to cache wholesale.
- **Builds:** pgvector install + a **polymorphic `embeddings(corpus, entity_id, …)` table** + `search()`
  in `store.py` (multi-corpus from day one, so D3/D10 reuse it — not a canon-only table); a real
  `embeddings.embed()` behind the seam (provider is a **decision** — see the pack); embed canon +
  events on seed; wire `retrieve()` into `context._select_canon`; tag the canon facts.
- **Docs:** `src/providers/embeddings.py` (the stub + its TRIGGER note), `src/world/store.py` (the
  documented FUTURE vector seam), `src/world/context.py` (`_select_canon` fallback), the `claude-api`
  skill (embeddings provider question — Anthropic has no first-party embeddings endpoint).
- **Seams:** `embeddings.embed`/`retrieve`, `store` vector seam, `context._select_canon`,
  `store.canon_by_tags`.
- **Depends on:** **D1** (needs the bigger, foldered, taggable canon to be worth switching on).

### D3 — World Engine (`PHASE_D_WORLD_ENGINE_TASKS.md`) — THE KEYSTONE
- **Goal:** make the +600y world *live the way reality does* — a moving present on top of the static
  bible. A nightly **world tick** generates plausible new happenings consistent with the bible,
  models each as a **story with an arc** (rumoured → upcoming → happening → developing → past) with an
  in-world datetime, and **advances** running stories over subsequent ticks.
- **Builds:** a story-log schema (stories + beats, arc stage) in `store.py`; the generative tick
  (Layer 3 → Layer 1, gated, batched, cached); story-advancement across ticks; consistency via the
  continuity gate + RAG recall; wired into the periodic job (the C5 "nightly batch").
- **Docs:** `docs/ROADMAP.md` (Phase D "world-simulation engine" bullet — the arc model),
  `docs/ARCHITECTURE.md` (Layer 1 state, "the tick is generative … uses Layer 3's machinery"),
  `src/world/events.py` + `clock.py` (status/relative-phrase framing), `src/world/store.py` (events
  table), the C0 gate seams (`safety`, `conversation.continuity_check`), the `claude-api` skill (Batch
  API for the nightly run).
- **Seams:** `store` events/stories, `events.status_of`/`progressed`/`relative_phrase`, `clock`, the
  gates, `embeddings.retrieve` (D2, for consistency recall).
- **Depends on:** **D1** (canon to stay consistent with); **D2 strongly recommended** (semantic recall
  keeps new stories from contradicting canon) but the tick can write events without it.

### D4 — News Desk (`PHASE_D_NEWS_DESK_TASKS.md`)
- **Goal:** replace the one-shot news bulletin with a **desk that reads the story log and broadcasts
  it like a real station** — every hour relevant to canon AND to what's happening now; stories recur
  across the day (some repeated, some repeated-and-evolved); correct temporal framing
  (upcoming/now/past); cross-segment continuity.
- **Builds:** a story-log-driven `news` producer; recurrence + evolution logic; temporal framing via
  the relative-time renderer; continuity across segments/hours/days.
- **Docs:** `src/formats/news.py` (the current one-shot desk to replace — keep its `generate_safe` +
  evergreen pattern), `src/world/events.py` (`relative_phrase`), D3's story-log schema, ROADMAP "news
  desk" bullet.
- **Seams:** `formats` registry, `make_format_segment`/`stamp_duration`, `events`/story log,
  `embeddings.retrieve`, the safety gate.
- **Depends on:** **D3** (the story log it reports), **D2** (semantic recall).

### D5 — Freshness / Anti-repetition (`PHASE_D_FRESHNESS_TASKS.md`)
- **Goal:** 24/7 output never loops — track what aired recently (topics, openings, beats) so talk and
  news stay fresh; combined with the moving world (D3), the station feels live.
- **Builds:** a recent-airplay memory (what topics/openings/beats aired, when) the producers read to
  avoid repeats; wired into the showrunner/news/talk prompts.
- **Docs:** `src/scheduler.py` (the `schedule.json` history it can build on), `src/writers/
  conversation.py` (showrunner/orchestrator prompts), ROADMAP "freshness/anti-repetition" bullet.
- **Seams:** scheduler state, `context.assemble`, the writers' room prompts.
- **Depends on:** **D3/D4** conceptually (a moving world + recurring stories to *not* repeat), but
  buildable against the scheduler + writers any time after D1.

### D6 — Programming Backbone + Status Console (`PHASE_D_PROGRAMMING_TASKS.md`)
- **Goal:** named **programs**, **dayparts**, and a **weekly routine** the scheduler reads (which
  show, which DJs, when); a **read-only status console** (what's airing, buffer depth, last night's
  run, the story log); surface **now-playing / program info** to the web player.
- **Builds:** a programming grid (config/DB) the scheduler consumes instead of a flat
  `buffer_rotation`, each program carrying a **clock** (a real-radio-style sequence + run-lengths — so
  the grid expresses *dedicated music blocks* vs *music interspersed with talk*, and pinned slots like
  top-of-hour news); generalisation of `world/framing.py` beyond two hardcoded hosts; a read-only
  console over `schedule.json` + `health` + the story log; now-playing surfaced to `/web`.
  *(The write/management surface is Phase E — keep this read-only.)*
- **Docs:** `src/world/framing.py` (the only daypart logic today — the seam to grow), `src/scheduler.
  py` (flat rotation + the `schedule.json` contract), `src/health.py` (the console's data feed),
  `web/` (the player route, C8), ROADMAP "programming + admin backbone" bullet.
- **Seams:** `framing.show_frame`, scheduler `top_up`/state, `health.run_checks`, the web app.
- **Depends on:** the **C2 scheduler** (built) — largely **independent of D1–D5**, so it can run in
  parallel with the world/news spine. Needed before D7/D8 (they need dayparts for ad/break cadence).

### D7 — Production Layer: sound design + songs (`PHASE_D_PRODUCTION_TASKS.md`)
- **Goal:** make it *sound* like a real station — **jingles / idents / stings / beds** mixed with
  **ducking** (a bed under speech, a sting before news; Layer 4, finally real); and **songs as cultural
  artifacts** — tracks catalogued with their **lore** (artist→D10 figure, album, in-world era, story),
  dropped into the `music` format's `[SONG]` slot with a DJ intro that **tells the song's story** ("a
  classic from the 24th century, by …") + now-playing (then re-add `music` to the rotation). Only
  files are *playable*; the broader music *culture* lives as D10 artists + D3 releases + D1 culture canon.
- **Builds:** the curated media file-sets under `assets/{idents,themes,stings,music}/`; a cultural
  `tracks` table (title, artist-figure link, album, era, story, mood, duration, licence note) + a curated
  music-lore manifest (human-owned, survives canon refresh) in `store.py`; Layer 4 mixing/ducking in
  playout/render; the lore-driven song-slot fill; re-adding `"music"` to `buffer_rotation`.
- **Docs:** `docs/JINGLE_PROMPTS.md` (the brief + Suno prompts — already written), `src/formats/
  music.py` + `settings.format_music_song_marker` (the empty `[SONG]` slot), `config/radio.liq` +
  `src/providers/tts.py` `concat_audio` (the mixing seam), PHASE_C_ORIENTATION §6.1/§9 (music dropped
  from rotation; the prune name-exemption rule for shared media).
- **Seams:** `assets/`, `tts.concat_audio`, Liquidsoap, `formats.music`, `store` (`tracks`),
  scheduler `buffer_rotation`. **Protect shared media from C2.5 `prune()`** by name/`assets/` path.
- **Depends on:** **D6** (dayparts/programming decide when beds/stings/breaks fire). Uses
  JINGLE_PROMPTS. Song *catalogue/clearance* is the human's separate call — D7 builds only the
  plumbing.

### D8 — Commercials & Sponsorship (`PHASE_D_COMMERCIALS_TASKS.md`)
- **Goal:** texture, not interruption — an in-world **`commercial`/`promo` format** (Claude writes a
  short spot for a fictional +600y product, or a station promo, voiced like any segment), a scheduler
  **ad-break cadence** (dayparts decide when a break airs), and real **"Powered by"** reads from a
  small **`sponsors` table** once donations are live (CM).
- **Builds:** a new `commercial`/`promo` format (copy the `generate_safe` + evergreen pattern from
  `news.py`) — **generated fresh every airing** (no rotating reel; that's the AI advantage), at L1
  (voiced read) with opt-in richer levels (L2 bed via D7, L3 multi-voice/figure-testimonial via D9/D10,
  L4 sparse brand sting); ad-break cadence in the scheduler/dayparts; a `sponsors` table (text, optional
  audio, run window); always "Powered by," never "Sponsored by" (MARKETING.md).
- **Docs:** `src/formats/news.py` (the producer pattern to copy), `src/scheduler.py` (cadence),
  `docs/MARKETING.md` (the "Powered by" rule + sponsorship policy), ROADMAP "commercials &
  sponsorship" bullet.
- **Seams:** `formats` registry, scheduler cadence/dayparts, `store` (`sponsors`), the safety gate.
- **Depends on:** **D6** (dayparts decide breaks), **D7** (stings around breaks). Sponsor reads also
  gate on **CM** (donations live) for real sponsors — the plumbing can land earlier.

### D9 — Voice & Emotion + DJ Roster (`PHASE_D_VOICE_ROSTER_TASKS.md`)
- **Goal:** wire the `emotion` param to the chosen engine (**ElevenLabs carries emotion; Kokoro
  cannot** — so emotion presumes the flagship path), add a **pronunciation lexicon** so invented
  names are spoken right, and grow the cast — add/edit/remove DJs, each with a persona, a way of
  speaking, and **history/memory drawn from the event log** so a DJ remembers what the world (and
  they) lived through.
- **Builds:** `emotion` flowing through `tts.synthesize` to ElevenLabs; a pronunciation lexicon
  applied before TTS; cast CRUD beyond the two hardcoded hosts; **guest / non-host voices** (figures &
  invited guests speak in a segment — the D10 bridge); DJ memory drawn from the story log.
- **Docs:** `src/providers/tts.py` (the inert `emotion` param + voice registries), `src/world/store.
  py` (`"cast"` table — already supports more rows), `src/config.py` (`convo_speaker_ids`),
  PHASE_C_ORIENTATION §8/§9 (emotion presumes flagship; the C6 launch-voice decision), the
  `claude-api`/voice context for the engine call.
- **Seams:** `tts.synthesize` (`emotion`) + registries, `store` `"cast"`, `convo_speaker_ids`, the
  conversation turn model (N voices), the story log (DJ memory).
- **Depends on:** **D3** (event/story log for DJ memory); presumes the **C6 flagship-voice decision**
  (server track) for emotion; **D10** for *world-grounded* guest content (a guest still works without
  it via a generic persona). Roster CRUD itself is buildable earlier.

### D10 — Figures & Quotes (`PHASE_D_FIGURES_QUOTES_TASKS.md`)
- **Goal:** the world *speaks* — model in-world **figures** (the invented people a story is about) and
  their **attributable quotes** (what they said), so the news can attribute ("X said…"), DJs can
  reference an opinion, and (with D9) a quote can air as a distinctly-voiced **soundbite**. The biggest
  lever for *rich content*: it turns "a fact happened" into "people in a living world saying things."
- **Builds:** a `figures` table + a `quotes`/`statements` table in `store.py` (linked to D3's
  stories/beats, dated like beats); the D3 tick extended to generate gated, canon-safe figures + quotes;
  news attribution + DJ reference of quotes; the soundbite bridge to D9.
- **Docs:** D3's story log (`docs/PHASE_D_WORLD_ENGINE_TASKS.md`), D4's news desk (attribution), `src/
  world/store.py` (the `"cast"` shape to learn from), D9 (the guest/non-host voice that *plays* a quote),
  `events.relative_phrase` (framing quotes by date), CLAUDE.md IP boundary (invented people only).
- **Seams:** `store` (`figures`/`quotes`), the D3 tick, the gates, `embeddings.retrieve` (D2), the
  conversation turn model + D9 voice (soundbites).
- **Depends on:** **D3** (the story log figures/quotes attach to). **D2** recommended (recall by
  meaning). Voicing soundbites needs **D9**'s guest-voice slot — textual attribution lands without it.

### D11 — Operator / Admin Manual (`PHASE_D_ADMIN_MANUAL_TASKS.md`) — the capstone
- **Goal:** one clean `docs/ADMIN_MANUAL.md` covering **everything the operator does** to run the station —
  **simple, functionality + how-tos, no intro essays** (a cookbook, not a narrative). Every how-to is
  *verified by running it*, so it's trustworthy for unattended operation.
- **Builds:** the consolidated, simplified, gap-filled, verified operator manual (running the station,
  seed modes, authoring the bible, programming the grid, music/tracks, commercials/sponsors, voice,
  status/monitoring, recovery, admin access); reconciliation with `docs/HOWTO.md` (one operator source).
- **Docs:** the living `docs/ADMIN_MANUAL.md` stub (each functional pack appended its how-tos as built —
  see the standing convention in §2), `docs/HOWTO.md`, the Makefile targets + `python -m src.*` CLIs
  (the operator entry-point checklist), the C5 run essentials.
- **Depends on:** **D1–D10 built** (it documents the *as-built* surface). Leans on **C5** for the
  "running the station" section. **Re-verified at the soft launch (CM).**

## 4. Dependency graph + tracker

**Two parallel tracks**, mirroring how C split:
- **The living-world spine:** D1 → D2 → D3 → D4, with D5 riding on D3/D4 and **D10** (figures & quotes)
  riding on D3 (and feeding D4 attribution + D9 soundbites).
- **The station-craft track:** D6 → D7 → D8, largely independent of the spine (builds on the C2
  scheduler), plus D9 (needs D3's log for DJ memory; presumes C6 for emotion; bridges to D10 for guests).

```
D1 Canon→Folder ──▶ D2 RAG ──▶ D3 World Engine ──▶ D4 News Desk
                                   │   │   │            │
                                   │   │   └────────────┴──▶ D5 Freshness
                                   │   └──▶ D10 Figures & Quotes ──▶ (D4 attribution)
                                   └──▶ D9 Voice & Roster (DJ memory; +C6 emotion)
                                                  ▲           │
                                       D10 figure ┴──────────┘ D9 guest-voice  =  soundbites / guests

D6 Programming ──▶ D7 Production ──▶ D8 Commercials      (C2 scheduler → ; runs alongside the spine)

D1–D10 (all built) ──▶ D11 Operator/Admin Manual  (the capstone — documents the whole surface, last)
```
*(D9×D10 bridge: D10 supplies the figure + quote, D9 gives it a voice + turn slot → an aired soundbite
or invited guest.)*

**Tracker** — update the Status column as packs are written/built. `Ready` = its dependencies are
done and Claude (chat) can generate the `_TASKS.md` now.

| Sub-pack | File | Depends on | Pack written? | Built? | Status |
|---|---|---|---|---|---|
| D1 Canon → Folder | `PHASE_D_CANON_FOLDER_TASKS.md` | — | ✅ | ✅ | **Built** (D1.0–D1.4) |
| D2 Semantic Retrieval / RAG | `PHASE_D_RAG_TASKS.md` | D1 | ✅ | ✅ | **Built** (D2.0–D2.6) |
| D3 World Engine (keystone) | `PHASE_D_WORLD_ENGINE_TASKS.md` | D1 (D2 recommended) | ✅ | ✅ | **Built** (D3.0–D3.5) |
| D4 News Desk | `PHASE_D_NEWS_DESK_TASKS.md` | D3, D2 | ✅ | ✅ | **Built** (D4.0–D4.4) |
| D5 Freshness / Anti-repetition | `PHASE_D_FRESHNESS_TASKS.md` | D3/D4 | ✅ | ☐ | **Ready** (D3 built; rides D4) |
| D6 Programming + Status Console | `PHASE_D_PROGRAMMING_TASKS.md` | C2 scheduler | ✅ | ☐ | **Ready** (parallel-able) |
| D7 Production (sound + songs) | `PHASE_D_PRODUCTION_TASKS.md` | D6 (soft→D10: artist links) | ✅ | ☐ | Blocked on D6 build |
| D8 Commercials & Sponsorship | `PHASE_D_COMMERCIALS_TASKS.md` | D6, D7 (CM for real sponsors) | ✅ | ☐ | Blocked on D6/D7 build |
| D9 Voice & Emotion + Roster | `PHASE_D_VOICE_ROSTER_TASKS.md` | D3 (memory); C6 (emotion); D10 (guests) | ✅ | ☐ | **Ready** (D3 built; +C6 for emotion) |
| D10 Figures & Quotes | `PHASE_D_FIGURES_QUOTES_TASKS.md` | D3 (D2 rec.; D9 for soundbites) | ✅ | ✅ | **Built** (D10.0–D10.2, D10.4; D10.3 soundbite awaits D9) |
| D11 Operator/Admin Manual (capstone) | `PHASE_D_ADMIN_MANUAL_TASKS.md` | D1–D10 built | ✅ | ☐ | Do last (re-verify at CM) |

**Done-when for Phase D (from ROADMAP):** the world visibly progresses on its own (fresh, evolving
stories the news + DJs reference with correct past/now/future framing); conversations draw on a real
bible via semantic recall; sound design + emotion make it *sound* like a real station; a first-time
visitor hears enough depth to come back tomorrow.

**Plus an integrated acceptance gate (the D11 capstone runs it).** Beyond each pack's unit tests, Phase D
must pass one **end-to-end 24–48h simulation** (a runnable harness, accelerated clock): run tick → news →
freshness → grid → music/commercials across the window and assert — **no dead gaps** in the schedule,
**no repetition loops** (talk/news/music), **stories evolve** with correct past/now/future framing,
**cost stays bounded** (the telemetry rollup), and the **schedule output is sane** (durations, ordering,
program clocks). This is the local, simulated dress rehearsal *before* the C9 live 7-day soak.

## 5. Relationship to the Phase C server track (C5–C9)

Phase D code runs on the **local stack** and does not depend on the VPS (see PHASE_C_ORIENTATION §0).
Where D meets the server track: the **world tick is the "nightly batch"** the C5 cron/systemd runs
(D3 builds it as a callable job; C5 schedules it); the **status console + now-playing** (D6) is the
read-side of what C8's player surfaces; **emotion/voice** (D9) presumes the **C6 launch-voice
decision**. None of these block starting D — build against local Postgres + the chosen TTS now, and
the server track wires them to the box when it lands.

---

*How to use this file going forward:* when a sub-pack's dependencies are built, ask Claude (chat) to
generate the next `PHASE_D_<NAME>_TASKS.md` from this overview (the Goal/Builds/Docs/Seams/Depends
lines above are its brief), flip its tracker row to "pack written," build it task-by-task, then flip
"Built?" Keep this overview the single source of truth for sequencing.

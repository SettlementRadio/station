# ADMIN_MANUAL.md — operator how-tos (living draft)

> A running cookbook of *what an operator does* to run Settlement Radio. Each Phase D sub-pack
> appends its how-tos here as it's built (terse: what it does + the exact command/file/steps); the
> **D11 capstone** consolidates, simplifies, gap-fills, and verifies this into the final manual. Until
> then this is an append-only draft — keep entries short and command-first.

---

## D1 — The canon bible (`docs/canon/`)

**What it is.** The world bible is the [`docs/canon/`](canon/) folder of cornerstone markdown files —
the hand-authored *static substrate* the world is seeded from. The authoring contract (layout,
conventions, fact-id scheme, tags) is [`docs/canon/README.md`](canon/README.md). The DB is the
queryable projection; the folder is the source of truth.

### Edit the world bible
1. Edit / add files under `docs/canon/`. Filenames are `NN-stem.md` — `NN` sets reading order
   (sorted numerically; gaps are fine), `stem` names the file's facts (`canon-<stem>-N`).
2. Inside a file, three `## ` headings are special: `## Canon facts` (numbered list → facts),
   `## Cast` (`### Name` cards → DJs, in `90-cast.md`), `## Events` (`### Title` → timeline, in
   `95-events.md`). **Every other `## ` heading is narrative "series-bible" prose** the DJs read.
3. Required fields: each cast `### ` needs `- **Logical voice:**`; each event `### ` needs
   `- **In-world datetime:**` (ISO, in-world year = real + 600). Missing → seed fails loud.
4. Reload: `make seed-canon`.

### Add a new cornerstone file
Drop a new `NN-stem.md` in `docs/canon/` (unique stem). Scaffold files ship with guidance above the
first `## ` heading and an empty `## Canon facts` — they seed nothing until authored (see
`docs/canon/README.md` §7). Author by adding `## Topic` prose + a `## Canon facts` list, then
`make seed-canon`.

### Seed / refresh the world  ⚠ two commands
- **`make seed-canon`** — the SAFE everyday command. Reloads folder-owned `canon`/`cast`/bible and the
  `source='seed'` events, **leaving the living, tick-generated world (`source='tick'` events) intact**.
  Idempotent — run it after every bible edit. (`make seed` is a back-compat alias for this.)
- **`make reset-world`** — DESTRUCTIVE. Wipes the whole world+canon set (incl. tick-generated events)
  and rebuilds from the folder. Prompts: type `reset-world` to confirm (or pass `--force`
  non-interactively: `python -m src.world.seed reset --force`). **Never** touches station
  config/catalog (grid/tracks/sponsors).

### Point at a different bible (config)
`CANON_DIR` (folder, default `docs/canon`) and `CANON_PATH` (legacy single file, fallback). Seeding
auto-selects the folder when it has content, else the file. Set in `.env` only to relocate the bible.

### Verify a seed
```bash
make seed-canon          # logs per-table counts (canon / cast / events / state)
make context             # prints the assembled cached bible + dynamic now (no DB writes)
make demo                # event progression: "in five days" -> "yesterday"
```
To confirm tick-safety by hand: insert a `source='tick'` event, run `make seed-canon`, confirm it
survives; `make reset-world` clears it.

---

## D2 — Semantic retrieval / RAG (canon recalled by meaning)

**What it is.** The writers' room recalls canon by **meaning** (not just date/tag) via pgvector. The
embedding model is **local** (sentence-transformers, free, no key); all vector SQL is in `store.py`,
the model only behind `providers/embeddings.py`. Canon facts are embedded automatically on every seed.

### One-time setup (per machine)
1. **Python deps** (includes `sentence-transformers`): `pip install -r requirements.txt`. The model
   (`all-MiniLM-L6-v2`, ~80 MB) downloads once on first embed, then caches locally.
2. **pgvector extension** (Postgres-side; `init_schema` runs `CREATE EXTENSION vector` and fails loud
   without it). postgresql@17/@18: `brew install pgvector`. postgresql@14: build from source against
   pg14's `pg_config` — see README step 4.

### Use it / verify
```bash
make seed-canon   # embeds every canon fact into embeddings(corpus='canon'); logs embeddings_canon=N (== canon)
make context      # the dynamic slice now includes canon chosen by meaning (hybrid semantic + tag)
```
Manual meaning-recall check (returns canon ranked by meaning even for an off-tag topic):
```bash
python -c "from datetime import datetime; from src.world import context; \
print(context.assemble(datetime.now(), topic='loneliness', speakers='vell').dynamic)"
```

### Tag canon facts (sharpens the structured half of the hybrid)
In a `## Canon facts` item, add a child bullet `   - **Tags:** a, b, c` (lowercase single words — the
query side lowercases + splits on non-alphanumerics, so `Lumen-Festival` won't match `lumen`). Re-run
`make seed-canon`. Tags also let `store.canon_by_tags` narrow by topic.

### Config knobs (`.env`; defaults sane)
`EMBEDDINGS_PROVIDER` (`local`|`voyage`), `EMBEDDINGS_MODEL`, `EMBEDDINGS_DIM` (must match the model —
it's the `vector(N)` column; a change means re-embed + migration), `CONTEXT_CANON_TOP_K` (facts pulled
per topic). **Switching model:** change model+dim together, then `make seed-canon` to re-embed.

### Notes
- If pgvector/embeddings are unavailable, `retrieve()` returns `[]` and the room **degrades to
  structured retrieval** — no crash; check logs for `embeddings_retrieve_unavailable`.
- `make reset-world` clears the embeddings table (re-embedded on the rebuild); `make seed-canon`
  re-embeds only the `source='seed'` (canon) rows and leaves tick-generated vectors intact.

---

## D3 — The world engine (the nightly world tick)

**What it is.** A nightly job that makes the world *move on its own*: it invents new
bible-consistent **stories** (each an arc of dated **beats**) and **advances** running ones over
successive runs. All world state lives in `stories` + beat-linked `events` (`source='tick'`) in
[`src/world/store.py`](../src/world/store.py); the job is [`src/world/world_tick.py`](../src/world/world_tick.py).
It is the nightly batch the C5 cron/systemd timer runs — a **separate job** from `make schedule` (the
tick *writes* world state; the scheduler *reads* it to make audio).

### Run one tick
```bash
make world-tick                          # one tick: invent + advance world stories (Claude Batch)
LLM_BATCH_ENABLED=false make world-tick  # quick local run, synchronous (no async batch wait)
```
Prints a summary (proposed / accepted / dropped / duplicates; advanced / resolved) and the new +
advanced story ids. Needs `make seed` + a populated `.env`. One-shot by design; exits **non-zero** on
failure with the store left untouched (a tick is one transaction — it rolls back on any error).

### Warm up a fresh world (give it a living "now")
A freshly-seeded DB has no running stories. Run the tick a few times so there's a moving present for
the news/DJs (and for the C9 soak) to draw on:
```bash
make seed
LLM_BATCH_ENABLED=false make world-tick   # tick 1 — creates stories
LLM_BATCH_ENABLED=false make world-tick   # tick 2 — advances some of them (watch the summary)
```

### Schedule it (the box)
Run `make world-tick` (i.e. `python -m src.world.world_tick`) **nightly** from cron/systemd, independent
of the scheduler's top-up timer. Leave `LLM_BATCH_ENABLED=true` on the box for the 50% Batch discount.

### What survives a re-seed
Tick-generated stories/beats/events are the living world: `make seed-canon` (a bible edit) leaves them
**intact**; only `make reset-world` clears them. They are the irreplaceable asset C5 backs up.

### Config knobs (`.env`; defaults sane)
- **Counts/mix:** `WORLD_TICK_NEW_STORIES_MIN/MAX`, `WORLD_TICK_LARGE_RATIO`,
  `WORLD_TICK_BEAT_HORIZON_DAYS` (how far from "now" a beat may be dated).
- **Continuity/pacing:** `WORLD_TICK_ADVANCE_MAX` (running stories advanced per tick),
  `WORLD_TICK_RESOLVE_AFTER_TICKS` (steer old stories to resolution),
  `WORLD_TICK_MAX_ACTIVE_STORIES` (soft cap → propose no new stories when full).
- **Variety:** `WORLD_TICK_DOMAIN_WINDOW_TICKS`, `WORLD_TICK_QUIET_DOMAINS` (domain balance),
  `WORLD_TICK_DEDUP_THRESHOLD` (semantic) + `WORLD_TICK_DEDUP_JACCARD` (structural) de-dup.
- **Cost/model:** `WORLD_TICK_PROPOSE_TIER`/`_CONTINUITY_TIER`, `WORLD_TICK_MAX_ATTEMPTS`
  (regenerate-then-drop), and `LLM_BATCH_ENABLED` / `LLM_BATCH_POLL_INTERVAL_SEC` /
  `LLM_BATCH_MAX_WAIT_SEC` (the Batch path).

### Verify / inspect
```bash
LLM_BATCH_ENABLED=false make world-tick   # run twice; the 2nd should report advanced > 0
```
Inspect the story log the tick just wrote:
```bash
python -c "
from src.world import store
with store.connect() as c:
    s = store.active_stories(c)
    print([(x.arc_stage, x.title) for x in s])
    if s:
        print('beats:', [(b.beat_kind, b.in_world_datetime.isoformat())
                          for b in store.story_beats(c, s[0].id)])
"
```
Gate behaviour (a contradictory/unsafe proposal is regenerated once then dropped, never written) is
covered by `tests/test_world_tick.py`; run `pytest -q`.

---

## D4 — The news desk (reports the living world)

The `news` format no longer reads N flat headlines; it reads the **story log** (D3) and broadcasts it
like a real station — selecting a tagged mix of running stories each hour, recurring + evolving them
across the day with correct past/now/future framing, and staying self-consistent. Per-story **coverage
memory** (`news_coverage`) is what makes recurrence work; it survives `seed-canon` and is cleared by
`reset-world` (§2a). Nothing new to operate — the desk runs inside the normal scheduler/`make format`
path — but here is how to see it and tune it.

### See it (no tokens)
```bash
make news-demo     # a simulated day: one story goes breaking → repeated → evolved → past,
                   # another is steadily trailed. Deterministic; seeds + rolls back its own demo
                   # stories, so it never touches your world. Needs a reachable Postgres.
```
For a single **voiced** bulletin from the real world: `make format FMT=news` (Claude + TTS; needs
`make seed` + a couple of `make world-tick` runs so there are running stories to report).

### Config knobs (`.env`; defaults sane)
- **Selection mix:** `NEWS_STORY_COUNT` (stories per bulletin), `NEWS_TARGET_BREAKING/_TRAILED/_ONGOING`
  (soft per-kind quotas).
- **Timing windows:** `NEWS_BREAKING_WINDOW_HOURS` (a beat this close to now is "breaking"),
  `NEWS_TRAIL_HORIZON_DAYS` (how far ahead is still "trailed"), `NEWS_REPEAT_MAX_STALE_HOURS` (drop a
  repeat with no new beat older than this).
- **Canon grounding (D2):** `NEWS_CANON_RECALL_K`, `NEWS_CANON_WEIGHT` (degrades to temporal-only when
  RAG is off); rank lifts `NEWS_BREAKING_BONUS`, `NEWS_EVOLVE_BONUS`.
- **Continuity (D4.3):** `NEWS_CONTINUITY_MAX_ATTEMPTS` (drafts before evergreen), `NEWS_CONTINUITY_TIER`
  / `NEWS_CONTINUITY_ESCALATION_TIER`, `NEWS_CONTINUITY_MAX_TOKENS`.

### Inspect / verify
Show what the desk has covered (its memory):
```bash
python -c "
from src.world import store
with store.connect() as c:
    s = store.active_stories(c)
    if s:
        cov = store.last_coverage(c, s[0].id)
        print(s[0].title, '->', cov)   # None until a bulletin has reported it
"
```
Selection tagging, temporal framing, the safety + continuity gates (regenerate-then-evergreen), and
coverage recording are covered by `tests/test_news_select.py` + `tests/test_news_desk.py`; run
`pytest -q`.

---

## D10 — Figures & quotes (the world's people speak)

**What it does.** The world tick peoples each story with invented **figures** (the people it's about) and
their attributable, dated **quotes**. The news desk attributes them ("X, the relay-keeper, said
yesterday: …") and the writers' room surfaces a "what people are saying" slice the DJs react to. Stored in
the `figures` + `quotes` tables (behind `src/world/store.py`); generated inside the gated, batched tick, so
a flagged or off-canon figure/quote drops with its story. **Hard rule: invented in-world people only.**

### See it (no tokens)
```bash
make figures-demo        # seed one peopled story; print the news attribution + the DJ "what people
                         # are saying" slice. Deterministic, rolled back — never touches your world.
```
The GENERATED path is the tick itself — figures + quotes come out of `make world-tick` (above); a voiced
bulletin that attributes them is `make format FMT=news`.

### Config knobs (`.env`; defaults sane)
- **Generation (the tick):** `WORLD_TICK_FIGURES_ENABLED` (master toggle; false => people-less stories),
  `WORLD_TICK_FIGURES_PER_STORY_MAX` (3), `WORLD_TICK_QUOTES_PER_STORY_MAX` (4),
  `WORLD_TICK_ADVANCE_NEW_FIGURES_MAX` (reuse-vs-new: max new people an advancement adds, 1).
- **Attribution surfaces:** `NEWS_QUOTES_PER_STORY` (quotes per story in a bulletin brief; 0 disables),
  `CONTEXT_QUOTES_LIMIT` (quotes shown to the DJs; 0 disables), `CONTEXT_QUOTES_TOP_K` (semantic breadth).

### What survives a re-seed
Like the rest of the living world: **tick-generated** figures/quotes (`source=tick`) survive
`make seed-canon` and are cleared only by `make reset-world`; **bible-authored** ones (`source=bible`) are
re-seeded by `seed-canon`. (Bible-authored figures arrive via the canon folder — the seed path that loads
them is future work; the schema + split are in place now.)

### Inspect / verify
Show a story's people + what they said:
```bash
python -c "
from src.world import store
with store.connect() as c:
    s = store.active_stories(c)
    if s:
        for q, f in store.attributed_quotes_for_story(c, s[0].id):
            print(f'{f.name} ({f.role}) — {q.in_world_datetime:%Y-%m-%d}: {q.text}')
"
```
The schema/split, the tick's reuse + drop-the-flagged behaviour, and the news/talk attribution are covered
by `tests/test_figures_quotes.py` + additions to `test_world_tick.py` / `test_context.py` /
`test_news_desk.py`; run `pytest -q`.

---

## D5 — Freshness / anti-repetition (the station never loops itself)

A small **airplay memory** (`airplay_history`) records what aired recently — *features only* (a topic/beat
handle, an **opening fingerprint**, a few key phrases), never the audio — so the writers' room can steer the
next segment off recent ground: the showrunner avoids re-picking a recent beat, the talk + news producers
avoid reusing an opening. It is DISTINCT from D4's coverage memory: D4 drives *which* stories recur; D5 keeps
the *wording* fresh on top. Nothing new to operate — recording happens automatically at the scheduler
chokepoint and the reads happen inside the normal `make format` / scheduler path.

**Lifecycle (important):** the airplay memory **outlives the audio** — it is NOT collected by the C2.5 disk
GC (that would defeat the point); it is bounded by its OWN sweep (`FRESHNESS_WINDOW_HOURS ×
FRESHNESS_RETENTION_MARGIN`), folded into the top-up housekeeping. It **survives `make seed-canon`** and is
cleared only by `make reset-world` (§2a).

### See it (a few Claude calls, no TTS)
```bash
make freshness-demo   # four talk segments at an advancing clock, each steered off what aired before it;
                      # prints the growing avoid-list + a distinctness check. Needs ANTHROPIC_API_KEY +
                      # `make seed` (richer after `make world-tick`). Its airplay writes are rolled back.
```

### Config knobs (`.env`; defaults sane)
- **`FRESHNESS_ENABLED`** — master toggle (false = the writers' room ignores the memory).
- **`FRESHNESS_WINDOW_HOURS`** — the "recently on air" look-back (broadcast timeline). Keep it comfortably
  ABOVE `BUFFER_DEPTH_HOURS` so the whole upcoming buffer counts as recent. Default 6.
- **`FRESHNESS_MODE`** — `prefer` (soft nudge) vs `avoid` (hard don't-reuse). Default `prefer`.
- **`FRESHNESS_RECENT_LIMIT`** — how many recent topics/openings a prompt block shows. Default 6.
- **`FRESHNESS_RETENTION_MARGIN`** — the airplay sweep keeps rows for window × this, then drops them. Default 4.

### Inspect / verify
Show what the memory holds right now (most recent first):
```bash
python -c "
from datetime import datetime, timedelta
from src.world import store
with store.connect() as c:
    for r in store.recent_airplay(c, datetime.now(), within=timedelta(hours=24)):
        print(f'{r.aired_at:%m-%d %H:%M}  {r.format:<5} open={r.opening!r}  topic={r.topic!r}')
"
```
The store round-trip + window bounding + `reset`/`seed-canon` contract are in `tests/test_airplay.py`;
feature extraction + the prompt-block reads in `tests/test_freshness.py`; the prompt injection into the
showrunner/producer/news prompts in `test_conversation.py` / `test_news_desk.py`. Run `pytest -q`.

---

## D6 — Programming backbone + status console (the station is programmed, not a flat loop)

The station now runs a **weekly programming grid**: each in-world hour maps to a **named program**
(*The Long Night*, *First Light*, *Daywatch*, *Nightfall*) with its own **hosts**, **framing** (solo /
handover), and a **clock** — a real-radio-style format sequence with **run-lengths** (`music x3` = a
three-song sweep) and **pinned top-of-hour slots** (`news@:00`). The scheduler reads the grid at each
slot instead of cycling a flat rotation, and routes the program's hosts into generation (so day news is
anchored by the day host, etc.). Framing is driven by the active program (N hosts, not two hardcoded).

### Edit the grid (the human-edited source of truth)
The grid is a hand-edited YAML file — **the only thing you edit** (full management via a web editor is
Phase E). Workflow mirrors the bible: **edit → live** (no re-seed, no restart — it's mtime-reloaded).
```bash
$EDITOR docs/programming/grid.yaml     # add/rename a program, retune a clock, move a slot
```
Shape (see `docs/programming/README.md` for the full model — programs, the clock grammar, the tiling):
```yaml
programs:
  daywatch:
    name: "Daywatch"
    hosts: [wren, vell]              # cast ids (docs/canon/90-cast.md); hosts[0] = lead/anchor
    framing: solo                    # solo | handover | ensemble | legacy (the default program)
    clock: [talk, news@:00, talk]    # the hour-clock: sequence + run-lengths + pinned slots
grid:
  daily:                             # daily | weekdays | weekends | mon-fri | sat | mon,wed
    "07:00-20:00": daywatch          # weekday range -> HH:MM-HH:MM (may wrap midnight) -> program id
```
Rules the grid must respect: it should **tile the week with no gaps** (a reserved `default` program
backstops any hole so the scheduler never stalls), and each `stem`/program id is unique. Formats are the
`formats.FORMATS` keys (`talk`/`news`; `music` airs from D7). Markers (`sting`) are inert until D7.

### See it (token-free)
```bash
make programming-demo   # the weekly daypart map, the clock walking across the dawn boundary (pinned
                        # news landing on the hour), run-lengths, and the console + now-playing feed.
```

### Operator status console (private; read-only)
A CLI that shows the live station state — **operator-only, never internet-exposed** (opposite of the
public feed below). Reads existing state, mutates nothing.
```bash
make console            # or: python -m src.console
```
Panels: **on air / next** (program · format · hosts · duration), **buffer** runway (reuses the health
calc), **last run** heartbeat, the **D3 story log** (active stories + newest beats), and a **cost**
rollup (omitted until the jobs persist one). Degrades gracefully if the DB is down. This is distinct
from `make status`, which shows the playout processes + mount.

### Public now-playing feed (for the web player)
A small JSON the C8 web player reads — **public-safe fields only** (on-now / next + program + hosts +
the AI-disclosure line), never operator/internal state. The scheduler refreshes it on every top-up; run
it standalone to write + inspect:
```bash
make now-playing        # writes + prints segments/nowplaying.json
cat segments/nowplaying.json
```
The disclosure line is sourced from `src/disclosure.py` and kept identical to `web/src/lib/disclosure.ts`
(air and screen agree — a hard rule).

### Config knobs (`.env`; defaults sane)
- **`PROGRAMMING_ENABLED`** — master switch. `false` = rollback to the flat `BUFFER_ROTATION` (pre-D6);
  `true` = the grid drives what/who airs, and `BUFFER_ROTATION` becomes only the default program's mix.
- **`PROGRAMMING_GRID_PATH`** — the grid YAML (default `docs/programming/grid.yaml`).
- **`PROGRAMMING_DEFAULT_PROGRAM`** — the reserved never-stall fallback program id (default `default`).
- **`PROGRAMMING_CONSOLE_UPCOMING`** / **`CONSOLE_STORY_LIMIT`** / **`CONSOLE_BEATS_PER_STORY`** — console panel sizes.
- **`NOWPLAYING_FEED_PATH`** / **`NOWPLAYING_NEXT_COUNT`** — where the public feed is written + how many "next" items.

### What survives a re-seed
The grid is **config, not world**: `reset-world` leaves it alone (git is its backup); `seed-canon`
leaves it alone. It has no DB rows in Phase D — `program_for` reads the YAML directly (the DB-table
projection + `make seed-grid` land in Phase E when the web editor needs a write target).

### Inspect / verify
`program_for` boundaries + whole-week tiling and the generalised framing (two-host parity) are in
`tests/test_programming.py`; the scheduler airing the grid (clocks, pins, host routing) in
`tests/test_scheduler_grid.py`; the console + feed (read-only, public-safe allow-list) in
`tests/test_console.py` / `tests/test_nowplaying.py`. Run `pytest -q`.

## D7 — Production layer (jingles, beds, songs — the station sounds produced)

Layer 4 is live: curated **idents/themes/stings** air where the grid calls for them, **beds** duck
under speech, and **real songs** play in the `music` format with a DJ intro/back-announce that tells
each song's story. Code home: `src/production/` (media registry · mixer · placement · selector).

### The media folders (curated, GC-safe)
All curated audio lives under `assets/` — gitignored, backed up (C5), and **never** touched by the
disk GC (it only scans `segments/`): `assets/idents/`, `assets/themes/` (+ loopable `*_bed`
variants), `assets/stings/`, `assets/music/`, plus the fixed `assets/bed.mp3` (C4 playout fallback).
**Filenames are the contract** — the exact names live in `docs/JINGLE_PROMPTS.md` §4 and the
clip→placement registry in `src/production/media.py`. A registered clip whose file is missing is
skipped with a warning, never a crash.

### Register / update a song (the catalogue is yours, not generated)
```bash
$EDITOR config/tracks.yaml        # write the row: id/title/artist/album/era/mood/tags/story_blurb/
                                  #   audio_path (+ licence via licence_default or per-row)
cp <trimmed>.mp3 assets/music/<exact audio_path filename>.mp3
make seed-tracks                  # refresh the `tracks` table; probes real durations from the files
```
- A row whose file is absent loads as **lore only** (referenceable, not playable); dropping the file
  in later makes it playable immediately (playability is checked live — re-seed only to stamp its
  duration).
- The catalogue **survives `seed-canon` AND `reset-world`** (curated catalog, not world state);
  `make seed-tracks` is its only refresh. To **promote** a track, add the tag `featured` or `pinned`
  to its manifest row (+ re-seed) — the selector boosts it.

### What airs where (and the dials)
- **Program boundary** → the show's theme (handover shows get the B6 "passing the light" sting
  first). Dial: `PRODUCTION_THEME_AT_BOUNDARY` (true).
- **Before every news bulletin** → the C8 sting. Dial: `PRODUCTION_STING_BEFORE_NEWS` (true).
- **A1 sung station ident** every N content segments. Dial: `PRODUCTION_IDENT_EVERY_N` (8; 0=off).
  The C3 disclosure ident is separate and keeps airing.
- **Beds under speech** — doubly opt-in: `PRODUCTION_BEDDED_PROGRAMS` × `PRODUCTION_BEDDED_FORMATS`
  (default: `["long_night"]` × `["talk"]` — news always dry). Level: `PRODUCTION_BED_GAIN_DB`
  (−15 dB below the untouched speech), fade: `PRODUCTION_BED_FADE_SEC`. Baked at render; a mix
  failure airs the clean dry speech.
- **The music selector** — rule-based + deterministic (no LLM): daypart mood, world tone (story
  log), freshness (no repeat track/artist in the D5 window), era spread, featured/pinned. Weights:
  `MUSIC_SELECT_*` in `.env.example`. The slot with no playable track falls back to a spoken
  evergreen — a silent gap is impossible.

### Hear it / verify
```bash
make format FMT=music     # one full spin: intro → bumper → the track → back-announce (live calls)
make now-playing          # the public feed now carries track{title, artist, album, era}
pytest -q tests/test_production.py tests/test_selector.py tests/test_production_schedule.py
```
The D7 surgical tests cover the mixer's duration accounting + never-silence fallback, every selector
input + determinism, the music stitch order + lore-in-prompt, the grid placements, and the invariant
that `assets/` is never in the GC's candidate set.

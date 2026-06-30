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

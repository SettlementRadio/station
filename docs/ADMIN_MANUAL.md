# ADMIN_MANUAL.md — the operator manual

> **How to OPERATE Settlement Radio**, organised by operator task — every entry is a goal + the
> exact command/file/steps. Development (repo setup, generating segments by hand, tests, lint)
> lives in [`docs/HOWTO.md`](HOWTO.md).
>
> **Last verified:** 2026-07-07 (D11), against the local stack. **Re-verify at soft launch (CM),**
> when unattended operation begins: re-run the how-tos here, then bump this date.
>
> **Tag convention — `→ Phase E panel`:** any how-to that is a *hand-edit-a-file / re-run-a-seed / set
> an env dial* workflow carries this tag. These are deliberate interim mechanics; the Phase E operator
> control surface (ROADMAP "management / control surface") is built from exactly the tagged list —
> a missing tag is a missing panel feature.

---

## Running the station

Where it runs: the local Mac today; the VPS from **C5** (cron/systemd schedules the two jobs below).
All commands from the repo root; live-generation commands need a populated `.env`.

| Do | Command |
|---|---|
| Start the stream (top up the buffer + serve the playlist) | `make air` |
| Serve only (Icecast + Liquidsoap over the current playlist) | `make serve` |
| Stop playout (no orphans) | `make stop` |
| Playout processes + mount state | `make status` |
| Station state: on-air/next, buffer, story log, cost | `make console` |
| Health checks (non-zero exit when unhealthy) | `make health` |

**The recurring jobs** (cron/systemd on the box — C5; they are separate, don't fold them):
- **Scheduler top-up** — `make schedule` (one-shot, the cron shape; `make schedule INTERVAL=300`
  loops locally). Tops the rolling buffer up to `BUFFER_DEPTH_HOURS` of measured audio, rewrites
  `segments/playlist.txt` (Liquidsoap re-reads it, no restart), refreshes the public now-playing
  feed, and runs the disk GC + airplay sweep.
- **World tick, nightly** — `make world-tick`. *Writes* world state (stories/beats/events,
  figures/quotes); the scheduler *reads* it. Keep `LLM_BATCH_ENABLED=true` on the box (50% Batch
  discount). One-shot; exits non-zero on failure with the store untouched (one transaction).
- **Micro-tick, every 2–4h** — `make micro-tick` (R4.1). The light, near-live counterpart to the
  nightly tick: it may nudge ONE of *today's* live stories a small beat (a detail, a reaction, a
  complication) so the day evolves between nightly ticks, or do nothing — a quiet run is normal and
  common. Haiku-tier, direct (non-batch) path regardless of `LLM_BATCH_ENABLED`; runs in seconds;
  invents no new story, moves no arc, and never touches the schedule. Cron it a few times through
  the broadcast day (e.g. every 3h). Dials: `micro_tick_enabled` (kill switch),
  `micro_tick_advance_probability` (how often a run acts), `micro_tick_live_window_hours` (how recent
  a story's last beat must be to count as "live today"), `micro_tick_tier` / `micro_tick_max_tokens`
  / `micro_tick_continuity_max_tokens`. *→ Phase E panel: a "run micro-tick now" button beside the
  world screen (R5.2), and these dials on the dials screen (E1.5).*

**Playout assets** (each also runs automatically; the target is the standalone prepare/verify):
- `make fallback` — pre-render the never-dead fallback pool + evergreen playlist (auto at the top of
  every `make schedule`; `FORCE=1` re-renders).
- `make ident` — render the spoken AI-disclosure ident (woven in every `DISCLOSURE_EVERY_N` content
  segments — a hard rule, keep it airing; `FORCE=1` after editing the copy).
- `make prune` — GC aired, unreferenced segment audio (auto at the end of every `make schedule`).

---

## Seeding & the world (which command, when)

**The load-bearing rule: a bible edit is a canon refresh (`make seed-canon`) — NEVER a world wipe.**
`make reset-world` destroys the living, irreplaceable tick-generated world.

| Command | Touches | When |
|---|---|---|
| `make seed-canon` (alias: `make seed`) | SAFE — reloads folder-owned canon/cast/bible + `source='seed'` events, re-embeds canon; **tick state intact** | after every bible/roster edit; idempotent |
| `make reset-world` | ⚠ **DESTRUCTIVE** — wipes world+canon incl. everything tick-generated, then rebuilds from the folder; never touches grid/tracks/sponsors | dev resets only; type `reset-world` to confirm (non-interactive: `python -m src.world.seed reset --force`) |
| `make seed-tracks` | the `tracks` catalogue from `config/tracks.yaml` (probes durations) | after editing the music manifest |
| `make seed-sponsors` | the `sponsors` catalog from `config/sponsors.yaml` | after editing sponsors |
| *(no grid seed)* | the grid YAML is read live (mtime-reloaded) | edit → live |

### What persists vs resets
- **The living world** — tick-generated stories/beats/events, figures/quotes (`source='tick'`), news
  coverage, airplay memory: survives `seed-canon`; cleared ONLY by `reset-world`. **Irreplaceable —
  this is what gets backed up** (see Recovery).
- **Folder-owned canon/cast/seed-events**: replaced by `seed-canon`; git is the backup.
- **Config/catalog** — grid YAML, tracks, sponsors: survives BOTH seed-canon and reset-world; each
  has its own refresh; sponsors are hand-entered, back them up.
- **Embeddings**: derived — `reset-world` clears + re-embeds everything; `seed-canon` re-embeds only
  the canon rows and leaves tick-generated vectors intact.

### Run the world tick / warm up a fresh world
A freshly-seeded DB has no running stories; run the tick a few times so the news/DJs have a moving
present (tick dials: see *Tuning the living world*):
```bash
make seed-canon
LLM_BATCH_ENABLED=false make world-tick   # tick 1 — creates stories (synchronous, no batch wait)
LLM_BATCH_ENABLED=false make world-tick   # tick 2 — advances some of them (watch the summary)
```
The summary prints proposed / accepted / dropped / duplicates and advanced / resolved story ids.

### One-time setup per machine (embeddings)
1. **Python deps** (includes `sentence-transformers`): `pip install -r requirements.txt`. The local
   model (`all-MiniLM-L6-v2`, ~80 MB, free, no key) downloads once on first embed, then caches.
2. **pgvector** (Postgres extension; `init_schema` runs `CREATE EXTENSION vector` and fails loud
   without it). postgresql@17/@18: `brew install pgvector`; postgresql@14: build from source against
   pg14's `pg_config` — see README "pgvector".

If pgvector/embeddings are unavailable, retrieval returns `[]` and the writers degrade to structured
(date/tag) recall — no crash; look for `embeddings_retrieve_unavailable` in the logs.

**Embeddings dials** (`.env`; defaults sane)  → Phase E panel:
`EMBEDDINGS_PROVIDER` (`local`|`voyage`), `EMBEDDINGS_MODEL`, `EMBEDDINGS_DIM` (must match the model —
it's the `vector(N)` column; changing it means re-embed + migration), `CONTEXT_CANON_TOP_K` (facts per
topic). **Switching model:** change model+dim together, then `make seed-canon` to re-embed.

### Verify a seed
```bash
make seed-canon          # logs per-table counts (canon / cast / events / embeddings_canon=N)
make context             # prints the assembled cached bible + dynamic now (no DB writes)
make demo                # event progression: "in five days" -> "yesterday"
```
Meaning-recall check (returns canon ranked by meaning even for an off-tag topic):
```bash
python -c "from datetime import datetime; from src.world import context; \
print(context.assemble(datetime.now(), topic='loneliness', speakers='vell').dynamic)"
```
Tick-safety check by hand: insert a `source='tick'` event, run `make seed-canon`, confirm it
survives; `make reset-world` clears it.

---

## Authoring the bible (`docs/canon/`)

The world bible is the [`docs/canon/`](canon/) folder of cornerstone markdown files — the
hand-authored *static substrate* the world is seeded from. The authoring contract (layout,
conventions, fact-id scheme, tags) is [`docs/canon/README.md`](canon/README.md). The folder is the
source of truth; the DB is the queryable projection.

### Edit the world bible  → Phase E panel
1. Edit / add files under `docs/canon/`. Filenames are `NN-stem.md` — `NN` sets reading order
   (sorted numerically; gaps are fine), `stem` names the file's facts (`canon-<stem>-N`).
2. Inside a file, three `## ` headings are special: `## Canon facts` (numbered list → facts),
   `## Cast` (`### Name` cards → DJs, in `90-cast.md`), `## Events` (`### Title` → timeline, in
   `95-events.md`). **Every other `## ` heading is narrative "series-bible" prose** the DJs read.
3. Required fields: each cast `### ` needs `- **Logical voice:**`; each event `### ` needs
   `- **In-world datetime:**` (ISO, in-world year = real + 600). Missing → seed fails loud.
4. Reload: `make seed-canon`.

**Prompt-cache note (self-heals, no action):** the bible is the shared prompt-cache block every DJ
reads from (CO2). Editing `docs/canon/` changes those bytes, so the FIRST generation after a bible
edit pays a one-time cache write to re-warm the shared block; every generation after that reads it
cheaply again. That is expected — nothing to clear or restart. Cost visibility: the `cache_creation`
vs `cache_read` token split is logged on every call (`make costprobe` runs a repeatable before/after
probe). See [`docs/CACHE_OPTIMIZATION_TASKS.md`](CACHE_OPTIMIZATION_TASKS.md); the bible-block TTL dial
is `settings.llm_cache_bible_ttl` (`.env`)  → Phase E panel.

### Add a new cornerstone file  → Phase E panel
Drop a new `NN-stem.md` in `docs/canon/` (unique stem). Scaffold files ship with guidance above the
first `## ` heading and an empty `## Canon facts` — they seed nothing until authored (see
`docs/canon/README.md` §7). Author by adding `## Topic` prose + a `## Canon facts` list, then
`make seed-canon`.

### Tag canon facts (sharpens semantic recall)  → Phase E panel
In a `## Canon facts` item, add a child bullet `   - **Tags:** a, b, c` (lowercase single words — the
query side lowercases + splits on non-alphanumerics, so `Lumen-Festival` won't match `lumen`). Re-run
`make seed-canon`. Tags also let `store.canon_by_tags` narrow by topic.

### Add / edit / remove a DJ  → Phase E panel
1. Author/edit the card in `docs/canon/90-cast.md` (the `Logical voice` line is required;
   keep a few tick-DOMAIN words on the `Tags:` line — they drive that DJ's on-air memory
   affinity, see the file's intro). Set `- **Based:** field` for a travelling correspondent
   (default `station`): a field host is never written as live in the booth — the writers'
   room frames their segments as recorded dispatches across the relay lag, automatically,
   on whatever show the grid puts them. Give each card a distinct `Humour:` line too — it's
   part of what keeps the hosts from sounding like clones.
2. Add that voice to `config/voices.yaml` — one entry, all three engines (kokoro /
   elevenlabs / say). The file header documents picking presets.
3. `make seed-canon` — FAILS LOUD if a card names a voice the registry doesn't have.
4. To air them: schedule a program with their cast id in `docs/programming/grid.yaml`
   (read live, no seed step).

⚠ **Removing a DJ** = delete the card + `make seed-canon` (which truncates + reloads the `cast`
table from the folder, so the row is gone). SAFE: the card is git-tracked (restore + re-seed to bring
them back), and the DJ's tick-generated world history in the event log is NOT touched. A grid still
naming the removed id fails loud at generation and the slot falls back — never dead air. Pull the id
from `grid.yaml` too so nothing schedules them.

### Point at a different bible (config)
`CANON_DIR` (folder, default `docs/canon`) and `CANON_PATH` (legacy single file, fallback). Seeding
auto-selects the folder when it has content, else the file. Set in `.env` only to relocate the bible.

---

## Tuning the living world (tick · news · freshness · figures)

The world moves via the nightly tick (see *Running the station*); the news desk reports it, the
freshness memory keeps the wording from looping, and figures/quotes make it speak. All dials in
`.env`, defaults sane.

### See it (token-free or cheap; none touch your world)
```bash
make news-demo        # a simulated day: one story breaking → repeated → evolved → past, one trailed
                      # (deterministic, token-free; seeds + rolls back its own demo stories)
make figures-demo     # one peopled story: news attribution + the DJ "what people are saying" slice
                      # (deterministic, token-free, rolled back)
make freshness-demo   # four talk segments steered off each other; prints the growing avoid-list
                      # (a few Claude calls, no TTS; airplay writes rolled back)
make format FMT=news  # one voiced bulletin from the REAL world (Claude + TTS; needs seeded DB +
                      # a couple of world-tick runs so there are stories to report)
```

### Tune the world tick  → Phase E panel
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

A contradictory/unsafe proposal is regenerated once then dropped, never written (the C0 gates).

### Tune the news desk  → Phase E panel
- **Selection mix:** `NEWS_STORY_COUNT` (stories per bulletin), `NEWS_TARGET_BREAKING/_TRAILED/_ONGOING`
  (soft per-kind quotas).
- **Timing windows:** `NEWS_BREAKING_WINDOW_HOURS` (a beat this close to now is "breaking"),
  `NEWS_TRAIL_HORIZON_DAYS` (how far ahead is still "trailed"), `NEWS_REPEAT_MAX_STALE_HOURS` (drop a
  repeat with no new beat older than this).
- **Living day (R4.2):** `NEWS_STORY_COUNT_SHORT` (lean bulletin size for a short program's hourly
  news pin — a flagship/desk runs the full `NEWS_STORY_COUNT`); `NEWS_TRAIL_MAX_STALE_HOURS` (the
  longer staleness a *trailed* countdown gets so it recurs day to day instead of going cold at the
  ordinary 18h); `NEWS_TRAIL_PROXIMITY_BONUS` (rank lift as an upcoming event nears — closer = more
  coverage); `NEWS_DAYSUMMARY_START_HOUR`/`_END_HOUR` (the in-world window whose bulletin closes with
  a "the day so far" wrap — the drive desk).
- **Canon grounding:** `NEWS_CANON_RECALL_K`, `NEWS_CANON_WEIGHT` (degrades to temporal-only when
  RAG is off); rank lifts `NEWS_BREAKING_BONUS`, `NEWS_EVOLVE_BONUS`.
- **Continuity:** `NEWS_CONTINUITY_MAX_ATTEMPTS` (drafts before evergreen), `NEWS_CONTINUITY_TIER`
  / `NEWS_CONTINUITY_ESCALATION_TIER`, `NEWS_CONTINUITY_MAX_TOKENS`.

Per-story coverage memory (`news_coverage`) drives recurrence; it survives `seed-canon`, cleared by
`reset-world`.

### Tune freshness / anti-repetition  → Phase E panel
- **`FRESHNESS_ENABLED`** — master toggle (false = the writers ignore the memory).
- **`FRESHNESS_WINDOW_HOURS`** — the "recently on air" look-back (broadcast timeline). Keep it
  comfortably ABOVE `BUFFER_DEPTH_HOURS` so the whole upcoming buffer counts as recent. Default 6.
- **`FRESHNESS_MODE`** — `prefer` (soft nudge) vs `avoid` (hard don't-reuse). Default `prefer`.
- **`FRESHNESS_RECENT_LIMIT`** — how many recent topics/openings a prompt block shows. Default 6.
- **`FRESHNESS_RETENTION_MARGIN`** — the airplay sweep keeps rows for window × this. Default 4.

The airplay memory records *features* only (topic/beat handle, opening fingerprint, key phrases —
never audio), outlives the audio (it is NOT collected by the disk GC; its own sweep bounds it), and
is DISTINCT from news coverage: coverage drives *which* stories recur, freshness keeps the *wording*
fresh. Survives `seed-canon`; cleared by `reset-world`.

### Tune figures & quotes  → Phase E panel
- **Generation (the tick):** `WORLD_TICK_FIGURES_ENABLED` (master toggle; false => people-less
  stories), `WORLD_TICK_FIGURES_PER_STORY_MAX` (3), `WORLD_TICK_QUOTES_PER_STORY_MAX` (4),
  `WORLD_TICK_ADVANCE_NEW_FIGURES_MAX` (reuse-vs-new: max new people an advancement adds, 1).
- **Attribution surfaces:** `NEWS_QUOTES_PER_STORY` (quotes per story in a bulletin brief; 0
  disables), `CONTEXT_QUOTES_LIMIT` (quotes shown to the DJs; 0 disables), `CONTEXT_QUOTES_TOP_K`
  (semantic breadth).

**Hard rule: invented in-world people only.** Tick-generated figures/quotes (`source='tick'`)
survive `seed-canon`; bible-authored ones (`source='bible'`) are re-seeded by it. (The seed path
that loads bible-authored figures is future work; the schema + split are in place.)

---

## Programming the grid

The station runs a **weekly programming grid** (the GRID_V2 speech-station week — the signed-off
design lives in `docs/programming/GRID_V2.md`, R2): **two 2-hour flagships** (breakfast 07–09,
drive 18–20) restructured into fast 3–5-minute items around `news@:00`/`news@:30` pins, and
**everything else daytime ≤30 minutes at the same time every day** — magazines, twice-daily
Conditions + Ledger updates, sport, the daily chart, dispatches, letters, the nightly 15-minute
Serial at 20:00. **Five rotating vertical windows** (09:30 / 10:00 / 13:30 / 14:00 / 14:30 — each
vertical owns ONE canonical time; the weekday pattern picks its days) plus the **15:30 weekly
belt** carry the subject verticals (politics, economy, conflict, law, science, travel, health,
style, story, history, the relay…). The night (20:15–07:00) is untouched. Each program is
**named**, with **hosts**, **framing** (solo / handover / ensemble), and a **clock** (a format
sequence with run-lengths `music x3` and pinned slots `news@:00`). Two format rules matter:
**`talk` is a two-DJ conversation (needs ≥2 hosts, lead first)**; **`news` is read by the
dedicated news desk (Thorn), not the show's host** — the bulletin cuts in on the hour and hands
back. An interview/dispatch show sets its own guest cadence (`guest_chance`); a solo-desk show
sets none.

### Edit the grid  → Phase E panel
The grid is a hand-edited YAML — **the only thing you edit** (a web editor is Phase E). Workflow
mirrors the bible: **edit → live** (no re-seed, no restart — mtime-reloaded).
```bash
$EDITOR docs/programming/grid.yaml     # add/rename a program, retune a clock, move a slot
```
Shape (full model — programs, the clock grammar, the tiling — in `docs/programming/README.md`):
```yaml
programs:
  the_gallery:
    name: "The Gallery"              # cast ids (docs/canon/90-cast.md); hosts[0] = lead/anchor
    hosts: [mira, orin]              # `talk` needs ≥2 hosts; a music show needs exactly 1
    framing: ensemble               # solo | handover | ensemble | legacy (the default program)
    clock: [talk, talk, news@:00, talk, music]   # sequence + run-lengths + pinned slots
    break_every: 5                   # ad-break cadence (see Commercials; absent/0 = no breaks)
    guest_chance: 0.8                # 0..1 — how often this talk show runs a guest/played record
    energy: steady                   # R1: delivery pace — calm | steady | bright (calm = the night's
                                     # lyric register; steady/bright = the plain daytime register;
                                     # also picks the A4 sweeper tier, R2.3)
    talk_length_sec: 420             # R2.2: this show's talk-ITEM length (flagships 240, 30-min
                                     # specialists 420, 15-min desks 180; absent = the global
                                     # default). Scales the word budget — length is a parameter.
    brief: >-                        # R1: the editorial identity — 2-4 sentences, concrete stakes,
      The arts as event: an opening, a premiere, a feud between schools.   # an explicit "never" line;
      Never hushed-gallery reverence.                                      # reaches the writers' room
                                                                           # as the ON THIS SHOW block
grid:
  daily:                             # daily | weekdays | weekends | mon-fri | sat | mon,wed
    "07:00-20:00": the_gallery       # weekday range -> HH:MM-HH:MM (may wrap midnight) -> program id
  mon: { "14:00-16:00": the_workshop }  # a per-day key (narrower) overrides `weekdays`/`daily`
```
Rules: the grid should **tile the week with no gaps** (the reserved `default` program backstops any
hole — the scheduler never stalls); each program id is unique; formats are the `formats.FORMATS`
keys (`talk`/`news`/`music`). Marker tokens in a clock (`sting`/`bed`/`ident`) are accepted but
skipped by the scheduler — actual sting/bed/ident placement is dial-driven (see *Music & culture*).
**Music is short by design** — the catalogue is ~2.5h total, so keep music to short features (a
30-min top-5, a weekend hour), never multi-hour blocks that would just repeat.
**Briefs are the editorial steering wheel (R1):** every non-default program should carry `brief` +
`energy` — they reach the showrunner/orchestrator as the "ON THIS SHOW" block, scope the beat pick,
and set the register (daytime plain, night lyric). Edits go live on the next top-up like any grid
edit; the `plain_register` property in `make acceptance` guards the daytime register.

### See it (token-free)
```bash
make programming-demo   # the weekly daypart map, the clock walking across the dawn boundary (pinned
                        # news landing on the hour), run-lengths, and the console + now-playing feed
```

### Dials (`.env`; defaults sane)  → Phase E panel
- **`PROGRAMMING_ENABLED`** — master switch. `false` = rollback to the flat `BUFFER_ROTATION`
  (pre-D6); `true` = the grid drives what/who airs (`BUFFER_ROTATION` is only the default
  program's mix).
- **`PROGRAMMING_GRID_PATH`** — the grid YAML (default `docs/programming/grid.yaml`).
- **`PROGRAMMING_DEFAULT_PROGRAM`** — the reserved never-stall fallback program id (`default`).
- **`NEWS_ANCHOR_IDS`** — the dedicated news desk (default `["thorn"]`): every `news` bulletin is
  read by this anchor, independent of the show on air. Empty = the show's lead reads its own bulletin
  (the pre-D12.4 behaviour).

The grid is **config, not world**: both `seed-canon` and `reset-world` leave it alone; git is its
backup. No DB rows in Phase D (`make seed-grid` + the DB projection land in Phase E).

### Talk continuity / show flow (D12)  → Phase E panel
Consecutive talk segments in one program play as **one flowing show**, not N mini-shows: the show
opens once (a spoken sign-on by name), the middle segments come in **cold** and carry the same thread
forward, a settlement-time check fires only occasionally, and it signs off once at the end. It's
best-effort context layered on the atomic segment — a missing hand-off just opens the next segment
standalone.
- **`CONVO_CONTINUITY_ENABLED`** — master toggle (default `true`). `false` = the pre-D12 shape (every
  talk segment self-contained, opens + closes) — the clean rollback.
- **`CONVO_CONTINUITY_MAX_SEGMENTS`** — how many consecutive talk segments one thread may hold
  (opener included) before a forced transition to a fresh subject (default `3`). A continuing
  thread carries a covered-beats list (so it advances instead of circling), and a transition slot
  is told the OLD topic so the hosts pivot off it in half a line instead of silently dropping it.
- **`CONVO_CONTINUITY_HANDOFF_MAX_AGE_MIN`** — how old (minutes of air time) a persisted talk
  hand-off may be and still be continued (default `60`; `0` disables). Protects a restart after
  downtime from resuming yesterday's conversation mid-sentence.
- **`CONVO_FLOW_TIMECHECK`** — when a spoken time-check is allowed: `never | handover | open | hourly`
  (default `hourly` — the top of the hour + handovers, not every segment).
- **`CONVO_FLOW_SIGNON`** — spoken program sign-on/sign-off by name at a show's first/last slot
  (default `true`).
- **`CONVO_FLOW_SHORT_SHOW_MAX_MIN`** — R2.3: a show whose grid slot runs at most this many
  minutes signs on/off in **one line** (a breath, not a ceremony — a 30-min fixture can't spend
  itself on hellos). Default `45`; the 2h flagships keep the fuller welcome; `0` disables.
- **`CONVO_GUEST_CHANCE`** — the *global* guest/interview rate; a program's own `guest_chance` (grid)
  overrides it per show.

See it (a few Claude calls, no TTS, writes nothing):
```bash
make continuity-demo    # 5 consecutive talk slots of one show, scripts back-to-back:
                        # one sign-on, cold middles that carry the thread, one close
```

---

## Music & culture

Layer 4: curated **idents/themes/stings** air where the grid calls for them, **beds** duck under
speech, and **real songs** play in the `music` format with a DJ intro/back-announce that tells each
song's story. Code home: `src/production/` (media registry · mixer · placement · selector).

### The media folders (curated, GC-safe)
All curated audio lives under `assets/` — gitignored, backed up (C5), and **never** touched by the
disk GC (it only scans `segments/`): `assets/idents/`, `assets/themes/` (+ loopable `*_bed`
variants), `assets/stings/`, `assets/music/`, plus the fixed `assets/bed.mp3` (C4 playout fallback).
**Filenames are the contract** — the exact names live in `docs/JINGLE_PROMPTS.md` §4 and the
clip→placement registry in `src/production/media.py`. A registered clip whose file is missing is
skipped with a warning, never a crash.

### Register / update a song  → Phase E panel
```bash
$EDITOR config/tracks.yaml        # write the row: id/title/artist/album/era/mood/tags/story_blurb/
                                  #   audio_path (+ licence via licence_default or per-row)
cp <trimmed>.mp3 assets/music/<exact audio_path filename>.mp3
make seed-tracks                  # refresh the `tracks` table; probes real durations from the files
```
- A row whose file is absent loads as **lore only** (referenceable, not playable); dropping the file
  in later makes it playable immediately (playability is checked live — re-seed only to stamp its
  duration).
- The catalogue **survives `seed-canon` AND `reset-world`**; `make seed-tracks` is its only refresh.
- To **promote** a track, add the tag `featured` or `pinned` to its manifest row (+ re-seed) — the
  selector boosts it.

### What airs where (the dials)  → Phase E panel
- **Program boundary** → the show's theme (handover shows get the B6 "passing the light" sting
  first). Dial: `PRODUCTION_THEME_AT_BOUNDARY` (true).
- **Before every news bulletin** → the C8 sting. Dial: `PRODUCTION_STING_BEFORE_NEWS` (true).
- **Between items inside the fast-clock shows** → the A4 sweeper, energy-matched via the
  program's `energy` (calm|steady|bright → the A4 tier; daypart fallback). Dial:
  `PRODUCTION_SWEEPER_PROGRAMS` (default the two flagships; empty list = no sweepers). Never at
  a boundary (the theme owns that join) and never around a break (the D18 pair owns those) —
  R2.3.
- **A1 sung station ident** every N content segments. Dial: `PRODUCTION_IDENT_EVERY_N` (8; 0=off).
  The C3 disclosure ident is separate and keeps airing.
- **Beds under speech** — doubly opt-in: `PRODUCTION_BEDDED_PROGRAMS` × `PRODUCTION_BEDDED_FORMATS`
  (default: `["long_night"]` × `["talk"]` — news always dry). Level: `PRODUCTION_BED_GAIN_DB`
  (−15 dB below the untouched speech), fade: `PRODUCTION_BED_FADE_SEC`. Baked at render; a mix
  failure airs the clean dry speech.
- **The music selector** — rule-based + deterministic (no LLM): daypart mood, world tone (story
  log), freshness (no repeat track/artist in the freshness window), era spread, featured/pinned.
  Weights: `MUSIC_SELECT_*` in `.env.example`. A slot with no playable track falls back to a spoken
  evergreen — a silent gap is impossible.

### Hear it / verify
```bash
make format FMT=music     # one full spin: intro → bumper → the track → back-announce (live calls)
make now-playing          # the public feed now carries track{title, artist, album, era}
pytest -q tests/test_production.py tests/test_selector.py tests/test_production_schedule.py
```

---

## Commercials & sponsors

In-world ad breaks — a `commercial` (fictional +600y product spot) or `promo` (station self-promo)
**generated fresh every airing** (never a prerecorded reel), placed sparsely by the grid and
bracketed by the break stings — plus real supporter **"Powered by" reads** from the `sponsors`
table (empty until CM). Spots run the C0 gate + evergreen fallback like every producer.

### Generate a spot by hand
```bash
.venv/bin/python -m src.formats commercial    # one fictional product spot (live calls)
.venv/bin/python -m src.formats promo         # one station promo (names the current grid show)
make commercials-demo                         # spots + the break walk + a sponsor-read demo
```

### Tune the ad load  → Phase E panel
- **Which shows take breaks, how often** — `break_every: N` per program in
  `docs/programming/grid.yaml` (absent/0 = no breaks). Shipped: daywatch 4, long_night 6,
  handovers + default none. Edit → live (the grid reloads on change).
- **Break shape** — `.env`: `COMMERCIAL_BREAK_ENABLED` (true), `COMMERCIAL_BREAK_MAX_SEGMENTS`
  (1 — spots per break), `COMMERCIAL_BREAK_PROMO_EVERY_N` (3 — every Nth spot is a promo; 0=never).
- **Spot length/voice/production** — `.env`: `FORMAT_COMMERCIAL_WORDS_LOW/HIGH` (55/90),
  `FORMAT_COMMERCIAL_SPEAKER_ID` (vell), `FORMAT_COMMERCIAL_PRODUCTION_LEVEL` (1; 2=bedded read,
  3=testimonial via voice+figures, 4=brand-sting bookend once the clip exists — unbuilt levels
  degrade to 1, the effective level is in the segment meta).

### Manage sponsors ("Powered by" reads)  → Phase E panel
1. Edit `config/sponsors.yaml` — id, name, `powered_by_text` blurb, optional `audio_path`
   (supplied clip under `assets/sponsors/`), `run_start`/`run_end` (real dates, half-open window),
   `weight` (rotation share). **Leave empty until CM (donations live).**
2. `make seed-sponsors` — refreshes the table (catalog: survives `seed-canon`/`reset-world`).
   ⚠ It **clears + replaces** the whole `sponsors` table from the file, so the YAML is the source of
   truth: to remove a sponsor, delete its row and re-seed; emptying the file wipes every read. SAFE:
   sponsors are hand-entered + git-tracked (and in the DB backup, §Recovery) — restore from either.
3. Reads air inside every `SPONSOR_READ_EVERY_N_BREAKS`-th break (2; 0=off), voice
   `SPONSOR_READ_VOICE` (vell_night), only within the run window. An empty table airs nothing.

**Wording is binding:** always **"Powered by"**, never "Sponsored by" (`docs/MARKETING.md`). The
lead-in is templated in `src/formats/sponsor.py`; a "sponsored by" blurb is auto-corrected + logged.

### Verify
```bash
pytest -q tests/test_commercials.py    # builder, gate fallback, cadence+cap, run window, wording
```

---

## Voice

Roster changes (add/edit/remove a DJ) live under *Authoring the bible* — a cast card is bible.

### Fix a mispronounced invented name  → Phase E panel
Edit `config/pronunciation.yaml` (`respell` = any engine; `phonemes` = exact Kokoro sound,
misaki alphabet — see the header). Applies on the next render, no restart. Unknown names
pass through unharmed. Off switch: `TTS_LEXICON_ENABLED=false`.

### Tune emotion  → Phase E panel
- Writers tag turns themselves (`Vell [somber]:` — vocabulary: warm | wry | somber | bright |
  urgent); un-tagged turns take the daypart mood floor (`_PART_OF_DAY_EMOTION`,
  writers/conversation.py), then `.env` `TTS_EMOTION_DEFAULT` ("" = engine default).
- AUDIBLE only on `TTS_PROVIDER=elevenlabs` (Kokoro has no emotion knob) — which engine
  ships is the C6 decision; C6 also retunes the per-emotion curves (`_ELEVENLABS_EMOTIONS`,
  providers/tts.py) by ear and confirms the 8 new DJs' premade voice ids.

### Guests / soundbites  → Phase E panel
`.env`: `CONVO_GUEST_ENABLED` (true), `CONVO_GUEST_CHANCE` (0.2 — share of talk slots; the
draw is per-slot deterministic). A figure with a quote airs as a soundbite in its own
stable voice (`guest_*` pool in `config/voices.yaml`; a `figures.voice_id` naming a registry
voice wins); no figures = a one-off invited persona. Hosts always open and close (gated).

### DJ memory  → Phase E panel
`.env`: `CONVO_MEMORY_ENABLED` (true), `CONVO_MEMORY_PER_HOST` (3), `CONVO_MEMORY_WINDOW_DAYS`
(60 — the look-back). A host prefers stories whose tags overlap their card tags; the
continuity editor sees the same block, so misremembering re-rolls the draft.

### Self & interpersonal memory — the journal (D13)  → Phase E panel
The hosts' durable record of what THEY said on air (opinions, personal details, running bits,
host-to-host exchanges): captured post-air by one `haiku` call per scheduled talk segment,
recalled into future segments, and enforced by the continuity editor (a host reversing a
journaled stance re-rolls the draft). **The card always wins** — the journal never overrides
`docs/canon/90-cast.md`; to canonise a journaled detail, edit the card by hand.

- **Dials (`.env`):** `CONVO_JOURNAL_ENABLED` (true — `false` is the clean pre-D13 rollback:
  no capture, no recall, no editor check), `CONVO_JOURNAL_TIER` (haiku),
  `CONVO_JOURNAL_MAX_ENTRIES_PER_SEGMENT` (4 — capture bound),
  `CONVO_JOURNAL_MAX_DETAILS_PER_HOST` (12 — the bounded-biography cap; oldest details drop),
  `CONVO_JOURNAL_PER_HOST` (3) / `CONVO_JOURNAL_WINDOW_DAYS` (30) / `CONVO_JOURNAL_TOP_K`
  (8 — recall bounds; top_k=0 turns off the semantic blend).
- **See it (cheap, cleans up after itself):** `make journal-demo` — two talk slots "air" and
  are journaled, then a day later the hosts write WITH the journal; read day 2 for the callback.
- **Inspect:** `make console` (the HOST JOURNAL panel: entries per host), or read-only SQL:
  `psql "$DATABASE_URL" -c "SELECT host_id, kind, text, air_time FROM host_journal ORDER BY
  air_time DESC LIMIT 20"`.
- **Prune one bad entry:** `psql "$DATABASE_URL" -c "DELETE FROM host_journal WHERE id = <id>"`
  then clear its vector: `DELETE FROM embeddings WHERE corpus='journal' AND entity_id='<id>'`.
  (The per-host detail cap prunes automatically; this is for a wrong/unwanted memory.)
- **Lifecycle:** runtime accrual — survives `seed-canon`, cleared by `reset-world`, backed up
  with the world DB (§2a). Only AIRED segments journal; `make conversation`/`make format`
  never do.

### Verify
```bash
pytest -q tests/test_tts_emotion.py tests/test_lexicon.py tests/test_voices.py \
          tests/test_guest.py tests/test_memory.py tests/test_journal.py
.venv/bin/python -m src.formats talk   # a talk segment; logs show emotion/memory/guest per slot
make journal-demo                      # the D13 loop end-to-end on paper (air → recall → callback)
```

---

## Status & monitoring

### The operator console (private; read-only)
```bash
make console            # or: python -m src.console
make timeline           # its web sibling: http://127.0.0.1:8010/ (loopback ONLY)
```
The **timeline** page auto-refreshes: what's ON AIR (with progress), the generated
segments queued next, and the grid's intended program blocks for the hours ahead —
the side-by-side view for listening tests. Read-only; binds 127.0.0.1; never expose.
`TIMELINE_PORT` moves the port.  → Phase E panel
Panels: **on air / next** (program · format · hosts · duration), **buffer** runway (the health
calc), **last run** heartbeat, the **story log** (active stories + newest beats), the **host
journal** (D13 — entries accrued per host), and a **cost** rollup (omitted until the jobs
persist one). Reads existing state, mutates nothing; degrades
gracefully if the DB is down. **Operator-only, never internet-exposed.** Distinct from
`make status`, which shows the playout processes + mount. Panel sizes:
`PROGRAMMING_CONSOLE_UPCOMING` / `CONSOLE_STORY_LIMIT` / `CONSOLE_BEATS_PER_STORY`.

### The public now-playing feed
The small JSON the web player reads — **public-safe fields only** (on-now / next + program + hosts +
track info + the AI-disclosure line), never operator/internal state. The scheduler refreshes it on
every top-up; standalone:
```bash
make now-playing        # writes + prints segments/nowplaying.json
```
Dials: `NOWPLAYING_FEED_PATH` / `NOWPLAYING_NEXT_COUNT`. The disclosure line comes from
`src/disclosure.py` and is kept identical to `web/src/lib/disclosure.ts` (air and screen agree —
a hard rule).

### Health & logs
- `make health` — buffer depth / last scheduler run / stream liveness; logs + optional
  webhook/uptime ping; exits non-zero when unhealthy (so a cron timer can act on it).
- Playout logs: `.run/icecast.log`, `.run/liquidsoap.log`. Pipeline jobs log structured JSON to
  the console (readable form: `LOG_JSON=false`; verbosity: `LOG_LEVEL=debug|info|warning|error`).

### Pre-launch dress rehearsal (the acceptance gate)
The integrated 24–48h simulation — the Phase-D gate to run before the C9 live soak and after any
change to the spine. It drives the real pipeline (world tick → news → freshness → grid →
music/commercials) across an accelerated window and asserts five properties: **no dead gaps · no
repetition loops · stories evolve · cost bounded · schedule sane**.
```bash
make acceptance            # 24h window; make acceptance HOURS=48 for the wider run
```
- **No cost, no live calls, non-destructive:** the model + TTS seams are mocked, and the whole
  simulated world runs in one rolled-back transaction — it never touches your world or schedule.
  Needs a reachable Postgres. Exits non-zero and names the failing property + reason on any failure.
- The same checks run in CI as `tests/test_acceptance.py` (each property is unit-tested both ways
  plus a short end-to-end run). Debug a failure with `--dump PATH` to write the placed timeline JSON:
  `.venv/bin/python -m src.acceptance --hours 24 --dump /tmp/timeline.json`.

### Jingle placement audit (R3.0)
Proof, not assumption, that every curated clip (idents/themes/stings) fires where and when it
should — run it after any grid change (new/moved programs) and before dropping in a new jingle
batch (R3.1's JINGLE_PROMPTS_3).
```bash
make jingle-audit                    # 48h window; JINGLE_HOURS=72 for a wider run
make jingle-audit DUMP=/tmp/t.json   # also dump the placed timeline JSON
```
- Prints a **mapping table** — every grid program → the clip it actually resolves to (`override` /
  `bespoke` / `fallback` / `missing`), straight from the `placement.py` code path an operator can
  eyeball for reuse choices (`the_mailbag` → `c11_letters.mp3`, etc.) and spot which programs are
  still on a format fallback (`c9_talk.mp3`/`c7_news.mp3`) and so belong on the next jingle batch's
  list.
- Then asserts five DYNAMIC properties over a simulated week driven through the real scheduler:
  every program boundary got its theme, every `news@` pin got the C8 sting immediately before it,
  every handover got the B6 sting before its theme, every ad break got the D18 in/out bracket, and
  no theme repeats back-to-back (two adjacent programs sharing a fallback clip skip the second
  play rather than repeat it — see `placement.program_theme_segment`'s `avoid_repeat`).
- Same isolation as `make acceptance` (mocked seams, one rolled-back Postgres transaction, no live
  calls, no cost); reads your REAL `assets/` tree for the static mapping, so it also proves a
  freshly-dropped clip actually resolves. `tests/test_jingle_audit.py` covers the same checks unit
  + end-to-end in CI.

### Peek inside the world (read-only snippets)
The story log the tick wrote:
```bash
python -c "
from src.world import store
with store.connect() as c:
    s = store.active_stories(c)
    print([(x.arc_stage, x.title) for x in s])
    if s:
        print('beats:', [(b.beat_kind, b.in_world_datetime.isoformat(), b.planned)
                          for b in store.story_beats(c, s[0].id)])
"
```
A beat with `planned=True` (R4.0) is part of a **same-day arc**: the tick wrote it last night as the
plan for later today, and the news desk will not report it until its hour passes. `make console`
labels these `(planned)` in the story log. This is the ONE place the operator sees more than the air
does — everything on-air goes through `events.airable`, so a planned beat can never air early. Dials:
`world_tick_dayarc_stories_max` / `world_tick_dayarc_beats_max` (set stories to 0 to stop the tick
planning day arcs at all). *→ Phase E panel: the world screen (R5.2) shows arcs in flight + today's
expected beat timeline; these dials belong on the dials screen (E1.5).*
What the news desk has covered (its recurrence memory):
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
What the freshness memory holds (most recent first):
```bash
python -c "
from datetime import datetime, timedelta
from src.world import store
with store.connect() as c:
    for r in store.recent_airplay(c, datetime.now(), within=timedelta(hours=24)):
        print(f'{r.aired_at:%m-%d %H:%M}  {r.format:<5} open={r.opening!r}  topic={r.topic!r}')
"
```
A story's people + what they said:
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

---

## Recovery

### The stream sounds wrong / dead
It shouldn't be silent: an empty or stale playlist airs the **never-dead fallback** (evergreen pool
+ disclosure ident) automatically — dead air self-heals. Check, in order:
1. `make status` — are Icecast + Liquidsoap up, is the mount live? If not: `make serve` (it always
   stops stale processes first).
2. `make health` — buffer depth / last-run heartbeat / stream liveness, with reasons.
3. `.run/liquidsoap.log`, `.run/icecast.log` — playout errors.
4. If the fallback assets themselves are missing: `make fallback` (re-prepare; `FORCE=1` re-renders).

### The buffer drains / a top-up failed
`make health` says why. Run `make schedule` by hand and read its output — generation failures fall
back to evergreen segments (never silence, never a crash-loop). A failed run leaves the previous
playlist airing; fix the cause (API key, DB up, disk) and re-run.

### The world tick failed / went wrong
The tick is one transaction: on any error it exits non-zero and the store is untouched — safe to
just re-run. To bisect batch-vs-generation problems: `LLM_BATCH_ENABLED=false make world-tick`
(synchronous). A flagged/contradictory proposal being dropped is normal gate behaviour (it's in the
summary counts), not a failure.

### Restore from backup
What's irreplaceable (per the OVERVIEW §2a matrix): the **tick-generated world** (stories, beats,
events, figures, quotes, coverage) and the **hand-entered sponsors**. Everything else is git
(bible, grid, manifests), `assets/` copies, or regenerable (embeddings, audio).
```bash
pg_dump settlement_radio > world-$(date +%Y%m%d).sql    # take a backup (also covers sponsors)
psql settlement_radio < world-YYYYMMDD.sql              # restore into a fresh createdb
```
The scheduled off-box backup job is **C5 (VPS)** — until then, take one before anything risky.

### Last resort
`make reset-world` rebuilds a clean world from the bible — but it **destroys the living world**;
only after a backup, only when the world state itself is the problem. A bible mistake is fixed by
editing the file + `make seed-canon`, never by a reset.

---

## Admin access & security

- **Phase D admin = this machine's CLI** (the VPS via SSH from C5): the Makefile targets, the
  manifests/YAML files, `.env`. Single operator; there is no remote/web admin surface.
- **The private/public boundary (hard rule):** the operator console (`make console`) and every
  admin entry point are **private — never internet-exposed**. The public surface is exactly the
  stream + the now-playing JSON (allow-listed, public-safe fields) — **read-only**.
- **Secrets live only in `.env`** — never committed (`.env.example` carries empty keys); on a
  server, not world-readable (`chmod 600 .env`).
- **AI disclosure stays on** (spoken ident + player line) — a hard rule on every public surface.
- The **Phase E panel** (VPS-only, single-operator, private) replaces the hand-edit workflows —
  it is specified by exactly the `→ Phase E panel` tags in this manual. **Its task pack is
  written: `docs/PHASE_E_PANEL_TASKS.md` (E1)** — forms-over-files (these hand-edit how-tos remain
  the fallback path, so they stay in this manual even after the panel ships), loopback-only behind
  an SSH tunnel, planned for the C9 soak week.

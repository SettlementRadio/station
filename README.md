<p align="center"><img src="assets/wordmark-horizontal.svg" alt="Settlement Radio" width="420"></p>

<p align="center">
  <!-- add at MG6: <a href="LINK"><img src="badge" alt="Live"></a> -->
  <img src="https://img.shields.io/badge/code-Apache--2.0-blue" alt="Code: Apache-2.0">
  <img src="https://img.shields.io/badge/world-CC%20BY--SA%204.0-green" alt="World: CC BY-SA 4.0">
  <img src="https://img.shields.io/badge/built%20with-Claude%20Code-d97757" alt="Built with Claude Code">
</p>

<p align="center"><em>Late-night radio from the far future.</em></p>

<p align="center"><em>A love letter to 20th-century science fiction — broadcasting from the future it imagined.</em></p>

Settlement Radio is an always-on, AI-voiced radio station that broadcasts from the settled worlds
of the late 27th century, six hundred years from now. It knows what time it really is, reflects
it in-universe, and keeps you company across the dark with news from the colonies, music for the
small hours, and presenters who carry the same conversation night after night. It's a tribute to
the science-fiction authors who taught a generation to imagine a kinder future.

It's also being built almost entirely by AI agents — and in the open.

## Listen
- 🎧 Live stream: Cooming soon
- 🌍 [settlementradio.com]

## What it is
- A continuous, time-aware broadcast — generated ahead of air, played out 24/7.
- Persistent AI presenters with consistent personalities and a shared, version-controlled world.
- All writing, reasoning, and world-simulation by **Claude**; voice by an external TTS; the whole
  system built with **Claude Code**.

## Built in the open with Claude Code
Settlement Radio is an experiment in handing a creative production to AI agents: Claude Code wrote
the pipeline, the world engine, and the writers'-room that scripts each segment in character. The
build log lives in [`docs/DEVLOG.md`](docs/DEVLOG.md); the design in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## How it works (in brief)
Generation and playout are decoupled in time: a writers'-room of Claude agents drafts segments
ahead of air from a living world-state (canon, cast, an event timeline, and a world clock running
+600 years), those segments are voiced and stored, and a lightweight playout layer streams them
around the clock. Segment length is a parameter, so the same pipeline serves an overnight block or
a near-live drop. Details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Run it locally
The station backend (the Python pipeline + Liquidsoap playout) runs on macOS (Apple Silicon)
with Homebrew. Generation and playout are decoupled, so you can generate a segment, then serve it.
For a one-page command cheat-sheet (every `make` target, the test commands, env knobs, and
troubleshooting), see [`docs/HOWTO.md`](docs/HOWTO.md).

**1. System packages.** Note: **Python 3.12, not 3.13** — the Kokoro TTS package requires
`>=3.10,<3.13`.
```bash
brew install python@3.12 icecast ffmpeg coreutils curl lame mad espeak-ng
```
Liquidsoap is no longer in Homebrew; build it from source via opam, *with* the MP3 plugins
(`lame` to encode, `mad` to decode — without them `%mp3` is "unsupported format"):
```bash
brew install opam && opam init -y
opam install -y liquidsoap lame mad
# Apple Silicon: point the C toolchain at Homebrew if the opam build can't find headers:
#   export CPATH=/opt/homebrew/include LIBRARY_PATH=/opt/homebrew/lib
```

**2. Python environment** (on 3.12):
```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**3. Voice — Kokoro (local TTS).** Kokoro is the default `TTS_PROVIDER`: a self-hosted,
open-weight neural voice that is free, unlimited, and offline after a one-time model download.
The `espeak-ng` system package (installed in step 1) is its grapheme-to-phoneme fallback. On the
**first** `synthesize` call Kokoro downloads its model weights from HuggingFace (cached under
`~/.cache/huggingface`) and a small spaCy English model for phonemization — so the first render
is slow (~tens of seconds) and needs network; every render after is fast and offline. No API key.
Alternatives, all behind the same seam (set `TTS_PROVIDER` in `.env`): `elevenlabs` (flagship
cloud voice; needs `ELEVENLABS_API_KEY` + credits) and `say` (macOS built-in; offline fallback if
Kokoro won't install).

**4. World-state database (Postgres).** From Phase B the world (canon, cast, events) lives in a
local PostgreSQL database, seeded from the **canon bible**. Install and start it with Homebrew, then
create the database:
```bash
brew install postgresql@14
brew services start postgresql@14      # run it now and at login
createdb settlement_radio              # the default DB in DATABASE_URL
```
The connection string is `DATABASE_URL` (default `postgresql://localhost/settlement_radio`); set it
in `.env` only if your Postgres differs.

**pgvector (Phase D / D2 — semantic retrieval).** The world store uses the
[pgvector](https://github.com/pgvector/pgvector) extension for meaning-based canon recall;
`init_schema` runs `CREATE EXTENSION vector` and fails loudly if it isn't installed. The Homebrew
bottle currently covers postgresql@17/@18 (`brew install pgvector`); for **postgresql@14** (the
version above) build it from source against pg14's `pg_config`:
```bash
# postgresql@14: bottle unavailable — compile + install the extension for pg14
git clone --branch v0.8.3 --depth 1 https://github.com/pgvector/pgvector.git
cd pgvector && PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config make && \
  PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config make install
```
No DB restart needed — `make seed-canon` (next) creates the extension and the `embeddings` table.

The bible is the [`docs/canon/`](docs/canon/) folder of cornerstone files (`00-station.md`,
`90-cast.md`, … — see [`docs/canon/README.md`](docs/canon/README.md) for the authoring contract;
`CANON_DIR` overrides the location). Seeding reads the whole folder; it auto-selects the folder when
it holds content and otherwise falls back to the legacy single `docs/CANON.md`. Two commands, split so
a routine bible edit never destroys the living, tick-generated world (Phase D / D1):
```bash
make seed-canon  # SAFE everyday reload: refresh canon/cast/seed-events; keep source=tick events
make reset-world # DESTRUCTIVE full world+canon wipe + rebuild (warns + confirms)
```
Both are idempotent; re-run `make seed-canon` any time you edit a file under `docs/canon/`. (`make
seed` is a back-compat alias for the safe path.)
The station knows what time it is. The world clock ([`src/world/clock.py`](src/world/clock.py)) maps
real time to the in-world `year + 600`, and event progression ([`src/world/events.py`](src/world/events.py))
turns a stored event date into a live status and the phrase a DJ would say. See it flip:
```bash
make demo        # renders the Lumen Festival at two times: "in five days" -> "yesterday"
```
The writers' room is fed the right slice of that world by
[`src/world/context.py`](src/world/context.py): `assemble(now)` returns a **cached stable core**
(the series bible + the speaking DJ's card → sent as a prompt-cache breakpoint) plus the **dynamic
now** (events near the current time, with live status and relative phrasing, and topic-relevant
canon — all by structured DB query). Inspect exactly what the writer will send:
```bash
make context     # prints the cached core and the dynamic (events/canon) slice for now
```
> **Semantic retrieval is live (Phase D / D2).** Structured queries (by date / status / tag) still
> serve the fast path, but the canon is now also recalled by **meaning** via pgvector. The vector SQL
> lives only in [`src/world/store.py`](src/world/store.py) — `CREATE EXTENSION vector` plus ONE
> polymorphic `embeddings(corpus, entity_id, …)` table (multi-corpus so D3 events and D10 figures reuse
> it) with an HNSW cosine index — and the embedding model lives only behind
> [`src/providers/embeddings.py`](src/providers/embeddings.py). The model is a **local** open
> sentence-transformer (`settings.embeddings_*`; 384-d, free, no key — D2.0 decision); `embeddings_dim`
> is the `vector(N)` width, so a model change means a re-embed + a column migration.

Two DJs hold a conversation, not two monologues. The conversation orchestrator
([`src/writers/conversation.py`](src/writers/conversation.py)) runs a light writers' room over the
assembled context: a **showrunner** picks one beat from the current events, an **orchestrator**
writes the whole two-voice exchange in a single call from both DJ cards (Vell, night → Wren,
first light), and a **continuity** pass checks it against canon on `sonnet`, escalating to `opus`
only if it flags trouble. Each turn is voiced in that DJ's own Kokoro voice and the turns are
stitched into one talk segment. The facts are the hosts' *shared knowledge to reference naturally*
— the prompt forbids reciting or explaining canon to each other.
```bash
make conversation   # showrunner → dialogue → continuity → two-voice segment (Claude + TTS)
```

Generation fills a proven skeleton, not a blank page. [`src/formats/`](src/formats/) holds three
**program-format templates**, each a function `(now, context) -> Segment` behind a small registry
([`make_format_segment`](src/formats/__init__.py)) that assembles exactly the cast each one needs:
- **news** — a single-DJ desk: sting → in-world headlines derived from the current events →
  sign-off. (Reportage, so stating the facts plainly is correct — the opposite of the talk rule.)
- **talk** — the two-DJ conversation (open → banter → music lead-in → close); it *wraps* B4,
  reusing `conversation.compose_segment` with a structural directive.
- **music** — a single-DJ wrap: intro → a `[SONG]` slot marker (real song scheduling is Phase C
  playout) → back-announce. The marker is kept in the script and never spoken.
```bash
make format FMT=news    # one format segment on demand (FMT=news|talk|music; Claude + TTS)
make format FMT=music TOPIC="the festival"   # TOPIC steers canon retrieval
```

A **light nightly buffer** ([`src/buffer.py`](src/buffer.py)) generates the whole mind at volume in
one run — the original B6 bridge. It cycles the formats until their length targets sum to ~an hour of
audio, advancing each segment's `air_time` so the block plays back-to-back. Every segment lands as
`segments/<id>.mp3` **plus** a `segments/<id>.json` metadata sidecar, and the run is summarized in a
`segments/buffer-<timestamp>.json` manifest.
```bash
make buffer                 # ~an hour of varied segments into segments/ (Claude + Kokoro; slow)
make buffer SECONDS=600     # a shorter run for a quick check (target length in seconds)
```

The **rolling scheduler** ([`src/scheduler.py`](src/scheduler.py), C2) is the real 24/7 replacement
for that one-shot buffer. It keeps a rolling buffer of upcoming audio at `BUFFER_DEPTH_HOURS` of
**measured** duration (every render is probed with `ffprobe` and the real length recorded on the
`Segment` — `length_target_sec` is only the writer's word-count goal and runs short of it), decides
the airing order, retries-then-skips a failed slot without leaving dead air, and writes an **ordered
playlist** (`segments/playlist.txt`) that Liquidsoap re-reads — so the scheduler's decisions actually
drive what airs. Run it periodically (cron/systemd lands in C5) to keep the buffer topped up:
```bash
make schedule                 # one top-up + (re)write the playout playlist (Claude + Kokoro; slow)
make schedule INTERVAL=300    # local: keep topping up every 5 minutes
```
`BUFFER_DEPTH_HOURS` is the lead-time dial (deeper = more resilient; ~0 + streaming TTS enables
near-live later). For Phase C the `music` format is dropped from `BUFFER_ROTATION` (its `[SONG]` slot
has nothing to fill it until Phase D), so only `talk`/`news` air — no silent gaps.

**Disk retention** ([`src/scheduler.py`](src/scheduler.py) `prune()`, C2.5). At ~1 MB/min of
generated audio, an unbounded `segments/` would fill the VPS disk in weeks. After every top-up the
scheduler garbage-collects each `<id>.mp3` (+ its `<id>.json` sidecar) that has **aired** (is no
longer referenced by the live playlist) and whose air end is more than `SEGMENT_RETENTION_HOURS`
(default 6) in the past — a grace window so a just-aired clip Liquidsoap may still be reading isn't
yanked. The **shared disclosure ident** clip (`ident-disclosure-*.mp3`, reused across every ident
slot) and everything under **`assets/`** (curated, non-regenerable media) are never collected; the GC
only ever touches `segments/`. An optional `SEGMENT_RETENTION_MAX_GB` backstop evicts the oldest
aired renders if the directory still exceeds the cap. Each sweep logs the files + bytes reclaimed.
```bash
make prune                    # standalone GC (no Claude/TTS) — verify retention on disk
```

**AI disclosure on air** ([`src/disclosure.py`](src/disclosure.py), C3). The station must say it's
AI-generated (CLAUDE.md; EU AI Act Art. 50). As it places content, the scheduler weaves a short
**spoken disclosure ident** into the playlist every `DISCLOSURE_EVERY_N` content segments (default
4) — so the live stream audibly discloses on a regular cadence. The ident is static, canon-safe copy
rendered once and reused (no Claude call), so it's cheap; preview or pre-render it with `make ident`.
The same written line (`DISCLOSURE_LINE`) is shown on the web player ([`web/src/lib/disclosure.ts`](web/src/lib/disclosure.ts))
and belongs in the YouTube description (wired in C7).

**Never-dead air + health checks** ([`src/fallback.py`](src/fallback.py) + [`src/health.py`](src/health.py), C4).
A 24/7 stream must survive any single failure. Playout ([`config/radio.liq`](config/radio.liq)) airs a
**fallback chain** — `scheduled playlist → evergreen pool → music bed → disclosure ident → tone` —
so if the generator is down and the rolling buffer drains, the stream degrades to a clean pre-rendered
spoken segment, never silence. The lower tiers are pre-rendered **while the system is healthy** (so they
survive a Claude/Kokoro outage): `make fallback` (also run at the top of every `make schedule`) renders
the **evergreen pool** to GC-exempt clips and writes the playlist Liquidsoap watches. Separately,
`make health` (cron/systemd in C5) checks the **buffer runway**, the **last scheduler run** (the scheduler
writes a `last_topup_at` heartbeat), and **stream liveness**, and on any issue logs an alert plus, if
configured, POSTs a webhook / pings an uptime URL (a healthchecks.io-style dead-man's switch). It exits
non-zero when unhealthy. Drop an optional `assets/bed.mp3` to give the music-bed tier real audio.

**5. Secrets.** Copy `.env.example` to `.env`. For a fully local, zero-cost run you only need
`ANTHROPIC_API_KEY` (the script) and the default `TTS_PROVIDER=kokoro` (the voice);
`ELEVENLABS_API_KEY` is optional.

**6. Program + play.** Playout now airs the **scheduler's playlist**, so fill it first, then serve:
```bash
make schedule   # top up the rolling buffer + write segments/playlist.txt (Claude + Kokoro)
make serve      # start Icecast + Liquidsoap; airs the playlist in scheduled order
make stop       # stop Icecast + Liquidsoap
```
`make serve` prints the local player URL (`http://127.0.0.1:8000/`); Liquidsoap re-reads the
playlist as later `make schedule` runs top it up, so the stream keeps going with no restart. If the
playlist is empty or absent, the never-dead fallback chain (evergreen pool → music bed → ident → tone)
keeps the mount live. `make generate` / `make conversation` still write individual ad-hoc segments for inspection;
the live stream airs whatever the scheduler has queued. See the `Makefile` for `serve` / `status`.

## Developing the station backend
The backend follows the engineering standards in [`CLAUDE.md`](CLAUDE.md). For contributors:

- **Config over hardcoding.** All tunable values live in one typed module,
  [`src/config.py`](src/config.py) (`pydantic-settings`). Code reads `settings.X`; nothing reads a
  raw literal or `os.getenv` directly. Every field can be overridden by an env var of the same name
  (e.g. `LOG_LEVEL=debug`, `TTS_PROVIDER=elevenlabs`) — see `.env.example`.
- **Structured logging, never `print()`.** [`src/logging_setup.py`](src/logging_setup.py)
  configures `structlog` once (JSON by default for 24/7 runs; `LOG_JSON=false` for pretty console).
  Get a logger with `from .logging_setup import get_logger`.
- **Resilient external calls.** Claude and TTS calls go through `call_with_retry`
  ([`src/retry.py`](src/retry.py)) — a bounded retry that logs loudly and re-raises on exhaustion,
  rather than silently producing nothing.
- **One place for SQL.** All world-state reads/writes go through
  [`src/world/store.py`](src/world/store.py) — the same seam discipline as `providers/`. Nothing
  else imports `psycopg` or writes SQL. The [`docs/canon/`](docs/canon/) bible folder is the
  human-editable source; the parser
  ([`src/world/canon_source.py`](src/world/canon_source.py)) and `make seed-canon` project it into the DB,
  and the writer reads its world back out through [`src/world/context.py`](src/world/context.py),
  never the raw file.
- **Lint + format.** [`ruff`](https://docs.astral.sh/ruff/) is configured in `pyproject.toml`:
  ```bash
  .venv/bin/ruff check src     # lint
  .venv/bin/ruff format src    # format
  ```
- **Pre-commit hooks.** Fast checks run on every commit: ruff lint+format, a `gitleaks` secret
  scan, a config-drift guardrail (`scripts/check_no_direct_env.sh` — fails if any code under `src/`
  reads the environment directly instead of via `settings`), and whitespace/newline/large-file/
  JSON-YAML-TOML basics. Install them once after creating the venv:
  ```bash
  .venv/bin/pre-commit install
  .venv/bin/pre-commit run --all-files   # optional: run across the whole repo
  ```
  The test suite is deliberately **not** in pre-commit (it would get bypassed).

## A note on what you're hearing
Settlement Radio is a **work of fiction, written and voiced by AI**. The presenters are not real people;
the news from the future is invented. AI generation is disclosed on the stream and the player.

## License
Code is Apache-2.0; the world (canon and generated lore) is original and licensed CC BY-SA 4.0 — a
tribute to the genre, not derived from any franchise or author's work.
- **Code:** Apache-2.0 — see [`LICENSE-CODE`](LICENSE-CODE).
- **Creative world** (lore, scripts, canon): Creative Commons Attribution-ShareAlike 4.0 — see
  [`LICENSE-CONTENT`](LICENSE-CONTENT). Build in this universe; share alike; credit Settlement Radio.

## Support & follow
☕ [Ko-fi] · ✦ [GitHub Sponsors] · 🛰️ [X] · ✉️ [newsletter]

<p align="center"><sub>For the authors who imagined us here.</sub></p>

# HOWTO — the development cheat-sheet

A practical cheat-sheet for **building and developing** the station backend (the Python pipeline +
Liquidsoap playout): setup, generating segments by hand, tests, lint. **Operating** the running
station (seed modes & the world, the bible, the grid, tracks/sponsors, voice, console, recovery) has
ONE source: [`docs/ADMIN_MANUAL.md`](ADMIN_MANUAL.md) — cross-linked here, never duplicated. For the
*why*, see [`README.md`](../README.md) (full setup), [`CLAUDE.md`](../CLAUDE.md) (the rules), and
[`DEVLOG.md`](DEVLOG.md) (the session-by-session story).

Conventions used below:
- `PY` means the venv Python: `.venv/bin/python`. Most things have a `make` shortcut **and** the
  raw command — the `make` target is the one to reach for; the raw form shows what it runs.
- Anything marked **(Claude)** makes a live Anthropic API call (needs `ANTHROPIC_API_KEY` in
  `.env`). Voice uses local **Kokoro** by default — free, offline, no key.
- The `/web` Next.js app is a separate world; its commands are not here (see `web/`).

---

## 0. One-time setup

```bash
# System packages (macOS / Homebrew). NOTE: Python 3.12, not 3.13 (Kokoro needs <3.13).
brew install python@3.12 icecast ffmpeg coreutils curl lame mad espeak-ng postgresql@14
brew install opam && opam init -y && opam install -y liquidsoap lame mad   # playout

# Python env
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Secrets
cp .env.example .env          # then fill in ANTHROPIC_API_KEY (ElevenLabs optional)

# World-state database (Postgres) — needs the pgvector extension (D2):
# postgresql@17/@18: `brew install pgvector`; postgresql@14: build from source (README "pgvector").
brew services start postgresql@14
createdb settlement_radio
make seed-canon               # seed the world from the canon bible (docs/canon/)

# Pre-commit hooks (lint + secret scan on every commit)
.venv/bin/pre-commit install
```

Done when: `make seed-canon` reports row counts and `.venv/bin/pytest -q` is green.

---

## 1. The world-state DB (canon / cast / events)

**Operating the world lives in the manual**, not here — seed modes (SAFE `make seed-canon` vs
DESTRUCTIVE `make reset-world`), editing the bible, the world tick, the catalogs
(`seed-tracks`/`seed-sponsors`), and what survives what: see [`ADMIN_MANUAL.md`](ADMIN_MANUAL.md).
Dev-side checks:

| Do | `make` | Raw |
|----|--------|-----|
| Show the progressing-event flip (B2 demo) | `make demo` | `$PY -m src.world.events` |
| Print the writer's assembled context (B3) | `make context` | `$PY -m src.world.context` |

- `make demo` renders the Lumen Festival at two `now` values → `"in five days"` then `"yesterday"`.
- `make context` shows the two halves the writer sends: the **cached core** (bible + DJ card) and
  the **dynamic now** (events near now + canon).
- `make seed` is a back-compat alias for the SAFE `make seed-canon` — never the destructive path.

---

## 2. Generate audio segments

All output lands in `segments/` (gitignored) as `.mp3`. Voice = Kokoro by default.

| Do | `make` | Raw |
|----|--------|-----|
| One single-DJ talk segment (Vell) **(Claude)** | `make generate` | `$PY -m src.produce` |
| Two-DJ conversation (Vell + Wren) **(Claude)** | `make conversation` | `$PY -m src.writers.conversation` |
| One **program-format** segment (B5) **(Claude)** | `make format FMT=news` | `$PY -m src.formats news` |
| A **whole varied buffer** (~an hour, B6) **(Claude)** | `make buffer` | `$PY -m src.buffer` |
| Print a single-DJ *script* only (no audio) **(Claude)** | — | `$PY -m src.writer` |

- `make conversation` runs the writers' room (showrunner → dialogue → continuity), voices each turn
  in its own Kokoro voice, and stitches them into one segment. It prints the beat, the script, the
  audio path, and the continuity verdict.
- **`make format`** fills a proven show backbone; pick one with `FMT=` (default `talk`) and
  optionally steer canon retrieval with `TOPIC=`:
  - `FMT=news` — single-DJ desk: sting → in-world headlines from current events → sign-off.
  - `FMT=talk` — two-DJ show (open → banter → music lead-in → close); wraps `make conversation`.
  - `FMT=music` — a full spin (D7): intro → bumper → a real track from the curated catalogue →
    back-announce that tells the song's story (registering tracks: see the manual, D7).
  ```bash
  make format FMT=news
  make format FMT=music TOPIC="the festival"
  ```
  Output lands as `news-…`/`talk-…`/`music-…` in `segments/`; the raw form is `$PY -m src.formats
  <news|talk|music> [topic…]`.
- **`make buffer`** (B6) predates the real rolling scheduler (`make schedule`, C2 — see §3) but is
  still handy for pre-generating a **whole varied block in one run**: it cycles the formats until
  their length targets sum to ~`buffer_target_sec` of audio, advancing each segment's `air_time` so
  the block plays back-to-back and current events progress across it. Every segment lands as
  `segments/<id>.mp3` **plus** a `segments/<id>.json` metadata sidecar, and the run is summarized in
  a `segments/buffer-<timestamp>.json` **manifest**. The full hour is ~20 segments — **slow** (each
  is a Claude call + a render); use `SECONDS=` for a quick check:
  ```bash
  make buffer                 # ~an hour of varied segments (default buffer_target_sec)
  make buffer SECONDS=600     # ~10 minutes — a fast check (target length in seconds)
  ```
  Tune the mix and ceiling in `.env`: `BUFFER_ROTATION` (which formats, in order),
  `BUFFER_TARGET_SEC` (the default length), `BUFFER_MAX_SEGMENTS` (the safety cap). See §6.
- First Kokoro run downloads model weights (~tens of seconds, needs network); every run after is
  fast and offline.

---

## 3. Play it (Icecast + Liquidsoap)

Generation and playout are decoupled. Since C2, **`serve` airs the SCHEDULER's playlist**
(`segments/playlist.txt`), not the newest file — so **`make air`** (= `schedule` + `serve`) is the
live path; an empty playlist airs the never-dead fallback (C4). Running/monitoring the live station
(health, console, recovery) is the manual's territory.

| Do | `make` |
|----|--------|
| The live path: top up the buffer + serve the playlist (C2) | `make air` |
| Just serve (Icecast + Liquidsoap over the current playlist) | `make serve` |
| Top up the rolling buffer + rewrite the playlist | `make schedule` (loop: `INTERVAL=300`) |
| Generate one ad-hoc single-DJ segment, then serve | `make play` |
| Generate one ad-hoc two-DJ conversation, then serve | `make play-convo` |
| Stop Icecast + Liquidsoap (no orphans) | `make stop` |
| Show what's running + mount state | `make status` |
| List all targets | `make help` |

- `play`/`play-convo` write a single **ad-hoc** segment for inspection, but the stream airs whatever
  the scheduler queued (or the fallback) — they don't jump the queue.
- Player: <http://127.0.0.1:8000/>  ·  Stream: <http://127.0.0.1:8000/settlement.mp3>
- Use the IPv4 literal `127.0.0.1`, not `localhost` (Icecast binds IPv4).
- Logs while serving: `.run/icecast.log`, `.run/liquidsoap.log`.

---

## 4. Tests

The suite is **surgical** — it covers the bits with real logic (the world clock, relative phrasing,
the parsers, the gates, the scheduler/grid, the selectors…), not glue; each phase pack added its own
`tests/test_*.py` (300+ tests). No live model/TTS calls; store tests use a local Postgres when one is
reachable (each rolls back at teardown) and **skip cleanly** without Postgres/pgvector.

```bash
.venv/bin/pytest -q                       # run everything (fast, the default)
.venv/bin/pytest                          # verbose-ish (per-file dots + summary)
.venv/bin/pytest -v                       # one line per test (see every name)
.venv/bin/pytest tests/test_events.py     # one file
.venv/bin/pytest -k phrase                # only tests whose name matches "phrase"
.venv/bin/pytest -x                       # stop at the first failure
.venv/bin/pytest --collect-only -q        # list test names without running them
.venv/bin/pytest -s                       # don't capture stdout (see prints/logs)
```

Each test file's docstring says what it covers — `.venv/bin/pytest --collect-only -q` lists the
whole surface (a per-file inventory here would just go stale).

> Tests are deliberately **not** in the pre-commit hook (slow checks get bypassed) — run them
> yourself before pushing.

---

## 5. Lint, format, and the commit gate

```bash
.venv/bin/ruff check src tests            # lint
.venv/bin/ruff check --fix src tests      # lint + auto-fix (imports, etc.)
.venv/bin/ruff format src tests           # format (88-col, double quotes)
.venv/bin/ruff format --check src tests   # verify formatting without changing files

bash scripts/check_no_direct_env.sh       # guardrail: no os.getenv/os.environ outside config.py

.venv/bin/pre-commit run --all-files      # run the whole commit gate now
.venv/bin/pre-commit install              # install it (one-time)
```

The pre-commit gate runs: `ruff` (lint + format), `gitleaks` (secret scan), the env-drift
guardrail, and whitespace/EOF/large-file/JSON-YAML-TOML basics. It runs automatically on
`git commit` and blocks on failure.

---

## 6. Env knobs (set in `.env`, or inline for one run)

Every field in [`src/config.py`](../src/config.py) is overridable by an env var of the same name.
The handy ones:

```bash
TTS_PROVIDER=kokoro        # default: local, free, offline. Also: elevenlabs | say
LOG_JSON=false             # human-pretty console logs (default true = JSON for 24/7)
LOG_LEVEL=debug            # debug | info | warning | error
DATABASE_URL=postgresql://localhost/settlement_radio

# B6 buffer (`make buffer`):
BUFFER_TARGET_SEC=3600          # ~how much audio per run, in seconds (default ~an hour)
BUFFER_ROTATION=["talk","news","music"]   # which formats to cycle, in order (JSON list)
BUFFER_MAX_SEGMENTS=30          # safety cap on segments per run
# NB: with PROGRAMMING_ENABLED=true (the default, D6) the GRID decides what airs;
# BUFFER_ROTATION is only the reserved `default` program's mix (see the manual, D6).
```

Override per run without editing `.env`:

```bash
TTS_PROVIDER=say make generate        # use macOS `say` instead of Kokoro
LOG_JSON=false make conversation      # readable logs for this run
make buffer SECONDS=600               # a ~10-min buffer (shortcut for BUFFER_TARGET_SEC)
```

Provider notes: `kokoro` = local neural voice (default, no key); `elevenlabs` = flagship cloud
voice (needs `ELEVENLABS_API_KEY` + credits; free tier ≈ 2 segments/month); `say` = macOS built-in,
offline fallback if Kokoro won't install.

---

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `make seed`/`make demo` errors connecting to the DB | `brew services start postgresql@14`; `createdb settlement_radio` |
| `make context`/segment cmds say a speaker/event is missing | run `make seed` first (DB is empty or stale) |
| Player shows an empty page | use `http://127.0.0.1:8000/`, not `localhost`; check `make status` and `.run/*.log` |
| Port 8000 already held | `make stop` (it also `pkill`s orphans), then `make serve` |
| First Kokoro render hangs ~tens of seconds | expected — it's downloading model weights once; needs network that first time |
| Out of ElevenLabs credits | you're on the free tier (~2 segments/mo); switch back with `TTS_PROVIDER=kokoro` |
| A commit is blocked | read the hook output; run `.venv/bin/pre-commit run --all-files` to see/fix all |

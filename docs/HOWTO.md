# HOWTO — every command, in one place

A practical cheat-sheet for running the **station backend** (the Python pipeline + Liquidsoap
playout). For the *why* behind any of it, see [`README.md`](../README.md) (full setup),
[`CLAUDE.md`](../CLAUDE.md) (the rules), and [`DEVLOG.md`](DEVLOG.md) (the session-by-session story).

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

# World-state database (Postgres)
brew services start postgresql@14
createdb settlement_radio
make seed                     # load docs/CANON.md into the DB

# Pre-commit hooks (lint + secret scan on every commit)
.venv/bin/pre-commit install
```

Done when: `make seed` reports row counts and `.venv/bin/pytest -q` is green.

---

## 1. The world-state DB (canon / cast / events)

| Do | `make` | Raw |
|----|--------|-----|
| Seed the DB from `docs/CANON.md` (idempotent) | `make seed` | `$PY -m src.world.seed` |
| Show the progressing-event flip (B2 demo) | `make demo` | `$PY -m src.world.events` |
| Print the writer's assembled context (B3) | `make context` | `$PY -m src.world.context` |

- **Edit the world** by editing [`docs/CANON.md`](CANON.md), then re-run `make seed` — it
  TRUNCATEs and reloads, so the DB becomes exactly what the file says (no orphans).
- `make demo` renders the Lumen Festival at two `now` values → `"in five days"` then `"yesterday"`.
- `make context` shows the two halves the writer sends: the **cached core** (bible + DJ card) and
  the **dynamic now** (events near now + canon).

---

## 2. Generate audio segments

All output lands in `segments/` (gitignored) as `.mp3`. Voice = Kokoro by default.

| Do | `make` | Raw |
|----|--------|-----|
| One single-DJ talk segment (Vell) **(Claude)** | `make generate` | `$PY -m src.produce` |
| Two-DJ conversation (Vell + Wren) **(Claude)** | `make conversation` | `$PY -m src.writers.conversation` |
| Print a single-DJ *script* only (no audio) **(Claude)** | — | `$PY -m src.writer` |

- `make conversation` runs the writers' room (showrunner → dialogue → continuity), voices each turn
  in its own Kokoro voice, and stitches them into one segment. It prints the beat, the script, the
  audio path, and the continuity verdict.
- First Kokoro run downloads model weights (~tens of seconds, needs network); every run after is
  fast and offline.

---

## 3. Play it (Icecast + Liquidsoap)

Generation and playout are decoupled. **`serve` loops the newest segment** in `segments/` — picked
by file **modification time** (so it works whatever the filename prefix: `vell-…` or `convo-…`) — and
re-scans after every loop, so a segment generated while the stream is up airs on the next pass.

| Do | `make` |
|----|--------|
| Generate a **single-DJ** segment **and** serve it | `make play` |
| Generate a **two-DJ conversation** **and** serve it | `make play-convo` |
| Just serve (loop the newest existing segment) | `make serve` |
| Stop Icecast + Liquidsoap (no orphans) | `make stop` |
| Show what's running + mount state | `make status` |
| List all targets | `make help` |

- `make play` = `generate` + `serve`; `make play-convo` = `conversation` + `serve`. To air a
  conversation you already generated, just `make serve` (it picks the newest by mtime).
- Player: <http://127.0.0.1:8000/>  ·  Stream: <http://127.0.0.1:8000/settlement.mp3>
- Use the IPv4 literal `127.0.0.1`, not `localhost` (Icecast binds IPv4).
- Logs while serving: `.run/icecast.log`, `.run/liquidsoap.log`.
- No scheduler yet — playout always loops the single newest segment; the real scheduler that plays
  *through* a buffer is Phase C.

---

## 4. Tests

The suite is **surgical** — it covers the bits with real logic (the world clock, relative-time
phrasing, the CANON parser, context assembly, dialogue parsing, retries), not glue. No DB or API is
needed: tests use fixtures and pure functions. **24 tests** across 6 files.

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

What each file covers:

| File | Tests | Covers |
|------|------:|--------|
| `tests/test_clock.py` | 4 | real→in-world `+600y` mapping; the 29-Feb Gregorian trap; wall-clock display |
| `tests/test_events.py` | 5 | status (upcoming/today/past) + relative phrasing thresholds ("in five days"…) |
| `tests/test_canon_source.py` | 5 | parsing `CANON.md` → facts/cast/events; the B3 series-bible extractor |
| `tests/test_context.py` | 3 | topic→tags tokenizer; the dynamic-block renderer (relative phrase + facts) |
| `tests/test_conversation.py` | 4 | `parse_turns` (labels, `**bold**`, wrapped lines, preamble); continuity verdict reader |
| `tests/test_retry.py` | 3 | bounded retry: first-try success, recovery after transient fails, exhaust-then-raise |

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
```

Override per run without editing `.env`:

```bash
TTS_PROVIDER=say make generate        # use macOS `say` instead of Kokoro
LOG_JSON=false make conversation      # readable logs for this run
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

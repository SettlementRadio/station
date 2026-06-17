# Settlement Radio

An AI-powered fictional sci-fi radio station broadcasting 600 years ahead of the present.
Every word and world decision is produced by Claude; the entire system is built by Claude Code.
Voice synthesis (TTS) is the one external component.

See [`CLAUDE.md`](CLAUDE.md) for the project constitution and
[`docs/`](docs/) for the architecture, canon, and phase tasks.

## Current phase: A — "Proof of Loop"

Produce one ~5-minute audio segment (a single DJ, generated from the canon and voiced by TTS) and
play it on a local loop in the browser.

## Setup

Requires **Python 3.11+** and **macOS** (Apple Silicon; system tools via Homebrew).

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Configure secrets
cp .env.example .env
#   then edit .env and fill in ANTHROPIC_API_KEY and ELEVENLABS_API_KEY
```

System tools for playout (`icecast`, `ffmpeg`, `liquidsoap`) — see
[Playout (T5)](#playout-t5) below.

## Project layout

```
src/            Pipeline code
  providers/    The two vendor seams (llm.py, tts.py)
config/         Liquidsoap + Icecast configs
docs/           Architecture, canon, phase tasks
segments/       Generated audio (gitignored)
assets/         Jingles / beds (gitignored)
.env            Secrets (gitignored)
.env.example    Template with empty keys (committed)
```

## Provider seams (T1)

All vendor calls go through two modules — nothing else imports a vendor SDK:

- [`src/providers/llm.py`](src/providers/llm.py) — `generate(prompt, *, system=None,
  model="sonnet", cached_context=None, max_tokens=4000)`. `model` is a logical tier
  (`haiku` | `sonnet` | `opus`) mapped to a real Claude ID inside the module;
  `cached_context` is sent as a prompt-cache breakpoint.
- [`src/providers/tts.py`](src/providers/tts.py) — `synthesize(text, *, voice, emotion=None,
  out_path)`. `voice` is a logical name (e.g. `vell_night`) mapped to a vendor voice id;
  the backend is selected by `TTS_PROVIDER`: `elevenlabs` (default, the real voice),
  `say` (macOS built-in — **offline, free, unlimited; for testing**), or the stubbed
  `kokoro`/`orpheus`. Non-mp3 backends transcode to mp3 via ffmpeg (`_to_mp3`).

Both read their keys from `.env`. Quick check from the repo root (needs a populated `.env`):

```bash
.venv/bin/python -c "from src.providers import llm; print(llm.generate('say hello'))"
```

## Script generation (T3)

[`src/writer.py`](src/writer.py) — `write_segment_script(canon_text, now_iso)` asks Claude
(tier `sonnet`) to write Vell's ~5-minute night-shift talk segment from the canon. The canon is
passed as the `cached_context` breakpoint (the Phase A cost lever); the in-world clock
(`real time + 600 years`, weekday preserved) and the segment spec go in the small per-call system
prompt so the time check is real. A no-op `safety_check(text)` marks where a content gate slots in
later. Print a fresh segment for the current time (needs a populated `.env`):

```bash
.venv/bin/python -m src.writer
```

## Render to audio (T4)

[`src/produce.py`](src/produce.py) — `make_segment(now_iso, *, length_target_sec=300)` runs the
Phase A pipeline: write the script (`write_segment_script`), synthesize it via the TTS seam with
voice `vell_night`, write the audio into [`segments/`](segments/), and return a populated
[`Segment`](src/segment.py) (`format="talk"`, `audio_path` set, `disclosure=True`). The length is
a dial with a default, not a hardcoded constant — pass a smaller `length_target_sec` later for a
near-live drop. Generate a fresh ~5-min segment for the current time (needs a populated `.env`):

```bash
.venv/bin/python -m src.produce
```

## Playout (T5)

Loop the generated segment on a **local** Icecast stream that never goes silent.

### Install the system tools

`icecast` and `ffmpeg` come from Homebrew. Liquidsoap **no longer has a Homebrew
formula** (and upstream ships only Linux packages), so on macOS it installs via
**opam**, the OCaml package manager, and must be built from source with the MP3
codec plugins enabled — Liquidsoap's MP3 support is optional and pulled in via
two extra opam packages: `lame` (MP3 **encode**, for the Icecast output) and
`mad` (MP3 **decode**, to read the segments `produce.py` writes). Build them in
the same `opam install` so Liquidsoap is compiled with both.

```bash
# 1. Stream server + audio plumbing, and the MP3 system libraries the codec
#    plugins link against (lame = encoder, mad = decoder). coreutils + curl are
#    Liquidsoap's other system deps.
brew install icecast ffmpeg coreutils curl lame mad

# 2. opam (OCaml package manager), then initialise it.
brew install opam
opam init -y && eval "$(opam env)"

# 3. Build Liquidsoap WITH the MP3 plugins. CPATH/LIBRARY_PATH point the C stubs
#    at Homebrew's headers/libs (not on clang's default Apple-Silicon search
#    path). This compiles a sizable OCaml tree — allow ~30–60 min on first run.
export CPATH="/opt/homebrew/include"
export LIBRARY_PATH="/opt/homebrew/lib"
opam install -y --assume-depexts liquidsoap lame mad
```

`liquidsoap` lives in opam's switch, so each new shell needs `eval "$(opam env)"`
on PATH first (opam's `opam init` shell hook does this automatically for new
terminals). Then sanity-check the playout script against your build — it should
print nothing and exit 0:

```bash
liquidsoap --check config/radio.liq
```

### Configs

- [`config/icecast.xml`](config/icecast.xml) — local-only Icecast on
  `http://localhost:8000`. Reuses Homebrew's web/admin/log dirs so the status
  page renders with no extra setup. The `<source-password>` must match
  `ICECAST_SOURCE_PASSWORD` in `.env` (both default to `hackme`).
- [`config/radio.liq`](config/radio.liq) — Liquidsoap plays the **newest** file
  in [`segments/`](segments/) on a loop, re-scanning each loop so a freshly
  generated segment is picked up without a restart. A **never-dead fallback**
  (a bundled `assets/bed.mp3` if you drop one in, else a quiet sine tone) keeps
  the mount live when no segment exists. Output is the `settlement.mp3` mount.

### Run it

Generate a segment first (T4), then, **from the repo root**, in two terminals:

```bash
# Terminal 1 — start the stream server
icecast -c config/icecast.xml

# Terminal 2 — start playout (reads ICECAST_SOURCE_PASSWORD from the env if set)
liquidsoap config/radio.liq
```

Then open it in a browser:

```
http://localhost:8000/                     # player page (play button + disclosure)
http://localhost:8000/settlement.mp3       # the raw audio stream
```

> The bundled player page lives at [`config/web/index.html`](config/web/index.html)
> and is served by Icecast at `/`. Browsers won't render a play button for a bare
> MP3 mount, so open `/` (the player), not `/settlement.mp3` directly. The page
> also carries the AI-generation disclosure (a CLAUDE.md hard rule).

But you normally won't run those by hand — use the `make` workflow below.

## Run (T6)

One command does the whole Phase A loop. From the repo root:

```bash
make play       # generate a fresh segment for NOW + serve it, then print the URL
```

Then open **http://localhost:8000/** and press play — you'll hear Vell deliver a
freshly generated night-shift segment with a correct (in-world) time check.

Individual targets:

```bash
make generate   # write a fresh segment for the current time (Claude → TTS)
make serve      # start Icecast + Liquidsoap; loops the newest segment
make stop       # stop both cleanly (no orphan processes / port-8000 squatters)
make status     # show what's running and the mount's HTTP state
```

Notes:
- `make serve` always stops any running instance first, so a stale Icecast can
  never hold port 8000 — the recurring "Could not create listener socket"
  problem is handled.
- `make generate` / `make play` make a live Anthropic call, plus a TTS call. With
  the default `elevenlabs` backend that spends voice credits; the free tier only
  covers ~2 full segments/month. **To test offline with no credits, use the
  macOS `say` backend for that run:**
  ```bash
  TTS_PROVIDER=say make play     # generate + serve using the free, offline voice
  ```
  (`say` is lower quality — a stand-in for testing the loop, not Vell's real
  voice. The shell override beats `.env`, so the default stays `elevenlabs`.)
- Processes run in the background; PIDs and logs are under `.run/` (gitignored).
  Liquidsoap runs via `opam exec`, so `make` finds it without `eval "$(opam env)"`.

**Phase A definition of done:** `make play` → open the URL → hear Vell. ✅

<p align="center"><img src="assets/brand/wordmark-horizontal.png" alt="Settlement Radio" width="420"></p>

<p align="center"><em>Late-night radio from the far future.</em></p>

Settlement Radio is an always-on, AI-voiced radio station that broadcasts from the settled worlds
of the late 27th century — six hundred years from now. It knows what time it really is, reflects
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

**4. Secrets.** Copy `.env.example` to `.env`. For a fully local, zero-cost run you only need
`ANTHROPIC_API_KEY` (the script) and the default `TTS_PROVIDER=kokoro` (the voice);
`ELEVENLABS_API_KEY` is optional.

**5. Generate + play:**
```bash
make play     # write a fresh segment for the current time, then serve it
make stop     # stop Icecast + Liquidsoap
```
`make play` prints the local player URL (`http://127.0.0.1:8000/`). See the `Makefile` for the
individual `generate` / `serve` / `status` targets.

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
Settlement Radio is a **work of fiction, generated with AI**. The presenters are not real people;
the news from the future is invented. AI generation is disclosed on the stream and the player.

## License
- **Code:** Apache-2.0 — see [`LICENSE-CODE`](LICENSE-CODE).
- **Creative world** (lore, scripts, canon): Creative Commons Attribution-ShareAlike 4.0 — see
  [`LICENSE-CONTENT`](LICENSE-CONTENT). Build in this universe; share alike; credit Settlement Radio.

## Support & follow
☕ [Ko-fi] · ✦ [GitHub Sponsors] · 🛰️ [X] · ✉️ [newsletter]

<p align="center"><sub>For the authors who imagined us here.</sub></p>

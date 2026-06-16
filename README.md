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

System tools (`liquidsoap`, `icecast`, `ffmpeg`) are installed later in T5 — see
[`docs/PHASE_A_TASKS.md`](docs/PHASE_A_TASKS.md).

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
  the backend is selected by `TTS_PROVIDER` (`elevenlabs` now; `kokoro`/`orpheus` stubbed).

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

## Run

Commands land here as the phase tasks are completed (see `docs/PHASE_A_TASKS.md`).
The Phase A goal is `make play` → a fresh segment generated and served on a local stream.

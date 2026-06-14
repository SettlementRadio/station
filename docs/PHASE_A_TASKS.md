# PHASE_A_TASKS.md — executable task list (Proof of Loop)

Work these **in order**. After each task, summarize what changed and how the human verifies it.
Respect `CLAUDE.md` (the two seams, the hard rules) at every step. Keep changes small.

Prerequisite (human-supplied): `.env` contains `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY`.

---

## T0 — Scaffold the repo
**Goal:** a clean, reproducible project skeleton.
**Do:**
- Create `src/`, `src/providers/`, `config/`, `docs/`, `segments/` (gitignored), `assets/`
  (gitignored).
- Create `.gitignore` (ignore `.env`, `segments/`, `assets/`, `__pycache__`, venv).
- Create `.env.example` with empty `ANTHROPIC_API_KEY=` and `ELEVENLABS_API_KEY=` and
  `TTS_PROVIDER=elevenlabs`.
- Set up a Python 3.11+ virtual environment and a `requirements.txt` (anthropic SDK, the
  ElevenLabs SDK or plain `requests`, `python-dotenv`).
- Start `README.md` with setup + run instructions (update it as you go).
**Done when:** `pip install -r requirements.txt` succeeds in a fresh venv and the tree matches
`CLAUDE.md` → "Repo conventions".

## T1 — Provider abstraction (Seam #1)
**Goal:** the only two modules that touch vendor SDKs.
**Do:**
- `src/providers/llm.py` implementing `generate(...)` per `docs/ARCHITECTURE.md`, mapping the
  logical tiers `haiku|sonnet|opus` to current Claude model IDs, reading the key from env.
- `src/providers/tts.py` implementing `synthesize(...)`, with an ElevenLabs implementation
  selected by `TTS_PROVIDER=elevenlabs`, and a `voice` registry mapping logical names
  (`vell_night`) to a vendor voice id. Leave a clearly-marked stub for a future `kokoro`/`orpheus`
  implementation.
**Done when:** a tiny scratch call (`generate("say hello")` and `synthesize("hello", voice="vell_night", out_path="segments/_test.mp3")`) each succeed and are runnable from a one-line command. Then delete the scratch call.

## T2 — The Segment model (Seam #2)
**Goal:** the unit that makes segment length a dial.
**Do:** create `src/segment.py` with the `Segment` dataclass exactly as in
`docs/ARCHITECTURE.md` (including `length_target_sec`, `lead_time_sec`, `disclosure`).
**Done when:** a `Segment` can be created and printed; no length is hardcoded anywhere else.

## T3 — Script generation (Layer 3, minimal)
**Goal:** Claude writes Vell's segment from the canon.
**Do:**
- `src/writer.py` with `write_segment_script(canon_text, now_iso) -> str`.
- It builds a system prompt from `docs/CANON.md` (read the file) + the in-world clock
  (`now + 600 years`) and asks Claude (via `llm.generate`, tier `sonnet`, passing the canon as
  `cached_context` so it's a prompt-cache breakpoint) for the Phase A segment
  spec at the bottom of `CANON.md`: a ~5-min, in-character night-shift talk segment with a real
  time check. ~700–800 words.
- Keep the script step structured so a safety-gate function could wrap it later (a no-op
  `safety_check(text) -> text` placeholder is fine now).
**Done when:** running it prints a coherent, in-character script that includes a correct time
check for the current time.

## T4 — Render to audio (Layer 4, minimal)
**Goal:** turn the script into one audio file.
**Do:**
- `src/produce.py` with `make_segment(now_iso) -> Segment`: call `write_segment_script`, then
  `tts.synthesize` with `voice="vell_night"`, write the audio into `segments/`, and return a
  populated `Segment` (set `format="talk"`, `length_target_sec=300`, `audio_path`, `disclosure=True`).
**Done when:** running it produces a playable ~5-min `.mp3`/`.wav` in `segments/` that sounds like
Vell.

## T5 — Playout (Layers 5–6, minimal)
**Goal:** loop the segment on a local stream with no silence.
**Do:**
- Install `liquidsoap`, `icecast`, `ffmpeg` via Homebrew (show the commands; add to README).
- `config/icecast.xml` (local, a source password from env or a documented default for local-only).
- `config/radio.liq`: a Liquidsoap script that plays the newest file in `segments/` on a loop,
  with a **fallback** (a short silence-avoidance tone or a bundled royalty-free bed in `assets/`)
  so the stream is never dead, and outputs to local Icecast.
**Done when:** starting Icecast + Liquidsoap serves a local stream URL.

## T6 — One command + listen
**Goal:** the human can run the whole loop trivially.
**Do:** a `Makefile` (or `run.sh`) with:
- `make generate` → runs `make_segment` for the current time.
- `make serve` → starts Icecast + Liquidsoap.
- `make play` → `generate` then `serve`, and prints the local stream URL.
- Document all three in `README.md`.
**Done when (DEFINITION OF DONE FOR PHASE A):** the human runs `make play`, opens the URL in a
browser, and hears Vell deliver a freshly generated night-shift segment with a correct time check.

---

## T7 — (Optional stretch) prove the dial
Only if T0–T6 are solid. Add `make drop` that calls `make_segment` with `length_target_sec=60`
and a tighter prompt to produce a ~60-second segment, demonstrating that segment length is a
parameter, not a rewrite. This becomes the seed of the near-live demo and a great marketing clip.

## Explicitly NOT in Phase A
Database, pgvector, RAG, the world/event engine, a second DJ, multi-agent conversation, the VPS,
YouTube, the safety gate (beyond the placeholder), donations, the web player UI, **the Batch API
path** (Phase A makes a single on-demand live call; prompt caching is the Phase A cost lever). Do
not start these — note them for Phase B.

# CLAUDE.md — Settlement Radio

> This file is the project constitution. Read it before doing anything. Also read
> `docs/ARCHITECTURE.md`, `docs/CANON.md`, and `docs/PHASE_A_TASKS.md`.

## What this project is

An AI-powered fictional sci-fi **radio station** named **Settlement Radio**, broadcasting from
**600 years ahead of the real present** (the in-world year is always `real year + 600` — never
hardcode a year), as
a tribute to the science-fiction authors who shaped the genre. **Every word, reasoning step, and
world decision is produced by Claude. The entire system is built by Claude Code.** Voice
synthesis (TTS) is the one external component, because Anthropic does not make a voice product.

## Current phase: PHASE A — "Proof of Loop"

**Goal:** produce ONE ~5-minute audio segment — a single DJ talking, generated from the canon by
Claude and voiced by TTS — and play it on a **local** loop the human can listen to in a browser.

**In scope:** one DJ, one segment, local playback only.
**Out of scope for Phase A:** database, RAG, a second DJ, the time/event engine, the VPS,
YouTube, donations, anything public. Those come in later phases. Do not build them now.

**Definition of done:** running the documented command (e.g. `make play`) generates a fresh
segment and serves a local stream; the human opens the URL and hears the DJ speak in character.

## Tech reality (important)

- The human works **only through Claude Code**. You (the agent) do the building. Prefer small,
  verifiable steps and explain how to check each one.
- **Language:** Python 3.11+ for the pipeline; Liquidsoap's own config language for playout.
- **Platform:** macOS (Apple Silicon). Install system tools with Homebrew. You may run install
  commands, but show them and put them in the README.
- **Intelligence:** Anthropic API (Claude), with **model routing by job** (map these logical
  tiers in `src/providers/llm.py`):
  - `sonnet` → **Claude Sonnet 4.6** (`claude-sonnet-4-6`) — the DEFAULT writing brain: DJ
    scripts, showrunner, continuity. Script quality is the product, so this is the workhorse.
  - `haiku` → **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — high-volume, low-stakes, and
    near-live: time checks, idents, filler, the future 60-second drops.
  - `opus` → **Claude Opus 4.8** (`claude-opus-4-8`) — hard reasoning only (gnarly continuity,
    big worldbuilding calls); runs rarely.
  - Do NOT use Fable 5 / Mythos as a workhorse — overkill and ~2x Opus cost.
- **Cost levers are mandatory, not optional** (text cost must stay near-trivial):
  - **Prompt caching (Phase A)** — cache the stable canon / character cards / system prompt so
    each call pays full price only for the small variable part (~90% off cached input). The
    provider abstraction must support a cached-context path **from the start**, and Phase A uses
    it (the canon is passed as a cache breakpoint).
  - **Batch API (Phase B)** — once generation becomes a nightly batch job, run it through the
    Batch API (50% off). Phase A generates a single segment on demand (a live call), so Batch is
    deferred; do not build a Batch code path now.
- **Voice:** **ElevenLabs API (free tier)** for now — accessed ONLY through the TTS abstraction so
  it can be swapped for self-hosted Kokoro/Orpheus later without touching anything else.
- **Playout:** Liquidsoap + Icecast + ffmpeg (Homebrew).
- **No database in Phase A.** The canon lives in `docs/CANON.md` and is read into the prompt.

## The two load-bearing seams (build these now, thin)

1. **Provider abstraction.** All model/voice calls go through `llm.generate(...)` and
   `tts.synthesize(text, voice, emotion)`. **Never call a vendor SDK directly outside these two
   modules.** Implementations are selected by env/config.
2. **Segment abstraction.** A `Segment` is the unit of everything: audio + metadata (`id`,
   `length_target`, `air_time`, `format`, `disclosure`). **Segment length and lead-time are
   parameters, never hardcoded** — this is what later lets a 3-hour overnight block and a
   60-second near-live drop share one code path.

See `docs/ARCHITECTURE.md` for the concrete interfaces and the `Segment` shape.

## Repo conventions

- Structure: `src/` (code), `config/` (liquidsoap + icecast configs), `docs/`, `segments/`
  (generated audio — gitignored), `assets/` (jingles/beds — gitignored), `.env` (secrets —
  gitignored), `.env.example` (empty keys, committed).
- **Secrets only in `.env`, NEVER committed.** Always keep `.env.example` current.
- Small modules, clear names, type hints. Add a test only where the logic is non-trivial.
- Every dependency and command goes in the `README.md` so the build is reproducible from scratch.

## Hard rules — never violate

- **NEVER commit secrets or API keys.**
- **IP boundary — this is a TRIBUTE, not a derivative.** Do not use real franchises, named
  characters, trademarks, or any living author's creations. Original world only — the *spirit* of
  the genre, never its intellectual property.
- **Content safety:** before any *public* broadcast (Phase C onward), generated text must pass a
  safety gate. Not required in Phase A (nothing is public), but structure the script step so a
  gate can slot in cleanly later.
- **AI disclosure:** when public, the station must disclose that it is AI-generated (spoken + on
  the player). Keep a placeholder field for it now.
- **Ask before destructive actions** (deleting files, force operations, anything irreversible).

## How to work (agent instructions)

- Read `docs/ARCHITECTURE.md`, `docs/CANON.md`, and `docs/PHASE_A_TASKS.md` before coding.
- Work **task by task** from `docs/PHASE_A_TASKS.md`, in order. After each task, state what you
  did and exactly how the human can verify it.
- Keep changes small and reviewable. Update `README.md` as you go.
- If a detail isn't specified, choose the simplest option that respects the two seams, and note
  the choice in your summary.

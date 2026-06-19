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

## Active phase

The current phase and its scope live in `docs/ROADMAP.md`; the detailed task pack for the active
phase is `docs/PHASE_<X>_TASKS.md`. **If you're unsure which phase is active, ask the human — do
not assume.** Build only what the active phase's pack calls for; everything else is explicitly
deferred to a later phase. (Phase A — "Proof of Loop," a single local segment — is complete;
later phases add the world engine, more DJs, the VPS, public broadcast, etc.)

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
  - **Batch API** — the nightly generation is a batch job; run it through the Batch API (50% off).
  - **Prompt caching** — cache the stable canon / character cards / system prompt so each call
    pays full price only for the small variable part (~90% off cached input). The provider
    abstraction must support a cached-context path from the start.
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

### Monorepo: the web app (`/web`)

The repo is a monorepo. The Python **station backend** stays at the root (`src/`, `config/`, etc.)
and is never built or deployed by Vercel. Alongside it, **`/web`** is a self-contained Next.js
(App Router + TypeScript + Tailwind) app — the public site, deployed to **settlementradio.com** via
**Vercel with Root Directory = `web`**. It started as the A2 coming-soon page and **grows into the
audio player + studio in Phase C** (new routes in the same app, pointing at the live stream). The
two halves run independently, so web work and the Python pipeline don't block each other. Web
secrets live in `web/.env.local` (and as Vercel env vars), separate from the root `.env`.

## Engineering standards (the station backend — apply from now on)

These keep an unattended, 24/7, long-lived system maintainable. They apply to the Python
**station backend**. The `/web` coming-soon app may be pragmatic/temporary and need not meet all
of these.

- **Config over hardcoding.** All tunable values — model tiers, file paths, DB connection,
  segment defaults, buffer depth, provider names — come from ONE typed settings module
  (`src/config.py`, loaded from env via `pydantic-settings`). No magic numbers or literal config
  strings scattered in code. Code reads `settings.X`, never a raw literal.
- **Structured logging, never `print()`.** Use Python `logging` (structured/JSON, e.g.
  `structlog`) configured once, with levels (debug/info/warning/error). Every external call and
  every batch step logs start/outcome. This is how you'll diagnose a 3 a.m. failure you didn't
  watch — it is not optional polish for a 24/7 system.
- **Error handling + retries on external calls.** Wrap Claude / TTS / DB calls with sensible
  failure handling and bounded retries; on failure, fall back or fail loudly into the logs — never
  silently produce nothing.
- **Lint + format automatically.** Use `ruff` (lint + format) configured in `pyproject.toml`, and
  run it (plus a fast secrets scanner) on every commit via **pre-commit** hooks. Keep hooks fast —
  no test suite in pre-commit, or it gets bypassed.
- **Type hints throughout**, especially on the seams and public functions.
- **Tests are surgical, not exhaustive.** Test the bits with real logic where a silent bug would
  hurt (e.g., the world clock and the relative-time renderer). Don't chase coverage on glue code.
- **Secrets:** only in `.env` locally; on any server, not world-readable and never in the repo.

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

- Read `docs/ARCHITECTURE.md` and `docs/CANON.md`, plus the task pack for the **active phase**
  (`docs/PHASE_<X>_TASKS.md` — `docs/ROADMAP.md` lists the phases; ask the human if unsure which
  is active), before coding.
- Work **task by task** from the active phase's task pack, in order. After each task, state what
  you did and exactly how the human can verify it.
- Keep changes small and reviewable. Update `README.md` as you go.
- If a detail isn't specified, choose the simplest option that respects the two seams, and note
  the choice in your summary.

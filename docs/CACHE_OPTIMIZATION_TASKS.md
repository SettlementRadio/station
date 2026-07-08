# CACHE_OPTIMIZATION_TASKS.md — CO: Shared-bible prompt cache (a cost-lever pack)

> A **cross-cutting cost-lever** pack, not a numbered Phase D sub-pack. It exists because the Phase D
> standing principle **"cost levers stay mandatory — D's volume re-justifies them, revisit per sub-pack"**
> (`docs/PHASE_D_OVERVIEW.md` §2) applies to the *whole* built pipeline once it runs 24/7. Work in order,
> one task at a time: implement → show + how to verify → stop for review.
>
> **Read first:** `docs/ARCHITECTURE.md` (Seam #1 — the `llm.generate` contract), `src/providers/llm.py`
> (`generate`, `generate_batch`, `_system_blocks`), `src/world/context.py` (`AssembledContext`,
> `_render_core`), `docs/PHASE_D_OVERVIEW.md` §2 (cost levers + observability). For current model IDs,
> pricing, and the prompt-caching/Batch APIs, consult the `claude-api` skill — **do not answer from memory.**
>
> **Depends on:** the pipeline being built (per-segment formats + the world tick already emit
> `cached_context`). No new world state, no schema change, no new provider. **Purely a cache-topology +
> telemetry change** behind the existing seam.

**The one finding this pack acts on.** The world bible is ~40k words (~50k tokens) — the largest stable
block in every prompt. Today `context._render_core` glues the bible and the DJ character cards into **one
string**, and `llm._system_blocks` wraps that whole string in **one `cache_control` breakpoint**. Because
the cache is a prefix match keyed on the full block up to the breakpoint, **each distinct speaker set
caches its own private copy of the bible** — talk (`vell+wren`), news (`thorn`), music/commercial
(`vell`), grid speaker-overrides, and the tick (bible-only) never share it. A single top-up that touches
several formats re-writes the 50k-token bible several times over. Splitting the cache into **two
breakpoints — bible first, cards second — makes the bible one shared entry every caller reads from.**

**Why this is provably quality-neutral (the core claim to defend).** Prompt caching is **transparent to
generation**: `cache_control` breakpoints change *what is billed*, never *what the model sees*. The text
the model receives before the split (`bible+cards` then `dynamic`) is **byte-identical** to the text after
the split (`bible`, then `cards`, then `dynamic`) — same tokens, same order. So "no quality impact" is not
a hope to measure; it is an **invariant to assert** (CO1). We still measure empirically (CO4), but the
guarantee is structural.

**The discipline (same bar as every pack).**
- **Behind the seam.** All of this stays inside `providers/llm.py` + `world/context.py` + the call sites.
  No vendor specifics leak upward; `llm.generate`'s public contract stays provider-agnostic (a future
  provider that ignores `cache_control` must still get correct output — the blocks concatenate to the same
  prompt). See CLAUDE.md "two load-bearing seams."
- **Measure before you touch (CO0 first).** No optimization lands without a recorded BEFORE baseline from
  the real seeded stack. "It should be cheaper" is a guess; the telemetry is the proof.
- **Prove both directions.** The pack is done only when there is (a) a recorded **cost** delta showing the
  bible stops being re-written per speaker-set, and (b) a **quality-equivalence** proof that the model
  input is unchanged — the before/after tests the reviewer asked for.

**Definition of done for CO:** the bible is emitted as its own shared `cache_control` block (1h TTL) with
the cards as a second block; the model-visible prompt is byte-identical to pre-split (asserted by test);
usage telemetry logs the `cache_creation` / `cache_read` / `input` token split; a BEFORE and an AFTER
measurement are recorded side-by-side showing the drop; `docs/ARCHITECTURE.md` + `docs/ADMIN_MANUAL.md`
updated, DEVLOG entry appended; `ruff`/`pytest` green.

---

## CO0 — Baseline: usage telemetry + capture the BEFORE numbers
**Goal:** make the cache spend visible and record where it stands today, before any change.
**Do:**
- Extend the existing usage telemetry (OVERVIEW §2 observability) — the `llm_generate_done` log in
  `providers/llm.py` and the batch rollup in `_map_batch_result` — to emit the three token fields the
  prompt-cache economics turn on: `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`
  (read from `message.usage`). Today the seam only logs `cached=bool(...)`, which can't show a silent miss.
- Add a small **repeatable cost probe** (a `make` target or a `tests/`-adjacent harness, e.g.
  `python -m src.costprobe`) that, on the seeded local stack, runs one representative **mixed** cycle —
  talk + news + music + commercial (the distinct speaker sets) twice back-to-back — and rolls up the token
  split per tier. Two passes is the point: pass 2 is where a *shared* bible would read from cache.
- **Record the BEFORE baseline** in this pack (a short table) and in the DEVLOG-to-be: per format, the
  bible's `cache_creation` vs `cache_read` on pass 2. Expectation to confirm: today each format shows its
  own bible `cache_creation` (no cross-format read) — the waste this pack removes.
**Done when:** the seam logs the token split; a repeatable probe exists; a BEFORE table is recorded showing
the bible re-created per speaker-set.

## CO1 — The equivalence guardrail (write the test BEFORE the change)
**Goal:** lock the invariant that the change must not break — the model-visible prompt is unchanged.
**Do:**
- Add a test (extend `tests/test_context.py` + a new `tests/test_llm_cache.py`) that captures, for each
  format's assembled context, the **exact concatenated text** the model receives: the joined `.text` of
  the system blocks + the user prompt. Golden-snapshot it against the current (pre-split) output on a
  **fixed clock** and fixed seed.
- State the invariant explicitly in the test: after the split, `"".join(b["text"] for b in system_blocks)`
  must equal the pre-split single-string content **byte-for-byte** — only the number/placement of
  `cache_control` markers may differ.
**Done when:** an equivalence/golden test exists and passes against current code, pinning the exact prompt
bytes per format. (This test is what makes CO2 safe: if the split alters model input, it goes red.)

## CO2 — Split the cached prefix into bible + cards breakpoints (the core change)
**Goal:** the bible becomes one shared cache entry across every speaker set and the tick.
**Do:**
- `world/context.py`: expose the **bible** and the **cards** separately instead of pre-joining them in
  `_render_core` (e.g. `AssembledContext.bible` + `AssembledContext.cards_text`, keeping `cached_context`
  as a computed back-compat join so nothing breaks mid-migration).
- `providers/llm.py`: teach `generate` (and `BatchRequest` / `generate_batch`) a **two-part stable
  prefix** — a `bible` block and a `cards` block — and have `_system_blocks` emit them as **two `text`
  blocks each with its own `cache_control`**, followed by the uncached per-call `system`, then the user
  `prompt`. The single-`cached_context` path stays supported (it maps to one block) so callers migrate
  incrementally. Keep well under the 4-breakpoint limit (this uses 2).
- Update the call sites to pass bible + cards separately: `writer.py`, `formats/music.py`,
  `formats/commercial.py`, `formats/news.py` (both call sites), `writers/conversation.py` (all three:
  showrunner, orchestrator, continuity). The world tick already sends **bible-only** as its cached prefix —
  after the split its bible block is byte-identical to the segment writers', so it shares when temporally
  close (and its internal batch sharing is unchanged).
- Confirm the bible block clears the model's minimum cacheable prefix (Sonnet's is well under 50k tokens —
  verify via the `claude-api` skill, don't assume).
**Done when:** the bible is one shared `cache_control` block ahead of the variable cards for every format;
**CO1's equivalence test is still green** (model input unchanged); `ruff`/`pytest` green.

## CO3 — 1-hour TTL on the bible block
**Goal:** keep the static bible warm across top-ups instead of re-writing it every 5-minute cycle.
**Do:**
- Add a typed setting (e.g. `llm_cache_bible_ttl: str = "1h"`, config-over-hardcoding) applied **only** to
  the bible block's `cache_control`; the cards and dynamic parts stay on the default (5-min) ephemeral TTL.
- One-line rationale in the config comment: the bible changes only on a canon edit + re-seed, so a 1h TTL
  trades a 2× write (vs 1.25×) for far fewer writes — a win at any cadence above ~3 top-ups/hour, which
  continuous operation guarantees; it also protects the nightly batch (batches can run up to an hour).
**Done when:** the bible block carries a configurable 1h TTL; cards/dynamic unchanged; tests green.

## CO4 — AFTER: re-measure the win + prove no quality change (the before/after)
**Goal:** the reviewer's ask — show it works *and* show it didn't touch quality.
**Do:**
- **Cost (it works):** re-run the CO0 probe unchanged and record the AFTER table **beside** BEFORE. Assert
  the shift: on pass 2 the bible reads from cache across *all* formats (one `cache_creation` shared, the
  rest `cache_read`) instead of one `cache_creation` per speaker-set. State the measured reduction in
  bible `cache_creation` tokens per cycle.
- **Quality (no impact) — two proofs:**
  1. **Structural (the strong one):** CO1's equivalence test is green — the concatenated model input is
     byte-identical before and after, so generation cannot differ by construction.
  2. **Empirical (corroboration):** an A/B on a **fixed clock + fixed seed** — generate the same set of
     segments (talk/news/music) on pre-split vs post-split code and diff the scripts. With identical input
     they match modulo model nondeterminism; record the diff (expected: none, or within sampling noise).
- Write a one-paragraph pass/fail summary (cost delta + both quality proofs) for the DEVLOG.
**Done when:** BEFORE and AFTER numbers sit side-by-side showing the bible stops being re-created per
speaker-set; the equivalence test is green; the A/B diff is recorded; the summary is written.

## CO5 — Document, log, link
**Goal:** the new cache topology is written down where the next reader (and Phase E) will look.
**Do:**
- `docs/ARCHITECTURE.md` (Seam #1): document the **two-breakpoint cache topology** (shared bible block +
  per-speaker cards block) and the bible's 1h TTL, as the standing shape of the cost lever — one terse
  paragraph, not an essay.
- `docs/ADMIN_MANUAL.md`: a one-line operator note — *editing the bible (`docs/canon/`) invalidates the
  shared cache on next generation; that is expected and self-heals* — tagged `→ Phase E panel` if it
  surfaces any dial.
- Append a DEVLOG entry (use the template): Focus = shared-bible prompt cache; Decisions = two breakpoints
  + 1h bible TTL; Changed = `providers/llm.py`, `world/context.py`, call sites, tests; Why = the bible was
  re-cached per speaker-set; include the CO4 cost delta. Add a `📣 Postable:` line (a clean cost-mechanism
  story).
- Note in `docs/PHASE_D_OVERVIEW.md` §2 (cost levers) that the shared-bible cache is now the as-built
  topology, so future sub-packs inherit it.
**Done when:** ARCHITECTURE + ADMIN_MANUAL updated; DEVLOG appended with the measured delta; the OVERVIEW
cost-lever note added; `ruff`/`pytest` green.

---

## Measurements

### BEFORE (CO0) — recorded 2026-07-08, `make costprobe`, tier=sonnet

One mixed cycle (talk + news + music + commercial) run twice back-to-back on the seeded stack.
Numbers are tokens from `message.usage`; the stable core (bible + cards) measures ~31.3k tokens
(bible ≈ 31k; the cards are the small remainder — talk's two cards make it 31,614).

| pass | format | input | cache_creation | cache_read |
|---|---|---:|---:|---:|
| 1 | talk | 20 | 31,614 | 0 |
| 1 | news | 20 | 31,284 | 0 |
| 1 | music | 20 | 31,297 | 0 |
| 1 | commercial | 20 | 0 | 31,297 |
| 2 | talk | 20 | 0 | 31,614 |
| 2 | news | 20 | 0 | 31,284 |
| 2 | music | 20 | 0 | 31,297 |
| 2 | commercial | 20 | 0 | 31,297 |
| 1 | **total** | 80 | **94,195** | 31,297 |
| 2 | **total** | 80 | **0** | 125,492 |

**Reading it:** exactly the waste this pack predicts. Each distinct speaker set writes its own
private copy of the ~31k-token bible on a cold cycle — three `cache_creation` writes (talk, news,
music) where a shared bible block would need one (~62k redundant cache-write tokens per cold
cycle, at the 1.25× write premium). Commercial reads music's entry only because both happen to be
`vell` (byte-identical prefix), not because the bible is shared. On pass 2 every format reads —
but each from its own copy, so the redundancy repeats on every cache expiry and every speaker-set
roster change. AFTER table (CO4) goes here beside it.

---

## Explicitly NOT in this pack (→ elsewhere)
- **Switching the LLM provider** (the DeepSeek/Kimi/Qwen question) → a separate decision. This pack makes
  the *current* provider's caching correct first; a provider swap is evaluated on top of a clean baseline,
  not instead of it.
- **Changing model tiers / what the writers do** → the routing (Haiku/Sonnet/Opus) and the prompts are
  unchanged; this pack only alters *how the stable prefix is cached*, never the tier or the content.
- **Changing what goes in the bible or the cards** → canon authoring is D1; this pack moves bytes between
  cache blocks, it does not add, cut, or reword a single fact.
- **TTS cost** → out of scope. Kokoro/ElevenLabs is the other (larger) cost ceiling and is a different
  lever behind the TTS seam; this pack is text-only.
- **A new telemetry surface / dashboard** → CO0 *extends* the existing usage logging (OVERVIEW §2); the
  D6 status console / any richer rollup is its own work.

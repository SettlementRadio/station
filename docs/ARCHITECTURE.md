# ARCHITECTURE.md

The long-term design and the two seams that must not be violated. Each layer carries a per-phase
status line. The point of writing it down is so the small early code is shaped to grow into the big
system without rewrites. **Status: Phase A complete, Phase B ("The Mind") complete; Phases C–E are
planned in detail (`docs/ROADMAP.md` + the phase packs) and previewed in each layer's forward note
below.** Layers 1–3 are now real (vector retrieval excepted); Layers 4–6 are still Phase A's minimal
forms; Layer 0 (listener inbound) arrives in Phase E.

## Layered design

0. **Interaction (inbound)** — *new in Phase E; the one genuinely new concept.* Listener inbound —
   requests, dedications, messages (the canon's "letters between worlds") — captured,
   **safety-gated**, and fed into the writers' room as material a DJ reads on air. The mirror of
   Layer 6: everything else in this doc flows outward; this is the only inward path. *Phase A–D: none.*

1. **World state & time** — event store (in-world timestamps), a world clock (real→in-world
   mapping), a progression engine, a relative-time renderer ("in five days" → "yesterday").
   *Phase A: skipped (real time straight into the prompt; +600y computed inline).*
   **Phase B: REAL.** Postgres world store (`src/world/store.py`, the only SQL), seeded reproducibly
   from `docs/CANON.md` (`seed.py` + `canon_source.py`); `clock.py` is the single real↔in-world
   source (+600y); `events.py` gives `status_of()` + `relative_phrase()` and the progressing-event
   demo.
   **Phase D (forward):** a generative, nightly **world-tick** invents new in-world happenings
   consistent with the bible and *advances* running ones, so the present moves on its own. A single
   `events` row grows into a **story with an arc** — a lifecycle (rumoured → upcoming → happening →
   developing → past) plus accumulating beats — which the clock above frames as future/now/past for
   free. (The tick is generative, so it uses Layer 3's machinery to write into this layer's state.)
   Two **media catalogs** join the world store here too: a **`tracks`** table (the song library —
   id, title, in-world artist, mood/tags, duration, `file_path`, licence note; seeded from a
   human-editable source the way canon is) and a **`sponsors`** table (real "Powered by" reads —
   text, optional audio, run window). The DB holds only metadata; the audio files live under
   `assets/` (see Layer 4), never in the database.
2. **Knowledge & RAG** — canon/cast/events in Postgres + pgvector; retrieval + Claude prompt
   caching. *Phase A: skipped (canon read from `docs/CANON.md`).* **Phase B: REAL except vectors.**
   `world/context.py` `assemble()` returns a cached stable core (bible + cards) + a dynamic slice
   (events near now, topic/all canon) via **structured** date/status/tag queries. Prompt caching is
   in use. **Vector RAG is a documented, UNUSED stub** (`providers/embeddings.py`); pgvector is not
   installed — added only when context outgrows the cache or needs semantic recall.
   **Phase D (forward):** the bible moves from one `docs/CANON.md` into a `docs/canon/` **folder**
   (history, literature, finance, war, nations, peoples, geography, religion, culture, tech, cast);
   the seeder reads the whole folder and **tags** facts (today they're untagged, so retrieval falls
   back to "all"). pgvector activates here for semantic recall — including a DJ's **memory/history**
   pulled from the event/story log.
3. **Writers' room (Claude agents)** — showrunner → continuity editor → DJ writer(s) →
   conversation orchestrator; output is a structured **script**. *Phase A: a single function writing
   one DJ's segment.* **Phase B: REAL (single-call).** `writers/conversation.py` runs showrunner →
   orchestrator (both personas in ONE call — cheaper, more coherent) → continuity (sonnet, escalate
   to opus). `src/formats/` adds `news`/`talk`/`music` skeletons, each `(now, ctx) -> Segment`;
   `talk` wraps the conversation. Continuity is **advisory** (logged, not yet gating).
   **Phase C (forward):** continuity + safety become blocking **gates**, and the showrunner picks the
   DJ pairing/framing from the **clock** (fixing the hardcoded night→dawn handover). **Phase D
   (forward):** the one-shot `news` format grows into a **news desk** that reads the story log and
   reports it like a real station — stories **recur and evolve** through the day, framed past/now/
   future, with **continuity** across segments — plus a **freshness/anti-repetition** memory (what
   aired recently: topics, openings, beats) so 24/7 output never loops.
4. **Production** — script → TTS → mix with jingles/beds → emit a `Segment`. *Phase A: TTS only;
   mixing deferred to the playout fallback.* **Phase B: unchanged shape, TTS now local.** Kokoro is
   the default backend (free/unlimited); two logical voices (`vell_night`, `dj_two`) alternate and
   are stitched per-turn via `tts.concat_audio`. Still no jingle/bed mixing step.
   **Phase D (forward):** real Layer 4 mixing — station idents, jingles, **beds + stings** with
   **ducking** (a bed sits under speech; a sting fires before news). Voice gains **emotion** (the
   flagship path — Kokoro can't carry it) and a **pronunciation lexicon** for invented names (both
   reserved in Seam #1b). **Three media kinds, three stores:** (a) **jingles / idents / stings /
   beds** — a small, static, curated file-set in `assets/{idents,themes,stings}/` keyed by *use* via
   a tiny registry (no DB), aired as non-spoken Segments (see `docs/JINGLE_PROMPTS.md`); (b) **songs**
   — tracks in `assets/music/`, catalogued by the Layer 1 `tracks` table, which the Layer 5 scheduler
   drops into the `music` format's `[SONG]` slot (the DJ back-announces from the catalog metadata;
   clearance is a separate human call); (c) **commercials** — mostly *generated* (Layer 3), scheduled
   in Layer 5. All audio stays under `assets/` / `segments/` (gitignored), never in the DB.
5. **Scheduling & playout** — a scheduler decides what/when (buffer depth = a parameter);
   Liquidsoap plays segments with a fallback chain. *Phase A: loops the one segment.* **Phase B:
   still no scheduler.** `make buffer` (`src/buffer.py`) is a one-shot *generator* of a varied run +
   JSON sidecars + a manifest (the shape a Phase C scheduler will read) — not a scheduler, and its
   `length_target_sec` accounting is metadata, not measured audio.
   **Phase C (forward):** a real scheduler — rolling buffer to a depth dial, **measured** durations
   (ffprobe), regenerate-on-failure, a never-dead fallback chain, and **retention GC** (C2.5) that
   deletes aired one-shot renders so `segments/` stays bounded — the reused disclosure ident and
   everything under `assets/` are never touched. **Phase D (forward):** it reads a
   **programming model** — named programs, dayparts, a weekly routine (which show, which DJs, when) —
   inserts **songs** (from the `tracks` catalog) into the music slot, and schedules **commercial
   breaks** on a daypart cadence: an in-world `commercial`/`promo` Segment (generated by Layer 3) or
   a real `sponsors` "Powered by" read. **Phase E (forward):** the depth dial → ~0 for near-live.
6. **Distribution** — Icecast → web/YouTube. *Phase A & B: local Icecast only; the `/web` app is the
   coming-soon page (the player + studio land in Phase C).* **Phase C (forward):** YouTube Live relay
   + the web player, both showing the AI disclosure. **Phase D:** the player surfaces **now-playing /
   program info**. **Phase E:** more channels on the same engine.

Cross-cutting: provider abstraction (**real** — `llm`/`tts`, plus the `store` SQL seam and the
`embeddings` stub); content-safety gate (**still a no-op placeholder**, `writer.safety_check`; the
real gate lands in C and also guards Layer 0 inbound in E); AI disclosure (**field only**,
`Segment.disclosure`; spoken + shown in C); **operator/management console** — a read-only **status**
console in D (what's airing, buffer depth, last night's run, the story log) growing into a **write
control surface** in E (edit the grid, allocate + CRUD DJs, approve/reject stories, trigger regen).

## Seam #1 — Provider abstraction (build in Phase A)

Two modules are the *only* place vendor SDKs are imported.

```python
# src/providers/llm.py  (as built)
from collections.abc import Callable

def generate(
    prompt: str,
    *,
    system: str | None = None,
    model: str = "sonnet",   # "haiku" | "sonnet" | "opus" — mapped to real model IDs internally
    cached_context: str | None = None,  # large stable text (canon/cards) → sent as a cache breakpoint
    max_tokens: int = 4000,
    on_token: Callable[[str], None] | None = None,  # streamed text deltas → caller progress
    timeout: float = 120.0,                          # per-request timeout (seconds)
) -> str:
    """Return Claude's text output. Implementation selected by env (ANTHROPIC_API_KEY).

    The call is STREAMED internally (the first bytes arrive immediately; a non-streaming
    call blocked silently at the socket for the whole ~25s generation and looked hung).
    `on_token` fires per text delta so callers can show progress; the full text is still
    returned as one string — streaming is an implementation detail of the seam. `timeout`
    makes a genuine network stall fail fast instead of blocking indefinitely.

    Model routing (logical tier → real ID):
      haiku  → claude-haiku-4-5-20251001   # high-volume, low-stakes, near-live
      sonnet → claude-sonnet-4-6           # DEFAULT: DJ scripts, showrunner, continuity
      opus   → claude-opus-4-8             # hard reasoning only; rare
    Cost rules:
      - cached_context MUST be passed as a prompt-caching breakpoint (canon/cards/system),
        so repeat calls pay ~0.1x on that input. (Phase A: in use.)
      - Batch API (50% off) is a "revisit when it pays" lever, not a MUST: with free local Kokoro
        the text bill is trivial, so B6/C deferred it — build it only when text volume (more DJs/
        channels/near-live) justifies it. The cached-context path above is the standing cost lever.
    """

# src/providers/tts.py  (as built)
def synthesize(
    text: str,
    *,
    voice: str,              # a logical voice name from a voice registry, NOT a vendor voice id
    emotion: str | None = None,  # a logical emotion from tts.EMOTIONS (D9.0) — see note below
    out_path: str,
) -> str:
    """Render speech to an audio file at out_path; return the path.
       Implementation selected by env TTS_PROVIDER (Phase B made kokoro the default).
       The logical-voice → vendor-preset mapping is DATA as of D9.2: config/voices.yaml
       (settings.tts_voices_path), one entry per DJ with all engines — adding a DJ never
       edits tts.py. Fail loud: unknown voice / missing engine mapping / missing file all
       raise, and `make seed-canon` pre-validates the cast against the registry (seed.py).
         - kokoro      (DEFAULT) — self-hosted Kokoro-82M, local/free/unlimited (B0). The
                                    workhorse. All 10 DJs mapped to DISTINCT presets
                                    (verified locally). Emits 24kHz WAV → _to_mp3().
         - elevenlabs            — cloud flagship; a runtime-switchable public voice via
                                    settings.tts_provider (free tier ≈ 2 seg/mo). All 10 DJs
                                    mapped (the 8 new ids = premade-roster picks, confirm at
                                    the C6 listen), so either backend voices any segment —
                                    voice is a config choice. (The free-tier quota, not the
                                    seam, is the limit; see C6.)
         - say                   — macOS built-in `say`, offline TEST voice. Emits AIFF → _to_mp3().
         - <streaming/self-hosted> — a future near-live backend (Phase E): a streaming TTS (e.g.
                                    Cartesia) or self-hosted engine behind this same seam. An
                                    `orpheus` stub holds the place today (NotImplementedError).
       `emotion` is WIRED as of D9.0: a logical name (warm|wry|somber|bright|urgent — the
       `EMOTIONS` vocabulary; validated + defaulted by `resolve_emotion`, operator default
       `settings.tts_emotion_default`) maps on the **elevenlabs** backend to the vendor's
       expressiveness controls (`_ELEVENLABS_EMOTIONS` → `VoiceSettings` stability/style/speed);
       on kokoro/say it stays accepted-and-ignored (no such knob), so emotion is AUDIBLE only on
       the flagship path — the C6 launch-voice decision. The per-emotion numbers are a starting
       tune, to be retuned by ear in C6 (see PHASE_C_TASKS C6). A **pronunciation** hint (a lexicon
       for invented names) is the remaining knob to add on this seam (D9.1). Non-mp3 backends share
       `_to_mp3()` (ffmpeg); `concat_audio()` stream-copies per-turn clips into one multi-voice
       talk segment."""
```

Rules: callers pass *logical* model tiers ("haiku/sonnet/opus") and *logical* voice names; the
modules map those to the current vendor's real IDs. Swapping vendors = editing one module + env,
nothing else.

## Seam #2 — The Segment (build in Phase A)

```python
# src/segment.py
from dataclasses import dataclass, field

@dataclass
class Segment:
    id: str
    format: str               # "talk"|"news"|"music"|"ident"|"sting"|"song"|"commercial" ...
    length_target_sec: int    # the DIAL: 3600 for an hour, 60 for near-live. NEVER hardcode.
    air_time: str | None = None   # ISO time this should air; None = "whenever"
    lead_time_sec: int = 0        # how long before air it may be generated. The other DIAL.
    script: str | None = None
    audio_path: str | None = None
    disclosure: bool = True       # AI-generation disclosure attached
    meta: dict = field(default_factory=dict)
```

The whole pipeline is `make_segment(...) -> Segment`: write script (Layer 3) → synthesize
(Layer 4) → return a `Segment` with `audio_path` set. As built (`src/produce.py`), the signature
is:

```python
# src/produce.py  (as built)
def make_segment(now_iso: str, *, length_target_sec: int = 300) -> Segment:
    """Generate one talk Segment for `now_iso`: script → audio → Segment."""
```

The design intent (length is a dial, not a constant) holds: `length_target_sec` is a keyword
input with a default, never hardcoded downstream, so the same path later serves an overnight block
or a 60-sec near-live drop — only the number and the model/TTS tier change. Two notes vs. the
original sketch: (1) the input is a real-time ISO string + a length dial, not a `spec` object;
(2) `lead_time_sec` exists on the `Segment` but is not yet an input to `make_segment` (it becomes
one when scheduling/near-live lands).

Phase D adds more `format`s the producer doesn't *write* but the scheduler still airs:
`ident`/`sting`/`jingle` (pre-rendered assets) and `song` (a track from the `tracks` catalog dropped
into the `music` slot) carry `audio_path` with `script=None`; `commercial`/`promo` (in-world ad /
station promo) are *generated* like any spoken segment (script + audio). The Segment shape already
holds all of them — `audio_path`, `meta` (e.g. the track/sponsor id), the disclosure field — so
playout treats them as ordinary segments. No new model below the seam.

## Phase A data flow (what to actually build)

```
docs/CANON.md  ─┐
real clock ─────┤→ llm.generate(...) → script
                                         │
                                         ▼
                              tts.synthesize(...) → segment audio file
                                         │
                                         ▼
                          Liquidsoap loops it → local Icecast → browser
```

## Phase B data flow (what actually runs now)

```
docs/CANON.md ──seed──> Postgres (canon/cast/events/state)
                              │
                  context.assemble(now, speakers) → cached core + dynamic now
                              │
        ┌─────────────────────┴─────────────────────┐
   single-DJ writer                         two-DJ writers' room
   (writer/produce, formats news/music)     showrunner→orchestrate→continuity
        └─────────────────────┬─────────────────────┘
                       safety_check (no-op) → script
                              │
                tts.synthesize (Kokoro) [+ concat_audio for talk] → segment mp3 (+ JSON sidecar)
                              │
              make buffer → run manifest   →   (Phase C: scheduler) → Liquidsoap → Icecast
```

## How later phases plug in (no rewrite)

- **World/time engine:** *done in Phase B* — Layers 1–3 feed the writers' room; the script step
  calls `context.assemble` (structured retrieval + the relative-time renderer). The Segment and
  providers didn't change. Vector retrieval drops into the `embeddings` + `store` seams when needed.
- **Phase C — safe · continuous · public:** the scheduler reads the buffer-manifest shape with
  *measured* durations; the advisory continuity check + `safety_check` no-op become blocking
  **gates**; the showrunner frames by the clock (the C1 handover fix); disclosure gets spoken +
  shown; a never-dead fallback covers DB/TTS failures. Nothing below the Segment seam changes.
- **Phase D — the living world:** the bible becomes a `docs/canon/` folder + pgvector (Layer 2); a
  generative **world-tick** + **story arcs** make Layer 1's present move; a **news desk** +
  **freshness memory** ride Layer 3; **sound design** (idents/jingles/beds/stings + ducking) and
  **songs** land in Layer 4/5; voice gains **emotion + pronunciation** (Seam #1b); the scheduler
  reads a **programming model** (programs/dayparts/weekly); a read-only **status console** appears.
  media catalogs (`tracks`/`sponsors`) join Layer 1, and **commercial breaks** schedule in Layer 5.
  The two seams and the Segment are unchanged — new `format`s (ident/sting/song/commercial) reuse it.
- **Phase E — scale, near-live & control:** smaller `length_target_sec` + `lead_time_sec`, route to
  Haiku, swap TTS to a **streaming** provider (Cartesia) — same `make_segment`; the status console
  grows into a **write control surface**; **Layer 0 inbound** (listener messages) feeds the writers'
  room through the safety gate; more channels = more schedulers on the same Layer 1 state.
- **Beyond:** more surfaces reading the same Layer 1 state. Nothing below the seams changes.

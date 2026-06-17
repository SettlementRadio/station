# ARCHITECTURE.md

The long-term design and the two seams that must not be violated. Most of this is *future*; the
"Phase A" notes say what actually gets built now. The point of writing it down is so the small
Phase A code is shaped to grow into the big system without rewrites.

## Layered design

1. **World state & time** — event store (in-world timestamps), a world clock (real→in-world
   mapping), a progression engine, a relative-time renderer ("in five days" → "yesterday").
   *Phase A: skipped. The current real time is passed straight into the prompt; the clock is just
   `real_time + 600 years` computed inline.*
2. **Knowledge & RAG** — canon/cast/events in Postgres + pgvector; retrieval + Claude prompt
   caching. *Phase A: skipped. Canon is read from `docs/CANON.md` into the prompt.*
3. **Writers' room (Claude agents)** — showrunner → continuity editor → DJ writer(s) →
   conversation orchestrator; output is a structured **script**. *Phase A: a single function that
   asks Claude to write one DJ's 5-minute segment from the canon. No multi-agent yet.*
4. **Production** — script → TTS → mix with jingles/beds → emit a `Segment`. *Phase A: built,
   minimally — TTS only. Mixing was deferred; the bed/jingle role is instead filled by the
   playout fallback in `radio.liq` (Layer 5), so no mixing step exists in production yet.*
5. **Scheduling & playout** — a scheduler decides what/when (buffer depth = a parameter);
   Liquidsoap plays segments with a fallback chain. *Phase A: Liquidsoap loops the one segment,
   with a silence-avoidance fallback. No scheduler yet.*
6. **Distribution** — Icecast → web/YouTube. *Phase A: local Icecast only.*

Cross-cutting (future): provider abstraction (build now), content-safety gate (placeholder now),
AI disclosure (placeholder now), operator console (later).

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
      - The nightly generation pipeline MUST submit via the Batch API (50% off), not live calls.
        (Phase B: deferred. Phase A generates one segment on demand via a live call — no Batch
        path is built now. The cached-context path above is the Phase A cost lever.)
    """

# src/providers/tts.py  (as built)
def synthesize(
    text: str,
    *,
    voice: str,              # a logical voice name from a voice registry, NOT a vendor voice id
    emotion: str | None = None,  # reserved — accepted but not yet wired to a vendor knob
    out_path: str,
) -> str:
    """Render speech to an audio file at out_path; return the path.
       Implementation selected by env TTS_PROVIDER:
         - elevenlabs  (DEFAULT) — ElevenLabs API, the real Phase A voice.
         - say                   — macOS built-in `say`, offline/free/unlimited; a TEST voice,
                                    added after the ElevenLabs free tier (~2 segments/mo) ran dry.
                                    Emits AIFF → transcoded to mp3 via a shared `_to_mp3()` helper.
         - kokoro / orpheus      — planned self-hosted backends; raise NotImplementedError for now.
       Non-mp3 backends share `_to_mp3()` (ffmpeg) so the pipeline always lands an mp3."""
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
    format: str               # "talk" | "news" | "music" | "ident" ...
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

## How later phases plug in (no rewrite)

- **Near-live:** smaller `length_target_sec` + `lead_time_sec`, route to Haiku, swap TTS to a
  streaming provider. Same `make_segment`.
- **World/time engine:** Layers 1–2 start feeding the writers' room; the script step gains a
  retrieval call + the relative-time renderer. The Segment and providers don't change.
- **More channels / the wider +600yr world:** more schedulers and more surfaces reading the same
  Layer 1 state. Nothing below changes.

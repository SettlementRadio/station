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
   minimally (TTS only; mixing optional).*
5. **Scheduling & playout** — a scheduler decides what/when (buffer depth = a parameter);
   Liquidsoap plays segments with a fallback chain. *Phase A: Liquidsoap loops the one segment,
   with a silence-avoidance fallback. No scheduler yet.*
6. **Distribution** — Icecast → web/YouTube. *Phase A: local Icecast only.*

Cross-cutting (future): provider abstraction (build now), content-safety gate (placeholder now),
AI disclosure (placeholder now), operator console (later).

## Seam #1 — Provider abstraction (build in Phase A)

Two modules are the *only* place vendor SDKs are imported.

```python
# src/providers/llm.py
def generate(
    prompt: str,
    *,
    system: str | None = None,
    model: str = "sonnet",   # "haiku" | "sonnet" | "opus" — mapped to real model IDs internally
    cached_context: str | None = None,  # large stable text (canon/cards) → sent as a cache breakpoint
    max_tokens: int = 4000,
) -> str:
    """Return Claude's text output. Implementation selected by env (ANTHROPIC_API_KEY).

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

# src/providers/tts.py
def synthesize(
    text: str,
    *,
    voice: str,              # a logical voice name from a voice registry, NOT a vendor voice id
    emotion: str | None = None,
    out_path: str,
) -> str:
    """Render speech to an audio file at out_path; return the path.
       Implementation selected by env (TTS_PROVIDER=elevenlabs now; kokoro/orpheus later)."""
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

The whole pipeline is `make_segment(spec) -> Segment`: write script (Layer 3) → synthesize
(Layer 4) → return a `Segment` with `audio_path` set. Because `length_target_sec` and
`lead_time_sec` are inputs, the same function serves overnight batch and near-live later — only
the numbers and the model/TTS tier change.

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

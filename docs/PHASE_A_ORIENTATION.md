# PHASE A — Orientation & Retro

> Written at the close of Phase A ("Proof of Loop"), before Phase B planning. Phase A is complete:
> `make play` generates a fresh ~5-minute Vell segment (Claude → TTS) and serves it on a local
> Icecast stream the human can hear in a browser. This is the snapshot of what actually got built,
> how the code ended up, where it diverged from the original design, and what the build taught us.
> The canonical design lives in `docs/ARCHITECTURE.md` (now updated to match); this is the
> companion narrative.

## 1. Current repo tree

```
station/
├── CLAUDE.md
├── Makefile                  # generate / serve / play / stop / status
├── README.md
├── requirements.txt          # anthropic, elevenlabs, python-dotenv, requests
├── .env.example              # keys + ICECAST_SOURCE_PASSWORD + TTS_PROVIDER
├── config/
│   ├── icecast.xml           # local-only :8000, webroot → config/web
│   ├── radio.liq             # newest-file loop + never-dead fallback
│   └── web/index.html        # <audio> player + AI disclosure
├── docs/
│   ├── ARCHITECTURE.md       # the two seams + layered design (updated post-Phase-A)
│   ├── CANON.md              # the world bible (read into the prompt)
│   ├── PHASE_A_TASKS.md      # T0→T6 task list
│   ├── PHASE_A_ORIENTATION.md # ← this file
│   ├── DEVLOG.md             # one entry per session, T0→T6
│   ├── ROADMAP.md
│   └── ai-radio-marketing-strategy.md   # untracked
├── src/
│   ├── segment.py            # Seam #2: Segment dataclass
│   ├── writer.py             # Layer 3: script from canon + clock
│   ├── produce.py            # Layer 4: make_segment() → script→TTS→Segment
│   └── providers/
│       ├── llm.py            # Seam #1a: only Anthropic importer
│       └── tts.py            # Seam #1b: only TTS importer
├── segments/.gitkeep         # generated mp3s (gitignored)
└── assets/.gitkeep           # jingles/beds (gitignored)
```

Untracked: `.vscode/`, `docs/ai-radio-marketing-strategy.md`. Runtime dirs `.run/` and `.venv/`
exist and are gitignored.

## 2. The actual signatures

**`llm.generate`** — `src/providers/llm.py`
```python
def generate(
    prompt: str,
    *,
    system: str | None = None,
    model: str = "sonnet",                    # "haiku"|"sonnet"|"opus" → real IDs
    cached_context: str | None = None,        # canon → cache breakpoint
    max_tokens: int = 4000,
    on_token: Callable[[str], None] | None = None,   # added: streaming progress
    timeout: float = 120.0,                          # added
) -> str
```
Streams internally; returns the joined text as one string.

**`tts.synthesize`** — `src/providers/tts.py`
```python
def synthesize(
    text: str,
    *,
    voice: str,                  # logical name, e.g. "vell_night"
    emotion: str | None = None,  # reserved, not wired to a vendor knob
    out_path: str,
) -> str
```
Dispatches on `TTS_PROVIDER`: `elevenlabs` (default), `say` (macOS, offline), `kokoro`/`orpheus`
(NotImplementedError stub).

**`Segment`** — `src/segment.py` — matches the design doc **verbatim**:
```python
@dataclass
class Segment:
    id: str
    format: str
    length_target_sec: int        # required, no default
    air_time: str | None = None
    lead_time_sec: int = 0
    script: str | None = None
    audio_path: str | None = None
    disclosure: bool = True
    meta: dict = field(default_factory=dict)
```

## 3. Where the implementation diverged from ARCHITECTURE.md

(All of these are now reflected back in `docs/ARCHITECTURE.md`.)

1. **`generate` grew two params** — `on_token` and `timeout`. The original blocking text-in/
   text-out call looked frozen for the ~25s generation and kept getting Ctrl-C'd; we made it
   stream (T6 fix). Return type and the logical-tier contract are unchanged.
2. **A third TTS backend, `say`** — not in the original doc, which only named `elevenlabs` +
   future `kokoro/orpheus`. Added after ElevenLabs' free tier ran dry (~2 segments/month) so the
   loop is testable offline/unlimited. Lives entirely behind the seam, plus a shared `_to_mp3()`
   helper for non-mp3 backends.
3. **The pipeline isn't `make_segment(spec) -> Segment`** — the doc posited a `spec` object; what
   shipped is `make_segment(now_iso, *, length_target_sec=300) -> Segment`. Same intent (length is
   a dial, not a constant), but the input is a timestamp string + keyword dial, not a spec struct.
   `lead_time_sec` exists on the `Segment` but isn't yet an input to `make_segment`.
4. **Layer 4 mixing (jingles/beds) was not built** — the doc called it optional. Instead the
   *playout* layer (`radio.liq`) supplies the bed as the never-dead fallback (`assets/bed.mp3` →
   quiet sine). So "mix" moved from production into playout for Phase A.
5. **`safety_check()` placeholder exists in `writer.py`** — consistent with the doc's
   content-safety-gate intent; worth noting it's a real (no-op) seam in the script step, not just
   a future idea.

Everything else (the two seams, the +600yr computed clock, canon-as-cache-breakpoint, local
Icecast→browser) landed as designed.

## 4. Retro — what was fiddly, how it sounded, what surprised us

**What was fiddly:**
- **Liquidsoap install was the real time sink.** `brew install liquidsoap` is gone; built from
  source via `opam`, and had to explicitly add `lame` (mp3 encode) + `mad` (mp3 decode) or `%mp3`
  was "unsupported format" — it couldn't even read its own segments. Needed `CPATH`/`LIBRARY_PATH`
  → Homebrew for the C stubs on Apple Silicon. All now in the README.
- **Orphan Icecast processes** squatting port 8000 ("Could not create listener socket"). Fixed
  structurally by making `serve` depend on `stop`.
- **Browser wouldn't render a player for a bare mp3 mount** — `/settlement.mp3` showed an empty
  page until wrapped in `config/web/index.html`. Also `localhost` resolves to IPv6 `::1` first but
  Icecast binds IPv4, so the URL had to be the `127.0.0.1` literal.
- **The silent-socket "looks hung" problem** drove the streaming change.

**Script quality & voice:** The Sonnet 4.6 scripts came out coherent and genuinely in-character —
warm, unhurried night-shift Vell, ~700–800 words, with a correct computed "settlement time" check,
no stage directions leaking into the spoken text. Good enough that the script side feels like the
*cheap, solved* part. Rendered length lands ~246–256s (~4.1–4.3 min) against the 300s target — a
touch short, the one number worth tuning. ElevenLabs "Adam" was a serviceable Vell; `say`/"Daniel"
is an obvious test-only voice.

**What surprised us:** the cost shape inverted from intuition. **TTS is the entire cost ceiling**,
not the LLM — the canon caches to ~0.1x and scripts are near-trivial, but ElevenLabs' free tier
only covers ~2 full segments/month. That's the single most important fact for Phase B: nightly
batch generation is gated by *voice* credits, not Claude. It points at either self-hosted
Kokoro/Orpheus (the `_to_mp3` groundwork is already laid) or a paid voice tier as a Phase B
prerequisite — before the Batch API work is worth doing.

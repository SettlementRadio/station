# PHASE B — Orientation & Retro

> Written at the close of Phase B ("The Mind"), before Phase C planning. Phase B is complete
> (B0–B6): the world moved out of the flat file into a queryable Postgres store seeded from
> `docs/CANON.md`; a formal world clock + relative-time renderer make the station time-aware; a
> two-DJ conversation orchestrator (Vell night → Wren first-light) holds a real in-character
> exchange; three program formats (`news`/`talk`/`music`) fill proven skeletons; and `make buffer`
> generates a varied block of audio in one run — all voiced locally and free via Kokoro. This is
> the snapshot of what actually got built, the signatures Phase C will build on, where the code
> diverged from the plan, and what the build taught us (grounded in a real `make buffer` run whose
> artifacts are still on disk). The canonical design lives in `docs/ARCHITECTURE.md` (now updated to
> match); this is the companion narrative. Format mirrors `docs/PHASE_A_ORIENTATION.md`.

## 1. Current repo tree

```
station/
├── CLAUDE.md
├── Makefile                       # play / seed / demo / context / conversation / format / buffer …
├── README.md                      # full reproducible build (Kokoro, Postgres, pre-commit, …)
├── README_Backup.md               # tracked; superseded copy
├── LICENSE-CODE / LICENSE-CONTENT
├── requirements.txt               # anthropic, elevenlabs, kokoro, soundfile, psycopg[binary],
│                                   #   pydantic-settings, structlog, ruff, pre-commit, pytest
├── pyproject.toml                 # ruff lint+format config (line 88, py311, E/F/W/I/UP/B/C4/N)
├── .pre-commit-config.yaml        # ruff, gitleaks, no-direct-env guard, basics
├── .env.example                   # committed; keys + DB + provider/tuning knobs (no secrets)
├── .vscode/settings.json          # tracked
├── scripts/
│   └── check_no_direct_env.sh     # pre-commit hook: no os.getenv/os.environ outside config.py
├── config/
│   ├── icecast.xml                # local-only :8000, webroot → config/web
│   ├── radio.liq                  # newest-file loop + never-dead fallback (Phase A)
│   └── web/index.html             # <audio> player + AI disclosure (Phase A playout page)
├── docs/
│   ├── ARCHITECTURE.md            # the two seams + layered design (updated post-Phase-B)
│   ├── CANON.md                   # the world bible — human-edited SOURCE; seeds the DB
│   ├── ROADMAP.md
│   ├── PHASE_A_TASKS.md / PHASE_A_ORIENTATION.md
│   ├── PHASE_A2_WEB_TASKS.md
│   ├── PHASE_B_TASKS.md           # B0–B6 task pack
│   ├── PHASE_B_ORIENTATION.md     # ← this file
│   ├── DEVLOG.md                  # one entry per session (… B3, B4, B5, B6)
│   ├── HOWTO.md
│   └── MARKETING.md                # the marketing playbook + validatable milestones
├── src/
│   ├── config.py                  # B0.5 — the ONE typed settings module (pydantic-settings)
│   ├── logging_setup.py           # B0.5 — structlog, configured once (JSON default)
│   ├── retry.py                   # B0.5 — call_with_retry(): bounded retry for the seams
│   ├── segment.py                 # Seam #2: the Segment dataclass (unchanged from A)
│   ├── writer.py                  # single-DJ script writer + safety_check() placeholder
│   ├── produce.py                 # make_segment(): single-DJ talk Segment (Phase A path, B3-rewired)
│   ├── buffer.py                  # B6 — build_buffer() / `make buffer`: a varied run + manifest
│   ├── providers/
│   │   ├── llm.py                 # Seam #1a: ONLY Anthropic importer (streamed, cached, retried)
│   │   ├── tts.py                 # Seam #1b: ONLY TTS importer (kokoro|elevenlabs|say) + concat
│   │   └── embeddings.py          # B3 — vector-search seam, STUBBED + unused (raises/no-ops)
│   ├── world/
│   │   ├── store.py               # B1 — the ONLY module that speaks SQL (schema + rows + queries)
│   │   ├── seed.py                # B1 — reproducible seed: CANON.md → DB (`make seed`)
│   │   ├── canon_source.py        # B1 — parse CANON.md into row shapes + the series bible
│   │   ├── clock.py               # B2 — real↔in-world (+600y); the single time source
│   │   ├── events.py              # B2 — status_of() + relative_phrase() + the progression demo
│   │   └── context.py             # B3 — assemble(): cached core + dynamic now (structured retrieval)
│   ├── writers/
│   │   └── conversation.py        # B4 — two-DJ orchestrator (showrunner→orchestrate→continuity→render)
│   └── formats/
│       ├── __init__.py            # B5 — FORMATS registry + make_format_segment() dispatcher
│       ├── __main__.py            # `python -m src.formats <name>` CLI
│       ├── common.py              # B5 — shared single-voice render / speaker helpers
│       ├── news.py                # B5 — news desk (single DJ)
│       ├── talk.py                # B5 — two-DJ show; wraps B4 via compose_segment()
│       └── music.py               # B5 — music wrap with [SONG] slot marker (single DJ)
├── tests/                         # surgical pytest: clock, events, context, conversation,
│   │                             #   canon_source, formats, retry  (29 tests)
│   └── test_*.py
├── segments/.gitkeep              # generated mp3s + JSON sidecars + buffer manifest (gitignored)
├── assets/.gitkeep               # jingles/beds + brand kit (gitignored)
└── web/                           # the Next.js public site (Vercel root = web) — SEE BELOW
    ├── src/app/                   # page.tsx (coming-soon), SignupForm.tsx, api/subscribe/route.ts
    ├── public/                    # wordmark, beacon mark, og-image
    ├── package.json / tsconfig.json / next.config.ts / eslint.config.mjs / postcss.config.mjs
    ├── CLAUDE.md / AGENTS.md / README.md
    └── .gitignore
```

**Gitignored** (present locally, not tracked): `.env`; everything under `segments/*` and `assets/*`
except the `.gitkeep` (the real `make buffer` artifacts — five mp3s, their JSON sidecars, and a run
manifest from the 2026-06-20 run — live here untracked); `__pycache__/`, `.venv/`, `.pytest_cache/`,
`.ruff_cache/`; the `.run/` playout pids/logs; `web/node_modules`, `web/.next`. The brand kit under
`assets/brand/` is gitignored like all assets.

**The `/web` app did not change in Phase B.** It is still the Phase A2 coming-soon page (one
night-field screen: wordmark, tagline, email signup → `/api/subscribe`, AI disclosure, follow
links). It grows into the player + studio in **Phase C**, pointing at the live stream. Phase B was
entirely the Python "mind"; the two halves remain independent.

## 2. The actual signatures Phase C builds on

### `src/config.py` — the one typed settings module
`from src.config import settings`; every tunable reads `settings.X`. Constructed once at import.
Loads (precedence) process env → repo `.env` → defaults. Area-prefixed fields; `settings.model_id(tier)`
maps a logical tier to a real model id. The knobs Phase C will touch most:

| Area | Fields (defaults) |
|---|---|
| Secrets | `anthropic_api_key`, `elevenlabs_api_key` (vendor names, no prefix) |
| Models | `model_haiku=claude-haiku-4-5-20251001`, `model_sonnet=claude-sonnet-4-6`, `model_opus=claude-opus-4-8` |
| LLM | `llm_default_tier=sonnet`, `llm_max_tokens=4000`, `llm_timeout_sec=120.0` |
| TTS | `tts_provider=kokoro`, `tts_elevenlabs_model`, `tts_kokoro_repo_id=hexgrad/Kokoro-82M`, `tts_kokoro_sample_rate=24000`, `tts_kokoro_speed=1.0`, `tts_mp3_bitrate=128k` |
| World | `world_years_ahead=600` |
| Segment | `segment_default_length_target_sec=300`, `segment_vell_voice=vell_night` |
| Writer | `writer_words_low=1000`, `writer_words_high=1050`, `writer_max_tokens=2000`, `writer_speaker_id=vell` |
| Context (B3) | `context_event_window_days=14` |
| Conversation (B4) | `convo_speaker_ids=[vell, wren]`, `convo_words_low=450`, `convo_words_high=600`, `convo_max_tokens=1600`, `convo_showrunner_max_tokens=300`, `convo_continuity_tier=sonnet`, `convo_continuity_escalation_tier=opus`, `convo_continuity_max_tokens=500` |
| Formats (B5) | `format_news_speaker_id=vell`, `format_news_headline_count=3`, `format_news_words_low/high=320/420`, `format_news_max_tokens=900`, `format_news_length_target_sec=150`; `format_music_*` (words 130/200, `length_target_sec=90`, `format_music_song_marker=[SONG]`) |
| Buffer (B6) | `buffer_target_sec=3600`, `buffer_rotation=[talk, news, music]`, `buffer_max_segments=30` |
| Retry | `retry_attempts=3`, `retry_backoff_sec=2.0` |
| Logging | `log_level=info`, `log_json=True` |
| **DB** | `database_url=postgresql://localhost/settlement_radio` (vendor name `DATABASE_URL`) |
| Paths | `segments_dir`, `canon_path` (both resolved from repo root) |

**How the DB connection is configured:** purely `settings.database_url` (env `DATABASE_URL`, default
`postgresql://localhost/settlement_radio`). `store.connect()` passes it straight to `psycopg.connect`;
the URL is password-redacted before it touches the logs. There is no separate host/port/user config —
one URL string, swappable per environment.

### World clock — `src/world/clock.py`
The single source of the real↔in-world mapping. All pure functions, year-shift only (keeps the wall
clock; handles the 29-Feb leap trap):
```python
to_inworld(now: datetime) -> datetime        # +600y face (arithmetic; used by events)
to_real(inworld: datetime) -> datetime       # inverse
inworld_year(real_year: int) -> int          # real_year + settings.world_years_ahead
render_wall_clock(now: datetime) -> str       # "Tuesday, 16 June 2626, 02:14" (display; real weekday)
```

### Relative-time renderer — `src/world/events.py`
Pure; operates on a fetched `store.Event` vs real `now` (compares against `clock.to_inworld(now)`):
```python
UPCOMING = "upcoming"; TODAY = "today"; PAST = "past"
status_of(event, now) -> str                  # upcoming | today | past
progressed(event, now) -> Event               # copy with status recomputed live
relative_phrase(event, now) -> str            # "tomorrow" / "in five days" / "tonight" /
                                              #   "yesterday" / "last week" / "two weeks ago" …
```
Thresholds (`_WEEK=7`, `_FORTNIGHT=14`, `_MONTH=28`) + a small number-word table are named module
constants (intrinsic to the renderer — deliberately NOT in config). `python -m src.world.events`
(= `make demo`) renders one event at two `now` values and prints the phrase flip.

### Event store / query interface — `src/world/store.py` (the ONLY SQL)
Row dataclasses (frozen): `CanonFact(id, text, tags)`, `CastMember(id, name, card_text,
logical_voice, tags)`, `Event(id, title, body, in_world_datetime, status, tags)`. Tables:
`canon`, `"cast"` (quoted — SQL keyword), `events`, `state`.
```python
@contextmanager
connect() -> Iterator[psycopg.Connection]     # one transaction: commit on clean exit, rollback+log on error
init_schema(conn); clear_world(conn)          # idempotent create; TRUNCATE for clean re-seed
# writes:
insert_canon(conn, facts) -> int; insert_cast(conn, members) -> int; insert_events(conn, events) -> int
set_state(conn, key, value)
# reads:
all_canon(conn); canon_by_tags(conn, tags)            # tag overlap (&&); empty until canon is tagged
all_cast(conn); get_cast_member(conn, id) -> CastMember | None
get_event(conn, id) -> Event | None
events_by_status(conn, status); events_in_range(conn, start, end)   # the date-window query
get_state(conn, key); counts(conn) -> dict[str,int]
```
**FUTURE vector seam is documented here** (a `CREATE EXTENSION vector` + `canon_embeddings` table +
`search_canon()`), intentionally not built.

### Context assembly — `src/world/context.py`
```python
assemble(now, *, topic=None, speakers=None) -> AssembledContext
#   speakers: one cast id ("vell") or several (["vell","wren"]); unknown id RAISES.
#   returns AssembledContext(cached_context, dynamic, speakers, events, canon)
#     .cached_context → series bible + each speaker's card  (pass to llm.generate cached_context)
#     .dynamic        → events near now (live status + relative phrase) + topic/all canon (per-call)
#     .speaker (property) → first speaker, for single-DJ callers
```
The only DB block in the module; events pulled within `±context_event_window_days` of in-world now,
each `progressed()` to a live status. Canon is tag-matched to `topic`, falling back to all canon
(the case today — seeded facts carry no tags yet).

### Conversation orchestrator — `src/writers/conversation.py`
Entry point for a two-DJ talk segment:
```python
make_conversation_segment(now_iso, *, topic=None, length_target_sec=None) -> Segment
#   assembles context for settings.convo_speaker_ids, then:
compose_segment(ctx, now, *, seg_id=None, length_target_sec=None, extra_directive=None, fmt="talk") -> Segment
#   the shared core: showrunner(ctx, now) → orchestrate(ctx, beat, now, extra_directive=…)
#     → safety_check → parse_turns → continuity_check (sonnet, escalate to opus) → _render_turns
#   meta carries: speakers, turns, beat, continuity_ok/tier/note
```
`extra_directive` is how B5's `talk` injects its open→banter→music-lead-in→close backbone without
re-implementing the room. Steps: `showrunner()`, `orchestrate()`, `continuity_check()` (with
`ContinuityResult`), `parse_turns()` (speaker-labelled → `Turn`s), `_render_turns()` (voice each turn,
stitch with `tts.concat_audio`).

### Program formats — `src/formats/`
Each builder is `(now: datetime, ctx: AssembledContext) -> Segment`. Dispatcher:
```python
make_format_segment(name, now_iso, *, topic=None) -> Segment    # name ∈ {"news","talk","music"}
#   assembles context with the format's cast (FORMATS[name].speaker_ids()), then runs the builder
news(now, ctx)  → single DJ, sting → N headlines → sign-off
talk(now, ctx)  → wraps conversation.compose_segment with the talk backbone
music(now, ctx) → single DJ, intro → [SONG] marker (split out, never spoken) → back-announce
```
CLI: `python -m src.formats <name> [topic]` (= `make format FMT=news`).

### The buffer command — `src/buffer.py` / `make buffer`
```python
build_buffer(now=None, *, target_sec=None, rotation=None) -> list[Segment]
```
Cycles `settings.buffer_rotation`, calling `make_format_segment` per slot, advancing an `air_cursor`
by each segment's `length_target_sec`, until the summed targets reach `target_sec` (or
`buffer_max_segments`). Writes a JSON **sidecar** per segment (`segments/<id>.json`) and a run
**manifest** (`segments/buffer-<ts>.json`) — the on-disk shape a Phase C scheduler reads.
CLI: `python -m src.buffer [target_sec]`; `make buffer SECONDS=600` for a quick run.

## 3. Where the implementation diverged from the plan

(All now reflected back in `docs/ARCHITECTURE.md`.)

1. **`talk` is single-call, NOT multi-agent — as the B4 guidance preferred.** Both personas are
   scripted in one `orchestrate()` call (cheaper, more coherent); turn-by-turn agents were never
   needed. The "writers' room" is three sequential Claude calls (showrunner → orchestrator →
   continuity), not parallel agents per DJ.
2. **`context.assemble` takes `speakers=` (str | list), not `speaker=`.** The B3 pack wrote
   `assemble(now, *, topic, speaker)`; it shipped as `speakers` so the same call serves the single-DJ
   writer and the two-DJ room. A `.speaker` convenience property preserves the single-DJ ergonomics.
   `writer.py`'s docstring still says `speaker=…` in prose — harmless, but the kwarg is `speakers`.
3. **`compose_segment` was extracted from `make_conversation_segment` (a B5-era refactor).** B4
   shipped one entry point; B5 split out `compose_segment(ctx, now, …)` so the `talk` format can pass
   a pre-assembled context + an `extra_directive`. B4's behaviour is unchanged.
4. **A third+ TTS reality: Kokoro is the default, `say` and `elevenlabs` remain behind the seam.**
   `tts_provider=kokoro` by default (local, free, unlimited); `elevenlabs` is kept for future flagship
   use, `say` as the offline fallback. Two logical voices now exist — `vell_night`→`bm_george`
   (British male) and `dj_two`→`af_heart` (American female, Wren). `orpheus` is still a
   `NotImplementedError` stub. `concat_audio()` (ffmpeg stream-copy) was added to stitch per-turn clips.
5. **The vector seam is stubbed AND unused, exactly as planned.** `providers/embeddings.py` `embed()`
   raises and `retrieve()` no-ops/returns `[]`; `context.py` never calls it. pgvector is not installed.
   Retrieval is 100% structured (date/status/tag SQL). This is the intended B3 outcome, noted here so
   Phase C doesn't mistake the stub for missing work.
6. **`canon_by_tags` is wired but inert.** The parser leaves canon facts un-tagged, so tag-matched
   retrieval always falls back to `all_canon`. The seam works; the data isn't tagged yet.
7. **`Segment.length_target_sec` on the new formats is metadata, not a rendered-length contract.**
   `compose_segment`/the format builders set it from config but the *actual* spoken length is governed
   by the word-count guidance — and they diverge significantly (see retro §5). The B0 "within ~10%"
   tune was done for the single-DJ writer only.
8. **Continuity is advisory.** `continuity_check` runs (and escalates sonnet→opus correctly), but a
   `continuity_ok=False` segment is still rendered and written to the buffer. It exercises the seam a
   real gate will occupy; it does not yet gate anything.
9. **Layers vs. the architecture doc:** Layers 1–3 (world/time, knowledge store, writers' room) are
   now **real**; Layer 2's *vector* half is stubbed. Layer 4 still has no jingle/bed mixing (playout
   fallback fills it). Layer 5 (scheduler) and Layer 6 (public distribution) remain Phase A's
   loop-the-newest-file — `make buffer` is a generator, **not** a scheduler.

## 4. The engineering baseline (B0.5) as it actually stands

**Green across the board, verified at the close of Phase B:**
- `ruff check src tests` → *All checks passed!*  •  `ruff format --check` → *34 files already formatted*.
- `pytest` → **29 passed** (test_clock, test_events, test_context, test_conversation,
  test_canon_source, test_formats, test_retry).
- `pre-commit` is **installed** (`.git/hooks/pre-commit` present; pre-commit 4.6.0) with hooks: ruff
  (lint `--fix` + format), **gitleaks** (the secrets-scanner backstop, diff-scanning, no baseline),
  the **`no-direct-env`** local guard (`scripts/check_no_direct_env.sh` — blocks `os.getenv`/`os.environ`
  outside `config.py`), and the basics (trailing-whitespace, EOF-fixer, large-file, check-json/yaml/toml).

**Config-over-hardcoding: fully in place.** Every tunable is a `settings.X` field; the `no-direct-env`
pre-commit hook mechanically enforces that nothing outside `config.py` reads the environment directly.
Genuinely intrinsic constants (the relative-time thresholds, the vendor voice registries, the news
backbone text) live as named, commented module constants — by the documented rule in `config.py`, not
as drift.

**Structured logging:** `structlog`, configured once in `logging_setup.py` (JSON by default;
`LOG_JSON=false` for console-pretty dev), level from `settings.log_level`. Every external call and
every pipeline step logs a `*_start`/`*_done` event pair with structured fields (e.g.
`llm_generate_start tier=… model=… cached=…`, `tts_synthesize_done provider=… out_path=…`,
`buffer_slot index=… format=…`). No `print()` in the backend except the deliberate CLI stdout of the
`__main__` demos.

**Error handling + retries:** `retry.call_with_retry(op, func)` wraps both seams (`llm.generate`'s
stream and every `tts.synthesize` backend), `retry_attempts=3` with linear backoff; an exhausted call
logs `external_call_failed` at error and re-raises — it fails loudly, never silently empty. `store.connect`
rolls back and logs on any exception.

**Tests are surgical, as intended:** they cover the bits with real logic where a silent bug bites —
the clock/leap-year math, the relative-phrase thresholds, context assembly, turn parsing, the canon
parser, format dispatch, and the retry policy. Glue (the live LLM/TTS/DB calls) is not mocked-to-death.

## 5. Retro — what was fiddly, how it turned out, what surprised us

*Grounded in a real `make buffer SECONDS=900` run from 2026-06-20 still on disk: 5 segments
(talk, news, music, talk, news).*

**The two-DJ conversation genuinely works — it's a conversation, not two narrators.** The second
talk segment (which passed continuity) opens:
> **Vell:** …It's just gone fourteen after the sixth hour, settlement time, and I've been sitting here all night with something I can't quite name. Not the festival itself. Just the four days before it.
> **Wren:** I felt it coming in. The relay corridor's so quiet this morning it practically echoes.
> **Vell:** …arguing whether the Calloway Reach tradition counts as the right way or just *a* way…
> **Wren:** My grandmother used to call it the held breath. The four days before Lumen where everything is almost.

It **uses canon without info-dumping**: the Lumen Festival is referenced as shared anticipation ("the
held breath," the simultaneity of every world kindling lights "weeks and weeks of signal apart"), never
explained between them. Vell and Wren sound distinct (his slow musing vs. her bright forward energy),
they build on each other's lines, and the settlement-time check lands naturally near the open. The
anti-recitation instruction in the orchestrator prompt did its job.

**The single-call design was the right call** — coherent, cheap, in-character. Multi-agent turn-by-turn
was never needed. Continuity escalation works as designed: the first talk segment flagged on `sonnet`
and re-ran on `opus`.

**The biggest surprise / the thing Phase C must worry about — the `talk` format assumes a fixed
night→first-light handover regardless of air time.** In the buffer run the advancing `air_cursor`
pushed a `talk` slot into the *afternoon*, and the orchestrator prompt still framed it as the
night→dawn handover. The continuity editor caught it precisely (`continuity_ok=False`):
> ISSUES: scene is set at "two in the afternoon" but the handover is Vell's night→Wren's first-light
> shift; references to "all night," "this morning," "afternoon" all collide… Vell out of character:
> keeps the night shift past handover into afternoon…

…and yet **the flawed segment was still rendered and written into the buffer** (continuity is advisory).
So the time-awareness spine is real, but the *conversation framing* is not yet time-aware — the room
needs to pick the right pairing/handover for the actual hour, and a real gate needs to reject or
regenerate a flagged draft. (The "in five days → yesterday" *renderer* itself works cleanly — the
`make demo` flip is solid and unit-tested; the bug is in the show framing, not the clock.)

**Rendered length is well under target on the new formats — the B0 tune didn't carry over.** Measured
audio vs. `length_target_sec`:

| format | words | length_target | **actual audio** |
|---|---|---|---|
| talk | ~505–530 | 300s | **~165s** (~45% short) |
| news | ~363–365 | 150s | **~132s** (~12% short) |
| music | ~178 | 90s | **~62s** (~31% short) |

B0 tuned the *single-DJ writer* (~1000 words → ~5 min) to within 10%; the B4/B5 word counts were set
deliberately short for fast iteration and never re-tuned to their length targets. Consequently the
buffer's accounting (which sums `length_target_sec`) **over-counts**: the run "reached" 990s of target
but the real audio totals ~657s (~11 min, not ~16). A Phase C scheduler that trusts `length_target_sec`
will mis-plan; either tune word counts up or measure real duration post-render.

**Kokoro's voice quality:** the segments render cleanly and fully local at zero cost — both voices are
intelligible and distinct (`bm_george` warm British for Vell, `af_heart` brighter American for Wren),
which is what makes a two-voice talk segment read as two people. They are *serviceable open-weight neural
voices*, a clear step up from `say` but not flagship — emotional range is flat (the `emotion` param is
accepted and ignored), and there's no fine prosody control. Final voice identity is still an open Phase C
question (Kokoro at volume vs. a paid flagship for the public launch).

**Cost / throughput reality (the inversion holds and deepens):** with Kokoro as default, the **text is
the only API cost and it's near-trivial** — short showrunner/continuity calls plus one dialogue call per
talk segment, all on `sonnet`, with the stable core cached. **Voice is now free but slow:** Kokoro
loads the 82M model per process (cached per language) and renders on CPU, so a full ~hour buffer is the
real time sink, not the dollar sink. The Phase A finding ("TTS is the cost ceiling") is *resolved* for
iteration by going local — which, as B6 notes, **weakens the case for the Batch API** (50%-off Claude on
an already-trivial text bill); revisit Batch in Phase C only if text volume grows.

**Fiddly bits:** Kokoro needs Python 3.10–3.12 (not 3.13) + the `espeak-ng` system package + a
first-run model download — all now in the README (the Phase A liquidsoap lesson applied). Postgres
install + `make seed` is a prerequisite for nearly every Phase B command, which is easy to forget;
the code fails loud ("run `make seed`?") rather than silently. The `"cast"` table name needs quoting
everywhere (SQL keyword).

## 6. Open risks for going public / 24-7

These are the things that are currently fragile, hardcoded-by-necessity, or simply unhandled, that
matter the moment this runs unattended and in public:

1. **The content-safety gate is still a no-op placeholder.** `writer.safety_check()` returns text
   unchanged and is the same seam everywhere (writer, news, music, conversation). CLAUDE.md requires a
   real safety gate before any *public* broadcast — this is a hard Phase C prerequisite, not polish.
2. **Continuity is advisory, so bad segments still air.** A `continuity_ok=False` draft (e.g. the
   afternoon-handover collision above) is rendered and written anyway. Going 24/7 needs the gate to
   *reject and regenerate* on failure, with a bounded attempt count and a safe fallback segment.
3. **The `talk` framing is not time-aware.** The room hard-frames a night→first-light handover
   regardless of the actual hour. Unattended generation across a full day will produce
   internally-contradictory segments unless the showrunner picks the pairing/handover from the clock.
4. **No scheduler, and `length_target_sec` lies.** `make buffer` is a one-shot generator; there is no
   buffer-depth dial, no "what airs when," no regeneration on failure. And because rendered audio runs
   well short of the metadata target, any scheduler that trusts `length_target_sec` will mis-time the
   playlist. Both are core Phase C work.
5. **AI disclosure is a field, not a behaviour.** `Segment.disclosure=True` is set but nothing speaks
   or displays it yet. Public launch needs the spoken + on-player disclosure wired (the Phase A web
   page has placeholder text; the audio path has none).
6. **Single points of failure with no live fallback.** A Postgres outage or a Kokoro model-load
   failure aborts generation (it logs loudly and raises — good for diagnosis, bad for a live stream).
   24/7 needs an evergreen fallback segment/loop so the air is never dead, plus health checks. Retries
   exist on the seams but not at the orchestration level.
7. **Voice identity & licensing for public use.** Kokoro is fine for local iteration; the public
   station's final voices (Kokoro at scale vs. a paid flagship, and the licence/disclosure implications)
   are unresolved. The `emotion` knob is still inert.
8. **Operational secrets on a server.** Today secrets live only in `.env` (gitignored, gitleaks-guarded).
   The VPS deploy must keep them non-world-readable and out of logs (the DB-URL redaction pattern is the
   model to follow for any new secret).

---

*Bottom line:* the **mind is real** — a seeded, queryable, time-aware world feeding a writers' room
that produces a genuine two-DJ conversation, all free and local. The seams held (no vendor SDK leaked
past `llm`/`tts`/`store`; the cache lever and the Segment dial survived). The gaps that remain are
exactly the ones Phase B deferred on purpose: a real safety/continuity *gate*, a *scheduler* with honest
length accounting, time-aware show framing, disclosure-in-the-air, and never-dead fallback — i.e. the
work of making it safe and continuous enough to be public.

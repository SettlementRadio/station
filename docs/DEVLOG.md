# DEVLOG — Settlement Radio

The written record of decisions and changes, one entry per working session. The screen
recordings show *how*; this log captures *what changed and why* — the part video can't make
searchable, and the source material for the case study and "built in public" posts later.

## How to use this

- **One entry per session**, newest on top. Keep it fast (5 minutes) or it won't survive.
- Tie each entry to its evidence: the commit(s) for that session and the clip filename(s) in
  `devlog/`. The trio — entry + commit + clip — is one session's complete record.
- Once code exists, "Changed" overlaps with git commits; that's fine. The log's real value is
  **Decisions** and **Why**, which commits don't capture.
- When you write the case study, read this bottom-up (oldest first) — it's the story arc.

**Entry template (copy this):**

```
## YYYY-MM-DD — [Phase] — <one-line focus>
**Focus:** what this session was about, in a sentence.
**Decisions:** the durable choices (the things that matter in three months).
**Changed:** files/commits/accounts that concretely changed.
**Why:** the one or two reasons behind the key decision (your future self will thank you).
**Next:** the single next action.
Commit: <hash>  ·  Clips: <filenames in devlog/>
```

A typical *build* session will be short, e.g.:
> `## 2026-07-02 — Phase A — T3 script generation working`
> Focus: got Claude writing Vell's segment from canon. Decisions: cache the whole canon as one
> breakpoint. Changed: src/writer.py, README. Why: keeps input cost ~0.1x. Next: T4 (render to
> audio). Commit: a1b2c3 · Clips: 2026-07-02-first-script.mov

---

## 2026-06-22 — Phase C — C1: time-aware show framing (the afternoon-handover fix)

**Focus:** stop the room hardcoding a night→first-light handover at every hour — the bug that made
an afternoon talk slot say "all night / this morning / handover" and get (correctly) rejected by the
new C0 continuity gate. Land it right behind C0 so the gate isn't thrashing on a framing bug.
**Decisions:**
- New `src/world/framing.py` — a pure clock→`ShowFrame` mapper (the single home for "who's on air
  this hour and what's the situation"): deep/late night = Vell solo · first light = Vell→Wren
  handover · morning/afternoon/evening = Wren anchors · nightfall = Wren→Vell handover. Stateless
  and DB-free (host ids passed in), so it's unit-tested like `clock.py`/`events.py`.
- `showrunner()` and `orchestrate()` now take the frame (computed once in `compose_segment`) and drop
  its `part_of_day` + prose `situation` into the prompt in place of the constant. The time-check
  instruction is handover-placed only when the frame is actually a handover.
- Frame fields (`part_of_day`, `lead`, `handover`) ride in the Segment meta for the scheduler/debug.
- Window boundaries + daypart cutoffs are named module constants (intrinsic daily schedule, not
  config) — no new settings. Daylight hours can NEVER be framed as a handover (a unit test pins this).
- Scope: the two-DJ room only (the sole continuity-gated path, and the documented bug). Reassigning
  which solo DJ reads news/music by the clock, and wiring the buffer to avoid odd talk slots, is the
  scheduler's job (C2) — not folded in here. The Phase A single-DJ `writer.py` still hardcodes a
  night frame; it's off the gated 24/7 path, noted as a later cleanup.
**Changed:** new `src/world/framing.py`; `src/writers/conversation.py` (showrunner/orchestrate/
compose wired to the frame, meta enriched); tests `test_framing.py` (+ updated `test_compose_gate.py`
stubs for the new `frame=` kwarg). 46 tests pass.
**Why:** an unattended 24/7 station generates talk across the whole day; without hour-true framing it
manufactures self-contradictions the C0 gate then burns attempts regenerating before falling back to
evergreen. C1 removes the bug so the gate guards real problems, not a constant.
**Next:** C2 — honest length accounting (ffprobe) + a real rolling scheduler wired to playout.
Commit: <pending>  ·  Clips: —

## 2026-06-22 — Phase C — C0: the safety + continuity gates are real

**Focus:** turn the two no-op placeholders (the `safety_check` stub and advisory continuity) into
*blocking* gates, so nothing unsafe or self-contradictory can reach air.
**Decisions:**
- `safety_check` now returns a verdict (`SafetyResult`), not mutated text — it's a *gate*, not a
  rewriter. Two stages, cheap-first: a fast keyword/profanity pre-filter (no API), then an LLM pass
  on the `haiku` tier tuned to ALLOW in-world sci-fi conflict and flag only genuinely unsafe
  content. The "what to do when flagged" policy lives with the producers, not the gate.
- New `src/safety.py` (the gate, used by every producer) and `src/evergreen.py` (the safe fallback).
  Moved `safety_check` out of `writer.py` into `safety.py`; updated all four producers' imports.
- Policy: regenerate on a flag (bounded), then drop to an evergreen segment — a flagged/contradictory
  draft is NEVER rendered or written to `segments/`/the manifest. Single-DJ producers use
  `safety.generate_safe`; the two-DJ room runs a combined safety+continuity loop in `compose_segment`,
  feeding the continuity editor's note back into the rewrite.
- Named the continuity dial `convo_continuity_max_attempts` (matches the existing `convo_continuity_*`
  family + the config prefix convention), not the spec's illustrative `continuity_max_attempts`.
- Evergreen is render-on-demand from a small static pool for now; C4 promotes it to a pre-rendered
  pool + the full fallback chain + health checks.
**Changed:** new `src/safety.py`, `src/evergreen.py`; `src/config.py` (safety_* + continuity dial);
`src/writer.py`, `src/formats/news.py`, `src/formats/music.py`, `src/writers/conversation.py` (gates
wired); `.env.example`; tests `test_safety.py`, `test_evergreen.py`, `test_compose_gate.py` (40 pass).
**Why:** CLAUDE.md requires a real safety gate before any public broadcast, and a 24/7 stream can't
air the afternoon-handover contradiction the orientation caught. Gates + a never-dead fallback are the
hard prerequisite to exposing the stream (C7/C8).
**Next:** C1 — time-aware show framing — to land right behind C0, so the new gate isn't thrashing on
the hardcoded night→dawn handover bug (it would currently regenerate, then fall back to evergreen).
Commit: <pending>  ·  Clips: —

## 2026-06-21 — Pre-Phase-C — full audit + roadmap/architecture realignment + switchable TTS

**Focus:** a full audit of everything built (Phases A/B) and everything planned (C→F), then
realigning the docs to the *truth* and to an expanded product vision — plus a small code fix so both
TTS backends are fully switchable. No build-phase work; this is the session that makes Phase C
safe to start from.

**Decisions (the durable ones):**
- **Roadmap integrity fix.** A prior draft of `ROADMAP.md` had marked **Phase C as "✓ DONE"** and
  put "we are here" at the soft launch — false (HEAD is B6; C is unbuilt). Corrected: Phase C is the
  *current* build phase. A roadmap that lies about being public-ready is the one error that could let
  a future session skip the safety/deploy phase entirely.
- **Two standing Phase-C constraints, from the human.** (1) **The VPS does ALL generation and
  playout — no personal hardware in the runtime loop** (killed the "generate on the Mac and rsync"
  option in C6). (2) **Voice is a runtime setting** — both Kokoro (free) and ElevenLabs (flagship)
  must work via `settings.tts_provider`, not a one-way door.
- **The world is two layers (the refined vision).** A large, mostly-static **bible** (RAG-able:
  history, literature, finance, war, nations, peoples, geography, tech, cast) + a generative
  **living "now" at +600y**: events modelled as multi-beat **stories with a lifecycle** (rumoured →
  upcoming → happening → developing → past), surfaced by a **news desk** that recurs/evolves stories
  across the day with past/now/future framing and cross-segment continuity. This is the Phase-D
  keystone.
- **Vision distributed across phases, not crammed into C.** World-sim + news desk + sound design +
  songs + voice/emotion/pronunciation + DJ roster/memory + programming backbone → **D**. Near-live +
  a write **management/control surface** + **listener interaction** → **E**. Community inbound +
  in-universe surfaces → **F**.
- **Architecture gains exactly ONE new concept — Layer 0 (listener inbound).** Everything else fits
  existing layers/seams (proven "no rewrite below the seams"). The Batch API was downgraded from a
  MUST to "revisit when it pays" (Kokoro made the text bill trivial); the `orpheus` stub generalized
  to a streaming/self-hosted backend (Cartesia for near-live); a **pronunciation** knob reserved
  alongside `emotion` on the TTS seam.

**Changed:**
- `docs/ROADMAP.md` — Phase C moved out of DONE into a real build section (constraints baked in);
  Phase D expanded into the living-world spec; Phase E → "Scale, near-live & control"; milestone ✓
  corrected.
- `docs/ARCHITECTURE.md` — new Layer 0 (inbound); per-layer C/D/E forward notes; console → control
  surface; softened Batch rule; generalized TTS stub; reserved pronunciation; "How later phases plug
  in" rewritten into C/D/E blocks.
- `docs/PHASE_C_TASKS.md` — C6 reframed to *verify* (registry now done); **added the missing
  scheduler → Liquidsoap playout task**; decisive music-slot default (drop from rotation in C); soak
  "give it a now" note; C0 safety-check shape + C3 disclosure-as-setting; removed Discord
  (four-channel rule); C0/C1 ordering note.
- `docs/ai-radio-marketing-strategy.md` — superseded banner (four channels), Cloudflare Pages →
  Vercel.
- `src/providers/tts.py` — added Wren to the ElevenLabs ("Rachel") and `say` ("Samantha") registries;
  all three backends now map both DJs, so the **two-DJ show renders on any backend**.
- `src/writer.py` — docstring fix (`speaker=` → `speakers=`). Deleted `README_Backup.md` (cruft).
- Verified green: `ruff check` clean, `pytest` 29 passed.

**Why:** truth-in-docs is load-bearing for an agent-built project — the next session acts on what the
docs say, so a false "done" or an out-of-date plan is a real production risk, not cosmetics. Encoding
the full vision + constraints *before* building C means every later pack is informed and the
architecture can prove none of it forces a rewrite below the two seams.

**Next:** begin Phase C — **C0** (real safety + continuity gates), landing **C1** (time-aware
framing) alongside it.
Commit: (uncommitted at time of entry — docs realignment + TTS registry in the working tree)  ·  Clips: none

---

## 2026-06-20 — Phase B — B6 light nightly buffer (`make buffer`) — the mind at volume

**Focus:** one command that generates a small, varied block of audio in a single run — the mind
proven at volume at zero API cost — *without* building the real 24/7 scheduler (that, the
buffer-depth dial, the Batch API, and the content-safety gate are all deferred to Phase C). This
completes Phase B's "bonus" line: the whole mind runs at volume for free via Kokoro.

**Decisions (the durable ones):**
- **New `src/buffer.py` — a loop over the B5 dispatcher, not a new generation path.** `build_buffer`
  cycles `settings.buffer_rotation` (a mix of the three formats) calling `make_format_segment` per
  slot until the segments' `length_target_sec` values sum to ~`buffer_target_sec`. It reuses the
  whole stack underneath unchanged (formats → conversation/writer → context → world → providers);
  B6 adds *no* new world-query, LLM, or TTS code.
- **Length is measured by the segments' own targets, not a duplicated length table.** Rather than
  pre-planning durations (which would re-encode each format's length in a second place), the loop
  generates one segment, adds its *actual* `length_target_sec` to the running total, and stops when
  it reaches the goal — so the only source of a format's length stays its own config. It lands a
  little OVER target (a half-segment would be worse than slightly long).
- **Variety + progression come for free from the rotation + an advancing `air_time`.** Each slot is
  generated against an `air_cursor` that advances by the prior segment's length, so the block is
  contiguous *and* each segment assembles its own world context at its slot time — current events
  progress across the hour, exactly the Phase-B spine paying off. Both DJs appear because `talk` is
  the two-DJ show.
- **Each segment self-describes on disk; the run gets a manifest — the Phase-C handoff shape.**
  Every segment writes a `segments/<id>.json` sidecar (the full `Segment` via `dataclasses.asdict`),
  and the run writes `segments/buffer-<ts>.json` (ordered playlist: ids, formats, contiguous
  air_times, lengths, paths). Nothing reads the manifest to *air* it yet — that's the Phase-C
  scheduler — but the on-disk contract it will consume exists now.
- **A `buffer_max_segments` safety cap.** A hard stop so a tiny per-segment length (or a silly
  target) can't spin an unbounded run. All three knobs (`buffer_target_sec`, `buffer_rotation`,
  `buffer_max_segments`) live in a new `buffer_` config section; `make buffer SECONDS=` is the
  per-run length shortcut.

**Changed:**
- New: `src/buffer.py` (loop + sidecar + manifest + CLI).
- Updated: `src/config.py` (a `buffer_` section), `Makefile` (`make buffer`, `SECONDS=` override,
  help/header), `README.md`, `.env.example` (the B6 knobs), `docs/HOWTO.md` (buffer row + §2/§3/§6).

**Why:** Phase B's bonus done-when is "the whole mind runs at volume for free." Looping the B5
dispatcher (instead of writing a scheduler) gets that proof in the smallest code, and accumulating
by the segments' real length targets keeps length single-sourced. The sidecar+manifest is the cheap
groundwork that makes the Phase-C scheduler a *reader* of this output, not a rewrite.

**Verification:** the loop/sidecar/manifest/cap logic was exercised with a stubbed
`make_format_segment` (no DB/Claude/TTS): rotation cycles correctly, air_times are contiguous
(22:00:00 → +5m → +2.5m …), the target-driven loop stops just over goal (600s target → 4 segments,
840s), the `max_segments` cap holds (target 999999 → exactly 30), and a `<id>.json` per segment plus
one `buffer-*.json` manifest are written with all Segment fields. `ruff check src` + format clean;
new `segments/*.json` are gitignored. **Not yet run end-to-end** on the real stack (needs seeded
Postgres + the Kokoro model; the full hour is ~20 live segments) — that real run is the one
remaining human check.

**Next:** Phase B is feature-complete (B0–B6). Run a real `make buffer` for the hero clip, then
Phase C — the VPS, the real scheduler that airs *through* this buffer/manifest, public broadcast,
the content-safety gate, and the player/studio in `/web`.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-20 — Phase B — B5 program format templates (news / talk / music)

**Focus:** reusable show backbones so generation fills a proven skeleton instead of a blank page —
three formats, each a function `(now, context) -> Segment`, behind one registry/dispatcher.

**Decisions (the durable ones):**
- **New `src/formats/` package, one template per file + a registry.** `news`, `talk`, `music` each
  implement `(now, ctx) -> Segment`; `FORMATS` (a `{name: FormatSpec}` map) plus
  `make_format_segment(name, now_iso, topic=)` is the single public entry. The dispatcher assembles
  exactly the cast each format needs (one card for news/music, both for talk) via the same
  `context.assemble` seam, then calls the template — templates never touch the DB.
- **`talk` *wraps* B4, doesn't re-implement it.** Extracted `conversation.compose_segment(ctx, now,
  …)` (the context-taking generation core) out of `make_conversation_segment`, and added an optional
  `extra_directive` to `orchestrate`. `talk` calls `compose_segment` with an open→banter→music
  lead-in→close backbone. B4's own behaviour is unchanged.
- **`news` is reportage — the anti-recitation rule is deliberately inverted.** Unlike the two-DJ
  talk, a news anchor *should* state facts plainly; the prompt says so. Headlines are derived from
  the events near `now` (live relative phrasing from `events.py`); fewer than N → the anchor extends
  with plausible, canon-consistent items.
- **`music` keeps a `[SONG]` slot marker.** One Claude call writes intro + back-announce separated by
  a marker line; the marker stays in the saved `script` and in `Segment.meta`, but is split out
  before rendering so it is **never spoken** (real song scheduling is Phase C playout). Split logic
  (`split_on_marker`) is pure and unit-tested.
- **Config gets a `format_` section** (per-format speaker ids, word-count guidance, length-target
  DIALs, the song marker) — same config-over-hardcoding discipline; word counts/lengths are what make
  the three read as tonally distinct (a tight ~2.5-min news desk vs. a short ~1.5-min music bed).
- **Builders imported under aliases** (`from .news import news as build_news`) so the submodule names
  (`formats.news`, …) aren't shadowed by the function names.

**Changed:**
- New: `src/formats/{__init__,common,news,talk,music,__main__}.py`, `tests/test_formats.py`
  (marker split + registry).
- Updated: `src/writers/conversation.py` (extracted `compose_segment` + `orchestrate` directive),
  `src/config.py` (`format_` section), `Makefile` (`make format FMT=…`), `README.md`, `docs/HOWTO.md`.

**Why:** Phase B's "the Mind" needs more than one show shape; templating the backbone makes each kind
repeatable and tonally consistent while reusing the B4/B3 machinery (no new TTS or world-query code).
The signature `(now, context)` is the same shape B6's nightly buffer will loop over.

**Verification:** live `make format FMT=news` produced a coherent bulletin — sting → exactly 3
in-world headlines (lead derived from the seeded Lumen Festival, "with four days to go", plus two
canon-consistent invented items) → sign-off — rendered free via Kokoro to a **137.6s** segment
against a **150s** target (~8%). Distinctly a measured news desk, not the warm late-night talk.
`talk`/`music` share already-proven paths (B4 conversation; the news single-call + single-voice
render, plus the unit-tested marker split). **29 `pytest` pass**; `ruff` + format clean.

**Next:** B6 — a light nightly buffer (`make buffer`): ~an hour of varied segments (a mix of the
three formats, both DJs) into `segments/`, the mind proven at volume at zero API cost.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-20 — Phase B — B4 second DJ + conversation orchestrator (the creative core)

**Focus:** the hard creative core — two DJs (Vell, night → Wren, first light) holding a real,
in-character conversation that *uses* a current event/canon fact without info-dumping, voiced in two
distinct Kokoro voices and stitched into one talk `Segment`.

**Decisions (the durable ones):**
- **A light writers' room in three Claude steps, one shared cache.** New
  `src/writers/conversation.py`: a **showrunner** picks one beat/angle from the events near `now`;
  an **orchestrator** writes the whole exchange; a **continuity** editor checks it. All three pass
  the *same* `cached_context` (bible + both cards), so the prompt cache is reused across the
  session — only the small variable part of each call pays full price.
- **Single-call dialogue, both personas in one prompt** (per the B4 guidance) — cheaper and more
  coherent than turn-by-turn agents. The output is speaker-labelled (`Vell:` / `Wren:`); a parser
  (`parse_turns`) splits it into per-voice turns, tolerating `**bold**` labels, wrapped lines, and
  stray preamble. Try multi-agent only if single-call feels flat (it didn't).
- **Anti-recitation baked into the prompt:** the facts are the hosts' *shared knowledge to
  reference naturally*, never to explain to each other or recite. This is the line between "a
  conversation" and "two narrators," and it's the whole point of the task.
- **Continuity escalates by cost only when needed:** one pass on `sonnet`; if it flags trouble,
  re-check on `opus`. Advisory in B4 (verdict logged + stored in `Segment.meta`), exercising the
  seam a real continuity/safety gate slots into. The draft also runs through the existing
  `safety_check()` placeholder.
- **Two-voice rendering = synthesize per turn, then stitch.** Each turn is voiced in its DJ's own
  logical voice (`vell_night` / `dj_two`) and the per-turn mp3s are joined by a new
  `tts.concat_audio()` (ffmpeg concat demuxer, stream-copy — no re-encode). **All ffmpeg stays in
  `tts.py`**, next to `_to_mp3`, keeping the seam intact.
- **`context.assemble` generalized to N speakers.** `speakers=` now takes one id *or* several
  (both cards → cached core); a `speaker` convenience property keeps the single-DJ B3 path
  unchanged. This is what B5's formats will reuse.

**Changed:**
- New: `src/writers/{__init__,conversation.py}`, `tests/test_conversation.py` (the brittle
  `parse_turns` + verdict reader).
- Updated: `src/world/context.py` (multi-speaker `assemble` + `speakers`/`speaker` property),
  `src/providers/tts.py` (`concat_audio`), `src/config.py` (a `convo_` section: speaker ids, word
  guidance, per-step token caps, continuity tier + opus escalation tier), `src/writer.py`
  (`speakers=` kwarg), `Makefile` (`make conversation`), `README.md`.

**Why:** Phase B's definition of done is "two DJs hold a sensible in-character conversation that
uses canon." Single-call + a strong anti-recitation rule gets a genuine exchange for one Claude
call's cost; voicing turns separately is the only way two voices share one segment cleanly.

**Verification:** live `make conversation` produced a **22-turn, 2:47** two-voice segment
(`vell_night` + `dj_two`), continuity `OK` on the first `sonnet` pass. The dialogue reacts and
builds turn-to-turn (distinct voices: Vell musing/warm, Wren bright/forward), gives a real time
check at the handover, and references canon glancingly ("four days out from the Lumen," weeks-old
letters riding the relay) without explaining it — judged "a conversation, not two narrators." 24
`pytest` pass; `ruff` + format clean; env-drift guardrail green; the single-DJ B3 path still
assembles.

**Next:** B5 — program format templates (`news` / `talk` / `music`), each `(now, context) ->
Segment`; `talk` wraps this B4 conversation.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-19 — Phase B — B3 context assembly for the writer (structured retrieval; vector RAG stubbed)

**Focus:** feed the writer the *right slice* of the world for `now` — cheaply and fast — from the
DB, and stop reading the whole `CANON.md` into the prompt. The retrieval spine for B4–B6.

**Decisions (the durable ones):**
- **`src/world/context.py` — `assemble(now, *, topic, speaker)` splits the world into two parts
  that match the two cost seams.** A **cached stable core** (series bible + the speaking DJ's card)
  → sent as `cached_context` (the prompt-cache lever, ~0.1x on repeats); plus the **dynamic now**
  (events near `now` with live status + relative phrasing, and topic-relevant canon) → the small
  per-call part. The split is deliberate: the core barely changes, the dynamic part is what makes a
  segment time-aware.
- **Structured retrieval only; vectors stay a documented, *unused* seam.** Date/status/tag SQL is
  the right, fast tool while the canon is tiny. `src/providers/embeddings.py` fixes the contract
  (`retrieve()` no-op returning `[]`; `embed()` raises) with the TRIGGER spelled out — implement
  real vectors only when the context outgrows the cache *or* you need meaning-based (not date/tag)
  recall. `context.py` never calls it (done-when: "the seam exists but is unused").
- **The series bible is read from `CANON.md`, not the DB.** It's standing prose not projected into
  rows; a `canon_source.load_series_bible()` extracts just those sections, so `CANON.md` stays the
  single human-editable source while everything dynamic comes from the DB.
- **Canon goes in the *dynamic* (queried) half, not the cache** — matching the RAG intent
  (tag-matched to topic, anticipating growth). Today facts carry no tags, so a topic query falls
  back to the full (small) canon via a new `store.canon_by_tags()` — the seam is ready for when
  facts get tagged.
- **`context.py` touches no SQL** — the only DB block calls the `store` seam; psycopg never leaks
  out of `store.py`.

**Changed:**
- New: `src/world/context.py`, `src/providers/embeddings.py`, `tests/test_context.py`.
- Updated: `src/world/store.py` (`canon_by_tags`), `src/world/canon_source.py`
  (`load_series_bible`), `src/writer.py` (calls `context.assemble`, no more whole-file read),
  `src/produce.py` (dropped the canon read), `src/config.py` (`context_event_window_days`,
  `writer_speaker_id`), `tests/test_canon_source.py` (bible-loader test), `Makefile`
  (`make context`), `README.md`.

**Why:** a flat file can't answer "what's relevant *now*?" cheaply. Splitting cached-core from
queried-dynamic keeps the cost lever while making the prompt time-aware; deferring vectors avoids
standing up pgvector before it earns its keep.

**Verification:** `make context` prints the cached core (bible + Vell's card) and the dynamic slice
— the Lumen Festival rendered live as **"in five days (upcoming)"** plus the 7 canon facts. A
stubbed `llm.generate` confirmed the writer sends bible+card as `cached_context` and clock + events
+ facts in the system prompt. 20 `pytest` pass; `ruff` clean; env-drift guardrail green.
*(Noted, not fixed — pre-existing B1 parser truncates a multi-line event `**Body:**` to its first
line; out of B3 scope.)*

**Next:** B4 — second DJ + the conversation orchestrator (showrunner → dialogue → continuity),
two-voice render.
Commit: 7d114f1 · Clips: (none)

---

## 2026-06-19 — Phase B — B2 world clock + event progression + relative-time renderer

**Focus:** the time-awareness spine, and the proof of the progressing event — render the *same*
event at two `now` values and watch the phrase flip ("in five days" → "yesterday").

**Decisions (the durable ones):**
- **`src/world/clock.py` is the single source of the real→in-world (`now + 600y`) mapping.** The
  inline computation that lived in `writer.py` moved here; the writer now calls
  `clock.render_wall_clock`. Two uses kept deliberately apart: **display** (`render_wall_clock`)
  keeps the real weekday/day/month and only relabels the year (+600), honouring CANON's "a real
  Tuesday is an in-world Tuesday"; **arithmetic** (`to_inworld`/`to_real`) shifts both sides by
  +600 so the gap to an event is identical in real and in-world frames. Handles the 29-Feb
  Gregorian trap (2000 leap, 2600 not).
- **`src/world/events.py` is pure (no DB/IO).** `status_of(event, now)` → upcoming/today/past and
  `relative_phrase(event, now)` → "tomorrow"/"in five days"/"tonight"/"yesterday"/"last week" —
  computed against the in-world `now`. Purity makes the brittle bit (phrasing thresholds) trivially
  testable and lets B3 call it on already-fetched rows.
- **Phrasing thresholds + number-words are domain constants, not config** — named module-level
  constants next to the code (per the B0.5 config-vs-constant rule), since they're intrinsic to the
  renderer, not operator-tunable.
- **The demo anchors `now` on the event's own date** (not the wall clock), so the proof is
  deterministic: five days before → "in five days" (upcoming); one day after → "yesterday" (past).

**Changed:**
- New: `src/world/{clock,events}.py`, `tests/test_clock.py`, `tests/test_events.py`.
- Updated: `src/writer.py` (calls `clock` instead of inline `+600y`), `src/world/store.py` (a small
  read for the demo), `Makefile` (`make demo`), `README.md`.

**Why:** "a world that progresses" is the whole Phase B pitch and the future hero clip; it needs one
authoritative clock and a renderer that turns a stored date into the phrase a DJ would actually say.

**Verification:** `make demo` reads the seeded Lumen Festival and prints `[upcoming] "in five days"`
at `now−5d` and `[past] "yesterday"` at `now+1d`. `pytest` (clock + events) green; `ruff` clean.

**Next:** B3 — context assembly: cached core (bible + DJ card) + structured-query dynamic
(events/canon), the vector seam stubbed; rewire the writer onto it.
Commit: cb23d09 · Clips: (none)

---

## 2026-06-19 — Phase B — B1 world-state DB: schema + SQL seam + seed from canon

**Focus:** moved the world out of the flat file into a queryable Postgres store — the spine for the
time-awareness (B2) and context-assembly (B3) work to come. Schema, one SQL seam, and a
reproducible seed that projects `docs/CANON.md` into the DB.

**Decisions (the durable ones):**
- **`src/world/store.py` is the ONLY place SQL lives** — same seam discipline as `providers/`.
  Nothing else imports `psycopg`. It owns the row dataclasses (1:1 with tables), reads
  `settings.database_url` (never a literal), logs every query/error, and exposes the structured
  reads B2/B3 need (`events_by_status`, `events_in_range`, `get_cast_member`, …).
- **CANON.md stays the single human-editable source; the DB is a projection of it.** Added
  `src/world/canon_source.py` to *parse* the markdown (numbered facts, `### ` DJ cards, `### `
  events) rather than keep a second machine copy. Restructured CANON.md's DJ section into a
  parseable `## Cast` (two cards) and a new `## Events` timeline with a real in-world datetime.
- **Seed reproduces by TRUNCATE + reload in one transaction** — re-running yields the exact state
  the file describes (no orphans, no dupes), satisfying "reproducible." Stable slug ids
  (`canon-1`, `vell`, `lumen-festival`) keep references stable across re-seeds.
- **Defined the second DJ: Wren, the first-light host** — a bright, question-asking foil to Vell's
  calm night shift; maps to the `dj_two` Kokoro voice reserved in B0. (Approve/tune the persona.)
- **pgvector deliberately NOT installed.** Structured date/status/tag queries are the right
  retrieval now; the vector path is a documented FUTURE slot in `store.py` (extension +
  `canon_embeddings` table), wired in B3 via the `providers/embeddings.py` stub. `tags` is a real
  `text[]` column now (populated for cast/events; canon tags enriched in B3).

**Changed:**
- New: `src/world/{__init__,store,canon_source,seed}.py`, `tests/test_canon_source.py`.
- Updated: `docs/CANON.md` (`## Cast` with Vell + new Wren; `## Events` with the dated Lumen
  Festival), `requirements.txt` (`psycopg[binary]`), `Makefile` (`make seed`), `README.md`
  (Postgres install + seed step + pgvector-deferral note + store-seam dev note), `.env.example`.
- Dev env: `brew install postgresql@14` + `createdb settlement_radio`; installed `psycopg` in
  `.venv`.

**Why:** a flat file can't answer "what's happening near *now*?" — the whole point of Phase B is a
world that progresses, which needs date/status queries. Parsing CANON.md (not duplicating it) keeps
one source a human edits by hand, per CLAUDE.md.

**Verification:** `make seed` loads 7 canon / 2 cast / 1 event; re-running twice leaves counts
identical (idempotent). `events_by_status('upcoming')` and `events_in_range(...)` both return the
festival; out-of-window/`'past'` queries return empty. `pytest` (parser, 4) + the existing retry
tests pass; `ruff check src` clean.

**Next:** B2 — world clock (`now + 600y` as the single source), event progression + a relative-time
renderer ("in five days" → "yesterday"), and the two-`now` demo on the Lumen Festival.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-19 — Phase B — B0.5 foundation: config + logging + lint/pre-commit + retries

**Focus:** laid the engineering baseline before the world engine — one typed settings module,
structured logging, lint/format + a pre-commit gate, and bounded retries on the vendor seams — so
B1–B6 are *built on* the standards instead of retrofitted. Then hardened config against future
sprawl (a config-vs-constant policy, area-prefix naming, and an automated drift guardrail).

**Decisions (the durable ones):**
- **One typed settings module, `src/config.py` (`pydantic-settings`).** Every tunable now reads
  `settings.X`; no module reads a literal or the env directly. Precedence is process env → `.env` →
  defaults. Secrets and conventional names (`ANTHROPIC_API_KEY`, `TTS_PROVIDER`, `DATABASE_URL`)
  kept their plain forms, so `.env` and the per-run `TTS_PROVIDER=x make play` ergonomic are
  unchanged. The tier→model-id map moved here as `settings.model_id(tier)`.
- **Config vs domain constant — the real anti-sprawl rule, written into config.py's header.** Only
  environment/run-tunable values live in `Settings`; logic *intrinsic to an algorithm* (relative-
  time thresholds later, `_part_of_day` cutoffs, the vendor voice registries) stays as a *named*
  module constant next to its code. A named constant is not a "magic number"; hauling it into
  Settings makes a god-object, which is the mess to avoid.
- **Area-prefix naming to prevent collisions as B1–B6 add fields.** `llm_`/`tts_`/`world_`/
  `segment_`/`writer_`/… (reserved `context_`/`convo_`/`format_`/`buffer_`). Applied now while
  small — renamed the unprefixed Phase-A fields (`years_ahead`→`world_years_ahead`,
  `vell_voice`→`segment_vell_voice`, `words_*`→`writer_words_*`, the `elevenlabs_*`/`kokoro_*`→
  `tts_*`) so B4's cap is `convo_max_tokens`, never a bare `max_tokens`.
- **`structlog`, JSON by default, configured once.** `LOG_JSON=false` for pretty console. Every
  external call and pipeline step logs start/outcome; replaced the `print()`/silent paths in
  `llm.py`/`tts.py`/`writer.py`/`produce.py`. (CLI *deliverable* output — the writer's printed
  script — stays on stdout; logging is for diagnostics.)
- **Bounded retry on the seams (`src/retry.py`).** Claude's stream and every TTS render go through
  `call_with_retry` — retries with linear backoff, logs each attempt loudly, re-raises on
  exhaustion. The rule is "fail loudly into the logs, never silently produce nothing."
- **`ruff` (lint+format) in `pyproject.toml`; a fast pre-commit gate.** Hooks: ruff, `gitleaks`
  (the automated backstop to "never commit keys"), a **custom config-drift guardrail**
  (`scripts/check_no_direct_env.sh` — blocks `os.getenv`/`os.environ`/`dotenv` anywhere under
  `src/` except `config.py`), and whitespace/EOF/large-file/JSON-YAML-TOML basics. **No test suite
  in pre-commit** (it would get bypassed).

**Changed:**
- New: `src/config.py`, `src/logging_setup.py`, `src/retry.py`, `tests/test_retry.py` (the one
  non-trivial bit), `scripts/check_no_direct_env.sh`, `pyproject.toml`, `.pre-commit-config.yaml`.
- Updated: `src/providers/llm.py` + `src/providers/tts.py` (settings + logging + retry; dropped
  `load_dotenv`), `src/writer.py` + `src/produce.py` (settings + logging; field renames),
  `requirements.txt` (pydantic-settings, structlog; dev: ruff, pre-commit, pytest), `.env.example`
  (logging/retry/DB knobs), `README.md` ("Developing the station backend" section).
- Dev env: installed pydantic-settings, structlog, ruff, pre-commit, pytest into `.venv`.

**Why:** B0.5's whole point is to set the standards while the code is ~6 files, so the world engine
inherits them. The config-vs-constant policy + prefixes + guardrail are the cheap insurance against
the settings module rotting into an unsearchable junk drawer once B1–B6 pile on their knobs.

**Verification:** `ruff check src` clean; `pytest` 3 passed; full `pre-commit run` green incl. the
guardrail — and the guardrail correctly **blocks** a planted `os.environ` violation. Forced an
Anthropic stream failure → caught, logged (`llm_generate_start`→`external_call_retry`→
`external_call_failed`), re-raised. The real `make_segment` path emits the info-level JSON chain
(`make_segment_start`→`write_segment_script_*`→`make_segment_done`).

**Next:** B1 — PostgreSQL world-state DB: schema (`canon`/`cast`/`events`/`state`),
`src/world/store.py` (the only SQL seam, reads `settings.database_url`), and a reproducible seed
from `docs/CANON.md`.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-19 — Phase A2 — the coming-soon site (`/web`), live on settlementradio.com

**Focus:** built and shipped the public coming-soon page — a single branded night-field screen
with working email capture — as a Next.js app in a new `/web` folder, deployed to
**settlementradio.com** via Vercel. First non-Python surface; the seed that grows into the audio
player + studio in Phase C.

**Decisions (the durable ones):**
- **Monorepo, one repo.** The Python station stays at the root; `/web` is a self-contained Next.js
  (App Router + TS + Tailwind) app. **Vercel deploys only `/web`** (Root Directory = `web`); the
  backend is never built or deployed by Vercel. Recorded in `CLAUDE.md` (A2-T7) so the two-part
  shape is canon.
- **Email signup with no database.** A server route `app/api/subscribe/route.ts` holds the
  **Buttondown** key server-side and POSTs `{email_address}`; the client form never sees the key.
  Honeypot field + email validation; Buttondown's `400 email_already_exists` is mapped to a
  friendly "already on the list". Buttondown chosen because it's also the newsletter surface.
- **The brand lockup *is* the `<h1>`.** The horizontal wordmark SVG (beacon + wordmark) renders as
  the page heading via its `alt` text — on-brand and accessible without duplicate text. Brand
  tokens are Tailwind v4 `@theme` vars (`night`/`amber`/`neutral`); Inter via `next/font`.
- **Metadata points the OG/Twitter image absolute.** `metadataBase = https://settlementradio.com`
  so the branded `og-image.png` resolves to an absolute URL for crawlers; title + description carry
  the fiction/AI disclosure. (Known nit: the OG asset is a *portrait* stacked lockup, so a
  `summary_large_image` Twitter card will center-crop it — flagged for a later landscape asset.)
- **`/web` env is separate from the root `.env`.** Next only reads env files inside its own project
  dir, so the Buttondown key lives in `web/.env.local` (gitignored) and as a Vercel env var — not
  the root `.env`. This bit us once: the key was in root `.env` and the route saw nothing.
- **Heed the Next 16 breaking-changes warning.** `web/AGENTS.md` says this Next.js differs from
  training data — read `node_modules/next/dist/docs/` before coding (Image, route handlers,
  metadata APIs all confirmed against the shipped docs).

**Changed:**
- New: `web/` Next.js app — `src/app/page.tsx` (coming-soon screen), `src/app/SignupForm.tsx`
  (client form), `src/app/api/subscribe/route.ts` (Buttondown route), `src/app/layout.tsx`
  (metadata), `src/app/globals.css` (brand tokens), `public/` brand assets, `.env.example`,
  `README.md`.
- Updated: root `CLAUDE.md` (the monorepo / `/web` subsection, A2-T7).
- Accounts/infra (manual): Buttondown list + API key; Vercel project (Root Directory = `web`) with
  the key as an env var; **settlementradio.com** DNS pointed at Vercel — **Microsoft mail records
  left untouched** so `hello@settlementradio.com` keeps delivering.

**Why:** a coming-soon page that captures emails is the cheapest "built in public" surface, and
doing it as the *real* Next.js app (not a throwaway) means Phase C's player is new routes, not a
rebuild. Keeping the key server-side and the web env separate from the station's is the difference
between "works on my laptop" and "safe to deploy".

**Verification:** `npm run build` / `lint` / `tsc --noEmit` all green. `/api/subscribe` smoke-tested
live — invalid email → 400, honeypot filled → 200 (no API call), valid email with no key → 500.
The Buttondown key authenticates (GET `/v1/subscribers` → 200). Rendered `<head>` shows the
`og:*` / `twitter:*` / `<title>` tags with absolute image URLs. Page deployed and served over
HTTPS at settlementradio.com (T5, done manually).

**Next:** A2-T6 (optional) — flip on Vercel Web Analytics — then Phase B (the world engine /
nightly batch). Consider a dedicated landscape Twitter/OG image.
Commit: A2-T0 84b6a54 · A2-T1 b872cc0 · A2-T2 da0d443 · A2-T4 7b16259/bcf2c38/b176d76 ·
A2-T7 (uncommitted) · Clips: (none)

---

## 2026-06-17 — Phase A — free offline TTS backend (`say`) for testing

**Focus:** added a second TTS backend — macOS's built-in `say` — so the loop can be
tested unlimited and offline, after ElevenLabs' free tier ran dry (~2 full segments/month).

**Decisions (the durable ones):**
- **A `TTS_PROVIDER=say` backend, selected by env, alongside `elevenlabs` (still default).**
  The seam's whole point is parallel backends; `say` is offline, free, unlimited, and
  needs no key — ideal for exercising the pipeline without spending voice credits. It's a
  *test* voice, not Vell's real one.
- **Override per-run, don't change the default.** `TTS_PROVIDER=say make play` beats `.env`
  (dotenv doesn't override a shell var), so the default stays `elevenlabs` and the free path
  is one prefix away.
- **A shared `_to_mp3()` helper (ffmpeg) for non-mp3 backends.** `say` emits AIFF; the helper
  transcodes to the mp3 the pipeline expects. Deliberately shared so the future Kokoro backend
  (emits WAV) reuses it — adding `say` is groundwork, not throwaway. The only per-provider bit
  is its voice registry (`_SAY_VOICES`: `vell_night` → "Daniel").

**Changed:**
- Updated: `src/providers/tts.py` (`_synthesize_say` + `_to_mp3` + `say` dispatch + registry),
  `.env.example` (document the three providers + the override tip), `README.md` (provider-seams
  + Run notes).

**Why:** TTS is the real cost wall (the script side is cache-cheap), so a free, offline voice
keeps development unblocked when credits are exhausted — without touching anything but `tts.py`,
which is exactly what the provider seam was built to allow.

**Verification:** `TTS_PROVIDER=say .venv/bin/python -m src.produce` generated
`segments/vell-20260617T200508.mp3` — **246 s (~4.1 min)**, valid mp3 via `ffprobe` — with zero
ElevenLabs credits spent (only the cheap streamed Anthropic script call). Playout is
provider-agnostic, so the T6 loop serves it unchanged.

**Next:** commit the T5/T6/streaming + `say` work; optionally wire Kokoro later as the free
*offline + high-quality* voice (reuses `_to_mp3`).
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T6 one-command loop + browser player (+ streaming fix)

**Focus:** made the whole Phase A loop a single command (`make play`), gave it a real
browser play button, and fixed the script step's "looks-frozen" UX. This is the **Phase A
definition of done** — verified by hearing a freshly generated Vell segment in the browser.

**Decisions (the durable ones):**
- **`make serve` always runs `stop` first.** Backgrounded Icecast instances kept surviving
  and squatting port 8000 ("Could not create listener socket"). Making `serve` depend on
  `stop` (which kills by PID file *and* by process pattern) means a stale server can never
  block a fresh start — the recurring orphan problem is structurally gone.
- **Processes background via `nohup` into `.run/` (gitignored); Liquidsoap runs through
  `opam exec`.** No more "leave a terminal open per service" and no need to `eval "$(opam
  env)"` first — `make` finds Liquidsoap itself. PIDs + logs live in `.run/`.
- **A minimal static player page (`config/web/index.html`) served by Icecast at `/`.**
  Browsers won't render a play button for a *bare* MP3 mount (Chrome/Firefox showed "empty
  page" on `/settlement.mp3`), so the page wraps the mount in `<audio controls>`. It's also
  the home for the **AI-generation disclosure** (a CLAUDE.md hard rule) — *not* the
  out-of-scope "web player UI", just one static file.
- **`llm.generate` now streams** (with an optional progress callback + a 120s timeout). The
  non-streaming call blocked silently at the socket for the full ~25s generation, looked
  hung, and kept getting Ctrl-C'd. Streaming returns the same string but surfaces progress
  (`produce.py` prints a dot per chunk) and makes a real network stall fail fast.

**Changed:**
- New: `Makefile` (`generate`/`serve`/`play`/`stop`/`status`), `config/web/index.html`.
- Updated: `config/icecast.xml` (webroot → `config/web`, `/` → the player), `src/providers/llm.py`
  (streaming + `on_token` + `timeout`), `src/writer.py` + `src/produce.py` (thread the progress
  callback), `README.md` (T6 run section), `.gitignore` (`.run/`).

**Why:** one command + clean start/stop is what makes the loop demoable and stops the
orphan-process foot-guns; the player page is the difference between "serves a stream URL" and
"a human opens it and hears Vell"; streaming is what stops a 25-second call from looking broken.

**Verification:** `make play` generated `segments/vell-20260616T225823.mp3` and served it —
`http://localhost:8000/` shows the player, the mount returns `200 audio/mpeg`, and Liquidsoap's
`libmad` decoded the **new** segment (confirmed in `.run/liquidsoap.log`). Heard end-to-end in
the browser. **Known external blocker:** ElevenLabs **free-tier quota** caps fresh renders at
~2 full 5-min segments/month (~4.2k credits each); once exhausted, `make play` fails at the TTS
step with `quota_exceeded` (401) until the monthly reset — the pipeline itself is unchanged and
proven. (Recorded to project memory.)

**Next:** commit the T5 + T6 + streaming work (on a branch); optionally T7 (`make drop`, a ~60s
segment) — which also fits within leftover ElevenLabs credits. Otherwise Phase A is done.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T5 playout (Layers 5–6): loop on a local stream

**Focus:** stood up local playout — Liquidsoap loops the newest segment to a local Icecast
mount with a never-dead fallback, so the stream is always live.

**Decisions (the durable ones):**
- **Homebrew no longer ships `liquidsoap`; build it from source via opam — *with* the MP3
  plugins.** This was the session's real friction. The task assumed `brew install liquidsoap`,
  but the formula is gone and upstream ships only Linux `.deb`s. Installed via `opam`, and
  critically had to add **`lame` (MP3 encode)** and **`mad` (MP3 decode)** — the first build
  had neither, so `%mp3` was "unsupported format" and it couldn't even read the segments. Also
  needed `CPATH`/`LIBRARY_PATH` → Homebrew so the C stubs find headers on Apple Silicon. All of
  this is now in the README so the build is reproducible.
- **`radio.liq` re-picks the newest file on every loop** (`request.dynamic`), so a freshly
  generated segment is adopted with no restart. Filenames sort by time → "last in a sorted
  listing wins."
- **Never-dead fallback:** `assets/bed.mp3` if present, else a quiet sine tone, via
  `fallback(track_sensitive=false, …)` + `mksafe` — Icecast drops a source-less mount, so the
  stream must never be silent.
- **Icecast is local-only:** bound to `127.0.0.1:8000`, source password `hackme` matching
  `.env` / `ICECAST_SOURCE_PASSWORD`. Not hardened for public — that's Phase C.

**Changed:**
- New: `config/icecast.xml`, `config/radio.liq`. Updated `README.md` (Playout/install section).
- System: `brew install icecast ffmpeg coreutils curl lame mad`; `opam` + `opam install
  liquidsoap lame mad` (Liquidsoap 2.4.4).

**Why:** the "newest file wins + always-on fallback" pair is the minimal seed of the Phase-5
scheduler (buffer depth as a parameter) without building a scheduler; pinning down the opam +
lame/mad reality now means future machines reproduce the build instead of rediscovering it.

**Verification:** `liquidsoap --check config/radio.liq` passes clean; starting Icecast +
Liquidsoap serves `http://localhost:8000/settlement.mp3` (`200 audio/mpeg`), and the log shows
`libmad` decoding the real Vell segment (not the fallback tone). Several orphaned test-Icecast
processes were cleaned up afterward.

**Next:** T6 — one command (`make play`) + a browser the human can actually press play in.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T4 render to audio (Layer 4)

**Focus:** wired the Phase A pipeline end to end — script → TTS → a populated `Segment` with a
playable audio file on disk.

**Decisions (the durable ones):**
- **`length_target_sec` is a parameter with a default, not a hardcoded `300`.** `make_segment`
  defaults to ~5 min but takes the dial as a keyword arg, so the T7 60-sec drop is a different
  argument, not a rewrite — honouring the Segment seam.
- **Timestamped segment ids (`vell-YYYYMMDDThhmmss`).** Sortable so Liquidsoap's "newest file
  wins" (T5) is trivial, and ids never collide across runs.
- **Paths resolved from the module, not the cwd.** Canon read from `docs/CANON.md` and audio
  written under `segments/` via `__file__`-relative paths, so `python -m src.produce` works from
  anywhere. `format="talk"`, `disclosure=True` set per the T4 spec.
- **No vendor SDKs here.** `produce.py` only touches the two seams (`writer` + `tts`), keeping
  the whole pipeline behind the abstractions.

**Changed:**
- New: `src/produce.py`. Updated `README.md` (T4 section).

**Why:** making length a dial on this one function is what later lets the same path serve an
overnight block and a near-live drop; routing through the seams keeps model/TTS swaps a one-file
change.

**Verification:** `.venv/bin/python -m src.produce` generated
`segments/vell-20260616T104252.mp3` — 4,093,536 bytes, **255.8 s (~4.3 min)** confirmed via
`ffprobe` — in Vell's voice, and returned a populated `Segment` (`format=talk`,
`length_target_sec=300`, `disclosure=True`).

**Next:** T5 — playout: install `liquidsoap`/`icecast`/`ffmpeg` via Homebrew, loop the newest
segment on a local Icecast stream with a silence-avoidance fallback.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T3 script generation (Layer 3, minimal)

**Focus:** got Claude writing Vell's ~5-min night-shift segment from the canon — the single-
function "writers' room", no multi-agent yet.

**Decisions (the durable ones):**
- **Canon rides in `cached_context`; only the small per-call instructions + clock pay full
  price.** The bulky stable world bible is the cache breakpoint (the Phase A cost lever); the
  variable system prompt stays compact.
- **The +600yr clock is computed, never hardcoded, and preserves the real weekday.** A real
  Tuesday 02:00 becomes an in-world Tuesday 02:00 six centuries on, so the spoken time check is
  accurate. A `_part_of_day` phrase steers the time-check mood.
- **Tier `sonnet` (the default writing brain); spoken-script-only output** — no stage directions,
  labels, or headings, so the text goes straight to TTS.
- **`safety_check(text)` is a no-op placeholder** marking exactly where a content gate slots in
  before any public broadcast.

**Changed:**
- New: `src/writer.py`. Updated `README.md` (T3 section).

**Why:** caching the whole canon keeps input cost ~0.1x on repeat runs, and computing the clock
(rather than baking a year) means the time check never goes stale — the two things this step has
to get right to be reusable.

**Verification:** `.venv/bin/python -m src.writer` prints a coherent, in-character ~700–800-word
script with a correct "settlement time" time check for the current time.

**Next:** T4 — `src/produce.py`: script → TTS → a populated `Segment` audio file.
Commit: 14902ba · Clips: (none)

---

## 2026-06-16 — Phase A — T2 the Segment model (Seam #2)

**Focus:** built Seam #2 — the `Segment` dataclass — so segment length and lead-time become
dials on one code path instead of assumptions baked into the pipeline.

**Decisions (the durable ones):**
- **`Segment` matches the ARCHITECTURE.md spec verbatim**, dials and all: `length_target_sec`
  (required, no default — callers *must* dial it) and `lead_time_sec` (defaults 0). Keeping the
  shape identical to the doc means later phases plug in without a rewrite.
- **`length_target_sec` is a required field, not defaulted.** Forcing it at construction is the
  enforcement of "never hardcode length" — there's nowhere for a magic 300 to hide.
- **`disclosure` defaults `True`; `meta` is a `field(default_factory=dict)`** open bag for
  per-format extras, so the dataclass stays stable as formats grow.

**Changed:**
- New: `src/segment.py`. No other files touched (writer/produce consume it in T3–T4).

**Why:** making length and lead-time *inputs* is what later lets one `make_segment` serve a
3-hour overnight block and a 60-second near-live drop — only the numbers and the model/TTS tier
change, never the code path.

**Verification:** `python3 -c "from src.segment import Segment; print(Segment(id='demo-001',
format='talk', length_target_sec=300))"` constructs and prints a fully-populated Segment
(dials + `disclosure=True` + empty `meta`). No length is hardcoded anywhere else.

**Next:** T3 — `src/writer.py`: Claude writes Vell's ~5-min segment from the canon, canon passed
as the cache breakpoint.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-14 — Phase A — T1 provider abstraction (the two vendor seams)

**Focus:** built Seam #1 — the only two modules that touch a vendor SDK — so every later
task talks in logical tiers/voices and never imports `anthropic`/`elevenlabs` directly.

**Decisions (the durable ones):**
- **Tiers map to real IDs inside `llm.py`, nowhere else.** `haiku`→`claude-haiku-4-5-20251001`,
  `sonnet`→`claude-sonnet-4-6` (default), `opus`→`claude-opus-4-8`. Unknown tier raises early.
- **`cached_context` is a real cache breakpoint from day one.** It's placed *first* in the
  system prompt with `cache_control: ephemeral`, and the small per-call `system` text follows
  it — caching is a prefix match, so the stable canon must precede the volatile part. (Phase A
  prefixes may be below the model's min cacheable size and silently not cache; the path is still
  in use and grows into Phase B free.)
- **`generate` is plain text-in/text-out — no thinking.** Simplest general-purpose seam and
  keeps text cost trivial; a thinking knob can be added later without changing callers.
- **TTS backend chosen by `TTS_PROVIDER`; `kokoro`/`orpheus` raise a clear `NotImplementedError`
  stub.** Logical voice `vell_night` → ElevenLabs "Adam" (`pNInz6obpgDQGcFmaJgB`), the only place
  a vendor voice id appears. `emotion` is accepted but reserved (no vendor knob wired yet).

**Changed:**
- New: `src/providers/llm.py`, `src/providers/tts.py`, `src/__init__.py`,
  `src/providers/__init__.py`. Updated `README.md` (provider-seams section).
- Created a throwaway `src/_scratch_t1.py`, ran it, deleted it (+ its `segments/_test.mp3`).

**Why:** isolating both vendors behind one function each is what later lets us swap models,
swap TTS to self-hosted, and share one code path between overnight batch and 60-sec near-live —
without touching anything upstream.

**Verification:** `python -m src._scratch_t1` made a live Claude call (returned a greeting) and
a live ElevenLabs call (`segments/_test.mp3`, 24,703 bytes, confirmed real MPEG layer-III audio
via `file`). Both keys read from `.env`. Scratch + artifact deleted afterward.

**Next:** T2 — the `Segment` dataclass (Seam #2), so segment length/lead-time become dials.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-14 — Phase A — T0 repo scaffold (skeleton + venv)

**Focus:** stood up the reproducible project skeleton so the build has somewhere to live —
no pipeline logic yet, just the tree, ignores, deps, and the env template.

**Decisions (the durable ones):**
- **`.gitkeep` to version the empty dirs.** `segments/` and `assets/` are gitignored, but the
  dirs ship in git via a `.gitkeep` each (ignore `segments/*` but un-ignore the keep file), so a
  fresh clone has the tree the pipeline expects without committing generated audio.
- **`.env.example` holds every Phase A setting, not just T1's.** Added `ICECAST_SOURCE_PASSWORD`
  (T5) now with a working local default (`hackme`) so the human fills keys once. Vendor voice IDs
  stay **out** of env — the `vell_night` → real-id map lives in the `tts.py` registry per Seam #1.
- **Loose lower-bound pins** in `requirements.txt` (`anthropic>=0.40`, `elevenlabs>=1.0`,
  `python-dotenv`, `requests`) — simplest reproducible install for a solo Phase A.

**Changed:**
- Created the tree: `src/`, `src/providers/`, `config/`, `segments/` + `assets/` (gitignored,
  with `.gitkeep`).
- New files: `.gitignore`, `.env.example`, `requirements.txt`, `README.md` (setup + layout).
- Created `.venv/` (Python 3.13.5, satisfies 3.11+) and installed all deps.

**Why:** a clean, clone-and-run skeleton up front means every later task (T1→T6) just drops a file
into a known place; the `.env.example`-completeness + `.gitkeep` choices both exist to make
"fill keys once, then it works from a fresh clone" true.

**Verification:** `pip install -r requirements.txt` succeeds in the fresh venv; all four deps
import; `git check-ignore` confirms `.env` and `segments/*.mp3`/`assets/*.mp3` are ignored while
`.gitkeep` stays tracked. Tree matches CLAUDE.md → "Repo conventions".

**Next:** T1 — the provider abstraction (`llm.py` + `tts.py`), pending API keys in `.env`.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-13 — Phase 0 (planning) — Project shape, name, and the full doc pack settled

**Focus:** turned a broad idea into a decided plan — architecture, funding angle, name, and the
document set that drives the build — before touching Claude Code.

**Decisions (the durable ones):**
- **Architecture = hybrid, no hardware bought.** Cheap always-on CPU VPS (Hetzner CX22, ~€4/mo)
  for 24/7 playout; generation via on-demand/serverless GPU or APIs; YouTube Live as the free,
  unlimited-listener relay. Chosen over buying a Mac Mini.
- **Anthropic angle = "powered by Claude," honestly framed.** Anthropic supplies all
  intelligence + the whole build (Claude Code); voice is the one external piece (no Anthropic
  TTS exists). Realistic Anthropic support is *being featured*, not big credits (those need
  institutional equity funding); fund usage via small self-serve credits + Claude on AWS/GCP
  credits. So the MVP's job is to be **featurable**.
- **MVP scope:** 2 DJs, 1 show, 3 formats, small real canon, batch-only generation + one 60-sec
  near-live demo, content-safety gate + AI disclosure, built by Claude Code and documented in
  public. Everything bigger is explicitly deferred.
- **Name = Settlement Radio.** Verified clean at the brand/trademark level (no station, podcast,
  or media brand uses it). Worldbuilding justification: "settlement" is a *linguistic fossil* —
  the worlds are mature city-planets but still called the settlements out of six-century habit.
- **In-world year = real year + 600, computed at generation time** — never hardcoded (so it
  never goes stale).
- **Model routing:** Sonnet 4.6 default writing brain; Haiku 4.5 for high-volume/near-live;
  Opus 4.8 for rare hard reasoning; Fable/Mythos not workhorses. **Batch API + prompt caching
  mandatory** — text cost stays near-trivial; TTS is the real cost driver.
- **Voice:** ElevenLabs free tier now, behind the TTS abstraction, swappable to Kokoro/Orpheus.
- **Two load-bearing seams:** provider abstraction (swap model/voice/local↔cloud) and the
  Segment abstraction (segment length + lead-time as parameters → batch and near-live share one
  path).
- **Infra identity:** create a GitHub **org** `settlementradio` (org name is the scarce asset),
  repo lives inside. Buy the **domain first**; use Cloudflare free Email Routing to forward a
  branded address into a dedicated project inbox; register *all* project accounts to that, not
  personal email.
- **Habit:** devlog + screen recordings from Phase 0 (Cmd+Shift+5 now, asciinema for terminal
  sessions, OBS later — it doubles as the Phase C streaming tool).

**Changed (documents produced/updated this session):**
- Created the four-file Claude Code pack: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/CANON.md`,
  `docs/PHASE_A_TASKS.md`.
- Created `docs/ROADMAP.md` (the single who-does-what-when path: Phase 0 → A → B → C → D →
  Beyond).
- Created the strategy set: funding & licensing kit, the Anthropic-anchored build plan, the
  marketing strategy.
- Updated docs with: the Settlement Radio name, the floating-year fix, the "linguistic fossil"
  canon note, and the model-routing + batch/caching rules (in CLAUDE.md, ARCHITECTURE.md, and
  PHASE_A_TASKS.md).

**Why (the key reasons):**
- Hybrid over hardware: near-zero up-front cost, fits €0–40/mo, and credits subsidize cloud/API
  but never a hardware purchase.
- Settlement Radio over prettier names: the cozy-audio namespace is crowded, so plain + verified
  beats evocative + taken; it also ties to the canon's "settlement time."
- Just-in-time task packs: only Phase A is detailed on purpose; B–D get written when reached, so
  they're informed by what Phase A actually teaches.

**Next:** execute Phase 0 — buy the domain (everything hangs off it), set up the forwarding
inbox, claim handles + the GitHub org, install Claude Code, get Anthropic + ElevenLabs API keys,
stand up the coming-soon page, start recording. Then in Claude Code: create the repo in the org,
upload the four-file pack, run `PHASE_A_TASKS.md` from T0.
Commit: (pre-repo; docs created in planning chat) · Clips: (none yet — start with Phase 0)

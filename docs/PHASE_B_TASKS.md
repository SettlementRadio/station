# PHASE_B_TASKS.md — executable task list ("The Mind")

Work these **in order**, one at a time: implement, show what changed + how to verify, then stop
for review before the next. Respect `CLAUDE.md` (the two seams, model routing, cost levers, hard
rules) throughout. This pack is written against the **as-built** Phase A code (see
`docs/PHASE_A_ORIENTATION.md`), not the original sketch.

**Why this order:** the Phase A retro found that **voice (TTS) is the entire cost ceiling**, and
the ElevenLabs free tier covers only ~2 segments/month. Phase B multiplies voice volume, so we
**unblock voice first (B0)** or nothing downstream is testable. We also **defer vector RAG on
purpose** — structured queries over an events table are the fast, right retrieval for now;
embeddings are a stubbed seam, added only when lore outgrows the cached context.

**Definition of done for Phase B:** two DJs hold a sensible, in-character conversation that *uses*
canon without reciting it (B4), AND the progressing-event demo flips "in five days" → "yesterday"
end to end (B2). Bonus: the whole mind runs at volume for free via Kokoro (B0 + B6).

---

## B0 — Unblock voice: local Kokoro backend + length tune
**Goal:** free, unlimited, local voice so Phase B iteration isn't gated by paid credits; and hit
the length target.
**Do:**
- Implement the `kokoro` backend in `src/providers/tts.py`, behind the existing seam, reusing
  `_to_mp3()`. Install Kokoro locally and **document every install step in the README** (per the
  Phase A liquidsoap lesson — Homebrew/build pain is expected; write it down).
- Register two logical voices in the voice registry: `vell_night` and a second DJ voice (a
  distinct Kokoro preset) — the second DJ arrives in B1/B4 but reserve the voice now.
- Make `kokoro` the default `TTS_PROVIDER` for local generation; keep `elevenlabs` for future
  flagship use and `say` as the offline fallback. Keep the `emotion` param flowing (accept it;
  map to what Kokoro supports or ignore gracefully — do not break the signature).
- Tune length: Phase A renders ~250s against a 300s target. Raise the word-count guidance in
  `writer.py`'s prompt (~900–950 words) so rendered audio lands within ~10% of `length_target_sec`.
**Done when:** `TTS_PROVIDER=kokoro make play` produces unlimited local segments at zero API cost,
two distinct DJ voices are selectable, and a talk segment renders within ~10% of its target length.

## B0.5 — Foundation: config + logging (do BEFORE the world engine)
**Goal:** establish the engineering baseline now, while the code is small, so the rest of Phase B
is built on it instead of retrofitted. (See `CLAUDE.md` → Engineering standards.)
**Do:**
- Add a single typed settings module `src/config.py` (`pydantic-settings`, loaded from `.env`).
  Migrate existing scattered values into it — model-tier names, paths, `TTS_PROVIDER`, segment
  defaults, timeouts, and (for B1) the DB connection. Code reads `settings.X`; remove literals.
- Set up structured logging once (`structlog` or stdlib `logging` with a JSON formatter), with
  levels. Replace any `print()`/silent paths in `llm.py`, `tts.py`, `writer.py`, `produce.py`
  with logged start/outcome lines; log every external call.
- Add `ruff` (lint + format) config to `pyproject.toml`; run it clean over `src/`.
- Add **pre-commit** hooks (`.pre-commit-config.yaml`) that run on every commit and block on
  failure — keep them FAST: `ruff` (lint + format), a secrets scanner (`detect-secrets` or
  `gitleaks` — the automated backstop to the "never commit keys" rule), and the basics
  (trailing-whitespace, end-of-file-fixer, large-file check, JSON/YAML validity). Do NOT put the
  test suite or any slow check in pre-commit, or it'll get bypassed. Document `pre-commit install`
  in the README.
- Wrap the existing Claude and TTS calls with basic error handling + a bounded retry; failures log
  loudly rather than producing nothing.
**Done when:** no config literals remain in module bodies (all via `settings`), a run emits
structured logs at info level, `ruff check` is clean, and a forced API error is caught + logged.

## B1 — World-state database + schema + seed from canon
**Goal:** move the world out of the flat file into a queryable store — the spine for
time-awareness and growth.
**Do:**
- Install PostgreSQL locally (Homebrew; document steps). Do NOT install/enable pgvector yet —
  vector search is deferred (see B3); note in the README where it will slot in.
- Schema (minimal but real): `canon(id, text, tags)`, `cast(id, name, card_text, logical_voice,
  tags)`, `events(id, title, body, in_world_datetime, status, tags)`, `state(key, value)`.
- `src/world/store.py` — the ONLY place SQL lives (same seam discipline as `providers/`). It
  reads the DB connection from `settings` (B0.5), not a hardcoded string, and logs queries/errors.
- A reproducible seed that loads current `docs/CANON.md` into the DB: the canon facts, BOTH DJ
  cards (Vell + a second DJ you define), and the Lumen Festival as an `events` row with an
  in-world datetime. `CANON.md` stays the human-editable source that seeds the DB.
**Done when:** the DB holds canon, two cast members, and at least one dated event; a query returns
events filtered by status/date; re-running the seed reproduces the state from `CANON.md`.

## B2 — World clock + event progression + relative-time renderer + the demo
**Goal:** the time-awareness spine, and proof of the progressing event.
**Do:**
- `src/world/clock.py` — formalize real→in-world (`now + 600y`) as the single source; replace the
  inline computation currently in `writer.py` with a call to it.
- `src/world/events.py` — a progression function that computes each event's status
  (upcoming/today/past) from its `in_world_datetime` relative to `now`, and
  `relative_phrase(event, now)` → "in five days" / "tonight" / "yesterday" / "last week".
- A small CLI/test that renders the **same** Lumen Festival event at `now − 5 days` and
  `now + 1 day` and shows the phrase flip.
**Done when:** the demo prints the correct relative phrasing for one event at two different `now`
values — the progressing-event proof (and your future hero clip).

## B3 — Context assembly for the writer (structured retrieval; vector RAG stubbed)
**Goal:** feed the writer the right slice of the world, cheaply and fast — without premature
vector search.
**Do:**
- `src/world/context.py` — `assemble(now, *, topic=None, speaker=None)` returns: the **stable
  core** (series bible + the speaking DJ's card) to pass as `cached_context` (keep the cache
  lever), PLUS the **dynamic bits** fetched by structured query (events near `now` by date/status,
  tag-matched canon for the topic).
- Add `src/providers/embeddings.py` as an **interface stub** and a `retrieve()` seam so vector
  search is a later drop-in. DO NOT stand up pgvector now. Document the trigger in the file:
  *add real embeddings only when the assembled context outgrows the cache window or you need
  semantic (not date/tag) recall.*
- Rewire `writer.py` to call `context.assemble(now)` instead of reading the whole `CANON.md`.
**Done when:** the writer's prompt is built from the DB (cached core + queried events/canon),
segments still generate correctly, and the vector seam exists but is unused.

## B4 — Second DJ + conversation orchestrator (the hard creative core)
**Goal:** two DJs holding a conversation that *uses* canon in character, not reciting it.
**Do:**
- `src/writers/conversation.py` — a light writers' room: a **showrunner** step picks a beat/topic
  from current events (via `context.assemble`); an **orchestrator** generates a two-voice dialogue
  from both cards + assembled context; a light **continuity** check (one `llm.generate`, tier
  `sonnet`, escalate to `opus` only if it flags trouble) checks the draft against canon.
- Start with a **single-call** dialogue (both personas in one prompt) — cheaper and more coherent;
  only try turn-by-turn multi-agent if the single-call output feels flat. Bake in anti-recitation
  instruction: facts are the DJs' *shared knowledge to reference naturally*, never to explain to
  each other.
- Render with the two Kokoro voices alternating, stitched into one `Segment` (`format="talk"`).
  Run the draft through the existing `safety_check()` placeholder so the seam is exercised.
**Done when:** a generated two-DJ segment sounds like two distinct people having a real,
in-character exchange that draws on a current event/canon fact without info-dumping — and you
judge it "a conversation, not two narrators."

## B5 — Program format templates
**Goal:** reusable show backbones so generation fills a proven skeleton.
**Do:**
- `src/formats/` with three templates, each a function `(now, context) -> Segment`:
  - `news` — sting → 3 in-world headlines derived from current events → sign-off (single DJ).
  - `talk` — open → banter on an event/fact → music lead-in line → close (two DJs; wraps B4).
  - `music` — short DJ intro → [song slot: a placeholder marker; real song scheduling is Phase C
    playout] → back-announce (single DJ).
**Done when:** each of the three formats produces a coherent, tonally-distinct `Segment` on demand.

## B6 — Light nightly buffer (bridge to Phase C)
**Goal:** generate a small varied buffer in one run — the mind proven at volume — without building
the real 24/7 scheduler yet.
**Do:**
- `make buffer` — generate ~an hour of varied segments (mix of the three formats, both DJs,
  current events) into `segments/`, voiced by Kokoro, each a proper `Segment` with metadata.
- README/code note: the real scheduler, the buffer-depth dial, the Batch API (50% off Claude),
  and the real content-safety gate land in **Phase C** with the VPS / 24-7 work. (With free local
  Kokoro, the cost case for the Batch API is now weak — revisit in C.)
**Done when:** one command produces ~an hour of coherent, varied, in-universe audio locally at
zero API cost.

---

## Explicitly NOT in Phase B (→ Phase C and beyond)
Real 24/7 scheduler + buffer-depth dial; Batch API at scale; the real content-safety gate; the
VPS + YouTube deployment; vector/embedding RAG (seam only for now); near-live; more than two DJs;
generated music. Don't start these — note them for Phase C.

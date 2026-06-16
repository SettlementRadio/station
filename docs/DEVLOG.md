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

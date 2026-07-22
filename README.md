<p align="center"><img src="assets/wordmark-horizontal.svg" alt="Settlement Radio" width="420"></p>

<p align="center">
  <!-- add at MG6: <a href="LINK"><img src="badge" alt="Live"></a> -->
  <img src="https://img.shields.io/badge/code-Apache--2.0-blue" alt="Code: Apache-2.0">
  <img src="https://img.shields.io/badge/world-CC%20BY--SA%204.0-green" alt="World: CC BY-SA 4.0">
  <img src="https://img.shields.io/badge/built%20with-Claude%20Code-d97757" alt="Built with Claude Code">
</p>

<p align="center"><em>Late-night radio from the far future.</em></p>

<p align="center"><em>A love letter to 20th-century science fiction — broadcasting from the future it imagined.</em></p>

Settlement Radio is an always-on, AI-voiced radio station that broadcasts from the settled worlds
of the late 27th century, six hundred years from now. It knows what time it really is, reflects
it in-universe, and keeps you company across the dark with news from the colonies, music for the
small hours, and presenters who carry the same conversation night after night. It's a tribute to
the science-fiction authors who taught a generation to imagine a kinder future.

It's also being built almost entirely by AI agents — and in the open.

## Listen
- 🎧 Live stream: Cooming soon
- 🌍 [settlementradio.com]

## What it is
- A continuous, time-aware broadcast — generated ahead of air, played out 24/7.
- Persistent AI presenters with consistent personalities and a shared, version-controlled world.
- All writing, reasoning, and world-simulation by **Claude**; voice by an external TTS; the whole
  system built with **Claude Code**.

## Built in the open with Claude Code
Settlement Radio is an experiment in handing a creative production to AI agents: Claude Code wrote
the pipeline, the world engine, and the writers'-room that scripts each segment in character. The
build log lives in [`docs/DEVLOG.md`](docs/DEVLOG.md); the design in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## How it works (in brief)
Generation and playout are decoupled in time: a writers'-room of Claude agents drafts segments
ahead of air from a living world-state (canon, cast, an event timeline, and a world clock running
+600 years), those segments are voiced and stored, and a lightweight playout layer streams them
around the clock. Segment length is a parameter, so the same pipeline serves an overnight block or
a near-live drop. Details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Programming the station
The station is a **programmed weekly grid**, not a flat loop — a talk-first week of many short, themed
programs: news/current-affairs flagships, subject *verticals* (politics, economy, conflict, law,
science, travel, the arts…), sport, short music features, and the night shows. Each is a **named
program** with hosts, framing, and a **clock** — a real-radio format sequence with run-lengths
(`music x3`) and pinned slots (`news@:00` / `news@:30`). A stable news rhythm surrounds a **rotating
specialist** (cycling Mon→Fri) so the whole world is heard across a week. Two rules: **`talk` is a
two-DJ conversation**; **`news` is read by the dedicated news desk (Thorn), not the show's host** — it
cuts in on the hour and hands back.

- **One flowing show** — consecutive talk segments in a program play as **one show**, not N mini-shows:
  it opens once (a spoken sign-on), the middle segments come in cold and carry the same thread forward,
  and it signs off once (D12). An interview/dispatch show also brings in guests/played records on its
  own cadence (`guest_chance`).
- **Edit the grid** — the human-edited source of truth is one YAML file,
  [`docs/programming/grid.yaml`](docs/programming/grid.yaml) (model + clock grammar in
  [`docs/programming/README.md`](docs/programming/README.md)). Edit → live (reloaded on change, no
  restart). Full grid *management* (a drag-the-grid web editor) is **Phase E**; in Phase D you edit the file.
- **See it, token-free** — `make programming-demo` prints the weekly daypart map, the clock walking across
  a program boundary (pinned news landing on the hour), run-lengths, and the console + feed;
  `make continuity-demo` prints a show's consecutive talk scripts back-to-back so the single-show flow
  is visible (a few Claude calls, no TTS); `make journal-demo` runs the D13 self-memory loop on paper —
  two slots air and are journaled, and the next day's script calls the journal back (cleans up after
  itself).
- **Operator console** (private, read-only) — `make console` shows on-air/next, buffer runway, the
  last-run heartbeat, and the world story log. Never internet-exposed.
- **Operator panel** (private, write control surface — E1) — `make panel` serves a loopback-only web
  UI at `http://127.0.0.1:8787/`: a live Dashboard, Actions (seed/tick/schedule/prune/… as buttons,
  with a mutation lock + a typed-phrase gate on `reset-world`), a Schedule screen (on-air + upcoming
  queue with per-slot regenerate/skip, paginated aired history with scripts + audio, and playout
  start/stop/restart), a Budgets screen (estimated spend by job/day from the logged token + TTS
  usage, a daily-budget bar + red alert), a World screen (the post-tick digest + arcs in flight +
  today's beat timeline, with tick/micro-tick run buttons), and forms-over-files editors — Grid,
  Catalogs (Tracks/Sponsors/Pronunciation/Voices), Cast, and Dials — each validating through the real
  loader, showing
  a diff, and writing atomically with a `.bak`. It binds `127.0.0.1` ONLY and refuses
  a non-loopback bind without `PANEL_ALLOW_NONLOCAL=true`; on the VPS it's reached via an SSH tunnel
  (`ssh -L 8787:localhost:8787 <vps>`), never a public URL. Deploy with
  `config/settlement-panel.service`. The files stay the source of truth, so the hand-edit workflows in
  `docs/ADMIN_MANUAL.md` remain the fallback.
- **Public now-playing feed** — `make now-playing` writes `segments/nowplaying.json` (refreshed on every
  scheduler top-up): the public-safe subset (on-now/next + program + hosts + AI-disclosure line + the
  playing track's title/artist/album/era) the web player reads. The player UI itself is C8.

## The production layer (sound design + songs — D7)
The station *sounds produced*: curated jingles/idents/stings air where the grid calls for them, beds
duck under speech, and real songs play in the `music` format — all Layer 4
([`src/production/`](src/production/)).

- **Curated media lives under `assets/`** (gitignored, backed up, **never** touched by the disk GC —
  it only ever scans `segments/`): `assets/idents/` (station IDs), `assets/themes/` (program themes +
  loopable `_bed` variants), `assets/stings/` (short punctuation), `assets/music/` (songs), plus the
  fixed `assets/bed.mp3` playout fallback. The exact filenames are the contract in
  [`docs/JINGLE_PROMPTS.md`](docs/JINGLE_PROMPTS.md) §4; the clip→placement mapping (which theme opens
  which program, which sting precedes the news) is the registry in
  [`src/production/media.py`](src/production/media.py). A missing clip degrades to "skip that
  placement" — never a crash.
- **On air, placed by the grid** — each program boundary opens with its theme (handover shows get the
  B6 "passing the light" sting first), the C8 sting fires before every news bulletin, and the A1 sung
  station ident airs every `PRODUCTION_IDENT_EVERY_N` content segments. Beds are doubly opt-in
  (`PRODUCTION_BEDDED_PROGRAMS` × `PRODUCTION_BEDDED_FORMATS`; default: the night show's talk only) and
  are baked at render time at `PRODUCTION_BED_GAIN_DB` below the untouched speech
  ([`src/production/mix.py`](src/production/mix.py) — a mix failure degrades to clean, dry speech).
- **Songs are cultural artifacts, not files** — the catalogue is the human-authored music-lore
  manifest [`config/tracks.yaml`](config/tracks.yaml) (title, artist, album, era, story, mood, licence),
  seeded into the `tracks` table by `make seed-tracks`. **Registering a track:** drop the mp3 into
  `assets/music/` under the exact `audio_path` filename, write/keep its manifest row, run
  `make seed-tracks` (durations are probed from the files; a row whose file is absent stays
  referenceable lore — just not playable yet). The catalogue survives `seed-canon` *and*
  `reset-world` — it's curated station catalog, not world state.
- **`music` is back in the rotation** — when a music slot comes up, a deterministic, rule-based
  **selector** ([`src/production/selector.py`](src/production/selector.py) — no LLM) picks the track by
  daypart mood, the live world's tone, freshness (don't repeat a song/artist), era spread, and
  featured/pinned artists (`MUSIC_SELECT_*` dials). The DJ's intro/back-announce is written around that
  track's lore — the segment airs as one mp3: intro → music bumper → **the track** → back-announce.
  No playable track ⇒ the slot falls back to a spoken evergreen — a silent gap is impossible.

## Commercials & sponsorship (texture, not interruption — D8)
The station airs **in-world commercials** — but never a rotating ad reel. Every spot is **written
fresh and voiced fresh for that airing** (a fictional +600y product or a station promo; a break is
never the same spot twice — infinite in-character copy is the AI advantage). Spots run the same
safety gate + evergreen fallback as every producer, and the IP boundary holds: fictional products
only, never a real brand, franchise, or person.

- **The formats** — `commercial` (an invented in-world product/service spot) and `promo` (a station
  self-promo that truthfully names the current grid show) share one builder
  ([`src/formats/commercial.py`](src/formats/commercial.py)); `FORMAT_COMMERCIAL_*` dials set the
  speaker, length, and the **production level** (1 = voiced read, default; 2 = read over a ducked
  D7 bed; 3 = multi-voice testimonial, arrives with D9/D10; 4 = a curated ~2s brand-sting bookend —
  the only prerecorded ad audio; unbuilt levels degrade to 1, and the effective level lands in the
  segment meta).
- **The grid owns the ad load** — a program declares `break_every: N` in
  [`docs/programming/grid.yaml`](docs/programming/grid.yaml) (a sparse break after every N content
  segments; absent = no breaks — the handover shows and the fallback stay clean). The scheduler
  brackets each break with the d18 `break_in`/`break_out` stings; `COMMERCIAL_BREAK_*` dials cap
  spots per break (default **one**) and rotate in a station promo every Nth spot.
- **Real sponsors say "Powered by" — never "Sponsored by"** ([`docs/MARKETING.md`](docs/MARKETING.md),
  binding; the lead-in is templated so it can't drift, and any "sponsored by" in a hand-entered
  blurb is corrected and logged). Supporters live in the hand-entered
  [`config/sponsors.yaml`](config/sponsors.yaml) → `make seed-sponsors` → the `sponsors` table
  (catalog like tracks: survives `seed-canon` *and* `reset-world`). A read airs inside every
  `SPONSOR_READ_EVERY_N_BREAKS`-th break, only within its real-wall-clock run window; a
  sponsor-supplied clip under `assets/` plays instead when provided. **The table ships empty:
  populating real sponsors is gated on CM (donations live), not on D8.**
- **See/hear it** — `make commercials-demo`: generates one commercial + one promo (live calls),
  prints the grid's per-program cadence + a simulated sting-bracketed break, and runs a demo
  sponsor row through the run window + wording guard (then removes it).

## Run it locally
The station backend (the Python pipeline + Liquidsoap playout) runs on macOS (Apple Silicon)
with Homebrew. Generation and playout are decoupled, so you can generate a segment, then serve it.
Two docs, split by intent: for **operating** the running station (seed modes & the world, the bible,
the grid, tracks/sponsors, voice, the console, recovery, the acceptance gate) see the operator
manual, [`docs/ADMIN_MANUAL.md`](docs/ADMIN_MANUAL.md); for **developing** the repo (a one-page
cheat-sheet of every `make` target, the test commands, env knobs, and troubleshooting) see
[`docs/HOWTO.md`](docs/HOWTO.md).

**1. System packages.** Note: **Python 3.12, not 3.13** — the Kokoro TTS package requires
`>=3.10,<3.13`.
```bash
brew install python@3.12 icecast ffmpeg coreutils curl lame mad espeak-ng
```
Liquidsoap is no longer in Homebrew; build it from source via opam, *with* the MP3 plugins
(`lame` to encode, `mad` to decode — without them `%mp3` is "unsupported format"):
```bash
brew install opam && opam init -y
opam install -y liquidsoap lame mad
# Apple Silicon: point the C toolchain at Homebrew if the opam build can't find headers:
#   export CPATH=/opt/homebrew/include LIBRARY_PATH=/opt/homebrew/lib
```

**2. Python environment** (on 3.12):
```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**3. Voice — Kokoro (local TTS).** Kokoro is the default `TTS_PROVIDER`: a self-hosted,
open-weight neural voice that is free, unlimited, and offline after a one-time model download.
The `espeak-ng` system package (installed in step 1) is its grapheme-to-phoneme fallback. On the
**first** `synthesize` call Kokoro downloads its model weights from HuggingFace (cached under
`~/.cache/huggingface`) and a small spaCy English model for phonemization — so the first render
is slow (~tens of seconds) and needs network; every render after is fast and offline. No API key.
Alternatives, all behind the same seam (set `TTS_PROVIDER` in `.env`): `elevenlabs` (flagship
cloud voice; needs `ELEVENLABS_API_KEY` + credits) and `say` (macOS built-in; offline fallback if
Kokoro won't install).

**Emotion (D9.0).** The writers' room can stamp a turn with a logical emotion (`warm | wry |
somber | bright | urgent` — the orchestrator emits a sparse `Vell [somber]:` tag; un-tagged turns
take the hour's mood, e.g. warm nights / bright mornings, or `TTS_EMOTION_DEFAULT`). Emotion flows
end-to-end through `tts.synthesize(..., emotion=...)`, but it is **audible only on the flagship
path** — on ElevenLabs it maps to the voice's expressiveness controls; **Kokoro and `say` have no
emotion knob** and ignore it cleanly. Whether launch runs Kokoro-at-scale or the flagship engine is
the open **C6** decision (`docs/PHASE_C_TASKS.md`) — that choice, not this code, decides whether
emotion is heard on air.

**Pronunciation (D9.1).** The world's invented names (Zhe, the Lumen Festival) are spoken right and
consistently on every engine via the **pronunciation lexicon** — `config/pronunciation.yaml`, the
human-edited source of truth. Fix a mispronunciation by editing that file (no code change or restart;
the loader re-reads on change): each entry maps a spelled name to a phonetic `respell` (used on
ElevenLabs/`say`) and an optional `phonemes` string (used on Kokoro via its exact-phoneme markup —
see the file's header for the workflow and alphabet). Unknown names pass through to the engine
default unharmed; `TTS_LEXICON_ENABLED=false` switches the whole thing off.

**The DJ roster (D9.2).** The cast is **bible-authored**: the 10 DJs live as persona cards in
`docs/canon/90-cast.md`, each with a distinct voice on every engine via the **voice registry**
(`config/voices.yaml` — logical voice → vendor preset, per engine; the old hardcoded dicts in
`tts.py` are gone). **Add a DJ:** author a card in the bible (the `Logical voice` line is required)
+ add that voice's entry to `config/voices.yaml`, then `make seed-canon` — which **fails loud** if
the bible and the registry disagree, so a typo'd voice is caught at seed time, not on air. **Edit /
remove** a DJ the same way (edit/delete the card, re-seed); a grid program still naming a removed
cast id fails loud at generation and the slot falls back — never dead air. **Put a DJ on air** by
scheduling them in `docs/programming/grid.yaml` (hosts are cast ids; the grid is read live). The
Bridge (weekend mornings, joss + mira) is the first show carrying the new cast. The runtime
management UI is Phase E — this file-based flow is the current model. Note the 8 new DJs'
ElevenLabs ids are premade-roster picks not yet heard (the key lacks `voices_read`) — confirm at
the C6 funded listen; Kokoro presets are verified locally.

**Guest voices (D9.3).** A talk segment can carry one **non-host speaker**, the way real radio plays
a clip or runs an interview: a **figure soundbite** (a person from the world's stories, speaking
their attributable quote — the D9×D10 bridge) or a one-off **invited guest**. Sparse by design
(`CONVO_GUEST_CHANCE`, ~1 in 5 talk slots, drawn deterministically per slot): the hosts introduce
and close the guest — a draft that lets the guest open or close is re-rolled by a structural gate.
Guest voices come from the registry's `guest_*` pool (`config/voices.yaml`), distinct from every
host; a figure with its own `voice_id` keeps it, and the same figure keeps the same pool voice
across segments. `CONVO_GUEST_ENABLED=false` returns to host-only. Guests are part of the station's
AI-voiced fiction, covered by the standing on-air disclosure.

**DJ memory (D9.4).** On air, the hosts remember what the world lived through: each talk segment
carries a small "what {DJ} remembers" block assembled from the story log — recent **past**
happenings, clock-framed ("yesterday", "last week") and labelled resolved / still unfolding, so a
DJ references them as lived history rather than re-announcing them as news. Persona-weighted (a
story whose tags match a host's card sticks with that host), bounded by two dials
(`CONVO_MEMORY_WINDOW_DAYS` look-back, `CONVO_MEMORY_PER_HOST` stories each), clipped to
one-sentence handles, and kept in the **per-call** prompt so the cached bible is untouched. The
same block is shown to the continuity editor, so a host misremembering a logged story is flagged
and re-rolled like any continuity error. Distinct from the news desk's coverage memory (D4) and
the anti-repetition freshness memory (D5) — this is in-character recall.
`CONVO_MEMORY_ENABLED=false` switches it off.

**Self & interpersonal memory — the journal (D13).** The hosts also remember *themselves and each
other*: after a scheduled talk segment airs, one cheap `haiku` extraction distills it into durable
`host_journal` rows — opinions voiced, personal details revealed, jokes with callback potential,
and what two hosts last talked about. Future segments get a "what you've said on air before" block
(per host, persona-weighted, semantically recalled against the slot's beat via the `journal`
embeddings corpus) plus a per-pair relationship line for the showrunner — so a host can say "as I
said the other night…" and be *right*. The continuity editor sees the same block, making a host who
reverses a journaled stance a flagged continuity error — which is what makes emergent self-canon
safe: a detail a host invents about themselves becomes something they stay true to. **The
hand-authored cast card always wins over the journal.** Capture is post-gate and best-effort (a
segment never fails because of its journal); personal details are capped per host
(`CONVO_JOURNAL_MAX_DETAILS_PER_HOST`); only aired segments journal. See the loop on paper with
`make journal-demo`. `CONVO_JOURNAL_ENABLED=false` is the clean rollback.

**4. World-state database (Postgres).** From Phase B the world (canon, cast, events) lives in a
local PostgreSQL database, seeded from the **canon bible**. Install and start it with Homebrew, then
create the database:
```bash
brew install postgresql@14
brew services start postgresql@14      # run it now and at login
createdb settlement_radio              # the default DB in DATABASE_URL
```
The connection string is `DATABASE_URL` (default `postgresql://localhost/settlement_radio`); set it
in `.env` only if your Postgres differs.

**pgvector (Phase D / D2 — semantic retrieval).** The world store uses the
[pgvector](https://github.com/pgvector/pgvector) extension for meaning-based canon recall;
`init_schema` runs `CREATE EXTENSION vector` and fails loudly if it isn't installed. The Homebrew
bottle currently covers postgresql@17/@18 (`brew install pgvector`); for **postgresql@14** (the
version above) build it from source against pg14's `pg_config`:
```bash
# postgresql@14: bottle unavailable — compile + install the extension for pg14
git clone --branch v0.8.3 --depth 1 https://github.com/pgvector/pgvector.git
cd pgvector && PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config make && \
  PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config make install
```
No DB restart needed — `make seed-canon` (next) creates the extension and the `embeddings` table.

The bible is the [`docs/canon/`](docs/canon/) folder of cornerstone files (`00-station.md`,
`90-cast.md`, … — see [`docs/canon/README.md`](docs/canon/README.md) for the authoring contract;
`CANON_DIR` overrides the location). Seeding reads the whole folder; it auto-selects the folder when
it holds content and otherwise falls back to the legacy single `docs/CANON.md`. Two commands, split so
a routine bible edit never destroys the living, tick-generated world (Phase D / D1):
```bash
make seed-canon  # SAFE everyday reload: refresh canon/cast/seed-events; keep source=tick events
make reset-world # DESTRUCTIVE full world+canon wipe + rebuild (warns + confirms)
```
Both are idempotent; re-run `make seed-canon` any time you edit a file under `docs/canon/`. (`make
seed` is a back-compat alias for the safe path.) Seeding also **embeds** every canon fact into the
`embeddings` table (`corpus='canon'`) so the writers' room can recall canon by meaning (D2); a
refresh re-embeds the canon corpus cleanly and leaves tick-generated vectors untouched.
The station knows what time it is. The world clock ([`src/world/clock.py`](src/world/clock.py)) maps
real time to the in-world `year + 600`, and event progression ([`src/world/events.py`](src/world/events.py))
turns a stored event date into a live status and the phrase a DJ would say. See it flip:
```bash
make demo        # renders the Lumen Festival at two times: "in five days" -> "yesterday"
```
The writers' room is fed the right slice of that world by
[`src/world/context.py`](src/world/context.py): `assemble(now)` returns a **cached stable core**
(the series bible + the speaking DJ's card → sent as a prompt-cache breakpoint) plus the **dynamic
now** (events near the current time, with live status and relative phrasing, and topic-relevant
canon — events by structured date query, canon by a hybrid of semantic recall + tag match). Inspect
exactly what the writer will send:
```bash
make context     # prints the cached core and the dynamic (events/canon) slice for now
```
> **Semantic retrieval is live (Phase D / D2).** Structured queries (by date / status / tag) still
> serve the fast path, but the canon is now also recalled by **meaning** via pgvector. The vector SQL
> lives only in [`src/world/store.py`](src/world/store.py) — `CREATE EXTENSION vector` plus ONE
> polymorphic `embeddings(corpus, entity_id, …)` table (multi-corpus so D3 events and D10 figures reuse
> it) with an HNSW cosine index — and the embedding model lives only behind
> [`src/providers/embeddings.py`](src/providers/embeddings.py). The model is a **local** open
> sentence-transformer (`settings.embeddings_*`; 384-d, free, no key — D2.0 decision); `embeddings_dim`
> is the `vector(N)` width, so a model change means a re-embed + a column migration.

The world moves on its own (Phase D / D3). A nightly **world tick**
([`src/world/world_tick.py`](src/world/world_tick.py)) invents plausible new happenings consistent
with the bible and models each as a **story with an arc** — `rumoured → upcoming → happening →
developing → past` — whose individual developments are dated `events` rows (its *beats*), so the world
clock frames them future/now/past for free. Each run also **advances** a bounded set of running stories
(a new beat, sometimes a stage change) and steers old ones to resolution, so the world has real
day-to-day continuity. Every proposal passes the **safety + a world-continuity gate** (against canon
*and* the story's own prior beats) before it's written — flagged content is regenerated once, then
dropped, never written — and the run stays varied via domain balancing, similarity de-duplication, and
a new-vs-advance pacing cap. The story log lives in [`src/world/store.py`](src/world/store.py)
(`stories` + beat-linked `events`, `source='tick'`) and **persists forever** — a canon refresh
(`make seed-canon`) never wipes it; only `make reset-world` does.
Between nightly ticks a light **intra-day micro-tick** (R4.1, `run_micro_tick`) keeps the day alive:
fired every 2–4h, it may nudge ONE of *today's* live stories a small beat — a detail, a reaction, a
complication — or do nothing (a quiet run is normal). It invents no new story and moves no arc (the
nightly tick owns those); it only adds intra-day texture, rotating across the day's live threads so
none runs away. It runs **haiku-tier on the direct path** (latency over the Batch discount — one small
call), through the *same* safety + continuity gates.
```bash
make world-tick                       # run one tick: invent + advance world stories (Claude Batch)
LLM_BATCH_ENABLED=false make world-tick  # quick local run, synchronous (no async batch wait)
make micro-tick                       # one intra-day micro-tick: nudge a live story (haiku; seconds)
```
Cost levers are mandatory here (this is the high-volume job): the gate calls go through the **Batch API**
(50% off, behind [`llm.generate_batch`](src/providers/llm.py) — the only place the vendor batch SDK is
imported) and the stable bible is **prompt-cached**. The tick writes **world state**; the C2 scheduler
reads it to make audio — they're **separate jobs** on the box's timer (the C5 cron/systemd runs the tick
nightly; don't fold it into `make schedule`). A run is transactional, so a failure rolls back and exits
non-zero (loud) without corrupting the store. A fresh DB has no running stories yet — run a couple of
ticks after seeding to give the world a living "now".

The news desk reports that living world (Phase D / D4). Instead of N flat headlines,
the desk ([`src/formats/news.py`](src/formats/news.py)) **reads the story log** and broadcasts it like
a real station. Each hour it **selects** ([`news_select.py`](src/formats/news_select.py)) a bounded,
ranked mix of running stories — tagged `breaking`/`trailed`/`ongoing` by where their beats sit on the
clock and `new`/`repeat`/`evolve` from a per-story **coverage memory** (`news_coverage`, D4.0) — grounds
them against canon by semantic recall, and frames each by its arc + relative phrase ("tonight" /
"tomorrow" / "yesterday"). A story that gained a beat since last coverage is reported as an **update**
(the delta), a repeated one as a light "still developing" touch; prior coverage is fed back so naming
stays consistent, and a **continuity editor** pass catches a renamed or contradicted story (re-roll with
the note, then evergreen — the C0 discipline). Coverage is recorded only on a clean render.
```bash
make news-demo          # watch one story go breaking → repeated → evolved → past across a simulated day
make format FMT=news     # one voiced bulletin on demand (Claude + TTS)
```
`make news-demo` is deterministic and token-free: it seeds a tiny story log in a rolled-back transaction
(never touches your world) and prints the desk's selection + framing for four bulletins across a day.

The world's people speak (Phase D / D10). A story is no longer just a fact: the tick
peoples it with invented **figures** (the relay-keeper, the engineer, the moon-president's son) and
their attributable, dated **quotes** — `figures` + `quotes` tables behind the store seam
([`src/world/store.py`](src/world/store.py)), generated **inside the same gated, batched tick call** as
the story (so a flagged or off-canon figure/quote regenerates/drops with it; a continuing story **reuses**
its figures by name rather than spawning a new person each beat). The news desk then **attributes** them —
"Mira Voss, the relay-keeper, said yesterday: …" — with correct temporal framing
([`events.phrase_for_datetime`](src/world/events.py)), and the writers' room surfaces a **"what people are
saying"** slice (recalled by meaning via D2 when a topic is in play) so the DJs can react to an opinion in
character. **Hard rule: invented in-world people only — never a real or trademarked person** (the gate
checks it). Voicing a quote as a distinct **soundbite** is the D10×D9 bridge (lands with D9's guest voice);
until then attribution is textual.
```bash
make figures-demo   # seed one peopled story; show the news attribution + the DJ "what people are saying"
make world-tick      # the GENERATED path: a tick invents figures + quotes for its stories
```
`make figures-demo` is deterministic and token-free (seeds + rolls back). Dials live under `WORLD_TICK_FIGURES_*`
(volume + reuse) and `NEWS_QUOTES_PER_STORY` / `CONTEXT_QUOTES_LIMIT` (how many reach each surface).

The station never loops itself (Phase D / D5). Round-the-clock output would drift into the same
openings and the same beat every hour; a small **airplay memory** stops it. At the scheduler chokepoint every
placed content segment lands one row of *features only* — a topic/beat handle, an **opening fingerprint** (first
few spoken words, normalised so near-identical openings collide), and a few key phrases — in an `airplay_history`
table behind the store seam ([`src/world/store.py`](src/world/store.py)), extracted cheaply (no extra LLM call)
in [`src/freshness.py`](src/freshness.py). Before it writes, the writers' room reads that recent window back: the
**showrunner** is steered off recently-used topics, and the **producers** (talk + news) off recent openings —
"prefer a different angle / open differently". It is DISTINCT from D4's per-story coverage memory: D4 drives
*which* stories recur and *how they evolve* (intended); D5 only keeps the *wording* from looping on top of that
(the news prompt says so explicitly). The memory **outlives the audio** it describes (it is not GC'd with the
renders — it is bounded by its own much-wider sweep) and **survives a `seed-canon` refresh**, cleared only by
`reset-world`.
```bash
make freshness-demo   # four talk segments at an advancing clock; watch the openings/beats stay varied
```
`make freshness-demo` spends a few Claude calls per segment (no TTS, no gates) and rolls its writes back. Dials live
under `FRESHNESS_*`: `FRESHNESS_WINDOW_HOURS` (the look-back — keep it above `BUFFER_DEPTH_HOURS`),
`FRESHNESS_MODE` (`prefer` soft vs `avoid` hard), `FRESHNESS_RECENT_LIMIT`, and `FRESHNESS_ENABLED`.

Two DJs hold a conversation, not two monologues. The conversation orchestrator
([`src/writers/conversation.py`](src/writers/conversation.py)) runs a light writers' room over the
assembled context: a **showrunner** picks one beat from the current events, an **orchestrator**
writes the whole two-voice exchange in a single call from both DJ cards (Vell, night → Wren,
first light), and a **continuity** pass checks it against canon on `sonnet`, escalating to `opus`
only if it flags trouble. Each turn is voiced in that DJ's own Kokoro voice and the turns are
stitched into one talk segment. The facts are the hosts' *shared knowledge to reference naturally*
— the prompt forbids reciting or explaining canon to each other.
```bash
make conversation   # showrunner → dialogue → continuity → two-voice segment (Claude + TTS)
```

Generation fills a proven skeleton, not a blank page. [`src/formats/`](src/formats/) holds three
**program-format templates**, each a function `(now, context) -> Segment` behind a small registry
([`make_format_segment`](src/formats/__init__.py)) that assembles exactly the cast each one needs:
- **news** — a single-DJ desk that reads the **story log** (D4): selects a tagged mix of running
  stories, frames each by arc + beat date, recurs/evolves them across the day, and stays consistent via
  a continuity gate. (Reportage, so stating the facts plainly is correct — the opposite of the talk rule.)
- **talk** — the two-DJ conversation (open → banter → music lead-in → close); it *wraps* B4,
  reusing `conversation.compose_segment` with a structural directive.
- **music** — a single-DJ wrap: intro → a `[SONG]` slot marker (real song scheduling is Phase C
  playout) → back-announce. The marker is kept in the script and never spoken.
```bash
make format FMT=news    # one format segment on demand (FMT=news|talk|music; Claude + TTS)
make format FMT=music TOPIC="the festival"   # TOPIC steers canon retrieval
```

A **light nightly buffer** ([`src/buffer.py`](src/buffer.py)) generates the whole mind at volume in
one run — the original B6 bridge. It cycles the formats until their length targets sum to ~an hour of
audio, advancing each segment's `air_time` so the block plays back-to-back. Every segment lands as
`segments/<id>.mp3` **plus** a `segments/<id>.json` metadata sidecar, and the run is summarized in a
`segments/buffer-<timestamp>.json` manifest.
```bash
make buffer                 # ~an hour of varied segments into segments/ (Claude + Kokoro; slow)
make buffer SECONDS=600     # a shorter run for a quick check (target length in seconds)
```

The **rolling scheduler** ([`src/scheduler.py`](src/scheduler.py), C2) is the real 24/7 replacement
for that one-shot buffer. It keeps a rolling buffer of upcoming audio at `BUFFER_DEPTH_HOURS` of
**measured** duration (every render is probed with `ffprobe` and the real length recorded on the
`Segment` — `length_target_sec` is only the writer's word-count goal and runs short of it), decides
the airing order, retries-then-skips a failed slot without leaving dead air, and writes an **ordered
playlist** (`segments/playlist.txt`) that Liquidsoap re-reads — so the scheduler's decisions actually
drive what airs. Run it periodically (cron/systemd lands in C5) to keep the buffer topped up:
```bash
make schedule                 # one top-up + (re)write the playout playlist (Claude + Kokoro; slow)
make schedule INTERVAL=300    # local: keep topping up every 5 minutes
```
`BUFFER_DEPTH_HOURS` is the lead-time dial (deeper = more resilient; ~0 + streaming TTS enables
near-live later). For Phase C the `music` format is dropped from `BUFFER_ROTATION` (its `[SONG]` slot
has nothing to fill it until Phase D), so only `talk`/`news` air — no silent gaps.

**Disk retention** ([`src/scheduler.py`](src/scheduler.py) `prune()`, C2.5). At ~1 MB/min of
generated audio, an unbounded `segments/` would fill the VPS disk in weeks. After every top-up the
scheduler garbage-collects each `<id>.mp3` (+ its `<id>.json` sidecar) that has **aired** (is no
longer referenced by the live playlist) and whose air end is more than `SEGMENT_RETENTION_HOURS`
(default 6) in the past — a grace window so a just-aired clip Liquidsoap may still be reading isn't
yanked. The **shared disclosure ident** clip (`ident-disclosure-*.mp3`, reused across every ident
slot) and everything under **`assets/`** (curated, non-regenerable media) are never collected; the GC
only ever touches `segments/`. An optional `SEGMENT_RETENTION_MAX_GB` backstop evicts the oldest
aired renders if the directory still exceeds the cap. Each sweep logs the files + bytes reclaimed.
```bash
make prune                    # standalone GC (no Claude/TTS) — verify retention on disk
```

**AI disclosure on air** ([`src/disclosure.py`](src/disclosure.py), C3). The station must say it's
AI-generated (CLAUDE.md; EU AI Act Art. 50). As it places content, the scheduler weaves a short
**spoken disclosure ident** into the playlist every `DISCLOSURE_EVERY_N` content segments (default
4) — so the live stream audibly discloses on a regular cadence. The ident is static, canon-safe copy
rendered once and reused (no Claude call), so it's cheap; preview or pre-render it with `make ident`.
The same written line (`DISCLOSURE_LINE`) is shown on the web player ([`web/src/lib/disclosure.ts`](web/src/lib/disclosure.ts))
and belongs in the YouTube description (wired in C7).

**Never-dead air + health checks** ([`src/fallback.py`](src/fallback.py) + [`src/health.py`](src/health.py), C4).
A 24/7 stream must survive any single failure. Playout ([`config/radio.liq`](config/radio.liq)) airs a
**fallback chain** — `scheduled playlist → evergreen pool → music bed → disclosure ident → tone` —
so if the generator is down and the rolling buffer drains, the stream degrades to a clean pre-rendered
spoken segment, never silence. The lower tiers are pre-rendered **while the system is healthy** (so they
survive a Claude/Kokoro outage): `make fallback` (also run at the top of every `make schedule`) renders
the **evergreen pool** to GC-exempt clips and writes the playlist Liquidsoap watches. Separately,
`make health` (cron/systemd in C5) checks the **buffer runway**, the **last scheduler run** (the scheduler
writes a `last_topup_at` heartbeat), and **stream liveness**, and on any issue logs an alert plus, if
configured, POSTs a webhook / pings an uptime URL (a healthchecks.io-style dead-man's switch). It exits
non-zero when unhealthy. Drop an optional `assets/bed.mp3` to give the music-bed tier real audio.

**5. Secrets.** Copy `.env.example` to `.env`. For a fully local, zero-cost run you only need
`ANTHROPIC_API_KEY` (the script) and the default `TTS_PROVIDER=kokoro` (the voice);
`ELEVENLABS_API_KEY` is optional.

**6. Program + play.** Playout now airs the **scheduler's playlist**, so fill it first, then serve:
```bash
make schedule   # top up the rolling buffer + write segments/playlist.txt (Claude + Kokoro)
make serve      # start Icecast + Liquidsoap; airs the playlist in scheduled order
make stop       # stop Icecast + Liquidsoap
```
`make serve` prints the local player URL (`http://127.0.0.1:8000/`); Liquidsoap re-reads the
playlist as later `make schedule` runs top it up, so the stream keeps going with no restart. If the
playlist is empty or absent, the never-dead fallback chain (evergreen pool → music bed → ident → tone)
keeps the mount live. `make generate` / `make conversation` still write individual ad-hoc segments for inspection;
the live stream airs whatever the scheduler has queued. See the `Makefile` for `serve` / `status`.

## Developing the station backend
The backend follows the engineering standards in [`CLAUDE.md`](CLAUDE.md). For contributors:

- **Config over hardcoding.** All tunable values live in one typed module,
  [`src/config.py`](src/config.py) (`pydantic-settings`). Code reads `settings.X`; nothing reads a
  raw literal or `os.getenv` directly. Every field can be overridden by an env var of the same name
  (e.g. `LOG_LEVEL=debug`, `TTS_PROVIDER=elevenlabs`) — see `.env.example`.
- **Structured logging, never `print()`.** [`src/logging_setup.py`](src/logging_setup.py)
  configures `structlog` once (JSON by default for 24/7 runs; `LOG_JSON=false` for pretty console).
  Get a logger with `from .logging_setup import get_logger`.
- **Resilient external calls.** Claude and TTS calls go through `call_with_retry`
  ([`src/retry.py`](src/retry.py)) — a bounded retry that logs loudly and re-raises on exhaustion,
  rather than silently producing nothing.
- **One place for SQL.** All world-state reads/writes go through
  [`src/world/store.py`](src/world/store.py) — the same seam discipline as `providers/`. Nothing
  else imports `psycopg` or writes SQL. The [`docs/canon/`](docs/canon/) bible folder is the
  human-editable source; the parser
  ([`src/world/canon_source.py`](src/world/canon_source.py)) and `make seed-canon` project it into the DB,
  and the writer reads its world back out through [`src/world/context.py`](src/world/context.py),
  never the raw file.
- **Lint + format.** [`ruff`](https://docs.astral.sh/ruff/) is configured in `pyproject.toml`:
  ```bash
  .venv/bin/ruff check src     # lint
  .venv/bin/ruff format src    # format
  ```
- **Pre-commit hooks.** Fast checks run on every commit: ruff lint+format, a `gitleaks` secret
  scan, a config-drift guardrail (`scripts/check_no_direct_env.sh` — fails if any code under `src/`
  reads the environment directly instead of via `settings`), and whitespace/newline/large-file/
  JSON-YAML-TOML basics. Install them once after creating the venv:
  ```bash
  .venv/bin/pre-commit install
  .venv/bin/pre-commit run --all-files   # optional: run across the whole repo
  ```
  The test suite is deliberately **not** in pre-commit (it would get bypassed).

## A note on what you're hearing
Settlement Radio is a **work of fiction, written and voiced by AI**. The presenters are not real people;
the news from the future is invented. AI generation is disclosed on the stream and the player.

## License
Code is Apache-2.0; the world (canon and generated lore) is original and licensed CC BY-SA 4.0 — a
tribute to the genre, not derived from any franchise or author's work.
- **Code:** Apache-2.0 — see [`LICENSE-CODE`](LICENSE-CODE).
- **Creative world** (lore, scripts, canon): Creative Commons Attribution-ShareAlike 4.0 — see
  [`LICENSE-CONTENT`](LICENSE-CONTENT). Build in this universe; share alike; credit Settlement Radio.

## Support & follow
☕ [Ko-fi] · ✦ [GitHub Sponsors] · 🛰️ [X] · ✉️ [newsletter]

<p align="center"><sub>For the authors who imagined us here.</sub></p>

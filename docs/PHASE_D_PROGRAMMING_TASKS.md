# PHASE_D_PROGRAMMING_TASKS.md — D6: Programming Backbone + Status Console

> Sub-pack **D6** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the scheduler `scheduler.top_up`
> (which today cycles a **flat** `settings.buffer_rotation` — `name = rotation[rot_i % len]` — and
> calls `make_format_segment(name, air_cursor)`), the clock-driven framing `world/framing.py`
> (`show_frame(now, *, night_host, day_host) -> ShowFrame`, two hardcoded hosts, dawn/dusk handover
> as module constants), the health/status reads `health._runway_seconds` + `health.run_checks` +
> `_load_state` over `schedule.json`, and the web app under `web/` (`web/src/lib/disclosure.ts`).
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D6 brief); `docs/ROADMAP.md` (Phase D "programming +
> admin backbone" bullet); `src/world/framing.py` (the only daypart logic today — the seam to grow);
> `src/scheduler.py` (the flat-rotation selection + the `schedule.json` contract — see
> PHASE_C_ORIENTATION §5); `src/health.py` (the console's data feed); `web/` (the player route is
> **C8**, server track — D6 produces the *data* it shows).
>
> **Depends on:** only the **C2 scheduler** (built) — largely **independent of D1–D5**, so it can run
> in parallel with the living-world spine. **Needed before D7/D8** (sound design + commercial breaks
> key off dayparts). The story-log panel of the console (D6.4) is richer once **D3** exists; without
> it, the console shows scheduler + health only. Programming with a larger cast lands fully with **D9**;
> D6 builds the grid so it *can* reference more hosts, today referencing the two.

**What D6 delivers (ROADMAP, verbatim intent).** Named **programs**, **dayparts**, and a **weekly
routine** the scheduler reads (which show, which DJs, when); a **read-only status console** (what's
airing, buffer depth, last night's run, the story log); and **now-playing / program info** surfaced to
the web player. *(The write/management surface — edit the grid, allocate + CRUD DJs — is Phase E.
D6 stays read-only.)*

**The shift from today.** The scheduler currently airs a flat `["talk","news"]` cycle regardless of
hour, and `framing.py` frames every talk segment off a hardcoded night/dawn/dusk handover between two
hosts. D6 turns "a folder of clips on a flat rotation" into "a programmed station": a weekly grid maps
each in-world hour/day to a **named program** with its own format mix, hosts, and framing; the
scheduler consults the grid at the air-cursor instead of `% len(rotation)`; `framing.py` is generalised
so the program drives who's on air and the on-air situation. (Handovers become daypart boundaries.)

**Definition of done for D6:** a weekly programming grid exists; the scheduler picks each slot's format
+ hosts + framing from the grid at the slot's in-world datetime (not a flat rotation); generating
across a simulated week yields hour-appropriate, named programs; a read-only console reports what's
airing / buffer depth / last run / (if D3) the story log; a now-playing/program-info feed is available
for the web player; `ruff` + `pytest` green; README/DEVLOG updated.

---

## D6.0 — Design the programming model (programs · dayparts · weekly grid) — decide, write it down
**Goal:** a data model for the grid that generalises `framing.py` and replaces the flat rotation, and a
decision on where it lives.
**Do:**
- Define the entities:
  - **Program** — a named show (e.g. "The Long Night", "First Light", "Daywatch"): its **clock** (see
    below — how its formats are sequenced), its **host ids** (cast ids; today `vell`/`wren`), and a
    **framing hint** (how the room should frame it — handover, solo, etc.).
  - **Clock** — the load-bearing piece, borrowed from real-radio "hour clocks": **how a program
    sequences its `formats.FORMATS`** (`talk`/`news`/later `music`/`commercial`). A weighted *ratio*
    alone isn't enough — it can't tell "a 3-song sweep, then a break, then talk" from "one song between
    every chat." So support an **explicit sequence with run-lengths**, e.g. a repeating template like
    `[talk, music×3, sting, talk, news@:00]` (run of 3 songs, a break, talk, news pinned to the top of
    the hour). This is exactly what lets the grid express your two models — a **dedicated music block**
    (a program whose clock is `music×N`) vs **music in between** (a clock alternating `talk, music,
    talk`). Keep it data (a per-program list/template), with a simple weighted-rotation fallback when a
    program doesn't define a full clock.
  - **Daypart / grid slot** — a (weekday, time-range) → Program mapping that tiles the week with no
    gaps. The in-world wall clock = the real wall clock (clock shifts the year only), so slots are
    plain weekday + hour ranges.
- **How the human authors/manages the grid (Phase D) — a hand-edited STRUCTURED file, NOT `.md`.** The
  bible is markdown because it's prose; the grid is *structured data* (times, sequences, host
  assignments), so use **YAML/TOML** (e.g. `docs/programming/grid.yaml`), hand-edited over git/SSH. The
  workflow mirrors the bible loop — **edit the file → reload/re-seed → live** — just in a structured
  format. Shape:
  ```yaml
  programs:
    long_night:        # a named show
      hosts: [vell]
      framing: solo
      clock: [talk, music, music, music, sting, talk, news@:00]   # the per-program sequence (D6.0 clock)
  grid:                # the weekly tiling (weekday range → time range → program)
    mon-fri:
      "22:00-06:00": long_night
      "06:00-07:00": first_light
  ```
- Decide **where the grid lives** — both paths keep that YAML as the human-edited source of truth; the
  only difference is whether a DB copy exists:
  - **Config-file path** (simplest now): the scheduler reads the YAML directly (a reload picks up edits).
    No DB, no SQL.
  - **DB-table path** (**recommended**): the YAML is a **seed manifest** that seeds `programs` +
    `program_grid`/`dayparts` in `store.py` (the canon-folder pattern: a human file → derived rows),
    applied by a **scoped** `make seed-grid` that touches only the grid tables (**never the world
    state** — editing the grid is not a world reset; OVERVIEW §2). Recommended because the **Phase E web
    grid editor** (drag-the-grid, no file editing — a private, VPS-only, single-operator admin surface,
    never the public app) needs a table to write to, while the YAML stays the version-controlled,
    reproducible source.
  Document the choice; either way, the human edits a **file**, never raw SQL and never a web UI in Phase
  D. Expose tuning via `settings` where it's a dial (default program, console options).
- Decide how this **subsumes `framing.py`**: the program now selects hosts + framing; `show_frame`'s
  dawn/dusk handover logic folds into **daypart boundaries** (a handover program/slot at the night→day
  and day→night edges). Keep a pure `clock → frame` function, but parameterised by the grid + the
  program's hosts (N hosts, not two hardcoded).
- Define the fallback: what plays when no program matches a slot (there should be none if the grid
  tiles the week, but define a default program so the scheduler never stalls).
**Done when:** the Program/daypart/grid model is specified, **including the per-program clock
(sequence + run-lengths, with a weighted-rotation fallback)**; the storage choice (DB vs config) is made
and written down; the framing-generalisation plan is clear; a default program covers any gap.

## D6.1 — The programming module: `program_for(now)` + generalised framing
**Goal:** one module answers "what program, formats, hosts, and framing apply at this datetime," reusing
and generalising the clock framing.
**Do:**
- Add `src/world/programming.py` (or `src/programming.py`): `program_for(now: datetime) -> Program`
  reads the grid (DB or config per D6.0) and returns the active program — its format mix, host ids,
  and framing hint — for the in-world wall-clock slot.
- Generalise `world/framing.py`: instead of two hardcoded `night_host`/`day_host`, derive the on-air
  hosts + `ShowFrame` (part_of_day, lead, companion, is_handover, situation) from the **program** and
  the clock. Keep it pure/stateless and unit-testable (the way `framing`/`clock`/`events` are). The
  existing dawn/dusk handover becomes the framing of the boundary programs. Preserve backward behaviour
  for the current two-host setup (so D1–D5 work unchanged).
- Keep the writers' room integration point intact: `conversation.compose_segment` already computes a
  `ShowFrame` via `_frame_for` — feed it the program-derived hosts/frame so talk segments are framed by
  the active program, not a constant.
**Done when:** `program_for(now)` returns the right program across a week; the generalised frame yields
hour/program-appropriate hosts + situation for ≥2 hosts; existing two-host framing tests still pass.

## D6.2 — Wire the scheduler to the grid (replace the flat rotation)
**Goal:** the scheduler airs the programmed grid, on measured durations, with the never-dead chain
intact.
**Do:**
- In `scheduler.top_up`, replace the flat `rotation[rot_i % len(rotation)]` selection with a
  grid-driven one: for the current `air_cursor`, ask `program_for(air_cursor)` for the program, then
  pick the next format **by advancing that program's clock** (D6.0 — the explicit sequence/run-lengths,
  so a `music×3` sweep airs three songs in a row, then the break, then talk). Carry a **per-program
  clock cursor** in the persisted `schedule.json` state so the sequence advances correctly across
  top-up runs and resets/continues sensibly across program boundaries. Honour any **pinned slots** (e.g.
  `news@:00` at the top of the hour) when the air-cursor crosses them. Fall back to weighted rotation
  for a program with no explicit clock.
- Pass the program's host ids / framing through to generation (the format builders already assemble
  hosts via `FORMATS[name].speaker_ids()` + `context.assemble`; route the program's hosts in so the
  grid actually drives who's on air — generalise the speaker selection beyond the static
  `convo_speaker_ids`).
- **Keep everything else intact:** `buffer_depth_hours`, measured-duration accounting + `stamp_duration`,
  the disclosure ident cadence (C3), retry→skip on failure, `prune` (C2.5), and the
  `ensure_fallback_assets` step. The grid changes *what's chosen*, not the rolling-buffer/never-dead
  machinery.
- Decide the relationship to `settings.buffer_rotation`: it becomes the **default program's** format
  mix (or is superseded by the grid). Document it; don't leave two sources of truth silently fighting.
**Done when:** the scheduler airs grid-appropriate programs/formats/hosts across a simulated week,
**following each program's clock** (a music-block program airs song sweeps; an interspersed program
alternates talk/music; pinned slots land on time); buffer depth, idents, pruning, and the fallback
chain all still work; a slot with no matching program falls back to the default program (never a stall).

## D6.3 — Read-only status console (operator view)
**Goal:** a human (or an uptime view) can see the station's state at a glance, without touching files.
**Do:**
- Add a read-only console — a CLI (`python -m src.console` / `make status` — note: a basic `make
  status` already exists for playout pids; either extend it or add a distinct target) and/or a small
  read endpoint — that reports:
  - **what's airing / what's next** — from `schedule.json` (current + upcoming entries: program,
    format, hosts, air_time, measured duration);
  - **buffer depth** — reuse `health._runway_seconds` (don't recompute — reuse so they never disagree);
  - **last night's run** — the `last_topup_at` heartbeat + last tick summary (if D3);
  - **the story log** — active stories + recent beats (from D3's store reads), if D3 is built; omit the
    panel gracefully if not.
- **Strictly read-only** (the CLI must not mutate state) — the write/management surface is Phase E. Reuse
  the existing seams (`scheduler._load_state`, `health.*`, `store` reads); add no new SQL beyond simple
  reads.
**Done when:** the console prints current/next programming, buffer runway, last-run heartbeat, and (if
D3) the story log, all from existing state, mutating nothing.

## D6.4 — Now-playing / program-info feed for the web player
**Goal:** the data the C8 web player needs to show what's on — produced read-only by the backend.
**Do:**
- Produce a **now-playing / program-info feed** (a small JSON the web app can read — a written file the
  way `schedule.json`/`playlist.txt` are, or a tiny read endpoint): current program name, current
  segment (format + host display names + topic/beat from `seg.meta`), what's next, and the AI
  **disclosure line** (already in `web/src/lib/disclosure.ts` / `disclosure.DISCLOSURE_LINE` — keep the
  two in sync). Update it when the scheduler/console refreshes.
- **Scope boundary:** D6 produces the *feed*; the **player UI route is C8** (server track). If C8 isn't
  built, the feed still stands alone and is verifiable (cat the JSON / curl the endpoint). If the
  coming-soon `/web` app is convenient, a minimal now-playing read is fine, but don't build the audio
  player here.
- Keep AI disclosure correct (CLAUDE.md hard rule): the feed always carries the disclosure line.
**Done when:** a now-playing/program-info feed reflects the current schedule + program + disclosure and
updates as the schedule advances; it's consumable by the (future) C8 player and verifiable on its own.

## D6.5 — Tests + verification + docs
**Goal:** the grid + framing logic is covered, and the programming is demonstrable.
**Do:**
- Tests (surgical; pure logic where possible): `program_for(now)` returns the right program across
  weekday/hour boundaries and the grid tiles the week with no gaps (default covers any hole);
  generalised framing yields correct hosts/handover for boundary vs mid-program slots and preserves the
  two-host behaviour; the scheduler picks grid-appropriate formats/hosts (mock generation); the console
  + now-playing feed render from a fixture `schedule.json` without mutating it. Keep the clock/framing
  tests' pure style.
- Add a demo: generate/inspect a simulated week and show the programs/hosts changing by daypart; print
  the console + now-playing feed.
- Update `README.md` (the programming grid; the console + now-playing feed; how to edit the grid —
  noting full management is Phase E), `.env.example` (`PROGRAMMING_*`/console dials), and the DEVLOG
  (Phase D — D6).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the simulated-week demo
shows named programs changing by daypart, and the console + now-playing feed reflect live state.

---

## Explicitly NOT in D6 (→ other sub-packs)
- **The write/management surface** (edit the grid, allocate DJs to shows, CRUD personas, trigger
  regeneration) → **Phase E** (D6's console + grid are strictly read-only / data-only).
- **The web audio player UI** → **C8** (server track). D6 only produces the now-playing/program-info
  *feed* the player consumes.
- **Sound design (idents/beds/stings) keyed to dayparts, and commercial-break cadence** → **D7 / D8**
  (they build on D6's dayparts).
- **Growing the cast beyond the two hosts / DJ memory** → **D9** (D6 makes the grid able to reference
  N hosts; D9 adds them and their memory).
- **The story-log content itself** → **D3** (D6's console only *displays* it).

# PHASE_D_COMMERCIALS_TASKS.md — D8: Commercials & Sponsorship

> Sub-pack **D8** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` (especially the **IP
> boundary** — fictional +600y products only, no real brands/franchises/people — and the safety gate)
> and the Phase D standing principles (OVERVIEW §2). Written against the **as-built code**: the
> single-DJ producer pattern in `formats/news.py` (`generate_safe(lambda: llm.generate(...))` → on a
> persistent safety flag, `evergreen.evergreen_segment(...)`, else `common.render_single_voice`), the
> format registry `formats.FORMATS` + `make_format_segment` + `stamp_duration` (a new format is a
> registry entry), the scheduler placement loop `scheduler.top_up` (post-D6, grid-driven), and the
> store SQL seam.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D8 brief); `docs/ROADMAP.md` (Phase D "commercials &
> sponsorship" bullet); `src/formats/news.py` (**the producer pattern to copy verbatim** — gate +
> evergreen fallback); `src/scheduler.py` (placement/cadence); `docs/MARKETING.md` (the **"Powered by,"
> never "Sponsored by"** rule + sponsorship policy — this is binding); `docs/PHASE_D_PROGRAMMING_TASKS.md`
> (D6 — dayparts decide breaks) + `docs/PHASE_D_PRODUCTION_TASKS.md` (D7 — break stings).
>
> **Depends on:** **D6** (dayparts decide when a break airs), **D7** (the stings that bracket a break).
> Real **sponsor "Powered by" reads also gate on CM** (donations live) — but the *plumbing* (format,
> table, cadence) can land now and be populated when sponsors exist.

**What D8 delivers (ROADMAP, verbatim intent).** An in-world **`commercial`/`promo` format** — Claude
writes a short spot for a fictional +600y product, or a station promo, voiced like any segment — plus a
scheduler **ad-break cadence** (the dayparts decide when a break airs). Real **"Powered by"** reads —
once donations are live (CM) — come from a small **`sponsors` table** (text, optional audio, run
window), **always "Powered by," never "Sponsored by"** (per `docs/MARKETING.md`). **Keep it sparse and
in-character — texture, not interruption.**

**Two content kinds, kept separate.**
1. **Commercials / promos** — *generated* in-world spots (a fictional product, or a station self-promo).
   The bulk of the texture; generated text → gated → evergreen-fallback, like any producer.
2. **Sponsor "Powered by" reads** — *real* acknowledgements from the `sponsors` table (a short read, or
   optional pre-recorded audio), placed within a run window. Plumbing now; real sponsors at CM.

**Load-bearing principle — generated, NOT prerecorded (this is what avoids "the same jingle 50× a day").**
A prerecorded ad reel rotates a tiny set and goes stale fast — the small-catalogue problem. So commercials
are **written fresh and voiced fresh every airing**: a break is *never the same spot twice*. Infinite,
in-character ad copy is the whole advantage of the AI approach, and the opposite of a rotating jingle.
**Prerecorded audio is the sparse exception**, only where it earns its place: a sponsor's own supplied
clip (D8.2's optional `audio_path`), or a short **brand sting** (a ~2s recognizable sound for a recurring
in-world product — curated like an ident; a 2s sting rotating is fine, a 30s jingle rotating is not). Default
to generated; reach for prerecorded only for those two cases.

**Definition of done for D8:** a `commercial`/`promo` format airs short, in-world, IP-safe spots that are
**generated fresh each airing** (never a repeating reel) and pass the gates (or fall back to evergreen),
at **L1** (single voiced read) with **L2/L3/L4 opt-in** via D7/D9/D10; the scheduler airs a **sparse** ad
break on a daypart-driven cadence, bracketed by D7 stings; a `sponsors` table + "Powered by" read producer
exists and honours run windows + the "Powered by" wording (populated later); `ruff` + `pytest` green;
README/DEVLOG updated.

---

## D8.0 — The in-world `commercial` / `promo` format
**Goal:** a new producer that writes and voices a short in-world spot — a fictional +600y product or a
station promo — safely.
**Do:**
- Add a producer (e.g. `src/formats/commercial.py`) and register it in `formats.FORMATS` (a new entry →
  `make_format_segment` dispatches it; `stamp_duration` gives honest duration for free). Decide whether
  `commercial` and `promo` are one builder with a **mode** (`commercial` = fictional product spot; `promo`
  = station self-promo) or two entries sharing a builder — **recommend one builder + a mode** to share
  the gate/render plumbing; document the choice.
- **Copy `news.py`'s pattern verbatim:** `generate_safe(lambda: llm.generate(..., cached_context=...))`
  → on a persistent safety flag, `evergreen.evergreen_segment(...)` (never air a flagged spot) → else
  `common.render_single_voice`. Single voice (decide: a host, or a distinct "ad read" voice from the
  registry). Keep `disclosure=True` and put the mode + (for promos) what's promoted in `meta`.
- **Enforce the hard rules in the prompt + rely on the gate:** the spot is for a **fictional +600y
  product/service or a station promo** — *never* a real brand, franchise, person, or trademark (CLAUDE.md
  IP boundary); stay inside the fiction; never mention being an AI. Keep it short (config word-count +
  `length_target_sec` dials, like the other formats) and in the station's voice — texture, not a hard
  sell.
- For **promos**: it may reference real station facts (the show grid from D6, "Powered by" supporters,
  the Ko-fi/follow call) — keep those truthful and in-character.
- **Production spectrum — level 1 now, richer levels opt-in (reuse existing machinery, don't build new).**
  Ship the single-voice read first; the richer levels are the *same seams the other sub-packs build*,
  applied to a spot, so they're config/flags not new infrastructure. Keep richer spots **sparse** —
  texture, not a production showcase. A `production_level` (or per-spot tag) selects:
  - **L1 — voiced read** *(default, this task)*: one voice, a sting bracket (D8.1 + D7).
  - **L2 — read over a bed**: the spot sits over a music bed, ducked → "produced" feel. **Reuses D7's
    mixing primitive** (the bed-under-speech path); just opt the spot in.
  - **L3 — multi-voice "scene" / testimonial**: a two-voice mini-skit, or an **in-world figure giving a
    testimonial** ("'changed my crossing,' said a relay-keeper"). **Reuses the conversation turn model
    (N voices) + D9's guest/non-host voice + D10 figures** — a testimonial is literally a D10 figure × D9
    voice, the same soundbite mechanism as a news quote. No new audio plumbing.
  - **L4 — brand sting / sung tag** *(sparse)*: a short curated audio bookend per recurring in-world
    product (a D7-style curated sting, GC-safe under `assets/`). The *only* prerecorded ad audio, kept to
    a couple of seconds so its rotation is unnoticeable.
  Document the levels; gate the generated text at every level (L2/L3 text still passes `generate_safe`);
  default `production_level=1` so D8 ships without depending on D7/D9/D10 being built yet.
**Done when:** the format produces short in-world commercials and station promos that pass the gates;
a flagged draft falls back to evergreen; spots never name a real brand/person; mode + payload + the
production level are in `meta`; the segment is duration-stamped and registered; **L1 works standalone, and
L2/L3/L4 are wired to opt in via D7/D9/D10 (degrading to L1 when those aren't built).**

## D8.1 — Ad-break cadence (the dayparts decide when a break airs)
**Goal:** breaks air **sparsely**, at daypart-appropriate moments — texture, never wall-to-wall.
**Do:**
- Add an **ad-break cadence** the scheduler honours: a "break" is one (or a small number) of
  `commercial`/`promo` (and later sponsor-read) segments, placed on a cadence the **D6 dayparts/grid
  decide** (e.g. a break per program, or every N minutes of content / every M content segments). Drive
  it from `program_for(air_cursor)` / the grid (a program declares whether/how often it takes breaks),
  not a global constant — different dayparts carry different ad loads.
- **Bracket the break with D7 stings** (a break opener/closer sting) so a break sounds like a break, and
  return to programming cleanly.
- Keep cadence dials in `settings` (`commercial_break_every_*`, `commercial_break_max_segments`),
  **defaulting sparse** — over-running ads is worse than none (ROADMAP: texture, not interruption). The
  disclosure ident (C3) and never-dead chain (C4) are unaffected.
- Place breaks via the normal scheduler entry mechanism (like the disclosure ident / D7 idents) so
  playout needs no change; honest duration accounting and `prune` behave as usual.
**Done when:** the scheduler airs sparse ad breaks at daypart-driven points, bracketed by stings, with
cadence as a dial; no daypart is over-loaded; buffer depth / idents / fallback all still work.

## D8.2 — The `sponsors` table + "Powered by" reads (plumbing now, sponsors at CM)
**Goal:** real supporter acknowledgements, correctly worded and time-bounded — built now, populated when
donations exist.
**Do:**
- Add a **`sponsors` table** in `store.py`: `sponsors(id, name, powered_by_text, audio_path nullable,
  run_start, run_end, weight/cadence, tags)`. Add row dataclass + writes + reads (`active_sponsors(now)`
  honouring the run window). Fold into `clear_world`/`counts`.
- Add a **sponsor-read producer**: for an active sponsor, either voice a short **"Powered by {name}…"**
  read (generated/templated text, still through the safety gate) **or** play the optional pre-recorded
  `audio_path` (curated under `assets/` — GC-safe). Place it on a sparse cadence within breaks/boundaries
  (reuse D8.1's mechanism).
- **Enforce the wording rule (binding, `docs/MARKETING.md`): always "Powered by," NEVER "Sponsored by."**
  Template the lead-in so it can't drift; if generated, reject/avoid "sponsored." Keep reads short and
  in-character.
- **Scope/gating:** the table starts empty and reads nothing until populated — so this ships harmlessly
  before CM. Real sponsors are added once donations are live (CM); note in the code + README that
  populating real sponsors is gated on CM, not on D8.
**Done when:** the `sponsors` table + active-window reads work; a populated test sponsor produces a
"Powered by" read (text or audio) within its run window and nothing outside it; the wording is
guaranteed "Powered by"; an empty table airs no sponsor reads.

## D8.3 — Tests + verification + docs
**Goal:** the commercial/sponsor logic is covered, and the texture is demonstrable.
**Do:**
- Tests (surgical; mock `llm.generate`): the commercial/promo builder produces a spot, a flagged draft
  falls back to evergreen, and the prompt/gate keep it IP-safe (assert no real-brand path / the safety
  fallback fires on a planted flag); the break cadence places breaks per the daypart and stays within the
  max-per-break cap; `active_sponsors(now)` honours run windows (in/out); the "Powered by" wording is
  enforced (a "sponsored by" attempt is corrected/rejected); an empty sponsors table yields no reads.
  Use fixtures; don't spend tokens.
- Add a demo: generate a commercial + a promo, and show a sparse break (sting → spot → sting) placed in a
  simulated daypart; with a test sponsor row, show a "Powered by" read in-window.
- Update `README.md` (the commercial/promo format; the break cadence dials; the `sponsors` table +
  "Powered by" rule + that real sponsors come at CM), `.env.example` (`COMMERCIAL_*`/sponsor dials), and
  the DEVLOG (Phase D — D8).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the demo shows an in-world
spot + a sparse, sting-bracketed break, and a "Powered by" read honouring its run window.

---

## Explicitly NOT in D8 (→ other sub-packs / phases)
- **The stings/beds + the mixing primitive themselves** → **D7** (D8 *places* D7's stings around a break
  and *opts a spot into* D7's bed for L2; it doesn't build the mixing).
- **The voices for an L3 multi-voice / testimonial spot** → **D9** (the guest/non-host voice slot) — D8's
  L3 *reuses* it; without D9 (and D10 for the figure), L3 degrades to L1.
- **The in-world figure who gives an L3 testimonial** → **D10** (a figure × a D9 voice = the testimonial,
  the same as a news soundbite). D8 supplies the *spot context*, not the figure.
- **Which dayparts carry ads / the program grid** → **D6** (D8 reads the grid's break decisions).
- **Adding real sponsors / turning donations on** → **CM** (marketing) — D8 ships the empty table +
  read plumbing; real sponsors are populated when donations are live.
- **emotion in the ad-read voice / extra ad-read DJs** → **D9**.
- **Generating jingles/brand audio (incl. an L4 brand sting)** → human/Suno via JINGLE_PROMPTS; D8 only
  *reads/plays* curated audio and *generates spot copy* — it never synthesizes the sung/musical audio.

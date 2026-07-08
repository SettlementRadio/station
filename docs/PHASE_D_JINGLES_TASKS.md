# PHASE_D_JINGLES_TASKS.md — extend jingle use across the new grid

> **Read first:** `docs/JINGLE_PROMPTS.md` (the media brief + §3 placement mapping + §4 file names),
> `docs/JINGLE_PROMPTS_2.md` (the new per-program themes to generate), `src/production/media.py`
> (the registry), `src/production/placement.py` (`boundary_segments`), `docs/programming/grid.yaml`
> (the ~28 programs), `src/config.py` (the `production_*` dials).

## The gap (why this exists)

The sonic-identity code was built for the **old 4-daypart grid**. Two things drifted out of sync
when the grid grew to ~28 named programs (`docs/programming/grid.yaml`):

1. **Content.** Only 4 daypart themes exist (`b4_night`, `b5_first_light`, `b5a_daywatch`,
   `b5b_nightfall`). The ~24 subject/currents/weekend programs have **no opening theme**.
   `JINGLE_PROMPTS_2.md` is the brief for the missing clips.
2. **Code.** `PROGRAM_THEMES` in [src/production/media.py](../src/production/media.py) maps only those
   old ids — and one, `daywatch`, **no longer exists** in the grid. `program_theme_segment` →
   `theme_for_program` returns `None` for almost every current program, and `boundary_segments` has
   **no fallback**, so most shows open cold (straight into speech, no ident).

## The design (convention + reuse + fallback — do this, don't hand-map 28 rows)

Resolve a program's theme in this order, so new programs wire themselves and nothing opens cold:

1. **Explicit override** — an entry in `PROGRAM_THEMES` (legacy daypart files + the two reuse cases).
2. **Convention** — `assets/themes/<program_id>.mp3`. This is the contract with `JINGLE_PROMPTS_2.md`:
   the filename *is* the grid program id, so dropping the clip in is the only step — no code edit.
3. **Format-theme fallback** — the program's first content format's theme (`news` → C7, `talk` → C9,
   `music` → the music bumper is a sting, so talk theme). Guarantees an on-brand open even before the
   bespoke clip is generated.
4. **None** — logged, skipped (never a crash, never dead air).

Keep the "missing file → warn + skip" behaviour throughout — the human generates media over time.

---

## Tasks

### J1 — Convention-based per-program theme resolution
**File:** `src/production/media.py`.
- Change `theme_for_program(program_id)` to: return the `PROGRAM_THEMES` override if present; **else**
  fall back to the convention path `themes/{program_id}.mp3` and resolve it (existing `_resolve`, so a
  missing file still returns `None` + a `media_unmapped`/`media_file_missing` log).
- Do **not** add the format fallback here (keep `media.py` keyed purely by id) — that lives in J3.
- **Verify:** `python -c "from src.production import media; print(media.theme_for_program('the_assembly'))"`
  logs a `media_file_missing` for `assets/themes/the_assembly.mp3` (until the clip exists) and returns
  `None`; with a dummy file at that path it returns the resolved `Path`.

### J2 — Repoint the stale registry
**File:** `src/production/media.py` — `PROGRAM_THEMES`.
- **Remove `daywatch`** (gone from the grid).
- **Keep the legacy daypart overrides** so existing files still resolve: `long_night` → `b4_night`,
  `first_light` → `b5_first_light`, `nightfall` → `b5b_nightfall`.
- **Add the two reuse overrides** (existing batch-1 files, no new media): `the_mailbag` →
  `themes/c11_letters.mp3`, `the_circuit` → `themes/c12_games.mp3`.
- Everything else resolves by the J1 convention — no entry needed.
- **Verify:** the resulting dict has exactly those 5 keys; `theme_for_program('the_circuit')` resolves
  to the c12 file when present.

### J3 — Format-theme fallback at the boundary
**File:** `src/production/placement.py` — `program_theme_segment(program, now)`.
- When `media.theme_for_program(program.id)` is `None`, fall back to
  `media.theme_for_format(<first content format of program.clock>)` before giving up.
- Derive the first content format from `program.clock`: the first entry, stripped of any `@:MM` pin
  (`news@:00` → `news`); a solo-`music` program → fall back to the talk theme (music has a bumper
  sting, not an opener). Add a small helper (e.g. `_first_content_format(program)`).
- Stamp the segment's `meta` so the console/feed still name the show (as it does today).
- **Verify:** a talk-first program with no bespoke clip opens on `c9_talk.mp3`; `settlement_desk`
  (clock starts `news@:00`) opens on `c7_news.mp3`.

### J4 — Beds & bedded programs for the new night shows
**Files:** `src/config.py` (`production_bedded_programs`), `src/production/media.py` (`PROGRAM_BEDS`).
- `production_bedded_programs` is still `["long_night"]`. The new grid's solo/atmospheric night shows
  are the natural bed candidates: `long_night`, `deep_hours`, `deep_field`, `the_gathering`,
  `deep_listening`. Extend the dial to those.
- Beds need a curated `_bed` loop variant to actually duck (D7.3). Only `b4_night_bed` exists today,
  so bedding stays a no-op for the others until those are generated — that's fine (doubly opt-in:
  `bed_clip_for` returns `None` when no bed file is mapped/on disk). **Note in the doc** that new
  `*_bed.mp3` variants are a *later, optional* media task, not required for this pack.
- **Verify:** `bed_clip_for('deep_hours', 'talk')` returns `None` today (no bed file) and does not
  crash; `long_night` still beds as before.

### J5 — Sweeper dayparts (light polish; optional)
**File:** `src/production/media.py` — `SWEEPERS`.
- The new grid uses dayparts like `morning`, `midday`, `evening`, `late morning`, `afternoon`,
  `weekend morning`, `weekend`. Currently only `deep night`/`first light`/`daytime`/`nightfall` are
  mapped; the rest fall to `_SWEEPER_DEFAULT` (mid) — graceful, so this is optional.
- If done: map day-energy dayparts (`morning`/`midday`/`afternoon`/`evening`/`late morning`/`weekend
  morning`) → `daytime` (bright), keep `deep night`/`deep-night-ish` → calm, dusk → mid.
- **Verify:** `sweeper_for_daypart('afternoon')` no longer logs a fallback-to-default (if mapped).

### J6 — Sync docs, tests, acceptance
- Update `JINGLE_PROMPTS.md` §3 (the mapping table still names `daywatch` and the old 4-program world)
  — either refresh it to point at the convention + `JINGLE_PROMPTS_2.md`, or add a one-line
  "superseded by JINGLE_PROMPTS_2 / convention" note so the two docs don't contradict.
- Update the production-placement tests (search `tests/` for `theme_for_program`, `boundary_segments`,
  `PROGRAM_THEMES`, `daywatch`) for the new resolution order + the removed `daywatch` key; add a case
  for the convention path and one for the format fallback.
- `make acceptance` stays green; `ruff` clean.
- Append a one-line DEVLOG entry and flip nothing in the overview tracker (this is a follow-on to D7,
  not a new sub-pack) unless you want a tracked row.

---

## What the human does in parallel (content)

Generate the clips in `docs/JINGLE_PROMPTS_2.md` in Suno, trim/fade, and drop each at
`assets/themes/<program_id>.mp3`. As each file lands, that program's boundary automatically upgrades
from the format-theme fallback (J3) to its bespoke opener (J1) — **no re-seed, no restart, no code
change**. Until then every show still opens on-brand via the fallback.

> This whole pack is **behind the TTS/media seam** — no model below Layer 4 changes, playout is
> untouched, and every step degrades to "skip the clip" when a file is absent.

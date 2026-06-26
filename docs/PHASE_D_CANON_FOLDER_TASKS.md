# PHASE_D_CANON_FOLDER_TASKS.md — D1: Canon → Folder (the static substrate)

> Sub-pack **D1** of Phase D (see `docs/PHASE_D_OVERVIEW.md` for the map). Work in order, one task at
> a time: implement → show + how to verify → stop for review. Respect `CLAUDE.md` (seams, model
> routing, config-over-hardcoding, structured logging, hard rules) and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the real signatures are
> `canon_source.load(path)` / `load_series_bible(path)`, `store.insert_canon/insert_cast/
> insert_events` + the `CanonFact/CastMember/Event` row shapes, `seed.py` reading `settings.
> canon_path`, and `context.assemble` calling `canon_source.load_series_bible(settings.canon_path)`.
>
> **Read first:** `docs/PHASE_C_ORIENTATION.md` §9 (this is the "Canon → folder" seam); `docs/CANON.
> md` (the current single-file stub); `src/world/canon_source.py`, `src/world/seed.py`, `src/world/
> context.py` (the parse → seed → assemble path); `CLAUDE.md` ("the canon lives in docs/CANON.md").

**Why this is first.** Everything else in Phase D stands on the bible. RAG (D2) needs a canon big
enough to be worth embedding; the world engine (D3) needs a substrate to stay consistent with; the
news desk (D4) and DJs (D9) draw on it. D1 turns the Phase-A stub (`docs/CANON.md`, ~105 lines, one
event) into a real, growable, **folder-structured** bible the seeder reads whole — *without* changing
the row shapes or the gates downstream.

**The core constraint.** `docs/CANON.md` is the human-editable source of truth (CLAUDE.md). D1 must
keep it that way: the human authors prose in well-marked files; the parser projects the structured
sections (`canon facts` / `cast` / `events`) into rows and keeps the narrative sections as the cached
series bible. **No second machine-readable copy.** The bullet-field convention stays
`- **Field:** value`; section headings stay `## `/`### `.

**Definition of done for D1:** `docs/canon/` is a folder of cornerstone files; seeding (`make seed-canon`,
+ `make reset-world` for a fresh DB — D1.2) reads the whole folder and loads strictly more canon than the
old stub; the series bible assembled into `context` is drawn from the folder; re-seed is idempotent; fact
ids are globally unique across files;
`ruff` + `pytest` green; README + `.env.example` updated. **Tag *population* is deferred to D2** — D1
only makes the format *support* per-fact tags.

---

## D1.0 — Design the folder layout + authoring conventions (decide, write it down)
**Goal:** a cornerstone-file layout and a documented authoring format, so the human can write the
bible and the parser has a stable contract.
**Do:**
- Choose the cornerstone files under `docs/canon/` — the ROADMAP names: history, literature, finance,
  war, nations, peoples/aliens, geography, religion, culture, tech, **cast**. Use a numeric prefix for
  reading order (e.g. `00-station.md`, `01-time.md`, `10-history.md`, …, `90-cast.md`,
  `95-events.md`). Cast and events keep their own files (they project to rows).
- Decide which `## ` sections are **structured** (projected to rows — `canon facts`, `cast`,
  `events`) vs **series bible** (cached narrative prose — the rest, e.g. `the station`, `the time
  concept`, and the new cornerstone prose). A file may contain both: a narrative body *and* a
  `## Canon facts` list of its hard, queryable facts.
- Decide the **fact id scheme** so ids are unique across files (the current parser numbers
  `canon-1, canon-2, …` per call, which collides across files). Recommend `canon-<file-stem>-<n>`
  (e.g. `canon-history-3`), derived from the filename — stable for re-seed idempotency.
- Decide the **per-fact tag affordance** the format must support so D2 can populate it later without a
  re-format. Recommend an optional trailing ``tags: `a, b` `` on a fact, or a `- **Tags:** a, b`
  bullet — pick one and document it. (Population is D2; D1 just parses it if present, else `[]`.)
- Write `docs/canon/README.md` documenting the layout, the section conventions, the field-bullet
  convention, the id scheme, and the tag affordance — this is the human's authoring guide.
**Done when:** `docs/canon/README.md` describes the layout + conventions; the structured-vs-bible
split and the id/tag schemes are written down and ready to implement against.
**Note:** keep the choice minimal and consistent with the existing parser regexes (H2/H3 headings,
`- **Field:** value`, numbered fact lists) so D1.1 is an extension, not a rewrite.

## D1.1 — Folder-loading canon parser (globally-unique ids; bible from many files)
**Goal:** `canon_source` reads a folder of files and merges them into the existing row shapes, with
unique ids and a folder-wide series bible.
**Do:**
- Add `canon_source.load_folder(canon_dir: Path) -> tuple[list[CanonFact], list[CastMember],
  list[Event]]` that iterates `*.md` in sorted (numeric-prefix) order, parses each with the existing
  per-section parsers, and concatenates the results. Keep the single-file `load()` working (delegate
  to it, or keep it for tests) so nothing breaks abruptly.
- Make fact ids globally unique per the D1.0 scheme (e.g. namespace `_make_fact` by file stem). Cast
  and event ids are already slug-based (`_slug(name)`) and stay stable — but **guard against
  duplicate slugs across files** (fail loud, like the existing missing-field errors).
- Add `load_series_bible_folder(canon_dir) -> str` that concatenates the narrative (non-structured)
  sections across files in order, preserving `## ` headings, so the cached core reads naturally.
  Generalise `_BIBLE_HEADINGS` from the two hardcoded headings to "every `## ` section that isn't one
  of the structured three" (so new cornerstone prose is included automatically).
- Parse the optional per-fact tags affordance from D1.0 into `CanonFact.tags` (empty list if absent).
**Done when:** `load_folder` over a small fixture folder returns merged facts/cast/events with unique
ids; `load_series_bible_folder` returns the concatenated narrative; duplicate slugs raise; tags parse
when present. Unit-tested (`tests/test_canon_source.py` extended).

## D1.2 — Config + seed + context read the folder
**Goal:** the whole pipeline points at the folder, swappably by config.
**Do:**
- Add `settings.canon_dir: Path` (default `_REPO_ROOT / "docs" / "canon"`) in a new
  `# --- Canon (D1) ---` section. Decide the relationship to the existing `settings.canon_path`:
  prefer keeping `canon_path` for the single-file/back-compat path and adding `canon_dir` for the
  folder, OR repoint `canon_path` at the dir — document the choice in the config comment and the
  summary. (Recommend: add `canon_dir`, have seed/context prefer it when the folder exists.)
- Update `src/world/seed.py` to load from the folder (`canon_source.load_folder(settings.canon_dir)`)
  and insert via the unchanged `store.insert_*`. Keep the idempotent re-seed flow.
- **Two seed modes — do NOT let a canon refresh nuke the living world (load-bearing).** Today
  `clear_world` does a blanket `TRUNCATE canon, "cast", events, state`, which is fine while every event
  is hand-seeded. But once **D3** generates a *living* world (new events + a story log written by the
  nightly tick, directly to the DB — not the folder), a re-seed to pick up a one-line bible edit would
  **destroy everything the tick has generated**. So split the seed now, before that state exists:
  - **`make seed-canon`** (the EVERYDAY command) — re-load + re-insert ONLY the folder-owned tables
    (`canon`, `cast`, the bible, the `source=seed` events, and re-embed) **without** truncating the
    dynamic, tick-owned tables (`events` the tick wrote, the D3 `stories`/beats, tick figures/quotes) or
    the config/catalog (grid/tracks/sponsors). This is the **safe default** an operator runs after every
    bible edit; and
  - **`make reset-world`** (the DESTRUCTIVE command — loud warning + an explicit confirmation prompt) —
    truncate + rebuild the **world+canon** set from the folder (the "cleared" column of the OVERVIEW §2a
    matrix). **Never** touches grid/tracks/sponsors (station config/catalog have their own
    `seed-grid`/`seed-tracks`/`seed-sponsors`). Used for dev / first seed / a deliberate world wipe.
  - **Naming matters (audit fix):** the *common* command must be the *safe* one. Do **not** keep
    `make seed` meaning "full destructive reset" once the world is alive — it's a foot-gun. `seed-canon`
    is the daily driver; `reset-world` is the one that warns. (Keep a `make seed` alias only if it maps
    to `seed-canon` or is removed — never to the destructive path.)
  - Make `clear_world` take a **scope** (which tables it clears) so each command clears exactly its matrix
    column. The folder's **seed events** and the tick's **generated events** both live in `events`, so
    distinguish them with a **`source` column (`seed` | `tick`)** (the OVERVIEW §2a convention): a
    canon refresh replaces only `source=seed`, never `source=tick`. Decide + document the `source`
    convention here; **D3.0, D10.0, and the §2a matrix all honour the same split.**
  - **Migrations, not truncate-reseed, for schema changes (OVERVIEW §2):** adding the `source` column (and
    any later column) lands via an additive, idempotent migration / backfill — never by wiping live state.
- Update `src/world/context.py` to assemble the cached bible from the folder
  (`load_series_bible_folder(settings.canon_dir)`).
**Done when:** `make seed-canon` reads `docs/canon/`; `context.assemble` includes the folder's narrative in
`cached_context`; the config dial selects file-vs-folder; **`make seed-canon` updates the bible/cast/facts
(and re-embeds) while leaving any `source=tick` `events` rows intact** (verifiable now by hand: insert a
fake `source=tick` event, run `seed-canon`, confirm it survives); **`make reset-world` warns + confirms
before wiping, and never touches grid/tracks/sponsors**; no SQL moved out of `store.py`.

## D1.3 — Migrate the existing stub into the folder
**Goal:** the world's current content lives in the new structure, losslessly, and the old stub is
retired cleanly.
**Do:**
- Split `docs/CANON.md` into the cornerstone files: `the station` + `the time concept` → the bible
  files (`00-station.md`, `01-time.md`); the ~6 canon facts → the appropriate cornerstone file(s)'
  `## Canon facts` lists (re-id per the scheme); `## Cast` (Vell, Wren) → `90-cast.md`; `## Events`
  (Lumen Festival) → `95-events.md`. Drop the Phase-A-only `## Phase A segment spec` section (it's not
  world content).
- **Ask the human before deleting/overwriting `docs/CANON.md`** (CLAUDE.md hard rule). Recommend
  leaving a short `docs/CANON.md` pointer that says "the bible now lives in `docs/canon/` — see
  `docs/canon/README.md`," rather than deleting it, so external references don't dangle.
- Verify the migration is lossless: every old fact/cast/event appears in the new folder; `make seed`
  `counts` are ≥ the old counts.
**Done when:** the seeded world from `docs/canon/` reproduces (and can extend) the old content; the
old monolith is retired to a pointer; `make seed` + `make demo`/`make conversation` still run.
**Note:** this is where the human's bible-authoring begins (ROADMAP: "author the world bible — yours
to write"). D1 ships the *structure + the migrated stub*; the human grows the cornerstone files over
the phase. Don't fabricate large amounts of new canon here — migrate what exists and leave clearly
marked room.

## D1.4 — Tests + verification + docs
**Goal:** the folder substrate is covered where a silent bug would bite, and reproducible from scratch.
**Do:**
- Extend `tests/test_canon_source.py`: folder load merges multiple files; ids are globally unique;
  duplicate cast/event slugs raise; the series bible includes new cornerstone prose; tags parse when
  present and default to `[]`. Use a small fixture folder (don't depend on the real bible's contents).
- Confirm the existing `test_context` still passes (assembly over the folder).
- Update `README.md` (the bible now lives in `docs/canon/`; how `make seed` reads it) and
  `.env.example` (the new `CANON_DIR`). Add a DEVLOG entry (Phase D — D1).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff check src tests` + `ruff format --check` clean; `pytest` green (new cases
included); README + `.env.example` + DEVLOG updated.

---

## Explicitly NOT in D1 (→ later sub-packs)
- **Tag population / embeddings / pgvector / `search_canon`** → **D2** (D1 only makes the format
  *support* tags; `canon_by_tags` stays inert until D2 fills tags and RAG lands).
- **Generating new world content / story arcs / the world tick** → **D3** (D1 is the *static*
  substrate; the *moving* present is the keystone).
- **Splitting the canon into RAG chunks / embedding granularity** → **D2**.
- **Authoring the full bible** → the human's ongoing work across the phase; D1 ships structure + the
  migrated stub only.

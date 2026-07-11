# PHASE_E_PANEL_TASKS.md — E1: The Operator Panel (the write control surface)

> Sub-pack **E1** of Phase E — the first Phase E pack, deliberately pulled forward: **build it during
> the C9 soak week** (7 days of hands-off waiting = free build capacity), so the panel is ready the
> day the station goes public and the human switches from *building* the station to *running* it.
> Work in order, one task at a time: implement → show + how to verify → stop for review. Respect
> `CLAUDE.md` — especially the hard rule this pack exists inside: **public read-only, admin private.
> The panel is VPS-only, single-operator, and NEVER internet-exposed.**
>
> **Read first:** `docs/ADMIN_MANUAL.md` (**the requirements spec** — every `→ Phase E panel` tag is
> one workflow this panel replaces; the manual's §"Admin access & security" states the security
> posture verbatim); `docs/ROADMAP.md` (Phase E "management / control surface" bullet);
> `src/console.py` + `src/health.py` + `src/costprobe.py` + `src/nowplaying.py` (the read side —
> already built, reuse, don't re-derive); `src/scheduler.py` (`split_schedule`, `_load_state` — the
> shared "what's on" source); `src/world/seed.py` / `seed_tracks.py` / `seed_sponsors.py` (the write
> actions the panel triggers); `docs/programming/README.md` + `grid.yaml` (the grid model the editor
> must round-trip).
>
> **Depends on:** C5 (a VPS to be private *on*) for deployment — but every task below runs and is
> verified **locally first** (localhost is localhost on either box). Nothing here blocks, or is
> blocked by, C7–C9 code.

**What E1 delivers (ROADMAP, verbatim intent).** Upgrade Phase D's read-only console into a real
operator surface: edit the weekly grid + dayparts, allocate DJs to shows, add/edit/remove DJs and
personas, manage sponsors/tracks/pronunciation, tune the dials, trigger seeds/ticks/regeneration,
and see status — **without hand-editing files and re-seeding by hand.** The per-story
approve/reject queue remains a *later* Phase E opt-in (see "NOT in E1").

## Load-bearing principles (decide once, honour throughout)

1. **Forms over files — the files STAY the source of truth.** The panel edits the *existing*
   human-authored sources (`grid.yaml`, `tracks.yaml`, `sponsors.yaml`, `pronunciation.yaml`,
   `voices.yaml`, `docs/canon/*.md`, `.env`) and runs the *existing* seed/refresh paths. It never
   moves truth into the DB, never invents a second store, never bypasses a seam. Consequences that
   matter: everything stays git-diffable; the §2a seed/backup matrix is untouched; if the panel
   dies, the hand-edit workflows in ADMIN_MANUAL.md still work, losing nothing. The panel is a UI
   over the manual — not a replacement for its substance.
2. **Private by network position, not by auth code.** The app binds to `127.0.0.1` ONLY (a
   `panel_host` setting that defaults there; refuse a non-loopback bind without an explicit
   `PANEL_ALLOW_NONLOCAL=true` escape hatch that logs a loud warning). Access on the VPS is an SSH
   tunnel (`ssh -L 8787:localhost:8787 <vps>`). Single operator + SSH keys = no login system to
   build or get wrong. Never a public DNS name, never a reverse-proxy rule, never in `/web`.
3. **Not in `/web`, not on Vercel — ever.** `/web` is the public, read-only surface. The panel is a
   Python app in the station backend (`src/panel/`), same venv, importing `settings`/`store`/
   `console`/`health` directly — one codebase, no API duplication.
4. **Destructive actions keep their friction.** `reset-world` (and any future wipe) requires a
   typed confirmation phrase in the panel, mirroring the Make target's warn+confirm. A button must
   never be *less* safe than the command it replaces.
5. **Validate with the same code that consumes.** A grid edit is validated by actually loading it
   through `world/programming.py`'s loader before write; a voices edit through the tts registry
   loader; a tracks edit through the seeder's parser. Reject-on-invalid with the loader's real
   error — never a second, drifting validator.
6. **Engineering standards apply in full** (this is station backend, not the pragmatic `/web`):
   settings via `src/config.py` (`panel_*` prefix), structured logging, type hints, surgical tests.

**Definition of done for E1:** every `→ Phase E panel` tag in ADMIN_MANUAL.md is either served by a
panel screen or explicitly deferred in "NOT in E1"; the panel runs locally and on the VPS behind an
SSH tunnel, bound to loopback; a grid/cast/tracks/sponsors/dial edit made in the browser round-trips
to the file, validates, re-seeds where needed, and shows up on air; `reset-world` from the panel
demands the typed phrase; `ruff` + `pytest` green.

---

## E1.0 — Skeleton + the status dashboard (read side first)

**Goal:** a running local web app that shows everything the operator can already see via
`make console` / `make health` / `make now-playing` / `make costprobe` — one screen, zero writes.

**Do:**
- `src/panel/` — a small FastAPI app (add `fastapi` + `uvicorn` to requirements; server-rendered
  templates or a single small JS-free page set — this is a single-operator tool, not a product UI;
  no CDN assets, everything served locally).
- Settings: `panel_host: str = "127.0.0.1"`, `panel_port: int = 8787` (+ the non-local escape
  hatch per principle #2). `make panel` target runs `uvicorn` on them.
- Dashboard screen: on-air / next (reuse `scheduler.split_schedule` + `onair_hosts` — the SAME
  answer the console gives), buffer runway vs. depth target, last top-up heartbeat, health check
  results (`health.run_checks` — read-only invocation), the story log panel (reuse the console's
  query), the cost rollup (costprobe's usage read), and the public feed as-written
  (`segments/nowplaying.json`).
- Auto-refresh (meta-refresh or polling) so it can sit open on a second monitor during the soak.

**Done when:** `make panel` serves the dashboard on `127.0.0.1:8787`; it renders with the DB up and
degrades readably (not a 500) with the DB down; binding to `0.0.0.0` without the escape hatch
refuses to start.

---

## E1.1 — The actions page (run the operational commands from the browser)

**Goal:** the `make` verbs an operator actually runs, as buttons — with output visible and the
destructive one kept scary.

**Do:**
- Actions: `seed-canon`, `seed-tracks`, `seed-sponsors`, `world-tick`, `schedule` (one top-up),
  `prune`, `fallback`, `health`, `ident`. Each runs the same module entrypoint the Make target
  runs (invoke in-process where clean, else `subprocess` of the exact command), streams/loads its
  output into the page, and records an action log line (who/when is trivial — single operator —
  but *what/when/outcome* matters for the devlog).
- Long-running actions (`world-tick` with batch on, `schedule`) run in a background task with a
  status view — the page never hangs on a 30-minute batch.
- `reset-world`: its own page, red, restating what it destroys (the §2a matrix summary), requiring
  the typed phrase `reset the world` before the button enables (principle #4).
- Concurrency guard: one mutating action at a time (a simple lock file / in-process lock) — the
  panel must not race the cron top-up; document that the cron keeps running and the panel's
  `schedule` button is a manual extra, not the driver.

**Done when:** each button runs its action and shows real output; two mutating actions can't
overlap; `reset-world` without the phrase is inert; the cron/systemd top-up is unaffected.

---

## E1.2 — The grid editor (the highest-pain YAML replaced first)

**Goal:** edit the weekly programming — programs, hosts, dayparts, clocks, `break_every`,
`guest_chance` — in forms, never in a YAML buffer.

**Do:**
- Read `docs/programming/grid.yaml` into an editable model: per-program cards (name, hosts,
  framing hint, clock steps, break/guest dials) + the weekly slot map.
- Validate on save by loading the candidate through `world/programming.py`'s real loader
  (principle #5); on failure, show the loader's error and DON'T write.
- Show a unified diff (current file → candidate) before the write — the operator confirms a diff,
  not a form state. Write atomically (tmp + replace). No seed needed: the grid is mtime-reloaded,
  note that on the success page.
- Keep a one-deep backup (`grid.yaml.bak`) on every write — cheap undo.

**Done when:** a host swap made in the browser shows in `make console` (and on air at the next
placement) without touching an editor; an invalid edit (unknown host id, malformed clock) is
rejected with the real loader error; the diff step is unskippable.

---

## E1.3 — Catalog editors: tracks, sponsors, pronunciation, voices

**Goal:** the four remaining config YAMLs become forms + their seed buttons.

**Do:**
- **Tracks** (`config/tracks.yaml` → `make seed-tracks`): list with playable-state (file on disk?
  duration probed?), add/edit/remove rows, `featured`/`pinned` toggles, licence note field
  surfaced prominently (the clearance call stays human). Save → validate via the seeder's parser →
  diff → write → offer the seed button.
- **Sponsors** (`config/sponsors.yaml` → `make seed-sponsors`): add/edit/remove, run-window date
  pickers, weight; the page hard-codes the display of the templated **"Powered by"** lead-in
  (never "Sponsored by" — MARKETING.md is binding) so the operator sees exactly what will air.
- **Pronunciation** (`config/pronunciation.yaml`, live-reloaded — no seed): name → phoneme/respell
  entries; a "test it" button that renders the name through `tts.synthesize` to a throwaway clip
  and serves it for listening (the mispronunciation loop closes in one screen).
- **Voices** (`config/voices.yaml`): per-DJ engine mappings; validate through the tts registry
  loader; warn (not block) when a cast id in the DB has no entry — and note seeding pre-validates.

**Done when:** each file round-trips form → diff → write → (seed where applicable) and the result
is audible/queryable; an invalid row is rejected by the same parser the seeder uses.

---

## E1.4 — The cast manager (DJs without editing markdown)

**Goal:** add / edit / retire a DJ — today a `90-cast.md` card + a `voices.yaml` entry +
`make seed-canon` — as one screen.

**Do:**
- List the cast from the DB (id, name, voice, tags) beside the parsed cards from
  `docs/canon/90-cast.md` — the file remains the source of truth (principle #1).
- Edit = a form over one card's sections (persona, way of speaking, sample lines, tags,
  `logical_voice`), written back into `90-cast.md` via the canon parser's own structure
  (round-trip through `world/canon_source.py`'s format, so a hand edit and a panel edit are
  indistinguishable in the diff).
- Add = card + a voices.yaml entry in one flow (E1.3's editor embedded), then the `seed-canon`
  button (safe scope — the living world survives, per §2a).
- Retire = remove from the card file + grid usage check (warn if the grid still schedules them —
  validated via the programming loader).

**Done when:** a new DJ created entirely in the browser seeds, validates against the voice
registry, can be slotted into the grid (E1.2), and speaks on the next placement; the file diff of
a panel edit is as clean as a hand edit.

---

## E1.5 — The dials page (the tagged `.env` groups, with effective values)

**Goal:** every dial group ADMIN_MANUAL tags for the panel — tick, news desk, freshness, figures &
quotes, talk continuity/flow, ad load, emotion, guests, DJ memory, embeddings, cache TTL,
music-selector weights — editable without opening `.env` in an editor.

**Do:**
- Group the settings by the manual's sections (the tags are the page map). For each dial: the
  current **effective** value (from the live `settings` object), the default (from
  `src/config.py`), and the `.env` override state (set / unset).
- Writes go to `.env` (comment-preserving line edit or an appended override block — pick one,
  document it), atomically, with the same diff-before-write habit.
- Be honest about restart semantics: `settings` is constructed at import — the page must say
  which consumers pick a change up live (grid/pronunciation-style mtime reloads) vs. on the next
  process start (scheduler cron picks it up next run; long-running `serve` needs a restart), and
  offer the relevant action (E1.1) beside the save.
- Guardrails: type/range validation from the pydantic field types; the `safety_enabled` and
  `disclosure_enabled` toggles carry a visible "production must stay ON" warning (CLAUDE.md).

**Done when:** a dial changed in the browser lands in `.env`, the page shows effective-vs-file
state truthfully, and the next scheduler run behaves per the new value.

---

## E1.6 — Tests + deployment + the manual updated (the capstone)

**Goal:** the panel is covered where a silent bug would hurt, deploys on the VPS as a private
service, and ADMIN_MANUAL.md points at it.

**Do:**
- Tests (surgical): loopback-bind refusal; the reset-world phrase gate; grid/tracks round-trip
  through the real loaders (valid in → identical semantics out; invalid in → rejected, file
  untouched); the `.env` writer preserves unrelated lines; the mutation lock.
- Deployment (extends C5's setup): a systemd unit binding `127.0.0.1:8787`, docs for the SSH
  tunnel one-liner; confirm from a second machine that the port is NOT reachable without the
  tunnel (this check goes into the C5/soak verification list).
- Update `docs/ADMIN_MANUAL.md`: each `→ Phase E panel` tag gains its panel screen reference
  ("Panel: Grid" etc.) while KEEPING the hand-edit how-to (the fallback path when the panel is
  down — principle #1). Update README (`make panel`), `.env.example` (`PANEL_*`), DEVLOG.
- Flip this pack's row in the Phase E tracker (create the tracker section in ROADMAP or a
  PHASE_E_OVERVIEW when a second E pack exists — don't build overview scaffolding for one pack).

**Done when:** `ruff` + `pytest` green; the panel runs on the VPS reachable only through the
tunnel; every tag in the manual names its screen; the manual's hand-edit paths still stand.

---

## Screen ← workflow map (the 22 tags, accounted for)

| Panel screen | ADMIN_MANUAL tags it serves |
|---|---|
| Dashboard (E1.0) | (read side — console/health/now-playing/cost, untagged) |
| Actions (E1.1) | seed-canon / reset-world / world-tick / prune / fallback / health runs referenced throughout |
| Grid (E1.2) | Edit the grid · What airs where (the dials) · Talk continuity / show flow (D12) · Tune the ad load (`break_every` half) |
| Tracks (E1.3) | Register / update a song |
| Sponsors (E1.3) | Manage sponsors ("Powered by" reads) |
| Pronunciation (E1.3) | Fix a mispronounced invented name |
| Voices (E1.3) | (half of) Add / edit / remove a DJ |
| Cast (E1.4) | Add / edit / remove a DJ · Edit the world bible (cast file) |
| Bible dials note (E1.5) | Edit the world bible* · Add a new cornerstone file* · Tag canon facts* |
| Dials (E1.5) | Tune the world tick · Tune the news desk · Tune freshness · Tune figures & quotes · Dials (programming) · Tune emotion · Guests / soundbites · DJ memory · Embeddings dials · cache TTL · Tune the ad load (env half) |

\* Bible **prose** editing stays a text-editor job in E1 by design (it's authorship, not
operation — and the human explicitly owns the bible). E1 covers the *cast* file (structured) and
the seed action; a full canon-folder editor is deferred (see below).

## Explicitly NOT in E1 (→ later Phase E packs / signals)

- **Story approve/reject queue + regen-per-story** — the tick stays autonomous-behind-gates
  (OVERVIEW: a per-story approval queue is a Phase E *opt-in*, only if the gated tick ever
  under-delivers). Needs its own pack with review UX.
- **A canon-folder prose editor** — bible authorship remains the human's text editor; revisit only
  if operating proves otherwise.
- **Listener inbound (Layer 0)** — its own Phase E workstream, through the safety gate, not a
  panel feature.
- **Multi-user auth / roles / public exposure** — never for this panel; a second operator is a
  Phase F-scale question.
- **Moving any source of truth into the DB** — standing rejection, not a deferral (principle #1).

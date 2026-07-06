# PHASE_D_ADMIN_MANUAL_TASKS.md — D11: Operator / Admin Manual (the capstone)

> Sub-pack **D11** of Phase D (see `docs/PHASE_D_OVERVIEW.md`) — the **closing capstone**: it produces one
> clean operator manual covering everything the admin (you, the single operator) does to run the station.
> Work in order, one task at a time: implement → show + how to verify → stop for review.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` (the whole surface); the living `docs/ADMIN_MANUAL.md` stub
> (each functional pack D1–D10 appended its admin how-tos here as it was built — this capstone
> **consolidates + simplifies + gap-fills + verifies** them); the existing `docs/HOWTO.md` (reconcile —
> see D11.0); `README.md`; `CLAUDE.md`.
>
> **Depends on:** **D1–D10 built** (it documents the *as-built* admin surface; written before they exist,
> it would be wrong). It also leans on the **C5** server basics for the "running the station" section.

**Why this is the capstone, and the style bar.** Phase D *is* the functionality, so the manual must
cover the complete surface — which is only knowable once it's built. The constraint (yours): **simple —
functionality + how-tos, NOT intro essays.** A cookbook/reference, not a narrative. Every entry is *what
it does* + *the exact command/file/steps*. If a section reads like prose, cut it.

**The trust bar — verify, don't just describe.** This manual is what you rely on when the station runs
unattended, so it is written from the **as-built** admin surface and **every how-to is verified by
actually running it** (the same discipline as the orientation docs + each pack's verification). A how-to
that hasn't been run is a guess.

**The panel handoff — the manual is also the Phase E requirements list.** Many Phase D admin operations
are deliberately file-based for now (edit a YAML/env file, re-run a seed): sponsors
(`config/sponsors.yaml` + `make seed-sponsors`), the grid + per-program ad-break cadence (`grid.yaml`
`break_every`), the cadence/production dials (`.env`), the tracks manifest, the canon bible. While
consolidating, KEEP the **`→ Phase E panel`** tag on every such hand-edit workflow (the packs tag them
as they append — see the ADMIN_MANUAL header convention) and gap-fill any untagged ones — the Phase E
control surface (ROADMAP "management / control surface") is built from exactly this list, so a missing
tag is a missing panel feature.

**Definition of done for D11:** one `docs/ADMIN_MANUAL.md` covering every admin operation across D1–D10
(+ the essential C5 run commands), in a terse how-to style, with each how-to verified against the running
local stack; `HOWTO.md` reconciled (one source, not two); linked from the README; **plus the integrated
24–48h acceptance simulation (D11.3) passing** (the OVERVIEW §4 Phase-D gate before the C9 live soak);
`ruff`/`pytest` green (the manual is docs-only; the acceptance harness adds code/tests).

> **Note — D11 has two halves:** the *operator manual* (D11.0–D11.2, D11.4, docs) and the *integrated
> acceptance simulation* (D11.3, a runnable harness). Both belong here because both can only run once the
> full D1–D10 surface is built. If you'd rather split them later, the simulation can graduate to its own
> sub-pack — but it stays gated on "everything built," same as the manual.

---

## D11.0 — Consolidate the captured how-tos + reconcile `HOWTO.md`
**Goal:** pull the per-pack fragments into one document and settle where the operator docs live.
**Do:**
- Gather the admin how-tos each functional pack appended to `docs/ADMIN_MANUAL.md` (D1–D10) into a single
  ordered draft. Drop duplication and any intro/narrative the packs carried — keep only *what it does +
  how*.
- **Reconcile with `docs/HOWTO.md`:** decide whether the operator manual *is* the grown-up HOWTO or
  supersedes it — there must be **one** operator source, not two. If HOWTO.md is dev-focused (build/run
  the repo), keep it for *development* and make ADMIN_MANUAL.md the *operating* guide; cross-link, don't
  duplicate. Document the split in one line at the top of each.
**Done when:** a single consolidated draft exists; HOWTO.md vs ADMIN_MANUAL.md roles are settled and
cross-linked; no duplicated how-tos across the two.

## D11.1 — Structure the manual by operator task (terse, how-to-first)
**Goal:** the operator finds "how do I X" in seconds; nothing reads like an essay.
**Do:**
- Organise by **what the operator does**, not by sub-pack. Suggested sections (each = a short list of
  how-tos, each how-to = goal + exact command/file/steps):
  - **Running the station** — start/restart/stop; where it runs (VPS); the jobs (scheduler top-up, the
    world tick) and how they're scheduled; check it's alive (`make health` / the status console).
    *(Pulls the essential C5 commands — keep to the operator essentials, not a server-build treatise.)*
  - **Seeding & the world** — the seed modes (full reset vs **canon refresh** vs **`seed-grid`**) and
    *when to use which* (the load-bearing one: a bible edit is a canon refresh, **never** a world wipe);
    run the world tick; what persists vs resets.
  - **Authoring the bible** — edit `docs/canon/` (the cornerstone files, the conventions), tag facts,
    add/edit/remove a DJ (cast file + voice mapping), → re-seed (canon refresh).
  - **Programming the grid** — edit the grid YAML (programs, dayparts, clocks, hosts), dedicated music
    blocks vs interspersed, pinned slots → reload/`seed-grid`.
  - **Music & culture** — register a track (drop file + write lore), the playable-vs-culture line,
    artists as figures, how the selector picks.
  - **Commercials & sponsors** — the generated spots, the break cadence dial, add a sponsor ("Powered
    by", run window), the production levels.
  - **Voice** — the lexicon (fix a pronunciation), emotion (flagship only), guests/soundbites.
  - **Status & monitoring** — the read-only console, now-playing, health alerts, where logs are.
  - **Recovery** — restore from backup; what to do if the buffer drains / a job fails / the tick goes
    wrong; the never-dead fallback (it self-heals — what to check).
  - **Admin access & security** — how *you* reach the controls (SSH/CLI in Phase D; the private VPS-only
    panel in Phase E), single-operator, secrets in `.env` non-world-readable — the private-admin boundary.
- Keep a one-line "what this is" at the very top and nothing else introductory. Use tables/command blocks
  over paragraphs.
**Done when:** the manual is task-organised; every section is how-tos (goal + exact steps), not prose; a
reader can answer "how do I X" by scanning headings.

## D11.2 — Verify every how-to against the running stack + fill gaps
**Goal:** nothing in the manual is a guess.
**Do:**
- **Run each how-to** on the seeded local stack (commands, file edits, seed modes, the tick, grid reload,
  track registration, console, a simulated recovery). Fix any command/flag/path that doesn't match the
  as-built code. Where a how-to needs the flagship voice or the VPS (emotion, deploy), mark it clearly and
  verify what *can* be verified locally.
- **Fill gaps** the per-pack fragments missed — any operator action that exists in the built code but
  isn't documented (grep the Makefile targets + the `python -m src.*` CLIs as a checklist; every operator
  entry point must appear in the manual).
- Confirm the **dangerous operations are flagged** (`make reset-world` wipes the world — vs the safe
  everyday `make seed-canon`; removing a DJ; clearing sponsors) with the safe alternative next to them.
**Done when:** every how-to has been executed (or explicitly marked flagship/VPS-only) and corrected; no
Makefile/CLI operator entry point is undocumented; destructive operations carry a warning + the safe path.

## D11.3 — Integrated acceptance simulation (the Phase-D gate)
**Goal:** prove the whole pipeline holds together over time — not just per-pack unit tests — before the
C9 live soak. (This is the OVERVIEW §4 acceptance gate; D11 is its home since it runs last, on the full
built surface.)
**Do:**
- Build a **runnable 24–48h simulation harness** (an accelerated clock; needs `make seed-canon` + a
  populated `.env`; mock or budget the live calls): drive **tick → news → freshness → grid →
  music/commercials** across the window, writing a real schedule + world.
- **Assert the integration properties** (the things only an end-to-end run catches):
  - **No dead gaps** — the schedule has continuous audio (the never-dead chain never needed to fire for a
    *generation* gap);
  - **No repetition loops** — talk beats, openings, news wording, and song/artist picks don't cycle (D5 +
    the news coverage + the track selector actually working together);
  - **Stories evolve** — running stories advance through their arc with correct past/now/future framing
    across the window (D3 + D4);
  - **Cost stays bounded** — the telemetry rollup over the window is within an expected envelope (no
    runaway regeneration / call storms);
  - **Schedule output is sane** — durations measured, ordering correct, program clocks honoured, idents/
    breaks placed as configured.
- Make it a **repeatable check** (a `make` target / test harness) so it can be re-run after changes and
  before the C9 soak; log a pass/fail summary per property.
**Done when:** the simulation runs end-to-end and all five properties pass (or fail loudly with a
specific reason); it's repeatable; the result is logged/summarised.

## D11.4 — Link, polish, lock the style
**Goal:** the manual is discoverable, consistent, and stays terse.
**Do:**
- Link `docs/ADMIN_MANUAL.md` from the `README.md` (and from `docs/PHASE_D_OVERVIEW.md`'s footer) so it's
  found. Add a DEVLOG entry (Phase D — D11).
- Final style pass: cut any remaining intro/justification text; ensure consistent command formatting;
  one-line section preambles max. Add a short **changelog/last-verified date** at the top so its freshness
  is visible.
- Add a note: **re-verify at the soft launch (CM)** — when unattended operation begins, re-run the how-tos
  and bump the last-verified date.
**Done when:** the manual is linked from README + overview; terse and consistent; carries a last-verified
date; the CM re-verify reminder is in place.

---

## Explicitly NOT in D11 (→ elsewhere)
- **Building any admin functionality** → the functional packs **D1–D10** (D11 only *documents* what they
  built; if a how-to can't be written because the feature is awkward, fix the feature in its pack).
- **The Phase E web admin panel + its security build** → **Phase E** (D11 documents the *Phase D* surface —
  files/CLI/SSH — and notes the panel is coming, private + single-operator).
- **The full server build/deploy runbook** → **C5** (D11's "running the station" section is the operator
  essentials — start/restart/backup/health — not the from-scratch provisioning).
- **Developer/build docs** → `README.md` / `docs/HOWTO.md` (reconciled in D11.0) — the manual is for
  *operating*, not *building the repo*.

# ADMIN_MANUAL.md — operator how-tos (living draft)

> A running cookbook of *what an operator does* to run Settlement Radio. Each Phase D sub-pack
> appends its how-tos here as it's built (terse: what it does + the exact command/file/steps); the
> **D11 capstone** consolidates, simplifies, gap-fills, and verifies this into the final manual. Until
> then this is an append-only draft — keep entries short and command-first.

---

## D1 — The canon bible (`docs/canon/`)

**What it is.** The world bible is the [`docs/canon/`](canon/) folder of cornerstone markdown files —
the hand-authored *static substrate* the world is seeded from. The authoring contract (layout,
conventions, fact-id scheme, tags) is [`docs/canon/README.md`](canon/README.md). The DB is the
queryable projection; the folder is the source of truth.

### Edit the world bible
1. Edit / add files under `docs/canon/`. Filenames are `NN-stem.md` — `NN` sets reading order
   (sorted numerically; gaps are fine), `stem` names the file's facts (`canon-<stem>-N`).
2. Inside a file, three `## ` headings are special: `## Canon facts` (numbered list → facts),
   `## Cast` (`### Name` cards → DJs, in `90-cast.md`), `## Events` (`### Title` → timeline, in
   `95-events.md`). **Every other `## ` heading is narrative "series-bible" prose** the DJs read.
3. Required fields: each cast `### ` needs `- **Logical voice:**`; each event `### ` needs
   `- **In-world datetime:**` (ISO, in-world year = real + 600). Missing → seed fails loud.
4. Reload: `make seed-canon`.

### Add a new cornerstone file
Drop a new `NN-stem.md` in `docs/canon/` (unique stem). Scaffold files ship with guidance above the
first `## ` heading and an empty `## Canon facts` — they seed nothing until authored (see
`docs/canon/README.md` §7). Author by adding `## Topic` prose + a `## Canon facts` list, then
`make seed-canon`.

### Seed / refresh the world  ⚠ two commands
- **`make seed-canon`** — the SAFE everyday command. Reloads folder-owned `canon`/`cast`/bible and the
  `source='seed'` events, **leaving the living, tick-generated world (`source='tick'` events) intact**.
  Idempotent — run it after every bible edit. (`make seed` is a back-compat alias for this.)
- **`make reset-world`** — DESTRUCTIVE. Wipes the whole world+canon set (incl. tick-generated events)
  and rebuilds from the folder. Prompts: type `reset-world` to confirm (or pass `--force`
  non-interactively: `python -m src.world.seed reset --force`). **Never** touches station
  config/catalog (grid/tracks/sponsors).

### Point at a different bible (config)
`CANON_DIR` (folder, default `docs/canon`) and `CANON_PATH` (legacy single file, fallback). Seeding
auto-selects the folder when it has content, else the file. Set in `.env` only to relocate the bible.

### Verify a seed
```bash
make seed-canon          # logs per-table counts (canon / cast / events / state)
make context             # prints the assembled cached bible + dynamic now (no DB writes)
make demo                # event progression: "in five days" -> "yesterday"
```
To confirm tick-safety by hand: insert a `source='tick'` event, run `make seed-canon`, confirm it
survives; `make reset-world` clears it.

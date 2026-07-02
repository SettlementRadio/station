# docs/programming/ — the weekly programming grid (Phase D / D6.0)

> **This folder is the human-editable source of truth for the station's *schedule of shows*.** You
> hand-edit `grid.yaml` — named programs, their hour-clocks, their hosts, and the weekly tiling that
> says which show airs when — and a scoped seed (`make seed-grid`, D6.0-decided, built in D6.2) projects
> it into the `programs` + `program_grid` DB tables the scheduler reads. The workflow mirrors the bible
> loop: **edit the file → re-seed → live.** (This is *structured data*, so it is YAML, not the prose
> markdown the bible under `docs/canon/` uses.)

This README is the **D6.0 design decision, written down**: the data model (Program · Clock · grid
slot), where the grid lives (DB-table path), how it subsumes `src/world/framing.py`, and the default
program that guarantees the scheduler never stalls. D6.1–D6.5 are written against exactly this model.

---

## 1. What this replaces

Today the scheduler airs a **flat rotation** — `settings.buffer_rotation = ["talk", "news"]`, cycled
`rotation[rot_i % len(rotation)]` regardless of the hour — and `src/world/framing.py` frames every talk
segment off a **hardcoded** night/dawn/dusk handover between two hardcoded hosts (`vell`/`wren`). That
is "a folder of clips on a flat rotation."

D6 turns that into "a programmed station": a **weekly grid** maps each in-world weekday/hour to a
**named program** with its own format sequence, hosts, and framing; the scheduler consults the grid at
the air-cursor instead of `% len(rotation)`; framing is driven by the active program (N hosts, not two
hardcoded). The in-world wall clock **equals** the real wall clock (the world clock shifts the *year*
only — `settings.world_years_ahead`; `clock.render_wall_clock`), so grid slots are plain weekday + hour
ranges.

---

## 2. The data model — three entities

### 2.1 Program — a named show

A `Program` is a named show (e.g. *The Long Night*, *First Light*, *Daywatch*) carrying:

| Field | Meaning |
|---|---|
| `id` | stable slug, unique across the grid (e.g. `long_night`) — the seed idempotency key |
| `name` | display name for the console + now-playing feed (*"The Long Night"*) |
| `hosts` | ordered list of **cast ids** (from `docs/canon/90-cast.md`; today `vell`, `wren`; the bible already defines `joss`, `kael`, `mira`, `thorn`, `sera`, `the-archivist`, `orin`, `zhe` for D9). Order is meaningful: `hosts[0]` is the lead/anchor. |
| `framing` | how the room frames the show: `solo` (one anchor + optional companion), `handover` (an outgoing→incoming boundary show), `ensemble` (≥2 co-hosts, later), or `legacy` (reserved for the `default` program — the hour-derived night/dawn/day/dusk frame, `framing.show_frame`). This is the generalised replacement for framing.py's hardcoded handover flag. |
| `daypart` | an **optional display label** for the console + now-playing feed (*The Long Night*, *First Light*…). It does **not** override the frame's `part_of_day`, which stays hour-derived (see §6) so a program spanning morning→evening still frames each hour correctly and the two-host tests keep exact parity. |
| `clock` | the format **sequence** (see §2.2) — the load-bearing piece. |

A program does **not** own its air-times; the **grid** (§2.3) places it. One program can tile many slots
(e.g. `daywatch` fills every weekday 07:00–17:00).

### 2.2 Clock — how a program sequences its formats (the load-bearing piece)

Borrowed from real-radio "hour clocks." A weighted *ratio* alone can't tell **"a 3-song sweep, then a
break, then talk"** from **"one song between every chat"** — so a clock is an **explicit sequence with
run-lengths**, authored as a list. Each step is one of:

- **a format name** — `talk`, `news`, `music` (the `formats.FORMATS` registry keys; `music` comes online
  in D7, so today's live clocks use `talk`/`news`);
- **a run-length** — `music x3` (equivalently `music*3`) → air that format N times in a row. This is
  exactly what expresses a *dedicated music block* (`music x8`) vs *music interspersed* (`talk, music,
  talk`);
- **a pinned step** — `news@:00` → this format is **pinned to the top of the hour**: when the air-cursor
  crosses `:00` the scheduler airs it regardless of where the sequence otherwise sits, then resumes the
  sequence. (General form `format@:MM`.)
- **a sound-design marker** — `sting` (and later `bed`, `ident`): a Layer-4 production element. **In D6
  these are inert placeholders** the scheduler skips (they carry no `formats` builder yet); **D7** wires
  them to real audio. Authoring them now means the clocks don't need rewriting when D7 lands.

The scheduler walks the clock with a **per-program cursor** (persisted in `schedule.json`, D6.2) so the
sequence advances correctly across top-up runs and resumes sensibly across program boundaries.

**Fallback:** a program that defines **no** `clock` falls back to a **weighted rotation** — a plain list
that is simply cycled (the current flat behaviour). This is what the **default program** (§5) uses.

Example clocks:

```yaml
# a dedicated overnight music-and-talk block: a 3-track sweep, a sting, talk, top-of-hour news
clock: [talk, music, music, music, sting, talk, news@:00]

# music interspersed one-between-each (the "music in between" model)
clock: [talk, music, talk, music, talk, news@:00]

# today's talk/news-only daytime clock (no music until D7); news pinned to the hour
clock: [talk, talk, news@:00]

# no clock at all -> weighted-rotation fallback
rotation: [talk, talk, news]
```

### 2.3 Grid slot / daypart — the weekly tiling

A grid **slot** maps `(weekday-range, time-range) → program id`. The grid must **tile the week with no
gaps** — every hour of every weekday resolves to exactly one program (the default program, §5,
backstops any hole). Because the in-world wall clock = the real wall clock, slots are plain weekday +
`HH:MM-HH:MM` ranges. A range may wrap past midnight (`22:00-05:00`), read as "from the start hour to
the end hour the next day."

Weekday ranges use short names: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`, ranges (`mon-fri`), and
the aliases `weekdays` (mon–fri) / `weekends` (sat–sun) / `daily` (all seven).

---

## 3. The `grid.yaml` shape

```yaml
programs:
  long_night:                 # <- program id (slug)
    name: "The Long Night"
    hosts: [vell]
    framing: solo
    daypart: deep night
    clock: [talk, talk, news@:00]

  first_light:
    name: "First Light"
    hosts: [wren, vell]       # hosts[0]=incoming lead, hosts[1]=outgoing companion
    framing: handover
    daypart: first light
    clock: [talk, news@:00]

grid:                         # the weekly tiling — weekday range -> time range -> program id
  weekdays:
    "22:00-05:00": long_night
    "05:00-07:00": first_light
    "07:00-17:00": daywatch
    # ...tiles to 24h with no gaps
```

See [`grid.yaml`](grid.yaml) for the full initial week (backward-compatible with the two current hosts).

---

## 4. Where the grid lives — the YAML is the source of truth, behind `program_for`

`grid.yaml` is the human-edited, git-versioned **source of truth** — that never changes. The only
open question is whether a DB *copy* exists, and both paths sit behind one seam: **`program_for(now)`**
(`src/world/programming.py`) is the single reader; nothing else touches the grid. So the storage can
evolve without any caller changing.

- **Phase D (as built): the config-file read.** `program_for` reads `grid.yaml` directly — an
  mtime-cached parse, so an operator edit is picked up on the next load, no restart, no DB, no SQL. This
  is all the running station needs: the human edits the file, the scheduler reads it (D6.1/D6.2).
- **Phase E (deferred): the DB-table projection.** When the **web grid editor** (drag-the-grid, no file
  editing — a private, VPS-only single-operator surface) arrives, it needs a table to write to. At that
  point `grid.yaml` becomes a **seed manifest** and a scoped **`make seed-grid`** projects it into
  `programs` + `program_grid` tables in `src/world/store.py` (all SQL behind the seam), added **behind
  the same `program_for`** — an additive migration (idempotent `CREATE TABLE IF NOT EXISTS`, an
  upsert of the grid rows), never a truncate-reseed. The OVERVIEW §2a matrix already reserves this row
  (`programs`/grid owned by the YAML manifest, refreshed by `seed-grid`, scoped so **`reset-world`
  leaves the grid alone** — it is config, not world; git is its backup).

The decision, then: **the YAML is authoritative in both phases; the DB is an additive projection built
only when Phase E's editor needs a write target.** We don't pay for a seeder + schema the running
station doesn't use yet — but nothing about reading the file now precludes it, because everything goes
through `program_for`. In Phase D the human **only ever edits the file** — never raw SQL, never a web UI.

---

## 5. The default program — no slot ever stalls

If the grid tiles the week correctly there is no gap, but the scheduler must **never** stall on a
lookup miss. So a reserved program id **`default`** always exists:

- its clock is the **weighted-rotation fallback** seeded from `settings.buffer_rotation` (today
  `["talk", "news"]`), and its hosts are `settings.convo_speaker_ids` (`["vell", "wren"]`);
- its framing is `legacy` — the **hour-derived** frame (§6: `framing.show_frame`, the night/dawn/day/
  dusk handover), so a fallback slot behaves exactly like today's flat rotation. `program_for` even
  **synthesises** this program from `settings` when the grid file is missing entirely, so an absent
  `grid.yaml` still yields today's behaviour;
- `program_for(now)` returns `default` whenever no grid slot matches the datetime.

This makes `default` both the safety net *and* the on-ramp: with an empty grid the station behaves
exactly as it does today.

**Relationship to `settings.buffer_rotation`:** when programming is on (the default), it stops being
the scheduler's rotation and becomes **only the default program's fallback clock** — a single source of
truth, not two silently fighting. The grid supersedes it for every slot that matches a program (once
the grid tiles the week, all of them). The master switch `settings.programming_enabled` is the clean
rollback: set it `false` and the scheduler airs the flat `buffer_rotation` exactly as it did pre-D6
(D6.2). The scheduler carries the per-program clock cursors (`seq`/`rot`) plus one global top-of-hour
cursor in `schedule.json` (`clock_state`), so sequences and pins advance correctly across top-up runs.

---

## 6. How this subsumes `src/world/framing.py`

`framing.show_frame(now, *, night_host, day_host)` today hardcodes two hosts and its dawn/dusk handover
windows as module constants. D6.1 generalises it so **the program drives the frame**:

- `src/world/programming.py` adds `program_for(now) -> Program` (reads the grid; §4).
- `show_frame` is generalised to derive `ShowFrame(part_of_day, lead, companion, is_handover,
  situation)` from **the program** — its `hosts` (N, ordered; `lead = hosts[0]`, `companion = hosts[1]`
  if present) and its `framing` hint (`solo`/`handover`/`ensemble` → `is_handover`, and the situation
  prose) — instead of the two hardcoded `night_host`/`day_host`. It stays **pure and stateless** (hosts
  passed in, no I/O) so it unit-tests like `clock.py`/`events.py`.
- **`part_of_day` stays hour-derived** (the existing deep/late-night, morning/afternoon/evening,
  first-light/nightfall cutoffs). This is deliberate: it is finer-grained than a program slot (one
  `daywatch` program spans morning→evening) and keeping it hour-derived is what preserves exact frame
  parity for the two-host tests. The program supplies *who* is on air and *whether it's a handover*; the
  hour supplies *what part of day it is*. (The program's optional `daypart` is only a display label.)
- The old **dawn/dusk handover** becomes the framing of the **boundary programs** (`first_light`,
  `nightfall`): a `handover` program at the night→day and day→night edges is exactly the old transition.
- **Backward compatibility is a hard requirement:** with the initial two-host grid (§ `grid.yaml`) the
  generalised frame must yield the *same* frames the current `show_frame` produces, so the existing
  framing tests and the D1–D5 writers'-room path (`conversation.compose_segment` → `_frame_for`) work
  unchanged. `_frame_for` is fed the program-derived hosts/frame instead of the constant pair.

The **default program** keeps the legacy hour-derived situation (§5) so no configured grid still frames
correctly.

---

## 7. Config dials (added in D6.1/D6.2, `# --- Programming (D6) ---` section)

Per the config-over-hardcoding standard, tuning is exposed via `settings`, not literals:

- `programming_grid_path` — path to this folder's `grid.yaml` (source manifest for `seed-grid`).
- `programming_default_program` — the reserved fallback program id (default `"default"`).
- `programming_enabled` — master switch; off = fall back to today's flat `buffer_rotation` (a clean
  rollback path).
- console dials (D6.3) — e.g. how many upcoming entries the status console prints.

---

## 8. Authoring workflow (the operator loop)

1. Edit `docs/programming/grid.yaml` (add/rename a program, retune a clock, move a slot).
2. Run **`make seed-grid`** (scoped: only the grid tables; never the world). *(Built in D6.2.)*
3. The next scheduler `top_up` reads the refreshed grid and airs it.

Full grid *management* (drag-the-grid editing, CRUD DJs) is **Phase E**; in Phase D you edit this file.
D6's console + feed are **read-only**.

---

## 9. What D6.0 does **not** decide (→ later D6 tasks)

- `program_for(now)` + the generalised `show_frame` implementation → **D6.1**.
- Rewiring `scheduler.top_up` to walk the clock + the persisted per-program clock cursor → **D6.2**.
- The read-only status console → **D6.3**; the public now-playing feed → **D6.4**; tests + demo → **D6.5**.

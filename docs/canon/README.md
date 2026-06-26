# docs/canon/ — the Settlement Radio world bible

> **This folder is the human-editable source of truth for the world.** You write prose here; the
> seeder (`make seed-canon`) reads the *whole folder* and projects its hard, queryable facts into the
> database, while keeping the narrative prose as the cached "series bible" the writers' room reads.
> There is **no second machine-readable copy** — this folder is it. (Phase D / D1. Supersedes the old
> single-file `docs/CANON.md` stub.)

This README is the **authoring contract**: the layout, the section conventions, the field-bullet
convention, the fact-id scheme, and the per-fact tag affordance. The parser
(`src/world/canon_source.py`) is written against exactly these conventions, so if you follow them your
prose loads cleanly; if you break them the seed fails loud (a missing required field raises, rather
than silently dropping content).

---

## 1. The folder layout (cornerstone files)

The bible is split into **cornerstone files**, one per domain of the world. Each filename carries a
**numeric prefix** that sets the *reading order* — the seeder loads `*.md` sorted by that prefix **as
an integer**, so the assembled series bible reads top-to-bottom the way these are numbered. Leave gaps
in the numbering (00, 01, 10, 20…) so you can slot new files between existing ones without renumbering.

The prefix can be **any width** — `2`, `20`, `100`, `250` all work, and they order numerically
(`2 < 20 < 100`), *not* as strings, so a wide number never sorts to the wrong place. **Add as many
files as you like;** the only rule is that each file's *stem* (the name after the prefix, see §4) is
unique across the folder. A new `100-alien-races.md` is exactly the intended way to grow the world.

| File | Domain | Contains |
|---|---|---|
| `00-station.md` | The station's identity | bible prose + `## Canon facts` |
| `01-time.md` | The +600y time concept | bible prose + `## Canon facts` |
| `10-history.md` | History of the settled worlds | bible prose + `## Canon facts` |
| `20-nations.md` | Nations / polities / powers | bible prose + `## Canon facts` |
| `25-peoples.md` | Peoples & aliens | bible prose + `## Canon facts` |
| `30-geography.md` | Worlds, routes, the relay-space between | bible prose + `## Canon facts` |
| `40-war.md` | Conflicts, treaties, the military | bible prose + `## Canon facts` |
| `50-finance.md` | Economy, trade, currency | bible prose + `## Canon facts` |
| `60-religion.md` | Faiths, rites, the sacred | bible prose + `## Canon facts` |
| `70-culture.md` | Daily life, customs, festivals | bible prose + `## Canon facts` |
| `75-literature.md` | Letters, stories, the genre tribute | bible prose + `## Canon facts` |
| `80-tech.md` | Technology, the relays, travel | bible prose + `## Canon facts` |
| `90-cast.md` | **The DJs** | `## Cast` (projects to `cast` rows) |
| `95-events.md` | **The world timeline** | `## Events` (projects to `events` rows) |

**You do not need every file to exist** — the seeder loads whatever `*.md` files are present. Start
with the migrated stub (D1.3 fills `00`, `01`, `90`, `95`) and grow the cornerstone files over the
phase. The two **structured** files — `90-cast.md` and `95-events.md` — keep their own files because
their whole purpose is to project to rows; keep cast in cast and events in events.

> The world's *moving present* (generated stories/events from the nightly tick, arriving in D3) is
> **not** authored here — it's dynamic DB state you never hand-edit. This folder is the *static
> substrate*. A `seed-canon` re-load refreshes this folder's content **without** wiping tick state.

---

## 2. Section conventions — structured vs. series bible

Every cornerstone file is a normal Markdown document. The parser splits it on `## ` (H2) headings and
treats each section as one of two kinds:

### Structured sections (projected into database rows)

Exactly three H2 headings are **structured** — their content becomes queryable rows:

- **`## Canon facts`** — a numbered list; each item becomes a `CanonFact` row. (May appear in any
  cornerstone file — that's how a file carries both narrative *and* its hard facts.)
- **`## Cast`** — `### Name — role` subsections; each becomes a `CastMember` row. (Lives in
  `90-cast.md`.)
- **`## Events`** — `### Title` subsections; each becomes an `Event` row. (Lives in `95-events.md`.)

The heading is matched loosely: anything after a ` — ` / ` - ` / `(` is ignored, so
`## Canon facts (keep small)` and `## Cast — the DJs` still key as `canon facts` / `cast`.

### Series-bible sections (cached narrative prose)

**Every other `## ` section** is *series bible* — slow-changing world-description prose that is **not**
projected to rows. The seeder concatenates these (preserving their `## ` headings) into the cached
"series bible" that `context.assemble` feeds the writers' room as stable, cacheable context.

This means: **write freely.** Any new `## Some Domain` section you add to any cornerstone file is
automatically picked up as bible prose — you don't register it anywhere. Only the three structured
heading names above are special.

A single file routinely contains **both**: a narrative body (`## History of the long quiet`, prose)
*and* a `## Canon facts` list of that file's hard, queryable facts. Put the discursive worldbuilding in
prose sections; reserve `## Canon facts` for short, atomic, checkable statements the writers must stay
consistent with.

---

## 3. The field-bullet convention

Inside the structured subsections (cast members, events) and on facts that carry tags, fields use a
single bullet line:

```
- **Field name:** value
```

The field name is **case-insensitive**. The value runs to end of line. This is the one convention the
parser keys on for every field, so keep the `- **`…`:**` shape exact (a bullet, bold field name, colon
*inside* the bold, then the value).

**Cast** (`### Name — role`) recognises:

- `- **Logical voice:** vell_night` — **required** (maps to the TTS voice registry); missing → seed fails loud.
- `- **Tags:** night, warmth, stories` — optional.
- The whole subsection body is also kept verbatim as the DJ's `card_text` (so the writers' room gets
  the full character card — personality, verbal tics, sample lines, all of it).

**Events** (`### Title`) recognises:

- `- **In-world datetime:** 2626-06-24T20:00` — **required**, ISO 8601; missing → seed fails loud.
  (In-world year is `real year + 600`; a `2626` date is the in-world face of `2026`.)
- `- **Status:** upcoming` — optional (defaults to `upcoming`).
- `- **Tags:** festival, lights, music` — optional.
- `- **Body:** …` — the event description the DJs read.

---

## 4. The fact-id scheme (globally unique, stable across re-seeds)

Each canon fact gets a database id of the form:

```
canon-<file-stem>-<n>
```

- **`<file-stem>`** is the filename with its numeric prefix and `.md` extension stripped:
  `10-history.md` → `history`, `00-station.md` → `station`. (So a fact in `10-history.md` ids as
  `canon-history-3`.)
- **`<n>`** is the fact's 1-based position **within that file's** `## Canon facts` list.

This makes ids **globally unique across files** (the old per-call `canon-1, canon-2…` numbering
collided once there was more than one file) and **stable across re-seeds** (the same fact in the same
position keeps the same id), which is what makes a re-seed idempotent.

**Authoring consequence:** ids are derived from *filename + position*, so **inserting a fact in the
middle of a file shifts the ids of every fact below it.** For the static bible that's fine (re-seed
re-derives them). Avoid renaming a cornerstone file casually — it renames every fact id in it. Each
file's stem must be **unique** across the folder.

Cast and event ids are **slugs of the name/title** (`Lumen Festival` → `lumen-festival`), already
stable. The parser **fails loud on a duplicate slug across files** (two cast members or two events that
slug to the same id), the same way it fails on a missing required field — so a collision is caught at
seed time, not silently merged.

---

## 5. The per-fact tag affordance

Facts may carry **tags** so D2 (semantic retrieval) can match canon by topic. The format **supports**
tags now; **populating** them is D2's job — until then most facts will have none, and an untagged fact
parses to an empty tag list (`[]`), never an error.

A tagged fact uses an indented `- **Tags:**` child bullet directly under the numbered item, reusing
the same field-bullet convention as cast/events:

```markdown
## Canon facts

1. Humanity lives across many settlements; Earth is distant history, spoken of fondly.
   - **Tags:** earth, history, diaspora
2. Travel between worlds takes weeks; radio is the thread that connects them.
3. "Settlement time" is the shared clock everyone tunes to.
   - **Tags:** time, ritual
```

- The tags line is **optional**. Facts 2 above has none → `tags: []`.
- Tags are comma-separated; surrounding whitespace and backticks are stripped.
- The `- **Tags:**` bullet is consumed as tags, **not** folded into the fact's prose text — the stored
  fact text stays clean (a wrapped fact that continues onto an un-bulleted next line still joins into
  one fact as before).

We chose the child-bullet form (over an inline `` tags: `a,b` `` suffix) so tags read the same way
everywhere in the bible — one `- **Field:** value` convention for facts, cast, and events alike.

---

## 6. Authoring checklist

- Put prose in plain `## Section` headings — it's bible context automatically.
- Put atomic, checkable facts in a `## Canon facts` numbered list (any file).
- Keep `## Cast` in `90-cast.md`, `## Events` in `95-events.md`.
- Give every cast member a `- **Logical voice:**`; every event an `- **In-world datetime:**`.
- One unique file-stem per file; don't rename files casually (it renames fact ids).
- Tags are optional and D2 will fill most of them — don't block on tagging.
- After editing, run **`make seed-canon`** (the safe, everyday reload). It refreshes this folder's
  canon/cast/bible and leaves the living, tick-generated world untouched. Use **`make reset-world`**
  (destructive, warns + confirms) only for a deliberate full world wipe.

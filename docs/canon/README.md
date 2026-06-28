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

> **Writing the world? Start with [`SPIRIT.md`](SPIRIT.md)** — the creative brief: the idea, the
> 20th-century SF tradition we honour, the authors we draw on, and the core themes to build (plus the
> hard IP rule: tribute, never derivative). Then this README for *format*, and [`TAGS.md`](TAGS.md)
> for the tag palette. These three are **authoring guides, not world content** — the seeder skips
> them (they carry no numeric prefix), so they never reach the DJs.

---

## 1. The folder layout (cornerstone files)

The bible is split into **cornerstone files**, one per domain of the world. Each filename carries a
**numeric prefix** that sets the *reading order* — the seeder loads `*.md` sorted by that prefix **as
an integer**, so the assembled series bible reads top-to-bottom the way these are numbered. Leave gaps
in the numbering (00, 01, 10, 20…) so you can slot new files between existing ones without renumbering.
**Only numeric-prefixed files are loaded** — a file without a prefix (`README.md`, `SPIRIT.md`,
`TAGS.md`, `AUDIT.md`) is an authoring *guide*, not world content, and the seeder skips it. So you can
keep notes and briefs in this folder freely; just don't give them a number.

The prefix can be **any width** — `2`, `20`, `100`, `250` all work, and they order numerically
(`2 < 20 < 100`), *not* as strings, so a wide number never sorts to the wrong place. **Add as many
files as you like;** the only rule is that each file's *stem* (the name after the prefix, see §4) is
unique across the folder. A new `100-alien-races.md` is exactly the intended way to grow the world.

The folder ships with a full set of cornerstone files. **Four are authored** (the migrated stub);
the rest are **scaffolds** — header + authoring guidance only, no world content yet, so they seed
nothing until you fill them (see §7).

| File | Domain | State |
|---|---|---|
| `00-station.md` | The station's identity + premise facts | **authored** |
| `01-time.md` | The +600y time concept | **authored** |
| `05-worlds.md` | The settled worlds & the dark between (the "map") | scaffold |
| `10-history.md` | Deep time: Earth, the diaspora, the ages | scaffold |
| `20-peoples.md` | The branches of humanity | scaffold |
| `25-other-minds.md` | Aliens, machine minds, the unknown (your call) | scaffold |
| `30-polities.md` | Governance & nations across distance | scaffold |
| `35-economy.md` | Trade, scarcity, currency | scaffold |
| `40-law.md` | Law & justice at a distance | scaffold |
| `45-conflict.md` | War & peace across weeks | scaffold |
| `50-daily-life.md` | The texture of ordinary life | scaffold |
| `55-language.md` | Tongues, drift & fossil-words | scaffold |
| `60-faith.md` | The sacred & the search for meaning | scaffold |
| `65-arts.md` | Story, image & the cultural memory (the tribute's home) | scaffold |
| `70-music.md` | Music as a living culture (song lore → D7) | scaffold |
| `75-technology.md` | The made world & its limits | scaffold |
| `78-communication.md` | The relays & how word travels (premise-critical) | scaffold |
| `80-cosmos.md` | The universe & the wonder (science, the sublime) | scaffold |
| `90-cast.md` | **The DJs** | `## Cast` → `cast` rows |
| `95-events.md` | **The world timeline** | `## Events` → `events` rows |

This set is a *suggestion*, not a schema — rename, drop, merge, or add files freely (only the stem
must be unique). The two **structured** files (`90-cast.md`, `95-events.md`) keep their own files
because their whole purpose is to project to rows; keep cast in cast and events in events.

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

Facts may carry **tags** so the writers' room can match canon by topic (D2 — they complement
semantic recall). The **recommended tag vocabulary** (the palette to pick from + the lowercase
single-word naming rule) lives in [`TAGS.md`](TAGS.md) — read it before tagging. Tags are optional:
an untagged fact parses to an empty tag list (`[]`), never an error.

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

---

## 7. Scaffold files — how to fill one in

Most cornerstone files ship as **scaffolds**: a header plus authoring guidance (what the domain is
for, building blocks to consider, the tone/tribute), but **no world content yet**. A scaffold is
deliberately *invisible to the seeder* — all its guidance sits **above the first `## ` heading**, and
its only section is an empty `## Canon facts`. Since the series bible is "every `## ` section that
isn't structured" (§2) and content before the first `## ` is dropped, a scaffold contributes **zero
rows and zero bible prose**. It's a brief for you, not world data.

To bring one to life, author *below* the guidance:

1. Add one or more narrative `## <Topic>` sections — these become cached **series-bible** prose the
   DJs read (the moment you add a real `## ` section, it starts flowing into context).
2. Fill the `## Canon facts` numbered list with the file's hard, queryable facts (`canon-<stem>-N`).
3. Optionally tag facts (§5).
4. Run `make seed-canon` and confirm the counts grew.

You can leave the guidance block in place (it stays invisible) or delete it once the file is written —
either is fine. **Don't fabricate a whole world in one sitting;** grow the cornerstones over time, and
keep new facts consistent with what's already authored.

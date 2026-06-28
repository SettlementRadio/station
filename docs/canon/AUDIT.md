# AUDIT.md — auditing an external writer's canon submission (agent runbook)

> **For the agent.** When the operator says **"Audit `docs/canon/<NN-stem>.md`"** (a cornerstone file
> an external writer has changed), follow this runbook end-to-end: **validate → fix → overwrite the
> file → seed.** The end result is the reference file replaced with an audited, fixed version, and the
> RAG corpus re-seeded. This file is an authoring/ops guide — it carries no numeric prefix, so the
> seeder skips it (it is never world content).
>
> **Operating rules:** parse the candidate in a *throwaway* copy first — do **not** edit anything in
> the repo until the fixes are final. `Read` a file before you `Write`/`Edit` it. Preserve the
> writer's voice and best lines — make the **minimal** edits the findings require, don't rewrite.
> Surface every finding to the operator, then apply.

---

## Read first (the rules live in these files — load them before judging)

- **`CLAUDE.md`** — the hard rules (IP boundary; AI-disclosure wall; the in-world year is always
  `real year + 600`, never hardcode it).
- **`docs/canon/SPIRIT.md`** — the world's spirit + the IP firewall + "good old SF, no modern-AI."
- **`docs/canon/TAGS.md`** — the tag palette + the naming rule (lowercase single words).
- **`docs/canon/README.md`** — the format/section/field conventions + the fact-id scheme.
- The **related cornerstone files** for consistency (e.g. `00-station.md`, `05-worlds.md`,
  `10-history.md`, `78-communication.md`, and whichever others the submission touches).

---

## The five gates (what you are checking)

1. **Format** — does the parser load it cleanly?
2. **Conventions** — tags + structure follow `README.md`/`TAGS.md`.
3. **Ground rules** — the `CLAUDE.md` / `SPIRIT.md` hard rules (IP, floating year, no modern-AI).
4. **Spirit** — tone matches `SPIRIT.md` (mature wonder, warmth, optimism tempered, moral seriousness).
5. **Consistency** — no contradictions with the rest of the bible.

---

## Step 1 — Parse it in isolation (scratch only; touch nothing in the repo)

Copy the target file to a temp dir and run the real parser. This confirms it *seeds*, prints every
fact + its tags, flags non-conforming tags, and proves no real-author name leaked into the bible.

```bash
FILE=docs/canon/01-time.md            # <-- the file under audit
TMP=$(mktemp -d); cp "$FILE" "$TMP/"
.venv/bin/python - "$TMP" <<'PY'
import sys, re
from pathlib import Path
from src.world import canon_source
d = Path(sys.argv[1])
facts, cast, events = canon_source.load_folder(d)        # raises loudly on a format error
bible = canon_source.load_series_bible_folder(d)
print(f"PARSES OK: {len(facts)} facts, {len(cast)} cast, {len(events)} events\n")
for f in facts:
    print(f"  {f.id}: {f.text[:75]}")
    print(f"      tags: {f.tags}")
bad = sorted({t for f in facts for t in f.tags if not re.fullmatch(r'[a-z0-9]+', t)})
print("\nNON-CONFORMING tags (must be lowercase single alphanumeric words):", bad or "none ✓")
leak = [a for a in ('Asimov','Clarke','Heinlein','Bradbury','Le Guin','Lem','Butler','Herbert',
                    'Dick','Tolkien','Strugatsky','Miller','Brunner','Delany','Russ','Tiptree')
        if a.lower() in bible.lower()]
print("author-name leak in bible prose:", leak or "none ✓")
PY
rm -rf "$TMP"
```

If `load_folder` raises, the format is broken — read the error, fix the candidate (see §Common format
breakers), re-run. **Common format breakers:** a blank line between a fact and its `- **Tags:**` bullet
(orphans the tags); a `## Canon facts` mis-heading; a numbered item that isn't `N. text`.

---

## Step 2 — Conventions (tags + structure)

- **Tags must be lowercase single words** — no hyphens, no spaces, no capitals. The `NON-CONFORMING
  tags` line above lists violations. A hyphenated/multiword tag (`deep-time`, `new-year`) parses
  without error but is **dead**: the query side splits a topic on non-alphanumerics, so nothing ever
  matches it. Fix by splitting (`deep-time` → `deep, time`) or choosing a single word (`new-year` →
  `newyear`/`festival`).
- **Prefer the `TAGS.md` palette.** Reuse existing tags before coining new ones. If you coin a new
  tag, it must be a lowercase single word **and** you add it to the matching group in `TAGS.md`.
- **Structure:** `## Canon facts` numbered list, sequential; each tagged fact's `- **Tags:**` bullet
  sits directly under it with no blank line; prose lives in other `## Topic` sections (auto-captured
  as series bible). Required fields still apply for cast/events (`- **Logical voice:**`,
  `- **In-world datetime:**`).

---

## Step 3 — Ground rules (the hard ones — a violation blocks the merge)

Run the greps, then **read** the flagged lines and judge:

```bash
FILE=docs/canon/01-time.md
echo "— hardcoded in-world year (2xxx) — should be NONE (year is always real+600):"
grep -nE '\b2[0-9]{3}\b' "$FILE" || echo "  none ✓"
echo "— fixed 'N years since/ago/after <event>' — floating-year risk:"
grep -niE '(hundred|thousand|[0-9]+) years? (since|ago|after|of counting)' "$FILE" || echo "  none ✓"
echo "— franchise-echo proper nouns (review each by hand):"
grep -niE 'core worlds|outer worlds|federation|the empire|jedi|terran|spice|ansible|foundation' "$FILE" || echo "  none obvious ✓"
echo "— modern-AI tropes (SPIRIT §2) — should be NONE:"
grep -niE 'singularity|superintelligence|upload(ing|ed|s)?|chatbot|neural net|machine learning|\bLLM\b' "$FILE" || echo "  none ✓"
```

What to enforce:
- **IP boundary** — no real author/work/character/franchise/trademark, and no proper noun that
  *echoes* one (e.g. "Core Worlds" leans on Star Wars). Original invented names (a world called
  *Meridian*, *Cold Harbor*) are exactly right — encourage them.
- **Floating year** — the in-world year is always `real + 600` (`settings.world_years_ahead`); the
  `+600` is the gap to *our* present, **not** an in-world count of years since some event. Reject any
  fixed "600 years since the Founding"-style claim (it goes stale). State the offset relatively
  ("six centuries on", "centuries of counting forward") if at all.
- **No modern-AI tropes** — classic SF only (no singularity / LLM / uploading / algorithmic dystopia).
- **AI-disclosure wall** — in-fiction machine minds (if any) are separate from the station's
  out-of-fiction AI disclosure; don't conflate them.

---

## Step 4 — Spirit & consistency (judgment — read SPIRIT.md + related files)

- **Tone (SPIRIT §1/§5):** mature wonder; cozy, intelligent, a little wry; warm; morally serious;
  optimism tempered by hard questions. Flag dystopian gloom, grimdark, camp, militarism, or
  contemporary-AI anxiety.
- **Consistency:** cross-read the related cornerstone files and flag contradictions — e.g. a single
  dramatic "Founding/landfall" clashes with `10-history.md`'s "slow tide outward, not one event";
  named clocks/terms must agree across `00-station.md`/`01-time.md`; the no-FTL / weeks-of-distance
  premise (`75-technology.md`) must hold. Also check the submission isn't internally contradictory
  (e.g. the same event landing on two differently-named places).
- **Original always** — the tribute takes the *strain*, never the IP (SPIRIT §0).

---

## Step 5 — Apply the fixes (minimal; preserve the writer's voice)

Edit the candidate to resolve every finding, keeping the writer's strongest lines and imagery intact.
Typical fixes: de-hyphenate tags; reframe a hardcoded-year claim; rename a franchise-echoing proper
noun (and de-dupe it across the doc); align a claim with an existing cornerstone; fix em-dash
typography (`names-Monday` → `names — Monday`); normalize spelling to the repo's British forms
(`honoured`, `neighbours`). If you coined any new tag, add it to `TAGS.md` now.

---

## Step 6 — Save to the reference file

`Read` the live `docs/canon/<file>` (to satisfy the edit-safety check), then `Write` the audited
version over it. This is the only repo write of the run.

---

## Step 7 — Seed + post-seed validation

```bash
make seed-canon 2>&1 | grep -E '"event": "seed_done"'     # canon count should change as expected; embeddings_canon == canon

STEM=time          # <-- the file's stem (01-time.md -> time)
.venv/bin/python - "$STEM" <<'PY'
import sys, re
from src.world import store
stem = sys.argv[1]
with store.connect() as conn:
    all_facts = store.all_canon(conn)
    facts = [f for f in all_facts if f.id.startswith(f"canon-{stem}-")]
    print(f"facts seeded for '{stem}':", len(facts))
    print("non-conforming tags remaining:", [t for f in facts for t in f.tags
                                              if not re.fullmatch(r'[a-z0-9]+', t)] or "none ✓")
    print("embeddings == canon:", store.embeddings_count(conn, corpus='canon') == len(all_facts))
PY
```

Both lines clean = the file is audited, fixed, saved, and the RAG corpus is updated.

---

## Step 8 — Report back (template)

```
AUDIT — docs/canon/<file>
  Format        : PASS (N facts parse)         [or: FIXED <what>]
  Conventions   : <tags OK / fixed: de-hyphenated X, Y>
  Ground rules  : <PASS / fixed: floating-year, IP echo …>
  Spirit        : <assessment — what's strong, what was adjusted>
  Consistency   : <PASS / reconciled with <file>: …>
  Fixes applied : <bullet list, preserving the writer's lines>
  Seed          : canon <old> -> <new>, embeddings match ✓
```
Keep the writer's voice in the final file; report what you changed and why.

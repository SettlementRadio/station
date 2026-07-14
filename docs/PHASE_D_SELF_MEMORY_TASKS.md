# PHASE_D_SELF_MEMORY_TASKS.md — D13: Self & Interpersonal Memory ("The Hosts Remember Themselves")

> Sub-pack **D13** of Phase D (see `docs/PHASE_D_OVERVIEW.md`) — a **post-D12 addendum**: the gap
> named by the 2026-07-13 DJ persona audit. Work in order, one task at a time: implement → show +
> how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing principles
> (OVERVIEW §2).
>
> **The problem, in the operator's words.** The hosts remember the *world* (D9.4: stories from the
> tick's log) but not *themselves or each other*. Nothing carries "you said last week you thought
> the renewal vote was a ritual, not a rule," a running joke, or a personal detail a host revealed
> on air ("Vell admitted he still writes to Meridian"). Cards are static; the DJs' personal lives
> never advance; an emergent self-detail either vanishes or — worse — gets contradicted later.
> D12's thread hand-off covers only *adjacent segments in one show*; day-to-day, host-to-host
> memory does not exist. This is the biggest remaining distance between "distinct voices" and
> "people who live at this station."
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §2 (standing principles) + §2a (the state/seed/backup
> matrix — the journal becomes a new runtime-accrual row); `src/writers/memory.py` (D9.4 — the
> world-memory sibling this pack mirrors: bounded dials, per-host ranking, degrade-to-"",
> per-call placement so the cache lever holds); `src/writers/conversation.py` (the reserved
> injection-point comment block; `_dispatch_section` shows the audit-fix pattern);
> `src/scheduler.py` (`top_up` — where a rendered segment's script is in hand, the D12.0 hand-off
> capture site); `src/providers/embeddings.py` + the polymorphic `embeddings` table (D2 — corpus
> per kind); `docs/PHASE_D_FRESHNESS_TASKS.md` (D5) and `docs/PHASE_D_CONTINUITY_TASKS.md` (D12)
> for the memory division-of-labour this must extend, not blur.
>
> **Depends on:** the **C2 scheduler** (built), **D9.4** (the pattern), **D12** (the hand-off
> substrate + `flow` param it complements). **D2** embeddings recommended (semantic recall of past
> exchanges) but optional — the structured recency read must work without vectors. Self-contained
> and buildable now; the DEVLOG recommendation is to design the extraction against the C9 soak's
> real output, but nothing here blocks on the server track.

## What D13 delivers

Each host accrues a durable, bounded **on-air journal** — opinions they voiced, jokes that landed,
personal details they revealed, and what they last talked about with each colleague — captured
automatically after a segment airs and recalled into future segments the way D9.4 recalls world
stories. A host can say "you told me last week you never finished that letter" and be *right*.
Self-consistency is enforced: the same journal block goes to the continuity editor, so a host
contradicting their own stated opinion flags like any continuity error — which is also what makes
**emergent self-canon safe**: a detail a host invents about themselves becomes durable instead of
random.

## Why this is a real gap (the as-built cause)

Four memories exist today, and none of them is this one:

1. **D4 coverage memory** — the NEWS DESK's intended story recurrence. World-facing.
2. **D5 airplay memory** — OUTPUT anti-repetition (don't re-pick topics / re-phrase openings).
   Negative memory: what *not* to say.
3. **D9.4 DJ memory** — a host remembering the *world's* stories, persona-weighted. Nothing about
   what the host themselves said or did.
4. **D12 talk hand-off** — the live thread across adjacent segments of ONE show. Evaporates at the
   program boundary.

The writers' room's "two people who've shared this booth for years" is therefore written on
*card + world* alone — the shared history is asserted, never evidenced. D13 is the positive,
durable, self/interpersonal memory: what I said, what we joked about, what I told you about me.

## The load-bearing design decisions (honour these)

- **The card is the bible; the journal is state.** The hand-authored card
  (`docs/canon/90-cast.md`) always WINS on conflict — the journal never edits, overrides, or
  auto-appends to a card. The journal is runtime accrual (like `airplay_history` /
  `news_coverage`): it **survives `seed-canon`**, is cleared only by `reset-world`, and gets its
  own row in the OVERVIEW **§2a matrix**. A journal entry contradicting the card is a capture bug
  to drop, not a canon change.
- **Capture is post-gate, cheap, best-effort — never load-bearing.** Extraction runs AFTER a talk
  segment clears both gates and renders, on the `haiku` tier (high-volume/low-stakes per
  CLAUDE.md routing), at the `top_up` site where the script is already in hand (the D12.0
  pattern). A failed extraction logs and moves on; a segment never waits on, or fails because of,
  its journal. Direct CLI paths (`make conversation`, `make format FMT=talk`) don't capture —
  only aired (scheduled) segments become memory, mirroring D4/D5.
- **Recall mirrors D9.4 exactly.** A small, VARIABLE block in the per-call system prompt (never
  the cached core — the cache lever holds), bounded by dials, per-host AND per-pair ("what you two
  last talked about"), degrading to `""` on empty/disabled/DB-failure. Reuse `writers/memory.py`'s
  shape; a sibling module (`writers/journal.py`), not a rewrite.
- **One embeddings table, one seam.** Semantic recall of past exchanges rides the existing
  polymorphic `embeddings` table (a new corpus, e.g. `journal`) behind
  `providers/embeddings.py` — no new vector store. Structured recency read (newest per
  host/pair) is the always-works fallback when vectors are off.
- **Bounded biography.** Personal details (`kind=detail`) are capped per host
  (`convo_journal_max_details_per_host`): hosts must not accrete unbounded life-facts that
  crowd the card. On overflow, oldest-least-referenced drops. The operator can inspect + prune
  (ADMIN_MANUAL how-to, `→ Phase E panel`).
- **Extend the division of labour, don't blur it.** D4/D5/D9.4/D12/D13 each keep their one job
  (the list above); document D13's place in the same standing note the earlier packs share. In
  particular: D13 recall must not fight D5 freshness — remembering "we discussed X last week" is
  a *callback*, not a licence to re-run topic X (the block's steer says so, like D9.4's
  "never re-announce").
- **Config over hardcoding.** One `# --- DJ self/interpersonal memory (D13) ---` section in
  `src/config.py`, area-prefixed `convo_journal_*`. `convo_journal_enabled=False` is the clean
  rollback to the pre-D13 room.
- **Field hosts and guests are in scope as SPEAKERS, not subjects.** Sera's journal works like
  Vell's (her dispatches are her on-air life). One-off invited guests (D9.3) are NOT journaled —
  they're texture, not cast. A figure soundbite is already the D10 quotes table's job.

**Definition of done for D13:** across a multi-day simulated run, a host references a past
on-air moment correctly ("as I said the other night…", a called-back joke, a remembered
colleague-exchange) without re-announcing it; a draft contradicting a journaled stance is flagged
by the continuity editor; the journal survives `seed-canon` and is wiped by `reset-world`;
everything degrades cleanly with the journal off/empty; `ruff` + `pytest` green; `make
acceptance` (with a new self-consistency property if feasible) passes; README/ADMIN_MANUAL/DEVLOG
updated; the overview tracker gets the D13 row flipped.

---

## D13.0 — The journal substrate (schema + store, no behaviour change)
**Goal:** the table and the seam exist; nothing reads or writes it in production yet.
**Do:**
- **Schema (additive migration, never truncate-reseed):** a `host_journal` table — `id`,
  `host_id` (FK-ish to cast id, but survives a cast reseed — plain text, like other accrual
  tables), `other_host` (nullable — set for interpersonal entries), `kind`
  (`opinion | detail | joke | exchange`), `text` (one compact sentence), `segment_id`,
  `air_time` (the slot's REAL broadcast time, the D5 timeline) plus the in-world face where
  useful, `tags text[]`. Indexes on `host_id`, `air_time`.
- **Store seam:** `insert_journal_entries`, `journal_for_host` (recency-bounded),
  `journal_for_pair`, `prune_journal` — all SQL behind `world/store.py`, typed rows.
- **§2a matrix:** add the `host_journal` row to `docs/PHASE_D_OVERVIEW.md` §2a — runtime accrual;
  survives `seed-canon`; cleared by `reset-world`; backed up with the world DB.
**Done when:** migration applies on a live DB; round-trip unit tests on the store functions pass;
`make seed-canon` leaves journal rows standing; `reset-world` clears them (extend the existing
seed-scope tests). No production code path writes it yet.

## D13.1 — Capture: the post-air extraction step
**Goal:** every aired talk segment leaves a few compact journal entries behind.
**Do:**
- At the `top_up` post-render site (where D12.0 captures the hand-off), run ONE `haiku` extraction
  over the segment script: return 0–N entries (bounded by
  `convo_journal_max_entries_per_segment`), each `host / kind / one-sentence text /
  optional other_host / tags`. Prompt it for the DURABLE, not the incidental: stated opinions,
  revealed personal details, jokes with callback potential, the gist of a notable
  host-to-host exchange. Nothing quotable-verbatim needed — this is recall, not transcript.
- Guard the card-wins rule at capture: the extractor sees the speakers' cards (cached blocks — the
  cache lever) and is told to DROP anything contradicting a card.
- Best-effort discipline: extraction failure/timeout logs a warning and the segment stands;
  evergreen fallbacks and non-talk formats are skipped; embed each stored entry into the
  `journal` corpus (best-effort too, like canon embeddings).
**Done when:** a scheduled talk segment produces visible journal rows (log + a
`make console`/status surface line); a segment with nothing durable produces zero rows without
error; unit tests cover the parse/validation of the extractor's output shape (stub the LLM).

## D13.2 — Recall: the "what you've said before" block
**Goal:** the room writes with the hosts' own history in hand — the D9.4 sibling.
**Do:**
- `writers/journal.py`: `journal_section(speakers, now, topic=None)` → a per-call prompt block:
  per host, a bounded pick of journal entries (recency + persona/tag weighting, the D9.4 ranking
  pattern) PLUS a per-pair line ("last time {A} and {B} shared a segment they …") when both hosts
  have history together. With a `topic` and vectors available, blend semantic recall from the
  `journal` corpus; else the structured recency read.
- The block's steer mirrors D9.4's: reference naturally and SPARINGLY, as people with a shared
  past — a callback or a held opinion, never a recap; a remembered topic is not an invitation to
  re-run it (the D5 boundary, stated in the block).
- Weave it into `orchestrate` beside the D9.4 `memory` block (the reserved injection point), and
  into the `showrunner` only as the pair-line (the beat-picker needs "their relationship," not
  the full journal). Dials: `convo_journal_per_host`, `convo_journal_window_days`,
  `convo_journal_top_k`. Degrades to `""` everywhere.
**Done when:** generated scripts show correct, sparing callbacks (verify by reading a run seeded
with known journal rows); the block rides the per-call prompt only (extend the D9.4 cache-lever
test); off/empty/DB-failure produce the pre-D13 room byte-for-byte.

## D13.3 — The self-consistency gate
**Goal:** a host contradicting their own journaled past flags like any continuity error — the
mechanism that makes emergent self-canon durable AND safe.
**Do:**
- Show the SAME journal block to the continuity editor (`_run_continuity`), with one added
  instruction: a host contradicting a journaled stance/detail (or the card — which always wins
  over the journal too) is an ISSUE. This mirrors exactly how D9.4's misremembering check landed.
- On a flagged contradiction, the standard C0 path applies (regenerate with the note → evergreen).
  No new gate machinery.
**Done when:** a test draft that reverses a journaled opinion is flagged by the editor
(stubbed-LLM unit test of the prompt content + a live spot-check); a draft consistent with the
journal passes; the card-wins ordering is stated in the editor prompt.

## D13.4 — Verify end-to-end + docs + acceptance
**Goal:** prove memory holds across days, keep the gates green, document it.
**Do:**
- A token-lean **demo** (`make journal-demo` or fold into `continuity-demo`): simulate several
  talk slots across two "days," print the captured entries and a later script's callback so the
  loop (air → journal → recall → callback) is visible without TTS.
- **Acceptance:** extend the D11 sim with a self-consistency property if it can stay
  deterministic (e.g. seeded journal rows + assert the block reaches the prompts and the editor);
  otherwise assert the substrate invariants (capture writes rows; seed-canon preserves;
  reset-world clears).
- **Docs:** ADMIN_MANUAL how-tos (inspect the journal, prune an entry, the dials, the rollback) —
  tagged `→ Phase E panel`; the memory division-of-labour note extended with D13; README if the
  talk description changes; a DEVLOG entry; flip the **D13 row** in the overview tracker + §3.
**Done when:** the demo shows a correct callback across a program boundary and across a simulated
day; `ruff` + `pytest` + `make acceptance` green; docs + tracker updated.

---

## Config knobs this pack introduces (sketch — finalise in-task)
One `# --- DJ self/interpersonal memory (D13) ---` section in `src/config.py`:
- `convo_journal_enabled` (master toggle; false = the pre-D13 room — the clean rollback).
- `convo_journal_max_entries_per_segment` (capture bound per aired segment).
- `convo_journal_per_host` / `convo_journal_window_days` / `convo_journal_top_k` (recall bounds —
  the D9.4 dial pattern).
- `convo_journal_max_details_per_host` (the bounded-biography cap; prune policy on overflow).

## Seams it touches
`world/store.py` (schema migration + journal CRUD), `scheduler.top_up` (the post-render capture
site, beside the D12.0 hand-off), `providers/llm.py` via the normal `generate` seam (`haiku`
extraction; no new vendor calls), `providers/embeddings.py` (a `journal` corpus on the existing
polymorphic table), a new `writers/journal.py` (recall — the D9.4 sibling),
`writers/conversation.py` (`orchestrate`/`showrunner`/`_run_continuity` — the reserved injection
points), `config.py` (the dials). **No new provider; no new engine; no card mutation.**

## Explicitly NOT in D13 (→ elsewhere)
- **Auto-evolving the cast cards** (the tick or the journal writing biography into
  `90-cast.md`) → NOT this pack, and probably never automatic: the card is the human-controlled
  bible (the D-phase operating model). If the operator wants a journal detail canonised, they
  edit the card by hand.
- **Tick-generated host life events** (the world engine authoring storylines *about* the DJs —
  "Vell's transfer request") → a different, riskier idea; a possible D14/Phase E discussion, not
  here. D13 only remembers what actually aired.
- **Listener-facing memory** (remembering a listener's letters across weeks — the Phase E inbound
  layer) → Phase E, on top of this substrate.
- **A transcript archive / full-script search** → not needed; the journal is distilled recall,
  and segments' scripts already live where they live. Don't build a second archive.
- **News desk self-memory** → the desk already has D4 coverage memory; the anchor's *persona*
  journal applies only via shared talk segments. Don't duplicate.

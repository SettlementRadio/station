# PHASE_D_CONTINUITY_TASKS.md — D12: Talk Continuity / Show Flow

> Sub-pack **D12** of Phase D (see `docs/PHASE_D_OVERVIEW.md`) — a **post-D11 addendum**: a
> product-quality gap found while operating the built station. Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2).
>
> **The problem, in the operator's words.** Consecutive talk segments feel disconnected — each opens
> with a time-stamp ("it's … hour…"), runs a 2–3 minute exchange, then *closes* and the next segment
> *resets* with a brand-new topic. It plays like N independent mini-shows back-to-back, not one radio
> show. Real radio carries a thread across breaks and only signs off at the end of the show.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §2 (standing principles) + §3; `src/writers/conversation.py`
> (`showrunner` picks ONE beat; `orchestrate` writes the exchange; the reserved injection-point comment
> block; `_frame_for`/`_situation` time framing); `src/formats/talk.py` (`_BACKBONE` = open→banter→
> music-lead-in→close); `src/scheduler.py` (`top_up` — the placement loop that generates the buffer in
> air order, and `clock_state`/`_last_cursor` persisted across runs); `docs/PHASE_D_FRESHNESS_TASKS.md`
> (D5 — the anti-repetition memory this must be reconciled with); `docs/PHASE_D_PROGRAMMING_TASKS.md`
> (D6 — programs/clocks give "where in the show am I").
>
> **Depends on:** **D6** (programs + per-program clocks — position-in-show comes from the grid) and the
> **C2 scheduler** (built). Reconciles with **D5** (freshness). Independent of the world spine otherwise
> — buildable now.

## What D12 delivers

Consecutive talk segments in the same program read as **one continuous conversation**: the show opens
once at the top, the hosts carry (and gently evolve) a thread across several segments with cold hand-offs
between them, do a time-check only occasionally, and sign off once at the end — the way a real show runs
across its music and breaks. A segment is still the atomic, independently-gated, hot-swappable unit (the
scheduler's resilience is untouched); D12 adds the **thin flow layer on top** that the writers' room was
always designed to grow into.

## Why this is a real gap (the as-built cause)

Each talk segment is generated as a **self-contained mini-show**. Four things fight continuity today:

1. **No cross-segment memory.** `showrunner` (conversation.py) picks ONE fresh beat with no knowledge of
   what the previous segment discussed or how it ended. There is no "continue the thread" input anywhere
   in the writers' room or the scheduler.
2. **A full open→close every segment.** `formats/talk.py` `_BACKBONE` hard-codes "Open warmly … then a
   short close," so every ~3 min segment deliberately opens AND closes.
3. **A time-check near every open.** `orchestrate`'s `time_check` = "a real time check belongs near the
   open" → the "it's X hour" that starts every segment.
4. **Freshness pushes the opposite way.** D5's steer tells each segment to *avoid* recently-aired
   topics — nudging toward a *new* topic every 3 minutes, i.e. against continuity.

It's built this way on purpose (atomic, resilient, gate-per-segment, evergreen-swappable). D5 solved
*"don't repeat yourself"*; *"flow across segments"* was never a pack. This is that pack.

## The load-bearing design decisions (honour these)

- **Segments stay atomic + resilient.** D12 is a flow layer, NOT a rewrite. Each segment is still built,
  safety/continuity-gated, rendered, and scheduled independently, and can still fall back to an evergreen
  without breaking its neighbours. Continuity is **best-effort context**, never a hard dependency: a
  missing/short/failed hand-off just means the next segment opens standalone (as today). It must never
  block or fail generation.
- **The seam is the writers' room, not a new engine.** All of this rides the existing
  `showrunner → orchestrate → continuity` structure via the injection points the code already reserves
  (conversation.py's comment block). No new segment engine; no scheduler rewrite.
- **The hand-off lives where the buffer is built.** The scheduler's `top_up` generates talk slots **in
  air order in one loop**, so the previous talk segment's tail is available *in-memory* as the next is
  built; **persist** it in `clock_state` (like `_last_cursor`) so the thread also survives across
  top-up runs. No new table needed unless D12.2 wants one — prefer the existing state.
- **Position comes from the program clock (D6), not a guess.** "First / middle / last content slot of
  this program" is derivable from the clock sequence the scheduler already walks — that drives open vs
  cold-in vs close.
- **Config over hardcoding.** New dials go in one `# --- Talk continuity (D12) ---` section of
  `src/config.py`, area-prefixed `convo_continuity_*` / `convo_flow_*`. Backbone strings stay out of code
  literals where a dial fits.
- **Gates unchanged.** The continuity *editor* gate (safety + canon continuity) still runs on every
  draft. D12's "conversational continuity" is a different thing (thread across segments) — additive.
- **Feed the operator manual.** Append the D12 how-tos (the flow dials, the demo) to
  `docs/ADMIN_MANUAL.md` under *Voice* / *Tuning the living world*, tagged `→ Phase E panel` where they
  are env dials.

**Definition of done for D12:** a run of consecutive talk segments in one program plays as a single
flowing show — one open at the top, cold hand-offs that pick up the prior thread, occasional (not
per-segment) time-checks, one close at the end — while a *new* program still opens fresh and D5 still
prevents day-scale looping; degrades cleanly to today's standalone behaviour when a hand-off is missing;
`ruff` + `pytest` green; the D11 acceptance sim still passes (ideally with a new continuity assertion);
README/ADMIN_MANUAL/DEVLOG updated; the overview tracker gets a D12 row.

---

## D12.0 — Show position + the talk hand-off substrate
**Goal:** the generator knows *where in the show* a slot sits, and the previous talk segment's tail is
carried forward — the substrate both layers read. No behaviour change yet.
**Do:**
- **Show position.** Derive, at the scheduler placement site, each content slot's position in its program
  run: `open` (first content slot of a program instance), `continue` (a middle slot), `close` (the last
  content slot before the program changes). Use the D6 clock cursor + the known program boundary
  (`last_program_id` / the next slot's program). Thread it into generation as a new optional parameter on
  `make_format_segment` (e.g. `flow: ShowFlow | None`), defaulting to `None` = today's standalone shape
  so the direct B4/B5 CLI paths are unchanged.
- **The hand-off record.** After a talk segment renders in `top_up`, capture a compact **hand-off**: the
  last 1–2 spoken lines (or a one-line "where we left off" the orchestrator emits), the active topic/beat
  handle, and an `open_thread` flag (is there more to say, or did it wrap?). Persist it in `clock_state`
  (JSON-serialisable, like `_last_cursor`) so the next slot — this run or the next top-up — can read it.
  Best-effort: an evergreen fallback or a parse-empty segment writes an *empty* hand-off (→ next opens
  fresh).
**Done when:** `top_up` computes + persists a per-program show position and the last talk hand-off; both
are visible in `clock_state`/logs; nothing about the *output* changes yet; direct `make conversation` /
`make format FMT=talk` paths behave exactly as before (position `None`). Unit test the
position/boundary logic + hand-off round-trip.

## D12.1 — Positional open / close / time-check (Layer 1 — stop the reset)
**Goal:** the cheap, high-impact win — segments stop opening, closing, and time-stamping every time.
**Do:**
- Make the talk backbone **positional** (driven by D12.0's `flow`): `open` → a real show open; `continue`
  → **cold in, cold out** (no greeting, no sign-off — "…anyway, the thing about that is…"); `close` → a
  genuine close. Replace the fixed `formats/talk.py` `_BACKBONE` with position-aware directives (keep the
  strings as tunable constants/config, not scattered literals).
- Make the **time-check occasional**, not per-open: only near a handover or the top of the hour (reuse
  the D6 pinned-slot / `_frame_for` handover signal), not every segment. Drop the unconditional
  "time check belongs near the open" for `continue` slots.
- Standalone (`flow=None`) keeps today's self-contained open→close (the direct paths + a lone slot still
  read as a complete little segment).
**Done when:** generating a run of consecutive talk slots in ONE program shows exactly **one** open at the
start, cold middles, **one** close at the end, and a time-check only at the hour/handover — verified by
reading the scripts (a token-lean demo or `make format` sequence). A new program still opens fresh.

## D12.2 — Thread the conversation across segments (Layer 2 — the real flow)
**Goal:** consecutive segments are the SAME conversation continuing, not new topics.
**Do:**
- Feed D12.0's hand-off into the **showrunner**: when `open_thread` is set and the thread isn't spent,
  the showrunner **continues** the prior beat (deepen it, take the next angle) instead of picking a fresh
  one; when it's exhausted (or a pacing budget is hit), it **transitions** naturally to a new beat — real
  radio moves on, but on purpose, not every 3 minutes.
- Feed the hand-off tail into the **orchestrator** for `continue` slots: open by *picking up where they
  left off* — reference the last exchange, don't re-introduce the topic or the hosts.
- A small **thread-pacing policy** (config): keep a thread for up to `convo_continuity_max_segments`
  consecutive talk slots (or until the showrunner flags it spent), then require a transition — so a topic
  neither dies after one segment nor overstays.
- Resilience: if the previous slot was evergreen / had no hand-off, `continue` degrades to a soft open
  (no "welcome back," but a fresh angle) — never a broken reference to a segment that didn't air.
**Done when:** across a simulated program hour, consecutive talk segments read as one evolving
conversation — segment 2 picks up segment 1's thread with no re-introduction; a spent thread transitions
cleanly; the hosts sound like they never left the booth. Verify by reading 3–5 consecutive scripts.

## D12.3 — Reconcile freshness (D5) with continuity (D12)
**Goal:** continuity and anti-repetition stop fighting — continue the *active* thread, still don't loop
across the *day*.
**Do:**
- Scope the **showrunner's** freshness steer so it does NOT veto continuing the current thread: the
  "avoid recently aired" pressure should target day-scale looping (yesterday's / last hour's *other*
  material), not the beat the hosts are actively on. Practically: exclude the active thread's topic from
  the avoid-list while `open_thread` holds, or weight recency so the immediate thread is exempt.
- Keep D5's **opening-fingerprint** freshness for `open`/transition moments (a new thread shouldn't start
  like a recent one); it's irrelevant to cold `continue` slots (which have no "opening").
- Confirm D4 news recurrence is untouched (news continuity is its own coverage memory — D12 is talk).
**Done when:** a long run shows the active thread *continuing* (D12.2) AND no day-scale looping (D5 still
bites on new-thread openings + repeated topics across the day); the two memories have a documented,
non-conflicting division of labour (extend the D5-vs-D4 note with D12).

## D12.4 — Program sign-on / sign-off + light sign-posting (optional depth)
**Goal:** a program reads as a *show* with a start and an end, not just flowing talk — the finishing
touch. Scope-gated: do the minimum that lands; defer the rest.
**Do:**
- A real **sign-on** at a program boundary ("welcome to The Long Night…") and **sign-off** at its end,
  tied to the D6 program identity + the D7 theme/sting that already fire at the boundary (so the spoken
  open/close lands *with* the produced theme, not randomly).
- Light **sign-posting**: before a music slot or a break, an occasional "coming up…" tease; after,
  a brief "back to it." Keep it sparse + config-gated (`convo_flow_signpost_*`), never formulaic.
**Done when:** a program has a recognisable spoken start + end aligned with its theme, with occasional
teases across it; it feels hosted, not shuffled. (If this proves large, split the sign-posting half to
Phase E and land only sign-on/off.)

## D12.5 — Verify end-to-end + docs + acceptance
**Goal:** prove the flow holds over a real program run, keep the gates green, document it.
**Do:**
- A **demo** (`make continuity-demo` or fold into `programming-demo`): generate a program's worth of
  consecutive talk slots at an advancing clock and print the scripts back-to-back so the single-show flow
  is visible; token-lean (showrunner + orchestrator, no TTS), rolled back if it writes state.
- Extend the **D11 acceptance sim**: add/adjust an assertion that consecutive talk slots in one program
  DON'T each re-open/time-stamp (a "flow" property) and that the existing *no-repetition* property still
  passes (continuity must not reintroduce looping). Keep it deterministic.
- **Docs:** append the flow dials + the demo to `docs/ADMIN_MANUAL.md` (Voice / Tuning), update
  `README.md` if the talk behaviour description changes, add a DEVLOG entry, and add the **D12 row** to
  the `docs/PHASE_D_OVERVIEW.md` tracker (§4) + a one-line D12 brief in §3.
**Done when:** the demo shows one flowing show; the acceptance sim (with the new flow assertion) passes;
`ruff` + `pytest` green; docs + tracker updated.

---

## Config knobs this pack introduces (sketch — finalise in-task)
One `# --- Talk continuity (D12) ---` section in `src/config.py`:
- `convo_continuity_enabled` (master toggle; false = today's per-segment open→close — the clean
  rollback).
- `convo_continuity_max_segments` (how many consecutive talk slots a thread may hold before a forced
  transition).
- `convo_flow_timecheck` (`open|hourly|handover|never` — when a spoken time-check is allowed).
- `convo_flow_signpost_chance` (D12.4 tease frequency; 0 = off).

## Seams it touches
`writers/conversation.py` (`showrunner`/`orchestrate` — the reserved injection points), `formats/talk.py`
(`_BACKBONE` → positional directives), `scheduler.top_up` (compute show position; capture + persist the
hand-off in `clock_state`), `formats.make_format_segment` (the new optional `flow` param),
`world/framing.py`/`_frame_for` (handover/hour signal for the time-check), `config.py` (the dials),
`freshness` (D5 reconciliation, D12.3). **No new vendor calls; no new provider.**

## Explicitly NOT in D12 (→ elsewhere)
- **Rewriting segments into one giant per-program script** → NOT this pack. Segments stay atomic +
  independently gated + evergreen-swappable; D12 is a thin flow layer over them. A single-script-per-show
  generator is a different (riskier) architecture and is out of scope.
- **Near-live / reactive talk** (responding to a live event mid-show) → Phase E.
- **Listener-driven threads** (calls/inbound shaping the conversation) → Phase E.
- **News desk continuity** → already D4 (coverage memory); D12 is the *talk* thread. Don't duplicate.
- **Deep program rundown planning** (a full producer that plans an hour's arc up front) → if D12.4's
  sign-posting balloons, split it to Phase E; land the atomic-flow win (D12.0–D12.3) first.

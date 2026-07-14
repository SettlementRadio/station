# DEVLOG — Settlement Radio

The written record of decisions and changes, one entry per working session. The screen
recordings show *how*; this log captures *what changed and why* — the part video can't make
searchable, and the source material for the case study and "built in public" posts later.

## How to use this

- **One entry per session**, newest on top. Keep it fast (5 minutes) or it won't survive.
- Tie each entry to its evidence: the commit(s) for that session and the clip filename(s) in
  `devlog/`. The trio — entry + commit + clip — is one session's complete record.
- Once code exists, "Changed" overlaps with git commits; that's fine. The log's real value is
  **Decisions** and **Why**, which commits don't capture.
- When you write the case study, read this bottom-up (oldest first) — it's the story arc.
- **This is the marketing content feedstock** — there is no separate `highlights.md`. Flag shareable
  moments with the `📣 Postable:` line below; the `docs/marketing/*` playbooks mine the DEVLOG.

**Entry template (copy this):**

```
## YYYY-MM-DD — [Phase] — <one-line focus>
**Focus:** what this session was about, in a sentence.
**Decisions:** the durable choices (the things that matter in three months).
**Changed:** files/commits/accounts that concretely changed.
**Why:** the one or two reasons behind the key decision (your future self will thank you).
**📣 Postable:** (optional) if this session produced something shareable — a clip, a milestone, a
neat mechanism — one line on what to post + the clip/commit. This is the marketing feedstock the
platform docs (`docs/marketing/*`) mine; `grep "📣"` to find them. Skip when there's nothing to post.
**Next:** the single next action.
Commit: <hash>  ·  Clips: <filenames in devlog/>
```

A typical *build* session will be short, e.g.:
> `## 2026-07-02 — Phase A — T3 script generation working`
> Focus: got Claude writing Vell's segment from canon. Decisions: cache the whole canon as one
> breakpoint. Changed: src/writer.py, README. Why: keeps input cost ~0.1x. Next: T4 (render to
> audio). Commit: a1b2c3 · Clips: 2026-07-02-first-script.mov

---

## 2026-07-14 — Audit follow-up — Three new cornerstones: sports, legendary figures, knowledge (215 → 244 facts)
**Focus:** built the three docs the audit's gap analysis recommended. **Seed clean (244 facts,
embeddings match), 427 tests pass**, tick state untouched.
**Decisions:**
- **The cornerstone test, stated:** a topic gets a standalone file when a tick domain or DJ desk
  generates content against it, or its facts are accumulating scattered — otherwise it's a section.
  (This is why medicine stays inside 75-technology.)
- **`52-sports.md`** — the `sports` tick domain and Kael's desk finally have structures: hollowball
  (the stations' own sport, architectural home advantage), the three circuit kinds, the
  season-as-ledger (provisional records, ratified weeks later), team/call-name naming conventions
  (constrain the tick without hardcoding rosters), Games host rotation + the Reading of the Absent.
- **`15-figures.md`** — the who-was-who file, with the **hard ownership rule in its header: the
  bible names only the dead and the legendary; living named figures are tick state
  (`figures`/`quotes`, D10), never hand-authored.** Twelve legend-framed entries (the Wayfinder, the
  Quiet Engineer, Teller Ashe, Mother Ledger, the Chorus of Nine, the Anonymous of the Latecomers…)
  binding the unnamed archetypes 70-music/65-arts/45-conflict already implied, each contested-on-
  purpose so DJs can retell and doubt them safely. Station founders stay nameless (00-station f7).
  Closes the ad-hoc name-coining risk: DJs reaching for a historical name now find one.
- **`58-knowledge.md`** — learning + science as institutions: the Common Lessons curriculum,
  correspondence science ("a result is not real until a stranger repeats it under another sun"),
  twin discoveries (priority disputes disarmed by custom), core academies vs frontier practical
  schools, Circuit Scholars, relay casebooks; the refused questions (no FTL research,
  mind-engineering restricted) restated from 75/25 so the files agree.
**Changed:** `docs/canon/15-figures.md`, `52-sports.md`, `58-knowledge.md` (new); README table +
TAGS.md (two new groups: Games & play extended, Knowledge & learning) updated.
**Why:** sports stories were already being tick-generated against three facts; unnamed history was
an invitation for the LLM to coin contradictory names ad hoc; education/science was the audit's
last flagged gap. All three consolidate what other files implied rather than fabricating fresh.
**Next:** the standing plan — D13 or C5–C9.
Commit: (this session) · Clips: (none)

---

## 2026-07-14 — Audit — Full canon audit: conflicts reconciled, palette refreshed, gazetteer added (197 → 215 facts)
**Focus:** full audit of `docs/canon/` against the four gates (conflicts between topics, tag
conventions, SPIRIT alignment, gaps) — then applied every finding. **Seed clean (215 canon facts,
10 cast, 9 seed events, embeddings match), 427 tests pass**, tick-generated world state untouched.
**Decisions:**
- **The lag has two tiers, defined once in 78-communication.** The *broadcast* (wide, unaddressed,
  repeated by every node) crosses the worlds in hours — a day or two to the far frontier; *addressed*
  messages ride the queue — days core, weeks frontier, months dark zones. This was the canon's one
  load-bearing contradiction (30-polities' same-evening Council speech and 10-history's "hours apart
  by signal" vs 78's "frontier weeks"): both are now true, of different tiers. Field-host rule
  restated in 90-cast in tier terms; letters stay weeks old; near-live sport stays possible.
- **The Relay Authority is now a defined institution** (30-polities): chartered technical body under
  the Council's Committee on the Relays — owns no relays (no one does), keeps standards, runs the
  annual maintenance window, trains keepers, holds records, and operates Settlement Radio on a small
  levy. Resolves the 00-station/90-cast mentions that pointed at nothing, and squares 78's
  "no single body" with 95's coordinated maintenance.
- **Expansion: the *network* has an edge, settlement doesn't.** 80-cosmos now says connected
  expansion stopped at relay reach while settlement trickles past the last relay and falls out of
  contact — reconciled with 10-history's ongoing frontier push.
- **The Wayfarers.** The journey-is-destination faith is a named minority creed born among the
  Betweeners, no longer attributed to the whole people (60-faith fact 5 had made a branch of
  humanity a stigmatised cult — anti-SPIRIT caricature).
- **Native life exists; minds don't.** New 05-worlds facts: a few worlds carry native biospheres
  (nothing that thinks), protected by compact — pins the question Mira's "native fauna" line had
  already leaked, without touching the humanity-is-alone premise. Also pinned scale ("settled places
  number in the hundreds").
- **New `06-gazetteer.md`** — one pinned entry per named place (Concordance, Meridian, Cold Harbor,
  Forge, Halcyon, Ashfall, Far Reach, Breathe Easy, ES-447), consolidating attributes previously
  scattered across nine files; new places must get an entry.
- **Recurring events roll forward.** 95-events header now carries the policy (annual/seasonal dates
  bump to the next instance; rare cycles keep a fresh past date, then roll); stale 2626 instances
  rolled to 2627 (eclipse to 2637); "The Silence of Ashfall" renamed "The Ashfall Minute" to stop
  overloading the Silence era-name.
**Changed:** all 20 cornerstones touched + `06-gazetteer.md` new. Highlights beyond the decisions:
35-economy got its counterweight (Children of the Signal keep the relays on gift-tithes by choice;
Mutual Aid/cooperative facts; Clearing Day when a world pays out its debt) — it was the one file
tilting grimdark; 20-peoples got the kinship/gender fact (the unmined Delany/Russ/Tiptree strain);
50-daily-life got games & the Inter-Settlement Games in gravity classes (Kael's desk finally has
canon behind it; `sports` is a tick domain); 01-time clarified Settlement Time kept Earth's year
count; 00-station's "late 27th century" (wrong *and* stale) → floating phrasing; Wren's ship renamed
*The Long Patience* (Culture-cadence echo); Kael "seeing"→"hearing" (it's radio); the Archivist's
card now forbids resolving the mystery into a machine; 65-arts anchors the Synthesis quarrel on
craft, not machine-creativity; -ize→-ise; tag near-dupes collapsed (ship/ships, relay/relays,
world/worlds, zone/zones, freehold/freeholds, contract/contracts, question/questions,
economy/economics, etc.); TAGS.md palette 182 → 428 with a new §4 census script; README table
un-staled (all files authored, gazetteer row).
**Why:** the writers' room can only stay consistent with what the bible actually pins. The audit
found the contradictions clustered exactly where files were written independently (lag, relays,
expansion, Cold Harbor's nature) — each a future on-air contradiction; and the world's grey needed
guarding in both directions (economy too dark, Compacts fine, Betweeners caricatured).
**Next:** the standing plan — D13 or C5–C9. The gazetteer is the template for pinning any world the
tick starts mentioning often.
Commit: (this session) · Clips: (none)

---

## 2026-07-14 — D12 addendum — Flow audit: threads no longer die on "good morning"
**Focus:** audited the cross-segment talk flow against the two operator-reported symptoms (the same
conversation re-worded segment after segment; a thread silently abandoned for a new topic). Verdict:
the D12 layer works as designed, but four holes remained — all fixed. **425 tests pass**, ruff clean.
**Decisions:**
- **Thread-end is POSITIONAL, never guessed from the words.** The D12.0 sign-off regex — probed
  live — false-positived on "good morning" (Wren's signature greeting), "stay with us", "see you",
  "take care", silently killing live threads mid-show: the operator's "abandoned conversation". Now
  an `open`/`continue` slot (told not to sign off) keeps its thread open; a `close` wraps it. The
  regex is deleted; the promised-but-never-built D12.2 replacement is finally moot.
- **Transitions bridge instead of vanish.** A mid-show slot that is NOT continuing (pacing budget
  spent) now tells the orchestrator the OLD topic (`_transition_section`), so the hosts pivot off it
  in half a line — no more faking a resume of a conversation that never happened.
- **Threads carry a covered-beats memory — shown to BOTH rooms.** `Handoff.covered` accumulates one
  handle per aired beat while a thread continues; the showrunner gets it as a don't-re-tread list
  AND the orchestrator's pickup section repeats it with an anti-echo rule ("never repeat or
  re-phrase lines from the prior exchange") — the first demo run showed a continue slot re-running
  the prior monologue, closing lines included, when only the showrunner was steered. Continue
  briefs now lead with an `Angle:` line so the covered handles carry content, not staging.
- **Stale hand-offs are dropped.** `Handoff.air_time` existed "so a stale hand-off can be
  recognised" but nothing checked it; now `live_handoff` (new dial
  `CONVO_CONTINUITY_HANDOFF_MAX_AGE_MIN`, default 60) stops a restart after downtime from resuming
  yesterday's conversation mid-sentence inside the same daily program.
**Changed:** `src/flow.py` (positional `open_thread`, `covered`, `beat_handle`, `live_handoff`;
regex deleted), `src/scheduler.py` (capture passes position/prev/continued; staleness at
`_show_flow`), `src/writers/conversation.py` (`_transition_section`; covered-beats block in the
showrunner thread), `src/continuity_demo.py`, `src/config.py` (the new dial), ADMIN_MANUAL; +6
tests (regression: ordinary phrases must not kill a thread).
**Why:** the flow substrate decided thread life from a wordlist scan of the last two lines — the
one part of D12 that guessed instead of knowing. Position is ground truth the scheduler already
has.
**Next:** D13 (`PHASE_D_SELF_MEMORY_TASKS.md`) or C5–C9, per the standing plan.
Commit: (this session) · Clips: (none)

---

## 2026-07-13 — Audit — DJ persona audit + the field-host fix: correspondents now cross the lag honestly
**Focus:** audited the DJ implementation (definitions, memory/personality machinery, speech
distinctiveness), validated live (two contrasting host pairs generated against the seeded world),
then fixed everything found. **419 tests pass**, ruff clean.
**Decisions:**
- **Field hosts are a CAST property, not a grid property.** New optional card bullet
  `- **Based:** field` (default `station`) flows card → parser → `cast.based` column (additive
  migration) → `CastMember.is_field`. Any show that schedules a field host gets the dispatch
  treatment automatically — the grid can't accidentally put Zhe live in the booth.
- **The dispatch form is a "stitched relay correspondence":** both sides genuinely answer each
  other (questions travelled out, answers came back before air), so conversational quality
  survives, but the seams show ("by the time you hear this…") and the correspondent names ONE
  location and stays there. Canon-blessed (78-communication's "pretending the lag does not
  exist"), enforced by the orchestrator directive + a continuity-editor check + the frame's
  situation prose.
**Changed:** `90-cast.md` (Based bullets; per-host `Humour:` registers; Wren fast/tumbling, Joss
terse, Thorn's close → "That's the current for this hour" so he stops sharing Joss's thread-tic),
`canon_source.py`, `store.py` (schema + migration), `framing.py` (`ShowFrame.remote` + dispatch
situations), `conversation.py` (`_dispatch_section`, editor check), `memory.py` (`_clip` no longer
truncates "Dr. …" summaries to "Dr."), `music.py` (links now in the DJ's OWN card register, was
hardcoded Vell-tone; field DJs' music shows are sent-in recordings), canon README, ADMIN_MANUAL,
grid.yaml header; +13 tests.
**Why:** the live probe caught Sera trading galley coffee with Kael in-studio — impossible under
canon lag and exactly the kind of contradiction that makes the continuity gate thrash. Re-probed
after the fix: Sera records from "a relay station common room on the edge of the Forge corridor",
acknowledges the lag, no shared space — and the hosts still sound like themselves.
**📣 Postable:** before/after of the same show slot — the impossible in-studio banter vs the
stitched relay correspondence with its seams showing. The fiction got MORE sci-fi by being honest.
**Next:** C5–C9 (server track). The interpersonal/self-memory gap is now a written pack — **D13**,
`docs/PHASE_D_SELF_MEMORY_TASKS.md` (tracker row added; recommended after the C9 soak, buildable
any time).
Commit: (this session) · Clips: (none)

---

## 2026-07-11 — Audit — Full pre-broadcast system audit: code track clean, broadcasting blocked only on C5–C9
**Focus:** a top-to-bottom audit before going public — security, LLM token efficiency, prod
readiness against the roadmap, and bug/drift hunting. Verified live: **406 tests pass**, ruff
clean, no secret patterns in the tree or the git history.
**Decisions:**
- **Verdict: the code is ready; the infrastructure is the gate.** Everything on the code track
  (A, A2, B, C0–C4, D1–D12 incl. the D12 talk-continuity addendum) is built, tracked ✅, and
  tested; `make acceptance` (the simulated 24–48h soak) is green. "Start broadcasting" = the
  C5–C9 server track, none of which exists yet — so the next work is ops, not code.
- **Security passed** with three items pinned to the C5 checklist: (1) `config/icecast.xml`
  ships `hackme` for source/relay/**admin** — real secrets on the VPS, admin never
  internet-reachable; (2) the whole scheduler timeline is **naive local time** (18
  `datetime.now()` sites, zero tzinfo) — run the VPS in **UTC** or a DST jump shifts the runway
  math and every air_time by an hour; (3) minor: the OK-prefix verdict parsers
  (safety/continuity/tick) would pass a reply starting "Okay, but…" — cheap hardening candidate.
  Everything else held up under reading: SQL fully parameterized behind the store seam, DB
  passwords redacted in logs, the public now-playing feed is allow-list-by-construction, the
  gates fail closed at the slot level.
- **LLM efficiency confirmed near-optimal — no wasted calls found** across all 10 `llm.generate`
  call sites: every one rides the two-breakpoint cache (shared ~31k bible @1h TTL + cards);
  routing honored (sonnet default, haiku safety pass, opus ONLY as a flag-confirm); the tick's
  gate/advances batched at 50% off. The one open lever stays the documented one: the 24/7
  scheduler generation is synchronous/full-price — batching it (~3h lead time) halves the main
  recurring text bill; revisit AFTER the C9 soak with real telemetry from the box.
**Changed:** fixed the doc drift the audit found — `docs/ARCHITECTURE.md` status header (said
"Phases C–E planned" though C0–C4 + D are built), `.env.example` (`NEWS_STORY_COUNT` default
3→4; `BUFFER_ROTATION` still said music was dropped — stale since D7.4), the Makefile header;
this entry. **Also wrote the first Phase E pack:** `docs/PHASE_E_PANEL_TASKS.md` (E1, the operator
panel — the human wants to run the station from a web UI, not YAML buffers). Load-bearing calls:
**forms-over-files** (the YAML/markdown sources + existing seeds stay the truth; the panel is a UI
over the ADMIN_MANUAL workflows, whose hand-edit paths remain the fallback), **private by network
position** (loopback-only + SSH tunnel, no auth system, never in `/web`), destructive actions keep
typed-confirmation friction, and validation reuses the real loaders (grid/voices/tracks parsers) —
never a second validator. Timing: **build E1 during the C9 soak week** (7 hands-off days = free
build capacity; panel ready the day the station goes public). ROADMAP Phase E + ADMIN_MANUAL now
point at the pack. Story approve/reject stays a later opt-in pack; bible PROSE editing stays the
human's text editor by design.
**Why:** the human wants to start broadcasting; the audit's job was to say "yes/no and what's
between here and there." The answer is a short, concrete list instead of a vague feeling —
and it protects C5 from rediscovering the icecast/UTC traps mid-deploy.
**Next:** start the Phase C server track at C5 (`docs/PHASE_C_TASKS.md`), with the icecast
passwords + UTC items added to its checklist.
Commit: (this session)  ·  Clips: (none — audit session)

## 2026-07-10 — Cost lever — Shared-bible prompt cache (CO0–CO4): the bible stops being re-cached per DJ
**Focus:** the ~31k-token world bible is the largest, most-stable block in every prompt, but it was
being cached **per speaker set** — talk (`vell+wren`), news (`thorn`), music/commercial (`vell`) and
the world tick each kept a private copy — so a mixed cycle re-wrote the whole bible several times over.
Split the cache into two breakpoints (shared bible + per-speaker cards) so every caller reads one bible
entry, and proved the change is cost-positive *and* quality-neutral before touching anything.
**Decisions:**
- **Two cache breakpoints, not one.** `context.assemble` now exposes the stable core as `bible` (raw,
  byte-identical across every caller) + `cards_text` (the per-speaker cards); the seam emits them as two
  `cache_control` blocks. `cached_context` stayed as a computed back-compat join so call sites migrated
  incrementally. Concatenated, the two blocks are **byte-identical** to the old single string — so the
  model input is unchanged *by construction*, not by hope.
- **1h TTL on the bible block only** (`llm_cache_bible_ttl`, config-over-hardcoding); cards + dynamic
  stay on the default 5-min ephemeral. The bible changes only on a canon re-seed, so a 1h TTL trades a
  2× write for far fewer writes — and, crucially, keeps it warm across the ~15-min DJ rotation gap that
  the old 5-min TTL blew through on every segment.
- **World tick routed through `bible=` too**, so its bible block carries the same text *and* the same
  cache_control (incl. TTL) as the segment writers' — so they actually share the entry.
- **Measure-first discipline.** Added usage telemetry (`input`/`cache_creation`/`cache_read` split on
  every call + batch rollup) and a repeatable cost probe BEFORE changing the topology; wrote the
  byte-equivalence golden test BEFORE the split.
**Changed:** `src/providers/llm.py` (two-part stable prefix in `generate`/`_system_blocks`/`BatchRequest`
+ usage telemetry), `src/world/context.py` (`bible`/`cards_text` fields, `cached_context`/`cards_block`
properties), call sites `src/writer.py`, `src/formats/{music,commercial,news}.py`,
`src/writers/conversation.py`, `src/world/world_tick.py`, `src/config.py` (`llm_cache_bible_ttl`),
new `src/costprobe.py` (cost probe + CO4 A/B) + `make costprobe`/`costprobe-ab`, tests
`tests/test_llm_cache.py` (new) + `tests/test_context.py` + fixture migrations, and the measurement
tables in `docs/CACHE_OPTIMIZATION_TASKS.md`. **406 tests green; ruff clean.**
**Why:** the bible was re-written per speaker set on every cold cycle, and the old 5-min TTL expired
between a DJ's turns (~15 min apart) — so a continuously-running station paid near-full price for the
bible on almost every segment. Measured on the real stack: **pass-1 `cache_creation` 94,195 → 32,291
tokens (−66%)** — the bible is now written once and read by the other formats. At 12h/day continuous
that is roughly **~$700/mo → ~$270/mo** in estimated LLM cost, almost entirely from the bible no longer
being re-cached. Quality is provably unchanged: the byte-equivalence test is green (model input
identical), corroborated by a fixed-clock A/B whose only script differences are model sampling noise.
**📣 Postable:** clean cost-mechanism story — "we cut our AI text bill ~60% by changing *nothing* the
model sees." The bible (90% of every prompt) was being cached separately for each DJ line-up and
expiring between their turns; splitting it into one shared, hour-warm cache block made it byte-identical
input at a third of the cost. The before/after token table + the "model input identical: yes, scripts
differ only by sampling noise" A/B is the proof. (docs/CACHE_OPTIMIZATION_TASKS.md Measurements)
**Next:** CO5 (document the two-breakpoint topology in ARCHITECTURE.md + ADMIN_MANUAL.md, note it in the
Phase D overview cost-lever section). Then weigh the two further levers surfaced here: batching the
ahead-of-time scheduler generation (50% off, the buffer has 3h of lead time) and tiering low-stakes
calls (continuity/music/commercial) down to Haiku.
Commit: (pending)  ·  Clips: —

## 2026-07-08 — Phase D — Jingles extended to the whole grid (per-program themes, by convention)
**Focus:** the sonic-identity code was built for the old 4-daypart grid; the grid has since grown to
~28 named programs, so most shows opened cold (no theme). Wired every program to its own opener and
generated the missing clips.
**Decisions:**
- **Convention over registry.** A program's theme resolves as `assets/themes/<program_id>.mp3` — the
  filename *is* the wiring, so a new grid program needs no code edit (the human drops the clip in). An
  explicit `PROGRAM_THEMES` dict now holds only OVERRIDES (the 3 legacy daypart files whose names ≠
  program id, plus 2 reuse cases: `the_mailbag`→C11 letters, `the_circuit`→C12 games).
- **Never open cold.** Added a format-theme fallback at the boundary (`placement.program_theme_segment`
  → first content format's theme: news→C7, talk→C9, music→talk), so a program with no bespoke clip yet
  still opens on-brand.
- **Night beds.** Extended `production_bedded_programs` to the deep-night talk shows (`deep_hours`,
  `deep_field`, `the_gathering`), all mapped to the existing B4 night bed (reused, not new media).
- Dropped the stale `daywatch` theme key (gone from the grid); extended the A4 sweeper daypart map.
**Changed:** `src/production/media.py` (convention resolution + repointed registry + beds + sweepers),
`src/production/placement.py` (format fallback + `_first_content_format`), `src/config.py`
(`production_bedded_programs`), `tests/test_production.py` (+convention / override-wins / format-fallback
cases), new `docs/JINGLE_PROMPTS_2.md` (22 new per-program Suno styles) + `docs/PHASE_D_JINGLES_TASKS.md`
(the J1–J6 tech pack), `docs/JINGLE_PROMPTS.md` (recorded the previously-undocumented D8 brand bug;
noted the convention supersedes the daypart mapping). Human generated all 22 theme clips +
`d8_brand.mp3`. **393 tests green; ruff clean; acceptance green.**
**Why:** a station whose every show opens with silence doesn't sound like a station; the convention
means the ~28-program grid (and any future program) gets its identity with zero code churn.
**Next:** listen to a real `make buffer` run — confirm the boundary themes land and the night beds sit
right; optionally curate dedicated `*_bed` variants for the deep-night shows (they reuse B4 for now).
Commit: (pending)  ·  Clips: —

## 2026-07-08 — Phase C/D — Playout loop bug: fixed the scheduler↔playout seam (two layers, runtime-proven)
**Focus:** the live stream replayed the same ~2-min talk segment over and over (an "exact repetition"
loop). Diagnosed it to the scheduler↔playout seam — **not** a generation bug (the segment sidecars
show the thread evolving normally) — and fixed it on both sides, with a runtime proof so it can't
silently regress in the C5 server work.
**Root cause (two compounding faults):**
- **Churn (my earlier "incremental playlist" fix over-fired).** I had made `top_up` rewrite
  `segments/playlist.txt` after *every* segment so a cold `make schedule` could start airing early.
  But Liquidsoap watches that file (`reload_mode="watch"`) and **resets to the top of the list on each
  reload**, so during a multi-hour cold fill the constant rewrites pinned playout to entry #0 — the
  show's opener — replaying it instead of advancing.
- **No drain escape.** `playlist` defaults to `loop=true`, so a stale/frozen list (scheduler killed —
  the operator had Ctrl-Z'd it — or generation stalled) **replays forever** rather than draining, so
  the never-dead fallback chain below it never got a turn.
**Decisions / fixes:**
- **Scheduler:** write the playlist once when audio first lands, then only every
  `schedule_playlist_write_every` (=5) segments — not every one — so playout can advance between
  reloads; and `_write_playlist(entries, now)` now **drops fully-aired entries** so the head is always
  "playing now", never a stale opener a reload could snap back to.
- **Playout (`config/radio.liq`):** `loop=false` on the **scheduled** tier only (evergreen keeps
  looping — it's the safety net). A drained list now plays through **once** and goes unavailable, so the
  chain falls through to the evergreen pool instead of replaying real content. `reload_mode="watch"`
  still **revives** it the instant a top-up writes fresh audio.
**Changed:** `src/scheduler.py` (throttled + aired-dropping playlist writes), `src/config.py`
(`schedule_playlist_write_every`), `config/radio.liq` (`loop=false` + rewritten rationale comment),
`tests/test_scheduler.py` (+`_write_playlist` aired-drop test). **390 tests green; ruff clean;
`liquidsoap --check` clean.**
**Why:** an unattended 24/7 station must never air an exact repeat — that instantly breaks the "live
mind" premise. The real operating model is the always-on scheduler (C5 systemd), where the buffer stays
hours ahead and never drains; `loop=false` is the belt to that suspenders, so even a dead generator
degrades to the evergreen safety clip, not a stuck groove.
**Verified at runtime (not just types):** two headless Liquidsoap 2.4.4 runs with `on_track` logging —
(1) a one-clip list drains → **falls to EVERGREEN and stays** (no replay); (2) writing a fresh clip
mid-run **recovers to SCHEDULED within one track**. So the fix both stops the loop and leaves normal
operation untouched.
**📣 Postable:** the debugging arc — "why is my AI radio station stuck repeating one segment?" → the
`reload_mode="watch"` reset-to-top gotcha + `playlist loop=false` → a runtime proof harness. A clean
"two-layer fix + prove it" story. (Commit for this session.)
**Next:** operator to restart cleanly (`make stop` → drop stale buffer → `make schedule INTERVAL=300` +
`make serve`) and confirm by ear; the always-on scheduler.timer/liquidsoap.service belong to C5.
Commit: (pending)  ·  Clips: —

## 2026-07-07 — Phase D — D12 built: talk continuity / show flow (consecutive talk plays as ONE show)
**Focus:** built the D12 sub-pack end-to-end (D12.0–D12.5) — the thin flow layer that makes consecutive
talk segments in a program read as one flowing show instead of N reset-after-reset mini-shows.
**Built:**
- **D12.0 substrate** — a per-slot show POSITION (open/continue/close) derived at the scheduler
  placement site + a compact talk HAND-OFF (last lines, beat, `open_thread`) persisted in `clock_state`;
  a new `src/flow.py` (`ShowFlow`/`Handoff`), threaded via an optional `flow` param on
  `make_format_segment`. No output change.
- **D12.1 positional** — the talk backbone + the spoken time-check are now positional (one open, cold
  middles, one close; time-check only at the hour/handover). New dials `convo_continuity_enabled`,
  `convo_flow_timecheck`.
- **D12.2 thread** — the showrunner CONTINUES the same beat across segments (pickup from the hand-off)
  until a `convo_continuity_max_segments` pacing budget forces a clean transition; the thread carries
  across a music slot and resets at a new program.
- **D12.3 reconcile** — D5 freshness no longer vetoes the active thread (topic excluded from the
  avoid-list while continuing; opening steer dropped on cold continues); still bites on day-scale loops.
- **D12.4 sign-on/off + talk-first** — spoken program sign-on/sign-off by name; the backbone no longer
  assumes a song follows. **Plus two operator-driven fixes found in review:** the `news` bulletin now
  reads from a DEDICATED anchor (`news_anchor_ids` = Thorn) in every show, not the show's host; and
  guests/interviews became **per-program** (`guest_chance`).
- **D12.5 verify** — `make continuity-demo` (consecutive scripts back-to-back, token-lean, writes
  nothing); a sixth `talk_flow` acceptance property (a show opens once, never re-opens mid-run); docs.
- **The grid, rebuilt (operator review):** a talk-first, many-vertical week (politics/economy/conflict/
  law/science/travel/arts/history/…), a per-day ROTATING specialist, music cut to short features (the
  catalogue is ~2.5h total), every DJ cast to role, formats tagged (desk/duo/interview/dispatch/music).
**Changed:** new `src/flow.py`, `src/continuity_demo.py`; `writers/conversation.py` (positional
backbone/time-check + thread + guest cadence), `formats/talk.py`, `scheduler.py` (position + hand-off +
news-desk routing + `flow_position` on entries), `world/programming.py` (`guest_chance`), `config.py`
(the `convo_continuity_*`/`convo_flow_*`/`news_anchor_ids` dials), `acceptance.py` (+`talk_flow`),
`docs/programming/grid.yaml` (full rewrite), README + ADMIN_MANUAL + overview tracker. **389 tests
green; ruff clean.**
**Why:** the disconnection undercut the premise — a station you'd leave on. The flow layer keeps the
atomicity/resilience the scheduler depends on while adding the show flow real radio has; the news desk +
verticals + per-program guests make the schedule believable to an actual listener.
**Next:** listen to a real `make continuity-demo` / `make buffer` run and tune the guest rates + thread
budget by ear; optionally the music new-vs-vintage selector filter (needs more older-era tracks).
Commit: (this session)  ·  Clips: —

## 2026-07-07 — Phase D — D12 planned: talk continuity / show flow (a gap found while operating)
**Focus:** operating the built station surfaced a real product-quality gap — consecutive talk segments
don't flow. Diagnosed the cause in the as-built code and wrote the full sub-pack to fix it
(`docs/PHASE_D_CONTINUITY_TASKS.md`), to build in a standalone session.
**The issue (operator-observed):** each talk segment opens with a time-stamp ("it's … hour…"), runs a
2–3 min exchange, then *closes* — and the next segment *resets* with a brand-new topic. It plays like N
independent mini-shows back-to-back, not one radio show that carries a thread across its music + breaks.
**Root cause (not a bug — a missing layer):** segments are generated as self-contained mini-shows, and
four things fight continuity — (1) `showrunner` picks ONE fresh beat with **no knowledge of the previous
segment**; (2) `formats/talk.py` `_BACKBONE` hard-codes open→banter→close *every* segment; (3)
`orchestrate`'s `time_check` puts "it's X hour" near *every* open; (4) D5 freshness steers each segment
to *avoid* recent topics — nudging toward a NEW topic every 3 min, i.e. AGAINST continuity. It's built
this way on purpose (atomic, resilient, gate-per-segment, evergreen-swappable); D5 solved "don't repeat
yourself," but "flow across segments" was never a pack.
**Decisions (the fix, as D12):**
- **A thin flow layer over atomic segments — NOT a rewrite.** Segments stay independently gated +
  hot-swappable + evergreen-able; continuity is best-effort context that never blocks generation. It
  rides the existing `showrunner → orchestrate` injection points (no new engine), and the cross-segment
  hand-off lives in the scheduler's persisted `clock_state` (no new table).
- **Two layers, cheap→deep.** Layer 1 (D12.1): make open/close/time-check **positional** off the D6
  program clock — one open at the top of a show, cold middles, one close at the end, time-check only at
  the hour/handover (kills ~80% of the "reset" feeling for ~½ day). Layer 2 (D12.2): **thread the
  conversation** — carry the previous segment's tail + topic forward so the showrunner *continues* the
  beat until it's spent, then transitions on purpose.
- **Resolve the freshness↔continuity tension (D12.3):** freshness targets *day-scale* looping, not the
  active thread; the showrunner may continue the current beat while still not re-running yesterday's.
- **Numbered D12** — a post-capstone addendum; the pack's last task adds its overview tracker row + §3
  brief (kept out of the other docs for now, per the build-it-in-its-own-session plan).
**Changed:** **new** `docs/PHASE_D_CONTINUITY_TASKS.md` (D12.0–D12.5, with the load-bearing decisions,
config section `convo_continuity_*`, seams, and an explicit "NOT in D12"). No code yet.
**Why:** the disconnection undercuts the whole premise — a station you'd leave on. Fixing it as a planned
sub-pack (not a quick hack) keeps the atomicity/resilience the scheduler depends on while adding the show
flow real radio has.
**Next:** build D12 in a standalone session — start D12.0 (show position + hand-off substrate), then the
Layer-1 win (D12.1).
Commit: (this session — planning only)  ·  Clips: —

## 2026-07-07 — Phase D — D11 built: the operator manual + the integrated acceptance gate (the capstone)
**Focus:** close Phase D. Consolidate every pack's captured how-tos into one verified operator manual
(D11.0–D11.2), then build the integrated 24–48h acceptance simulation that proves the whole spine
holds together over time (D11.3), and link/polish/lock it (D11.4).
**Decisions:**
- **Two operator docs, split by intent, ONE source each:** `docs/ADMIN_MANUAL.md` is *operating*
  (reorganised by operator TASK — running the station, seeding & the world, authoring the bible,
  programming the grid, music, commercials, voice, monitoring, recovery, admin/security — not by
  sub-pack); `docs/HOWTO.md` is *developing* (setup, tests, lint, ad-hoc generation). Cross-linked,
  never duplicated. Every hand-edit/env-dial workflow keeps its `→ Phase E panel` tag — the manual
  IS the Phase-E control-surface requirements list.
- **Verify, don't guess (D11.2):** ran every how-to against the live local stack (seed modes, a real
  world tick, the console/feed/health, the demos, a voiced `format`, the reset-world guard). This
  surfaced a real latent bug — the `tick_db` fixture cleared tick-owned events/stories/state but NOT
  `figures`/`quotes`, so a committed dev-DB tick broke a "nothing written" assertion (fixed).
- **The acceptance gate mocks ONLY the two provider seams** (`llm.generate` + `tts`/`mix.join_clips`)
  and runs EVERYTHING ELSE for real — story selection, temporal framing, the grid + clocks, freshness
  steering, the music selector, the gates — so the five properties (no dead gaps · no repetition loops
  · stories evolve · cost bounded · schedule sane) are genuinely exercised. No live calls, no cost;
  the whole simulated world runs in one rolled-back transaction (never touches the real world), and a
  FIXED start date makes it deterministic + repeatable.
- **A gate that can't fail is worthless:** each of the five evaluators is unit-tested BOTH ways —
  passes clean data AND fails loudly on a planted defect (a silent gap, a track loop, a frozen world,
  a call storm, a backwards schedule).
**Changed:** `docs/ADMIN_MANUAL.md` (task-organised, verified), `docs/HOWTO.md` (reconciled to
dev-only), `pyproject.toml` (pytest `pythonpath` so `.venv/bin/pytest` finds `src`),
`tests/test_world_tick.py` (fixture figures/quotes fix); **new** `src/acceptance.py` +
`tests/test_acceptance.py` + `make acceptance` (HOURS=…); README + this overview footer link the
manual → **343 tests green**, 24h & 48h windows pass.
**Why:** an unattended 24/7 station is only as trustworthy as the runbook you rely on at 3 a.m. and
the dress rehearsal you run before going live — the manual makes the ops surface knowable, the
acceptance sim makes "it all still fits together" a one-command check before the C9 soak.
**📣 Postable:** `make acceptance` — a 24-hour radio station simulated in seconds, asserting it never
goes silent, never loops, and its world keeps moving — the pre-flight check before it broadcasts for
real. "How do you test a station that runs forever? You fast-forward a day."
**Next:** Phase D is code-complete — the C5–C9 server track (provision the VPS, YouTube relay, web
player, the C9 live soak) and the C6 launch-voice decision. Re-verify the manual at soft launch (CM).
Commit: (this session)  ·  Clips: (record a `make acceptance` run)

## 2026-07-06 — Phase D — D9 built: voice & emotion + the DJ roster (the cast comes alive)
**Focus:** build the whole D9 sub-pack (D9.0–D9.5): emotion wired end-to-end, the pronunciation
lexicon, the data-driven voice registry with a distinct preset per DJ, guest/non-host voices (the
D9×D10 bridge), per-DJ memory from the story log, tests + a real on-air demo + docs.
**Decisions:**
- **Emotion is data behind the seam** — a 5-word logical vocabulary (`warm|wry|somber|bright|
  urgent`) maps to real ElevenLabs `VoiceSettings` (stability/style/speed) ONLY inside
  `_synthesize_elevenlabs`; Kokoro/`say` accept-and-ignore. Writers tag turns (`Vell [somber]:`),
  un-tagged turns take a daypart mood floor, operator default `TTS_EMOTION_DEFAULT`. AUDIBLE only
  on the flagship path — C6 decides the engine AND retunes the (unheard) curves by ear.
- **Two new human-edited registries** (the tracks.yaml pattern): `config/pronunciation.yaml`
  (invented names → respell + Kokoro phonemes via misaki's `[name](/…/)` markup — verified live:
  Zhe "zhee"→"zhay") and `config/voices.yaml` (logical voice → vendor preset per engine — the
  hardcoded tts.py dicts + 9 placeholder aliases are GONE; every DJ distinct; `make seed-canon`
  fails loud on a bible↔registry mismatch). ElevenLabs ids for the 8 new DJs are premade-roster
  picks, unheard (key lacks `voices_read`) — confirm at C6.
- **Guests are sparse, deterministic, and host-bracketed** — `writers/guest.py` draws ~1 in 5 talk
  slots (air-time-seeded): a D10 figure+quote becomes a voiced soundbite (stable pool voice per
  figure; `figures.voice_id` honoured) else an invited one-off persona; a structural gate re-rolls
  any draft where the guest opens/closes. This DELIVERS D10.3.
- **DJ memory = in-character recall, bounded** — `store.remembered_stories` (past beats in a
  window) → per-host persona-weighted one-sentence handles, in the PER-CALL prompt (cache lever
  holds), shown to the continuity editor so misremembering flags. Cross-referenced vs D4/D5.
- **Content fix that made memory bite:** cast card tags now carry tick-DOMAIN words (the two tag
  vocabularies never met before — hosts all remembered the same beats); added a `sports` domain so
  Kael's beat exists in the generated world.
**Changed:** `providers/tts.py` (+`lexicon.py`), `writers/{conversation,guest,memory}.py`,
`world/{store,seed,world_tick}.py`, `config/{voices,pronunciation}.yaml`, `docs/canon/90-cast.md`
(domain tags), `grid.yaml` (**The Bridge**, weekends 07–12 — joss+mira, the first show airing the
new cast), config/env/README/ARCHITECTURE/pack notes, 6 new test files → **328 tests green**.
**Why:** the roster is the product's ceiling — one pair of voices can't carry a 24/7 station; and
every new surface stayed DATA (bible + two YAML registries) so growing the cast never touches code.
**📣 Postable:** the demo segment — `segments/talk-20260711T090000.mp3` (~3 min): Joss + Mira's
first broadcast, in character, referencing a 12-years-back on-air moment pulled from the station's
own generated history, with per-turn emotion tags in the script. "The DJs remember now."
**Next:** D11 (operator manual capstone) or the C5–C9 server track — ask the human which.
Commit: (this session)  ·  Clips: (record The Bridge demo)

## 2026-07-06 — Phase D — D8 built: commercials & sponsorship (texture, not interruption)
**Focus:** build the whole D8 sub-pack (D8.0–D8.3): the `commercial`/`promo` format, the
daypart-driven ad-break cadence with the d18 sting bracket, the `sponsors` table + "Powered by"
reads, tests + demo + docs.
**Decisions:**
- **Generated, never a reel** — every spot is written + voiced fresh per airing (the load-bearing
  D8 principle: infinite in-character copy is the AI advantage; a break is never the same spot
  twice). One builder + a mode, exposed as TWO registry entries (`commercial`, `promo`) so the
  grid/scheduler can place either by name.
- **The grid owns the ad load** — a program declares `break_every: N` in `grid.yaml` (daywatch 4,
  long_night 6, handovers/default none); the scheduler weaves the break like the disclosure ident
  (no program-clock atom consumed), spots-first so a failed generation never airs a lone sting
  bracket. Dials default sparse (1 spot/break).
- **Production spectrum, opt-in** — `FORMAT_COMMERCIAL_PRODUCTION_LEVEL`: L1 read (default), L2
  bedded via D7's duck primitive, L3 testimonial (degrades to L1 until D9/D10), L4 brand-sting
  bookend (the only prerecorded ad audio); effective level recorded in the segment meta.
- **`sponsors` is hand-entered catalog, not world state** (§2a): outside `_WORLD_TABLES`, survives
  `seed-canon`/`reset-world`, own `config/sponsors.yaml` + `make seed-sponsors` path; SHIPS EMPTY —
  populating real sponsors is gated on CM. Run windows are REAL wall-clock, half-open; reads air
  inside every Nth break only in-window.
- **"Powered by" is structural** — the lead-in is a template in `formats/sponsor.py` (it cannot
  drift); a "sponsored by" blurb is auto-corrected + logged. Binding per MARKETING.md.
- **File-based admin is interim** — sponsors.yaml / grid break_every / the dials are tagged
  `→ Phase E panel` in ADMIN_MANUAL (new convention): the manual doubles as the Phase E control
  surface's requirements list (ROADMAP updated).
**Changed:** `src/formats/commercial.py` + `sponsor.py` (new), `formats/__init__.py` (registry),
`scheduler.py` (`_place_break` weave + persisted counters), `world/programming.py` (`break_every`),
`world/store.py` (Sponsor + sponsors table + active_sponsors + counts), `world/seed_sponsors.py` +
`config/sponsors.yaml` + Makefile (`seed-sponsors`, `commercials-demo`), `production/media.py`
(commercial bed, brand + sponsor clips), `placement.py` (`break_sting_segment`),
`src/commercials_demo.py` (new), `tests/test_commercials.py` (19 tests; 282 total green), README,
`.env.example`, ADMIN_MANUAL (D8 + tag convention), grid README, ROADMAP (Phase E panel scope).
**Why:** the small-catalogue problem is the whole argument — a prerecorded ad reel rotates a tiny
set and goes stale; generating per airing makes ads *world texture* instead of interruption, and
the sparse grid-owned cadence keeps it that way.
**📣 Postable:** the demo's first-ever generated spot — "Tessmer's. The boots remember who wore
them." — an AI radio station whose ads are fictional small businesses, never the same spot twice
(`make commercials-demo`).
**Next:** D9 (voice/emotion + roster) or the C5–C9 server track — operator's call.
Commit: (this session)  ·  Clips: (none)

## 2026-07-05 — Phase D — D7 built: the production layer (sound design + songs on air)
**Focus:** build the whole D7 sub-pack, task by task (D7.0–D7.5): the tracks catalogue, the Layer 4
mixer, grid-placed idents/stings/themes, ducked beds, the music selector — and `music` back on air.
**Decisions:**
- **`tracks` is curated catalog, not world state** — deliberately outside `_WORLD_TABLES` (survives
  `seed-canon` AND `reset-world`; its own `make seed-tracks` refresh); `artist_figure_id` is a SOFT
  reference (no FK — tracks outlive a world wipe that truncates figures; D10 backfills).
- **Playability is derived live, never stored** — a track is playable iff its manifest-named file
  exists (`production.media.is_playable`); dropping a Suno mp3 in makes the row playable, no re-seed.
- **Mixing is baked at render time** (segments stay single mp3s; scheduler/playout untouched), and
  ffmpeg has exactly TWO homes: synthesis plumbing in `providers/tts.py`, mixing in
  `production/mix.py`. Found + fixed a real bug on the way: ffmpeg's default mono→stereo conform
  applies the −3 dB pan law, so mixed speech aired quieter than dry — the mixer now upmixes mono at
  full gain (measured identical).
- **The selector is rule-based and deterministic, not an LLM** — weighted policy (daypart mood,
  world tone from the story log via a cheap keyword rule, D5 freshness for track+artist, era spread,
  featured/pinned) with a seeded jitter; same inputs + seed ⇒ same pick. The LLM only writes the
  intro/back-announce around the chosen track's lore.
- **Beds are doubly opt-in** (`production_bedded_programs × _formats`, default long_night×talk) —
  over-bedding is worse than none; news always stays dry.
**Changed:** `src/production/` (media/mix/placement/selector), `src/world/store.py` (+`tracks`),
`src/world/seed_tracks.py`, `src/formats/music.py` (real track in the `[SONG]` gap: intro → C10
bumper → track → back-announce via `join_clips`), scheduler weaves (boundary theme + B6 handover
sting, C8 before news, A1 cadence, `apply_bed`), freshness records track id/artist, now-playing
carries the track, `music` back in `grid.yaml` clocks + `buffer_rotation`; 29 new surgical tests
(263 green); README / `.env.example` / ADMIN_MANUAL / overview tracker updated.
**Why:** the station now *sounds produced* — the difference between "a TTS pipeline" and "a radio
station" is exactly this layer; and the human's 27-song Suno catalogue landed mid-session, so the
first real spin (Aurora Season, story told from its manifest blurb) aired the same day the plumbing
was built.
**📣 Postable:** the first real song on Settlement Radio — `segments/music-20260705T182414.mp3`
(Vell introduces "Aurora Season" from the lore, the track plays, he back-announces it). Commit e65eb4f.
**Next:** D8 (commercials — the d18 break stings are already on disk) or the C5–C9 server track.
Commit: e65eb4f (D7.4) + this session's D7.0–D7.3/D7.5 commits  ·  Clips: (record the first-spin playback)

## 2026-07-04 — Phase D — D7 prep: the media library (Suno production, no code)
**Focus:** author the full media-production layer *before* the D7 build — the song catalogue as
cultural artifacts, the expanded jingle set, the seed manifest — then generate the assets in Suno.
**Decisions:**
- **Artist = Suno Persona = future D10 figure.** The catalogue is a 14-act roster; each act is one
  Suno Persona (so a band's tracks share a voice) and each maps to `in_world_artist` today /
  `artist_figure_id` after the D10 backfill. One idea bridges the production tool and the data model.
- **`config/tracks.yaml` is pre-authored and is the D7.0 contract** — all 27 song rows (lore, tags,
  exact `audio_path`); the loader conforms to the file, not vice versa. Missing file = not playable,
  never crash; null duration = probe at seed. The D7 task pack now says this explicitly ("do NOT
  re-invent").
- **Playable vs referenceable stays a hard line:** 27 tracks with files are playable; the wider music
  culture (four new *scenes* — lane-rock, pulse-dance, void-lounge, relay-pop) went into canon
  `70-music.md` as facts 13–16, **without artist names** (artists stay owned by tracks.yaml → D10).
- **Jingle set expanded to match the as-built system**, not the MVP: B5b (nightfall — the grid program
  had no theme), D17 (event-agnostic special coverage — D3 generates events now, Lumen is not the only
  one), D18 (ad-break pair for D8), A4 sweepers ×3; three energy tiers + "Persona for Group A only" as
  the anti-sameness rules; every Style string self-contained (the human works Style-box + filename
  only; Lyrics box only for A1 and the 13 sung songs).
**Changed:** `docs/MEDIA_LIBRARY.md` (new — 27 songs, full lyrics, roster, Suno mechanics, storage
spec); `config/tracks.yaml` (new — 27 rows); `docs/JINGLE_PROMPTS.md` (22 entries / ~27 files, §4
storage table, tier guidance, self-contained styles); `docs/PHASE_D_PRODUCTION_TASKS.md` (contract
warnings); `docs/canon/70-music.md` (scenes of the present day + facts 13–16); `assets/` — **25/27
jingle files generated and placed** (only the D18 pair pending, needed for D8 not D7) + first 4 songs.
**Why:** D7's plumbing is only testable end-to-end with real curated media at known paths — and the
lore has to exist *before* the DJ can tell a song's story. Authoring the manifest first makes the
catalogue diffable, seedable, and safe from "the agent invents a format" drift.
**📣 Postable:** the roster reveal — 14 invented bands with genres grown from the world's physics
(oxygen-tank drums, relay-lag harmonies, storm-season dance music); pairs well with first-play clips.
**Next:** run `make seed-canon` (loads the four new scene facts), then **start D7.0 in a fresh
session** (media stores + `tracks` table, loading the pre-authored manifest).
Commit: (this session — docs/config/assets; commit before starting D7)  ·  Clips: (none)
**Focus:** turn "a folder of clips on a flat rotation" into a *programmed station* — a weekly grid of
named programs (hosts, framing, an hour-clock) the scheduler reads, a private operator console, and a
public now-playing feed for the web player.
**Decisions:**
- **The grid is a hand-edited YAML** (`docs/programming/grid.yaml`) read directly by `program_for(now)`
  — the config-file path. The **DB-table projection + `make seed-grid` are deferred to Phase E**, when
  the web grid editor needs a write target; both sit behind the one `program_for` seam, so storage can
  evolve without any caller changing. (Reconciled the D6.0 design doc to say this, not "DB now.")
- **The clock is an explicit sequence with run-lengths + pinned slots**, not a weighted ratio — that's
  the only shape that expresses a *dedicated music block* (`music x3`) vs *music interspersed*, plus
  `news@:00` top-of-hour. Pins fire on **crossing** the hour on the CONTINUOUS air timeline (a global
  cursor in `schedule.json`), so they land at the top of the hour even across a program boundary — not
  per-program (that skipped the boundary hour's news).
- **`part_of_day` stays hour-derived; the program drives hosts + handover.** This is what makes the
  generalised `framing.program_frame` reproduce the two-host C1 frame EXACTLY for the shipped grid
  (a per-hour parity test), so D1–D5 are untouched. The `default` program's `legacy` framing routes
  straight back through `show_frame`.
- **`programming_enabled` is the master switch / clean rollback** to the flat `buffer_rotation`; when on,
  `buffer_rotation` is only the default program's fallback mix — one source of truth, not two fighting.
- **Two strictly separate surfaces (audit fix): private console vs public feed.** The console
  (`make console`, CLI/SSH only) shows internal state (story log, buffer, health, cost); the feed
  (`segments/nowplaying.json`) is an explicit **allow-list** of public-safe fields (on-now/next +
  program + hosts + disclosure), never internal state. One shared `split_schedule` + `onair_hosts` so
  the two never disagree.
**Changed:** new `src/world/programming.py` (`program_for`, `next_format`), generalised
`src/world/framing.py`, `scheduler.py` (grid-driven selection + per-program/global clock cursors +
`split_schedule`/`onair_hosts`), new `src/console.py` + `src/nowplaying.py` + `src/programming_demo.py`;
`docs/programming/{README.md,grid.yaml}`; config + `.env.example` + Makefile (`console`, `now-playing`,
`programming-demo`) + README + ADMIN_MANUAL; tests `test_programming.py`, `test_scheduler_grid.py`,
`test_console.py`, `test_nowplaying.py`. `pytest` 234 green, ruff clean.
**Why:** a real station is programmed — the grid is what lets a 3-hour overnight block and a top-of-hour
news share one code path, and what D7 (sound design per daypart) + D8 (ad-break cadence) + D9 (a bigger
cast) build on. Keeping the read surfaces split is the public/private boundary the launch depends on.
**📣 Postable:** `make programming-demo` — a token-free screen of the grid: programs + hosts change by
daypart, `news@:00` lands on the hour, run-lengths (a 3-song sweep vs interspersed), and the console +
public feed rendered from it. Good "it's a real station now" clip.
**Next:** D7 (production layer: sound design + songs keyed to the dayparts D6 built) — or pivot to the
C server track (deploy) per the local-vs-server discussion.
Commit: (uncommitted) · Clips: (none yet — `make programming-demo`)

## 2026-07-01 — Phase D — D5: Freshness / Anti-repetition (the station never loops itself) — D5.0–D5.3
**Focus:** stop 24/7 output drifting into the same openings + the same beat every hour — a broad,
cross-format on-air memory that steers generation off recently-aired ground.
**Decisions:**
- **A dedicated `airplay_history` table, not schedule.json / sidecars.** Those hold only the *upcoming*
  buffer and are GC'd with the audio; the anti-repetition memory must be its own persistent, recency-
  queryable store of *features only* (topic/beat handle, opening fingerprint, key phrases — never audio).
- **It records on the BROADCAST timeline, not in-world.** `aired_at` is the segment's real `air_time`
  (scheduler order), because anti-repetition is about broadcast *adjacency* (don't loop back-to-back
  slots), NOT when the referenced events sit in the +600y world. (Corrected a D5.0 docstring that had
  claimed in-world.)
- **One chokepoint records everything.** Features are extracted once in the scheduler next to
  `_write_sidecar`, so every placed content slot is captured without wiring each producer;
  idents/evergreen/fallbacks are exempt (they're meant to repeat).
- **Kept DISTINCT from D4, in code and in the prompt.** D4's coverage memory drives *which* stories
  recur + *how they evolve* (intended); D5 keeps the *wording* fresh on top. The news prompt says so
  outright ("repeating a STORY is fine — vary the WORDING").
- **The memory outlives the audio + survives `seed-canon`.** It is bounded by its OWN sweep (window ×
  margin), never the C2.5 disk GC; cleared only by `reset-world` (added to the §2a matrix's scopes).
- **Conservative influence by default** (`prefer` soft, small limit): over-constraining starves a small
  canon, and D3's moving world is the real variety source — D5 only prevents *accidental* looping.
**Changed:** `src/world/store.py` (airplay_history schema + `record_airplay`/`recent_airplay`/
`recent_by_format`/`prune_airplay`, in `_WORLD_TABLES`), new `src/freshness.py` (extract at the
chokepoint + read blocks back), `src/scheduler.py` (record + sweep in the top-up housekeeping),
`src/writers/conversation.py` (showrunner topics + orchestrate openings), `src/formats/news.py`
(recent openings + the D4/D5 note), `src/config.py` + `.env.example` (`FRESHNESS_*`), new
`src/freshness_demo.py` + `make freshness-demo`, README, ADMIN_MANUAL, tests
(`test_airplay.py`, `test_freshness.py`, + injections in `test_conversation.py`/`test_news_desk.py`).
200 tests green.
**Why:** a station that repeats its own openings sounds broken within an hour; the memory is what lets
the writers' room *see what it just did* and choose differently — cheap string heuristics, no extra LLM.
**📣 Postable:** `make freshness-demo` — four talk segments at an advancing clock, each handed the
openings before it and told to open differently; ran 4/4 distinct openings AND beats. The "steer list
grows, the opening stays fresh" printout is a clean 20-second clip of the mechanism working.
**Next:** D6 (programming + status console) or D9 (voice & emotion) — both Ready.
Commit: _pending_  ·  Clips: 2026-07-01-freshness-demo.mov

---

## 2026-06-30 — Phase D — D10: Figures & Quotes (the world speaks) — D10.0–D10.2 + D10.4
**Focus:** model the invented PEOPLE a story is about and their attributable, dated quotes, then have
the news desk + DJs reference them — turning "a fact happened" into "people in a living world saying
things."
**Decisions:**
- **Two tables behind the store seam** (D10.0). `figures(id, name, role, card_text, voice_id?, tags,
  source)` and `quotes(id, story_id, beat_id?, figure_id, text, in_world_datetime, stance?, tags,
  source)`; a quote inherits its beat's datetime so the B2 clock frames it for free. `source` is the
  seed-vs-generated split, but the seed value is **`bible`** (per the §2a matrix, not `seed`): a
  `seed-canon` refresh clears bible figures/quotes and **leaves tick ones standing**; `reset-world`
  clears both. New tables land additively (`CREATE … IF NOT EXISTS`), not truncate-reseed.
- **Generated INSIDE the tick call** (D10.1), not a parallel pass. Each proposal/advancement JSON carries
  its figures + per-beat quotes, so they ride the SAME safety + continuity gate and Batch + caching levers
  — a flagged/off-canon figure or quote regenerates-then-drops **with its story**, no second gate engine.
  A continuing story **reuses** its figures by name (the advance prompt is fed the existing roster);
  unattributed quotes (naming an undeclared person) are dropped. IP rule enforced in prompt + gate.
- **Attribution rides the existing seams** (D10.2). News: `SelectedStory` carries the story's newest
  attributed quotes; the brief renders "X, the relay-keeper, said yesterday: …" via a new
  `events.phrase_for_datetime` (a quote isn't an `Event`). Talk: `context.assemble` adds a "what people
  are saying" slice — **semantic recall over the `quote` corpus when a topic is in play, structured
  date-window read otherwise** — so the DJs react in character with NO change to the writers (they already
  weave `ctx.dynamic`).
- **D10.3 (voiced soundbite) deferred to D9** — it's the D10×D9 guest-voice bridge; textual attribution
  stands alone, as the pack specifies.
**Changed:** `src/world/store.py` (figures/quotes tables + dataclasses + reads incl. the attributed-quote
JOINs + scoped `clear_world`), `src/world/world_tick.py` (figure/quote generation, reuse, gating, embed),
`src/world/events.py` (`phrase_for_datetime`), `src/world/context.py` + `src/formats/news_select.py` +
`src/formats/news.py` (attribution surfaces), `src/config.py` + `.env.example` (`WORLD_TICK_FIGURES_*`,
`NEWS_QUOTES_PER_STORY`, `CONTEXT_QUOTES_*`), `src/formats/figures_demo.py` + Makefile (`make
figures-demo`), tests (`test_figures_quotes.py` + additions to `test_world_tick.py`/`test_context.py`/
`test_news_desk.py`), README, `docs/ADMIN_MANUAL.md`, PHASE_D_OVERVIEW tracker (D10 ✅).
**Why:** figures + quotes are the single biggest lever for *rich* content, and folding them into the
gated tick (not a new pipeline) means the IP/continuity guarantees and cost levers come for free; the
seed-vs-generated split is what lets the human keep editing the bible without wiping the living world.
**📣 Postable:** `make figures-demo` — the world's people speak: "Mira Voss, the relay-keeper, said
yesterday: 'We are not going dark tonight.'" attributed off the living world (token-free).
**Next:** D5 (broad anti-repetition) or the D6 programming backbone; D10.3 soundbites land with D9.
Commit: (this session) · Clips: (optional — capture `make figures-demo` output)

---

## 2026-06-30 — Phase D — news register/length tuning + sequencing call (D9 anchor, D10 next)
**Focus:** reviewed a real `make format FMT=news` bulletin against three asks — named people, plainer
tone, ~5-min length — and decided what to fix now vs which pack owns what.
**Decisions:**
- **News register → formal, by prompt now.** The sample read poetic ("landed like a stone in still
  water"; invented studio colour like an archivist pulling old recordings). Retuned `news.py`
  `_build_system` to a formal broadcast register: facts first (who/what/when/numbers/names), short
  declarative sentences, NO metaphor/lyricism/editorial asides/invented colour, ≤1 light human note.
- **Length is a dial, not a feature.** Bumped the `FORMAT_NEWS_*` defaults to a full ~5-min hourly
  bulletin (words 800–1000, max_tokens 1600, length_target_sec 300, `NEWS_STORY_COUNT` 4). Spoken news
  is ~140–160 wpm and LLMs undershoot, so targets are set high; the scheduler still times on the
  MEASURED render, so verify by listening to one `make format FMT=news`.
- **Dedicated news anchor → DEFERRED to D9 (not a quick-win card now).** The cast card — not the prompt —
  is the dominant lever on voice; news currently borrows **Vell**, the atmospheric *night host*, which
  fights the formal instruction. A purpose-built plain newsreader card would help most. We *could* author
  one today (cast is hand-authored `docs/canon/90-cast.md` + the lazy `FORMAT_NEWS_SPEAKER_ID` dial, no
  code), but chose to fold it into **D9** (Voice & Roster) so the anchor lands with its managed roster
  slot, a distinct registered voice, the pronunciation lexicon (spoken-right invented names), and emotion
  — rather than a one-off card we'd revisit.
- **D10 is the next pack.** Its hard deps (D3 story log, D2 recall) are both BUILT and the tracker marks
  it Ready; D5–D9 don't block it. D10 (figures + attributable quotes, tick-generated + stored) is what
  makes named people PERSIST and stay consistent across bulletins/days/formats — the real fix for the
  "invent + keep consistent names" ask. Only the *voiced* soundbite defers to D9's guest-voice slot;
  textual attribution ("X said…") lands without it. D10-first also helps D7 (artist→figure links) and D8.
**Changed:** `src/formats/news.py` (formal register prompt), `src/config.py` (`FORMAT_NEWS_*` +
`news_story_count` defaults), `.env.example` (length/register dials), `tests/test_news_coverage.py`
(delta-count so the suite stays green once real bulletins have recorded coverage).
**Why:** voice quality is carried by the cast card, so the durable fix for tone is a real anchor (D9),
not more prompt text; and consistent NAMED people is a storage problem (D10), not a prompt problem —
sequencing D10 next delivers the highest-leverage content win while its dependencies are already in place.
**Next:** start **D10 — Figures & Quotes** (data layer + tick generation → news/DJ attribution).
Commit: (this session) · Clips: (optional — record a before/after news bulletin)

---

## 2026-06-30 — Phase D — D4: the News Desk (reports the living world) — D4.0–D4.4
**Focus:** replace the one-shot, memoryless news bulletin with a desk that reads the D3 story log and
broadcasts it like a real station — relevant to now AND canon, recurring + evolving across the day with
correct past/now/future framing, and self-consistent over time.
**Decisions:**
- **Coverage memory is the substrate** (D4.0). A new `news_coverage(story_id, covered_at, arc_stage,
  last_beat_id, angle)` table (the only SQL, in `store.py`) records *how the desk has told each story* —
  in-world `covered_at`, the newest beat reached, and the handle used. Kept DISTINCT from D5's broad
  output-level anti-repetition (this is per-story, news-specific); D5 layers on top. Survives
  `seed-canon`, cleared by `reset-world` (§2a), folded into `counts`.
- **Selection is its own module** (D4.1, `news_select.py`). Each hour it tags every active story
  `new`/`repeat`/`evolve` (from coverage + a genuinely newer beat) and `breaking`/`trailed`/`ongoing`
  (from the clock), grounds it against canon via D2 recall, drops cold repeats, and returns a ranked,
  bounded mix via soft per-kind quotas. Canon recall degrades to temporal-only when RAG is off; a
  `ground=False` fast path skips it entirely (the demo + any no-RAG caller).
- **The producer reuses the seams** (D4.2/D4.3). `news.py` consumes the selection, frames each item by
  arc + `relative_phrase` (evolve = "an update on …" with the delta beat; repeat = a light touch), and
  keeps the C0 gate — now **safety + a desk continuity editor** (against canon + prior coverage) in one
  regenerate-then-evergreen loop. Prior coverage is fed back for consistent naming; coverage is recorded
  only on a clean render. Records the story's *newest* beat so the next bulletin's evolve check is honest.
- **The demo seeds + rolls back, never TRUNCATEs** (D4.4). `make news-demo` adds its own `demo-` stories
  in a transaction and filters the display to them, rather than clearing the world — a TRUNCATE takes an
  exclusive lock and would block on the scheduler/tick. Deterministic, token-free, non-polluting.
**Changed:** `src/world/store.py` (news_coverage + reads/writes), `src/formats/news_select.py` (new),
`src/formats/news.py` (rewritten), `src/formats/news_demo.py` (new), `src/config.py` (NEWS_* dials),
`tests/test_news_coverage.py` + `test_news_select.py` + `test_news_desk.py` (new), Makefile (`news-demo`),
README / `.env.example` / `docs/ADMIN_MANUAL.md`, PHASE_D_OVERVIEW tracker (D4 ✅).
**Why:** the news desk is half the heart of Phase D — a world that *moves* (D3) is only worth featuring
if the station *reports* it like a real one. Coverage memory is what turns "a fact happened" into "an
update on the story we've been following," and the continuity gate is what keeps a 24/7 desk from
drifting a story's name or facts across the day.
**📣 Postable:** `make news-demo` — a 20-line, token-free trace of one story going breaking → repeated →
repeated-and-evolved → "yesterday" across a simulated day, while another is steadily trailed. Great
short clip of the desk "thinking."
**Next:** D5 (broad anti-repetition so talk + news never loop phrasing), or D10 (figures & quotes so the
news can *attribute* — "X said …").
Commit: (this session) · Clips: (record `make news-demo`)

---

## 2026-06-29 — Phase D — naturalness pass on the talk prompts (route A)
**Focus:** the DJs sounded official/stiff and segments mirrored each other — fix the *register* (how
they speak), which is separate from the persona (the cast cards) and from the looping problem (D5).
**Decisions:**
- **Persona vs delivery are two layers.** Who a DJ *is* lives in `docs/canon/90-cast.md` (cards, verbal
  tics, sample lines — already good); *how they talk on air* is shaped by the format/writer **prompts**.
  The stiffness was in the prompts + tight word budgets, not the personas.
- **Route A = talk only, wording-only.** Rewrote `writers/conversation.py` `orchestrate` to be
  natural-first and POSITIVE (contractions, varied rhythm, react-and-build, lean on each card's
  voice/tics) instead of a wall of "NEVER…" constraints; nudged the `showrunner` to pick a HUMAN angle
  (a feeling/detail/disagreement), not just a fact; loosened `convo_words_*` (450-600 → 550-750) so it
  can breathe. Left the showrunner→orchestrate→continuity **structure**, the framing/speaker logic
  (D6), and the gate seams untouched.
- **News stays for D4.** Its stiffness ("a trusted settlement desk" + rigid "exactly N headlines") is
  in `news.py`, which D4 rewrites — so I left a note in the D4 pack to carry these same principles in
  rather than patch a desk that's about to be replaced.
- **Marked the injection points.** Added comments in `orchestrate` (and notes in the D5/D9 packs)
  reserving where future inputs slot in WITHOUT conflicting: D5's "avoid recently-aired topics" line,
  D9's per-host event-log memory, D10's attributable quotes. They compose with route A, don't replace it.
**Changed:** `src/writers/conversation.py` (showrunner + orchestrate prompts), `src/config.py`
(`convo_words_*`), `docs/PHASE_D_{NEWS_DESK,FRESHNESS,VOICE_ROSTER}_TASKS.md` (notes), this DEVLOG.
**Why:** models go stiff when a prompt is mostly *don'ts* and the budget forces compression; leading
with the character's own cadence + positive guidance + room to breathe is what reads as human.
**Verify:** `make conversation` (or `make format FMT=talk`) — the exchange should use contractions,
uneven turn lengths, and each host's tics; `ruff` + `pytest tests/test_conversation.py` green (4).
**Next:** D4 (news desk, with the naturalness principles baked in) — or D5 for the on-air anti-repeat.
Commit: (this session) · Clips: (none yet)

## 2026-06-29 — Phase D — D3: the World Engine (the keystone) — D3.0–D3.5
**Focus:** make the +600y world *move on its own* — a nightly world tick that invents and advances
bible-consistent, arced stories, behind the same safety/continuity gates as the writers' room.
**Decisions:**
- **Story log = stories + beats-as-events** (D3.0). A new `stories` table holds the narrative spine;
  each beat is an `events` row linked by `story_id` (+ `beat_kind`), so beats keep their in-world
  datetime and the B2 clock frames them for free — reuse, not a parallel beats table. **Arc stage**
  (`rumoured→upcoming→happening→developing→past`) is a documented module constant with forward-only
  legal transitions, kept distinct from `events.status_of`'s temporal status.
- **The story log is tick-owned, persists forever.** `source='tick'` (reusing D1.2's split): a
  `seed-canon` refresh leaves stories/beats/tick-events standing; only `reset-world` clears them.
  Schema landed via idempotent migration (`ADD COLUMN IF NOT EXISTS`), never truncate-reseed.
- **Batch built FIRST, behind the seam** (audit fix). `providers/llm.generate_batch` is the only place
  the vendor batch SDK is imported; `world_tick` calls it like `generate`. `LLM_BATCH_ENABLED=false`
  runs synchronously for a fast local check. Gate calls are batched (50% off) + the bible is cached.
- **Gate every proposal; never write flagged/contradictory content** — safety + a world-continuity
  check (against canon *and* the story's own prior beats); regenerate-once-then-drop for new stories,
  skip-this-tick for advancements (the story stays, retried next tick).
- **Variety is engineered, not hoped for** (D3.3): domain balancing (spotlight quiet domains),
  similarity de-dup (semantic via D2 over the `story` corpus + a structural Jaccard fallback so it
  degrades cleanly without D2), and a new-vs-advance pacing cap on the living-world size.
- **Separate jobs** (D3.4): the tick WRITES world state; the C2 scheduler READS it for audio. The tick
  is the nightly C5 batch (`make world-tick`), one-shot, transactional, loud-on-failure (exit non-zero,
  store rolled back) — explicitly NOT folded into `scheduler.top_up`.
**Changed:** `src/world/store.py` (story log: `stories`/beat link, arc constants + `can_transition`,
`insert_story`/`insert_beats`/`advance_story`/`active_stories`/`recent_stories`/`story_beats`/`get_story`,
scoped `clear_world`); `src/world/world_tick.py` (new — `run_tick` + the propose/advance/gate/dedup
pipeline + CLI `main()`); `src/providers/llm.py` (`generate_batch` + `BatchRequest`/`BatchResult`);
`src/config.py` + `.env.example` (`LLM_BATCH_*`, `WORLD_TICK_*`); `Makefile` (`make world-tick`);
`tests/test_story_log.py` + `tests/test_world_tick.py` (30 new tests, LLM mocked, DB tests roll back);
README world-tick section; `docs/ADMIN_MANUAL.md` D3 how-tos; PHASE_D_OVERVIEW tracker.
**Why:** the world tick is what fixes "thin conversations" — a moving present on top of the static
bible is what makes the station worth coming back to. Building Batch behind the seam first (the audit's
call) keeps the cost lever from leaking into the tick and makes the nightly volume affordable.
**📣 Postable:** "Settlement Radio's world now writes its own news overnight" — a two-tick run showing a
story appear (`upcoming`) then advance (`happening`) with correct past/now/future framing.
**Next:** D4 (the news desk that *reports* this log on air) — now unblocked.
**Verify:** `make seed` then `LLM_BATCH_ENABLED=false make world-tick` twice — tick 1 creates stories,
tick 2 prints `advanced N running stories` with beats appended + stages moved. `pytest` green (129).
Commit: (this session) · Clips: (none yet)

## 2026-06-28 — Phase D — full canon audit campaign: the bible authored (18 cornerstones, ~7→193 facts) + RAG emotional-tag pass
**Focus:** ran `docs/canon/AUDIT.md` end-to-end on **every cornerstone an external writer expanded** —
validate → fix → overwrite → re-seed, file by file — taking the world from a handful of scaffold facts
to a complete, internally-consistent bible. Then closed a retrieval gap by enriching emotional tags.
**The campaign — 18 files audited & merged** (each scaffold/stub → 5 prose sections + 9–12 facts):
`00-station`, `05-worlds`, `10-history`, `20-peoples`, `25-other-minds`, `30-polities`, `35-economy`,
`40-law`, `45-conflict`, `50-daily-life`, `55-language`, `60-faith`, `65-arts`, `70-music`,
`75-technology`, `78-communication`, `80-cosmos`, plus structured `90-cast` (2→**10 DJs**) and
`95-events` (1→**9 events**). Canon grew **~7 → 193 facts** (01-time pre-authored).
**Decisions / recurring fixes:**
- **The no-FTL / compact-sublight premise was the spine.** Submissions kept reaching for FTL — "jump
  drives" (35/05/10), "shrink the distance between worlds" (30/10), light-years / "years to cross"
  (80/05), time-dilation + cryo "suspended animation" (70/60/55/10). All reframed to the established
  sublight / weeks-apart / compact-cluster premise (`75`). `05-worlds` (the scale-defining file) now
  *affirms* it; `35`'s fuel economy was flipped to match `75` (fuel cheap, **machines** scarce).
- **"The Silence" is now defined.** `65/60/55/45` all referenced it; `10-history` defines it (the
  relay-network collapse), so the term is coherent bible-wide.
- **Two operator calls held everywhere:** **humanity stays alone** — alien *cast* (`90`) and alien
  *prose* (`80`) reworked to humans per `25-other-minds`; and **real religions → strains, not names**
  (`60/55` keep impermanence / covenant / absorptive-cosmology, naming no real faith).
- **`70-music` Part B deferred to D7** (contemporary bands built on interstellar/relativistic physics +
  an AI gag + dystopian tone); `70` kept thematic.
- **Mechanical constants across all files:** stripped leaked-chat preambles + `STATUS:` lines;
  `core worlds` → `the core` (the Star-Wars echo); real names → invented/canon (New Geneva→**Concordance**,
  Titan's Landing→**Forge**; Lunar/Venera/Proxima/Kepler/Uniform-Commercial-Code gone); hardcoded
  future-dated "past" years → relative; **reformatted inline `Tags:` facts → numbered + `- **Tags:**`
  child bullets** (40/35/30/25/20/10/05 wouldn't have parsed otherwise — one had its whole first section
  un-`##`'d and would have seeded nothing); British spelling; em-dashes. **Zero non-conforming tags**
  corpus-wide.
- **Cast voices (operator call: keep full cast, wire placeholders):** 9 of 10 logical voices were
  missing from `tts.py`; added as placeholders aliasing the two real presets (all resolve/seed), with a
  `D9.2` heads-up — DJs share voices until the D9 voice pass (grep `tts.py` for "PLACEHOLDERS (D-cast)").
- **RAG emotional-tag pass:** the structured (tag) path was blind to feeling (loneliness=1 fact;
  grief/joy/melancholy/courage/kindness=0). Used the corpus's *own* semantic index to find the facts
  nearest each emotion, curated out the small-model cross-valence noise, applied **51 tag-additions**
  across 15 files. Every palette emotion now resolves to **2–9 on-target facts**; semantic recall was
  already solid (spot-checked: Lumen 0.78, machine-minds 0.66, war 0.63).
**Changed:** all 18 `docs/canon/*.md` cornerstones (audited overwrites + emotional tags);
`docs/canon/TAGS.md` (+`djs`, `midnight`, `newyear`, `physics`, `fusion`, `religion`);
`src/providers/tts.py` (9 placeholder voices ×3 backends); `docs/PHASE_D_VOICE_ROSTER_TASKS.md` (D9.2
heads-up). Two memories saved: `keep-world-consistent-with-spirit`, `rework-aliens-keep-alone-premise`.
Final seed: **canon 193, cast 10, events 9; embeddings_canon 193 (in sync); 0 non-conforming tags.**
**Why:** the audit gates caught real breakers an unattended station would have aired — FTL contradicting
the load-bearing premise, real author/franchise/place echoes, floating-year staleness, dropped-figure
dangling refs, fact blocks that wouldn't parse, and the aliens-vs-alone-premise contradiction. The world
is now consistent end to end; the static substrate is "enough" (the moving *present* comes from the D3
tick, not more canon), and the structured RAG path can finally *see emotion*.
**Next:** D3 (World Engine) for the moving present; D9 for distinct DJ voices; ops-harden by pinning the
local embedding model on the VPS so semantic recall survives offline. A `make buffer` would confirm DJs
now spread across the full event calendar + richer canon.
Commit: (pending)  ·  Clips: (none)

## 2026-06-27 — Phase D — SPIRIT.md brief + canon-loader guide-skip fix
**Focus:** wrote the world's creative brief for the (human) canon writer, and fixed a loader bug that
authoring docs surfaced.
**Decisions:**
- **`docs/canon/SPIRIT.md`** — the spirit & tribute brief: the idea (a love letter to 20th-century SF
  at its best), the **IP firewall** (name authors *here*, never in canon — take the spirit, leave the
  stuff), "good old SF, no modern-AI tropes," the authors we draw on (Asimov/Clarke/Heinlein/Bradbury/
  Cordwainer Smith/Stapledon · Le Guin/Lem/Strugatskys/Miller/Brunner/Butler/Delany/Russ/Tiptree) with
  a TAKE/AVOID line each, the 9 core themes mapped to cornerstone files, the house tone, and worked
  "influence → original canon" examples. Linked from `docs/canon/README.md`.
- **Bug fix (load-bearing):** `canon_source._sorted_canon_files` loaded **every `*.md` except
  README** — so `TAGS.md` (and any brief) **leaked into the cached series bible the DJs read**, and
  `SPIRIT.md` (which names real authors) would have put author names *on air* — an IP-rule breach.
  Fixed the rule to the actual convention: **a cornerstone carries a numeric prefix**; non-prefixed
  files (README/TAGS/SPIRIT/notes) are authoring guides and are skipped. Locked with a regression test
  (`test_folder_skips_non_prefixed_authoring_guides`).
**Changed:** new `docs/canon/SPIRIT.md`; `canon_source._sorted_canon_files` (prefix filter + docstring);
`tests/test_canon_source.py` (+1 test, 99 green); `docs/canon/README.md` (start-here pointer + the
skip rule). Verified: guides not loaded, no author name in the DJ bible, canon still 55 facts.
**Why:** the writer needs a single creative north star; and an authoring doc reaching the broadcast is
exactly the silent failure the IP rule can't afford — the prefix rule makes the folder safe for briefs.
**Next:** D3 — the World Engine (the human can now script canon against SPIRIT.md + TAGS.md).
Commit: (pending)  ·  Clips: (none)

## 2026-06-27 — Phase D — D2.7: tag vocabulary + filled the scaffold canon
**Focus:** gave the human a documented tag **palette** and grew the RAG corpus from 7 facts to **55**
by authoring tagged canon facts across all 16 previously-empty cornerstone scaffolds. Added at the
human's request (content, not code).
**Decisions:**
- **Tags are free-form, not a code enum.** New `docs/canon/TAGS.md` is a *recommended* palette + the
  two hard rules (lowercase single words — the query side tokenises on non-alphanumerics; the
  contiguous `- **Tags:**` child bullet). Linked from `docs/canon/README.md` §5. The fear of "breaking
  code with tags" is unfounded: worst case is a malformed bullet, which **fails loud** at seed.
- **Filled all scaffolds (3 atomic facts each), consistent with the established world** — sublight
  travel / weeks of distance, Earth a fondly-remembered origin, settlement time, the Lumen Festival,
  the drifting relay station — and the IP boundary (tradition/themes only). Fixed the one open
  worldbuilding choice in `25-other-minds`: humans are **alone** (only rumour); machine minds are
  tools, not persons (kept distinct from the out-of-fiction AI disclosure).
**Changed:** new `docs/canon/TAGS.md`; `## Canon facts` authored in `05-worlds`…`80-cosmos` (16 files);
`docs/canon/README.md` §5 (links TAGS.md, drops the stale "D2's job" line); D2.7 added to
`PHASE_D_RAG_TASKS.md`. Re-seeded: canon 7→55, embeddings_canon=55 (match); `ruff`+`pytest` green (98).
**Why:** the original 7-fact corpus was too thin for semantic recall to shine; a controlled vocabulary
keeps future tagging consistent. Both paths now demonstrably work — e.g. "are we alone" misses on tags
(nothing tagged that word) but the semantic half still finds the right fact.
**Next:** the new world content is a **first draft to review/refine** (all git-reversible, re-seedable);
then D3 — the World Engine.
Commit: (pending)  ·  Clips: (none)

## 2026-06-26 — Phase D — D2: Semantic retrieval / RAG goes live (D2.0–D2.6)
**Focus:** activated the stubbed vector seam so the writers' room recalls canon by **meaning**, not
just date/tag — the bible is multi-file after D1, so both embeddings triggers fire.
**Decisions:**
- **Embedding provider (D2.0):** Anthropic has NO first-party embeddings endpoint (confirmed via the
  `claude-api` skill), so the embedder is a real third-party pick. Chose a **local** open
  sentence-transformer — `all-MiniLM-L6-v2`, **dim 384**, provider `local` — free, no key, no network,
  CPU-cheap on the CX33 (the Kokoro stance). Hosted (Voyage) stays switchable behind the seam. `dim` is
  load-bearing config (the pgvector `vector(N)` width) → a model swap = re-embed + column migration.
- **ONE polymorphic table, not canon-only (audit fix):** `embeddings(corpus, entity_id, text, source,
  tags, embedding vector(384))` + HNSW **cosine** index — multi-corpus from day one so D3 events / D10
  figures reuse `insert_embeddings`/`search` by passing their own `corpus`. `source` carries the
  seed/tick split; `entity_id` is a soft cross-table ref (cleanup is app logic, no FK cascade).
- **Seam discipline held:** vector SQL only in `store.py` (bound as `%s::vector` text literals — no
  pgvector *Python* dep); the embedding model only behind `providers/embeddings.py`; `context._select_canon`
  calls the `retrieve()` contract. `retrieve` **degrades to `[]`** on any backend failure → the room
  falls back to structured retrieval, never dies.
- **Hybrid selection:** `_select_canon` unions semantic top-k (`context_canon_top_k=6`) with the
  tag-match, semantic-first, falling back to all canon when neither hits.
**Changed:** `config.py` (`embeddings_*`, `context_canon_top_k`); `store.py` (pgvector schema +
`embeddings` table/index, `insert_/delete_embeddings`, `search`/`search_canon`, `canon_by_ids`,
`embeddings_count`, `clear_world` honours the §2a matrix); `providers/embeddings.py` (`embed` via
sentence-transformers, model cached once, retried, dim-validated; real `retrieve`); `seed.py` (embed
canon on seed); `docs/canon/00-station.md`+`01-time.md` (facts tagged, D2.5); `requirements.txt`
(sentence-transformers; pgvector is a Postgres-side install, README-documented); tests
(`test_embeddings.py` + hybrid `_select_canon` in `test_context.py` — provider mocked, one skip-guarded
SQL-ordering test); README/.env.example/ADMIN_MANUAL.
**Why:** local matches the project ethos and keeps text cost near-trivial (TTS, not embedding, is the
ceiling); the polymorphic table avoids a mid-phase refactor when D3/D10 need to be searchable.
**📣 Postable:** "Taught the AI radio station to remember its own lore by *meaning* — ask it about
'loneliness' and it surfaces the right canon even though nothing is tagged that word." (commit + a
`make context TOPIC=…`-style clip.)
**Next:** D3 — the World Engine (the nightly generative tick), which embeds its events on write into
this same table (`corpus='event'`).
Commit: (pending)  ·  Clips: (none)

## 2026-06-26 — Phase D — D2.0: pick the embedding provider (RAG DECISION)
**Focus:** the first step of D2 (semantic retrieval) — decide what computes the vectors behind
`providers/embeddings.embed()` and record why, before any code touches pgvector or the seam.
**Decisions:**
- **Anthropic has no first-party embeddings endpoint** (confirmed via the `claude-api` skill), so the
  embedder is a genuine third-party choice, *not* a Claude call. It stays behind the
  `providers/embeddings.py` seam like `llm`/`tts`.
- **Local/open over hosted.** Chose **`sentence-transformers/all-MiniLM-L6-v2`** (dim **384**), provider
  `local`. Free, unlimited, no new secret, no network, CPU-cheap on the CX33 — the Kokoro stance. A
  hosted path (Voyage) stays switchable behind the seam (`embeddings_provider="voyage"` + a key) but is
  not the default unless quality demands it.
- **`embeddings_dim` is load-bearing config, never a literal.** It is the N in the pgvector `vector(N)`
  column (D2.1); a model swap = re-embed + column migration. MiniLM vectors are L2-normalised → the
  vector index will use the **cosine** opclass (D2.1).
**Changed:** `src/config.py` — new `# --- Embeddings (D2) ---` section (`embeddings_provider`,
`embeddings_model`, `embeddings_dim`). No `.env.example` change (local backend needs no key). `ruff`
clean; settings import verified.
**Why:** the bible is now big and multi-file (D1), so both embeddings triggers fire (context outgrows
the cache *and* we want meaning-based recall); local matches the project's local/free ethos and keeps
text cost near-trivial (TTS, not embedding, is the ceiling).
**Next:** D2.1 — enable pgvector + the ONE polymorphic `embeddings(corpus, entity_id, …)` table + the
vector search query in `store.py`.
Commit: (pending)  ·  Clips: (none)

## 2026-06-26 — Phase D — D1: Canon → Folder (the static substrate)
**Focus:** turned the single `docs/CANON.md` stub into a real, growable `docs/canon/` **folder** bible
the seeder reads whole — folder layout + conventions, a folder-loading parser, config/seed/context
wired to the folder, the migrated stub, and a full scaffold set.
**Decisions:**
- **Folder = source of truth; one parser, two read paths.** `canon_source.load_folder`/
  `load_series_bible_folder` merge `*.md` in **integer**-prefix order (`2 < 20 < 100`); single-file
  `load()` kept for back-compat/tests. Fact ids namespaced `canon-<file-stem>-<n>` (globally unique,
  re-seed-stable); duplicate cast/event slugs **and** duplicate file stems fail loud.
- **Series bible = "every `## ` section that isn't structured"** (`canon facts`/`cast`/`events`), so
  new cornerstone prose is picked up automatically — no registration.
- **Tag affordance** parsed now (`- **Tags:**` child bullet → `CanonFact.tags`), population deferred to
  D2.
- **File-vs-folder auto-select** (`settings.canon_dir` + `canon_path`): folder wins when it has
  content, else the legacy file — no extra flag.
- **Seed split (load-bearing):** `make seed-canon` (SAFE everyday — reloads folder-owned
  canon/cast/`source='seed'` events, leaves `source='tick'` intact) vs `make reset-world` (DESTRUCTIVE,
  warns+confirms). New `events.source` column lands via an **idempotent migration**, not a
  truncate-reseed; `clear_world(scope=…)` clears exactly its matrix column. `make seed` → safe alias.
- **Scaffolds don't leak:** the 16 new cornerstone files keep guidance *above the first `## `* + an
  empty `## Canon facts`, so they seed zero rows and zero bible prose until authored.
**Changed:** `src/world/canon_source.py`, `src/world/store.py` (source column + migration + scoped
clear), `src/world/seed.py` (seed_canon/reset_world + CLI), `src/world/context.py`, `src/config.py`
(Canon section), `Makefile` (seed-canon/reset-world), `tests/test_canon_source.py` (+folder/selection
cases); migrated `docs/CANON.md` → `docs/canon/` (00-station, 01-time, 90-cast, 95-events) + retired
the stub to a pointer; added `docs/canon/README.md` + 16 scaffold cornerstone files; updated
`README.md`, `.env.example`, new `docs/ADMIN_MANUAL.md`. Verified: tick event survives `seed-canon`,
cleared by `reset-world`; counts lossless (7/2/1); `ruff` + `pytest` (85) green.
**Why:** everything else in Phase D stands on the bible — RAG (D2) needs a canon worth embedding, the
world engine (D3) needs a substrate, the news desk/DJs draw on it; and the seed split must exist
*before* D3 writes irreplaceable tick state, or a one-line bible edit would nuke the living world.
**Next:** D1 complete — flip the overview tracker; begin D2 (semantic retrieval / RAG) or D6
(programming backbone), per the parallel tracks.
Commit: (uncommitted)  ·  Clips: (none)

## 2026-06-26 — Phase D — planning: full task-pack set + external-audit tightening (Claude chat)
**Focus:** prepped the *entire* Phase D ("The Living World") as a master plan + per-sub-pack task packs,
written against the as-built C0–C4 seams, then ran an external audit over it and tightened the result —
all docs, no code, so D1/D6 can start clean.
**Decisions (the durable ones):**
- **One master `PHASE_D_OVERVIEW.md` + 11 sub-pack `_TASKS.md` files (D1–D11)**, each in the
  `PHASE_C_TASKS` micro-format (Goal/Do/Done-when + "Explicitly NOT"), with a status tracker that drives
  sequencing. Two tracks: the **living-world spine** (D1 Canon→Folder → D2 RAG → D3 World Engine → D4
  News Desk, with D5 Freshness + D10 Figures&Quotes riding D3) and the **station-craft track** (D6
  Programming → D7 Production → D8 Commercials, + D9 Voice/Roster). **D1 and D6 are the buildable entry
  points;** D11 (Operator Manual + integrated acceptance sim) is the capstone, done last.
- **Static vs dynamic is the load-bearing split.** Canon = a hand-authored markdown **bible folder**
  (`docs/canon/`); the world = **dynamic DB state generated by an autonomous nightly tick** (gated, never
  per-story-approved — you control the bible, not each story). They never mix; **world history persists
  forever, never pruned like audio** (only regenerable mp3s are GC'd).
- **`make seed-canon` (safe, everyday) vs `make reset-world` (destructive, warned)** + a global
  **state-ownership/seed/backup matrix** (overview §2a): `reset-world` wipes world+canon only (never
  grid/tracks/sponsors); backups cover the tick-generated world + hand-entered sponsors.
- **Music = cultural artifacts, not files:** tracks carry lore (artist→figure, album, era, story);
  *playable files* vs *talked-about culture* (the world references far more music than it can play).
  **Commercials are generated fresh each airing (no rotating reel);** richer levels (bed/multi-voice/
  testimonial) reuse D7/D9/D10.
- **"When/what to play" is automation, not the LLM:** the programming **grid is structured YAML→DB** with
  a per-program **clock** (dedicated music blocks vs interspersed); the track **selector is rule-based**
  (mood/world/freshness/era/featured). The LLM only writes the words around the audio.
- **The world *speaks* (D10):** in-world figures + attributable quotes → news attribution, DJ references,
  and (D9×D10) distinctly-voiced **soundbites/guests** beyond the two hosts.
- **External audit (green-light) tightened before coding:** reworded the approval model (bible/patterns,
  not per-story); added the §2a matrix; made the **embeddings table polymorphic** (one multi-corpus table,
  not canon-only); a **batch-capable `llm` seam** so Batch doesn't leak into `world_tick`; **migrations,
  not truncate-reseed,** once the world is alive; **cost telemetry** in the console; a **public-feed vs
  private-console** boundary; admin is **VPS-only / single-operator** (panel itself is Phase E).
**Changed:** new `docs/PHASE_D_OVERVIEW.md` + `docs/PHASE_D_{CANON_FOLDER,RAG,WORLD_ENGINE,NEWS_DESK,
FRESHNESS,PROGRAMMING,PRODUCTION,COMMERCIALS,VOICE_ROSTER,FIGURES_QUOTES,ADMIN_MANUAL}_TASKS.md` (12 files);
edited `docs/ROADMAP.md` (Phase D pointer + approval reword). No code.
**Why:** Phase D adds most of the remaining functionality, so getting the *operating model* right on paper —
static/dynamic split, seed/reset safety, seam reuse, autonomy boundaries — is what lets it be built
pack-by-pack without a mid-phase rewrite. The audit confirmed the plan is sound and only needed tightening.
**📣 Postable:** "Planned the whole 'living world' phase as 11 build packs — an AI radio world that
generates its own evolving stories, news, music culture, and on-air guests, then ran an external audit and
green-lit it." (Build-in-public: the planning rigor + the static-bible/dynamic-world split.)
**Next:** begin building **D1 (Canon → Folder)** — the foundational pack — or **D6 (Programming)** in
parallel (both `Ready`).
Commit: <pending>  ·  Clips: —

**Focus:** picked the actual Hetzner box for C5 before provisioning.
**Decisions:** deploy on a **CX33** (4 vCPU Intel/AMD, 8 GB RAM, 80 GB SSD, €11.06/mo). The old
CX22 the docs named is retired; its like-for-like successor is the CX23 (2/4/40, €7.37). We upsized
to the CX33 and stay on the **Intel/AMD "CX"** line (not Ampere/ARM "CAX").
**Changed:** docs/PHASE_C_TASKS.md (C5 provisioning + box-decision note, C2.5 + C6 spec refs),
docs/ROADMAP.md (YOU + C5 lines), docs/DEVLOG.md (this entry + superseded note on the original
planning decision).
**Why:** C6 warns a 2-vCPU box may not finish a full day's CPU-only Kokoro render overnight, so the
extra cores buy headroom for ~€4/mo more; 80 GB gives the segment disk room. Resizing CPU/RAM *up* is
a reversible few-clicks reboot while disk only grows — so the bigger box is the low-regret pick. CX
over CAX for best-tested Liquidsoap/ffmpeg/Kokoro support.
**Next:** provision the CX33 (account, location, image, SSH key), then start C5 install.
Commit: <pending>  ·  Clips: —

## 2026-06-24 — Phase C — C4: never-dead air — fallback chain + health checks

**Focus:** make the stream survive any single failure. Two halves: a playout **fallback chain** that
never goes silent (with a *pre-rendered* evergreen pool that survives a generator outage), and
**health checks** that make a failure visible (low buffer / dead scheduler / unreachable stream) with
an alert. Fixes orientation open-risk #6 ("single points of failure with no live fallback").
**Decisions:**
- **The full fallback chain lives in Liquidsoap, not the scheduler** (`config/radio.liq`): a single
  `fallback(track_sensitive=false, [scheduled, evergreen, music_bed, ident, tone])`. Each lower tier is
  always-available audio, so an empty/absent scheduled playlist (buffer drained) degrades to a clean
  spoken evergreen, then a bundled music bed, then the disclosure ident, and only as a last resort a
  quiet sine — never silence. An absent tier is a `source.fail()` (the never-available source), so every
  tier is built unconditionally and *availability* decides what airs. Keeping the chain in playout (vs.
  injecting evergreen into the schedule) is the right layer: the scheduler decides programming, playout
  owns never-dead air. Type-checked with `liquidsoap --check`.
- **The evergreen POOL is pre-rendered and GC-exempt — the load-bearing choice.** C0's evergreen was
  render-on-demand into the failed slot's `<id>.mp3` (a one-shot, GC'd like any render) — useless if the
  outage that needs it is *Kokoro itself*. C4 adds `evergreen.render_evergreen_pool()`: render each
  static script ONCE to a stable `evergreen-{i}-{provider}-{voice}.mp3` and reuse it, so a clean spoken
  segment is ready *before* the outage. Exempted from the C2.5 prune by the `evergreen-` name prefix
  (same render-once/reuse pattern as the disclosure ident; on-demand evergreens keep their `<id>` name
  and are still GC'd).
- **New `src/fallback.py` owns "prepare the never-dead assets," called best-effort at the top of every
  `top_up`.** It renders the pool + ident (cached after first run — cheap) and writes the evergreen
  playlist Liquidsoap watches. Best-effort + guarded so prep can never raise into a top-up, and a prior
  healthy run's cached clips remain regardless — the whole point is readiness *before* the failure.
  Exposed as `make fallback` for a one-off prepare + verify.
- **Orchestration resilience was already mostly there (C2): a failed slot is retried→skipped, a total
  failure stops the run and leaves the existing buffer.** C4's addition is that when the buffer
  *fully* drains, playout has somewhere real to go (the pool) instead of a tone.
- **New `src/health.py` (`make health`) — three pure-read checks + a two-mode alert.** Buffer runway
  below `health_min_runway_minutes`; no top-up within `health_max_run_age_minutes` (the scheduler now
  writes a `last_topup_at` heartbeat into `schedule.json`); stream mount unreachable (optional). The two
  run-detectors are complementary: the heartbeat catches "the job isn't running," the buffer/stream
  checks catch "it runs but the air is at risk." On an issue: log error + optional webhook POST + a
  healthchecks.io-style `/fail` ping; on a clean pass: a success ping (dead-man's switch, so a health
  timer that dies is itself caught). Exits non-zero when unhealthy for cron/systemd. All alert URLs
  default empty (log-only). Avoided a circular import by having the scheduler only *write* the heartbeat
  dict key (health imports the scheduler's state helpers, not vice-versa).
- **Config:** new `fallback_evergreen_playlist_path` and a `health_*` block (runway floor, max run age,
  stream URL, ping URL, webhook URL, timeout). Liquidsoap reads the evergreen playlist + ident paths
  from env (`FALLBACK_EVERGREEN_PLAYLIST_PATH`, `FALLBACK_IDENT_PATH`).
**Changed:** new `src/fallback.py`, `src/health.py`; `src/evergreen.py` (`render_evergreen_pool` +
`EVERGREEN_NAME_PREFIX`); `src/scheduler.py` (call `ensure_fallback_assets`, write `last_topup_at`
heartbeat, exempt `evergreen-*` from prune); `config/radio.liq` (the 5-tier chain); `src/config.py`
(`fallback_*` + `health_*`); `Makefile` (`make fallback`, `make health`); `.env.example`; `README.md`;
new `tests/test_fallback.py` (+4) and `tests/test_health.py` (+9), `tests/test_scheduler.py` (+2:
heartbeat, evergreen-pool exemption; `_wire` neutralizes the fallback prep). `ruff` clean;
**78 tests pass** (was 62). `liquidsoap --check config/radio.liq` green.
**Why:** an unattended 24/7 stream cannot go dead or invisibly stop. The fallback chain guarantees the
air; pre-rendering the evergreen pool while healthy is what makes the chain survive the very outage
(TTS/Claude/DB down) that drains the buffer; the health checks turn a silent failure into an alert
before the buffer is gone. All three are hard prerequisites to exposing the stream (C7/C8) and to the
C9 soak.
**Verification:** `liquidsoap --check config/radio.liq` passes (the chain type-checks; an empty/absent
playlist falls through to the pool). `make health` against an empty schedule correctly reports low
buffer + missing last run and exits 1. The pool-render/playlist-write/idempotence/partial-failure paths,
the GC exemption, the heartbeat, and the buffer/last-run/stream checks + alert-vs-success-ping control
flow are covered deterministically by the new tests (no live Claude/TTS/network). Not yet exercised by
killing the generator against a live `make air` on the seeded stack with a rendered pool — that
end-to-end "pull the plug, stream keeps talking" check is the remaining human/soak (C9) verification.
**Next:** C5 — deploy to the Hetzner VPS (Postgres + Liquidsoap + Icecast + the scheduler top-up on
systemd/cron, `make health` on a timer, nightly `pg_dump` + `assets/` backups, secrets non-world-readable).
Commit: <pending>  ·  Clips: —

---

## 2026-06-24 — Marketing (GitHub) — MG3–MG5: README polish, licensing clarity, community health

**Focus:** the GitHub credibility pass from `docs/marketing/github.md` — make the repo read as a
serious, finished thing to a cold visitor (and to Anthropic devrel) without rewriting what already
works. Three tasks, all no-tech-dependency "do now" items: MG3 (README polish), MG4 (verify the
code-vs-world license split), MG5 (community health files).
**Decisions:**
- **MG3 — polish, not a rewrite.** The README already leads world-first and carries the tribute, so
  only additive edits: status badges under the wordmark (Apache-2.0 · CC BY-SA 4.0 · Built with
  Claude Code, with a commented `Live` placeholder for MG6), a one-line italic motto under the
  tagline, and aligning the disclosure wording to the canonical `DISCLOSURE_LINE` ("a work of fiction,
  **written and voiced by AI**" — was "generated with AI"). Used centered HTML `<img>` badges to match
  the README's existing centered-HTML header rather than the playbook's raw-markdown badges.
- **MG4 — the license split was already correct; only the framing was added.** `LICENSE-CODE`
  (Apache-2.0) and `LICENSE-CONTENT` (CC BY-SA 4.0) already exist and are right. Added a one-line
  tribute/original-world boundary to the README License section ("…a tribute to the genre, not derived
  from any franchise or author's work"). The drift MG4 flagged (MARKETING §4 / ROADMAP implying CC
  BY-SA is *future*) was already corrected in both docs — they say "already/existing CC BY-SA 4.0" — so
  no fix needed.
- **MG5 — net-new community files, deliberately light.** `CONTRIBUTING.md` is short and honest (built
  in public, **not** yet taking external code contributions, issues/ideas welcome) — keeping the build
  a clean end-to-end AI-authored artifact is the reason, stated as such. `CODE_OF_CONDUCT.md` is the
  standard Contributor Covenant v2.1 with contact `hello@settlementradio.com`. This completes the
  repo's "community profile" without inviting PRs that can't be handled solo.
**Changed:** `README.md` (badges + motto + disclosure wording + license framing line); new
`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`. No code touched.
**Why:** GitHub is the credibility anchor — the artifact eventually put in front of Anthropic (M4) —
so it has to read as intentional before the first "built in public" traffic arrives. These are
front-loaded because none depend on a later phase; only the live-demo link and funding button (MG6)
wait on C9/M1.
**📣 Postable:** the polished repo front page itself — the wordmark + three license/build badges +
world-first premise — is a clean screenshot for a "built in public, here's the repo" X post once the
launch sequence starts.
**Verification:** previewed the README (badges render, motto + disclosure read right);
`grep "written and voiced by AI"` matches README + `src/disclosure.py`, and "generated with AI" is
gone from the README. Community files present at repo root. GitHub-side items (repo topics, social
preview, pinning — MG2) are web-UI settings, not in the repo, so unverified here.
**Next:** MG5's remaining check is web-UI only (confirm repo topics/preview stuck). MG6 (live link +
FUNDING.yml + release tag) is gated on C9/M1. On the build side, Phase C continues at C4 (never-dead
air: evergreen pool + fallback chain + health checks).
Commit: <pending>  ·  Clips: —

## 2026-06-23 — Phase C — C2.5: disk retention — GC aired segment audio

**Focus:** bound `segments/` so a 24/7 station can't fill the VPS disk. C2 already prunes the
*schedule* (aired entries leave the state + playlist), but the **mp3 files themselves were never
deleted** — at ~1 MB/min of generated audio the 80 GB CX33 fills in a couple of months. C2.5 deletes aired,
unreferenced one-shot renders, and nothing else.
**Decisions:**
- **`prune()` lives in `src/scheduler.py` and runs at the end of every `top_up()`.** It keys off the
  same "aired + unreferenced" notion C2's schedule-entry pruning already uses (reusing `_load_state`,
  `_end_of`, `_duration_of`), wrapped so a GC failure can never break a top-up — the air is fed first;
  disk GC is housekeeping. Also exposed standalone as `python -m src.scheduler --prune` / `make prune`
  (no Claude/TTS) for verifying retention against what's on disk.
- **Deletes a `<id>.mp3` (+ its `<id>.json` sidecar) only when ALL hold:** (a) not referenced by any
  live schedule entry's `audio_path`; (b) its **air end** is more than `segment_retention_hours`
  (default 6) in the past — a grace window so a just-aired clip Liquidsoap may still be reading isn't
  yanked, and recent audio stays available for clip-cutting/debug; (c) it's a per-segment render under
  `segments_dir` (the `*.mp3` glob's scope).
- **The scheduler now writes a per-segment sidecar** (parity with the B6 buffer — `dataclasses.asdict`
  to `<id>.json`). This is the load-bearing choice: the sidecar records `air_time` + measured duration,
  the only reliable source of a render's **air end** *after* it has aired out of the live schedule.
  mtime alone breaks the grace window when `buffer_depth_hours` > retention (a deep-buffer render's
  mtime is hours before it even airs); the sidecar is the precise signal, mtime the fallback for
  pre-C2.5 renders.
- **Protect, never delete — the landmines:** the **shared disclosure ident** clip
  (`ident-disclosure-*.mp3`, reused by every ident slot per `src/disclosure.py`) is exempt by name
  prefix — deleting it because one ident slot aged out would break every future ident; **everything
  under `assets/`** is safe because the GC only ever globs `segments/`; and any file still in the live
  playlist/schedule survives via the reference check.
- **Optional `segment_retention_max_gb` backstop** (default off): if `segments_dir` still exceeds the
  cap after the age sweep, the oldest aired renders are evicted (ignoring the grace window) until under
  — the emergency valve so the disk is bounded even if retention is set too generous. Each sweep logs
  files + bytes reclaimed so disk management is auditable.
- **Config:** new `segment_retention_hours` + `segment_retention_max_gb` in a new "Disk retention"
  section; the ident name prefix stays a module constant (intrinsic, not a tunable).
**Changed:** `src/scheduler.py` (`prune()`, `_write_sidecar()` + its call in `top_up`, `--prune` CLI,
docstring step 7); `src/config.py` (the `segment_retention_*` block); `Makefile` (`make prune`);
`.env.example`; `README.md` (a "Disk retention" paragraph); `tests/test_scheduler.py` (+7 cases —
aged removal, referenced kept, in-grace kept, ident protected, mtime fallback, max-GB backstop,
sidecar written per render; existing C2/C3 tests' `_wire` now sandboxes `segments_dir`/retention so a
top-up's prune never touches the real `segments/`). `ruff` clean; **62 tests pass** (55 + 7 new).
**Why:** an unattended 24/7 stream that never deletes audio is a guaranteed disk-full outage in weeks —
a hard prerequisite to the C5 deploy + C9 soak. Keying file deletion off air end (via the sidecar, not
mtime) is what keeps the grace window correct at any buffer depth; exempting the shared ident and
`assets/` is what stops the GC from eating non-regenerable or render-once-reuse files.
**Verification:** `make prune` against a sandbox (an aired-10h render, a 1h-old render, the ident
clip) collected the aged render + its sidecar, kept the in-grace render, and left the ident untouched
(`prune_removed`/`prune_done` logged the file + bytes). The aged/referenced/grace/ident/mtime/backstop
paths and the per-render sidecar write are covered deterministically by the new scheduler tests
(stubbed generation, no live calls). Not yet exercised across a long live `make schedule` run on the
VPS — that, watching `segments/` stabilise over days, is the C9 soak check.
**Next:** C3 is already in; C4 — never-dead air: pre-rendered evergreen pool (kept at a GC-exempt path)
+ the full playout fallback chain + health checks/alerts.
Commit: <pending>  ·  Clips: —

## 2026-06-23 — Phase C — C3: AI disclosure in the air (spoken ident + on the player)

**Focus:** turn `Segment.disclosure` from a never-read field into behaviour — a short spoken
AI-disclosure ident woven into playout on a cadence, plus the same written line on the web surface
and ready for the YouTube description. Fixes orientation open-risk #5 ("AI disclosure is a field, not
a behaviour"); satisfies the CLAUDE.md disclosure rule + EU AI Act Art. 50.
**Decisions:**
- **New `src/disclosure.py` — the ident is static, canon-safe copy, like evergreen.** Two named
  constants are the single source of truth: `DISCLOSURE_SPOKEN` (the voiced line) and `DISCLOSURE_LINE`
  (the written line). Because it names nothing real and references no hour/event, it skips the
  safety/continuity gates entirely (same reasoning as `evergreen.py`) and needs **no Claude call**.
- **Rendered once, reused.** The line never changes, so the ident audio is cached to a stable file
  keyed by `(provider, voice)` — flipping `TTS_PROVIDER` or the voice re-renders rather than airing a
  stale clip; otherwise every ident slot reuses the one clip (Kokoro is slow, so this matters).
  Duration is stamped through the same C2 `formats.stamp_duration` chokepoint, so the scheduler times
  it like any other segment.
- **The scheduler weaves it, not Liquidsoap.** `top_up` places an ident every `disclosure_every_n`
  CONTENT segments (default 4), tracked by a `content_since_ident` counter **persisted in
  `schedule.json`** so the cadence stays steady across runs and pruning (not restarting each top-up).
  The ident is just another ordered playlist entry — so `config/radio.liq` needed **zero change**, it
  airs in order automatically. An ident render failure is logged and skipped (counter resets) — never
  blocks content or causes dead air, consistent with C2's never-dead-air stance.
- **One written line, shared.** `web/src/lib/disclosure.ts` holds the canonical web copy and the page
  renders from it (replacing the hardcoded disclosure paragraph); the same line belongs in the YouTube
  description (wired in C7) and grows into the C8 player. Backend `DISCLOSURE_LINE` and the web
  constant are kept saying the same thing (the two halves run independently per CLAUDE.md, so the
  string is intentionally mirrored, not shared across the seam).
- **Config:** new `disclosure_enabled` (master switch; false = local dev only), `disclosure_every_n`,
  `disclosure_voice` (mirrors `segment_vell_voice`). The ident *text* stays a module constant (intrinsic
  content, not a tunable), per the config-vs-constant rule.
**Changed:** new `src/disclosure.py`; `src/scheduler.py` (ident weaving + persisted counter);
`src/config.py` (a `disclosure_` block); new `web/src/lib/disclosure.ts` + `web/src/app/page.tsx`
(render from it); `Makefile` (`make ident` + FORCE); `.env.example`; `README.md`; `tests/test_scheduler.py`
(+3 cases: cadence, persistence, ident-failure resilience; existing C2 tests disable disclosure to stay
isolated). `ruff` clean; **55 tests pass** (52 + 3 new); web `tsc --noEmit` green.
**Why:** a public 24/7 broadcast must *say* it's AI-generated, audibly and on screen — a hard
prerequisite to exposing the stream (C7/C8). Weaving the ident in the scheduler (vs. a Liquidsoap
rotation) keeps disclosure on measured-duration airtime accounting and one ordered playlist, and makes
the cadence a config dial; persisting the counter is what stops a steady cadence from resetting every
top-up.
**Verification:** `make ident` (run with `TTS_PROVIDER=say` for speed) rendered the ident to an
**11.9s** clip and printed both the spoken + written lines; a second run logged
`disclosure_ident_cached` (reuse confirmed). The cadence/persistence/failure paths are covered
deterministically by the new scheduler tests (stubbed generation, no live calls). Not yet run through a
full live `make schedule` on the seeded stack — that, and a listen on the real Kokoro voice, is the
remaining human check.
**Next:** C4 — never-dead air: pre-rendered evergreen pool + the full playout fallback chain
(scheduled → evergreen → bed → ident) + health checks/alerts on stall / low-buffer / failed run.
Commit: <pending>  ·  Clips: —

## 2026-06-22 — Phase C — C2: honest length accounting + a real rolling scheduler

**Focus:** replace the one-shot B6 `build_buffer` with a real Layer-5 scheduler that knows what airs
when on *measured* durations, and wire Liquidsoap to air its decisions instead of looping the newest
file. Fixes orientation open-risk #4 ("no scheduler, and `length_target_sec` lies").
**Decisions:**
- **Schedule on measured audio, never the target.** New `Segment.actual_duration_sec`, set after
  render via `tts.probe_duration()` (ffprobe — added next to the other ffmpeg calls in the TTS seam,
  the only home for ffmpeg). Stamped at the single chokepoint every format returns through
  (`formats.make_format_segment`, so evergreen fallbacks are covered too) and on the direct B4
  `make_conversation_segment` path. `length_target_sec` stays the writer's word-count goal only;
  PHASE_B_ORIENTATION §5 showed it over-counts ~10–45%.
- **New `src/scheduler.py` (`make schedule`).** A *top-up* job, not a one-shot: load the persisted
  schedule (`segments/schedule.json`) → prune entries that have fully aired (or whose file vanished)
  → measure the remaining runway → generate back-to-back until the runway reaches
  `settings.buffer_depth_hours` of real audio → persist + write the ordered playlist. Idempotent and
  safe to run on any cadence (the C5 cron/systemd "nightly batch" is just this run on a timer).
- **`buffer_depth_hours` is THE dial** (default 3h) — the lead-time knob that later enables near-live
  by dropping toward ~0 + streaming TTS (Phase E). Reused the `buffer_` prefix so it satisfies both
  the spec's literal name and the config prefix convention (same call as C0's `convo_continuity_*`).
- **Never dead air on failure.** `make_format_segment` already falls back to evergreen on a *content*
  flag, so a raise is infra (Claude/TTS/DB): retry the slot (`schedule_failure_max_retries`), then
  SKIP to the next format; if a whole rotation fails, stop the run and let playout keep airing the
  existing buffer/fallback. The scheduler never writes a dead slot.
- **Playout wired to the schedule (the Layer 5 ↔ playout seam).** `config/radio.liq` no longer loops
  the newest file — it airs `segments/playlist.txt` via `playlist(mode="normal", reload_mode="watch")`,
  so the scheduler's *order* drives the stream and top-ups are picked up live with no restart; the
  never-dead fallback (bed/sine) still backs it when the playlist is empty/absent. `make serve` now
  airs the schedule, so added `make air` (= schedule + serve) as the live path.
- **Dropped `music` from the default rotation** (`buffer_rotation=["talk","news"]`) per the C2 note:
  its `[SONG]` slot has nothing to fill it until Phase D, so airing it would be a silent gap.
**Changed:** `src/segment.py` (+`actual_duration_sec`); `src/providers/tts.py` (+`probe_duration`);
`src/formats/__init__.py` (+`stamp_duration`, stamps the dispatch result); `src/writers/conversation.py`
(stamps the direct path); `src/config.py` (+`buffer_depth_hours`, `schedule_*`; rotation default);
new `src/scheduler.py`; `config/radio.liq` (playlist seam); `src/buffer.py` (manifest reports measured
total); `Makefile` (`schedule`/`air` + `INTERVAL`); `.env.example`; `README.md`; new
`tests/test_scheduler.py`. `ruff` clean; **52 tests pass** (46 + 6 new).
**Why:** an unattended 24/7 stream needs honest airtime accounting (or the playlist mis-times and
drifts) and a buffer with lead so a slow/failed generation run never starves the air — and the
scheduler's decisions must actually reach playout, or it's still just a folder of clips.
**Next:** C3 — disclosure in the air (spoken ident every N segments + on the player/description).
Commit: <pending>  ·  Clips: —

## 2026-06-22 — Phase C — C1: time-aware show framing (the afternoon-handover fix)

**Focus:** stop the room hardcoding a night→first-light handover at every hour — the bug that made
an afternoon talk slot say "all night / this morning / handover" and get (correctly) rejected by the
new C0 continuity gate. Land it right behind C0 so the gate isn't thrashing on a framing bug.
**Decisions:**
- New `src/world/framing.py` — a pure clock→`ShowFrame` mapper (the single home for "who's on air
  this hour and what's the situation"): deep/late night = Vell solo · first light = Vell→Wren
  handover · morning/afternoon/evening = Wren anchors · nightfall = Wren→Vell handover. Stateless
  and DB-free (host ids passed in), so it's unit-tested like `clock.py`/`events.py`.
- `showrunner()` and `orchestrate()` now take the frame (computed once in `compose_segment`) and drop
  its `part_of_day` + prose `situation` into the prompt in place of the constant. The time-check
  instruction is handover-placed only when the frame is actually a handover.
- Frame fields (`part_of_day`, `lead`, `handover`) ride in the Segment meta for the scheduler/debug.
- Window boundaries + daypart cutoffs are named module constants (intrinsic daily schedule, not
  config) — no new settings. Daylight hours can NEVER be framed as a handover (a unit test pins this).
- Scope: the two-DJ room only (the sole continuity-gated path, and the documented bug). Reassigning
  which solo DJ reads news/music by the clock, and wiring the buffer to avoid odd talk slots, is the
  scheduler's job (C2) — not folded in here. The Phase A single-DJ `writer.py` still hardcodes a
  night frame; it's off the gated 24/7 path, noted as a later cleanup.
**Changed:** new `src/world/framing.py`; `src/writers/conversation.py` (showrunner/orchestrate/
compose wired to the frame, meta enriched); tests `test_framing.py` (+ updated `test_compose_gate.py`
stubs for the new `frame=` kwarg). 46 tests pass.
**Why:** an unattended 24/7 station generates talk across the whole day; without hour-true framing it
manufactures self-contradictions the C0 gate then burns attempts regenerating before falling back to
evergreen. C1 removes the bug so the gate guards real problems, not a constant.
**Next:** C2 — honest length accounting (ffprobe) + a real rolling scheduler wired to playout.
Commit: <pending>  ·  Clips: —

## 2026-06-22 — Phase C — C0: the safety + continuity gates are real

**Focus:** turn the two no-op placeholders (the `safety_check` stub and advisory continuity) into
*blocking* gates, so nothing unsafe or self-contradictory can reach air.
**Decisions:**
- `safety_check` now returns a verdict (`SafetyResult`), not mutated text — it's a *gate*, not a
  rewriter. Two stages, cheap-first: a fast keyword/profanity pre-filter (no API), then an LLM pass
  on the `haiku` tier tuned to ALLOW in-world sci-fi conflict and flag only genuinely unsafe
  content. The "what to do when flagged" policy lives with the producers, not the gate.
- New `src/safety.py` (the gate, used by every producer) and `src/evergreen.py` (the safe fallback).
  Moved `safety_check` out of `writer.py` into `safety.py`; updated all four producers' imports.
- Policy: regenerate on a flag (bounded), then drop to an evergreen segment — a flagged/contradictory
  draft is NEVER rendered or written to `segments/`/the manifest. Single-DJ producers use
  `safety.generate_safe`; the two-DJ room runs a combined safety+continuity loop in `compose_segment`,
  feeding the continuity editor's note back into the rewrite.
- Named the continuity dial `convo_continuity_max_attempts` (matches the existing `convo_continuity_*`
  family + the config prefix convention), not the spec's illustrative `continuity_max_attempts`.
- Evergreen is render-on-demand from a small static pool for now; C4 promotes it to a pre-rendered
  pool + the full fallback chain + health checks.
**Changed:** new `src/safety.py`, `src/evergreen.py`; `src/config.py` (safety_* + continuity dial);
`src/writer.py`, `src/formats/news.py`, `src/formats/music.py`, `src/writers/conversation.py` (gates
wired); `.env.example`; tests `test_safety.py`, `test_evergreen.py`, `test_compose_gate.py` (40 pass).
**Why:** CLAUDE.md requires a real safety gate before any public broadcast, and a 24/7 stream can't
air the afternoon-handover contradiction the orientation caught. Gates + a never-dead fallback are the
hard prerequisite to exposing the stream (C7/C8).
**Next:** C1 — time-aware show framing — to land right behind C0, so the new gate isn't thrashing on
the hardcoded night→dawn handover bug (it would currently regenerate, then fall back to evergreen).
Commit: <pending>  ·  Clips: —

## 2026-06-21 — Pre-Phase-C — full audit + roadmap/architecture realignment + switchable TTS

**Focus:** a full audit of everything built (Phases A/B) and everything planned (C→F), then
realigning the docs to the *truth* and to an expanded product vision — plus a small code fix so both
TTS backends are fully switchable. No build-phase work; this is the session that makes Phase C
safe to start from.

**Decisions (the durable ones):**
- **Roadmap integrity fix.** A prior draft of `ROADMAP.md` had marked **Phase C as "✓ DONE"** and
  put "we are here" at the soft launch — false (HEAD is B6; C is unbuilt). Corrected: Phase C is the
  *current* build phase. A roadmap that lies about being public-ready is the one error that could let
  a future session skip the safety/deploy phase entirely.
- **Two standing Phase-C constraints, from the human.** (1) **The VPS does ALL generation and
  playout — no personal hardware in the runtime loop** (killed the "generate on the Mac and rsync"
  option in C6). (2) **Voice is a runtime setting** — both Kokoro (free) and ElevenLabs (flagship)
  must work via `settings.tts_provider`, not a one-way door.
- **The world is two layers (the refined vision).** A large, mostly-static **bible** (RAG-able:
  history, literature, finance, war, nations, peoples, geography, tech, cast) + a generative
  **living "now" at +600y**: events modelled as multi-beat **stories with a lifecycle** (rumoured →
  upcoming → happening → developing → past), surfaced by a **news desk** that recurs/evolves stories
  across the day with past/now/future framing and cross-segment continuity. This is the Phase-D
  keystone.
- **Vision distributed across phases, not crammed into C.** World-sim + news desk + sound design +
  songs + voice/emotion/pronunciation + DJ roster/memory + programming backbone → **D**. Near-live +
  a write **management/control surface** + **listener interaction** → **E**. Community inbound +
  in-universe surfaces → **F**.
- **Architecture gains exactly ONE new concept — Layer 0 (listener inbound).** Everything else fits
  existing layers/seams (proven "no rewrite below the seams"). The Batch API was downgraded from a
  MUST to "revisit when it pays" (Kokoro made the text bill trivial); the `orpheus` stub generalized
  to a streaming/self-hosted backend (Cartesia for near-live); a **pronunciation** knob reserved
  alongside `emotion` on the TTS seam.

**Changed:**
- `docs/ROADMAP.md` — Phase C moved out of DONE into a real build section (constraints baked in);
  Phase D expanded into the living-world spec; Phase E → "Scale, near-live & control"; milestone ✓
  corrected.
- `docs/ARCHITECTURE.md` — new Layer 0 (inbound); per-layer C/D/E forward notes; console → control
  surface; softened Batch rule; generalized TTS stub; reserved pronunciation; "How later phases plug
  in" rewritten into C/D/E blocks.
- `docs/PHASE_C_TASKS.md` — C6 reframed to *verify* (registry now done); **added the missing
  scheduler → Liquidsoap playout task**; decisive music-slot default (drop from rotation in C); soak
  "give it a now" note; C0 safety-check shape + C3 disclosure-as-setting; removed Discord
  (four-channel rule); C0/C1 ordering note.
- `docs/ai-radio-marketing-strategy.md` — superseded banner (four channels), Cloudflare Pages →
  Vercel.
- `src/providers/tts.py` — added Wren to the ElevenLabs ("Rachel") and `say` ("Samantha") registries;
  all three backends now map both DJs, so the **two-DJ show renders on any backend**.
- `src/writer.py` — docstring fix (`speaker=` → `speakers=`). Deleted `README_Backup.md` (cruft).
- Verified green: `ruff check` clean, `pytest` 29 passed.

**Why:** truth-in-docs is load-bearing for an agent-built project — the next session acts on what the
docs say, so a false "done" or an out-of-date plan is a real production risk, not cosmetics. Encoding
the full vision + constraints *before* building C means every later pack is informed and the
architecture can prove none of it forces a rewrite below the two seams.

**Next:** begin Phase C — **C0** (real safety + continuity gates), landing **C1** (time-aware
framing) alongside it.
Commit: (uncommitted at time of entry — docs realignment + TTS registry in the working tree)  ·  Clips: none

---

## 2026-06-20 — Phase B — B6 light nightly buffer (`make buffer`) — the mind at volume

**Focus:** one command that generates a small, varied block of audio in a single run — the mind
proven at volume at zero API cost — *without* building the real 24/7 scheduler (that, the
buffer-depth dial, the Batch API, and the content-safety gate are all deferred to Phase C). This
completes Phase B's "bonus" line: the whole mind runs at volume for free via Kokoro.

**Decisions (the durable ones):**
- **New `src/buffer.py` — a loop over the B5 dispatcher, not a new generation path.** `build_buffer`
  cycles `settings.buffer_rotation` (a mix of the three formats) calling `make_format_segment` per
  slot until the segments' `length_target_sec` values sum to ~`buffer_target_sec`. It reuses the
  whole stack underneath unchanged (formats → conversation/writer → context → world → providers);
  B6 adds *no* new world-query, LLM, or TTS code.
- **Length is measured by the segments' own targets, not a duplicated length table.** Rather than
  pre-planning durations (which would re-encode each format's length in a second place), the loop
  generates one segment, adds its *actual* `length_target_sec` to the running total, and stops when
  it reaches the goal — so the only source of a format's length stays its own config. It lands a
  little OVER target (a half-segment would be worse than slightly long).
- **Variety + progression come for free from the rotation + an advancing `air_time`.** Each slot is
  generated against an `air_cursor` that advances by the prior segment's length, so the block is
  contiguous *and* each segment assembles its own world context at its slot time — current events
  progress across the hour, exactly the Phase-B spine paying off. Both DJs appear because `talk` is
  the two-DJ show.
- **Each segment self-describes on disk; the run gets a manifest — the Phase-C handoff shape.**
  Every segment writes a `segments/<id>.json` sidecar (the full `Segment` via `dataclasses.asdict`),
  and the run writes `segments/buffer-<ts>.json` (ordered playlist: ids, formats, contiguous
  air_times, lengths, paths). Nothing reads the manifest to *air* it yet — that's the Phase-C
  scheduler — but the on-disk contract it will consume exists now.
- **A `buffer_max_segments` safety cap.** A hard stop so a tiny per-segment length (or a silly
  target) can't spin an unbounded run. All three knobs (`buffer_target_sec`, `buffer_rotation`,
  `buffer_max_segments`) live in a new `buffer_` config section; `make buffer SECONDS=` is the
  per-run length shortcut.

**Changed:**
- New: `src/buffer.py` (loop + sidecar + manifest + CLI).
- Updated: `src/config.py` (a `buffer_` section), `Makefile` (`make buffer`, `SECONDS=` override,
  help/header), `README.md`, `.env.example` (the B6 knobs), `docs/HOWTO.md` (buffer row + §2/§3/§6).

**Why:** Phase B's bonus done-when is "the whole mind runs at volume for free." Looping the B5
dispatcher (instead of writing a scheduler) gets that proof in the smallest code, and accumulating
by the segments' real length targets keeps length single-sourced. The sidecar+manifest is the cheap
groundwork that makes the Phase-C scheduler a *reader* of this output, not a rewrite.

**Verification:** the loop/sidecar/manifest/cap logic was exercised with a stubbed
`make_format_segment` (no DB/Claude/TTS): rotation cycles correctly, air_times are contiguous
(22:00:00 → +5m → +2.5m …), the target-driven loop stops just over goal (600s target → 4 segments,
840s), the `max_segments` cap holds (target 999999 → exactly 30), and a `<id>.json` per segment plus
one `buffer-*.json` manifest are written with all Segment fields. `ruff check src` + format clean;
new `segments/*.json` are gitignored. **Not yet run end-to-end** on the real stack (needs seeded
Postgres + the Kokoro model; the full hour is ~20 live segments) — that real run is the one
remaining human check.

**Next:** Phase B is feature-complete (B0–B6). Run a real `make buffer` for the hero clip, then
Phase C — the VPS, the real scheduler that airs *through* this buffer/manifest, public broadcast,
the content-safety gate, and the player/studio in `/web`.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-20 — Phase B — B5 program format templates (news / talk / music)

**Focus:** reusable show backbones so generation fills a proven skeleton instead of a blank page —
three formats, each a function `(now, context) -> Segment`, behind one registry/dispatcher.

**Decisions (the durable ones):**
- **New `src/formats/` package, one template per file + a registry.** `news`, `talk`, `music` each
  implement `(now, ctx) -> Segment`; `FORMATS` (a `{name: FormatSpec}` map) plus
  `make_format_segment(name, now_iso, topic=)` is the single public entry. The dispatcher assembles
  exactly the cast each format needs (one card for news/music, both for talk) via the same
  `context.assemble` seam, then calls the template — templates never touch the DB.
- **`talk` *wraps* B4, doesn't re-implement it.** Extracted `conversation.compose_segment(ctx, now,
  …)` (the context-taking generation core) out of `make_conversation_segment`, and added an optional
  `extra_directive` to `orchestrate`. `talk` calls `compose_segment` with an open→banter→music
  lead-in→close backbone. B4's own behaviour is unchanged.
- **`news` is reportage — the anti-recitation rule is deliberately inverted.** Unlike the two-DJ
  talk, a news anchor *should* state facts plainly; the prompt says so. Headlines are derived from
  the events near `now` (live relative phrasing from `events.py`); fewer than N → the anchor extends
  with plausible, canon-consistent items.
- **`music` keeps a `[SONG]` slot marker.** One Claude call writes intro + back-announce separated by
  a marker line; the marker stays in the saved `script` and in `Segment.meta`, but is split out
  before rendering so it is **never spoken** (real song scheduling is Phase C playout). Split logic
  (`split_on_marker`) is pure and unit-tested.
- **Config gets a `format_` section** (per-format speaker ids, word-count guidance, length-target
  DIALs, the song marker) — same config-over-hardcoding discipline; word counts/lengths are what make
  the three read as tonally distinct (a tight ~2.5-min news desk vs. a short ~1.5-min music bed).
- **Builders imported under aliases** (`from .news import news as build_news`) so the submodule names
  (`formats.news`, …) aren't shadowed by the function names.

**Changed:**
- New: `src/formats/{__init__,common,news,talk,music,__main__}.py`, `tests/test_formats.py`
  (marker split + registry).
- Updated: `src/writers/conversation.py` (extracted `compose_segment` + `orchestrate` directive),
  `src/config.py` (`format_` section), `Makefile` (`make format FMT=…`), `README.md`, `docs/HOWTO.md`.

**Why:** Phase B's "the Mind" needs more than one show shape; templating the backbone makes each kind
repeatable and tonally consistent while reusing the B4/B3 machinery (no new TTS or world-query code).
The signature `(now, context)` is the same shape B6's nightly buffer will loop over.

**Verification:** live `make format FMT=news` produced a coherent bulletin — sting → exactly 3
in-world headlines (lead derived from the seeded Lumen Festival, "with four days to go", plus two
canon-consistent invented items) → sign-off — rendered free via Kokoro to a **137.6s** segment
against a **150s** target (~8%). Distinctly a measured news desk, not the warm late-night talk.
`talk`/`music` share already-proven paths (B4 conversation; the news single-call + single-voice
render, plus the unit-tested marker split). **29 `pytest` pass**; `ruff` + format clean.

**Next:** B6 — a light nightly buffer (`make buffer`): ~an hour of varied segments (a mix of the
three formats, both DJs) into `segments/`, the mind proven at volume at zero API cost.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-20 — Phase B — B4 second DJ + conversation orchestrator (the creative core)

**Focus:** the hard creative core — two DJs (Vell, night → Wren, first light) holding a real,
in-character conversation that *uses* a current event/canon fact without info-dumping, voiced in two
distinct Kokoro voices and stitched into one talk `Segment`.

**Decisions (the durable ones):**
- **A light writers' room in three Claude steps, one shared cache.** New
  `src/writers/conversation.py`: a **showrunner** picks one beat/angle from the events near `now`;
  an **orchestrator** writes the whole exchange; a **continuity** editor checks it. All three pass
  the *same* `cached_context` (bible + both cards), so the prompt cache is reused across the
  session — only the small variable part of each call pays full price.
- **Single-call dialogue, both personas in one prompt** (per the B4 guidance) — cheaper and more
  coherent than turn-by-turn agents. The output is speaker-labelled (`Vell:` / `Wren:`); a parser
  (`parse_turns`) splits it into per-voice turns, tolerating `**bold**` labels, wrapped lines, and
  stray preamble. Try multi-agent only if single-call feels flat (it didn't).
- **Anti-recitation baked into the prompt:** the facts are the hosts' *shared knowledge to
  reference naturally*, never to explain to each other or recite. This is the line between "a
  conversation" and "two narrators," and it's the whole point of the task.
- **Continuity escalates by cost only when needed:** one pass on `sonnet`; if it flags trouble,
  re-check on `opus`. Advisory in B4 (verdict logged + stored in `Segment.meta`), exercising the
  seam a real continuity/safety gate slots into. The draft also runs through the existing
  `safety_check()` placeholder.
- **Two-voice rendering = synthesize per turn, then stitch.** Each turn is voiced in its DJ's own
  logical voice (`vell_night` / `dj_two`) and the per-turn mp3s are joined by a new
  `tts.concat_audio()` (ffmpeg concat demuxer, stream-copy — no re-encode). **All ffmpeg stays in
  `tts.py`**, next to `_to_mp3`, keeping the seam intact.
- **`context.assemble` generalized to N speakers.** `speakers=` now takes one id *or* several
  (both cards → cached core); a `speaker` convenience property keeps the single-DJ B3 path
  unchanged. This is what B5's formats will reuse.

**Changed:**
- New: `src/writers/{__init__,conversation.py}`, `tests/test_conversation.py` (the brittle
  `parse_turns` + verdict reader).
- Updated: `src/world/context.py` (multi-speaker `assemble` + `speakers`/`speaker` property),
  `src/providers/tts.py` (`concat_audio`), `src/config.py` (a `convo_` section: speaker ids, word
  guidance, per-step token caps, continuity tier + opus escalation tier), `src/writer.py`
  (`speakers=` kwarg), `Makefile` (`make conversation`), `README.md`.

**Why:** Phase B's definition of done is "two DJs hold a sensible in-character conversation that
uses canon." Single-call + a strong anti-recitation rule gets a genuine exchange for one Claude
call's cost; voicing turns separately is the only way two voices share one segment cleanly.

**Verification:** live `make conversation` produced a **22-turn, 2:47** two-voice segment
(`vell_night` + `dj_two`), continuity `OK` on the first `sonnet` pass. The dialogue reacts and
builds turn-to-turn (distinct voices: Vell musing/warm, Wren bright/forward), gives a real time
check at the handover, and references canon glancingly ("four days out from the Lumen," weeks-old
letters riding the relay) without explaining it — judged "a conversation, not two narrators." 24
`pytest` pass; `ruff` + format clean; env-drift guardrail green; the single-DJ B3 path still
assembles.

**Next:** B5 — program format templates (`news` / `talk` / `music`), each `(now, context) ->
Segment`; `talk` wraps this B4 conversation.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-19 — Phase B — B3 context assembly for the writer (structured retrieval; vector RAG stubbed)

**Focus:** feed the writer the *right slice* of the world for `now` — cheaply and fast — from the
DB, and stop reading the whole `CANON.md` into the prompt. The retrieval spine for B4–B6.

**Decisions (the durable ones):**
- **`src/world/context.py` — `assemble(now, *, topic, speaker)` splits the world into two parts
  that match the two cost seams.** A **cached stable core** (series bible + the speaking DJ's card)
  → sent as `cached_context` (the prompt-cache lever, ~0.1x on repeats); plus the **dynamic now**
  (events near `now` with live status + relative phrasing, and topic-relevant canon) → the small
  per-call part. The split is deliberate: the core barely changes, the dynamic part is what makes a
  segment time-aware.
- **Structured retrieval only; vectors stay a documented, *unused* seam.** Date/status/tag SQL is
  the right, fast tool while the canon is tiny. `src/providers/embeddings.py` fixes the contract
  (`retrieve()` no-op returning `[]`; `embed()` raises) with the TRIGGER spelled out — implement
  real vectors only when the context outgrows the cache *or* you need meaning-based (not date/tag)
  recall. `context.py` never calls it (done-when: "the seam exists but is unused").
- **The series bible is read from `CANON.md`, not the DB.** It's standing prose not projected into
  rows; a `canon_source.load_series_bible()` extracts just those sections, so `CANON.md` stays the
  single human-editable source while everything dynamic comes from the DB.
- **Canon goes in the *dynamic* (queried) half, not the cache** — matching the RAG intent
  (tag-matched to topic, anticipating growth). Today facts carry no tags, so a topic query falls
  back to the full (small) canon via a new `store.canon_by_tags()` — the seam is ready for when
  facts get tagged.
- **`context.py` touches no SQL** — the only DB block calls the `store` seam; psycopg never leaks
  out of `store.py`.

**Changed:**
- New: `src/world/context.py`, `src/providers/embeddings.py`, `tests/test_context.py`.
- Updated: `src/world/store.py` (`canon_by_tags`), `src/world/canon_source.py`
  (`load_series_bible`), `src/writer.py` (calls `context.assemble`, no more whole-file read),
  `src/produce.py` (dropped the canon read), `src/config.py` (`context_event_window_days`,
  `writer_speaker_id`), `tests/test_canon_source.py` (bible-loader test), `Makefile`
  (`make context`), `README.md`.

**Why:** a flat file can't answer "what's relevant *now*?" cheaply. Splitting cached-core from
queried-dynamic keeps the cost lever while making the prompt time-aware; deferring vectors avoids
standing up pgvector before it earns its keep.

**Verification:** `make context` prints the cached core (bible + Vell's card) and the dynamic slice
— the Lumen Festival rendered live as **"in five days (upcoming)"** plus the 7 canon facts. A
stubbed `llm.generate` confirmed the writer sends bible+card as `cached_context` and clock + events
+ facts in the system prompt. 20 `pytest` pass; `ruff` clean; env-drift guardrail green.
*(Noted, not fixed — pre-existing B1 parser truncates a multi-line event `**Body:**` to its first
line; out of B3 scope.)*

**Next:** B4 — second DJ + the conversation orchestrator (showrunner → dialogue → continuity),
two-voice render.
Commit: 7d114f1 · Clips: (none)

---

## 2026-06-19 — Phase B — B2 world clock + event progression + relative-time renderer

**Focus:** the time-awareness spine, and the proof of the progressing event — render the *same*
event at two `now` values and watch the phrase flip ("in five days" → "yesterday").

**Decisions (the durable ones):**
- **`src/world/clock.py` is the single source of the real→in-world (`now + 600y`) mapping.** The
  inline computation that lived in `writer.py` moved here; the writer now calls
  `clock.render_wall_clock`. Two uses kept deliberately apart: **display** (`render_wall_clock`)
  keeps the real weekday/day/month and only relabels the year (+600), honouring CANON's "a real
  Tuesday is an in-world Tuesday"; **arithmetic** (`to_inworld`/`to_real`) shifts both sides by
  +600 so the gap to an event is identical in real and in-world frames. Handles the 29-Feb
  Gregorian trap (2000 leap, 2600 not).
- **`src/world/events.py` is pure (no DB/IO).** `status_of(event, now)` → upcoming/today/past and
  `relative_phrase(event, now)` → "tomorrow"/"in five days"/"tonight"/"yesterday"/"last week" —
  computed against the in-world `now`. Purity makes the brittle bit (phrasing thresholds) trivially
  testable and lets B3 call it on already-fetched rows.
- **Phrasing thresholds + number-words are domain constants, not config** — named module-level
  constants next to the code (per the B0.5 config-vs-constant rule), since they're intrinsic to the
  renderer, not operator-tunable.
- **The demo anchors `now` on the event's own date** (not the wall clock), so the proof is
  deterministic: five days before → "in five days" (upcoming); one day after → "yesterday" (past).

**Changed:**
- New: `src/world/{clock,events}.py`, `tests/test_clock.py`, `tests/test_events.py`.
- Updated: `src/writer.py` (calls `clock` instead of inline `+600y`), `src/world/store.py` (a small
  read for the demo), `Makefile` (`make demo`), `README.md`.

**Why:** "a world that progresses" is the whole Phase B pitch and the future hero clip; it needs one
authoritative clock and a renderer that turns a stored date into the phrase a DJ would actually say.

**Verification:** `make demo` reads the seeded Lumen Festival and prints `[upcoming] "in five days"`
at `now−5d` and `[past] "yesterday"` at `now+1d`. `pytest` (clock + events) green; `ruff` clean.

**Next:** B3 — context assembly: cached core (bible + DJ card) + structured-query dynamic
(events/canon), the vector seam stubbed; rewire the writer onto it.
Commit: cb23d09 · Clips: (none)

---

## 2026-06-19 — Phase B — B1 world-state DB: schema + SQL seam + seed from canon

**Focus:** moved the world out of the flat file into a queryable Postgres store — the spine for the
time-awareness (B2) and context-assembly (B3) work to come. Schema, one SQL seam, and a
reproducible seed that projects `docs/CANON.md` into the DB.

**Decisions (the durable ones):**
- **`src/world/store.py` is the ONLY place SQL lives** — same seam discipline as `providers/`.
  Nothing else imports `psycopg`. It owns the row dataclasses (1:1 with tables), reads
  `settings.database_url` (never a literal), logs every query/error, and exposes the structured
  reads B2/B3 need (`events_by_status`, `events_in_range`, `get_cast_member`, …).
- **CANON.md stays the single human-editable source; the DB is a projection of it.** Added
  `src/world/canon_source.py` to *parse* the markdown (numbered facts, `### ` DJ cards, `### `
  events) rather than keep a second machine copy. Restructured CANON.md's DJ section into a
  parseable `## Cast` (two cards) and a new `## Events` timeline with a real in-world datetime.
- **Seed reproduces by TRUNCATE + reload in one transaction** — re-running yields the exact state
  the file describes (no orphans, no dupes), satisfying "reproducible." Stable slug ids
  (`canon-1`, `vell`, `lumen-festival`) keep references stable across re-seeds.
- **Defined the second DJ: Wren, the first-light host** — a bright, question-asking foil to Vell's
  calm night shift; maps to the `dj_two` Kokoro voice reserved in B0. (Approve/tune the persona.)
- **pgvector deliberately NOT installed.** Structured date/status/tag queries are the right
  retrieval now; the vector path is a documented FUTURE slot in `store.py` (extension +
  `canon_embeddings` table), wired in B3 via the `providers/embeddings.py` stub. `tags` is a real
  `text[]` column now (populated for cast/events; canon tags enriched in B3).

**Changed:**
- New: `src/world/{__init__,store,canon_source,seed}.py`, `tests/test_canon_source.py`.
- Updated: `docs/CANON.md` (`## Cast` with Vell + new Wren; `## Events` with the dated Lumen
  Festival), `requirements.txt` (`psycopg[binary]`), `Makefile` (`make seed`), `README.md`
  (Postgres install + seed step + pgvector-deferral note + store-seam dev note), `.env.example`.
- Dev env: `brew install postgresql@14` + `createdb settlement_radio`; installed `psycopg` in
  `.venv`.

**Why:** a flat file can't answer "what's happening near *now*?" — the whole point of Phase B is a
world that progresses, which needs date/status queries. Parsing CANON.md (not duplicating it) keeps
one source a human edits by hand, per CLAUDE.md.

**Verification:** `make seed` loads 7 canon / 2 cast / 1 event; re-running twice leaves counts
identical (idempotent). `events_by_status('upcoming')` and `events_in_range(...)` both return the
festival; out-of-window/`'past'` queries return empty. `pytest` (parser, 4) + the existing retry
tests pass; `ruff check src` clean.

**Next:** B2 — world clock (`now + 600y` as the single source), event progression + a relative-time
renderer ("in five days" → "yesterday"), and the two-`now` demo on the Lumen Festival.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-19 — Phase B — B0.5 foundation: config + logging + lint/pre-commit + retries

**Focus:** laid the engineering baseline before the world engine — one typed settings module,
structured logging, lint/format + a pre-commit gate, and bounded retries on the vendor seams — so
B1–B6 are *built on* the standards instead of retrofitted. Then hardened config against future
sprawl (a config-vs-constant policy, area-prefix naming, and an automated drift guardrail).

**Decisions (the durable ones):**
- **One typed settings module, `src/config.py` (`pydantic-settings`).** Every tunable now reads
  `settings.X`; no module reads a literal or the env directly. Precedence is process env → `.env` →
  defaults. Secrets and conventional names (`ANTHROPIC_API_KEY`, `TTS_PROVIDER`, `DATABASE_URL`)
  kept their plain forms, so `.env` and the per-run `TTS_PROVIDER=x make play` ergonomic are
  unchanged. The tier→model-id map moved here as `settings.model_id(tier)`.
- **Config vs domain constant — the real anti-sprawl rule, written into config.py's header.** Only
  environment/run-tunable values live in `Settings`; logic *intrinsic to an algorithm* (relative-
  time thresholds later, `_part_of_day` cutoffs, the vendor voice registries) stays as a *named*
  module constant next to its code. A named constant is not a "magic number"; hauling it into
  Settings makes a god-object, which is the mess to avoid.
- **Area-prefix naming to prevent collisions as B1–B6 add fields.** `llm_`/`tts_`/`world_`/
  `segment_`/`writer_`/… (reserved `context_`/`convo_`/`format_`/`buffer_`). Applied now while
  small — renamed the unprefixed Phase-A fields (`years_ahead`→`world_years_ahead`,
  `vell_voice`→`segment_vell_voice`, `words_*`→`writer_words_*`, the `elevenlabs_*`/`kokoro_*`→
  `tts_*`) so B4's cap is `convo_max_tokens`, never a bare `max_tokens`.
- **`structlog`, JSON by default, configured once.** `LOG_JSON=false` for pretty console. Every
  external call and pipeline step logs start/outcome; replaced the `print()`/silent paths in
  `llm.py`/`tts.py`/`writer.py`/`produce.py`. (CLI *deliverable* output — the writer's printed
  script — stays on stdout; logging is for diagnostics.)
- **Bounded retry on the seams (`src/retry.py`).** Claude's stream and every TTS render go through
  `call_with_retry` — retries with linear backoff, logs each attempt loudly, re-raises on
  exhaustion. The rule is "fail loudly into the logs, never silently produce nothing."
- **`ruff` (lint+format) in `pyproject.toml`; a fast pre-commit gate.** Hooks: ruff, `gitleaks`
  (the automated backstop to "never commit keys"), a **custom config-drift guardrail**
  (`scripts/check_no_direct_env.sh` — blocks `os.getenv`/`os.environ`/`dotenv` anywhere under
  `src/` except `config.py`), and whitespace/EOF/large-file/JSON-YAML-TOML basics. **No test suite
  in pre-commit** (it would get bypassed).

**Changed:**
- New: `src/config.py`, `src/logging_setup.py`, `src/retry.py`, `tests/test_retry.py` (the one
  non-trivial bit), `scripts/check_no_direct_env.sh`, `pyproject.toml`, `.pre-commit-config.yaml`.
- Updated: `src/providers/llm.py` + `src/providers/tts.py` (settings + logging + retry; dropped
  `load_dotenv`), `src/writer.py` + `src/produce.py` (settings + logging; field renames),
  `requirements.txt` (pydantic-settings, structlog; dev: ruff, pre-commit, pytest), `.env.example`
  (logging/retry/DB knobs), `README.md` ("Developing the station backend" section).
- Dev env: installed pydantic-settings, structlog, ruff, pre-commit, pytest into `.venv`.

**Why:** B0.5's whole point is to set the standards while the code is ~6 files, so the world engine
inherits them. The config-vs-constant policy + prefixes + guardrail are the cheap insurance against
the settings module rotting into an unsearchable junk drawer once B1–B6 pile on their knobs.

**Verification:** `ruff check src` clean; `pytest` 3 passed; full `pre-commit run` green incl. the
guardrail — and the guardrail correctly **blocks** a planted `os.environ` violation. Forced an
Anthropic stream failure → caught, logged (`llm_generate_start`→`external_call_retry`→
`external_call_failed`), re-raised. The real `make_segment` path emits the info-level JSON chain
(`make_segment_start`→`write_segment_script_*`→`make_segment_done`).

**Next:** B1 — PostgreSQL world-state DB: schema (`canon`/`cast`/`events`/`state`),
`src/world/store.py` (the only SQL seam, reads `settings.database_url`), and a reproducible seed
from `docs/CANON.md`.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-19 — Phase A2 — the coming-soon site (`/web`), live on settlementradio.com

**Focus:** built and shipped the public coming-soon page — a single branded night-field screen
with working email capture — as a Next.js app in a new `/web` folder, deployed to
**settlementradio.com** via Vercel. First non-Python surface; the seed that grows into the audio
player + studio in Phase C.

**Decisions (the durable ones):**
- **Monorepo, one repo.** The Python station stays at the root; `/web` is a self-contained Next.js
  (App Router + TS + Tailwind) app. **Vercel deploys only `/web`** (Root Directory = `web`); the
  backend is never built or deployed by Vercel. Recorded in `CLAUDE.md` (A2-T7) so the two-part
  shape is canon.
- **Email signup with no database.** A server route `app/api/subscribe/route.ts` holds the
  **Buttondown** key server-side and POSTs `{email_address}`; the client form never sees the key.
  Honeypot field + email validation; Buttondown's `400 email_already_exists` is mapped to a
  friendly "already on the list". Buttondown chosen because it's also the newsletter surface.
- **The brand lockup *is* the `<h1>`.** The horizontal wordmark SVG (beacon + wordmark) renders as
  the page heading via its `alt` text — on-brand and accessible without duplicate text. Brand
  tokens are Tailwind v4 `@theme` vars (`night`/`amber`/`neutral`); Inter via `next/font`.
- **Metadata points the OG/Twitter image absolute.** `metadataBase = https://settlementradio.com`
  so the branded `og-image.png` resolves to an absolute URL for crawlers; title + description carry
  the fiction/AI disclosure. (Known nit: the OG asset is a *portrait* stacked lockup, so a
  `summary_large_image` Twitter card will center-crop it — flagged for a later landscape asset.)
- **`/web` env is separate from the root `.env`.** Next only reads env files inside its own project
  dir, so the Buttondown key lives in `web/.env.local` (gitignored) and as a Vercel env var — not
  the root `.env`. This bit us once: the key was in root `.env` and the route saw nothing.
- **Heed the Next 16 breaking-changes warning.** `web/AGENTS.md` says this Next.js differs from
  training data — read `node_modules/next/dist/docs/` before coding (Image, route handlers,
  metadata APIs all confirmed against the shipped docs).

**Changed:**
- New: `web/` Next.js app — `src/app/page.tsx` (coming-soon screen), `src/app/SignupForm.tsx`
  (client form), `src/app/api/subscribe/route.ts` (Buttondown route), `src/app/layout.tsx`
  (metadata), `src/app/globals.css` (brand tokens), `public/` brand assets, `.env.example`,
  `README.md`.
- Updated: root `CLAUDE.md` (the monorepo / `/web` subsection, A2-T7).
- Accounts/infra (manual): Buttondown list + API key; Vercel project (Root Directory = `web`) with
  the key as an env var; **settlementradio.com** DNS pointed at Vercel — **Microsoft mail records
  left untouched** so `hello@settlementradio.com` keeps delivering.

**Why:** a coming-soon page that captures emails is the cheapest "built in public" surface, and
doing it as the *real* Next.js app (not a throwaway) means Phase C's player is new routes, not a
rebuild. Keeping the key server-side and the web env separate from the station's is the difference
between "works on my laptop" and "safe to deploy".

**Verification:** `npm run build` / `lint` / `tsc --noEmit` all green. `/api/subscribe` smoke-tested
live — invalid email → 400, honeypot filled → 200 (no API call), valid email with no key → 500.
The Buttondown key authenticates (GET `/v1/subscribers` → 200). Rendered `<head>` shows the
`og:*` / `twitter:*` / `<title>` tags with absolute image URLs. Page deployed and served over
HTTPS at settlementradio.com (T5, done manually).

**Next:** A2-T6 (optional) — flip on Vercel Web Analytics — then Phase B (the world engine /
nightly batch). Consider a dedicated landscape Twitter/OG image.
Commit: A2-T0 84b6a54 · A2-T1 b872cc0 · A2-T2 da0d443 · A2-T4 7b16259/bcf2c38/b176d76 ·
A2-T7 (uncommitted) · Clips: (none)

---

## 2026-06-17 — Phase A — free offline TTS backend (`say`) for testing

**Focus:** added a second TTS backend — macOS's built-in `say` — so the loop can be
tested unlimited and offline, after ElevenLabs' free tier ran dry (~2 full segments/month).

**Decisions (the durable ones):**
- **A `TTS_PROVIDER=say` backend, selected by env, alongside `elevenlabs` (still default).**
  The seam's whole point is parallel backends; `say` is offline, free, unlimited, and
  needs no key — ideal for exercising the pipeline without spending voice credits. It's a
  *test* voice, not Vell's real one.
- **Override per-run, don't change the default.** `TTS_PROVIDER=say make play` beats `.env`
  (dotenv doesn't override a shell var), so the default stays `elevenlabs` and the free path
  is one prefix away.
- **A shared `_to_mp3()` helper (ffmpeg) for non-mp3 backends.** `say` emits AIFF; the helper
  transcodes to the mp3 the pipeline expects. Deliberately shared so the future Kokoro backend
  (emits WAV) reuses it — adding `say` is groundwork, not throwaway. The only per-provider bit
  is its voice registry (`_SAY_VOICES`: `vell_night` → "Daniel").

**Changed:**
- Updated: `src/providers/tts.py` (`_synthesize_say` + `_to_mp3` + `say` dispatch + registry),
  `.env.example` (document the three providers + the override tip), `README.md` (provider-seams
  + Run notes).

**Why:** TTS is the real cost wall (the script side is cache-cheap), so a free, offline voice
keeps development unblocked when credits are exhausted — without touching anything but `tts.py`,
which is exactly what the provider seam was built to allow.

**Verification:** `TTS_PROVIDER=say .venv/bin/python -m src.produce` generated
`segments/vell-20260617T200508.mp3` — **246 s (~4.1 min)**, valid mp3 via `ffprobe` — with zero
ElevenLabs credits spent (only the cheap streamed Anthropic script call). Playout is
provider-agnostic, so the T6 loop serves it unchanged.

**Next:** commit the T5/T6/streaming + `say` work; optionally wire Kokoro later as the free
*offline + high-quality* voice (reuses `_to_mp3`).
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T6 one-command loop + browser player (+ streaming fix)

**Focus:** made the whole Phase A loop a single command (`make play`), gave it a real
browser play button, and fixed the script step's "looks-frozen" UX. This is the **Phase A
definition of done** — verified by hearing a freshly generated Vell segment in the browser.

**Decisions (the durable ones):**
- **`make serve` always runs `stop` first.** Backgrounded Icecast instances kept surviving
  and squatting port 8000 ("Could not create listener socket"). Making `serve` depend on
  `stop` (which kills by PID file *and* by process pattern) means a stale server can never
  block a fresh start — the recurring orphan problem is structurally gone.
- **Processes background via `nohup` into `.run/` (gitignored); Liquidsoap runs through
  `opam exec`.** No more "leave a terminal open per service" and no need to `eval "$(opam
  env)"` first — `make` finds Liquidsoap itself. PIDs + logs live in `.run/`.
- **A minimal static player page (`config/web/index.html`) served by Icecast at `/`.**
  Browsers won't render a play button for a *bare* MP3 mount (Chrome/Firefox showed "empty
  page" on `/settlement.mp3`), so the page wraps the mount in `<audio controls>`. It's also
  the home for the **AI-generation disclosure** (a CLAUDE.md hard rule) — *not* the
  out-of-scope "web player UI", just one static file.
- **`llm.generate` now streams** (with an optional progress callback + a 120s timeout). The
  non-streaming call blocked silently at the socket for the full ~25s generation, looked
  hung, and kept getting Ctrl-C'd. Streaming returns the same string but surfaces progress
  (`produce.py` prints a dot per chunk) and makes a real network stall fail fast.

**Changed:**
- New: `Makefile` (`generate`/`serve`/`play`/`stop`/`status`), `config/web/index.html`.
- Updated: `config/icecast.xml` (webroot → `config/web`, `/` → the player), `src/providers/llm.py`
  (streaming + `on_token` + `timeout`), `src/writer.py` + `src/produce.py` (thread the progress
  callback), `README.md` (T6 run section), `.gitignore` (`.run/`).

**Why:** one command + clean start/stop is what makes the loop demoable and stops the
orphan-process foot-guns; the player page is the difference between "serves a stream URL" and
"a human opens it and hears Vell"; streaming is what stops a 25-second call from looking broken.

**Verification:** `make play` generated `segments/vell-20260616T225823.mp3` and served it —
`http://localhost:8000/` shows the player, the mount returns `200 audio/mpeg`, and Liquidsoap's
`libmad` decoded the **new** segment (confirmed in `.run/liquidsoap.log`). Heard end-to-end in
the browser. **Known external blocker:** ElevenLabs **free-tier quota** caps fresh renders at
~2 full 5-min segments/month (~4.2k credits each); once exhausted, `make play` fails at the TTS
step with `quota_exceeded` (401) until the monthly reset — the pipeline itself is unchanged and
proven. (Recorded to project memory.)

**Next:** commit the T5 + T6 + streaming work (on a branch); optionally T7 (`make drop`, a ~60s
segment) — which also fits within leftover ElevenLabs credits. Otherwise Phase A is done.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T5 playout (Layers 5–6): loop on a local stream

**Focus:** stood up local playout — Liquidsoap loops the newest segment to a local Icecast
mount with a never-dead fallback, so the stream is always live.

**Decisions (the durable ones):**
- **Homebrew no longer ships `liquidsoap`; build it from source via opam — *with* the MP3
  plugins.** This was the session's real friction. The task assumed `brew install liquidsoap`,
  but the formula is gone and upstream ships only Linux `.deb`s. Installed via `opam`, and
  critically had to add **`lame` (MP3 encode)** and **`mad` (MP3 decode)** — the first build
  had neither, so `%mp3` was "unsupported format" and it couldn't even read the segments. Also
  needed `CPATH`/`LIBRARY_PATH` → Homebrew so the C stubs find headers on Apple Silicon. All of
  this is now in the README so the build is reproducible.
- **`radio.liq` re-picks the newest file on every loop** (`request.dynamic`), so a freshly
  generated segment is adopted with no restart. Filenames sort by time → "last in a sorted
  listing wins."
- **Never-dead fallback:** `assets/bed.mp3` if present, else a quiet sine tone, via
  `fallback(track_sensitive=false, …)` + `mksafe` — Icecast drops a source-less mount, so the
  stream must never be silent.
- **Icecast is local-only:** bound to `127.0.0.1:8000`, source password `hackme` matching
  `.env` / `ICECAST_SOURCE_PASSWORD`. Not hardened for public — that's Phase C.

**Changed:**
- New: `config/icecast.xml`, `config/radio.liq`. Updated `README.md` (Playout/install section).
- System: `brew install icecast ffmpeg coreutils curl lame mad`; `opam` + `opam install
  liquidsoap lame mad` (Liquidsoap 2.4.4).

**Why:** the "newest file wins + always-on fallback" pair is the minimal seed of the Phase-5
scheduler (buffer depth as a parameter) without building a scheduler; pinning down the opam +
lame/mad reality now means future machines reproduce the build instead of rediscovering it.

**Verification:** `liquidsoap --check config/radio.liq` passes clean; starting Icecast +
Liquidsoap serves `http://localhost:8000/settlement.mp3` (`200 audio/mpeg`), and the log shows
`libmad` decoding the real Vell segment (not the fallback tone). Several orphaned test-Icecast
processes were cleaned up afterward.

**Next:** T6 — one command (`make play`) + a browser the human can actually press play in.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T4 render to audio (Layer 4)

**Focus:** wired the Phase A pipeline end to end — script → TTS → a populated `Segment` with a
playable audio file on disk.

**Decisions (the durable ones):**
- **`length_target_sec` is a parameter with a default, not a hardcoded `300`.** `make_segment`
  defaults to ~5 min but takes the dial as a keyword arg, so the T7 60-sec drop is a different
  argument, not a rewrite — honouring the Segment seam.
- **Timestamped segment ids (`vell-YYYYMMDDThhmmss`).** Sortable so Liquidsoap's "newest file
  wins" (T5) is trivial, and ids never collide across runs.
- **Paths resolved from the module, not the cwd.** Canon read from `docs/CANON.md` and audio
  written under `segments/` via `__file__`-relative paths, so `python -m src.produce` works from
  anywhere. `format="talk"`, `disclosure=True` set per the T4 spec.
- **No vendor SDKs here.** `produce.py` only touches the two seams (`writer` + `tts`), keeping
  the whole pipeline behind the abstractions.

**Changed:**
- New: `src/produce.py`. Updated `README.md` (T4 section).

**Why:** making length a dial on this one function is what later lets the same path serve an
overnight block and a near-live drop; routing through the seams keeps model/TTS swaps a one-file
change.

**Verification:** `.venv/bin/python -m src.produce` generated
`segments/vell-20260616T104252.mp3` — 4,093,536 bytes, **255.8 s (~4.3 min)** confirmed via
`ffprobe` — in Vell's voice, and returned a populated `Segment` (`format=talk`,
`length_target_sec=300`, `disclosure=True`).

**Next:** T5 — playout: install `liquidsoap`/`icecast`/`ffmpeg` via Homebrew, loop the newest
segment on a local Icecast stream with a silence-avoidance fallback.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-16 — Phase A — T3 script generation (Layer 3, minimal)

**Focus:** got Claude writing Vell's ~5-min night-shift segment from the canon — the single-
function "writers' room", no multi-agent yet.

**Decisions (the durable ones):**
- **Canon rides in `cached_context`; only the small per-call instructions + clock pay full
  price.** The bulky stable world bible is the cache breakpoint (the Phase A cost lever); the
  variable system prompt stays compact.
- **The +600yr clock is computed, never hardcoded, and preserves the real weekday.** A real
  Tuesday 02:00 becomes an in-world Tuesday 02:00 six centuries on, so the spoken time check is
  accurate. A `_part_of_day` phrase steers the time-check mood.
- **Tier `sonnet` (the default writing brain); spoken-script-only output** — no stage directions,
  labels, or headings, so the text goes straight to TTS.
- **`safety_check(text)` is a no-op placeholder** marking exactly where a content gate slots in
  before any public broadcast.

**Changed:**
- New: `src/writer.py`. Updated `README.md` (T3 section).

**Why:** caching the whole canon keeps input cost ~0.1x on repeat runs, and computing the clock
(rather than baking a year) means the time check never goes stale — the two things this step has
to get right to be reusable.

**Verification:** `.venv/bin/python -m src.writer` prints a coherent, in-character ~700–800-word
script with a correct "settlement time" time check for the current time.

**Next:** T4 — `src/produce.py`: script → TTS → a populated `Segment` audio file.
Commit: 14902ba · Clips: (none)

---

## 2026-06-16 — Phase A — T2 the Segment model (Seam #2)

**Focus:** built Seam #2 — the `Segment` dataclass — so segment length and lead-time become
dials on one code path instead of assumptions baked into the pipeline.

**Decisions (the durable ones):**
- **`Segment` matches the ARCHITECTURE.md spec verbatim**, dials and all: `length_target_sec`
  (required, no default — callers *must* dial it) and `lead_time_sec` (defaults 0). Keeping the
  shape identical to the doc means later phases plug in without a rewrite.
- **`length_target_sec` is a required field, not defaulted.** Forcing it at construction is the
  enforcement of "never hardcode length" — there's nowhere for a magic 300 to hide.
- **`disclosure` defaults `True`; `meta` is a `field(default_factory=dict)`** open bag for
  per-format extras, so the dataclass stays stable as formats grow.

**Changed:**
- New: `src/segment.py`. No other files touched (writer/produce consume it in T3–T4).

**Why:** making length and lead-time *inputs* is what later lets one `make_segment` serve a
3-hour overnight block and a 60-second near-live drop — only the numbers and the model/TTS tier
change, never the code path.

**Verification:** `python3 -c "from src.segment import Segment; print(Segment(id='demo-001',
format='talk', length_target_sec=300))"` constructs and prints a fully-populated Segment
(dials + `disclosure=True` + empty `meta`). No length is hardcoded anywhere else.

**Next:** T3 — `src/writer.py`: Claude writes Vell's ~5-min segment from the canon, canon passed
as the cache breakpoint.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-14 — Phase A — T1 provider abstraction (the two vendor seams)

**Focus:** built Seam #1 — the only two modules that touch a vendor SDK — so every later
task talks in logical tiers/voices and never imports `anthropic`/`elevenlabs` directly.

**Decisions (the durable ones):**
- **Tiers map to real IDs inside `llm.py`, nowhere else.** `haiku`→`claude-haiku-4-5-20251001`,
  `sonnet`→`claude-sonnet-4-6` (default), `opus`→`claude-opus-4-8`. Unknown tier raises early.
- **`cached_context` is a real cache breakpoint from day one.** It's placed *first* in the
  system prompt with `cache_control: ephemeral`, and the small per-call `system` text follows
  it — caching is a prefix match, so the stable canon must precede the volatile part. (Phase A
  prefixes may be below the model's min cacheable size and silently not cache; the path is still
  in use and grows into Phase B free.)
- **`generate` is plain text-in/text-out — no thinking.** Simplest general-purpose seam and
  keeps text cost trivial; a thinking knob can be added later without changing callers.
- **TTS backend chosen by `TTS_PROVIDER`; `kokoro`/`orpheus` raise a clear `NotImplementedError`
  stub.** Logical voice `vell_night` → ElevenLabs "Adam" (`pNInz6obpgDQGcFmaJgB`), the only place
  a vendor voice id appears. `emotion` is accepted but reserved (no vendor knob wired yet).

**Changed:**
- New: `src/providers/llm.py`, `src/providers/tts.py`, `src/__init__.py`,
  `src/providers/__init__.py`. Updated `README.md` (provider-seams section).
- Created a throwaway `src/_scratch_t1.py`, ran it, deleted it (+ its `segments/_test.mp3`).

**Why:** isolating both vendors behind one function each is what later lets us swap models,
swap TTS to self-hosted, and share one code path between overnight batch and 60-sec near-live —
without touching anything upstream.

**Verification:** `python -m src._scratch_t1` made a live Claude call (returned a greeting) and
a live ElevenLabs call (`segments/_test.mp3`, 24,703 bytes, confirmed real MPEG layer-III audio
via `file`). Both keys read from `.env`. Scratch + artifact deleted afterward.

**Next:** T2 — the `Segment` dataclass (Seam #2), so segment length/lead-time become dials.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-14 — Phase A — T0 repo scaffold (skeleton + venv)

**Focus:** stood up the reproducible project skeleton so the build has somewhere to live —
no pipeline logic yet, just the tree, ignores, deps, and the env template.

**Decisions (the durable ones):**
- **`.gitkeep` to version the empty dirs.** `segments/` and `assets/` are gitignored, but the
  dirs ship in git via a `.gitkeep` each (ignore `segments/*` but un-ignore the keep file), so a
  fresh clone has the tree the pipeline expects without committing generated audio.
- **`.env.example` holds every Phase A setting, not just T1's.** Added `ICECAST_SOURCE_PASSWORD`
  (T5) now with a working local default (`hackme`) so the human fills keys once. Vendor voice IDs
  stay **out** of env — the `vell_night` → real-id map lives in the `tts.py` registry per Seam #1.
- **Loose lower-bound pins** in `requirements.txt` (`anthropic>=0.40`, `elevenlabs>=1.0`,
  `python-dotenv`, `requests`) — simplest reproducible install for a solo Phase A.

**Changed:**
- Created the tree: `src/`, `src/providers/`, `config/`, `segments/` + `assets/` (gitignored,
  with `.gitkeep`).
- New files: `.gitignore`, `.env.example`, `requirements.txt`, `README.md` (setup + layout).
- Created `.venv/` (Python 3.13.5, satisfies 3.11+) and installed all deps.

**Why:** a clean, clone-and-run skeleton up front means every later task (T1→T6) just drops a file
into a known place; the `.env.example`-completeness + `.gitkeep` choices both exist to make
"fill keys once, then it works from a fresh clone" true.

**Verification:** `pip install -r requirements.txt` succeeds in the fresh venv; all four deps
import; `git check-ignore` confirms `.env` and `segments/*.mp3`/`assets/*.mp3` are ignored while
`.gitkeep` stays tracked. Tree matches CLAUDE.md → "Repo conventions".

**Next:** T1 — the provider abstraction (`llm.py` + `tts.py`), pending API keys in `.env`.
Commit: (uncommitted) · Clips: (none)

---

## 2026-06-13 — Phase 0 (planning) — Project shape, name, and the full doc pack settled

**Focus:** turned a broad idea into a decided plan — architecture, funding angle, name, and the
document set that drives the build — before touching Claude Code.

**Decisions (the durable ones):**
- **Architecture = hybrid, no hardware bought.** Cheap always-on CPU VPS (Hetzner CX22, ~€4/mo)
  for 24/7 playout; generation via on-demand/serverless GPU or APIs; YouTube Live as the free,
  unlimited-listener relay. Chosen over buying a Mac Mini. *(Box superseded 2026-06: CX22 retired by
  Hetzner; provisioning on a CX33 — see that session's entry.)*
- **Anthropic angle = "powered by Claude," honestly framed.** Anthropic supplies all
  intelligence + the whole build (Claude Code); voice is the one external piece (no Anthropic
  TTS exists). Realistic Anthropic support is *being featured*, not big credits (those need
  institutional equity funding); fund usage via small self-serve credits + Claude on AWS/GCP
  credits. So the MVP's job is to be **featurable**.
- **MVP scope:** 2 DJs, 1 show, 3 formats, small real canon, batch-only generation + one 60-sec
  near-live demo, content-safety gate + AI disclosure, built by Claude Code and documented in
  public. Everything bigger is explicitly deferred.
- **Name = Settlement Radio.** Verified clean at the brand/trademark level (no station, podcast,
  or media brand uses it). Worldbuilding justification: "settlement" is a *linguistic fossil* —
  the worlds are mature city-planets but still called the settlements out of six-century habit.
- **In-world year = real year + 600, computed at generation time** — never hardcoded (so it
  never goes stale).
- **Model routing:** Sonnet 4.6 default writing brain; Haiku 4.5 for high-volume/near-live;
  Opus 4.8 for rare hard reasoning; Fable/Mythos not workhorses. **Batch API + prompt caching
  mandatory** — text cost stays near-trivial; TTS is the real cost driver.
- **Voice:** ElevenLabs free tier now, behind the TTS abstraction, swappable to Kokoro/Orpheus.
- **Two load-bearing seams:** provider abstraction (swap model/voice/local↔cloud) and the
  Segment abstraction (segment length + lead-time as parameters → batch and near-live share one
  path).
- **Infra identity:** create a GitHub **org** `settlementradio` (org name is the scarce asset),
  repo lives inside. Buy the **domain first**; use Cloudflare free Email Routing to forward a
  branded address into a dedicated project inbox; register *all* project accounts to that, not
  personal email.
- **Habit:** devlog + screen recordings from Phase 0 (Cmd+Shift+5 now, asciinema for terminal
  sessions, OBS later — it doubles as the Phase C streaming tool).

**Changed (documents produced/updated this session):**
- Created the four-file Claude Code pack: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/CANON.md`,
  `docs/PHASE_A_TASKS.md`.
- Created `docs/ROADMAP.md` (the single who-does-what-when path: Phase 0 → A → B → C → D →
  Beyond).
- Created the strategy set: funding & licensing kit, the Anthropic-anchored build plan, the
  marketing strategy.
- Updated docs with: the Settlement Radio name, the floating-year fix, the "linguistic fossil"
  canon note, and the model-routing + batch/caching rules (in CLAUDE.md, ARCHITECTURE.md, and
  PHASE_A_TASKS.md).

**Why (the key reasons):**
- Hybrid over hardware: near-zero up-front cost, fits €0–40/mo, and credits subsidize cloud/API
  but never a hardware purchase.
- Settlement Radio over prettier names: the cozy-audio namespace is crowded, so plain + verified
  beats evocative + taken; it also ties to the canon's "settlement time."
- Just-in-time task packs: only Phase A is detailed on purpose; B–D get written when reached, so
  they're informed by what Phase A actually teaches.

**Next:** execute Phase 0 — buy the domain (everything hangs off it), set up the forwarding
inbox, claim handles + the GitHub org, install Claude Code, get Anthropic + ElevenLabs API keys,
stand up the coming-soon page, start recording. Then in Claude Code: create the repo in the org,
upload the four-file pack, run `PHASE_A_TASKS.md` from T0.
Commit: (pre-repo; docs created in planning chat) · Clips: (none yet — start with Phase 0)

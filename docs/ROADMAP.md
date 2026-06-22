# ROADMAP.md — Settlement Radio: the whole path

The one file to read when overloaded. The complete journey — done and ahead — as one sequence.
**Build phases** (A, B, C, D, E…) alternate with their **marketing phases** (CM, DM, EM…). Each
forward phase says **what YOU do / what CLAUDE chat does / what CLAUDE CODE does / done when**.

**Milestones:**
- **Mini-MVP** — end of A — hear the station on your machine. ✓
- **Public station** — end of C — safe, continuous, listenable by anyone. ← next (in build)
- **MVP + sponsorship** — end of DM — loud launch fired, applications in, a featurable artifact in
  front of Anthropic, donations live. ← the commercial goal.
- **Full product** — Phase E onward — near-live, scale, more channels, the wider +600y world.

**Channels (deliberately only four):** **YouTube** (the broadcast + how-it's-made) · **X** (the one
active feed: build-in-public + the road to an Anthropic feature) · **Ko-fi** (donations) · **GitHub**
(the open repo + README = credibility + the featurable artifact). Everything else was dropped on
purpose. **The marketing playbook + the validatable milestones (M0–M5) live in `docs/MARKETING.md`;**
this file owns the *sequence*, that one owns the *how*.

**Division of labor:** **YOU** decide, listen, write the world, claim/post/apply (human-only).
**CLAUDE (chat)** plans, writes docs/copy, researches, preps each next pack. **CLAUDE CODE** builds
and operates the repo.

---

## ✓ DONE

**Phase 0 — Claim the ground.** Domain + Microsoft mailbox (`hello@settlementradio.com`, used
directly); handles on the four channels; GitHub org; API keys; Claude Code installed.

**Phase A — Mini-MVP (proof of loop).** `make play`: one DJ (Vell), generated from canon, voiced,
on a local stream. The seams proven in real code.

**Phase A2 — Coming-soon site.** The Next.js app in `/web` on Vercel, live at settlementradio.com,
branded, email signup → Buttondown.

**Phase B — The mind.** Postgres world-store seeded from the canon; world clock + relative-time
renderer ("in five days → yesterday"); a real two-DJ conversation (Vell ↔ Wren) that *uses* canon;
three formats (news/talk/music); `make buffer`; all voiced free/local via Kokoro. Engineering
baseline (config, structured logging, retries, ruff + pre-commit incl. secrets scan) green.

---

## Phase C — The body (safe · continuous · public · build) ← WE ARE HERE

Makes the station *real*: safe, continuous, and listenable by anyone — the work Phase B deferred on
purpose. The detailed pack is `docs/PHASE_C_TASKS.md` (C0–C9); the current-state handoff is
`docs/PHASE_B_ORIENTATION.md`.

**Two standing constraints for this phase:**
- **No personal hardware in the loop.** The VPS does ALL generation and playout, 24/7. Your Mac is
  for development only — it is never a runtime dependency (so "generate on the laptop and copy up"
  is off the table; if Kokoro can't keep up on the box, scale the box or the voice, not the laptop).
- **Voice is a runtime setting, not a one-way door.** Both Kokoro (local/free) and ElevenLabs
  (cloud/flagship) stay switchable via `settings.tts_provider`. Keeping BOTH working — including the
  ElevenLabs voice registry for *both* DJs — is part of the phase, so the public voice can be chosen
  (and changed) by config.

**YOU:** listen to and judge the gated output; provision the Hetzner VPS; confirm YouTube
live-streaming is enabled on the verified channel; make the launch-voice call (C6).
**CLAUDE CODE workstreams:**
- **Gates made real (C0).** Safety + continuity become *blocking* gates: a flagged or
  self-contradictory draft is regenerated or replaced by an evergreen fallback — never aired.
- **Time-aware show framing (C1).** The room picks the DJ pairing/handover from the in-world clock,
  not a hardcoded night→dawn handover (the afternoon-collision bug). Land it with/before C0 so the
  new gate isn't fighting a framing bug.
- **Honest length + a real scheduler (C2).** Measure actual audio duration; a rolling buffer to a
  configurable depth; regenerate on failure; never run dry.
- **Disclosure in the air (C3).** A spoken AI-disclosure ident on a cadence + on the player + in the
  YouTube description.
- **Never-dead air + health checks (C4).** Fallback chain (scheduled → evergreen → bed → ident) and
  alerts on stall / low-buffer / failed nightly run.
- **Deploy to the VPS (C5).** Postgres + Liquidsoap + Icecast + the nightly batch on Hetzner;
  nightly `pg_dump` backups; secrets non-world-readable. Survives a reboot, fully unattended.
- **Generation compute + voice (C6) — DECISION.** Benchmark a full day's Kokoro buffer ON THE VPS;
  if it can't render in the nightly window, move to a bigger VPS or a paid streaming TTS — never to
  local hardware. Complete the ElevenLabs registry so both DJs render on either backend.
- **YouTube Live relay + web player (C7–C8).** 24/7 RTMP push with a calm brand visual; the live
  player on settlementradio.com.
- **Soak test (C9).** 7 days unattended, zero rescues — the Phase C gate.
**CLAUDE (chat):** answers/reviews; preps the CM soft-launch copy + the grant-application answers.
**DONE WHEN:** 7 days of uninterrupted, safe, AI-disclosed, never-dead 24/7 broadcasting on the
VPS + YouTube, with zero manual rescues. **The station is then public-capable.**

---

## CM — Soft launch (marketing)

**YOU:** start posting for real on X (build-in-public has been warming since the first clip); a
quiet "it's alive" note to your existing followers; turn on **Ko-fi** (+ GitHub Sponsors); publish
the first **YouTube** clips + a short "how it's made"; **submit the grant applications now** — a
live public station is enough proof: **ElevenLabs Startup Grant, AWS Activate, Anthropic self-serve
credits.**
**CLAUDE (chat):** drafts the clips/threads/soft-launch copy and the grant-application answers.
**CLAUDE CODE:** light clip/Shorts tooling if useful; otherwise quiet.
**DONE WHEN:** the station is publicly listenable, the first real listeners + supporters are
trickling in, and the applications are submitted. *Stay quiet on purpose — the loud launch is later.*

---

## Phase D — The living world (build)

Makes the station *deep* and *alive* — the fix for "thin conversations," and what makes it worth
featuring. The heart of this phase: a world that **moves on its own** and a **news desk that reports
it like a real station**, all on top of a real bible. (Big phase — Claude (chat) sequences it into
sub-packs; the order below is roughly the build order.)

**YOU:** author the world bible (yours to write); approve generated stories/personas; make the
voice-engine call (Kokoro at scale vs. a paid flagship — emotion depends on it); set the music
policy (the *tech* is built here, the catalog/clearance is your separate call).
**CLAUDE CODE workstreams:**

- **Canon → folder (first task).** Split `docs/canon/` into cornerstone files — history, literature,
  finance, war, nations, peoples/aliens, geography, religion, culture, tech, cast; the seeder reads
  the whole folder. This is the *static substrate*: large, slow-changing, RAG-able.
- **RAG goes live.** Install pgvector, embed canon + events, semantic retrieval (the stubbed seam
  activates) — so the writers' room recalls by *meaning*, not just date/tag, once the bible is big.
  Tag the canon facts (today they're untagged, so retrieval falls back to "all") as part of this.
- **The world-simulation engine (the keystone).** A nightly "world tick" that makes the +600y world
  *live the way reality does* — a moving present on top of the static bible:
  - generates plausible new happenings consistent with the bible — large (a new festival, a
    political shift, an economic swing) and small (a cruise liner goes missing, a moon-president's
    son marries);
  - models each as a **story with an arc**, not a one-shot fact: *rumoured → upcoming → happening →
    developing → past*, each with an in-world datetime so the B2 clock frames it as future/now/past
    automatically;
  - **advances** running stories over subsequent ticks (new beats, consequences, resolutions) so the
    world has real day-to-day continuity; writes it all to the `events`/story log.
- **The news desk (reports the living world).** Replace the one-shot news bulletin with a desk that
  reads the story log and broadcasts it like a real station:
  - every hour's news is **relevant to canon AND to what's happening now**;
  - stories **recur across the day** — some simply repeated, some **repeated-and-evolved** (a fresh
    development since the last bulletin);
  - **correct temporal framing** — trailed as upcoming, covered as now, referenced as past (the B2
    relative-time renderer);
  - **continuity** — the same story is referred to consistently across segments, hours, and days.
- **Freshness / anti-repetition.** Track what aired recently (topics, openings, beats) so 24/7
  output never loops — recent-airplay memory + the moving world keep talk and news feeling fresh.
- **Programming + admin backbone.** Named programs, dayparts, and a weekly routine the scheduler
  reads (which show, which DJs, when); a **read-only status console** (what's airing, buffer depth,
  last night's run, the story log); surface **now-playing / program info** to the web player.
  *(The write/management surface — edit the grid, allocate + CRUD DJs — lands in Phase E.)*
- **Production layer (sound design).** Station idents, jingles, **beds and stings** with proper
  **ducking** — beds sit *under* speech, a sting fires *before* news; Layer 4 mixing, finally real.
  Plus **song playout (tech only):** a track pool the scheduler drops into the `music` format's
  `[SONG]` slot, with intro/back-announce and now-playing. *(Catalog + clearance excluded here — the
  plumbing is built so a cleared track just plays.)*
- **Voice & emotion + the DJ roster.** Wire the `emotion` param to the chosen engine — **ElevenLabs
  carries real emotion; Kokoro cannot**, so emotion presumes the flagship path — and add a
  **pronunciation lexicon** so the world's invented names are spoken right. Grow the cast: add / edit
  / remove DJs (a `cast` row + voice — already supported), each with their own persona, way of
  speaking, and **history/memory drawn from the event log**, so a DJ remembers what the world (and
  they) lived through.
**CLAUDE (chat):** sequences the Phase D pack into sub-packs (folder-split → world engine → news desk
→ production/voice → roster), drafts bible scaffolding + story examples, preps the loud-launch (DM)
assets.
**DONE WHEN:** the world visibly progresses on its own (fresh, evolving stories the news and DJs
reference with correct past/now/future framing), conversations draw on a real bible via semantic
recall, sound design + emotion make it *sound* like a real station — and a first-time visitor hears
enough depth to come back tomorrow.

---

## DM — Loud launch + sponsorship (marketing) ← THE COMMERCIAL GOAL

**YOU:** record/approve the **hero clip**; publish the **case study + tribute essay** (Claude drafts,
you voice and own); fire the **coordinated launch** — your four channels, plus *one-time* episodic
megaphones (Show HN + one sci-fi subreddit; not new ongoing feeds) — and be present in every thread;
after traction, send the **Anthropic devrel note** + open the **Cookbook PR** (the multi-agent
writers'-room guide).
**CLAUDE (chat):** drafts the essay, case study, launch posts, devrel note, Cookbook example.
**CLAUDE CODE:** launch polish; the Cookbook example code.
**DONE WHEN:** the launch is fired, the station *retains* the spike, and a featurable artifact + the
case study are in front of Anthropic. **This is "MVP with sponsorship":** applications in, credits
stacking, donations live, the Anthropic feature in play.

---

## Phase E — Scale, near-live & control (build)

**YOU:** watch load + cost; decide if/when a second channel is worth it; run the station day to day
through the new control surface.
**CLAUDE CODE:**
- **Near-live tier (the "live" lever).** Shrink the segment dial toward seconds, streaming TTS, Haiku
  for volume — so the station can react to the *now* instead of only playing a pre-rendered buffer.
  This is what turns "a stream" into "live radio."
- **The management / control surface.** Upgrade Phase D's read-only console into a real operator
  surface: edit the weekly grid + dayparts, allocate DJs to shows, add / edit / remove DJs and
  personas, review + approve (or reject) generated stories, trigger regeneration, manage fallbacks —
  without hand-editing files and re-seeding.
- **Listener interaction.** Inbound from the audience — requests, dedications, messages — read on air
  in character (the canon's "letters between worlds," made real), now that there *are* listeners.
- **Scale & resilience.** More channels on the same engine; performance + cost at scale; resilience
  hardening for a real audience.
**CLAUDE (chat):** the Phase E pack.
**DONE WHEN:** the station handles a real audience, offers near-live and/or a second channel, takes
listener input, and is run from a control surface — at controlled cost.

---

## EM — Sustain & grow (marketing)

**YOU:** convert the launch spike into a *returning* audience — steady X cadence + regular YouTube
clips, drawn from the devlog; grow Ko-fi/Sponsors; press + devrel follow-ups; nurture the Anthropic
relationship from a feature into an actual ongoing partnership.
**CLAUDE (chat):** ongoing content drafting from the devlog; supporter updates; follow-up outreach.
**DONE WHEN:** a durable returning audience and recurring support that covers running costs and then
some — the commercial goal, *sustained*.

---

## Phase F / BEYOND — The wider world (no dates; triggered by signals)

- **Community worldbuilding** — open inbound contributions under a **CC BY-SA** contributor
  agreement (the intended model; drafted when this triggers — see `docs/MARKETING.md` §4).
- **In-universe surfaces** — feeds, portals, new front-ends on the same world-state spine.
- **The universe beyond one station** — each new surface is a fresh pack → Claude Code; the seams
  mean none of it is a rewrite.
**DONE WHEN:** open-ended — Settlement Radio becomes a world people live in, not just a station.

---

## The standing weekly rhythm (from the soft launch on)

YOU: ~3 Claude Code sessions + a few X posts + the occasional YouTube clip + listen to the station.
CLAUDE (chat): drafts content, preps the next pack, answers anything.
CLAUDE CODE: builds what the current pack says.

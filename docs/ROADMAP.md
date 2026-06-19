# ROADMAP.md — Settlement Radio: the one path

When you feel overloaded, read only this file. It merges the tech and social tracks into one
sequence and says, for every phase: **what YOU do, what CLAUDE (chat) does, what CLAUDE CODE
does**, and how you know the phase is done.

**The three milestones:**
- **Mini-MVP** = end of Phase A — you can hear the station on your own machine.
- **MVP with sponsorship** = end of Phase D — public 24/7 station + launch + grant applications in.
- **Full product** = beyond — near-live, more channels, the wider +600y world.

Rule of thumb for the division of labor: **you** decide, listen, claim accounts, post, and apply
for things (only a human can). **Claude in chat** plans, writes docs/copy, researches, and
prepares the next phase's task packs. **Claude Code** builds and operates everything in the repo.

---

## PHASE 0 — Claim the ground (this week, ~3–4 h of your time)

**YOU:**
1. Buy the domain FIRST (everything hangs off it) — via the deal that bundles the Microsoft
   365 mailbox. Use `hello@settlementradio.com` from that mailbox **directly** for ALL project
   accounts below — no email-routing/forwarding layer. Host DNS in ONE place (the domain/mail
   provider, or Vercel) and add both the Microsoft mail records (MX/SPF/DKIM/autodiscover) and
   the Vercel site records there. No Cloudflare needed.
   - Caveat: confirm it's a real *sending-capable* M365 mailbox, not forwarding-only. If it's
     forwarding-only, it's no better than free Cloudflare Email Routing into Gmail — in that case
     use the free Cloudflare route and skip the paid add-on.
2. One sitting: claim `@settlementradio` on YouTube, X, Instagram, Bluesky, Reddit, Ko-fi;
   create the GitHub **organization** `settlementradio` (org name is the unique asset; the repo
   inside can be named anything). Quick USPTO/EUIPO sanity search.
3. Create Anthropic Console account + small prepaid credit; ElevenLabs account (free tier);
   put both API keys aside for `.env`.
4. Install Claude Code on your Mac (Node LTS + the CLI).
5. Start the habit: screen-record Claude Code sessions; keep a `devlog/` folder of clips +
   one-line notes. This footage is future marketing gold and can't be recreated.
6. Stand up the one-page "coming soon" site **on Vercel** (you have Pro; it's the production
   host too): premise (tribute hook), AI disclosure line, email signup. Nothing else public yet.

**CLAUDE (chat):** done for this phase — the doc pack exists. On call for copy/naming/questions.
**CLAUDE CODE:** nothing yet.
**DONE WHEN:** domain + handles + org claimed; keys in hand; Claude Code runs; site is up.

---

## PHASE A — Mini-MVP: proof of loop (weeks 1–2)

**YOU:** create the repo in the org; drop in the doc pack (`CLAUDE.md` at root; `ARCHITECTURE.md`,
`CANON.md`, `PHASE_A_TASKS.md`, this file under `docs/`); add `.env` with the two keys. Then run
Claude Code task by task: "work T0, then stop and show me." Listen to the output, judge the
voice, request retakes. Keep recording sessions.
**CLAUDE CODE:** executes T0–T6 (scaffold → provider seam → Segment seam → script → audio →
playout → `make play`). T7 (60-second drop) only if solid.
**CLAUDE (chat):** reviews anything you paste, helps when Claude Code gets stuck, and prepares
the **Phase B pack** (PHASE_B_TASKS.md + content calendar) when you say A is done.
**SOCIAL:** still quiet. Keep capturing footage.
**DONE WHEN:** `make play` → you hear Vell deliver a fresh, in-character segment with a correct
time check. **That's the mini-MVP.**

---

## PHASE B — The mind (weeks 3–6)

**YOU:** session-by-session with Claude Code as before; make the canon calls it can't (approve
events, tune personas); pick the second DJ's voice. **Social switches ON:** first clip posted
(the moment a DJ speaks), then 2–3 short posts/week + 1 "how it works" thread/week, from the
content calendar.
**CLAUDE CODE:** Phase B tasks — world clock + event store + progression (the
"concert in 5 days → yesterday" demo), pgvector RAG + prompt-cached canon, DJ #2, the
conversation orchestrator, the 3 show formats, nightly batch via the Batch API.
**CLAUDE (chat):** drafts your posts/threads from your devlog clips; prepares the **Phase C pack**
(VPS/YouTube/safety-gate tasks + soft-launch checklist).
**DONE WHEN:** two DJs hold a sensible in-character conversation that *uses* canon, and the
progressing-event demo works end to end. (That demo clip = your future hero asset.)

---

## PHASE C — The body: soft launch (weeks 6–8)

**YOU:** order the Hetzner CX22; create the YouTube Live stream; turn on Ko-fi + GitHub Sponsors;
quietly invite your seeded followers; watch the station for a week and file what breaks.
**CLAUDE CODE:** deploys playout to the VPS, wires Icecast → YouTube relay, builds the
content-safety gate + spoken/on-page AI disclosure, fallback chain, basic status/alerts.
**CLAUDE (chat):** soft-launch copy (site, channel descriptions, pinned posts), prepares the
**Phase D pack** (launch beats + grant application drafts).
**DONE WHEN:** 7 days of uninterrupted, safe, disclosed 24/7 broadcasting with zero manual
rescues. **Do not go loud before this.**

---

## PHASE D — Launch + sponsorship (weeks 8–10)

**YOU:** record/approve the hero clip (the time-progression moment); publish the case study +
tribute essay (Claude drafts, you voice); fire the coordinated 48h launch (Show HN + 2–3
subreddits + clip everywhere) and be present in every thread; **submit the applications:**
ElevenLabs Startup Grant, AWS Activate Founders, Anthropic self-serve credits; open a PR to the
Anthropic Cookbook (the multi-agent writers'-room guide); after visible traction, send the short
note to Anthropic devrel pointing at the live station + writeup.
**CLAUDE CODE:** the 60-second near-live drop demo (proving the segment dial), polish, the
Cookbook example code.
**CLAUDE (chat):** drafts everything above — essay, case study, HN/Reddit posts, grant answers,
the devrel note.
**DONE WHEN:** station public + launch fired + all applications submitted. **That's the MVP with
sponsorship** — sponsorship here means: applications in, credits stacking, and a featurable
artifact in front of Anthropic.

---

## BEYOND — Full product (no dates; triggered by signals, not the calendar)

- **Credits land** (ElevenLabs/AWS) → flip flagship voices to premium; lean into "powered by" story.
- **Returning listeners ask for more** → near-live tier (shrink segment params, Haiku + streaming
  TTS), more channels on the same engine.
- **Community forms** → open worldbuilding contributions (CC BY-SA inbound agreement is ready in
  the funding kit).
- **The wider world** (in-universe feeds, portals) → new surfaces on the same world-state spine.
- Each step = a new task pack from Claude (chat) → executed by Claude Code. The architecture
  seams mean none of it is a rewrite.

---

## The standing weekly rhythm (from Phase B on)

You: ~3 Claude Code sessions + 2–3 short posts + 1 longer piece + listen to the station.
Claude (chat): drafts content, preps the next pack, answers anything.
Claude Code: builds what the current pack says.

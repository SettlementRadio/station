# marketing/X.md — the X (Twitter) execution playbook

Concrete, copy-paste-ready X tasks for Phase C. The strategy lives in `docs/MARKETING.md`; this is
**execution** — one of a per-platform set (X · YouTube · GitHub · site · Ko-fi · Anthropic outreach;
this is the X one). Sequencing lives in `docs/ROADMAP.md`.

**How a task works:** every task **`MX#`** lists the **C-task it depends on** (you can't post about a
thing before the code that makes it true exists), the **audience**, the **goal**, the **asset** you
need (image/sound/video), the **exact text to post**, **Done-when** (binary), and **Result check**
(what signal to look at 48–72h later). Post a task only after its dependency is ✅.

**The in-world year is `real year + 600`.** In 2026 that's **2626**. All copy below uses 2626 — if you
post a task in a later calendar year, bump it (2627, …). Never imply the year is fixed.

**Status legend (validated 2026-06-23, against C0–C3 + C2.5 done and the DEVLOG):**
- **`✅ READY`** — its tech is built, and the copy below has been cross-checked against the DEVLOG /
  code and corrected to match reality. Safe to post once the *asset* is cut (noted per task).
- **`📝 DRAFT`** — its tech isn't built yet; the copy is a plan written ahead and will be re-validated
  against the DEVLOG when its C-task lands (the next loop).

**Handle note:** the live X handle is **`@settlement_ch`** (per the site footer) — `@settlementradio`
was unavailable on X. Use `@settlement_ch` in copy that needs the @.

---

## Audience, hooks, goals (read once)

- **Lead with the core message (see `MARKETING.md` → core message), even on dev-leaning X:** the WHAT
  is *a living human future you tune into — the one signal holding a scattered humanity together* —
  **not** "AI DJs." Then the build-story (HOW), then the motto/tribute (WHY): *"A love letter to
  20th-century science fiction — broadcasting from the future it imagined."* Don't feature-list, and
  don't headline the DJs in foundational copy (they shine in the *progress* posts below).
- **Primary audience on X:** indie devs / AI builders. **Lead with the built-by-agents hook**
  ("an entire 600-years-future station stood up by Claude Code"). They share things that are
  *technically novel and honestly documented* — but pair it with the tribute so it has a soul.
- **Secondary thread:** sci-fi / worldbuilding people (the tribute hook). Lore drops carry this.
- **Goal through Phase C:** seed the **first ~100 genuinely-interested followers** and build the
  agentic-build narrative that earns an Anthropic feature later — *before* the soft launch (M1).
  This is audience-*seeding*, not launch. Stay calm; the loud launch is Phase D / M4.
- **IP safety:** the tribute is to **20th- / early-21st-century science fiction — the golden-age and
  new-wave authors** and their *spirit*. Honor the era and its ideas; **never** name a franchise, a
  character, or a living author's creation. This is the one rule that matters most in public.

## Posting mechanics (the "when" and "how")

- **Cadence = event-driven.** Post one substantive task when its dependency C-task lands. That's a
  natural ~1 post/week through Phase C — which is the right pace. Between drops, at most one light
  post (a one-line lore drop, or a genuine reply/quote in a dev/sci-fi thread). Protect the build.
- **Best window:** weekday mornings, ~9–11am US-Eastern (the EU/US dev overlap). Avoid weekends for
  the technical threads.
- **Be present:** reply to every genuine comment in the first 2 hours. Engagement is the multiplier
  on a small account.
- **Native media always:** upload video/audio directly (don't link out to it); X suppresses external
  links and autoplays native media. Keep threads to ≤4 posts.
- **What "success" looks like here is small:** a few real follows, **bookmarks** (the strongest
  "I'll come back" signal — watch these over likes), profile visits, and the occasional reshape.
  Don't chase likes.

## Asset conventions (make once, reuse)

- **Brand card** — the night-field + beacon + wordmark visual (same family as the YouTube stream
  still). Build a reusable Canva template; 16:9 for cards, 1500×500 for the header.
- **Audiogram** — audio over the brand still with a waveform + **burned-in captions** (most people
  watch muted). 1:1 or 16:9, keep under ~60s. Tool: any free audiogram maker, or `ffmpeg` over the
  brand still + the segment WAV from `segments/`.
- **Code/terminal card** — a clean, mobile-readable screenshot (real terminal or a Canva mock) for
  the how-it-works threads. Readable at phone size or it's useless.

---

## The tasks

### MX0 — Account foundation · `✅ READY`
**Depends on:** nothing — **do now.**
**Audience:** everyone who lands on the profile. **Goal:** a profile that explains the project in 3
seconds and looks intentional, so build-in-public posts convert visitors to followers.
**Assets:** header image (brand card, 1500×500); a square avatar (the beacon mark).
**Do — set these fields:**
- **Handle:** `@settlement_ch` (the existing handle — confirm it, don't make a new one).
- **Name:** `Settlement Radio`
- **Bio:** `Radio from the human future — the signal holding a scattered humanity together across the dark. By Claude + Claude Code. A love letter to 20th-c sci-fi. 🛰️` *(world-first; the 160-char bio carries WHAT+HOW+a tribute nod — the DJs live in the pinned posts, not here.)*
- **Location:** `Broadcasting from 2626`
- **Website:** `settlementradio.com`
**Done-when:** all four fields + header + avatar are set.
**Result check:** n/a (foundation) — just confirm it reads clearly on mobile.

### MX1 — Plant the flag (the premise post) · `✅ READY`
**Depends on:** nothing — **do now**, right after MX0.
**Audience:** dev + sci-fi. **Goal:** state the premise once, openly; start the follow relationship.
**Asset:** one brand card (or text-only).
**Post:**
> Six hundred years from now, humanity is scattered across the settled worlds — and one signal keeps them company across the dark between them.
>
> We're building that signal: Settlement Radio — always-on radio from the human future, carrying the news, the music, and the long nights of a whole era. Every word written by Claude; the whole station built by Claude Code, in public.
>
> A love letter to 20th-century science fiction — broadcasting from the future it imagined.
>
> Follow along. 🛰️
**Done-when:** posted.
**Result check (72h):** any follows + bookmarks at all = the premise lands. Note which hook the
repliers respond to (tech vs. tribute) — it tells you which to lead with next.

### MX1b — The "why" (the tribute post) — pin-worthy companion · `✅ READY`
**Depends on:** nothing — **do now**, a day or two after MX1.
**Audience:** sci-fi / general (the tribute hook leads here). **Goal:** make the *soul* of the project
unmistakable early, so the channel never reads as only a tech demo. This is the seed of the eventual
tribute essay (M4).
**Asset:** a quiet brand card, or text-only.
**Post:**
> Why a radio station from the future?
>
> Because a generation grew up on science fiction that promised us somewhere to go — the golden-age and new-wave writers who imagined settled worlds, long nights between the stars, voices carrying across the dark.
>
> Settlement Radio is a thank-you to them. Not their worlds — our own, built in their spirit, broadcasting from 600 years on, the way they taught us to dream it. 🌌
**Done-when:** posted.
**Result check (72h):** replies that *get it* (people naming what the genre meant to them) +
bookmarks. This post tells you whether the tribute lands — if it's flat, sharpen it; it's the heart.

### MX2 — First real conversation (the held first clip) — PIN THIS · `✅ READY`
**Depends on:** **C1** (time-aware framing) — the clip must be a continuity-passing segment, *not*
the afternoon-handover bug. Confirm by ear before posting.
**Audience:** dev + sci-fi. **Goal:** let people *hear* the personality — the single highest-leverage
post of the phase.
**Asset:** a 30–60s **audiogram** (captions burned in) cut from the real two-voice segment. **Source
audio exists:** `segments/convo-20260622T224629.mp3` (a 2:47 Vell↔Wren talk segment) — still needs
cutting into a captioned clip. *(Verify by ear which lines it actually contains before you post —
copy below matches the B4 reference render: the Lumen Festival a few days out + relay letters.)*
**Post:**
> Settlement Radio just held its first real conversation.
>
> Two DJs — Vell on the night shift, Wren bringing in first light — in character, talking about the Lumen Festival a few days out, and letters weeks old still riding the relay between worlds. And they know it's the year 2626.
>
> Every word written by Claude. Every voice synthetic. 🎧👇
**Done-when:** posted **and pinned** to the profile.
**Result check (72h):** video views, **completion rate** (did people listen to the end?), bookmarks,
and any reshare. This is your benchmark clip — save the numbers to compare future clips against.

### MX3 — "How it doesn't embarrass itself" (the safety + continuity gate) · `✅ READY`
**Depends on:** **C0** (gates made real).
**Audience:** dev/AI (this is the trust-building, technically-credible thread). **Goal:** establish
that the station is *safe and reliable by design* — the precondition for anyone amplifying it.
**Asset:** optional code/terminal card showing a flagged draft being blocked + replaced by evergreen.
**Post (thread):**
> 1/ A 24/7 AI station has one terrifying failure mode: it says something unsafe, or contradicts itself on air, and no human is watching.
>
> So before Settlement Radio broadcasts to anyone, we built the gate. Here's how it works. 🧵
>
> 2/ Every line a DJ "writes" clears two checks before it can air. First, safety: a fast keyword pre-filter (no API), then a cheap Haiku pass — tuned to *allow* in-world sci-fi conflict and flag only what's genuinely unsafe. Flagged → regenerate → still bad → fall back to a pre-approved evergreen segment. Nothing flagged ever reaches the stream.
>
> 3/ Second, continuity: does this segment contradict the world's canon, or something that already aired? An editor pass checks. Fails → regenerate with the note fed back. Still failing → evergreen fallback. The station would rather repeat itself than lie.
>
> 4/ All written and checked by Claude — Haiku for the cheap high-volume passes, Sonnet for the writing. No human in the loop, by design. Reliability is the whole product: you can't amplify something that might embarrass you at 3am.
**Done-when:** thread posted.
**Result check (72h):** bookmarks + profile visits + new follows (this thread is a *credibility*
asset — devs bookmark and follow). Replies asking "how" = success; engage every one.

### MX4 — "It knows what time it is" (the world clock) · `✅ READY`
**Depends on:** **C1** (time-aware framing) + B2 (the relative-time renderer).
**Audience:** dev + sci-fi (this is the concept that makes the project *novel*). **Goal:** show the
single most distinctive idea — a station genuinely living 600 years ahead, in real time.
**Asset:** a short clip of one line aging "in five days" → "tonight" → "yesterday", OR an animated
text card of the same.
**Post (thread):**
> 1/ The hardest part of a station set 600 years in the future isn't the voices. It's time.
>
> Settlement Radio knows the real date, lives 600 years ahead of it, and speaks of events as future, now, or past — correctly. Here's the trick. 🧵
>
> 2/ A real Tuesday 02:00 in 2026 is a Tuesday 02:00 in 2626 on the station's clock — the same flow of time, shifted +600 years. So the Lumen Festival, dated "in five days," is genuinely upcoming. In five days, the DJs talk about it as last night.
>
> 3/ A relative-time renderer speaks any in-world datetime like a person would — "in five days," "tonight," "yesterday"; the DJs never touch a raw date. And the room reads the wall clock for *who's on air*: Vell solo deep at night, the handover to Wren at first light. The station is, quietly, actually live in its own timeline.
**Done-when:** thread posted.
**Result check (72h):** reshares/quotes (this is the most "quotable" idea — watch for it spreading
beyond your followers) + bookmarks.

### MX5 — "It programs itself" (the scheduler) · `✅ READY`
**Depends on:** **C2** (honest length + real scheduler). *(C2.5 disk-GC also done — too low-glamour
for its own post; mention only as a reply if someone asks how 24/7 audio doesn't fill the disk.)*
**Audience:** dev/AI. **Goal:** show the station is a *system*, not a loop — and tease the near-live
future without over-promising it.
**Asset:** a status/terminal card showing the buffer + ordered playlist (`segments/playlist.txt`).
**Post:**
> Settlement Radio now programs itself.
>
> Not a playlist on loop — a scheduler that picks what airs next, measures the *real* length of every segment (ffprobe, not a guess), keeps a rolling buffer so it never runs dry, and regenerates anything that fails.
>
> One dial sets how many hours to stay ahead (3h today). Later, that same dial turns toward seconds — and "a stream" becomes "live radio." 🛰️
**Done-when:** posted.
**Result check (72h):** bookmarks + replies from builders ("how's the buffer sized?" etc.). Don't
promise a near-live date — note it's "later."

### MX6 — "We taught it to admit what it is" (AI disclosure) · `✅ READY`
**Depends on:** **C3** (disclosure in the air).
**Audience:** dev + general. **Goal:** turn a legal requirement into a *trust* moment — and model
honest AI disclosure publicly (Anthropic-aligned values). **Bonus:** the real ident has the *tribute*
built into it — this post carries both the honesty and the soul at once.
**Asset:** a short **audiogram** of the spoken disclosure ident. **Source audio exists & is final:**
`segments/ident-disclosure-kokoro-vell_night.mp3` (~12s, Vell's voice; re-render any time with
`make ident`) — just needs the waveform + captions.
**Post:** *(quote the ident verbatim — this is the exact line that airs, from `src/disclosure.py`)*
> We taught the station to admit what it is.
>
> Every few segments, in Vell's voice, you'll hear: *"You're listening to Settlement Radio — a work of fiction, written and voiced by artificial intelligence. Everything you hear is imagined: a tribute to the science fiction that dreamed us all the way out here."*
>
> Disclosure isn't a disclaimer we bury. It's part of the broadcast — and it says why we're here. 🛰️👇
**Done-when:** posted with the ident clip.
**Result check (72h):** sentiment of replies (this should read as *integrity*, not apology) +
bookmarks.

### MX7 — "We broke it on purpose" (never-dead air) · `📝 DRAFT`
**Depends on:** **C4** (fallback chain + health checks). *(Re-validate against the C4 DEVLOG entry
when it lands.)*
**Audience:** dev/AI. **Goal:** prove operational reliability — the thing that makes it safe to
amplify and safe to leave running.
**Asset:** optional clip/terminal showing the generator killed while the stream keeps playing.
**Post (thread):**
> 1/ What happens when an AI radio station's brain dies at 3am?
>
> We went and broke it on purpose. The stream kept playing. Here's the fallback chain that makes Settlement Radio impossible to kill with a single failure. 🧵
>
> 2/ Four layers, in order: the scheduled segment → a pre-rendered evergreen → a music bed → the station ident. If everything upstream fails, it still never airs a second of silence. Plus health checks: a stall, a low buffer, or a failed nightly run pings us.
**Done-when:** thread posted.
**Result check (72h):** bookmarks + follows from the ops/infra crowd.

### MX8 — "It left my laptop" (live on the VPS) · `📝 DRAFT`
**Depends on:** **C5** (deploy to the VPS). *(Re-validate against the C5 DEVLOG entry — confirm the
real box/specs before posting.)*
**Audience:** dev + general. **Goal:** the "it's becoming real" milestone — 24/7, unattended, one
step from public.
**Asset:** a brand card, or a terminal screenshot of the services running on the box.
**Post:**
> Settlement Radio just left my laptop.
>
> It now runs on its own server — generation, playout, the world database, nightly backups — 24/7, fully unattended. No personal hardware in the loop, ever.
>
> It survives a reboot and keeps broadcasting. One step from opening the doors. 🛰️
**Done-when:** posted.
**Result check (72h):** follows + replies anticipating launch ("when can we listen?" = exactly the
demand you want building).

### MX9 — Meet the voices (the launch voice reveal) · `📝 DRAFT`
**Depends on:** **C6** (generation compute + public voice DECISION) — post the *chosen launch
voice*. *(Re-validate against the C6 DEVLOG decision — the post hinges on which voice ships.)*
**Audience:** sci-fi + dev. **Goal:** humanize the DJs right before launch; build attachment to Vell
and Wren as characters.
**Asset:** a **clip of the Vell→Wren handover** (night into first light) in the chosen launch voice.
**Post:**
> Meet the voices of Settlement Radio.
>
> Vell — the night shift. Low, warm, unhurried.
> Wren — first light. Brighter, awake.
>
> We just locked the production voice for launch. Here's the handover — night into morning, 600 years from now. 🎧👇
**Done-when:** posted with the handover clip.
**Result check (72h):** completion rate + bookmarks vs. your MX2 benchmark — voice attachment should
push these higher.

### MX10 — "It's live" (the soft launch) — RE-PIN THIS · `📝 DRAFT`
**Depends on:** **C9** (7-day soak passed) — and C7 + C8 live (stream + player). **This is milestone
M1.** Coordinate with the Ko-fi and YouTube tasks (their own docs). *(Re-validate against the
C7–C9 DEVLOG entries; fill the real YouTube + Ko-fi links.)*
**Audience:** your warmed followers first — **keep it soft**. The loud launch (Show HN, the hero
clip, the essay) is Phase D / M4.
**Asset:** the live stream link + a strong 60s clip from the live station.
**Post (thread):**
> 1/ Settlement Radio is live.
>
> Always-on radio from the human future — the one signal that holds a scattered humanity together across the dark between worlds, 600 years from now. Every word written by Claude, the whole station built entirely by Claude Code, in public, over the last few months.
>
> Listen: [YOUTUBE LIVE LINK] 🛰️🧵
>
> 2/ It ran unattended for 7 days straight — safe, never a second of dead air, disclosing itself on air the whole time — before I let anyone in. Reliability was the gate, not an afterthought. This is a soft open; it only gets deeper from here.
>
> 3/ If you want to help fund the next DJ and the next chunk of the world: [KO-FI LINK]. And if you've followed the build — thank you. Pull up a chair. The night shift is on. 🌌
**Done-when:** thread posted, **pinned** (replacing MX2), links live and tested.
**Result check (1 week):** new followers + concurrent listeners off the link + first Ko-fi activity +
**returning visitors** in Plausible (the north-star signal). Log the launch-day baseline — M3
(retention) is measured against it.

---

## Dependency map (X → Phase C)

| Task | Depends on | Status | Type | Pinned? |
|------|-----------|--------|------|---------|
| MX0 Foundation | — (now) | ✅ READY | profile | — |
| MX1 Premise | — (now) | ✅ READY | post | — |
| MX1b The "why" / tribute | — (now) | ✅ READY | post | — |
| MX2 First conversation | **C1** | ✅ READY (cut clip) | audiogram | 📌 pin |
| MX3 Safety/continuity gate | **C0** | ✅ READY | thread | — |
| MX4 World clock | **C1** | ✅ READY | thread + clip | — |
| MX5 Scheduler | **C2** | ✅ READY | post + card | — |
| MX6 Disclosure | **C3** | ✅ READY (cut clip) | audiogram | — |
| MX7 Never-dead air | **C4** | 📝 DRAFT | thread | — |
| MX8 On the VPS | **C5** | 📝 DRAFT | post | — |
| MX9 Voice reveal | **C6** | 📝 DRAFT | clip | — |
| MX10 Soft launch (M1) | **C9** (+C7,C8) | 📝 DRAFT | thread | 📌 re-pin |

## Running metrics log (fill as you go)

Track these per task so "did it work?" is auditable. Cumulative goal by MX10: **~100 genuinely
interested followers** and **≥1 organic reshare** across the run.

| Task | Date posted | Views | Bookmarks | New follows | Reshares | Notes |
|------|-------------|-------|-----------|-------------|----------|-------|
| MX1 | | | | | | |
| MX2 | | | | | | benchmark clip |
| … | | | | | | |

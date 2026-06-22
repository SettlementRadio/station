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

---

## Audience, hooks, goals (read once)

- **Primary audience on X:** indie devs / AI builders. **Lead with the built-by-agents hook**
  ("an entire 600-years-future station stood up by Claude Code"). They share things that are
  *technically novel and honestly documented*.
- **Secondary thread:** sci-fi / worldbuilding people (the tribute hook). Lore drops carry this.
- **Goal through Phase C:** seed the **first ~100 genuinely-interested followers** and build the
  agentic-build narrative that earns an Anthropic feature later — *before* the soft launch (M1).
  This is audience-*seeding*, not launch. Stay calm; the loud launch is Phase D / M4.
- **IP safety:** frame everything as *tribute* — "the authors who imagined the future," the *spirit*
  of golden-age sci-fi. Never a named franchise, character, or living author's creation. This is the
  one rule that matters most in public.

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

### MX0 — Account foundation
**Depends on:** nothing — **do now.**
**Audience:** everyone who lands on the profile. **Goal:** a profile that explains the project in 3
seconds and looks intentional, so build-in-public posts convert visitors to followers.
**Assets:** header image (brand card, 1500×500); a square avatar (the beacon mark).
**Do — set these fields:**
- **Name:** `Settlement Radio`
- **Bio:** `AI sci-fi radio from 600 years ahead. Synthetic DJs, every word written by Claude, built by Claude Code. A tribute to the authors who imagined the future. 🛰️`
- **Location:** `Broadcasting from 2626`
- **Website:** `settlementradio.com`
**Done-when:** all four fields + header + avatar are set.
**Result check:** n/a (foundation) — just confirm it reads clearly on mobile.

### MX1 — Plant the flag (the premise post)
**Depends on:** nothing — **do now**, right after MX0.
**Audience:** dev + sci-fi. **Goal:** state the premise once, openly; start the follow relationship.
**Asset:** one brand card (or text-only).
**Post:**
> We're building a radio station that broadcasts from the year 2626 — 600 years ahead of right now.
>
> Two AI DJs. Every word written by Claude. The whole thing built by Claude Code, in public.
>
> No franchise, no borrowed IP — an original world, as a tribute to the sci-fi that raised us.
>
> Follow along. 🛰️
**Done-when:** posted.
**Result check (72h):** any follows + bookmarks at all = the premise lands. Note which hook the
repliers respond to (tech vs. tribute) — it tells you which to lead with next.

### MX2 — First real conversation (the held first clip) — PIN THIS
**Depends on:** **C1** (time-aware framing) — the clip must be a continuity-passing segment, *not*
the afternoon-handover bug. Confirm by ear before posting.
**Audience:** dev + sci-fi. **Goal:** let people *hear* the personality — the single highest-leverage
post of the phase.
**Asset:** a 30–60s **audiogram** of the Vell↔Wren talk segment (captions burned in).
**Post:**
> Settlement Radio just held its first real conversation.
>
> Two DJs — Vell on the night shift, Wren bringing in first light — in character, talking about a concert happening "in five days." And the station knows it's the year 2626.
>
> Every word written by Claude. Every voice synthetic. 🎧👇
**Done-when:** posted **and pinned** to the profile.
**Result check (72h):** video views, **completion rate** (did people listen to the end?), bookmarks,
and any reshare. This is your benchmark clip — save the numbers to compare future clips against.

### MX3 — "How it doesn't embarrass itself" (the safety + continuity gate)
**Depends on:** **C0** (gates made real).
**Audience:** dev/AI (this is the trust-building, technically-credible thread). **Goal:** establish
that the station is *safe and reliable by design* — the precondition for anyone amplifying it.
**Asset:** optional code/terminal card showing a flagged draft being blocked + regenerated.
**Post (thread):**
> 1/ A 24/7 AI station has one terrifying failure mode: it says something unsafe, or contradicts itself on air, and no human is watching.
>
> So before Settlement Radio broadcasts to anyone, we built the gate. Here's how it works. 🧵
>
> 2/ Every line a DJ "writes" clears two checks before it can air. First, safety: a fast filter plus a cheap LLM pass. Flagged → regenerate once → if it's still bad, fall back to a pre-approved evergreen segment. Nothing flagged ever reaches the stream.
>
> 3/ Second, continuity: does this segment contradict the world's canon, or something that already aired? An editor pass checks. Fails → regenerate with the note fed back. Still failing → evergreen fallback. The station would rather repeat itself than lie.
>
> 4/ All written and checked by Claude — Haiku for the cheap high-volume passes, Sonnet for the writing. No human in the loop, by design. Reliability is the whole product: you can't amplify something that might embarrass you at 3am.
**Done-when:** thread posted.
**Result check (72h):** bookmarks + profile visits + new follows (this thread is a *credibility*
asset — devs bookmark and follow). Replies asking "how" = success; engage every one.

### MX4 — "It knows what time it is" (the world clock)
**Depends on:** **C1** (time-aware framing + the relative-time renderer).
**Audience:** dev + sci-fi (this is the concept that makes the project *novel*). **Goal:** show the
single most distinctive idea — a station genuinely living 600 years ahead, in real time.
**Asset:** a short clip of one line aging "in five days" → "tonight" → "yesterday", OR an animated
text card of the same.
**Post (thread):**
> 1/ The hardest part of a station set 600 years in the future isn't the voices. It's time.
>
> Settlement Radio knows the real date, lives 600 years ahead of it, and speaks of events as future, now, or past — correctly. Here's the trick. 🧵
>
> 2/ A real Tuesday 02:00 in 2026 is a Tuesday 02:00 in 2626 on the station's clock — the same flow of time, shifted +600 years. So a concert dated "in five days" is genuinely upcoming. In five days, the DJs talk about it as last night.
>
> 3/ We built a relative-time renderer: give it any in-world datetime and it speaks it like a person would — "in five days," "tonight," "yesterday." The DJs never touch a raw date. The station is, quietly, actually live in its own timeline.
**Done-when:** thread posted.
**Result check (72h):** reshares/quotes (this is the most "quotable" idea — watch for it spreading
beyond your followers) + bookmarks.

### MX5 — "It programs itself" (the scheduler)
**Depends on:** **C2** (honest length + real scheduler).
**Audience:** dev/AI. **Goal:** show the station is a *system*, not a loop — and tease the near-live
future without over-promising it.
**Asset:** a status/terminal card showing the buffer + ordered schedule.
**Post:**
> Settlement Radio now programs itself.
>
> Not a playlist on loop — a scheduler that picks what airs next, measures the real length of every segment, keeps a rolling buffer so it never runs dry, and regenerates anything that fails.
>
> One dial sets how many hours to stay ahead. Later, that same dial turns toward seconds — and "a stream" becomes "live radio." 🛰️
**Done-when:** posted.
**Result check (72h):** bookmarks + replies from builders ("how's the buffer sized?" etc.). Don't
promise a near-live date — note it's "later."

### MX6 — "We taught it to admit what it is" (AI disclosure)
**Depends on:** **C3** (disclosure in the air).
**Audience:** dev + general. **Goal:** turn a legal requirement into a *trust* moment — and model
honest AI disclosure publicly (Anthropic-aligned values).
**Asset:** a short **audiogram** of the spoken disclosure ident.
**Post:**
> We taught the station to admit what it is.
>
> On a regular cadence, between segments, you'll hear: "Settlement Radio — a work of fiction, voiced with AI." It's on the player and in the description too.
>
> Disclosure isn't a disclaimer we bury. It's part of the broadcast. 🛰️👇
**Done-when:** posted with the ident clip.
**Result check (72h):** sentiment of replies (this should read as *integrity*, not apology) +
bookmarks.

### MX7 — "We broke it on purpose" (never-dead air)
**Depends on:** **C4** (fallback chain + health checks).
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

### MX8 — "It left my laptop" (live on the VPS)
**Depends on:** **C5** (deploy to the VPS).
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

### MX9 — Meet the voices (the launch voice reveal)
**Depends on:** **C6** (generation compute + public voice DECISION) — post the *chosen launch
voice*.
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

### MX10 — "It's live" (the soft launch) — RE-PIN THIS
**Depends on:** **C9** (7-day soak passed) — and C7 + C8 live (stream + player). **This is milestone
M1.** Coordinate with the Ko-fi and YouTube tasks (their own docs).
**Audience:** your warmed followers first — **keep it soft**. The loud launch (Show HN, the hero
clip, the essay) is Phase D / M4.
**Asset:** the live stream link + a strong 60s clip from the live station.
**Post (thread):**
> 1/ Settlement Radio is live.
>
> A 24/7 AI sci-fi station broadcasting from the year 2626. Two synthetic DJs, an original world, every word written by Claude — built entirely by Claude Code, in public, over the last few months.
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

| Task | Depends on | Type | Pinned? |
|------|-----------|------|---------|
| MX0 Foundation | — (now) | profile | — |
| MX1 Premise | — (now) | post | — |
| MX2 First conversation | **C1** | audiogram | 📌 pin |
| MX3 Safety/continuity gate | **C0** | thread | — |
| MX4 World clock | **C1** | thread + clip | — |
| MX5 Scheduler | **C2** | post + card | — |
| MX6 Disclosure | **C3** | audiogram | — |
| MX7 Never-dead air | **C4** | thread | — |
| MX8 On the VPS | **C5** | post | — |
| MX9 Voice reveal | **C6** | clip | — |
| MX10 Soft launch (M1) | **C9** (+C7,C8) | thread | 📌 re-pin |

## Running metrics log (fill as you go)

Track these per task so "did it work?" is auditable. Cumulative goal by MX10: **~100 genuinely
interested followers** and **≥1 organic reshare** across the run.

| Task | Date posted | Views | Bookmarks | New follows | Reshares | Notes |
|------|-------------|-------|-----------|-------------|----------|-------|
| MX1 | | | | | | |
| MX2 | | | | | | benchmark clip |
| … | | | | | | |

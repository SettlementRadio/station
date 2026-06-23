# marketing/youtube.md — the YouTube execution playbook

Concrete, copy-paste-ready YouTube tasks for Phase C. Strategy: `docs/MARKETING.md`. Sequence:
`docs/ROADMAP.md`. Sibling execution doc: `docs/marketing/X.md`.

**Read the task format in `X.md` once** — same shape here: each **`MY#`** lists its **C-task
dependency**, audience, goal, asset, exact copy, **Done-when**, and **Result check**.

**YouTube is different from X.** On X you *talk about* the build. On YouTube the **24/7 live stream
is the product itself** (the "lofi radio" playbook — people find it via search/recommendations and
leave it on), and **Shorts are the discovery engine**. So YouTube has two jobs: (1) stand up and run
the stream, (2) feed Shorts/clips that pull strangers toward it. Long-form explainers are secondary
until Phase D.

**The in-world year is `real year + 600` → 2626 in 2026.** Bump it if you publish in a later year.

> **⚠️ Do this on day one, before anything else:** in YouTube Studio, **enable live streaming** on
> the channel (Settings → Channel → Feature eligibility → "Live stream"). It needs phone
> verification and there's a **~24h activation delay** — so turn it on now or C7 will stall waiting
> on Google, not on code.

---

## Audience, hooks, goals

- **Audience:** two pools. **Ambient/lofi-stream listeners** (find you by search + recommendations;
  the bar is a *pleasant, reliable, distinctive* stream) and **the curious** who click a Short and
  fall into the world. Mixed dev + sci-fi.
- **Lead hook on YouTube:** the **experience** — "a calm sci-fi station you can leave on" — with the
  built-by-Claude-Code story as the reason-to-care underneath. Less technical than X.
- **The motto (carry it — see `MARKETING.md`):** *"A love letter to 20th-century science fiction —
  broadcasting from the future it imagined."* Put the tribute in the channel About and the trailer;
  it's the soul, not a footer.
- **Goal through Phase C:** have the channel + a small Shorts library ready so that when the live
  stream goes public (M1), there's somewhere for discovery to land. **North star: returning viewers
  + watch time**, not subscriber count.
- **IP safety:** tribute framing only — never a named franchise/character/living author's creation.

## Posting mechanics (the "when" and "how")

- **Repurpose, don't reinvent.** Every YouTube asset shares its *source audio* with an X task — you
  cut it differently: **X = native audiogram (1:1/16:9)**, **YouTube Short = 9:16 vertical, hook in
  the first 2 seconds, big captions.** Make both from one segment WAV.
- **Shorts cadence:** 1–2/week is ideal for YouTube discovery; solo-realistic is **~1/week**, drawn
  from the same C-task that fed the X post. Shorts compound — even one a week builds reach.
- **The first 2 seconds decide everything** on a Short: open on the hook (a voice line or the
  on-screen question), never a slow logo intro.
- **The stream goes *live* at C7 but stays quiet until C9.** Run it unlisted/low-key during the
  soak; announce it (MY6) only after 7 clean days.
- **Every public video carries the AI disclosure in its description** (C3) — non-negotiable.

## Asset conventions

- **Brand still** — the night-field + beacon + wordmark, the *same* visual as the live stream, so
  Shorts and stream feel like one channel. 9:16 and 16:9 versions.
- **Short (9:16, ≤60s):** brand still or subtle motion bg + waveform + **burned-in captions** +
  a **hook caption** on frame 1. Title overlay optional.
- **Thumbnail (16:9, 1280×720):** readable at phone size — the wordmark + 3–4 huge words. One
  template, recolored per video.
- **Banner (2560×1440, safe area 1546×423):** wordmark + "AI sci-fi radio · live from 2626 · 24/7".

---

## The tasks

### MY0 — Channel foundation
**Depends on:** nothing — **do now** (and enable live streaming, see the ⚠️ box).
**Goal:** a channel that explains itself in one glance and is technically ready to stream.
**Assets:** avatar (beacon mark, 800×800), banner, a default thumbnail template.
**Do — set these:**
- **Handle / name:** `@settlementradio` / `Settlement Radio`
- **Description (About):**
  > Settlement Radio is a 24/7 AI science-fiction radio station broadcasting from the year 2626 — 600 years ahead of now. Two synthetic DJs, Vell and Wren, host an original future world, with every word written by Claude and the whole station built by Claude Code.
  >
  > A love letter to 20th-century science fiction — the golden-age and new-wave authors who imagined the future. An original world, broadcasting from inside it. This channel is AI-generated fiction, voiced with AI.
  >
  > 🌐 settlementradio.com
- **Links:** website (settlementradio.com), X. (Add Ko-fi at MY6, not before.)
- **Confirm:** "Made for kids?" = **No** (set at channel + video level); live streaming enabled.
**Done-when:** handle, name, avatar, banner, about, and links are set; live streaming shows as
enabled (or pending the 24h activation).
**Result check:** n/a — confirm it reads clearly on mobile.

### MY1 — Channel trailer (the "what is this" for non-subscribers)
**Depends on:** **C1** (needs a clean, continuity-passing clip).
**Goal:** a 30–60s loop that hooks a first-time visitor and explains the premise.
**Asset:** a 30–60s branded video: 2–3 lines of real DJ audio over the brand still, captioned, with
a one-line premise card at the end.
**Title:** `Settlement Radio — live from the year 2626 🛰️`
**Description:**
> A 24/7 AI sci-fi radio station broadcasting 600 years in the future. Two synthetic DJs, an original world, every word written by Claude — built entirely by Claude Code.
>
> This is AI-generated fiction, voiced with AI. 🌐 settlementradio.com
**Done-when:** uploaded and set as the **channel trailer** (Customization → Layout → "Video
spotlight" for non-subscribers).
**Result check (1wk):** trailer view count + the subscribe-conversion on the channel page.

### MY2 — Short: the first conversation
**Depends on:** **C1.** Shares source audio with X task **MX2**.
**Audience:** discovery (cold viewers). **Goal:** the personality hook, vertical, for reach.
**Asset:** 9:16, ≤45s, the best slice of the Vell↔Wren exchange, big captions.
**Frame-1 hook caption:** `Two AI DJs, talking to each other. In the year 2626.`
**Title:** `Two AI radio DJs have a real conversation 🛰️ #scifi #ai`
**Description:**
> Vell and Wren host Settlement Radio — a 24/7 AI sci-fi station broadcasting from 2626. Every word written by Claude, built by Claude Code. AI-generated fiction. Full station: settlementradio.com
**Done-when:** published as a Short.
**Result check (72h):** **views + average view duration** (did they watch past 2s?) + any subs from
it. This is your benchmark Short — log it.

### MY3 — Short: it knows what year it is
**Depends on:** **C1.** Shares the idea with X task **MX4**.
**Goal:** lead with the single most distinctive concept — the most "wait, what?" hook for cold reach.
**Asset:** 9:16, ≤40s — a line aging "in five days" → "tonight" → "yesterday," or text-animated.
**Frame-1 hook caption:** `This radio station is living 600 years in the future. In real time.`
**Title:** `An AI station that actually knows what day it is — in 2626 #scifi #ai`
**Description:** (same boilerplate as MY2)
**Done-when:** published.
**Result check (72h):** views + shares (this is the most shareable concept — watch for it
outperforming MY2).

### MY4 — Short: meet the voices
**Depends on:** **C6** (the chosen launch voice). Shares source with X task **MX9**.
**Goal:** humanize Vell + Wren right before launch.
**Asset:** 9:16, ≤45s — the Vell→Wren handover (night into first light) in the launch voice.
**Frame-1 hook caption:** `Meet the two voices of a station from the future.`
**Title:** `Night shift to first light — the voices of Settlement Radio 🎧`
**Description:** (boilerplate)
**Done-when:** published.
**Result check (72h):** view duration vs. MY2 benchmark — voice attachment should lift it.

### MY5 — Build & configure the 24/7 live stream (private dry run)
**Depends on:** **C7** (the RTMP relay exists) + **C3** (disclosure copy ready).
**Goal:** a persistent, correctly-configured live broadcast — running, but **not announced**, during
the soak.
**Asset:** the live brand visual (beacon/wordmark on night field, the C7 deliverable); a thumbnail.
**Do — create a persistent live stream and set:**
- **Title:** `Settlement Radio 🛰️ AI Sci-Fi Radio · Live from 2626 · 24/7`
- **Description:**
  > 🛰️ Settlement Radio — live 24/7 from the year 2626.
  > Two AI DJs, Vell (night) and Wren (first light), hosting an original future world. Every word written by Claude; the station built entirely by Claude Code.
  >
  > ⚠️ AI-generated fiction, voiced with AI.
  > 🌐 settlementradio.com
  > 🐦 Updates: [X LINK]
  >
  > A love letter to 20th-century science fiction — broadcasting from the future it imagined.
- **Category:** Music (or Science & Technology); **latency:** Normal; **Made for kids:** No;
  **DVR/recording:** on.
- Keep it **unlisted** (or quietly public, un-announced) through the C9 soak.
**Done-when:** the stream runs continuously from the VPS with the brand visual, correct title +
disclosed description, and survives the soak unannounced.
**Result check:** during the soak, confirm zero stream drops, no dead air on the YouTube side, and
the disclosure is visible in the description.

### MY6 — Go public: the live stream + first clips (soft launch)
**Depends on:** **C9** (soak passed). **This is milestone M1**, coordinated with X **MX10** and the
Ko-fi go-live.
**Goal:** open the doors — quietly, to your warmed audience.
**Do:**
- Flip the stream **public**, feature it on the channel, pin a welcome comment with the disclosure +
  links (now including **Ko-fi**).
- Publish a **first live clip/Short** cut from the actual live broadcast.
- Keep it soft — no Show HN, no big push (that's Phase D / M4).
**Welcome-comment copy:**
> Welcome to Settlement Radio — live 24/7 from the year 2626. AI-generated fiction, every word by Claude, built by Claude Code. 🌐 settlementradio.com · ✦ Support: [KO-FI LINK]
**Done-when:** stream is public + featured, the welcome comment is pinned, the first live clip is up.
**Result check (1wk):** **concurrent live viewers**, watch time, **returning viewers** (the
north-star signal — pairs with Plausible on the site), subs. Log the launch-week baseline; M3
(retention) is measured against it.

### MY7 — "How it's made" (short explainer)
**Depends on:** **C9** / soft-launch window (CM).
**Audience:** the curious + dev-adjacent. **Goal:** tell the agentic-build story in long-ish form —
the *short* version; the full hero case study is Phase D / M4.
**Asset:** a 3–5 min video — screen + voiceover (or captions): the premise, the world clock, the
writers' room, the safety gate, "built entirely by Claude Code." Reuse the X threads MX3/MX4/MX7 as
the script spine.
**Title:** `I had Claude Code build a 24/7 AI radio station from the year 2626`
**Description:** premise + the four-channel links + disclosure + "built with Claude Code."
**Done-when:** published, linked from the channel + the live stream description.
**Result check (2wk):** average view duration (the retention curve tells you which part lands) +
subs + any reshare into dev circles.

---

## Dependency map (YouTube → Phase C)

| Task | Depends on | Type | Public? |
|------|-----------|------|---------|
| MY0 Channel foundation | — (now) + enable live | setup | — |
| MY1 Channel trailer | **C1** | video | public |
| MY2 Short: conversation | **C1** | Short | public |
| MY3 Short: knows the year | **C1** | Short | public |
| MY4 Short: the voices | **C6** | Short | public |
| MY5 Live stream config | **C7** (+C3) | live setup | unlisted (soak) |
| MY6 Go public (M1) | **C9** | live + clip | **public** |
| MY7 "How it's made" | **C9** / CM | long video | public |

## Running metrics log

North star: **returning viewers + watch time.** Cumulative goal by MY6: the channel is set, a small
Shorts library is live, and the stream is running clean — somewhere for launch discovery to land.

| Task | Date | Views | Avg view duration | New subs | Shares | Notes |
|------|------|-------|-------------------|----------|--------|-------|
| MY2 | | | | | | benchmark Short |
| … | | | | | | |

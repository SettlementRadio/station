# marketing/site.md — how settlementradio.com evolves with time

The **product/marketing spec for the website** at each stage of the build. Strategy:
`docs/MARKETING.md`. Sequence: `docs/ROADMAP.md`. Sibling docs: `X.md`, `youtube.md`, `github.md`.

**The site is the only surface you fully own** (X/YouTube/GitHub are rented). It's the `/web` Next.js
app on Vercel — **built by Claude Code**, so these stages are real buildable deltas, not mockups.
This doc says *what the site must achieve for the audience* at each stage and *what tech gates it*;
the **how-to-build** lives in the phase task packs (C8, Phase D console, etc.) — don't duplicate it
here.

**One rule per stage: the site has exactly ONE job at a time.** Don't let a stage do two jobs — a
page that asks for an email *and* a play *and* a donation converts on none of them.

> **Builder note:** `web/AGENTS.md` warns this Next.js has breaking changes — read
> `node_modules/next/dist/docs/` before writing web code.

**In-world year = `real year + 600` → 2626 in 2026.** The current copy says "late 27th century" —
consistent; keep it relative, never hardcode a year.

---

## The current state (Stage 0 — live)

The coming-soon screen is up: night-field, wordmark, tagline *"Late-night radio from the far
future,"* the premise, a **Buttondown email signup**, the AI-disclosure line, and follow links
(X · GitHub · YouTube · Newsletter). **The site's one job today: capture the trickle of interested
people into the email list before launch.** That's the whole point of Stage 0 — don't add to it.

---

## The stages

### MS0 — Instrument it (add analytics)
**Depends on:** nothing — **do now.**
**The job:** start measuring *before* there's traffic, so the **returning-visitor** baseline (the
north-star signal, and the thing M3/retention is judged on) has history by launch.
**Build delta:** add **Plausible** (lightweight, privacy-friendly, no cookie banner) to the app.
Define two goals: `signup` (email captured) and later `listen` (play pressed).
**Done-when:** Plausible is live on every page and the `signup` goal fires on a real submit.
**Result check:** weekly returning-visitor % and referral sources are visible. (Required by M1 at the
latest — earlier just gives more baseline.)

### MS1 — "Nearly on air" (build anticipation)
**Depends on:** **C1** (a clean, continuity-passing clip exists) — aligns with milestone **M0**.
**Audience:** the curious who arrive from your first X/YouTube posts. **The job:** convert that
warmed attention into email signups by proving the station is *real and imminent* — still one job
(email), just a stronger pitch.
**Build delta (small):**
- Update the tagline/body from "broadcasting soon" → a **"nearly on air"** beat with a concrete
  signal of life.
- **Optional, high-leverage:** embed the **30–60s conversation clip** (the MX2/MY2 asset) so a
  visitor can *hear* it before subscribing — the single biggest signup-conversion lever pre-launch.
- Keep the signup as the primary CTA.
**Copy (body):**
> The signal is almost live. Two voices — Vell on the night shift, Wren bringing in first light —
> are already talking across the dark of the year 2626. Leave your signal; we'll tell you the moment
> we're on air.
**Done-when:** the page reads "nearly on air," and (if included) the clip plays inline.
**Result check (2wk):** **signup conversion rate** before vs. after the clip — does hearing it lift
subscribes?

### MS2 — Match the disclosure to the broadcast
**Depends on:** **C3** (the spoken disclosure ident is finalized).
**The job:** the site's disclosure line and the on-air spoken ident must say the **same thing** —
one consistent, honest voice (EU AI Act Art. 50 + the CLAUDE.md rule).
**Build delta (tiny):** align the existing disclosure copy with the final C3 ident wording (e.g.
"Settlement Radio — a work of fiction, voiced with AI").
**Done-when:** the site line matches the spoken/on-player/YouTube-description disclosure verbatim.
**Result check:** the four disclosure surfaces (spoken · player · site · YouTube) are word-identical.

### MS3 — The live player (the big one) — LAUNCH
**Depends on:** **C7** (the stream exists) + **C8** (the player is built) + **C9** (soak passed).
**This is the site half of milestone M1**, coordinated with X **MX10** / YouTube **MY6** / Ko-fi.
**Audience:** first real visitors arriving from the soft launch. **The job changes to exactly one new
thing: press play — and have a reason to come back.** Support is secondary; email stays available.
**Build delta (this is C8 — spec, not build steps):**
- A **play surface**: an `<audio>` player on the Icecast stream *or* the YouTube live embed (the C8
  call). Big, obvious, above the fold.
- The **disclosure line** (MS2) visible on the player.
- **Now-playing if feasible** (which DJ / format) — even a static "On air: the night shift" beats
  nothing; the real now-playing arrives at MS4.
- **Support + follow:** the **Ko-fi** link goes live here (not before — see `kofi.md`), plus the X /
  YouTube / GitHub links.
- Keep the email signup as a secondary CTA; the coming-soon copy can retire.
**Copy (hero):**
> **Settlement Radio — live now from 2626.**
> Two AI DJs, an original world, every word written by Claude. ▶ Listen.
> *A work of fiction, voiced with AI.*
**Done-when:** settlementradio.com plays the live stream, shows the disclosure, and offers
support/follow links — on the existing Vercel app.
**Result check (1wk):** the **`listen` goal** (play-press rate), time-on-page, **returning visitors**
(north star), and Ko-fi click-through. Log the launch-week baseline — M3 is measured against it.

### MS4 — Surface the living world (depth = retention)
**Depends on:** **Phase D** (the world engine + news desk + the read-only status console).
**Audience:** returning + first-time listeners deciding whether to come back. **The job: give a
reason to return** — show that the world is *alive*, not a loop. This is what actually moves the M3
retention needle.
**Build delta (rides on the Phase D status console + now-playing surface):**
- **Real now-playing / program info** — the current show, the DJ, what's on next (from the Phase D
  scheduler).
- **A "what's happening in 2626" element** — a few current in-world headlines/story beats from the
  news desk's story log, so a visitor sees the world *moving*.
- **A supporters page** — the "Powered by" credits + a milestone-framed ask ("fund the next DJ").
**Done-when:** the site shows live program info + a glimpse of the moving world + a supporters page.
**Result check:** **returning-visitor %** trend (does depth lift it?) + time-on-page + Ko-fi
conversion.

### MS5 — Two-way (listener interaction)
**Depends on:** **Phase E** (listener interaction + the control surface).
**Audience:** an engaged returning audience. **The job: let listeners into the world** — the canon's
"letters between worlds," made real.
**Build delta:** a request/dedication/message form that feeds the Phase E inbound pipeline (gated by
the same safety check as everything else) to be read on air in character; surface a "messages we
aired" trace.
**Done-when:** a visitor can send a message that can be aired in character.
**Result check:** submissions per week + the share/return lift from people hearing their own message
on air.

---

## Dependency map (site → phases)

| Stage | Depends on | The site's one job | Status |
|-------|-----------|--------------------|--------|
| Stage 0 coming-soon | — | capture emails | **live** |
| MS0 Analytics | — (now) | start measuring | |
| MS1 "Nearly on air" | **C1 / M0** | stronger email pitch (+ clip) | |
| MS2 Disclosure match | **C3** | one honest voice | |
| MS3 Live player (M1) | **C7+C8+C9** | **press play + return** | |
| MS4 Living world | **Phase D** | a reason to come back | |
| MS5 Two-way | **Phase E** | let listeners in | |

## What to track (the site owns the north star)

The site is where **returning visitors** — the project's north-star metric and M3's gate — is
actually measured (Plausible). Through Stage 1, the conversion metric is **email signups**; from MS3
on, it's the **`listen` goal + returning visitors + Ko-fi click-through**. Re-baseline at each stage
and compare; the only number that ultimately matters is *do people come back*.

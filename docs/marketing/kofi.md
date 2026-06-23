# marketing/kofi.md — the Ko-fi / donations execution playbook

Strategy: `docs/MARKETING.md` (§4 funding, §6 tooling). Sequence: `docs/ROADMAP.md`. Siblings:
`X.md`, `youtube.md`, `github.md`, `site.md`.

## The decision: do you need a Ko-fi page? **Yes — but not yet.**

- **Yes**, because it's the lowest-friction way for a fan to say "I want this to exist" — no
  subscription, no account, works for one-off tips *and* recurring support, low fees, and it gives
  the community a concrete way to participate. Pair it with **GitHub Sponsors** (the dev-native
  surface) so both audiences have a button.
- **Not yet**, because a Donate button with **nothing live to support reads as premature and
  slightly off** — it asks before you've given. **Ko-fi goes live only at the soft launch (C9 / M1),
  alongside the live stream.** Until then there's nothing to fund.
- **Be honest about what it is.** Per `MARKETING.md §4`: the real funding is **credits, not
  donations** (ElevenLabs/AWS/Anthropic grants — see `anthropic.md` + M2). Ko-fi covers the residual
  and, more importantly, **signals community** — it won't fund the project alone. Don't build the
  plan around it.

**Audience:** existing followers and first listeners who already care — *not* a growth channel. The
job is conversion of goodwill, framed in the station's voice.

---

## The tasks

### MK0 — Build the page, keep it dark
**Depends on:** nothing — **do now** (but don't link it anywhere yet).
**Goal:** the page is ready and on-brand so launch day is one switch, not a scramble.
**Do:**
- Create the Ko-fi page; handle **`settlementradio`** (must match the GitHub `FUNDING.yml` and the
  site link).
- Brand it with the **beacon + wordmark** (same as every other surface); night-field feel.
- Write the **About** in the station's voice (not "please donate"):
  > Settlement Radio broadcasts 24/7 from the year 2626 — two AI DJs, an original world, every word
  > written by Claude. It's a love letter to 20th-century science fiction, the authors who imagined
  > the future, broadcasting from inside it. It runs on real compute and real voices; if it keeps you
  > company across the dark, you can help keep the lights on and bring the next DJ on air. 🛰️
- Set up **GitHub Sponsors** in parallel (the dev-native button; wired via `FUNDING.yml` in MG6).
- **Leave it unlinked/quiet** — no buttons anywhere until MK1.
**Done-when:** the page exists, is on-brand, and is *not* yet linked from any channel.
**Result check:** n/a — confirm it looks intentional next to the site/X/YouTube.

### MK1 — Go live at the soft launch
**Depends on:** **C9 / M1** — fires *with* X **MX10**, YouTube **MY6**, site **MS3**.
**Goal:** turn on support the moment there's a living station to support.
**Do — light the buttons everywhere at once:**
- **Site:** the Ko-fi link on the live player (site task MS3).
- **YouTube:** in the pinned welcome comment + channel links (MY6).
- **GitHub:** the Sponsor button via `.github/FUNDING.yml` (MG6).
- **X:** the support line in the launch thread (MX10, post 3).
- A single **"support" launch note** in the station's voice, tied to a concrete milestone.
**Copy (the ask):**
> If Settlement Radio kept you company tonight and you want to hear the world grow — the next DJ, the
> next chunk of 2626 — you can chip in here. Every bit funds real compute and real voices. ☕🛰️
**Done-when:** Ko-fi + Sponsors are linked from all four surfaces and a first ask has gone out.
**Result check (1wk):** click-through from each surface (which one converts?), first supporters,
one-off vs. recurring split. Keep expectations low — *any* support this early is signal, not income.

### MK2 — Milestone-framed asks (ongoing, from M1)
**Depends on:** **M1+** (a live station with milestones to point at).
**Goal:** make support feel like *funding a specific thing*, not charity — the framing that actually
converts.
**Do:**
- Tie asks to concrete, in-voice milestones: **"fund the next DJ," "fund a week of the flagship
  voice," "keep the night shift on."**
- Optionally set a **visible Ko-fi goal** for the next concrete cost (e.g. a month of the launch
  voice / the VPS).
- Add a **"Powered by" supporters credit** on the site supporters page (site task MS4) — name
  supporters (with consent); say *"Powered by,"* never *"Sponsored by."*
- Mention support only when you've *given* first (a new clip, a milestone) — never as a standalone beg.
**Done-when:** at least one milestone-framed ask + the supporters credit exist.
**Result check:** conversion on milestone asks vs. generic ones; recurring-supporter count trend.

---

## Dependency map

| Task | Depends on | Job |
|------|-----------|-----|
| MK0 Build page, keep dark | — (now) | ready, on-brand, unlinked |
| MK1 Go live | **C9 / M1** | light all buttons at once |
| MK2 Milestone asks | **M1+** | fund a *specific thing* |

## What to track
Click-through per surface, supporter count (one-off vs. recurring), and whether recurring support
trends toward covering running cost. **The honest bar:** donations *signal community* and cover the
residual — the grants/credits in `anthropic.md` + `MARKETING.md §4` are what actually fund the build.

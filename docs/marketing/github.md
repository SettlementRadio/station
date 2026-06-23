# marketing/github.md — the GitHub execution playbook

Concrete tasks for the public **GitHub org** and the **station repo**. Strategy: `docs/MARKETING.md`.
Sequence: `docs/ROADMAP.md`. Sibling docs: `docs/marketing/X.md`, `docs/marketing/youtube.md`.

**GitHub is not a posting channel — it's the credibility anchor and the *featurable artifact*.** X
and YouTube spread the story; GitHub is where a curious dev (or Anthropic devrel) lands to check that
it's *real*. So the job here is mostly **one-time setup done well**, plus two launch-wiring moments.

**Front-load this.** Unlike X/YouTube, most GitHub tasks have **no tech dependency — do them now.**
Your very first X posts say "built in public," and people will click straight to the repo. It must
already look intentional and tell the story before that traffic arrives. Only the *live-demo link*
and the *funding button* wait on later phases.

**The in-world year is `real year + 600` → 2626 in 2026.**

---

## Audience, goal, what "good" looks like

- **Audience:** developers evaluating the project from a tweet / HN / a newsletter — potential
  amplifiers, future contributors, and **Anthropic devrel**. High-signal, allergic to hype.
- **Goal:** a cold visitor **understands what this is, believes it's real, and trusts it within ~30
  seconds** — then stars/shares. The repo is the artifact you eventually put in front of Anthropic
  (M4), so it has to read like a serious, finished thing, not a sketch.
- **North star here:** not stars-as-vanity but *comprehension + trust on first scroll*. Track unique
  visitors/clones (Insights → Traffic) and referral sources as the real signal.
- **IP safety on the most public code on the internet:** the README and LICENSE must make the
  *tribute / original-world* boundary explicit. This is where the IP line is most scrutinized.

---

## The tasks

### MG0 — Org visual identity
**Depends on:** nothing — **do now.**
**Goal:** the org page looks like a real outfit, not a personal scratch account.
**Assets:** org avatar = the beacon mark (same as X/YouTube avatar, square); a profile banner image.
**Do — set on the org:**
- **Display name:** `Settlement Radio`
- **Avatar:** the beacon mark (consistent across all platforms).
- **Description:** `A 24/7 AI sci-fi radio station broadcasting from 2626. Built entirely by Claude Code.`
- **URL:** `https://settlementradio.com`
- **Verify the domain** (Org → Settings → Verified domains) so the org shows the ✓ verified badge —
  cheap, strong credibility signal.
- **Email:** the project mailbox (`hello@settlementradio.com`), public.
**Done-when:** name, avatar, description, verified domain, and URL are all set.
**Result check:** n/a — confirm the org page reads clearly to a stranger.

### MG1 — Org profile README (the org landing page)
**Depends on:** nothing — **do now** (live link added later at MG6).
**Goal:** the org page itself tells the story — most visitors hit the org before any single repo.
**How:** create a repo named **`.github`** in the org with **`profile/README.md`** — GitHub renders
it on the org page.
**Asset:** a banner image (the brand wordmark on the night field), committed into the repo.
**Content to commit (`profile/README.md`):**
```markdown
<div align="center">
  <img src="profile/banner.png" alt="Settlement Radio" width="100%" />

  # Settlement Radio
  **An AI sci-fi radio station broadcasting from the year 2626 — 600 years ahead of now.**

  Two synthetic DJs. An original future world. Every word written by Claude;
  the whole station built by Claude Code.

  <!-- add at MG6: [▶ Listen live](LINK) · -->
  [settlementradio.com](https://settlementradio.com) · [X](LINK)
</div>

A love letter to 20th-century science fiction — the golden-age and new-wave authors who
imagined the future. We honor their *spirit*, never their work: an original world, no
franchise, no borrowed IP.

### What's here
- **[station](../station)** — the Python pipeline: the writers' room, the world clock,
  the safety + continuity gates, playout.
- **web** — the Next.js site at settlementradio.com.

> 🤖 AI-generated fiction, voiced with AI.
```
**Done-when:** the org page shows the banner + premise + links.
**Result check:** load the org page logged-out — does a stranger get it instantly?

### MG2 — Station repo: visuals + metadata
**Depends on:** nothing — **do now.**
**Goal:** the repo looks intentional in search results, when shared, and on the org page.
**Asset:** a **social preview image** (1280×640) — wordmark + one-line premise; shown whenever the
repo URL is shared anywhere.
**Do on the repo:**
- **Description:** `AI sci-fi radio from 2626 — synthetic DJs, an original world, built entirely by Claude Code.`
- **Website field:** `https://settlementradio.com`
- **Topics:** `ai`, `claude`, `anthropic`, `generative-ai`, `radio`, `text-to-speech`,
  `science-fiction`, `liquidsoap`, `python`, `agents`.
- **Social preview:** upload the 1280×640 image (Settings → Social preview).
- **Pin** the station + web repos on the org page (Customize pinned).
**Done-when:** description, website, topics, and social preview are set; key repos pinned.
**Result check:** paste the repo URL into X/Slack — does the preview card look sharp?

### MG3 — The README as the story (the artifact's front door)
**Depends on:** nothing for the rewrite — **do now**; the live badge slots in at MG6.
**Goal:** the README answers *what / why / is it real / how do I run it* without endless scrolling —
this is the page Anthropic devrel will actually read.
**Asset:** a README header image (reuse the social-preview art) + status badges.
**Do — structure the README top as:**
```markdown
<div align="center">
  <img src=".github/header.png" alt="Settlement Radio" width="100%" />

  # Settlement Radio

  **A 24/7 AI sci-fi radio station broadcasting from the year 2626.**
  Synthetic DJs · an original world · every word written by Claude · built entirely by Claude Code.

  *A love letter to 20th-century science fiction — broadcasting from the future it imagined.*

  <!-- add at MG6: [![Live](badge)](LINK) -->
  ![License](https://img.shields.io/badge/code-MIT-blue)
  ![World](https://img.shields.io/badge/world-CC%20BY%204.0-green)
  ![Built with Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-d97757)
</div>
```
Then, in order: **What it is** (the premise + the two hooks) → **How it works** (a 5-line tour: the
world clock, the writers' room, the safety + continuity gates, playout) → **Run it locally** (the
existing setup steps) → **The world** (link CANON) → **Disclosure** (AI-generated fiction) →
**License** (link MG4). Keep the agentic-build story *up top* — it's the differentiator.
**Done-when:** the README leads with the story + badges and a stranger can follow it to a running
station.
**Result check:** hand the README to someone who's never seen the project — can they explain it back?

### MG4 — Licensing clarity (code vs. world)
**Depends on:** nothing — **do now** (the repo is already public; this protects the IP boundary).
**Goal:** make the tribute / original-world boundary legally explicit and signal seriousness.
**Do:**
- **Code:** `LICENSE` = **MIT** (simple, expected for indie dev tooling).
- **The written world (docs/CANON + generated lore):** **CC BY 4.0**, stated in a `LICENSE-CONTENT`
  or a README "License" section — it's an *original* world offered as tribute. *(Community-contributed
  worldbuilding later moves to **CC BY-SA** — Phase F; see `docs/MARKETING.md` §4. Don't add that
  agreement until it triggers.)*
- One README line: *"Code is MIT. The world (canon and generated lore) is original and licensed
  CC BY 4.0 — a tribute to the genre, not derived from any franchise or author's work."*
**Done-when:** `LICENSE` exists and the README states the code/world split.
**Result check:** the IP boundary is unambiguous to a lawyer-brained reader.

### MG5 — Community health + discoverability
**Depends on:** nothing — **do now.** Keep it light.
**Goal:** the repo looks maintained and is findable, without inviting work you can't handle solo.
**Do:**
- `CONTRIBUTING.md` — short and honest: *"Settlement Radio is built in public but not yet taking
  external code contributions; follow along on [X]. Issues/ideas welcome."*
- `CODE_OF_CONDUCT.md` — the GitHub default template (one click).
- Confirm topics (MG2) and the README are doing the discoverability work; no wiki/Discussions needed
  yet.
**Done-when:** the two community files exist; the repo's "community profile" looks complete.
**Result check:** the repo doesn't read as abandoned or as begging for PRs.

### MG6 — Wire the live demo + funding (launch)
**Depends on:** **C9** (soak passed) → milestone **M1**, coordinated with X **MX10** / YouTube
**MY6**.
**Goal:** turn the repo from "a build" into "a live thing you can listen to and support."
**Do:**
- Add the **▶ Listen live** badge/link (YouTube + settlementradio.com) to the README **and** the org
  profile README (the placeholders left in MG1/MG3).
- Add **`.github/FUNDING.yml`** so the Sponsor button appears:
  ```yaml
  ko_fi: settlementradio
  github: [settlementradio]
  ```
- Tag a **release** (e.g. `v1.0-soft-launch`) with a short note — a public milestone marker and a
  clean point to link.
**Done-when:** the live link is in both READMEs, the Sponsor button shows, and the release is tagged.
**Result check (1wk):** repo **traffic + referral sources** (Insights → Traffic) around launch —
where are clicks coming from? Stars are a secondary signal.

### MG7 — Anthropic Cookbook PR *(forward pointer — Phase D / M4)*
**Depends on:** **DM / M4** — *not* this phase. The one concrete *direct* door to Anthropic: a
genuinely useful guide (the multi-agent writers'-room with the Agent SDK) contributed to the
**Anthropic Cookbook**. Full treatment lives in the **Anthropic-outreach** doc (Q6), since it's
about *how you approach the big guys*, not org hygiene. Listed here only so the dependency is visible.

---

## Dependency map (GitHub → phases)

| Task | Depends on | Type |
|------|-----------|------|
| MG0 Org identity | — (now) | visual/setup |
| MG1 Org profile README | — (now) | visual/content |
| MG2 Repo visuals + metadata | — (now) | visual/setup |
| MG3 README as story | — (now) | content |
| MG4 Licensing | — (now) | legal/IP |
| MG5 Community health | — (now) | hygiene |
| MG6 Live link + funding | **C9 / M1** | launch wiring |
| MG7 Cookbook PR | **DM / M4** | → Anthropic doc |

## What to track

Not stars (vanity). Track, in **Insights → Traffic**: unique visitors, clones, and **referral
sources** (which post/thread sent people). The qualitative bar is the real one: *did a cold visitor
understand and trust the project on the first scroll?* Re-test that after each README change.

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

**Status legend + the real repo facts (validated 2026-06-23):** `✅ READY` = the copy below is checked
against the actual repo; `📝 DRAFT` = waits on a later phase. The ground truth:
- **Org `SettlementRadio`, one repo `station`** at `github.com/SettlementRadio/station` — *already
  pushed and public*. It's a **monorepo** (folders `src/`, `web/`, `docs/`, `assets/`, …), **not**
  several repos — fix any copy that implies multiple.
- **Licenses already in place:** **`LICENSE-CODE` = Apache-2.0**, **`LICENSE-CONTENT` = CC BY-SA 4.0**
  (the world is *already* share-alike). Badges/copy must say Apache-2.0 + CC BY-SA 4.0 (not MIT / CC BY).
- **The `README.md` already exists and is strong** (carries the tribute, a "Built in the open with
  Claude Code" section, the disclosure mechanism, a License section). So MG3 is **polish, not a
  rewrite**.
- **Brand art exists** in `assets/brand/` (png + svg + favicon + tokens) — reuse it for avatar /
  banner / social preview; don't make new marks.
- **Handle/disclosure:** the canonical on-screen disclosure is `DISCLOSURE_LINE` from
  `src/disclosure.py`: *"Settlement Radio is a work of fiction, written and voiced by AI."*

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

### MG0 — Org visual identity · `✅ READY`
**Depends on:** nothing — **do now.** *(Org `SettlementRadio` already exists with repo `station`
pushed — this is dressing it, not creating it.)*
**Goal:** the org page looks like a real outfit, not a personal scratch account.
**Assets:** org avatar = the beacon mark from `assets/brand/` (same as X/YouTube avatar, square); a
profile banner from the same brand kit.
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

### MG1 — Org profile README (the org landing page) · `✅ READY`
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
  **Always-on radio from the human future — the one signal that holds a scattered
  humanity together across the dark between worlds.**

  Six hundred years from now the settled worlds are far apart, and radio is the thread
  between them. Settlement Radio carries the news, the music, and the long nights of a
  whole era — every word written by Claude, the entire station built by Claude Code.

  <!-- add at MG6: [▶ Listen live](LINK) · -->
  [settlementradio.com](https://settlementradio.com) · [X](LINK)
</div>

A love letter to 20th-century science fiction — the golden-age and new-wave authors who
imagined the future. We honor their *spirit*, never their work: an original world, no
franchise, no borrowed IP.

### What's here — one repo, [`station`](https://github.com/SettlementRadio/station)
- **`src/`** — the Python pipeline: the writers' room, the world clock, the safety +
  continuity gates, the scheduler, playout.
- **`web/`** — the Next.js site at settlementradio.com.
- **`docs/`** — the canon, the architecture, and the build log (DEVLOG).

> 🤖 Settlement Radio is a work of fiction, written and voiced by AI.
```
**Done-when:** the org page shows the banner + premise + links.
**Result check:** load the org page logged-out — does a stranger get it instantly?

### MG2 — Station repo: visuals + metadata · `✅ READY`
**Depends on:** nothing — **do now.** *(One repo: `station`.)*
**Goal:** the repo looks intentional in search results, when shared, and on the org page.
**Asset:** a **social preview image** (1280×640) — wordmark + one-line premise; shown whenever the
repo URL is shared anywhere. Build it from `assets/brand/`.
**Do on the `station` repo:**
- **Description:** `AI sci-fi radio from 2626 — synthetic DJs, an original world, built entirely by Claude Code.`
- **Website field:** `https://settlementradio.com`
- **Topics:** `ai`, `claude`, `anthropic`, `generative-ai`, `radio`, `text-to-speech`,
  `science-fiction`, `liquidsoap`, `python`, `agents`.
- **Social preview:** upload the 1280×640 image (Settings → Social preview).
- **Pin** the `station` repo (and the `.github` repo once MG1 creates it) on the org page.
**Done-when:** description, website, topics, and social preview are set; the repo is pinned.
**Result check:** paste the repo URL into X/Slack — does the preview card look sharp?

### MG3 — README polish (NOT a rewrite — it already exists & is strong) · `✅ READY`
**Depends on:** nothing — **do now**; the live badge slots in at MG6.
**Reality:** `README.md` already leads with the wordmark + tagline, the premise, a "Built in the open
with Claude Code" section, the disclosure mechanism, and a License section. It already carries the
tribute. **Don't rewrite it — add three small things and fix one wording drift:**
1. **Status badges** under the title (use the *real* licenses):
   ```markdown
   <!-- add at MG6: [![Live](badge)](LINK) -->
   ![Code: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue)
   ![World: CC BY-SA 4.0](https://img.shields.io/badge/world-CC%20BY--SA%204.0-green)
   ![Built with Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-d97757)
   ```
2. **The motto line** under the tagline (one italic line):
   *A love letter to 20th-century science fiction — broadcasting from the future it imagined.*
3. **Align the disclosure wording:** the README currently says "work of fiction, **generated with
   AI**" — change to the canonical **"a work of fiction, written and voiced by AI"** so README, air,
   site, and YouTube all match (`src/disclosure.py` `DISCLOSURE_LINE`).
**Done-when:** badges + motto line are in, and the disclosure wording matches everywhere.
**Keep the lead world-first.** The repo README already opens the right way ("…always-on radio that
broadcasts from the settled worlds… keeps you company across the dark"), which *is* the core message
(`MARKETING.md` → core message) — don't let any edit regress it into a "two DJs · an AI world" feature
list.
**Result check:** hand the README to someone who's never seen the project — can they explain it back?

### MG4 — Licensing clarity (code vs. world) · `✅ READY — already done, just verify`
**Reality:** the split **already exists in the repo** and is correct — don't recreate it:
- **Code:** `LICENSE-CODE` = **Apache-2.0**.
- **The written world** (canon + generated lore): `LICENSE-CONTENT` = **CC BY-SA 4.0** (already
  share-alike — *not* "CC BY 4.0 now, share-alike later"; the world is share-alike today).
- The README License section already names both.
**Do (just confirm + one tweak):** make sure the README's one-line framing makes the *tribute*
explicit, e.g.: *"Code is Apache-2.0; the world (canon and generated lore) is original and licensed
CC BY-SA 4.0 — a tribute to the genre, not derived from any franchise or author's work."*
**Note — this corrects `docs/MARKETING.md §4` and the ROADMAP Phase-F note**, which still imply the
CC BY-SA agreement is future; it's already in force. (Flag to fix — see summary.)
**Done-when:** the README's license line reads as the tribute/original-world boundary, citing the two
real files.
**Result check:** the IP boundary is unambiguous to a lawyer-brained reader.

### MG5 — Community health + discoverability · `✅ READY`
**Depends on:** nothing — **do now.** Keep it light. *(No `CONTRIBUTING.md`/`CODE_OF_CONDUCT.md` in
the repo yet — these are net-new.)*
**Goal:** the repo looks maintained and is findable, without inviting work you can't handle solo.
**Do:**
- `CONTRIBUTING.md` — short and honest: *"Settlement Radio is built in public but not yet taking
  external code contributions; follow along on [X]. Issues/ideas welcome."*
- `CODE_OF_CONDUCT.md` — the GitHub default template (one click).
- Confirm topics (MG2) and the README are doing the discoverability work; no wiki/Discussions needed
  yet.
**Done-when:** the two community files exist; the repo's "community profile" looks complete.
**Result check:** the repo doesn't read as abandoned or as begging for PRs.

### MG6 — Wire the live demo + funding (launch) · `📝 DRAFT`
**Depends on:** **C9** (soak passed) → milestone **M1**, coordinated with X **MX10** / YouTube
**MY6**. *(Re-validate against the C9 DEVLOG entry; fill the real live link.)*
**Goal:** turn the repo from "a build" into "a live thing you can listen to and support."
**Do:**
- Add the **▶ Listen live** badge/link (YouTube + settlementradio.com) to the README **and** the org
  profile README (the placeholders left in MG1/MG3).
- Add **`.github/FUNDING.yml`** so the Sponsor button appears (org is `SettlementRadio`):
  ```yaml
  ko_fi: settlementradio
  github: [SettlementRadio]
  ```
- Tag a **release** (e.g. `v1.0-soft-launch`) with a short note — a public milestone marker and a
  clean point to link.
**Done-when:** the live link is in both READMEs, the Sponsor button shows, and the release is tagged.
**Result check (1wk):** repo **traffic + referral sources** (Insights → Traffic) around launch —
where are clicks coming from? Stars are a secondary signal.

### MG7 — Anthropic Cookbook PR *(forward pointer — Phase D / M4)* · `📝 DRAFT`
**Depends on:** **DM / M4** — *not* this phase. The one concrete *direct* door to Anthropic: a
genuinely useful guide (the multi-agent writers'-room with the Agent SDK) contributed to the
**Anthropic Cookbook**. Full treatment lives in the **Anthropic-outreach** doc (Q6), since it's
about *how you approach the big guys*, not org hygiene. Listed here only so the dependency is visible.

---

## Dependency map (GitHub → phases)

| Task | Depends on | Status | Type |
|------|-----------|--------|------|
| MG0 Org identity | — (now) | ✅ READY | visual/setup |
| MG1 Org profile README | — (now) | ✅ READY | visual/content |
| MG2 Repo visuals + metadata | — (now) | ✅ READY | visual/setup |
| MG3 README polish | — (now) | ✅ READY | content |
| MG4 Licensing | — (already done) | ✅ READY (verify) | legal/IP |
| MG5 Community health | — (now) | ✅ READY | hygiene |
| MG6 Live link + funding | **C9 / M1** | 📝 DRAFT | launch wiring |
| MG7 Cookbook PR | **DM / M4** | 📝 DRAFT | → Anthropic doc |

## What to track

Not stars (vanity). Track, in **Insights → Traffic**: unique visitors, clones, and **referral
sources** (which post/thread sent people). The qualitative bar is the real one: *did a cold visitor
understand and trust the project on the first scroll?* Re-test that after each README change.

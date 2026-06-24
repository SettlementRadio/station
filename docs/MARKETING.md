# MARKETING.md — Settlement Radio

The **durable playbook**: who we're reaching, with what hooks, through which channels, and the
**validatable milestones** that say when a marketing move is allowed to fire. A build-in-public plan
that runs in lockstep with the tech build.

**The goal isn't "advertising"** — there's no budget and no audience yet. The goal is to *document
the making of something remarkable, let it spread on its own merit, and let Anthropic amplification
and funding follow.*

## How this doc relates to the others (read this, avoid duplication)

- **`docs/ROADMAP.md` owns the *sequence*** — the interleaved build (A–F) and marketing (CM/DM/EM)
  phases, in order, with division of labour. When a date/order question arises, ROADMAP wins.
- **This doc owns the *playbook*** — the principles, hooks, channels, content engine, metrics, the
  funding track, and the milestone acceptance criteria. It does **not** restate the timeline.
- **Phase task packs** (`PHASE_<X>_TASKS.md`) carry only a one-line pointer to the milestone for
  that phase — never a full marketing restatement.
- **`docs/marketing/` owns *execution*** — concrete, copy-paste-ready, per-platform task lists with
  exact post text + assets, each task gated on a Phase C tech task. Start: **`docs/marketing/X.md`**
  (X tasks MX0–MX10). YouTube · GitHub · site · Ko-fi · Anthropic-outreach docs follow the same shape.

If you find marketing strategy duplicated anywhere else, it's a bug — delete it and link here.

---

## The core message — what this is (the foundational say; lead with this)

**Settlement Radio is not "a radio station with AI DJs." It's a living human future you can tune
into — and the radio is the way in.** The mistake to avoid: feature-listing ("two DJs · an AI world ·
built by Claude"), which flattens a whole civilization into a bullet next to its staff count. No real
station sells itself that way. **The world is the product; the radio is your window onto it; the DJs
and the AI are *how*, not *what*.** Three layers, always in this order:

- **WHAT (leads):** Six hundred years from now, humanity is scattered across the settled worlds — and
  Settlement Radio is the **one signal that holds them together**, keeping the dark between worlds
  company with the news, music, and long nights of a living era. *You tune in, and you're there.*
  (Grounded in canon: the relay "always between, which is why it can talk to everyone"; "radio is the
  thread that connects them.")
- **HOW (second):** every word written by Claude, the entire station built and run by Claude Code —
  always-on and time-aware. The novelty/proof, never the headline.
- **WHY (third):** a love letter to 20th-century science fiction — the genre that imagined this future.

**The keystone line (one canonical paragraph — the foundational "what is this," use verbatim):**
> Six hundred years from now, humanity is scattered across the settled worlds — and one signal keeps
> them company across the dark between them. Settlement Radio is that signal: always-on radio from the
> human future, carrying the news, the music, and the long nights of a whole era. Written by Claude.
> Built by Claude Code. A love letter to 20th-century science fiction.

**Short keystone (for bios / tight space):**
> Always-on radio from the human future — the one signal that holds a scattered humanity together
> across the dark between worlds. Written by Claude, built by Claude Code; a love letter to
> 20th-century science fiction.

**The DJs are texture, not a headline.** Vell (night shift) and Wren (first light) are *how the world
speaks to you* — introduce them as the voices that carry the broadcast, after the world-first lead;
never as a co-equal feature ("two synthetic DJs"). They get the spotlight in *progress/character*
content (clips, the voice reveal), not in the foundational say.

## The motto / the WHY (the soul — carry it everywhere too)

We honor the genre's *spirit*, never its IP: an **original** world, broadcasting from 600 years ahead
as if the authors' dream of the future simply kept going.

**The motto (one canonical line — verbatim across every surface):**
> **A love letter to 20th-century science fiction — broadcasting from the future it imagined.**

**Rule:** every foundational premise/bio/About **leads with the core message (WHAT) and carries the
tribute (WHY)** — not just the "built by Claude Code" hook. If a piece of foundational copy reads as a
feature list, or buries the living world, it's not finished. *(Progress posts are exempt — they
legitimately show the mechanics and the DJs.)*

---

## 0. Core principle (read first)

**You do not market *to* Anthropic. You build something the community shares, and Anthropic
notices.** There is no "submit to get featured" portal — featuring happens *downstream* of a project
spreading in the developer/sci-fi world. The one concrete *direct* door is contributing a guide to
the **Anthropic Cookbook** on GitHub. Everything else is earned.

**Two hooks, two audiences — lead with the right one per channel:**
- **Tribute hook** (emotional): "a love letter to 20th-century science fiction — the golden-age and
  new-wave authors who imagined the future — broadcasting from the world they dreamed." → general /
  sci-fi audiences. *(This is the motto above; lead with it on every non-dev surface.)*
- **Built-by-agents hook** (technical): "an entire 600-years-future civilization stood up by Claude
  Code agents, broadcasting live and time-aware." → dev / AI audiences.

**The discipline — reliability *is* marketing.** Don't go loud before the stream is reliable and the
safety gate works. A broken or embarrassing first impression is unrecoverable, and Anthropic will
never amplify anything risky. This is why every launch milestone below is **gated on a tech state**,
not on a calendar.

---

## 1. Channels — the deliberate four

Narrowed on purpose. A wider set (Bluesky, Reddit-as-feed, Tumblr, TikTok, a Discord, Buffer) was
**dropped** — see the appendix. The four we run:

- **YouTube** — the flagship: the 24/7 live stream (the "lofi radio" playbook — calm sci-fi visual,
  endless stream, search/recommendation discovery) **plus** the how-it's-made clips. This is the
  product *and* the marketing.
- **X** — the one active feed: build-in-public, the road to an Anthropic feature. Main process
  channel, dev/AI audience.
- **Ko-fi** — the donation surface (+ GitHub Sponsors alongside). Turned on at soft launch, not
  before.
- **GitHub** — the public repo + README = credibility + the *featurable artifact*; the Cookbook PR.

**Supporting surfaces (not "channels," but load-bearing):**
- **settlementradio.com** (Vercel) — coming-soon now → web player in Phase C. Premise, support
  links, AI-disclosure, metrics instrumentation.
- **Newsletter: Buttondown** (free tier) — the build log / essays / supporter updates.
- **One-time launch megaphones (DM only):** Show HN + *one* sci-fi subreddit, fired once, never
  adopted as ongoing feeds.

---

## 2. The content engine (repeatable units, so solo posting stays sustainable)

- **Progress clips (15–60s):** a DJ voice, a two-DJ exchange, the time-aware moment, a jingle. The
  single highest-leverage unit — let people *hear* the personality. *(Tech reality: these are
  pre-rendered cuts from the buffer until Phase E; nothing interactive/near-live before then.)*
- **"How it works" threads:** one subsystem explained simply (world clock, writers' room,
  RAG-as-memory). Feeds the dev audience.
- **Behind-the-scenes of Claude Code building it:** the agentic-build story, honestly told. The
  differentiator almost no one else has.
- **Lore drops:** a faux 2626 news headline, a DJ backstory. Builds the universe in public; feeds
  the sci-fi audience. *(Richer once the Phase D world engine is live.)*
- **Tribute drops (carry the soul):** short posts that make the *why* legible — the idea or feeling
  from a 20th-century sci-fi classic that a segment echoes, honored in the original world ("tonight's
  show is in the spirit of the generation-ship stories — without ever being one"). Honor the era and
  its themes; **never name a living author's characters or a franchise.** At least one tribute beat
  every couple of weeks, so the project never reads as *only* a tech demo.
- **Milestone announcements:** "the station is live," "DJ #2 joins the night shift."

**Hero pieces (built for the loud launch, DM):**
1. **The demo clip** — the time-aware / concert moment. Make it excellent; it's the thing that
   spreads.
2. **The case study** — the agentic-build writeup. What Anthropic-adjacent channels share.
3. **The tribute essay** — the *why*. The emotional core that makes people root for it.

**Tone:** in-universe where it delights (the station "speaking"); honest behind-the-scenes where it
builds trust (you, the maker). Draft all of it with Claude.

**The content feedstock is `docs/DEVLOG.md` — not a separate list.** The DEVLOG already captures
every milestone, decision, and clip, one entry per session, and its own header names it "the source
material for the case study and 'built in public' posts." So **don't keep a parallel highlights doc**
— mine the DEVLOG. To make postable moments fast to find, each DEVLOG entry that produced something
shareable adds a **`📣 Postable:`** line (a one-liner + the clip/commit); skim or `grep "📣"` when
it's time to post. This doc and the per-platform docs decide *what/when/how* to post; the DEVLOG is
*what happened* (the raw material). Two jobs, one source each — no duplication.

---

## 3. Validatable milestones (binary, tech-gated)

Each milestone is a **checklist of yes/no facts** — no vanity numbers. A milestone is "done" only
when every box is true. Each is **gated on a tech state** so we never go louder than the product can
back up. Phases (CM/DM/EM) map to `docs/ROADMAP.md`.

### M0 — Seed the ground *(NOW — during the Phase C build)*
Quiet build-in-public warming. The trigger already exists: a real two-DJ conversation clip.
- [ ] First real X post fired (the "first real conversation" clip).
- [ ] Build-in-public cadence started (≥1 process post/week).
- [ ] DEVLOG `📣 Postable:` convention in use (the content feedstock — no separate highlights doc).
- [ ] Coming-soon page updated to a "nearly on air" note.
**Tech gate:** the clip must be a continuity-passing segment (not the afternoon-handover bug). No
other gate — this is warming, not launch.

### M1 — Soft launch *(CM — gated by Phase C / C9)*
The "it's alive" moment, quiet, to existing followers only.
- [ ] **C9 soak passed** (7 days unattended, safe, AI-disclosed, never-dead, zero rescues).
- [ ] Spoken + on-player + YouTube-description **AI disclosure** verified live (C3).
- [ ] "It's alive" announcement posted (Station + Maker voice) with the live link.
- [ ] **Ko-fi live** (+ GitHub Sponsors), framed in the station's voice.
- [ ] First YouTube clips/Shorts from the live station published.
- [ ] **Plausible installed** on the web player (so returning-listener tracking starts on day one).
**Tech gate:** *Do not fire M1 before C9 passes.* A 24/7 stream that stalls or says something unsafe
in week one is the one first impression you can't redo. Keep it a *soft* launch — the loud one is M4.

### M2 — Funding submitted & secured *(CM → DM — see §4)*
Funding, not donations, is the real ceiling (ElevenLabs free tier ≈ ~2 full segments/month).
- [ ] **ElevenLabs Startup Grant** application submitted.
- [ ] **AWS Activate** application submitted.
- [ ] **Anthropic self-serve / promo credits** applied for.
- [ ] ≥1 of the above **approved** (or the launch voice otherwise funded).
**Tech gate:** if C6 chooses ElevenLabs as the public voice, **pull the ElevenLabs grant forward
into Phase C** — the launch voice must be funded *before* M1, not after.

### M3 — Retention proven *(the gate that unlocks the loud launch)*
The loud launch is wasted if the station doesn't hold people. Prove retention first.
- [ ] A **returning-listener signal** is present (Plausible returning visitors and/or YouTube
      returning viewers) across **2+ consecutive weeks**.
- [ ] At least one organic, unprompted share/mention exists (someone other than you posted it).
**Tech gate:** requires the Phase D depth work (living world, news desk, sound design) to be far
enough that a first-time visitor hears a reason to come back tomorrow. Don't fake this box.

### M4 — Loud launch + sponsorship *(DM — THE COMMERCIAL GOAL)*
One coordinated 48-hour push. Fire only after M3 is true.
- [ ] Hero **demo clip** recorded/approved.
- [ ] **Case study** + **tribute essay** published.
- [ ] Coordinated push fired: Show HN + one sci-fi subreddit (staggered, not simultaneous) + the
      clip on all four channels + the essay/case study.
- [ ] Present and responsive in **every thread** for the full 48h.
- [ ] After visible traction: **Anthropic devrel note** sent (artifact-first, ask-last).
- [ ] **Cookbook PR** opened (the multi-agent writers'-room guide).
- [ ] The station **retained** the spike (returning-listener signal did not collapse post-launch).
**Tech gate:** near-live/interactive content is *not* available yet (Phase E) — the launch sells the
pre-rendered station honestly; don't promise live reaction it can't do.

### M5 — Sustain & grow *(EM)*
Convert the spike into a durable, supported audience.
- [ ] Weekly rhythm held for **4+ consecutive weeks** (≈3 X posts + 1 YouTube clip/week, drawn from
      the devlog).
- [ ] Recurring support (Ko-fi/Sponsors + credits) covers the running cost.
- [ ] Anthropic relationship moving from a one-off feature toward an ongoing conversation.
**Tech gate:** the Phase E control surface + listener-interaction features make sustaining cheap;
near-live (Phase E) is the lever if a second channel is ever justified.

---

## 4. Funding & grants (the real funding layer)

The honest hierarchy: **credits > donations.** Donations cover the residual and signal community;
they won't fund the project alone.

- **Apply once there's a live public demo** (M1 is enough proof) — except the **ElevenLabs Startup
  Grant**, pulled forward into Phase C if it's the launch voice (see M2 gate).
- **Targets:** ElevenLabs Startup Grant · AWS Activate · Anthropic self-serve/promo credits.
- **Donations:** Ko-fi + GitHub Sponsors at M1; frame asks in the station's voice, tied to concrete
  milestones ("fund the next DJ"); keep a supporters page and a "Powered by" (not "Sponsored by")
  credit line.
- **Community-contribution licensing:** the world is **already licensed CC BY-SA 4.0** (the repo's
  `LICENSE-CONTENT`); code is **Apache-2.0** (`LICENSE-CODE`). Phase F just *opens inbound*
  contributions under that existing share-alike license — no new agreement to invent.

**Application status** (keep current here, so M2's boxes are auditable):

| Grant / credit | Status | Date | Notes |
|---|---|---|---|
| ElevenLabs Startup Grant | not started | | pull forward to Phase C if it's the launch voice |
| AWS Activate | not started | | |
| Anthropic self-serve / promo credits | not started | | live demo (M1) = enough proof |

---

## 5. Metrics & cadence

**North star: returning listeners** — does the station give people a reason to come back? Not
one-time reach.

- **Instrumentation:** native platform analytics (YouTube, X) + **Plausible** on the web player for
  *returning* visitors. Plausible goes in at M1 so the returning-listener signal (M3's gate) has
  history.
- **Track:** returning listeners/viewers (primary), then YouTube subs + concurrents, newsletter
  signups, GitHub stars, Ko-fi/Sponsors, launch-day traffic — as *signals*, not gates.
- **Sustainable solo rhythm:** ~3 short posts/week + 1 longer piece/week + 1 stream-visible
  improvement/week. **Reality check:** during heavy build phases (C, D) protect the build — drop to
  ~1 post/week mined from the DEVLOG rather than stalling code. Cadence serves the build, not vice
  versa.

---

## 6. Content tooling stack (free-tier first)

- **Channels:** YouTube · X · Ko-fi · GitHub · settlementradio.com (Vercel).
- **Clips/audiograms:** a simple audio-to-shareable-video tool; the YouTube stream visual itself.
- **Graphics:** **Canva** (free) for thumbnails and lore graphics.
- **Newsletter:** **Buttondown** (free tier).
- **Analytics:** native + **Plausible** (track *returning*, not vanity reach).
- **Drafting:** **Claude** — posts, threads, the essay, the case study, subreddit-appropriate
  framing, grant answers.

---

## 7. What to avoid

- **Going loud before C9 passes and the safety gate works.** First impressions are one-shot; a bad
  one is unrecoverable and kills any chance of Anthropic amplification.
- **Spamming communities / leading with "AI project."** Lead with the *story*; earn the link.
- **Over-promising near-live** (Phase E) before it exists. Show what's real.
- **Burning the loud launch early** — fire M4 only after M3 proves retention.
- **Crossing the IP line in public** — frame everything as *tribute* (spirit, original world), never
  named characters or franchises. Public posts are where this risk is most visible.

---

## Appendix — deliberately NOT doing (background, not a to-do list)

These were considered and **dropped** to keep a solo build sustainable. Recorded so they're not
re-litigated:
- **Bluesky, Reddit-as-ongoing-feed, Tumblr, TikTok/Reels, a Discord server** — extra channels to
  feed; the four-channel focus beats spreading thin. (Reddit/Show HN return *once*, as one-time
  launch megaphones at M4 — not as ongoing presences.)
- **Paid social schedulers (Buffer, etc.)** — overkill for one active feed; batch from the DEVLOG
  instead.
- **The concentric-circles / give-to-get community-cultivation playbook** — still the right instinct
  (contribute value, don't drop links; win one circle, let it carry you to the next), but applied
  through the four channels above, not a sprawling community presence.

# DEVLOG — Settlement Radio

The written record of decisions and changes, one entry per working session. The screen
recordings show *how*; this log captures *what changed and why* — the part video can't make
searchable, and the source material for the case study and "built in public" posts later.

## How to use this

- **One entry per session**, newest on top. Keep it fast (5 minutes) or it won't survive.
- Tie each entry to its evidence: the commit(s) for that session and the clip filename(s) in
  `devlog/`. The trio — entry + commit + clip — is one session's complete record.
- Once code exists, "Changed" overlaps with git commits; that's fine. The log's real value is
  **Decisions** and **Why**, which commits don't capture.
- When you write the case study, read this bottom-up (oldest first) — it's the story arc.

**Entry template (copy this):**

```
## YYYY-MM-DD — [Phase] — <one-line focus>
**Focus:** what this session was about, in a sentence.
**Decisions:** the durable choices (the things that matter in three months).
**Changed:** files/commits/accounts that concretely changed.
**Why:** the one or two reasons behind the key decision (your future self will thank you).
**Next:** the single next action.
Commit: <hash>  ·  Clips: <filenames in devlog/>
```

A typical *build* session will be short, e.g.:
> `## 2026-07-02 — Phase A — T3 script generation working`
> Focus: got Claude writing Vell's segment from canon. Decisions: cache the whole canon as one
> breakpoint. Changed: src/writer.py, README. Why: keeps input cost ~0.1x. Next: T4 (render to
> audio). Commit: a1b2c3 · Clips: 2026-07-02-first-script.mov

---

## 2026-06-13 — Phase 0 (planning) — Project shape, name, and the full doc pack settled

**Focus:** turned a broad idea into a decided plan — architecture, funding angle, name, and the
document set that drives the build — before touching Claude Code.

**Decisions (the durable ones):**
- **Architecture = hybrid, no hardware bought.** Cheap always-on CPU VPS (Hetzner CX22, ~€4/mo)
  for 24/7 playout; generation via on-demand/serverless GPU or APIs; YouTube Live as the free,
  unlimited-listener relay. Chosen over buying a Mac Mini.
- **Anthropic angle = "powered by Claude," honestly framed.** Anthropic supplies all
  intelligence + the whole build (Claude Code); voice is the one external piece (no Anthropic
  TTS exists). Realistic Anthropic support is *being featured*, not big credits (those need
  institutional equity funding); fund usage via small self-serve credits + Claude on AWS/GCP
  credits. So the MVP's job is to be **featurable**.
- **MVP scope:** 2 DJs, 1 show, 3 formats, small real canon, batch-only generation + one 60-sec
  near-live demo, content-safety gate + AI disclosure, built by Claude Code and documented in
  public. Everything bigger is explicitly deferred.
- **Name = Settlement Radio.** Verified clean at the brand/trademark level (no station, podcast,
  or media brand uses it). Worldbuilding justification: "settlement" is a *linguistic fossil* —
  the worlds are mature city-planets but still called the settlements out of six-century habit.
- **In-world year = real year + 600, computed at generation time** — never hardcoded (so it
  never goes stale).
- **Model routing:** Sonnet 4.6 default writing brain; Haiku 4.5 for high-volume/near-live;
  Opus 4.8 for rare hard reasoning; Fable/Mythos not workhorses. **Batch API + prompt caching
  mandatory** — text cost stays near-trivial; TTS is the real cost driver.
- **Voice:** ElevenLabs free tier now, behind the TTS abstraction, swappable to Kokoro/Orpheus.
- **Two load-bearing seams:** provider abstraction (swap model/voice/local↔cloud) and the
  Segment abstraction (segment length + lead-time as parameters → batch and near-live share one
  path).
- **Infra identity:** create a GitHub **org** `settlementradio` (org name is the scarce asset),
  repo lives inside. Buy the **domain first**; use Cloudflare free Email Routing to forward a
  branded address into a dedicated project inbox; register *all* project accounts to that, not
  personal email.
- **Habit:** devlog + screen recordings from Phase 0 (Cmd+Shift+5 now, asciinema for terminal
  sessions, OBS later — it doubles as the Phase C streaming tool).

**Changed (documents produced/updated this session):**
- Created the four-file Claude Code pack: `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/CANON.md`,
  `docs/PHASE_A_TASKS.md`.
- Created `docs/ROADMAP.md` (the single who-does-what-when path: Phase 0 → A → B → C → D →
  Beyond).
- Created the strategy set: funding & licensing kit, the Anthropic-anchored build plan, the
  marketing strategy.
- Updated docs with: the Settlement Radio name, the floating-year fix, the "linguistic fossil"
  canon note, and the model-routing + batch/caching rules (in CLAUDE.md, ARCHITECTURE.md, and
  PHASE_A_TASKS.md).

**Why (the key reasons):**
- Hybrid over hardware: near-zero up-front cost, fits €0–40/mo, and credits subsidize cloud/API
  but never a hardware purchase.
- Settlement Radio over prettier names: the cozy-audio namespace is crowded, so plain + verified
  beats evocative + taken; it also ties to the canon's "settlement time."
- Just-in-time task packs: only Phase A is detailed on purpose; B–D get written when reached, so
  they're informed by what Phase A actually teaches.

**Next:** execute Phase 0 — buy the domain (everything hangs off it), set up the forwarding
inbox, claim handles + the GitHub org, install Claude Code, get Anthropic + ElevenLabs API keys,
stand up the coming-soon page, start recording. Then in Claude Code: create the repo in the org,
upload the four-file pack, run `PHASE_A_TASKS.md` from T0.
Commit: (pre-repo; docs created in planning chat) · Clips: (none yet — start with Phase 0)

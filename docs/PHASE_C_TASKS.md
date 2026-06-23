# PHASE_C_TASKS.md — "The Body" (safe · continuous · public)

Work in order, one at a time: implement → show + how to verify → stop for review. Respect
`CLAUDE.md` (seams, model routing, cost levers, engineering standards, hard rules). Written against
the **as-built Phase B code** (see `docs/PHASE_B_ORIENTATION.md`): the real signatures are
`safety_check()`, `conversation.compose_segment(...)` + `continuity_check()` → `ContinuityResult`,
`make_format_segment(...)`, `build_buffer(...)` + the manifest, `settings.*`, and `store` (DB via
`settings.database_url`).

**Why this order — harden, then deploy, then expose, then soak.** The orientation's open risks are
not polish; several are hard prerequisites to *any* public broadcast. C0–C4 make generation safe and
continuous; C5–C8 put it on a server and in front of people; C9 proves it survives unattended. Do
not expose the stream (C7/C8) before the gates and fallback (C0–C4) exist.

**Definition of done for Phase C:** 7 days of uninterrupted, safe, AI-disclosed, never-dead 24/7
broadcasting on the VPS + YouTube, with zero manual rescues — then a soft launch (see Marketing).

---

## C0 — Make the gates real (safety + continuity) — HARD PREREQUISITE
**Goal:** nothing unsafe or self-contradictory ever reaches air.
**Do:**
- Implement `writer.safety_check()` as a real automated check on generated text (profanity / unsafe
  content) used by every producer (writer, news, music, conversation). Likely shape: a fast
  keyword/profanity filter plus an LLM safety pass on the `haiku` tier (cheap). On a flag: regenerate
  once, then refuse (fall back to an evergreen segment) — never air flagged text. (Same gate later
  guards Layer 0 listener inbound in Phase E.)
- Promote continuity from advisory to a **gate**: in `compose_segment`, when `continuity_ok=False`,
  regenerate with the editor's note fed back (bounded: `settings.continuity_max_attempts`, e.g. 2);
  if still failing, drop to an evergreen fallback and log loudly. A flagged draft must NOT be
  written to the buffer.
**Done when:** a deliberately bad draft is blocked + regenerated or replaced by fallback; nothing
with `continuity_ok=False` or a safety flag lands in `segments/` or the manifest.
**Note — land C1 alongside C0.** Most continuity flags today come from the time-framing bug C1 fixes
(the night→dawn handover landing in the afternoon). If the gate goes live before C1, it will thrash
regenerating a bug C1 simply removes — do them together.

## C1 — Time-aware show framing (fix the afternoon-handover bug)
**Goal:** the room frames segments for the actual hour, not a hard-coded night→first-light handover.
**Do:** the `showrunner()` step picks the DJ pairing and framing from `clock` — Vell solo / Vell→Wren
handover only near dawn; Wren or appropriate framing in daylight hours; etc. Drive it from the
in-world wall clock, not a constant.
**Done when:** generating talk segments at several times of day yields hour-appropriate framing and
continuity stops flagging time collisions across a full simulated day.

## C2 — Honest length accounting + a real scheduler
**Goal:** replace the one-shot `build_buffer` with a scheduler that knows what airs when, using
*real* durations.
**Do:**
- After every render, measure actual audio duration (ffprobe) and record `actual_duration_sec` on
  the Segment + manifest. Stop trusting `length_target_sec` for timing. (Optionally raise the B5
  format word counts so audio ≈ target; either way, schedule on measured duration.)
- Build the scheduler (Layer 5): maintain a rolling buffer to a configurable depth
  (`settings.buffer_depth_hours` — the dial that later enables near-live), decide the airing order,
  regenerate on failure, and keep enough lead so the stream never runs dry. A periodic top-up job
  keeps the buffer at depth (the "nightly batch" of C5 is this job — it need not be literally
  once-a-night).
- **Wire playout to the schedule.** Today `radio.liq` just loops the newest file in `segments/`; make
  Liquidsoap air the scheduler's *ordered* output instead (a playlist/queue it re-reads, or the
  request protocol), so the scheduler's decisions actually drive what airs. This Layer 5 ↔ playout
  seam is what turns "a folder of clips" into "a programmed station."
**Done when:** the scheduler maintains a rolling buffer with accurate airtime accounting; buffer
depth is a settings dial; Liquidsoap airs segments in the scheduled order; a failed slot is
regenerated or skipped without dead air.
**Note — the `music` format's empty `[SONG]` slot.** Real songs (the pool) and beds (Layer 4
mixing) are both Phase D, so the slot has nothing to fill it in C. **Default for Phase C: drop
`music` from `settings.buffer_rotation`** so only `talk`/`news` air — no silent gaps. If you want a
music feel sooner, drop a short royalty-free bed into the slot instead; just never air the empty gap.
Real song playout returns in D.

## C2.5 — Disk retention: garbage-collect aired segment audio
**Goal:** bound `segments/` so a 24/7 station can't fill the VPS disk. C2 already prunes the
*schedule* (aired entries leave the state + playlist), but the **mp3 files themselves are never
deleted** — at ~1 MB/min of generated audio the 40 GB CX22 fills in a few weeks. C2.5 deletes aired,
unreferenced one-shot renders, and **nothing else**. (Independent of C3 — pickable any time after C2;
doing it *after* C3 is ideal, since the shared disclosure ident it must protect already exists, so the
protection rule is verifiable against real files.)
**Do:**
- Add a `prune()` pass — call it at the end of each `scheduler.top_up()` (or as a sibling the same
  cron runs) — that removes a file in `settings.segments_dir` only when it is ALL of: (a) **not
  referenced** by any current schedule entry's `audio_path` (reuse the live state in
  `settings.schedule_state_path`); (b) **older than `settings.segment_retention_hours`** past its air
  end (a grace window so a just-aired clip Liquidsoap may still be reading isn't yanked, and recent
  audio stays available for clip-cutting/debug); (c) a **one-shot per-segment render** — its `<id>.mp3`
  and matching `<id>.json` sidecar.
- **Protect, never delete** (these are the landmines found in the code):
  - the **reused disclosure ident** clip `ident-disclosure-{provider}-{voice}.mp3` — many schedule
    entries share that ONE file (see `src/disclosure.py`); deleting it because one ident slot aged
    out would break every future ident or force needless re-renders. Exempt it by name pattern.
  - **anything under `assets/`** (curated jingles/brand kit; later songs) — GC only ever touches
    `segments/`, never `assets/`.
  - any path still in the **live schedule/playlist**. (When C4 adds a pre-rendered evergreen pool,
    keep it at a protected path — under `assets/` or a GC-exempt name — so it's never collected.)
- Add the dial `settings.segment_retention_hours` (default e.g. 6); optionally a
  `settings.segment_retention_max_gb` backstop cap. Log each sweep (files + bytes reclaimed) so disk
  management is auditable.
**Don't break what exists:** C2's schedule-*entry* pruning stays exactly as is — C2.5 only adds
*file* deletion keyed off the same "aired + unreferenced" notion. The shared ident clip and every
in-playlist file MUST survive a sweep; the evergreen/disclosure render-and-reuse paths keep working.
**Done when:** after segments age past the retention window their `<id>.mp3`/`.json` are gone; the
disclosure ident, everything under `assets/`, and all upcoming/playlist files remain; `segments/`
size stabilises across a long run; and nothing in the live playlist is ever deleted.

## C3 — Disclosure in the air (spoken + on-player)
**Goal:** turn `Segment.disclosure` from a field into behaviour (EU AI Act Art. 50 + the CLAUDE.md
rule).
**Do:** weave a periodic spoken station ident/disclosure into playout (every
`settings.disclosure_every_n` segments, e.g. "Settlement Radio — a work of fiction, voiced with
AI"); surface the same line on the web player and the YouTube description.
**Done when:** the live stream audibly discloses AI generation on a regular cadence and the player
shows it.

## C4 — Never-dead air: fallback chain + health checks
**Goal:** the stream survives any single failure.
**Do:** ensure the playout fallback chain is scheduled → evergreen → music bed → ident (never
silence); pre-render a small evergreen set. Add orchestration-level resilience: if generation
(Postgres / Kokoro / Claude) fails, playout keeps airing the existing buffer/evergreen. Add health
checks (stalled stream, empty/low buffer, failed nightly run) with a basic alert (log + email/uptime
ping).
**Done when:** killing the generator mid-run leaves the stream playing; a low-buffer or stall
condition raises an alert.

## C5 — Deploy to the VPS (playout + DB + secrets + backups)
**Goal:** the station runs on the always-on box, not your laptop.
**Do:** provision Hetzner CX22. Install Postgres on the VPS; point `settings.database_url` at it;
**nightly `pg_dump` to object storage** (the world-state is the irreplaceable asset). **Back up
`assets/` too** — curated, NON-regenerable media (jingles, brand kit; later the song catalog) belongs
in object storage alongside the DB. **`segments/` is NOT backed up** — it's regenerable one-shot
audio, kept bounded by C2.5's retention GC. Deploy Liquidsoap + Icecast. systemd/cron for services +
the **periodic scheduler top-up** (which now also prunes — C2.5 — so the disk stays bounded
unattended); services restart on reboot. Secrets in env only, non-world-readable, redacted in logs
(DB-URL pattern).
**Done when:** the station runs on the VPS across a reboot, the DB **and `assets/`** are backed up
nightly, the segment disk stays bounded across a long run, and no secret is world-readable or logged.

## C6 — Generation compute + public voice (the honest architecture call) — DECISION
**Goal:** make a full day's audio render reliably ON THE VPS, and make the public voice a setting.
**Standing constraints:**
- The VPS does ALL generation and playout — **never the laptop.** No personal hardware is a runtime
  dependency. If Kokoro can't keep up, scale the box or the voice, not the laptop.
- The voice is switchable at runtime via `settings.tts_provider`: both **Kokoro** (local/free) and
  **ElevenLabs** (cloud/flagship) must work, so the public voice is a config choice, not a rewrite.
**Do:**
- **Verify the switchable seam (registry already done).** All three backends now map BOTH DJs
  (`vell_night` + `dj_two`) in `src/providers/tts.py` — Kokoro (`bm_george`/`af_heart`), ElevenLabs
  ("Adam"/"Rachel"), and `say` ("Daniel"/"Samantha") — so the seam is switch-ready. Remaining: with
  a funded key, confirm `TTS_PROVIDER=elevenlabs` renders a full two-voice `talk` segment end to end
  and that `emotion` still flows through untouched. Re-pick the ElevenLabs voices after a listen if
  they don't match the DJs' cards.
- **Benchmark Kokoro on the VPS.** Render a full day's buffer on the box; Kokoro is CPU-only and
  slow, so a 2-vCPU CX22 may not finish in the nightly window.
- **If it doesn't finish comfortably, scale the box or flip the voice — not the laptop:** either
  (a) a bigger VPS, or (b) `tts_provider=elevenlabs` (or Cartesia) for speed + production quality.
  **If (b) looks likely, pull the ElevenLabs Startup Grant application forward into Phase C** — don't
  wait for CM — so the launch voice is funded *before* launch.
- Resolve the licensing/disclosure implications of whichever backend ships as the default.
**Done when:** a full day's buffer reliably renders and lands on the VPS within the nightly window,
both backends are switchable by config (both DJs on each), and the default launch voice is chosen.
(Record the decision in the DEVLOG.)

## C7 — YouTube Live relay (the public stream + free scaling)
**Goal:** the 24/7 public stream, on a CDN that scales to any audience for free.
**Do:** FFmpeg push Icecast → YouTube Live (RTMP) with a calm branded visual (beacon/wordmark on
night field); confirm YouTube live-streaming is enabled on the verified channel; keep the direct
Icecast stream as the purist option. Put the AI disclosure in the YouTube description.
**Done when:** Settlement Radio is live 24/7 on YouTube with the brand visual; the Icecast stream
also works.

## C8 — The web player (grow the `/web` app)
**Goal:** settlementradio.com plays the live station (the production web deferred from A2).
**Do:** add a player route to the existing Next app in `/web`: an `<audio>` player pointing at the
stream (or the YouTube embed), the AI-disclosure line, now-playing if feasible, the support/follow
links. Keep the coming-soon content or replace it with the live player.
**Done when:** the domain plays the live stream with disclosure shown, on the existing Vercel app.

## C9 — Soak test: 7 days unattended
**Goal:** prove it survives being left alone.
**Do:** run the full system for 7 days; watch for stalls, dead air, failed nightly runs, drift,
safety escapes; fix what breaks. This is the Phase C gate.
**Done when:** 7 days uninterrupted, safe, disclosed, never-dead, zero manual rescues.
**Note — give the soak a living "now."** The world doesn't self-generate yet (the world-tick is
Phase D) and the one seeded event (Lumen Festival) passes mid-window, after which the dynamic context
thins to static canon. Seed a handful of dated events spanning the 7 days so the station has
upcoming/now/past things to reference and the time-aware framing stays visible. Content *variety* /
anti-repetition is a known Phase D item, not a soak blocker.

---

## Explicitly NOT in Phase C (→ Phase D / Beyond)
The loud launch (Show HN, Reddit, the hero demo, the case study, Anthropic outreach + Cookbook PR);
near-live (the buffer-depth dial is built, but driving it to ~0 + streaming TTS is later); more
channels; community worldbuilding; the wider in-universe digital world.

---

## Marketing this phase — pointer only

The full playbook + acceptance checklists live in **`docs/MARKETING.md`**; sequencing in
`docs/ROADMAP.md`. This phase touches two marketing milestones — work them there, not here:

- **M0 — Seed (do NOW):** you have the continuity-passing conversation clip the whole plan was
  waiting for. Fire the held "first real post" on X, flag postable moments in the DEVLOG (`📣
  Postable:`), update the coming-soon page to "nearly on air." (Checklist: MARKETING.md §3 / M0.)
- **M1 — Soft launch (only when C9 passes):** "it's alive" post, Ko-fi on, first YouTube clips,
  Plausible on the player. Quiet, to existing followers — the loud launch is Phase D / M4.
  (Checklist: MARKETING.md §3 / M1.)

**Don't go loud before C9.** A public 24/7 stream that stalls, airs dead silence, or says something
unsafe in its first week is the one first impression you can't redo — and it's why C0–C4 gate C7/C8.

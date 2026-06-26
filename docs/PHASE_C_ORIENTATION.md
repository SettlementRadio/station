# PHASE C — Orientation (the code track) & handoff to Phase D

> Written mid-Phase-C, at the close of the **code** workstreams **C0–C4**, to seed Phase D planning.
> Phase C splits cleanly into two tracks: the **code** (C0–C4 — gates, framing, scheduler, retention,
> disclosure, never-dead air) and the **operations/hardware migration** (C5–C9 — VPS provision,
> Postgres-on-the-box, YouTube relay, web player, the 7-day soak). **C0–C4 are complete and green;
> C5–C9 are the server track and are intentionally NOT covered here** — they gate the *public launch*,
> not Phase D code. This document is the as-built snapshot of the C0–C4 code, the real signatures and
> seams Phase D will build on, where the build diverged from the plan, and — most important for the D
> pack — **exactly which seam each Phase D workstream plugs into**.
>
> Companion to `docs/PHASE_B_ORIENTATION.md` (same format). The canonical design lives in
> `docs/ARCHITECTURE.md`; per-task detail in `docs/PHASE_C_TASKS.md`; the session-by-session record in
> `docs/DEVLOG.md` (C0–C4 entries, 2026-06-22 → 06-24).

## 0. Why Phase D can start now, in parallel with the server track

The two standing constraints of Phase C ("no personal hardware in the loop"; "voice is a runtime
setting") are about *where the station runs*, not *what the code does*. Everything C0–C4 built runs
locally today via the Makefile (`make schedule` / `air` / `health` / `fallback` / `prune`), against
local Postgres + Kokoro, with no VPS. C5–C9 move that same code onto the Hetzner CX33 and put it in
front of people; they change config and ops, **not the Python seams Phase D extends.** So:

- **Phase D code (world engine, news desk, RAG, production, roster) can proceed against the local
  stack now.** It reads/writes the same `store`, `context`, `scheduler`, and `formats` seams that are
  already on disk.
- The one place the two tracks meet is the **scheduler state + the Liquidsoap playlist seam** (§5).
  Phase D's "programming + admin backbone" (named programs, dayparts, a weekly grid) is the natural
  evolution of the C2 scheduler — built in code, deployed by the server track. Design it so the grid
  is read from config/DB, and it lands cleanly whichever track finishes first.

## 1. What got built (C0–C4) — the narrative

Phase B left a *mind* that could produce a genuine two-DJ conversation but had no gate, no scheduler,
no disclosure, and no never-dead air (PHASE_B_ORIENTATION §6 listed exactly these as the open risks).
C0–C4 closed them:

- **C0 — the gates are real.** `safety.safety_check()` is now an actual two-stage gate (keyword
  pre-filter → cheap `haiku` LLM pass), and continuity was promoted from *advisory* to a **blocking
  gate** inside `compose_segment`. A flagged draft is regenerated (with the editor's note fed back for
  continuity), bounded by attempts, then dropped to a safe **evergreen** fallback — a flagged draft is
  never rendered or aired.
- **C1 — time-aware framing.** `world/framing.py` maps the in-world wall-clock hour to a `ShowFrame`
  (who anchors, who's companion, is-it-a-handover, a prose situation), replacing Phase B's hardcoded
  night→first-light handover that produced the "two in the afternoon / all night" collisions.
- **C2 — a real rolling scheduler.** `scheduler.top_up()` keeps a rolling buffer to
  `buffer_depth_hours` of **measured** audio (ffprobe, not the word-count target), decides air order,
  retries/skips a failed slot without dead air, persists `schedule.json`, and writes the ordered
  `playlist.txt` that Liquidsoap re-reads. **C2.5** adds `prune()`: GC aired one-shot renders so the
  disk stays bounded, protecting the shared/reused clips.
- **C3 — disclosure in the air.** `disclosure.py` renders a spoken AI-disclosure ident (a static,
  gate-free, render-once/reuse clip) that the scheduler weaves into the playlist every
  `disclosure_every_n` content segments; the same line is mirrored in `web/src/lib/disclosure.ts`.
- **C4 — never-dead air.** A Liquidsoap **fallback chain** (`scheduled → evergreen pool → music bed →
  ident → tone`), a **pre-rendered evergreen pool** that survives a Kokoro/Claude/Postgres outage
  (`fallback.ensure_fallback_assets()`), and **health checks** (`health.py`) that make a stall / drained
  buffer / dead scheduler visible via log + webhook + dead-man's-switch ping.

## 2. The new modules Phase D builds on (real signatures)

### `src/safety.py` — the content-safety gate (C0)
```python
@dataclass(frozen=True)
class SafetyResult: ok: bool; reason: str; stage: str   # stage ∈ {keyword, llm, disabled}
safety_check(text: str) -> SafetyResult                 # keyword pre-filter → haiku LLM pass; never raises for content
generate_safe(produce: Callable[[], str], *, attempts=None) -> tuple[str, SafetyResult]
```
Plain-text in/out (knows nothing about Segments) — **this is the same gate Phase E points at listener
inbound, and the one any new Phase D producer (commercials, evolved news) must run.** `_BLOCKLIST` is a
named module constant; the LLM reviewer is tuned to *allow* in-world sci-fi conflict so it doesn't
thrash on drama. `settings.safety_enabled=False` bypasses (dev only).

### `src/world/framing.py` — clock-driven show framing (C1)
```python
@dataclass(frozen=True)
class ShowFrame: part_of_day: str; lead: str; companion: str; is_handover: bool; situation: str
show_frame(now, *, night_host: str, day_host: str) -> ShowFrame   # pure, stateless, no DB/settings
resolve_situation(frame, names: dict[str,str]) -> str             # fill {lead}/{companion} with display names
```
Daypart cutoffs (`_DAWN 5–6`, `_DUSK 20–21`, morning/afternoon/evening) are named module constants —
**the entire "what show is on at this hour" logic today is this one two-host function.** Phase D's
*programming/dayparts* workstream generalises exactly this (named programs, more hosts, a weekly grid);
treat `framing.py` as the seam to grow, not bypass.

### `src/evergreen.py` — the safe fallback segment (C0 + C4)
```python
evergreen_segment(now, *, fmt, seg_id, length_target_sec, reason) -> Segment   # render-on-demand into a failed slot's <id>.mp3 (GC'd)
evergreen_script(now) -> str                                                    # script-only, for a single-DJ path
pick_evergreen_script(now) -> str                                              # deterministic hourly rotation
render_evergreen_pool(*, force=False) -> list[str]                             # C4: pre-render each script ONCE to evergreen-*.mp3 (GC-exempt)
EVERGREEN_NAME_PREFIX = "evergreen-"                                            # the prune exemption key
```
Two tiers, deliberately: the **on-demand** evergreen fills a gate-failed slot and is GC'd like any
render; the **pre-rendered pool** is the never-dead playout tier and is exempt from `prune()` by name.
Scripts are static, timeless, single-voice, name nothing real → skip the gates. Add to the pool freely.

### `src/scheduler.py` — the rolling scheduler (C2) + disk retention (C2.5)
```python
top_up(now=None) -> list[dict]    # refill the rolling buffer to buffer_depth_hours of MEASURED audio; returns upcoming entries in air order
prune(now=None) -> dict           # {files, bytes} — GC aired, unreferenced one-shot renders past the retention grace window
# CLI: python -m src.scheduler [--interval N | --prune]
```
The on-disk contract (read these, don't re-derive):
- **`schedule.json`** (`settings.schedule_state_path`): `{entries:[{id,format,audio_path,air_time,
  actual_duration_sec,length_target_sec}], rotation_index, content_since_ident, last_topup_at}`.
- **`playlist.txt`** (`settings.schedule_playlist_path`): one absolute audio path per line, in air
  order, existing files only — what Liquidsoap watches.

`top_up` also (a) runs `ensure_fallback_assets()` up front, (b) weaves the disclosure ident on cadence,
(c) writes a `last_topup_at` heartbeat health reads, (d) calls `prune()` at the end. A whole-rotation
failure stops the run and leaves the existing buffer airing (never dead air). **Phase D's news desk,
world-tick output, and ad-break cadence all schedule *through this* — `make_format_segment(name, …)` is
the only thing it calls to produce a slot, so a new format is a registry entry, not a scheduler change.**

### `src/disclosure.py` — the spoken AI-disclosure ident (C3)
```python
DISCLOSURE_SPOKEN: str   # ~12s ident script (named constant)
DISCLOSURE_LINE: str     # the short written line — mirrored in web/src/lib/disclosure.ts
disclosure_ident_segment(now, *, seg_id=None) -> Segment   # the reused cached clip, duration-stamped
render_ident_audio(*, force=False) -> str                  # render-once per (provider, voice) → ident-disclosure-{provider}-{voice}.mp3
```
Static, gate-free, render-once/reuse — the cheapest segment in the system. `format="ident"`.

### `src/fallback.py` — prepare the never-dead playout assets (C4)
```python
ensure_fallback_assets(*, force=False) -> dict   # render pool + ident WHILE healthy; write the evergreen playlist; best-effort, never raises
```

### `src/health.py` — health checks + alerts (C4)
```python
run_checks(now=None) -> list[str]                # [] = healthy; logs error + webhook + /fail ping on any issue, success ping when clean
check_buffer(now) / check_last_run(now) / check_stream()   # three independent pure reads
```
Reuses the scheduler's `_load_state`/`_end_of` so the two never disagree. Exits non-zero when unhealthy
(for cron/systemd in C5). **The read-only status console Phase D calls for is this data surfaced** —
`_runway_seconds`, `last_topup_at`, and `schedule.json` are already the "what's airing / buffer depth /
last run" feed.

## 3. The seams that *changed* (what Phase D inherits)

- **`writers/conversation.compose_segment(...)` is now the gate.** Same signature as B5
  (`ctx, now, *, seg_id, length_target_sec, extra_directive, fmt`) but the body is a bounded
  **safety→continuity loop**: each draft must clear `safety_check` *and* `continuity_check`; a safety
  flag re-rolls fresh, a continuity flag re-rolls with `revision_note` fed back; exhausting
  `convo_continuity_max_attempts` returns an `evergreen_segment`. New `meta` keys: `attempts`,
  `part_of_day`, `lead`, `handover`, `safety_stage`, `continuity_ok/tier/note`. `showrunner()` and
  `orchestrate()` now take a `frame: ShowFrame` and a `revision_note`.
- **`formats/__init__.stamp_duration(seg)`** — the single post-render chokepoint that probes and stamps
  `actual_duration_sec`. **Every format returns through `make_format_segment`, so any new Phase D format
  gets honest duration accounting for free** — don't re-probe in the builder.
- **`formats/news.py` + `music.py`** wrap generation in `generate_safe(...)` and fall back to
  `evergreen_segment` on a persistent safety flag. **The pattern to copy for any new single-DJ
  producer** (commercials/promos, sponsor reads).
- **`providers/tts.py`** gained `probe_duration(path) -> float` (ffprobe; lives in the seam with
  `_to_mp3`/`concat_audio`). The `emotion` param is still **accepted-and-ignored** on every backend —
  Phase D wires it to ElevenLabs.
- **`segment.py`** gained `actual_duration_sec: float | None` (measured; the scheduler times on this,
  never `length_target_sec`). `format` now also includes `"ident"` and `"evergreen"`.
- **`config/radio.liq`** was rewritten from "loop the newest file" to "air `playlist.txt` behind the
  5-tier fallback chain" (reads `SCHEDULE_PLAYLIST_PATH`, `FALLBACK_EVERGREEN_PLAYLIST_PATH`,
  `FALLBACK_IDENT_PATH` from env). `liquidsoap --check` green.
- **`web/`** — `src/lib/disclosure.ts` (`DISCLOSURE_LINE`, `DISCLOSURE_TAGLINE`) consumed by
  `page.tsx`. The player route itself is **C8** (server track) — not built.

## 4. The new config dials (Phase D will add to these sections)

All under `settings`, area-prefixed (config.py conventions hold). The Phase-C additions:

| Area | Fields (defaults) |
|---|---|
| Safety (C0) | `safety_enabled=True`, `safety_llm_tier=haiku`, `safety_max_tokens=200`, `safety_max_attempts=2` |
| Continuity gate (C0) | `convo_continuity_max_attempts=2` (added to the B4 `convo_continuity_*` block) |
| Scheduler (C2) | `buffer_depth_hours=3.0`, `schedule_topup_max_segments=60`, `schedule_failure_max_retries=1`, `schedule_playlist_path`, `schedule_state_path` |
| Rotation (C2) | **`buffer_rotation=["talk","news"]`** — `music` DROPPED (empty `[SONG]` slot until D); `buffer_max_segments`, `buffer_target_sec` unchanged |
| Disclosure (C3) | `disclosure_enabled=True`, `disclosure_every_n=4`, `disclosure_voice=vell_night` |
| Retention (C2.5) | `segment_retention_hours=6.0`, `segment_retention_max_gb=None` (optional backstop) |
| Fallback (C4) | `fallback_evergreen_playlist_path` |
| Health (C4) | `health_min_runway_minutes=20`, `health_max_run_age_minutes=90`, `health_stream_url=""`, `health_ping_url=""`, `health_alert_webhook_url=""`, `health_request_timeout_sec=10` |

## 5. The scheduler ↔ playout seam (the one cross-track integration point)

This is where the code track and the server track meet, and where Phase D's programming backbone plugs
in. The contract is purely files in `segments_dir`:

```
scheduler.top_up()  ──writes──▶  schedule.json   (state: ordered entries + heartbeat + cadence counter)
                    ──writes──▶  playlist.txt    (ordered absolute audio paths)
fallback.ensure_*   ──writes──▶  evergreen.txt   (pre-rendered pool paths)
config/radio.liq    ──watches─▶  playlist.txt → evergreen.txt → bed → ident → tone   (never-dead chain)
```

Phase D's **named programs / dayparts / weekly grid** should drive *which format and which hosts*
`top_up` picks for a slot (today it's a flat `buffer_rotation` cycle + the two-host `framing.py`). The
**read-only status console** reads `schedule.json` + `last_topup_at` + `health.run_checks`. **Now-playing
on the web player** is `playlist.txt`/`schedule.json` surfaced over HTTP. None of these need the VPS to
build.

## 6. Where the implementation diverged from the plan

1. **`music` is dropped from the default rotation, not just deferred in playout.**
   `buffer_rotation=["talk","news"]` — airing `music` would mean a silent `[SONG]` gap until Phase D
   fills it (track pool + Layer 4 bed mixing). Re-add `"music"` to the rotation as the *first* visible
   sign Phase D's production layer works.
2. **Two evergreen tiers, by necessity** (C0 on-demand `<id>.mp3`, GC'd; C4 pre-rendered `evergreen-*`,
   GC-exempt) — see §2. A subtlety worth carrying: the prune exemption is *by name prefix*, so any
   future render-once/reuse asset (Phase D idents/stings/beds) must follow the same protected-name
   pattern or live under `assets/` to survive `prune()`.
3. **The Phase A single-DJ `writer.py` / `produce.py` path still hardcodes its `_part_of_day` and is
   NOT clock-framed.** It's unused by the scheduler (which only airs `talk`/`news`), so C1 deliberately
   didn't touch it. If Phase D revives a single-DJ talk format, route it through `framing.py` too.
4. **The continuity escalation (sonnet→opus) sits *inside* `continuity_check`, before the gate spends a
   retry** — it's a confirm step, not an extra attempt. `convo_continuity_max_attempts=2` is draft +
   one note-guided rewrite.
5. **The fallback chain lives in Liquidsoap, not the scheduler.** The scheduler decides *programming*;
   playout owns *never-dead air*. Phase D should keep that split — don't inject fallbacks into
   `schedule.json`.
6. **ElevenLabs registry is complete for both DJs but unvalidated with a funded key** (that's C6, on the
   server/voice track). The seam is switch-ready; the *emotion* wiring and the launch-voice decision are
   Phase D / C6 work, not done here.

## 7. Engineering baseline (verified at the close of C4)

- `ruff check src tests` → **All checks passed!** • `ruff format --check` → **48 files already formatted**.
- `pytest` → **78 passed** (was 29 at end of B; +49 across C). New suites: `test_safety`,
  `test_framing`, `test_evergreen`, `test_fallback`, `test_health`, `test_scheduler`,
  `test_compose_gate`.
- `liquidsoap --check config/radio.liq` → green (the 5-tier chain type-checks; empty/absent playlist
  falls through to the pool).
- Config-over-hardcoding, structured logging, bounded retries, the `no-direct-env` + gitleaks
  pre-commit guards — all still enforced; every C0–C4 module follows them (named domain constants for
  the blocklist / daypart cutoffs / disclosure + evergreen scripts; `settings.X` for every dial).
- **New Makefile targets:** `schedule`, `air` (= schedule + serve), `ident`, `prune`, `fallback`,
  `health` (alongside B's `seed`/`buffer`/`format`/`conversation`).

## 8. Retro — what was fiddly, what it taught us

- **C1 had to land with C0, exactly as the pack warned.** Most Phase B continuity flags were the
  afternoon-handover *bug*, not bad drafts; standing the gate up first would have burned regeneration
  attempts thrashing on a constant. Fixing the framing first means the gate now guards real problems.
  General lesson for D: **a gate is only as good as the framing feeding it** — the world-tick and news
  desk must hand the room *correctly-framed* state or the continuity gate will fight them.
- **"Honest length" was the highest-leverage fix.** PHASE_B_ORIENTATION §5 measured talk at ~45% under
  its `length_target_sec`; a scheduler trusting that metadata mis-plans by ~40%. Measuring with ffprobe
  and scheduling on `actual_duration_sec` is what makes the rolling buffer's runway real. Phase D
  formats inherit this free via `stamp_duration` — **never reintroduce length-target-based timing.**
- **Pre-rendering the fallback *while healthy* is the whole trick.** The outage that drains the buffer
  is often Kokoro/Claude/Postgres itself, so a render-on-demand fallback is useless then. The pool +
  ident are rendered every top-up and cached; that readiness-before-failure pattern is the model for any
  Phase D asset that must survive an outage.
- **The disk *will* fill without C2.5** (~1 MB/min ⇒ the 80 GB box in ~2 months). The prune's landmine
  is the *shared* clips (one disclosure ident reused by every ident slot; the evergreen pool) — deleting
  one because an entry aged out breaks every future use. Name-prefix exemption is the guard; Phase D's
  shared media must opt into it.
- **Cost posture is unchanged and still inverted:** text is near-trivial (short showrunner/continuity/
  safety calls, `haiku` for safety, the stable core cached); **Kokoro CPU render time is the real
  ceiling.** This is precisely why C6 benchmarks a full day's render on the VPS and why the
  launch-voice decision (Kokoro-at-scale vs. a paid flagship) is still open — and why Phase D's "voice &
  emotion" workstream presumes the flagship path (Kokoro can't carry `emotion`).

## 9. The seams Phase D plugs into (the handoff that matters)

Each Phase D workstream from `docs/ROADMAP.md` maps to a concrete seam that is **already on disk and
ready** — Phase D is mostly *filling* these, not laying new plumbing:

| Phase D workstream | The seam it extends | State today |
|---|---|---|
| **Canon → folder** | `world/canon_source.py` + `world/seed.py` read `docs/CANON.md` | single file; seeder parses it to rows. D splits to `docs/canon/*` and reads the folder. |
| **RAG goes live** | `providers/embeddings.py` (`embed`/`retrieve`) + `store` vector seam (documented `canon_embeddings` + `search_canon`) + `context.assemble` | **stubbed and unused**; pgvector not installed; canon facts **untagged** (so `canon_by_tags` falls back to all). D installs pgvector, embeds, tags, activates the seam. |
| **World-simulation engine** | `world/store.py` `events` table + `world/events.py` (`status_of`, `progressed`, `relative_phrase`) + `world/clock.py` | events are **static seeds**; the relative-time renderer already frames them future/now/past. **No nightly tick, no story arcs, no auto-advance** — D's keystone. |
| **News desk (living world)** | `formats/news.py` (one-shot bulletin) + the scheduler rotation | reports the static event window once; **no story log, no recurrence/evolution across the day, no cross-segment continuity.** D rebuilds it to read the story log. |
| **Freshness / anti-repetition** | scheduler `schedule.json` history + `context.assemble` | the scheduler records what aired (ids/formats/air_time) but **nothing tracks topics/openings to avoid repeats.** D adds recent-airplay memory. |
| **Programming + dayparts + grid** | `world/framing.py` (the only daypart logic) + `scheduler.top_up` (flat `buffer_rotation`) | two hardcoded hosts, fixed dawn/dusk handover, flat rotation. **D adds named programs, a weekly grid the scheduler reads, and the read-only status console** (over `schedule.json`/`health`). |
| **Now-playing / program info** | `schedule.json` + `playlist.txt` | written and ordered; **not surfaced** to the web player (player route itself is C8, server track). |
| **Production layer (sound design)** | `assets/` (untracked), `tts.concat_audio`, Liquidsoap | **Layer 4 mixing does not exist** — only the C4 fallback bed. `JINGLE_PROMPTS.md` has the brief. D adds idents/stings/beds + ducking; protect shared media from `prune()` (§6.2). |
| **Songs / music format** | `formats/music.py` + `format_music_song_marker="[SONG]"` + a future `tracks` table | the `[SONG]` slot is an unspoken marker; **`music` is dropped from rotation.** D adds the track catalog + scheduler drop-in + re-adds `music`. |
| **Commercials & sponsorship** | a NEW format (copy the `generate_safe`+evergreen pattern from `news.py`) + scheduler ad-break cadence + a `sponsors` table | nothing exists. The format registry (`FORMATS`) + `make_format_segment` is the slot to add it to. |
| **Voice & emotion + roster** | `providers/tts.py` `emotion` param (inert) + voice registries; `convo_speaker_ids`; `store` `"cast"` table | `emotion` accepted-and-ignored on all backends; **2 DJs hardcoded** in config but the `cast` table + voice registry already support more. D wires emotion (ElevenLabs), adds a pronunciation lexicon, grows the cast with event-log memory. |
| **Safety gate for new content** | `safety.safety_check` / `generate_safe` | done — **every new D producer must run it** (and it's the same gate Phase E points at listener inbound). |

## 10. Explicitly NOT in this document (the server/hardware track)

C5–C9 are real Phase C work but are **operations, not the code Phase D extends**, so they're out of
scope here and tracked in `docs/PHASE_C_TASKS.md`:

- **C5** — provision the Hetzner **CX33**; Postgres-on-the-box; `settings.database_url` repointed;
  nightly `pg_dump` + `assets/` backups to object storage; systemd/cron for the scheduler top-up +
  `make health`; secrets non-world-readable.
- **C6** — benchmark a full day's Kokoro render **on the VPS**; the launch-voice **DECISION** (Kokoro
  at scale vs. paid flagship); validate the ElevenLabs path with a funded key; pull the ElevenLabs
  grant forward if the flagship looks likely.
- **C7** — FFmpeg push Icecast → YouTube Live with the brand visual; disclosure in the description.
- **C8** — the web **player** route in `/web` (the disclosure *copy* is already in `lib/disclosure.ts`).
- **C9** — the **7-day unattended soak** — the Phase C gate before any public launch.

These gate the *public launch*, and they can run on their own timeline. **Phase D code does not depend
on them** — it depends only on the C0–C4 seams above, all of which run on the local stack today.

---

*Bottom line:* the **body is real** — generation is gated (nothing unsafe or self-contradictory airs),
framed for the actual hour, scheduled on honest durations into a rolling buffer that prunes itself,
disclosed on a cadence, and backed by a never-dead fallback chain with health alerts. The seams held
again (no vendor SDK past `llm`/`tts`/`store`; the Segment dial and the cached-core lever survived; a
new format is still just a registry entry). What's left for *public* is the server track (C5–C9); what's
left to make it *deep* is Phase D — and every Phase D workstream plugs into a seam that is already
built, green, and waiting (§9).

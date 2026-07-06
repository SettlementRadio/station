"""The ONE typed settings module — every tunable value in the station lives here.

CLAUDE.md "Engineering standards": config over hardcoding. Modules read
`settings.X`, never a raw literal or `os.getenv`. Values load (in precedence
order) from process env vars, then the repo `.env`, then the defaults below — so
the same code runs locally and on a server by changing env only.

    from .config import settings
    settings.tts_provider          # "kokoro"
    settings.model_id("sonnet")    # "claude-sonnet-4-6"

------------------------------------------------------------------------------
CONVENTIONS — follow these when Phase B tasks add settings, to keep this from
sprawling into a god-object (see the per-area sections below):

1. Config vs domain constant. Put a value HERE only if it varies by
   environment/run or is something an operator would tune (secrets, provider/
   model selection, timeouts, retries, paths, token caps, counts that drive
   cost/volume, the DB URL, log level, buffer size). Leave logic *intrinsic to
   an algorithm* as a NAMED, commented module-level constant next to its code
   (e.g. relative-time thresholds in world/events.py, _part_of_day's hour cutoffs
   in writer.py, the vendor voice registries in providers/tts.py). A named
   constant is not a "magic number" — and hauling it in here makes things worse.

2. Area prefix, always. Every field starts with its area: `llm_`, `model_`,
   `tts_`, `world_`, `segment_`, `writer_`, `context_` (B3), `convo_` (B4),
   `format_` (B5), `buffer_` (B6), `retry_`, `log_`. This is what prevents
   collisions — e.g. B4's cap is `convo_max_tokens`, never a bare `max_tokens`.
   (Secrets keep their conventional vendor names: ANTHROPIC_API_KEY etc.)

3. One section per area, in task order. Add new fields under the matching
   section; create a new `# --- <Area> (B?) ---` section for a new area.
------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root, resolved from this file so paths work regardless of the working
# directory (the pipeline is run from the repo root, but tests/tools may not be).
_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed, env-backed configuration for the whole station backend."""

    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # tolerate unrelated keys in .env (e.g. BUTTONDOWN_API_KEY)
    )

    # --- Secrets (read from .env / env; never hardcoded, never committed) ------
    # Kept under their conventional vendor names (no area prefix).
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""

    # --- Model routing: logical tier -> real Claude model id (CLAUDE.md) -------
    # Map the tiers here, in one place, so the rest of the codebase only ever
    # talks in tiers ("haiku" | "sonnet" | "opus"); see `model_id()` below.
    model_haiku: str = "claude-haiku-4-5-20251001"
    model_sonnet: str = "claude-sonnet-4-6"
    model_opus: str = "claude-opus-4-8"

    # --- LLM call defaults -----------------------------------------------------
    llm_default_tier: str = "sonnet"  # the default writing brain
    llm_max_tokens: int = 4000
    llm_timeout_sec: float = 120.0

    # --- LLM Batch API (D3: the nightly world tick's cost lever) ----------------
    # The Batch API runs many requests asynchronously at 50% of standard price —
    # the right fit for the nightly world tick (D3), which is not latency-sensitive.
    # It lives ONLY behind `providers/llm.generate_batch` (the vendor batch SDK is
    # imported nowhere else); callers like the tick never touch it directly.
    # `llm_batch_enabled=False` makes `generate_batch` run each request SYNCHRONOUSLY
    # via the normal `generate` path instead — no async wait, full price — so a local
    # `make world-tick` finishes immediately for a quick check; leave it True on the
    # box so the nightly run takes the discount. The poll interval + max wait bound
    # the submit→poll→collect loop (a batch usually finishes within an hour, may take
    # up to 24h — hence the generous default ceiling; a run that exceeds it fails loud).
    llm_batch_enabled: bool = True
    llm_batch_poll_interval_sec: float = 30.0
    llm_batch_max_wait_sec: float = 86_400.0  # 24h — the Batch API's own max lifetime

    # --- TTS seam --------------------------------------------------------------
    # Which implementation tts.py selects: kokoro (default, local/free) |
    # elevenlabs (flagship cloud) | say (macOS offline fallback). The vendor
    # voice *registries* stay in providers/tts.py (domain data, not config).
    tts_provider: str = "kokoro"
    tts_elevenlabs_model: str = "eleven_multilingual_v2"
    tts_elevenlabs_output_format: str = "mp3_44100_128"
    tts_kokoro_repo_id: str = "hexgrad/Kokoro-82M"
    tts_kokoro_sample_rate: int = 24_000
    tts_kokoro_speed: float = 1.0
    tts_mp3_bitrate: str = "128k"  # shared _to_mp3() transcode bitrate
    # D9.0 — the station-wide DEFAULT logical emotion, applied when a turn/
    # segment sets none ("" = engine default, no expressiveness override).
    # Values come from the emotion vocabulary in providers/tts.py (warm | wry |
    # somber | bright | urgent). Only the flagship (ElevenLabs) path renders
    # emotion audibly; Kokoro/`say` accept and ignore it — which engine ships
    # (and so whether this is heard) is the C6 launch-voice decision.
    tts_emotion_default: str = ""
    # D9.1 — the pronunciation lexicon: the world's invented names (Zhe, the
    # Lumen Festival) spoken right and consistently on either engine. The YAML
    # is the HUMAN-EDITED source of truth (fix a mispronunciation there — no
    # code change; the loader re-reads on file change). Applied to script text
    # just before synthesis, behind the seam (providers/lexicon.py): Kokoro
    # gets exact phonemes via misaki's [name](/phonemes/) markup, other engines
    # a phonetic-respelling substitution. The toggle is a clean rollback.
    tts_lexicon_enabled: bool = True
    tts_lexicon_path: Path = Field(default=_REPO_ROOT / "config" / "pronunciation.yaml")
    # D9.2 — the voice registry: logical voice -> vendor preset, per engine.
    # config/voices.yaml is the human-edited source of truth (one entry per DJ,
    # all engines) so growing the roster never means editing providers/tts.py.
    # Unlike the lexicon it is REQUIRED: a missing file / unmapped voice fails
    # loud (never a silent wrong voice); seeding pre-validates cast against it.
    tts_voices_path: Path = Field(default=_REPO_ROOT / "config" / "voices.yaml")

    # --- World (in-world clock; B2 events build on this) -----------------------
    world_years_ahead: int = 600  # in-world year is always real year + this (CANON.md)

    # --- Segment defaults ------------------------------------------------------
    segment_default_length_target_sec: int = 300  # ~5-min talk segment; a DIAL
    segment_vell_voice: str = "vell_night"  # logical voice name (tts.py registry)

    # --- Writer (single-DJ script) ---------------------------------------------
    # Spoken word-count guidance, tuned in B0 to land within ~10% of the length
    # target at Kokoro's pace. Retune if the TTS backend or pace changes.
    writer_words_low: int = 1000
    writer_words_high: int = 1050
    writer_max_tokens: int = 2000  # output cap for one talk script (~1000 words)
    writer_speaker_id: str = "vell"  # cast id whose card the writer speaks from (B3)

    # --- Context assembly (B3: structured retrieval for the writers' room) -----
    # The half-window, in whole days, for "events near `now`": context.assemble
    # pulls events whose in-world datetime falls within ±this of the in-world now,
    # so an upcoming festival or a just-passed one reaches the writer. Widen it to
    # give the DJs a longer horizon; it is a date query, not a cost driver.
    context_event_window_days: int = 14
    # D2.4: how many canon facts semantic recall (`embeddings.retrieve`) pulls for a
    # topic — the top-k by MEANING. `_select_canon` unions these with the structured
    # tag-match, falling back to all canon when neither hits (so the writer never
    # loses the core facts). Raise it to give the writer more relevant canon per
    # topic; it is a retrieval breadth dial, not a cost driver while the bible is small.
    context_canon_top_k: int = 6
    # D10.2: how many attributable figure quotes the writers' room sees ("what people
    # are saying"), so the DJs can reference and react to an opinion in character. With
    # a topic, they're recalled by MEANING (D2 over the `quote` corpus); with none, the
    # newest quotes in the event window. 0 disables it. `context_quotes_top_k` is the
    # semantic breadth pulled before bounding to the limit.
    context_quotes_limit: int = 4
    context_quotes_top_k: int = 8

    # --- Conversation (B4: two-DJ dialogue — the writers' room) ----------------
    # The cast ids (cards from the DB) who hold the conversation, in handover
    # order: the night host then the first-light host. Their logical voices come
    # from each card's `logical_voice`, mapped to a preset in providers/tts.py.
    convo_speaker_ids: list[str] = ["vell", "wren"]
    # Spoken-length guidance for the whole exchange (both DJs combined). A two-voice
    # exchange feels longer than its word count, but too tight a budget forces clipped,
    # unnatural compression — so the range gives the conversation room to breathe at a
    # natural rhythm (the orchestrate prompt says rhythm matters more than the number).
    # Retune as needed; higher = longer segments + more TTS time (free on Kokoro).
    convo_words_low: int = 550
    convo_words_high: int = 750
    # Per-step model tiers + output caps. The orchestrator (the dialogue) and the
    # showrunner (beat pick) run on the default writing brain; continuity runs on
    # sonnet and ESCALATES to opus only when the sonnet pass flags trouble.
    convo_max_tokens: int = 1600  # orchestrator: the dialogue draft
    convo_showrunner_max_tokens: int = 300  # showrunner: a short beat brief
    convo_continuity_tier: str = "sonnet"  # first continuity pass
    convo_continuity_escalation_tier: str = "opus"  # only if the first flags trouble
    convo_continuity_max_tokens: int = 500
    # C0: continuity is now a GATE, not advisory. When a draft flags, the room
    # regenerates with the editor's note fed back, up to this many attempts total;
    # if it still fails, the slot drops to an evergreen fallback (never airs the
    # flawed draft). 2 = one draft + one note-guided retry. (Spec: PHASE_C C0.)
    convo_continuity_max_attempts: int = 2

    # --- Content-safety gate (C0: real automated check on every draft) ---------
    # CLAUDE.md "Content safety": before any public broadcast, generated text must
    # pass a safety gate. The gate is a fast keyword pre-filter + a cheap LLM pass
    # on the `haiku` tier (see src/safety.py). `safety_enabled=False` bypasses it
    # for local dev ONLY — production must leave it on. `safety_max_attempts` is the
    # single-call producers' policy: generate, regenerate once on a flag, then fall
    # back to an evergreen segment (2 = one draft + one retry). The blocklist itself
    # is a named module constant in safety.py (intrinsic data, not config).
    safety_enabled: bool = True
    safety_llm_tier: str = "haiku"  # the cheap, near-live tier for the LLM pass
    safety_max_tokens: int = 200  # the reviewer replies "OK" / "FLAG: …" — small
    safety_max_attempts: int = 2  # draft + one regenerate before evergreen fallback

    # --- Program formats (B5: reusable show skeletons) -------------------------
    # Each format fills a proven backbone (see src/formats/). `news` and `music`
    # are single-DJ; `talk` is the two-DJ conversation (wraps B4, reusing the
    # convo_* settings above). Speakers are cast ids whose cards/voices drive the
    # segment; word-count guidance and the length-target DIAL are per format so
    # the three read as tonally distinct (a tight news desk vs. a short music bed).
    format_news_speaker_id: str = "vell"  # the single DJ on the news desk
    format_news_headline_count: int = 3  # legacy B5 dial; D4 uses news_story_count
    # A full ~5-minute hourly bulletin. Spoken news runs ~140-160 wpm, and LLMs tend to
    # undershoot a word target, so aim high (~800-1000 words → ~5-6 min) and give the
    # generation enough tokens to reach it. `length_target_sec` is scheduler metadata
    # (the playlist is timed on the MEASURED render, C2) — keep it ~ the real length.
    format_news_words_low: int = 800
    format_news_words_high: int = 1000
    format_news_max_tokens: int = 1600
    format_news_length_target_sec: int = 300  # ~5-min news bulletin; a DIAL
    format_music_speaker_id: str = "vell"  # the single DJ wrapping the track
    format_music_words_low: int = 130
    format_music_words_high: int = 200
    format_music_max_tokens: int = 500
    format_music_length_target_sec: int = 90  # ~1.5-min intro+back-announce; a DIAL
    # The placeholder marker separating the music intro from the back-announce.
    # Real song scheduling is Phase C playout; here the slot is just this marker,
    # kept in the script and recorded in the Segment meta, never spoken.
    format_music_song_marker: str = "[SONG]"

    # --- Nightly buffer (B6: light pre-generated buffer; bridge to Phase C) ----
    # `make buffer` generates a small, varied run of segments in one go — the mind
    # proven at volume, without the real 24/7 scheduler (that, the buffer-depth
    # dial, the Batch API, and the content-safety gate all land in Phase C). It
    # cycles `buffer_rotation` (a mix of the three B5 formats, so both DJs appear —
    # `talk` is the two-DJ show) until the segments' length targets sum to roughly
    # `buffer_target_sec` of audio. Lower the target for a quick check, e.g.
    # `BUFFER_TARGET_SEC=600 make buffer`; `buffer_max_segments` is a hard stop so a
    # tiny per-segment length can't spin an unbounded run.
    buffer_target_sec: int = 3600  # ~an hour of audio; the (pre-Phase-C) buffer depth
    # `music` is BACK in the rotation as of D7.4: the `[SONG]` slot is now filled
    # with a real curated track (selector → intro → track → back-announce, one
    # mp3), and a slot with no playable track falls back to evergreen — no silent
    # gap is possible (it was dropped in C2 precisely because the slot was empty).
    # (Both the B6 one-shot buffer and the C2 scheduler read this one rotation
    # dial; in grid mode the program clocks in docs/programming/grid.yaml decide.)
    buffer_rotation: list[str] = ["talk", "news", "music"]  # B5 format names, cycled
    buffer_max_segments: int = 30  # safety cap on segments per run

    # --- Scheduler (C2: the real rolling buffer — Layer 5, replaces one-shot B6) -
    # The scheduler keeps a rolling buffer of upcoming audio at `buffer_depth_hours`
    # of measured duration, in air order, and writes an ordered playlist Liquidsoap
    # re-reads (the Layer 5 <-> playout seam). `buffer_depth_hours` is THE dial that
    # later enables near-live (drop it toward ~0 + streaming TTS in Phase E). A
    # periodic top-up job (`python -m src.scheduler`; cron/systemd in C5) refills it
    # to depth. `schedule_topup_max_segments` caps one top-up run so a tiny per-
    # segment duration can't spin unbounded; `schedule_failure_max_retries` is how
    # many times a failed slot is retried before it's skipped (never dead air — the
    # existing buffer keeps airing). The playlist/state files live in `segments_dir`.
    buffer_depth_hours: float = 3.0  # rolling buffer depth, in hours of real audio
    schedule_topup_max_segments: int = 60  # hard stop on segments added per top-up
    schedule_failure_max_retries: int = 1  # retries of a failing slot before skipping
    schedule_playlist_path: Path = Field(
        default=_REPO_ROOT / "segments" / "playlist.txt"
    )
    schedule_state_path: Path = Field(default=_REPO_ROOT / "segments" / "schedule.json")

    # --- AI disclosure (C3: turn Segment.disclosure into spoken behaviour) -----
    # CLAUDE.md ("AI disclosure") + EU AI Act Art. 50: a public AI broadcast must
    # say so. The scheduler weaves a short spoken station ident (src/disclosure.py)
    # into the playlist every `disclosure_every_n` CONTENT segments, so the live
    # stream audibly discloses on a regular cadence; the SAME line shows on the web
    # player and in the YouTube description. `disclosure_enabled=False` drops the
    # ident from playout (local dev only — production keeps it on). The ident's
    # text is a named module constant in disclosure.py (intrinsic content, not a
    # tunable); `disclosure_voice` mirrors `segment_vell_voice` (the night host).
    disclosure_enabled: bool = True
    disclosure_every_n: int = 4  # air a spoken ident every N content segments
    disclosure_voice: str = "vell_night"  # logical voice for the ident (tts.py)

    # --- Disk retention (C2.5: GC aired segment audio so 24/7 can't fill disk) --
    # C2 prunes the *schedule* (aired entries leave the state + playlist); C2.5
    # prunes the *files* — at ~1 MB/min of generated audio the VPS disk fills in
    # weeks. `prune()` (src/scheduler.py, run at the end of each top-up) deletes a
    # `<id>.mp3`/`<id>.json` render in `segments_dir` only when it is aired
    # (unreferenced by the live schedule) AND its air end is more than
    # `segment_retention_hours` in the past — a grace window so a just-aired clip
    # Liquidsoap may still be reading isn't yanked, and recent audio stays around
    # for clip-cutting/debug. The shared disclosure ident clip and everything under
    # `assets/` are NEVER collected (see src/scheduler.py prune()).
    # `segment_retention_max_gb` is an optional emergency backstop: when set and
    # `segments_dir` still exceeds it after the age sweep, the oldest aired renders
    # are deleted (ignoring the grace window) until back under the cap; None = off.
    segment_retention_hours: float = 6.0  # grace past air end before a render is GC'd
    segment_retention_max_gb: float | None = None  # optional hard size backstop; off

    # --- Never-dead fallback (C4: the playout fallback chain's lower tiers) -----
    # config/radio.liq airs scheduled -> evergreen -> music bed -> ident -> tone so
    # the stream is never silent through any single failure. src/fallback.py
    # pre-renders the evergreen POOL (src/evergreen.py) WHILE the system is healthy
    # and writes this playlist for Liquidsoap to watch, so a clean spoken segment is
    # ready even if Claude/Kokoro are down when the buffer drains.
    # `ensure_fallback_assets()` runs best-effort at the top of every top-up; the
    # pool clips are GC-exempt by name (evergreen-*, like the disclosure ident) so
    # the C2.5 prune never collects them. Liquidsoap reads this path from the env
    # var FALLBACK_EVERGREEN_PLAYLIST_PATH.
    fallback_evergreen_playlist_path: Path = Field(
        default=_REPO_ROOT / "segments" / "evergreen.txt"
    )

    # --- Health checks + alerts (C4: make a failure visible) -------------------
    # `python -m src.health` (cron/systemd in C5) reads the live schedule + stream
    # and alerts when the air is at risk: the rolling-buffer runway has fallen below
    # `health_min_runway_minutes`; no scheduler top-up has completed within
    # `health_max_run_age_minutes` (the scheduler writes a `last_topup_at` heartbeat
    # into the schedule state — this is the "generator stopped running" detector, so
    # keep it comfortably above the top-up cadence); or the stream mount is
    # unreachable. On an issue it logs at error and, if set, POSTs to
    # `health_alert_webhook_url` and pings `health_ping_url` failure; on a clean pass
    # it pings `health_ping_url` success — a healthchecks.io-style dead-man's switch
    # that also catches a timer that stops running entirely. All URLs default empty
    # (log-only); set them in .env on the VPS. `health_stream_url` is the Icecast
    # mount to liveness-check (empty = skip that check).
    health_min_runway_minutes: float = 20.0  # alert below this much queued audio
    health_max_run_age_minutes: float = 90.0  # alert if no top-up completed within
    health_stream_url: str = ""  # Icecast mount to liveness-check; "" = skip
    health_ping_url: str = ""  # dead-man's-switch success ping (e.g. healthchecks.io)
    health_alert_webhook_url: str = ""  # POST alerts here (Slack/Discord/generic)
    health_request_timeout_sec: float = 10.0

    # --- External-call resilience (bounded retry on Claude/TTS) ----------------
    retry_attempts: int = 3  # total attempts, including the first
    retry_backoff_sec: float = 2.0  # base linear backoff between attempts

    # --- Logging ---------------------------------------------------------------
    log_level: str = "info"  # debug | info | warning | error
    log_json: bool = True  # JSON for unattended 24/7 runs; False = console-pretty

    # --- World-state database (used from B1; declared now so the seam reads it) -
    # Conventional name (DATABASE_URL), no area prefix.
    database_url: str = "postgresql://localhost/settlement_radio"

    # --- Paths (resolved from the repo root) -----------------------------------
    segments_dir: Path = Field(default=_REPO_ROOT / "segments")

    # --- Canon (D1: the world bible — a folder of cornerstone files) -----------
    # The bible grew from a single docs/CANON.md (Phase A/B) into a docs/canon/
    # FOLDER of cornerstone files (D1; see docs/canon/README.md). `canon_dir` is
    # the folder; `canon_path` is the legacy single file, kept for back-compat.
    # seed/context AUTO-SELECT (canon_source.load_world/load_bible): the FOLDER
    # wins whenever it holds at least one cornerstone *.md (README.md aside), else
    # they fall back to the single file. So pointing CANON_DIR at a populated folder
    # selects folder mode; an empty/missing folder selects CANON_PATH. This is the
    # file-vs-folder dial — no extra boolean flag.
    canon_dir: Path = Field(default=_REPO_ROOT / "docs" / "canon")
    canon_path: Path = Field(default=_REPO_ROOT / "docs" / "CANON.md")

    # --- Embeddings (D2: semantic retrieval / RAG) -----------------------------
    # Activates the stubbed vector seam (providers/embeddings.py) so the writers'
    # room recalls canon by MEANING, not just date/tag. ALL of this lives behind
    # that seam; the vector SQL lives only in world/store.py.
    #
    # Provider choice (D2.0 DECISION): Anthropic has NO first-party text-embedding
    # endpoint, so the embedder is a genuine third-party pick, not a Claude call.
    # We default to a LOCAL open model (sentence-transformers) — free, unlimited,
    # no new secret, no network, runs on the CX33 (embedding is far cheaper than
    # TTS, the real cost ceiling). This mirrors the Kokoro stance (CLAUDE.md).
    # A hosted option (e.g. Voyage AI) stays switchable behind the seam by setting
    # `embeddings_provider="voyage"` + an `embeddings_*_api_key` — don't make it the
    # default unless quality demands it.
    #
    # `embeddings_dim` is LOAD-BEARING: it is the N in the pgvector `vector(N)`
    # column (D2.1), so it MUST match the chosen model's output (all-MiniLM-L6-v2 =
    # 384). Changing the model means a re-embed + a column migration — never a bare
    # literal, always this dial. MiniLM vectors are L2-normalised, so the vector
    # index uses the COSINE opclass (set in store.py, D2.1).
    embeddings_provider: str = "local"  # local (sentence-transformers) | voyage
    embeddings_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embeddings_dim: int = 384  # == the model's output dim; the pgvector vector(N)

    # --- World tick (D3: the generative world engine) --------------------------
    # The nightly tick (src/world/world_tick.py) invents new bible-consistent
    # happenings as arced, dated stories and writes them to the story log (D3.0).
    # It proposes a bounded number of new stories each run — a MIX of large
    # (a political shift, a festival) and small (a liner goes missing) — then GATES
    # every proposal through safety + a world-continuity check before writing
    # (flagged proposals are regenerated once, then dropped; never written).
    #
    # `*_new_stories_min/max` bound how many new happenings one tick proposes;
    # `*_large_ratio` is the share aimed to be "large" (the rest small). The
    # generation runs on the `sonnet` writing brain (`opus` only for gnarly world
    # calls — not the default here); the continuity check also on `sonnet`.
    # `*_max_attempts` is the C0 regenerate-then-drop budget (2 = draft + one retry).
    # `*_beat_horizon_days` caps how far from "today" (in-world now) a generated beat
    # may be dated, so the clock frames new beats within a believable window.
    world_tick_new_stories_min: int = 2
    world_tick_new_stories_max: int = 4
    world_tick_large_ratio: float = 0.34  # ~1 in 3 new stories aims to be "large"
    world_tick_propose_tier: str = "sonnet"  # the writing brain (CLAUDE.md routing)
    # Headroom for a JSON array of several stories × up to 3 beats each — too small a
    # cap truncates the array mid-object (the parser salvages complete objects, but a
    # tight cap still loses the tail). Bumped for D10.1: each story now also carries its
    # figures + per-beat quotes, so the array is larger; ~6k fits the default batch.
    world_tick_propose_max_tokens: int = 6000
    world_tick_continuity_tier: str = "sonnet"
    world_tick_continuity_max_tokens: int = 300
    world_tick_max_attempts: int = 2  # draft + one regenerate before dropping a story
    world_tick_beat_horizon_days: int = 21  # max |days| from now for a generated beat
    world_tick_active_context_limit: int = 30  # active stories shown for dedup/context
    # D3.2 — advancing running stories so the world has day-to-day continuity.
    # `*_advance_max` caps how many running stories one tick moves on (the least-
    # recently-advanced first, so attention spreads and nothing starves);
    # `*_resolve_after_ticks` is the pacing pressure that keeps the world from
    # accumulating forever — a story older than this many ticks is steered toward
    # resolution (arc stage `past`, after which it stops advancing but stays in the
    # log as history). A flagged advancement is skipped this tick (the story stays
    # active and is retried next tick), never written.
    world_tick_advance_max: int = 3
    world_tick_resolve_after_ticks: int = 5
    # D3.3 — keep the GENERATED world varied, balanced, and non-repetitive (distinct
    # from D5's on-air anti-repetition). `*_max_active_stories` is the new-vs-advance
    # PACING dial: a soft cap on the living world's size — when this many stories are
    # already running the tick proposes NO new ones (only advances/resolves), so the
    # world neither churns (all new) nor stagnates. `*_domain_window_ticks` is how many
    # recent ticks count toward DOMAIN BALANCE, and `*_quiet_domains` how many of the
    # least-used domains the tick is steered to favour (the world-gen analog of D5's
    # airplay memory). De-dup rejects a proposed story too close to an existing one:
    # `*_dedup_threshold` is the SEMANTIC cosine cutoff (via D2 recall over the `story`
    # corpus), `*_dedup_jaccard` the STRUCTURAL title/summary token-overlap cutoff used
    # for within-batch siblings and as the fallback when D2 is unavailable.
    world_tick_max_active_stories: int = 24
    world_tick_domain_window_ticks: int = 7
    world_tick_quiet_domains: int = 4
    world_tick_dedup_threshold: float = 0.86
    world_tick_dedup_jaccard: float = 0.6
    # D10.1 — the tick also peoples its stories: invented FIGURES (the people a story is
    # about) and their attributable, dated QUOTES, generated INSIDE the same proposal /
    # advancement call (so they ride the same safety + continuity gate and the Batch +
    # caching cost levers — a flagged figure/quote drops/regenerates with its story).
    # `*_figures_enabled` is the master toggle (off => stories stay people-less, as
    # before D10). `*_figures_per_story_max` / `*_quotes_per_story_max` bound the volume
    # — a story needs a FEW named voices, not a crowd. `*_advance_new_figures_max` is
    # the reuse-vs-new preference: a continuing story should mostly REUSE its existing
    # figures (by name), introducing at most this many new people per advancement.
    world_tick_figures_enabled: bool = True
    world_tick_figures_per_story_max: int = 3
    world_tick_quotes_per_story_max: int = 4
    world_tick_advance_new_figures_max: int = 1

    # --- News desk (D4: the story-log-driven bulletin) -------------------------
    # The desk (src/formats/news.py) no longer asks for N flat headlines; it SELECTS
    # which running stories (D3 log) this hour reports (D4.1), tags each from the
    # coverage memory (D4.0) as new/repeat/evolve, and frames them by their arc + beat
    # date (D4.2). These dials tune the SELECTION mix.
    #
    # `news_story_count` is the bounded set per bulletin (the old
    # `format_news_headline_count` analog). The desk aims for a MIX, with soft per-kind
    # quotas (filled by rank, never exceeding the count): `news_target_breaking`
    # (a beat at/near now), `news_target_trailed` (a notable upcoming beat to preview),
    # `news_target_ongoing` (a covered-before story still developing). A beat counts as
    # BREAKING when within `news_breaking_window_hours` of in-world now; an upcoming
    # beat is TRAILED when within `news_trail_horizon_days` ahead. A REPEAT (covered
    # before, no new beat) older than `news_repeat_max_stale_hours` is dropped as too
    # cold to re-air (a story with a genuinely new beat is tagged `evolve`, not stale).
    # Canon grounding (D2 recall): each candidate is scored against the bible via
    # `news_canon_recall_k` nearest canon facts, weighted by `news_canon_weight`, so
    # the bulletin connects to canon, not just the calendar — degrading to pure
    # temporal ranking when embeddings/pgvector are unavailable. `news_breaking_bonus`
    # / `news_evolve_bonus` lift breaking + freshly-developed stories in the ranking.
    news_story_count: int = 4
    news_target_breaking: int = 2
    news_target_trailed: int = 1
    news_target_ongoing: int = 1
    news_breaking_window_hours: float = 18.0
    news_trail_horizon_days: int = 7
    news_repeat_max_stale_hours: float = 18.0
    news_canon_recall_k: int = 8
    news_canon_weight: float = 0.5
    news_breaking_bonus: float = 1.0
    news_evolve_bonus: float = 0.5
    # D4.3 — desk continuity: the bulletin is fed each re-reported story's PRIOR
    # coverage (the handle/angle + last stage) so it names + frames it consistently,
    # then a continuity editor pass checks the draft against canon + that prior
    # coverage for renames / contradictions / arc mis-framing. A flag re-rolls with
    # the editor's note fed back, bounded by `news_continuity_max_attempts` (then the
    # evergreen fallback — the C0 discipline). The check runs at `news_continuity_tier`
    # and ESCALATES to `news_continuity_escalation_tier` to confirm a flag before
    # spending a retry (mirrors the two-DJ gate, sparing a good bulletin a false drop).
    news_continuity_max_attempts: int = 2  # drafts before falling back to evergreen
    news_continuity_tier: str = "sonnet"  # the editor pass (CLAUDE.md routing)
    news_continuity_escalation_tier: str = "opus"  # confirm a flag before re-rolling
    news_continuity_max_tokens: int = 300
    # D10.2 — attribution: each selected story carries up to this many of its newest
    # figure quotes in the brief, so the anchor can attribute them ("X, the relay-keeper
    # …, said yesterday") with correct temporal framing. 0 disables quote attribution.
    news_quotes_per_story: int = 2

    # --- Freshness / anti-repetition (D5: the on-air recency memory) ------------
    # A small, persistent record of WHAT aired recently — features only (a topic/beat
    # handle, an opening fingerprint, a few key phrases), never the audio (D5.0) — so
    # 24/7 output doesn't loop: the showrunner avoids re-picking a recent beat, and
    # producers avoid reusing an opening/phrasing (D5.2). DISTINCT from D4's per-story
    # coverage memory, which drives INTENDED recurrence — this is broad, cross-format,
    # output-phrasing freshness (see store.airplay_history / AirplayRecord).
    #
    # `freshness_window_hours` is THE dial: the in-world look-back window (anchored at
    # the generation `now`, on the segment `air_time` timeline) the reads use for
    # "recently on air". Keep it comfortably above `buffer_depth_hours` so the WHOLE
    # upcoming buffer (segments placed AHEAD of now) counts as recent.
    # `freshness_retention_margin` bounds the table for a 24/7 station: `prune_airplay`
    # keeps rows for `freshness_window_hours × freshness_retention_margin` then drops
    # older ones — wide enough that the reads never miss a row, bounded enough that the
    # table can't grow forever. This memory SURVIVES `seed-canon` AND the C2.5 audio
    # prune (that is the whole point — it must outlive the audio it describes) and is
    # cleared only by the destructive `reset-world` (§2a matrix).
    freshness_window_hours: float = 6.0  # look-back for "recently on air"
    freshness_retention_margin: float = 4.0  # keep window × this before sweeping
    # D5.2 — reading the memory back into generation. `freshness_enabled` is the master
    # toggle (off => the writers' room ignores the memory, as before D5).
    # `freshness_recent_limit` caps how many recent topics/openings a prompt shows (the
    # block is small + variable, so it rides the per-call dynamic part, NOT the cached
    # bible — the cache still hits). `freshness_mode` tunes the influence: "prefer" is a
    # SOFT nudge ("prefer a different angle"), "avoid" a HARD "do not reuse these". The
    # default is conservative (prefer + a small limit): over-constraining can starve a
    # small canon, and the moving world (D3) is the real source of variety — D5 only
    # keeps the *wording* from looping on top of it.
    freshness_enabled: bool = True
    freshness_recent_limit: int = 6  # max recent items shown in a prompt block
    freshness_mode: str = "prefer"  # "prefer" (soft nudge) | "avoid" (hard)

    # --- Programming (D6: named programs, dayparts, the weekly grid) ------------
    # The station is programmed by a weekly GRID (docs/programming/grid.yaml — the
    # human-edited source of truth; see docs/programming/README.md for the model).
    # `program_for(now)` (src/world/programming.py) reads it and answers which named
    # show — its hosts, framing hint, and format CLOCK — airs at an in-world wall-
    # clock slot; D6.1 generalises framing.py off it, D6.2 wires the scheduler to it.
    #
    # `programming_grid_path` is the YAML source. `programming_default_program` is the
    # reserved fallback program id returned when no slot matches, so the scheduler
    # never stalls (its framing is the LEGACY hour-derived frame — see the grid file's
    # `default` program and framing.program_frame). `programming_enabled` is the master
    # switch: off => callers fall back to today's flat behaviour (a clean rollback).
    # `programming_console_upcoming` caps how many upcoming entries the D6.3 status
    # console prints; `console_story_limit`/`console_beats_per_story` bound its (D3)
    # story-log panel. The console (`python -m src.console` / `make console`) is
    # STRICTLY READ-ONLY + operator-private (CLI/SSH) — never an internet endpoint.
    programming_grid_path: Path = Field(
        default=_REPO_ROOT / "docs" / "programming" / "grid.yaml"
    )
    programming_default_program: str = "default"
    programming_enabled: bool = True
    programming_console_upcoming: int = 8
    console_story_limit: int = 6  # active stories shown in the console's story log
    console_beats_per_story: int = 1  # newest beats shown per story in that panel
    # D6.4 — the PUBLIC now-playing / program-info feed for the C8 web player
    # (src/nowplaying.py). A small JSON written beside the schedule, refreshed each
    # scheduler top-up, carrying ONLY public-safe fields (on-now/next + program +
    # hosts + disclosure) — never operator/internal state (that's the console above).
    nowplaying_feed_path: Path = Field(
        default=_REPO_ROOT / "segments" / "nowplaying.json"
    )
    nowplaying_next_count: int = 3  # how many upcoming items the public feed lists

    # --- Production media (D7: curated jingles/stings/beds + the songs catalogue) -
    # `assets_dir` is the home of ALL curated, non-regenerable media (idents/themes/
    # stings/music per docs/JINGLE_PROMPTS.md §4) — deliberately OUTSIDE
    # `segments_dir`, so the C2.5 disk GC (which only ever scans `segments_dir`) can
    # never touch it. `tracks_manifest_path` is the human-authored music-lore
    # manifest (the source of truth the `tracks` table is seeded from — `make
    # seed-tracks`); its `audio_path` strings are repo-root-relative. The clip→
    # placement mapping itself (which theme opens which program, which sting
    # precedes the news) is intrinsic domain data, a named registry in
    # src/production/media.py — not config (the config-vs-constant rule above).
    assets_dir: Path = Field(default=_REPO_ROOT / "assets")
    tracks_manifest_path: Path = Field(default=_REPO_ROOT / "config" / "tracks.yaml")
    # D7.1 — the Layer 4 mixing dials (src/production/mix.py). Mixing is baked at
    # RENDER time (the decision is written down in mix.py): a bed sits under speech
    # at `production_bed_gain_db` BELOW the untouched speech (more negative =
    # quieter bed; -15 dB keeps it audibly present but never competing), fading
    # in/out over `production_bed_fade_sec` so it never pops. Over-bedding is worse
    # than none — default conservative and let D7.3 tune per program by ear.
    production_bed_gain_db: float = -15.0
    production_bed_fade_sec: float = 1.5
    # D7.2 — placement cadences (src/production/placement.py; woven by the
    # scheduler exactly like the C3 disclosure ident — ordered entries, playout
    # unchanged). `production_theme_at_boundary` opens each program change with
    # its theme (a handover program gets the B6 "passing the light" sting first —
    # that pairing is mapping-driven, not a separate dial).
    # `production_sting_before_news` fires the C8 sting immediately before every
    # news bulletin. `production_ident_every_n` airs the A1 sung station logo
    # every N CONTENT segments (0 = off) — a separate, slower cadence than the
    # C3 disclosure ident (which keeps airing as-is; these are additive).
    production_theme_at_boundary: bool = True
    production_sting_before_news: bool = True
    production_ident_every_n: int = 8
    # D7.3 — which slots get a bed under the speech. DOUBLY opt-in, and
    # deliberately conservative (over-bedding is worse than none): a slot is
    # bedded only when its PROGRAM is listed AND its FORMAT is listed — so with
    # the defaults, only the night show's talk gets the soft B4 bed; its news
    # stays dry, and the whole day stays dry. WHICH bed comes from the D7.0
    # mapping (the program's own bed, else the format's); the LEVEL is the D7.1
    # `production_bed_gain_db` dial. Empty either list to switch bedding off.
    production_bedded_programs: list[str] = ["long_night"]
    production_bedded_formats: list[str] = ["talk"]
    # D7.4 — the music selector: "the brain that decides what to play"
    # (src/production/selector.py — a rule-based, deterministic policy over the
    # track catalogue; the LLM only writes the intro/back-announce AROUND the
    # chosen track, never picks it). Weighted inputs, each a dial:
    #   daypart  — the active program's daypart mood (mellow overnight, brighter
    #              morning; the mood sets are named constants in selector.py);
    #   world    — the live story log's tone tilts the pick (a somber development
    #              pulls a somber track — a cheap keyword rule, no LLM call);
    #   featured — an artist named in a running story, or a track the human
    #              tagged `featured`/`pinned` in config/tracks.yaml;
    #   repeats  — PENALTIES for a track/artist that aired within the D5
    #              freshness window, and for sitting in the same era as the last
    #              spin (the variety spread).
    # `music_select_jitter` is seeded variety: a small deterministic nudge (from
    # the air-time-derived seed) so equal-scored tracks rotate instead of always
    # winning by id — same inputs + seed always pick the same track (testable).
    music_select_daypart_weight: float = 2.0
    music_select_world_weight: float = 1.0
    music_select_featured_weight: float = 3.0
    music_select_repeat_track_penalty: float = 8.0
    music_select_repeat_artist_penalty: float = 3.0
    music_select_era_repeat_penalty: float = 1.0
    music_select_jitter: float = 0.5

    # --- Commercials & promos (D8: in-world spots — texture, not interruption) --
    # The `commercial`/`promo` formats (src/formats/commercial.py) — ONE builder,
    # two registry entries sharing it: `commercial` invents a fictional +600y
    # product/service spot FRESH every airing (never a rotating reel — infinite
    # in-character copy is the AI advantage); `promo` promotes the station / the
    # current named show, truthfully. Both run the C0 gate + evergreen fallback
    # like every producer. The speaker is the host card whose voice reads the
    # spot (a grid `speakers` override still applies); a DISTINCT ad-read voice
    # is a D9 roster decision, not a dial here.
    format_commercial_speaker_id: str = "vell"
    format_commercial_words_low: int = 55
    format_commercial_words_high: int = 90
    format_commercial_max_tokens: int = 300
    format_commercial_length_target_sec: int = 40  # a ~30-40s spot; a DIAL
    # The D8.0 production spectrum — how "produced" a spot sounds. 1 = a single
    # voiced read (default; works standalone). 2 = the read over a ducked bed
    # (reuses D7.1's mixing primitive + the D7.0 "commercial" bed mapping).
    # 3 = a multi-voice scene / figure testimonial (needs the D9 guest voice +
    # a D10 figure — degrades to 1 until D9 lands). 4 = a curated ~2s brand-sting
    # bookend (the ONLY prerecorded ad audio; degrades to 1 while no clip is on
    # disk). Every degrade is logged and the EFFECTIVE level is recorded in the
    # segment meta. Keep richer levels sparse — texture, not a showcase.
    format_commercial_production_level: int = 1
    # D8.1 — the ad-break cadence. WHERE/HOW OFTEN a break airs is the GRID's
    # call, not a global constant: a program declares `break_every: N` in
    # grid.yaml (one break after every N content segments while it's on air;
    # absent/0 = that show takes no breaks), so different dayparts carry
    # different ad loads. These dials only shape/gate the weave itself:
    # `commercial_break_enabled` is the master toggle; `*_max_segments` caps
    # spots per break (default ONE — sparse; over-running ads is worse than
    # none); `*_promo_every_n` makes every Nth spot (counted across breaks) a
    # station promo instead of a commercial (0 = commercials only). The break
    # is bracketed by the D18 break_in/break_out stings (D7 media registry) and
    # placed like the disclosure ident — ordered entries, playout unchanged.
    commercial_break_enabled: bool = True
    commercial_break_max_segments: int = 1
    commercial_break_promo_every_n: int = 3
    # D8.2 — real supporter "Powered by" reads (NEVER "Sponsored by" —
    # docs/MARKETING.md, binding; the lead-in is templated in formats/sponsor.py
    # so it can't drift). Sponsors are HAND-ENTERED catalog (§2a): the manifest
    # is the source of truth, seeded by `make seed-sponsors`, and SURVIVES
    # seed-canon/reset-world. The table ships EMPTY — populating real sponsors
    # is gated on CM (donations live), not on D8; until then this whole path
    # airs nothing. `sponsor_read_every_n_breaks` places one read inside every
    # Nth D8.1 ad break (0 = off) — sparse by default, an acknowledgement, not
    # a second ad load. The read's voice mirrors disclosure_voice (a logical
    # tts.py name, not a cast card — the read is station voice, not a show's).
    sponsors_manifest_path: Path = Field(
        default=_REPO_ROOT / "config" / "sponsors.yaml"
    )
    sponsor_read_every_n_breaks: int = 2
    sponsor_read_voice: str = "vell_night"

    def model_id(self, tier: str) -> str:
        """Map a logical tier ("haiku"|"sonnet"|"opus") to its real model id."""
        ids = {
            "haiku": self.model_haiku,
            "sonnet": self.model_sonnet,
            "opus": self.model_opus,
        }
        try:
            return ids[tier]
        except KeyError:
            raise ValueError(
                f"unknown model tier {tier!r}; expected one of {sorted(ids)}"
            ) from None


# The shared instance every module imports. Constructed once at import time.
settings = Settings()

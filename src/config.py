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

    # --- Conversation (B4: two-DJ dialogue — the writers' room) ----------------
    # The cast ids (cards from the DB) who hold the conversation, in handover
    # order: the night host then the first-light host. Their logical voices come
    # from each card's `logical_voice`, mapped to a preset in providers/tts.py.
    convo_speaker_ids: list[str] = ["vell", "wren"]
    # Spoken-length guidance for the whole exchange (both DJs combined). Kept
    # shorter than a single-DJ segment so iteration is fast and TTS time is low; a
    # two-voice exchange feels longer than its word count. Retune as needed.
    convo_words_low: int = 450
    convo_words_high: int = 600
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
    format_news_headline_count: int = 3  # in-world headlines per news segment
    format_news_words_low: int = 320
    format_news_words_high: int = 420
    format_news_max_tokens: int = 900
    format_news_length_target_sec: int = 150  # ~2.5-min news bulletin; a DIAL
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
    # C2: `music` is DROPPED from the default rotation for Phase C — its `[SONG]`
    # slot has nothing to fill it until Phase D (real song pool + Layer 4 bed
    # mixing), so airing it would mean a silent gap. Only `talk`/`news` air for now;
    # re-add "music" once Phase D fills the slot. (Both the B6 one-shot buffer and
    # the C2 scheduler read this one rotation dial.)
    buffer_rotation: list[str] = ["talk", "news"]  # B5 format names, cycled
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
    canon_path: Path = Field(default=_REPO_ROOT / "docs" / "CANON.md")

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

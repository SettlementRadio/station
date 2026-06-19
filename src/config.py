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

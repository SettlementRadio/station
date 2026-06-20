"""Layer 4 (minimal) — turn a script into one audio Segment.

This is the Phase A "production" step (docs/ARCHITECTURE.md, Layer 4): the whole
pipeline is `make_segment(now_iso) -> Segment` — write the script (Layer 3),
synthesize it to audio (the TTS seam), and hand back a populated `Segment`.

`length_target_sec` is the DIAL, not a constant: it defaults to ~5 minutes for
the Phase A talk segment but is a parameter, so the same function later serves a
3-hour overnight block or a 60-second near-live drop without a rewrite (CLAUDE.md
"Segment abstraction", PHASE_A_TASKS.md T7). Only the number — and eventually the
model/TTS tier — changes.
"""

from __future__ import annotations

from datetime import datetime

from .config import settings
from .logging_setup import get_logger
from .providers import tts
from .segment import Segment
from .writer import write_segment_script

log = get_logger(__name__)

# Phase A talk segment defaults (PHASE_A_TASKS.md T4) now live in `settings`: the
# length target is a DIAL with a default, the voice + paths are config, never
# hardcoded constants here.


def make_segment(
    now_iso: str,
    *,
    length_target_sec: int | None = None,
) -> Segment:
    """Generate one talk Segment for `now_iso`: script → audio → Segment.

    Args:
        now_iso: the current real time as an ISO 8601 string; the in-world clock
            (real + 600 years) is derived from it for the time check.
        length_target_sec: the DIAL — target spoken length in seconds. Defaults
            to `settings.segment_default_length_target_sec` (~5 min) for the
            Phase A talk segment; pass a smaller value for a near-live drop
            (PHASE_A_TASKS.md T7). Never hardcoded downstream.

    Returns:
        A populated `Segment` with `script` and `audio_path` set.
    """
    if length_target_sec is None:
        length_target_sec = settings.segment_default_length_target_sec

    # A unique, sortable id from the real timestamp, so Liquidsoap can pick the
    # newest file and ids never collide across runs.
    seg_id = f"vell-{datetime.fromisoformat(now_iso):%Y%m%dT%H%M%S}"
    log.info("make_segment_start", seg_id=seg_id, length_target_sec=length_target_sec)

    # The writer pulls its world context from the DB via context.assemble (B3);
    # no CANON.md read here. `make seed` must have populated the world store.
    script = write_segment_script(now_iso)

    out_path = settings.segments_dir / f"{seg_id}.mp3"
    tts.synthesize(script, voice=settings.segment_vell_voice, out_path=str(out_path))

    log.info("make_segment_done", seg_id=seg_id, audio_path=str(out_path))
    return Segment(
        id=seg_id,
        format="talk",
        length_target_sec=length_target_sec,
        air_time=now_iso,
        script=script,
        audio_path=str(out_path),
        disclosure=True,
    )


if __name__ == "__main__":
    # Runnable check: generate a fresh segment for the current time.
    #   .venv/bin/python -m src.produce
    segment = make_segment(datetime.now().isoformat())
    log.info(
        "segment_written",
        fmt=segment.format,
        seg_id=segment.id,
        audio_path=segment.audio_path,
        length_target_sec=segment.length_target_sec,
        disclosure=segment.disclosure,
    )

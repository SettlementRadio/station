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
from pathlib import Path

from .providers import tts
from .segment import Segment
from .writer import write_segment_script

# Phase A talk segment defaults (PHASE_A_TASKS.md T4). The length is a dial with
# a default, never a hardcoded constant downstream.
DEFAULT_LENGTH_TARGET_SEC = 300  # ~5 minutes
VELL_VOICE = "vell_night"        # logical voice name (see tts.py registry)

# Where generated audio lands (gitignored). Resolved from this file so it works
# regardless of the working directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SEGMENTS_DIR = _REPO_ROOT / "segments"
_CANON_PATH = _REPO_ROOT / "docs" / "CANON.md"


def make_segment(
    now_iso: str,
    *,
    length_target_sec: int = DEFAULT_LENGTH_TARGET_SEC,
) -> Segment:
    """Generate one talk Segment for `now_iso`: script → audio → Segment.

    Args:
        now_iso: the current real time as an ISO 8601 string; the in-world clock
            (real + 600 years) is derived from it for the time check.
        length_target_sec: the DIAL — target spoken length in seconds. Defaults
            to ~5 minutes for the Phase A talk segment; pass a smaller value for
            a near-live drop (PHASE_A_TASKS.md T7). Never hardcoded downstream.

    Returns:
        A populated `Segment` with `script` and `audio_path` set.
    """
    canon_text = _CANON_PATH.read_text()
    script = write_segment_script(canon_text, now_iso)

    # A unique, sortable id from the real timestamp, so Liquidsoap can pick the
    # newest file and ids never collide across runs.
    seg_id = f"vell-{datetime.fromisoformat(now_iso):%Y%m%dT%H%M%S}"
    out_path = _SEGMENTS_DIR / f"{seg_id}.mp3"

    tts.synthesize(script, voice=VELL_VOICE, out_path=str(out_path))

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
    print(f"Wrote {segment.format} segment {segment.id}")
    print(f"  audio: {segment.audio_path}")
    print(f"  length target: {segment.length_target_sec}s  disclosure: {segment.disclosure}")

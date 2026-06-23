"""C3 — disclosure in the air: the spoken AI-disclosure station ident.

CLAUDE.md ("AI disclosure") and the EU AI Act (Art. 50) both require that an
AI-generated broadcast *says so*. This module turns `Segment.disclosure` from a
field nobody reads into behaviour: a short, spoken station ident that the
scheduler (src/scheduler.py) weaves into the playlist every
`settings.disclosure_every_n` content segments, so the live stream audibly
discloses AI generation on a regular cadence.

Like the evergreen fallback, the ident is *static, human-authored, canon-safe*
copy — it names nothing real and references no current event or hour — so it
skips the safety/continuity gates entirely and can air at any time of day.

`DISCLOSURE_SPOKEN` is the script the DJ voices; `DISCLOSURE_LINE` is the short
written line shown on the web player (web/src/lib/disclosure.ts mirrors it) and
placed in the YouTube description (C7). They are the SAME disclosure, in two
registers — keep them saying the same thing if you edit either.

The rendered ident is cheap to reuse: the line never changes, so we render it
ONCE per (provider, voice) to a stable file and reuse that clip for every ident
slot, instead of re-synthesising the same words on every top-up.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import settings
from .formats import stamp_duration
from .logging_setup import get_logger
from .providers import tts
from .segment import Segment

log = get_logger(__name__)

# The spoken ident — a NAMED domain constant (intrinsic content, not a tunable;
# see the config.py convention). Kept short (~30 words ≈ ~12s spoken), in the
# night-host register, naming nothing real (CLAUDE.md IP + content-safety rules).
DISCLOSURE_SPOKEN: str = (
    "You're listening to Settlement Radio — a work of fiction, written and "
    "voiced by artificial intelligence. Everything you hear is imagined: a "
    "tribute to the science fiction that dreamed us all the way out here."
)

# The short written disclosure — the SAME message, for the web player and the
# YouTube description (C7/C8). web/src/lib/disclosure.ts holds the web copy of
# this string; if you change one, change the other so air and screen agree.
DISCLOSURE_LINE: str = (
    "Settlement Radio is a work of fiction, written and voiced by AI."
)

# Nominal metadata length for the ident slot. The scheduler times the playlist on
# the MEASURED duration (stamped below), never on this — it's only the Segment's
# length-target field. ~12s of speech; a domain constant, not an operator dial.
_IDENT_LENGTH_TARGET_SEC: int = 15


def _ident_audio_path(voice: str) -> str:
    """The stable cache path for the rendered ident, keyed by provider + voice.

    Keying on both means flipping `tts_provider` or the voice re-renders the ident
    in the new voice rather than airing a stale clip from the old one.
    """
    provider = settings.tts_provider.strip().lower()
    return str(settings.segments_dir / f"ident-disclosure-{provider}-{voice}.mp3")


def render_ident_audio(*, force: bool = False) -> str:
    """Render the disclosure ident to its cached file (reusing it if present).

    Returns the audio path. The line never changes, so a cached clip for the
    current (provider, voice) is reused; `force=True` re-renders (e.g. after an
    edit to `DISCLOSURE_SPOKEN`).
    """
    voice = settings.disclosure_voice
    out_path = _ident_audio_path(voice)
    if not force and Path(out_path).exists():
        log.info("disclosure_ident_cached", out_path=out_path, voice=voice)
        return out_path
    log.info("disclosure_ident_render", out_path=out_path, voice=voice)
    tts.synthesize(DISCLOSURE_SPOKEN, voice=voice, out_path=out_path)
    return out_path


def disclosure_ident_segment(now: datetime, *, seg_id: str | None = None) -> Segment:
    """Build the spoken disclosure ident as a `Segment` for the scheduler to place.

    Single-voice (the disclosure voice), static text — no gates, no DB. The audio
    is the shared cached clip (rendered once, reused across slots); duration is
    measured and stamped so the scheduler times it like any other segment.
    """
    seg_id = seg_id or f"ident-{now:%Y%m%dT%H%M%S}"
    audio_path = render_ident_audio()
    seg = Segment(
        id=seg_id,
        format="ident",
        length_target_sec=_IDENT_LENGTH_TARGET_SEC,
        air_time=now.isoformat(),
        script=DISCLOSURE_SPOKEN,
        audio_path=audio_path,
        disclosure=True,
        meta={"ident": "disclosure"},
    )
    return stamp_duration(seg)


def main(argv: list[str]) -> int:
    """CLI: render the ident and print its path + measured length (verification).

    .venv/bin/python -m src.disclosure          (render or reuse the cached clip)
    .venv/bin/python -m src.disclosure --force   (force a fresh render)

    Needs a populated .env (live TTS); makes no Claude call (the text is static).
    """
    force = "--force" in argv
    seg = disclosure_ident_segment(datetime.now())
    if force:
        render_ident_audio(force=True)
        seg = disclosure_ident_segment(datetime.now())
    dur = seg.actual_duration_sec
    print("\n----- DISCLOSURE IDENT -----")
    print(f'  spoken : "{DISCLOSURE_SPOKEN}"')
    print(f'  line   : "{DISCLOSURE_LINE}"')
    print(f"  audio  : {seg.audio_path}")
    length = f"{dur:.1f}s (measured)" if dur else "unknown (probe failed)"
    print(f"  length : {length}")
    print(f"  cadence: every {settings.disclosure_every_n} content segments")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))

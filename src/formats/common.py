"""Shared helpers for the program-format templates (PHASE_B_TASKS.md B5).

The three formats (`news`, `talk`, `music`) each fill a proven show skeleton and
hand back one `Segment`. The genuinely reusable, side-effecting bits — choosing
the single speaking DJ, voicing one or more spoken parts in a single voice — live
here so each format module stays a thin, readable backbone. The two-DJ render
path is not duplicated: the `talk` format reuses the B4 conversation orchestrator.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..providers import tts
from ..world.context import AssembledContext
from ..world.store import CastMember

log = get_logger(__name__)


def make_seg_id(fmt: str, now: datetime) -> str:
    """A unique, sortable segment id, prefixed by the format for discoverability."""
    return f"{fmt}-{now:%Y%m%dT%H%M%S}"


def require_speaker(ctx: AssembledContext, fmt: str) -> CastMember:
    """The single speaking DJ for a one-host format; fail loud if none was assembled."""
    if not ctx.speakers:
        raise ValueError(
            f"the {fmt!r} format needs one cast member, but the assembled context "
            "has none (check the format's speaker id and run `make seed`)"
        )
    return ctx.speakers[0]


def render_single_voice(parts: list[str], voice: str, seg_id: str) -> str:
    """Voice one or more spoken `parts` in a single DJ voice; return one mp3 path.

    A single part is synthesized straight to the segment file. Multiple parts (the
    `music` format's intro + back-announce, split by the song-slot marker) are each
    voiced to a temp clip and stitched with `tts.concat_audio`, so the marker line
    itself is never spoken — only the spoken halves around the (future) track land.
    """
    if not parts:
        raise ValueError("render_single_voice: no spoken parts to render")

    out_path = settings.segments_dir / f"{seg_id}.mp3"
    if len(parts) == 1:
        tts.synthesize(parts[0], voice=voice, out_path=str(out_path))
        return str(out_path)

    tmpdir = tempfile.mkdtemp(prefix=f"{seg_id}-")
    try:
        clips: list[str] = []
        for i, part in enumerate(parts):
            clip = os.path.join(tmpdir, f"{i:03d}.mp3")
            tts.synthesize(part, voice=voice, out_path=clip)
            clips.append(clip)
        tts.concat_audio(clips, str(out_path))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return str(out_path)

"""The `music` program format (PHASE_B_TASKS.md B5) — a single-DJ music wrap.

Backbone: a short, warm DJ intro to a piece of music → a SONG SLOT (a placeholder
marker; real song scheduling is Phase C playout) → a brief back-announce. One DJ,
one Claude call.

The song slot is just `settings.format_music_song_marker` on its own line. We keep
it in the saved `script` (so the skeleton is visible) and record it in the Segment
meta, but split the draft on it before rendering so the marker is NEVER spoken —
only the intro and back-announce are voiced, with the (future) track sitting in the
gap between them.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm
from ..segment import Segment
from ..world import clock
from ..world.context import AssembledContext
from ..writer import safety_check
from . import common

log = get_logger(__name__)


def split_on_marker(script: str, marker: str) -> list[str]:
    """Split `script` into spoken parts on any line that is just `marker`.

    Tolerates surrounding whitespace and `**bold**` around the marker line. Empty
    parts are dropped. With no marker present the whole script is one part (the DJ
    intro/back-announce weren't separated — still renders, just as one clip).
    """
    pattern = re.compile(
        rf"^\s*\*{{0,2}}{re.escape(marker)}\*{{0,2}}\s*$", re.MULTILINE
    )
    return [p.strip() for p in pattern.split(script) if p.strip()]


def _build_system(ctx: AssembledContext, now: datetime, dj: str) -> str:
    marker = settings.format_music_song_marker
    world = f"\nWhat's true right now:\n{ctx.dynamic}\n" if ctx.dynamic else ""
    return (
        "You are the writer for Settlement Radio, scripting the host "
        f"{dj} introducing and then back-announcing a piece of music. Write the "
        "SPOKEN SCRIPT ONLY — no stage directions, headings, speaker labels, or "
        "notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n"
        f"{world}\n"
        "Structure (fill this skeleton). You MUST separate the two spoken parts "
        f"with a line containing ONLY the marker {marker} — nothing else on that "
        "line:\n"
        "  1. A short, warm intro to a piece of music: describe it in-world — its "
        "mood, an in-world artist or origin you may invent, why it suits this hour. "
        "Lead the listener into it.\n"
        f"  2. {marker}\n"
        "  3. A brief back-announce: name the in-world piece again, one small "
        "reflective beat, then hand onward.\n\n"
        "Never name real songs, artists, brands, or people; never mention being an "
        "AI; stay entirely inside the fiction. "
        f"Target {settings.format_music_words_low}-"
        f"{settings.format_music_words_high} words across both spoken parts. Tone: "
        "warm, low, unhurried — the voice between the tracks in the small hours."
    )


def music(now: datetime, ctx: AssembledContext) -> Segment:
    """Generate one single-DJ music-wrap `Segment` (intro + slot + back-announce)."""
    dj_card = common.require_speaker(ctx, "music")
    seg_id = common.make_seg_id("music", now)
    marker = settings.format_music_song_marker
    log.info("format_music_start", seg_id=seg_id, dj=dj_card.id)

    system = _build_system(ctx, now, dj_card.name)
    script = llm.generate(
        "Write the music intro and back-announce now.",
        system=system,
        model=settings.llm_default_tier,
        cached_context=ctx.cached_context,
        max_tokens=settings.format_music_max_tokens,
    )
    script = safety_check(script.strip())

    parts = split_on_marker(script, marker)
    if len(parts) < 2:
        # The model didn't place the slot marker — render as one clip, but flag it
        # so the missing skeleton is visible rather than silently swallowed.
        log.warning("format_music_no_marker", seg_id=seg_id, parts=len(parts))

    audio_path = common.render_single_voice(parts, dj_card.logical_voice, seg_id)
    log.info(
        "format_music_done", seg_id=seg_id, parts=len(parts), words=len(script.split())
    )
    return Segment(
        id=seg_id,
        format="music",
        length_target_sec=settings.format_music_length_target_sec,
        air_time=now.isoformat(),
        script=script,
        audio_path=audio_path,
        disclosure=True,
        meta={
            "format_template": "music",
            "speaker": dj_card.id,
            "song_slot_marker": marker,
            "spoken_parts": len(parts),
        },
    )

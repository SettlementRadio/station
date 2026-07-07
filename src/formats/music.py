"""The `music` program format — a single-DJ wrap around a REAL curated track.

Backbone (B5, completed by D7.4): the selector picks a playable track from the
curated catalogue (`production/selector.py` — the rule-based "what to play"
brain; the LLM never chooses), the DJ intro/back-announce is written AROUND that
track's cultural lore (title, artist, album, era, story — the DJ tells the
song's story, not just its name), and the final segment is ONE mp3 stitched
intro → (music bumper) → track audio → back-announce.

The song slot is still `settings.format_music_song_marker` in the script: the
draft is split on it before rendering so the marker is NEVER spoken — but the
gap it marks is no longer empty; the track occupies it. The stitch is a
re-encoding join (`production/mix.join_clips`) because a Kokoro speech clip and
a Suno track share no codec — `tts.concat_audio` (stream copy) can't join them.

Never a silent gap: no playable track (or a selector failure) falls back to an
evergreen segment BEFORE any generation; a flagged draft falls back after (the
C0 gate discipline); a stitch failure raises and the scheduler skips the slot.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from datetime import datetime

from .. import evergreen
from ..config import settings
from ..flow import ShowFlow
from ..logging_setup import get_logger
from ..production import media, mix, selector
from ..providers import llm, tts
from ..safety import generate_safe
from ..segment import Segment
from ..world import clock
from ..world.context import AssembledContext
from ..world.store import Track
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


def _lore_block(track: Track) -> str:
    """The chosen track's cultural lore as prompt lines (skip what's unknown).

    This is what lets the DJ say "a classic from the 24th century, by …, off the
    album …" — the D7.0 catalogue's lore, fed to the writer. Falls back to just
    title + artist when the lore is thin.
    """
    lines = [f'Title: "{track.title}"', f"Artist: {track.in_world_artist}"]
    if track.album:
        lines.append(f'Album: "{track.album}"')
    era_bits = [b for b in (track.era, track.in_world_year) if b]
    if era_bits:
        lines.append(f"Era: {' / '.join(str(b) for b in era_bits)}")
    lines.append(f"Mood: {track.mood}")
    if track.story_blurb:
        lines.append(f"Its story: {track.story_blurb}")
    return "\n".join(lines)


def _build_system(ctx: AssembledContext, now: datetime, dj: str, track: Track) -> str:
    marker = settings.format_music_song_marker
    world = f"\nWhat's true right now:\n{ctx.dynamic}\n" if ctx.dynamic else ""
    return (
        "You are the writer for Settlement Radio, scripting the host "
        f"{dj} introducing and then back-announcing a real piece of music from "
        "the station's library. Write the SPOKEN SCRIPT ONLY — no stage "
        "directions, headings, speaker labels, or notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n"
        f"{world}\n"
        "The song being played (use EXACTLY these details — never invent a "
        "different song, artist, or album):\n"
        f"{_lore_block(track)}\n\n"
        "Structure (fill this skeleton). You MUST separate the two spoken parts "
        f"with a line containing ONLY the marker {marker} — nothing else on that "
        "line:\n"
        "  1. A short, warm intro that tells the song's story: the artist, where "
        "it comes from, its era, why it suits this hour — lead the listener into "
        "it by name.\n"
        f"  2. {marker}\n"
        "  3. A brief back-announce: name the title and artist again, one small "
        "reflective beat drawn from its story, then hand onward.\n\n"
        "Never name real songs, artists, brands, or people; never mention being an "
        "AI; stay entirely inside the fiction. "
        f"Target {settings.format_music_words_low}-"
        f"{settings.format_music_words_high} words across both spoken parts. Tone: "
        "warm, low, unhurried — the voice between the tracks."
    )


def _stitch(parts: list[str], voice: str, track: Track, seg_id: str) -> str:
    """Render the spoken parts and stitch intro → (bumper) → track → back into one mp3.

    The spoken clips are synthesized per part; the track audio comes straight
    from `assets/music/` (curated, never re-rendered); the C10 music bumper sits
    between the intro and the song when its clip exists (the §3 mapping). The
    join re-encodes (heterogeneous codecs), producing the segment's single mp3.
    Raises on a render/join failure — a music slot without its track must fail
    the slot (the scheduler skips it), never air around a hole.
    """
    out_path = settings.segments_dir / f"{seg_id}.mp3"
    track_audio = str(media.track_audio_path(track))
    bumper = media.sting("music_bumper")

    tmpdir = tempfile.mkdtemp(prefix=f"{seg_id}-")
    try:
        intro_clip = os.path.join(tmpdir, "intro.mp3")
        tts.synthesize(parts[0], voice=voice, out_path=intro_clip)

        ordered: list[str] = [intro_clip]
        if bumper is not None:
            ordered.append(str(bumper))
        ordered.append(track_audio)

        if len(parts) > 1:
            back_clip = os.path.join(tmpdir, "back.mp3")
            tts.synthesize("\n\n".join(parts[1:]), voice=voice, out_path=back_clip)
            ordered.append(back_clip)

        mix.join_clips(ordered, str(out_path))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return str(out_path)


def music(
    now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None
) -> Segment:
    """Generate one music `Segment`: a real track, introduced and back-announced.

    `flow` (D12.0) is accepted for the uniform format seam but unused today (the
    talk thread is a two-DJ-conversation concept; a music slot carries it across
    untouched — see the D12 pack).
    """
    dj_card = common.require_speaker(ctx, "music")
    seg_id = common.make_seg_id("music", now)
    marker = settings.format_music_song_marker

    # D7.4 — pick the track FIRST (the selector, not the LLM). No playable track
    # -> evergreen before spending a generation; the slot always airs something.
    track = selector.choose_track(now)
    if track is None:
        log.warning("format_music_no_track", seg_id=seg_id)
        return evergreen.evergreen_segment(
            now,
            fmt="music",
            seg_id=seg_id,
            length_target_sec=settings.format_music_length_target_sec,
            reason="no playable track in the catalogue",
        )
    log.info(
        "format_music_start",
        seg_id=seg_id,
        dj=dj_card.id,
        track=track.id,
        artist=track.in_world_artist,
    )

    system = _build_system(ctx, now, dj_card.name, track)
    script, safety = generate_safe(
        lambda: llm.generate(
            "Write the music intro and back-announce now.",
            system=system,
            model=settings.llm_default_tier,
            cached_context=ctx.cached_context,
            max_tokens=settings.format_music_max_tokens,
        )
    )
    if not safety.ok:
        # C0: never air a flagged draft — fall back to a safe evergreen slot.
        log.error("format_music_safety_fallback", seg_id=seg_id, reason=safety.reason)
        return evergreen.evergreen_segment(
            now,
            fmt="music",
            seg_id=seg_id,
            length_target_sec=settings.format_music_length_target_sec,
            reason=f"safety: {safety.reason}",
        )

    parts = split_on_marker(script, marker)
    if len(parts) < 2:
        # The model didn't place the slot marker — the track still plays (after
        # the whole spoken clip), just without a back-announce. Visible, not fatal.
        log.warning("format_music_no_marker", seg_id=seg_id, parts=len(parts))

    audio_path = _stitch(parts, dj_card.logical_voice, track, seg_id)
    # The target is metadata (the scheduler times on the measured render); make it
    # honest by including the track's probed length when the catalogue knows it.
    length_target = settings.format_music_length_target_sec + int(
        track.duration_sec or 0
    )
    log.info(
        "format_music_done",
        seg_id=seg_id,
        track=track.id,
        parts=len(parts),
        words=len(script.split()),
    )
    return Segment(
        id=seg_id,
        format="music",
        length_target_sec=length_target,
        air_time=now.isoformat(),
        script=script,
        audio_path=audio_path,
        disclosure=True,
        meta={
            "format_template": "music",
            "speaker": dj_card.id,
            "song_slot_marker": marker,
            "spoken_parts": len(parts),
            # D7.4 — the spun track: id/artist feed the D5 airplay memory (the
            # selector's freshness input); the `track` dict is the PUBLIC-SAFE
            # lore now-playing shows (title/artist/album/era only).
            "track_id": track.id,
            "track_artist": track.in_world_artist,
            "track": {
                "title": track.title,
                "artist": track.in_world_artist,
                "album": track.album,
                "era": track.era,
                "in_world_year": track.in_world_year,
            },
        },
    )

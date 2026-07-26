"""R6.1 — the `chart` format: The Count, the daily chart show.

One episode counts down the top N of the daily chart (`src/world/chart.py`),
each position PLAYING its track — the show is a real rundown, not just talk. The
host (Orin, grid-driven) intros each position with its **movement** ("up three",
"new entry", "holds at four") and the track's own story, opening on the day's
chart story; the D20 countdown stings sit between positions, tightening as the
numbers fall (approaching → climbing → the number-one fanfare).

Shape (mirrors the `music` format's pick-then-write-then-stitch, at show scale):
  1. Read the current chart's top N; resolve each to a PLAYABLE catalogue track.
  2. ONE LLM call writes the whole episode — an intro per position (counting down)
     plus a close, each spoken part separated by the song-slot marker.
  3. Stitch: for each position, countdown-sting → spoken intro → the track audio;
     then the close. One re-encoding join (heterogeneous speech+music codecs).

Never a silent gap: no chart, or no playable track in it, falls back to an
evergreen segment BEFORE any generation; a flagged draft falls back after (the C0
gate); a stitch failure raises and the scheduler skips the slot. Every played
track is recorded in the D5 airplay memory (via the segment's `chart_tracks` meta),
so the chart's spins don't loop again in the ordinary music slots right after.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime

from .. import evergreen
from ..config import settings
from ..flow import ShowFlow
from ..logging_setup import get_logger
from ..production import media, mix
from ..providers import llm, tts
from ..safety import generate_safe
from ..segment import Segment
from ..world import chart as chartmod
from ..world import clock, store
from ..world.context import AssembledContext
from ..world.store import CastMember, Track
from . import common

log = get_logger(__name__)


def _sting_for_rank(rank: int) -> str:
    """Which D20 countdown sting tier fits a position (energy climbs as rank falls)."""
    if rank == 1:
        return "chart_countdown_number_one"
    if 2 <= rank <= 5:
        return "chart_countdown_climbing"
    return "chart_countdown_approaching"


def _resolve_positions(
    conn, n: int
) -> tuple[list[tuple[chartmod.ChartEntry, Track]], dict | None]:  # noqa: ANN001
    """The top-`n` chart entries paired with their PLAYABLE catalogue track.

    Skips a charting entry whose track is missing or unplayable (lore without a
    file) — The Count plays what it can. Returns (positions, chart_blob).
    """
    blob = chartmod.current(conn)
    positions: list[tuple[chartmod.ChartEntry, Track]] = []
    for entry in chartmod.top(conn, n):
        track = store.get_track(conn, entry.track_id)
        if track is not None and media.is_playable(track):
            positions.append((entry, track))
        else:
            log.info("chart_position_unplayable", rank=entry.rank, track=entry.track_id)
    return positions, blob


def _rundown_block(
    positions: list[tuple[chartmod.ChartEntry, Track]], story_text: str | None
) -> str:
    """The countdown facts for the writer: each position's movement + story."""
    lines: list[str] = []
    if story_text:
        lines.append(f"STORY OF THE CHART (open on this): {story_text}")
    lines.append(
        "The rundown, in the order you count them down (highest number first):"
    )
    for entry, track in reversed(positions):  # N first … 1 last
        blurb = f" — {track.story_blurb}" if track.story_blurb else ""
        lines.append(
            f'  #{entry.rank}: "{track.title}" by {track.in_world_artist} '
            f"[{entry.movement_phrase()}]{blurb}"
        )
    return "\n".join(lines)


def _build_system(
    ctx: AssembledContext,
    now: datetime,
    dj: CastMember,
    positions: list[tuple[chartmod.ChartEntry, Track]],
    story_text: str | None,
) -> str:
    marker = settings.format_music_song_marker
    world = f"\nWhat's true right now:\n{ctx.dynamic}\n" if ctx.dynamic else ""
    n = len(positions)
    return (
        "You are the writer for Settlement Radio, scripting the host "
        f"{dj.name} presenting THE COUNT — the station's daily music chart show. "
        "Write the SPOKEN SCRIPT ONLY — no stage directions, headings, speaker "
        "labels, or notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n"
        f"{world}\n"
        "Chart movement is SPORT — call it like sport. If a track jumped, that is "
        "drama; treat it as drama. Never play it cool, never philosophise. Use the "
        'exact movement language given ("up three", "new entry", "holds at four"), '
        "and lean on each song's own story for the intro.\n\n"
        f"{_rundown_block(positions, story_text)}\n\n"
        f"Structure — write {n} short position intros, counting DOWN, then a close. "
        f"You MUST separate every spoken part with a line containing ONLY the marker "
        f"{marker} (the song plays there — never describe it playing):\n"
        f"  1. Open on the story of the chart, then intro the #{positions[-1][0].rank} "
        "record: its movement, its story, lead into it by name.\n"
        f"  2. {marker}\n"
        "  3. The next position down — movement, a beat of its story, into it.\n"
        f"  4. {marker}\n"
        "  … one intro + marker per position, counting down to number one …\n"
        "  final. A brief close after number one: name it once more, hand onward.\n\n"
        "Never name real songs, artists, brands, or people; never mention being an AI; "
        "stay entirely inside the fiction. "
        f"Target {settings.format_chart_words_low}-{settings.format_chart_words_high} "
        f"words total across all spoken parts. Tone: unmistakably {dj.name}'s OWN — "
        "follow the register, verbal tics, humour, and cadence of their character card "
        "(cached above); bright, quick, proud — a host who takes the chart personally."
    )


def _stitch(
    parts: list[str],
    voice: str,
    positions: list[tuple[chartmod.ChartEntry, Track]],
    seg_id: str,
) -> str:
    """Stitch sting → intro → track for each position (counting down), then the close.

    `parts` are the spoken halves split on the song marker: ideally one intro per
    position (in count-down order) plus a trailing close. Robust to a miscount — a
    position with no intro still plays (after its sting); leftover parts are voiced
    as the close. Raises on a render/join failure (the scheduler skips the slot).
    """
    out_path = settings.segments_dir / f"{seg_id}.mp3"
    ordered_desc = list(reversed(positions))  # rank N … rank 1
    tmpdir = tempfile.mkdtemp(prefix=f"{seg_id}-")
    try:
        ordered: list[str] = []
        for i, (entry, track) in enumerate(ordered_desc):
            sting = media.sting(_sting_for_rank(entry.rank))
            if sting is not None:
                ordered.append(str(sting))
            if i < len(parts):
                intro_clip = os.path.join(tmpdir, f"intro-{i:02d}.mp3")
                tts.synthesize(parts[i], voice=voice, out_path=intro_clip)
                ordered.append(intro_clip)
            ordered.append(str(media.track_audio_path(track)))

        # Any spoken parts beyond the per-position intros are the close (voiced last).
        if len(parts) > len(ordered_desc):
            close_clip = os.path.join(tmpdir, "close.mp3")
            tts.synthesize(
                "\n\n".join(parts[len(ordered_desc) :]),
                voice=voice,
                out_path=close_clip,
            )
            ordered.append(close_clip)

        mix.join_clips(ordered, str(out_path))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return str(out_path)


def _evergreen(now: datetime, seg_id: str, reason: str) -> Segment:
    return evergreen.evergreen_segment(
        now,
        fmt="chart",
        seg_id=seg_id,
        length_target_sec=settings.format_chart_length_target_sec,
        reason=reason,
    )


def chart(
    now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None
) -> Segment:
    """Generate one The Count `Segment`: the day's chart, counted down and played.

    `flow` is accepted for the uniform format seam but unused (a chart episode is a
    single-host rundown; it carries any live talk thread across untouched).
    """
    dj_card = common.require_speaker(ctx, "chart")
    seg_id = common.make_seg_id("chart", now)
    marker = settings.format_music_song_marker

    # Pick the chart FIRST (no LLM) — no chart / nothing playable in it -> evergreen
    # before spending a generation; the slot always airs something.
    with store.connect() as conn:
        positions, blob = _resolve_positions(conn, settings.format_chart_top_n)
    if not positions:
        log.warning("format_chart_no_positions", seg_id=seg_id)
        return _evergreen(now, seg_id, reason="no playable track on the chart")

    story_text = (blob or {}).get("story_text")
    log.info(
        "format_chart_start",
        seg_id=seg_id,
        dj=dj_card.id,
        positions=len(positions),
        top=positions[0][1].id,
    )

    system = _build_system(ctx, now, dj_card, positions, story_text)
    script, safety = generate_safe(
        lambda: llm.generate(
            "Write The Count episode now — count them down.",
            system=system,
            model=settings.llm_default_tier,
            bible=ctx.bible,
            cards=ctx.cards_block,
            max_tokens=settings.format_chart_max_tokens,
        )
    )
    if not safety.ok:
        log.error("format_chart_safety_fallback", seg_id=seg_id, reason=safety.reason)
        return _evergreen(now, seg_id, reason=f"safety: {safety.reason}")

    from .music import split_on_marker  # shared marker splitter

    parts = split_on_marker(script, marker)
    if len(parts) < len(positions):
        log.warning(
            "format_chart_few_markers",
            seg_id=seg_id,
            parts=len(parts),
            positions=len(positions),
        )

    audio_path = _stitch(parts, dj_card.logical_voice, positions, seg_id)
    length_target = settings.format_chart_length_target_sec + sum(
        int(t.duration_sec or 0) for _, t in positions
    )
    top_entry, top_track = positions[0]
    log.info(
        "format_chart_done",
        seg_id=seg_id,
        positions=len(positions),
        parts=len(parts),
        words=len(script.split()),
    )
    return Segment(
        id=seg_id,
        format="chart",
        length_target_sec=length_target,
        air_time=now.isoformat(),
        script=script,
        audio_path=audio_path,
        disclosure=True,
        meta={
            "format_template": "chart",
            "speaker": dj_card.id,
            "song_slot_marker": marker,
            "spoken_parts": len(parts),
            "chart_no": (blob or {}).get("chart_no"),
            # The #1 is the segment's primary track (now-playing shows its lore); the
            # full played set feeds the D5 airplay memory (freshness.record_segment
            # reads `chart_tracks`) so these spins don't loop in the ordinary music
            # slots right after The Count.
            "track_id": top_track.id,
            "track_artist": top_track.in_world_artist,
            "track": {
                "title": top_track.title,
                "artist": top_track.in_world_artist,
                "album": top_track.album,
                "era": top_track.era,
                "in_world_year": top_track.in_world_year,
                "story_blurb": top_track.story_blurb,
                "chart_rank": top_entry.rank,
            },
            "chart_tracks": [
                {"id": t.id, "artist": t.in_world_artist} for _, t in positions
            ],
        },
    )

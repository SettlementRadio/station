"""D7.2 — the station's discrete sonic identity as scheduler entries.

Producers for the curated `assets/` clips (idents / program themes / stings),
built exactly the way the C3 disclosure ident is: a static, gate-free `Segment`
with `script=None` and `audio_path` pointing at the REUSED curated file
(never re-rendered — the clip IS the render), duration-stamped via
`stamp_duration` so the scheduler times it honestly. The scheduler weaves these
into its ordered playlist like any other entry, so playout needs no change.

Which clip goes where comes from the D7.0 registry (`production.media` — the
JINGLE_PROMPTS §3 mapping); the *when* comes from the D6 grid (the scheduler
detects program boundaries and news slots). Every producer degrades to None
when its clip isn't on disk yet (media logs the warning) — a missing clip means
"skip this placement", never a crash and never dead air.

These clips are MEANT to repeat, so the scheduler does not record them in the
D5 airplay memory (same as the disclosure ident), and their audio lives under
`assets/` where the C2.5 GC never looks.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..config import settings
from ..formats import stamp_duration
from ..logging_setup import get_logger
from ..segment import Segment
from ..world.programming import Program
from . import media, mix

log = get_logger(__name__)

# Nominal metadata length for a curated clip slot (idents/themes/stings run
# ~2–15s). The scheduler times the playlist on the MEASURED duration stamped
# below — this is only the Segment's length-target field (domain constant).
_CLIP_LENGTH_TARGET_SEC = 10

# The handover framing marker (programming.Program.framing) — a program opened
# by "passing the light" gets the B6 handover sting before its theme.
_HANDOVER_FRAMING = "handover"


def _first_content_format(program: Program) -> str | None:
    """The program's opening content format, for the theme fallback.

    The first non-marker clock step's format (`news@:00` → `news`), else the
    first weighted-rotation entry (the `default` program has no clock). None when
    a program has neither. `music` maps to the talk theme upstream — a music slot
    opens with a bumper sting, not a full theme.
    """
    for step in program.clock:
        if not step.is_marker:
            return step.format
    return program.rotation[0] if program.rotation else None


def _clip_segment(
    clip: Path, *, fmt: str, now: datetime, seg_id: str, meta: dict
) -> Segment:
    """One curated clip as a gate-free, duration-stamped `Segment`."""
    seg = Segment(
        id=seg_id,
        format=fmt,
        length_target_sec=_CLIP_LENGTH_TARGET_SEC,
        air_time=now.isoformat(),
        script=None,
        audio_path=str(clip),
        disclosure=False,
        meta=meta,
    )
    return stamp_duration(seg)


def station_ident_segment(now: datetime) -> Segment | None:
    """The A1 sung station ident ("the light between the worlds"), or None."""
    clip = media.ident("signature")
    if clip is None:
        return None
    return _clip_segment(
        clip,
        fmt="ident",
        now=now,
        seg_id=f"ident-station-{now:%Y%m%dT%H%M%S}",
        meta={"ident": "signature"},
    )


def program_theme_segment(program: Program, now: datetime) -> Segment | None:
    """The program's opening theme for a boundary (top of show), or None.

    Carries the program in its meta so the D6.3 console / D6.4 feed name the
    show the theme belongs to, same as a content slot.

    Resolution: the program's own theme (bespoke clip or override), else a
    fallback to its opening FORMAT's theme (news → C7, talk → C9; a music-first
    show uses the talk theme), so a program with no bespoke clip yet still opens
    on-brand rather than cold. None only when neither resolves.
    """
    clip = media.theme_for_program(program.id)
    if clip is None:
        fmt = _first_content_format(program)
        if fmt == "music":
            fmt = "talk"  # music opens with a bumper sting, not a theme
        clip = media.theme_for_format(fmt) if fmt else None
    if clip is None:
        return None
    return _clip_segment(
        clip,
        fmt="theme",
        now=now,
        seg_id=f"theme-{program.id}-{now:%Y%m%dT%H%M%S}",
        meta={
            "theme": program.id,
            "program": program.id,
            "program_name": program.name,
        },
    )


def handover_sting_segment(program: Program, now: datetime) -> Segment | None:
    """The B6 "passing the light" sting opening a handover program, or None."""
    clip = media.sting("handover")
    if clip is None:
        return None
    return _clip_segment(
        clip,
        fmt="sting",
        now=now,
        seg_id=f"sting-handover-{now:%Y%m%dT%H%M%S}",
        meta={
            "sting": "handover",
            "program": program.id,
            "program_name": program.name,
        },
    )


def break_sting_segment(moment: str, now: datetime) -> Segment | None:
    """The D18 sting bracketing an ad break (`"break_in"` | `"break_out"`), or None.

    D8.1: the pair makes a break SOUND like a break — the opener before the
    spot(s), the closer returning to programming. Missing clips degrade to None
    (the break airs unbracketed rather than not at all; media logs the gap).
    """
    if moment not in ("break_in", "break_out"):
        raise ValueError(f"break_sting_segment: unknown moment {moment!r}")
    clip = media.sting(moment)
    if clip is None:
        return None
    return _clip_segment(
        clip,
        fmt="sting",
        now=now,
        seg_id=f"sting-{moment}-{now:%Y%m%dT%H%M%S}",
        meta={"sting": moment},
    )


def sweeper_segment(program: Program, now: datetime) -> Segment | None:
    """The A4 transition sweeper joining two items INSIDE a show (R2.3), or None.

    The quick "moving parts" join for the fast flagship clocks: energy-matched
    via the program's `energy` (calm|steady|bright → the A4 tier), falling back
    to the daypart mapping when the program carries no energy. The scheduler
    weaves it between consecutive content items of the programs listed in
    `settings.production_sweeper_programs` — never at a boundary (the theme owns
    that join) and never around a break (the D18 pair owns those).
    """
    clip = media.sweeper_for_energy(program.energy) if program.energy else None
    if clip is None:
        clip = media.sweeper_for_daypart(program.daypart)
    if clip is None:
        return None
    return _clip_segment(
        clip,
        fmt="sting",
        now=now,
        seg_id=f"sting-sweeper-{now:%Y%m%dT%H%M%S}",
        meta={
            "sting": "sweeper",
            "program": program.id,
            "program_name": program.name,
        },
    )


def news_sting_segment(now: datetime) -> Segment | None:
    """The C8 sting that fires immediately before a news bulletin, or None."""
    clip = media.sting("news")
    if clip is None:
        return None
    return _clip_segment(
        clip,
        fmt="sting",
        now=now,
        seg_id=f"sting-news-{now:%Y%m%dT%H%M%S}",
        meta={"sting": "news"},
    )


def bed_clip_for(program_id: str, fmt: str) -> Path | None:
    """The bed that belongs under this (program, format) slot, or None (dry).

    DOUBLY opt-in (D7.3, conservative by design): both the program AND the
    format must be listed in the `production_bedded_*` dials — so news stays dry
    even inside a bedded program. Which bed: the program's own (D7.0 mapping)
    first, else the format's. None when nothing is mapped or the file is absent.
    """
    if program_id not in settings.production_bedded_programs:
        return None
    if fmt not in settings.production_bedded_formats:
        return None
    return media.bed_for_program(program_id) or media.bed_for_format(fmt)


def apply_bed(seg: Segment, program: Program) -> Segment:
    """Bake the slot's bed (if any) under a rendered speech segment (D7.3).

    Render-time, per the D7.1 decision: the D7.1 primitive loops the bed under
    the speech at `production_bed_gain_db` and returns ONE mp3; the segment then
    points at the mixed render and is RE-MEASURED on that final audio (honest
    duration accounting). A mix failure already degrades inside `duck_bed_under`
    — the segment simply keeps its dry render. The dry `<id>.mp3` stays on disk
    beside the `<id>-bedded.mp3` and both age out through the C2.5 GC normally.
    """
    if not seg.audio_path:
        return seg
    clip = bed_clip_for(program.id, seg.format)
    if clip is None:
        return seg
    out_path = str(settings.segments_dir / f"{seg.id}-bedded.mp3")
    mixed = mix.duck_bed_under(seg.audio_path, str(clip), out_path)
    if mixed != seg.audio_path:  # success — point at the mixed render
        seg.audio_path = mixed
        seg.meta["bed"] = clip.name
        stamp_duration(seg)
        log.info(
            "placement_bed_applied",
            seg_id=seg.id,
            program=program.id,
            bed=clip.name,
            duration_sec=seg.actual_duration_sec,
        )
    return seg


def boundary_segments(program: Program, now: datetime) -> list[Segment]:
    """The clips that open `program` at its boundary, in air order.

    A handover program (the light passes between hosts) opens with the B6
    handover sting, then its theme; a solo program opens with just its theme.
    Missing clips drop out gracefully — the list may be empty.
    """
    out: list[Segment] = []
    if program.framing == _HANDOVER_FRAMING:
        sting = handover_sting_segment(program, now)
        if sting is not None:
            out.append(sting)
    theme = program_theme_segment(program, now)
    if theme is not None:
        out.append(theme)
    return out

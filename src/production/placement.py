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

from ..formats import stamp_duration
from ..logging_setup import get_logger
from ..segment import Segment
from ..world.programming import Program
from . import media

log = get_logger(__name__)

# Nominal metadata length for a curated clip slot (idents/themes/stings run
# ~2–15s). The scheduler times the playlist on the MEASURED duration stamped
# below — this is only the Segment's length-target field (domain constant).
_CLIP_LENGTH_TARGET_SEC = 10

# The handover framing marker (programming.Program.framing) — a program opened
# by "passing the light" gets the B6 handover sting before its theme.
_HANDOVER_FRAMING = "handover"


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
    """
    clip = media.theme_for_program(program.id)
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

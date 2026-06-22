"""C1 — clock-driven show framing: who's on air, and what the on-air situation is.

Phase B framed every two-DJ talk segment as the night→first-light handover, no
matter the hour. With the air cursor (B6) and the scheduler (C2) pushing talk
slots across the whole day, that produced internally-contradictory drafts — a "two
in the afternoon" time check wrapped in "all night / this morning / handover"
language — which the continuity gate (C0) then correctly rejected and regenerated,
thrashing on a bug instead of a bad draft. (See PHASE_B_ORIENTATION §5.)

This module is the single source that maps the in-world wall-clock hour to a
`ShowFrame`: the host anchoring the hour, the companion present, whether this is a
handover, and a prose `situation` the writers' room drops into its prompts in
place of the old constant. The canon's two hosts hand the broadcast between them at
the day's edges — Vell on the quiet night, Wren through the waking day — so:

    deep/late night          → Vell anchors (no handover)
    first light (dawn)       → Vell → Wren handover
    morning / afternoon / eve→ Wren anchors (no handover)
    nightfall (dusk)         → Wren → Vell handover

Pure and stateless (no DB, no settings): the host ids are passed in by the caller
(from the assembled cards), so this stays a clock→frame function with no I/O — and
is unit-testable the way `clock.py` and `events.py` are. The hour is the in-world
wall-clock hour, which equals the real hour (the world clock shifts the year only,
keeping the wall clock — see `clock.render_wall_clock`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Handover windows + daypart cutoffs — named module constants (the intrinsic daily
# schedule, not operator-tunable config; config.py convention). Hours are 0-23 on
# the in-world wall clock. The dawn window hands the night host off to the day host;
# the dusk window hands it back. Everything between is a solo anchor.
_DAWN_START, _DAWN_END = 5, 6  # Vell -> Wren (first light)
_DUSK_START, _DUSK_END = 20, 21  # Wren -> Vell (nightfall)
_MORNING_END = 12  # < this (after dawn) is "morning"
_AFTERNOON_END = 17  # < this is "afternoon"; up to dusk is "evening"


@dataclass(frozen=True)
class ShowFrame:
    """The on-air situation for one hour, derived from the wall clock.

    `lead` anchors the hour (the on-shift host, or the incoming host at a
    handover); `companion` is the other host present. `situation` is a prose
    template with `{lead}` / `{companion}` placeholders the caller fills with the
    hosts' display names — kept here so the framing prose has ONE home.
    """

    # one of: deep night | late night | first light | morning | afternoon |
    # evening | nightfall
    part_of_day: str
    lead: str  # cast id anchoring this hour
    companion: str  # the other host present
    is_handover: bool  # True only in the dawn/dusk transition windows
    situation: str  # prose template; .format(lead=…, companion=…) at the call site


def show_frame(now: datetime, *, night_host: str, day_host: str) -> ShowFrame:
    """Map `now` to its `ShowFrame`, given the night- and day-shift host ids.

    Drives the writers' room's framing from the in-world wall-clock hour instead
    of a hardcoded handover, so a segment generated at any time of day is framed
    for that actual hour (C1). `night_host`/`day_host` are cast ids (e.g. the two
    `settings.convo_speaker_ids`, in canon handover order).
    """
    h = now.hour

    if _DAWN_START <= h <= _DAWN_END:
        return ShowFrame(
            part_of_day="first light",
            lead=day_host,
            companion=night_host,
            is_handover=True,
            situation=(
                "{companion} is handing the broadcast over to {lead} as first light "
                "comes up — the quiet night shift giving way to the waking hours"
            ),
        )

    if _DUSK_START <= h <= _DUSK_END:
        return ShowFrame(
            part_of_day="nightfall",
            lead=night_host,
            companion=day_host,
            is_handover=True,
            situation=(
                "{companion} is handing the broadcast back to {lead} as the dark "
                "comes in — the day winding down into the long night shift"
            ),
        )

    if _DAWN_END < h < _DUSK_START:  # daylight: 7..19
        part = (
            "morning"
            if h < _MORNING_END
            else "afternoon"
            if h < _AFTERNOON_END
            else "evening"
        )
        return ShowFrame(
            part_of_day=part,
            lead=day_host,
            companion=night_host,
            is_handover=False,
            situation=(
                f"{{lead}} is anchoring the {part} shift, the waking worlds well "
                "into their day; {companion} has stayed on for a stretch on air"
            ),
        )

    # Night: 22, 23, 0-4 — the night host alone with the listeners still awake.
    deep = h >= 23 or h <= 4
    return ShowFrame(
        part_of_day="deep night" if deep else "late night",
        lead=night_host,
        companion=day_host,
        is_handover=False,
        situation=(
            "{lead} is carrying the "
            + ("deep, quiet night" if deep else "late night")
            + " shift, alone with the few listeners still awake; {companion} has "
            "stopped in for a few minutes on air"
        ),
    )


def resolve_situation(frame: ShowFrame, names: dict[str, str]) -> str:
    """Fill a frame's `situation` template with host display names (id → name)."""
    return frame.situation.format(
        lead=names.get(frame.lead, frame.lead),
        companion=names.get(frame.companion, frame.companion),
    )

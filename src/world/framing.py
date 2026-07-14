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

D6.1 generalises this beyond the two hardcoded hosts: `program_frame(now, program)`
derives the same `ShowFrame` from a **program** (its N-host cast, lead-first, and its
framing hint — solo/handover/ensemble), so the active program drives *who* is on air
and *whether* it's a handover. `part_of_day` stays hour-derived (finer than a program
slot), which is what keeps the frame prose parity with the two-host `show_frame` — the
`default` program's `legacy` framing routes straight back through `show_frame`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # type-only; program_frame duck-types at runtime (stays I/O-free)
    from .programming import Program

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

    `remote` (field-host audit fix) lists the cast ids in this frame who are
    FIELD-based (`CastMember.based == "field"`): correspondents who reach the air
    only across the relay lag. The situation prose frames them as dispatches, and
    the writers' room adds the dispatch directive — never live in-studio banter.
    """

    # one of: deep night | late night | first light | morning | afternoon |
    # evening | nightfall
    part_of_day: str
    lead: str  # cast id anchoring this hour
    companion: str  # the other host present
    is_handover: bool  # True only in the dawn/dusk transition windows
    situation: str  # prose template; .format(lead=…, companion=…) at the call site
    remote: tuple[str, ...] = ()  # cast ids present only across the relay lag


def part_of_day(now: datetime) -> str:
    """The in-world wall-clock hour's daypart label (the finer, hour-level grain).

    deep night | late night | first light | morning | afternoon | evening |
    nightfall — kept hour-derived (a program slot is coarser than this), which is
    what preserves the two-host frame parity across `show_frame`/`program_frame`.
    """
    h = now.hour
    if _DAWN_START <= h <= _DAWN_END:
        return "first light"
    if _DUSK_START <= h <= _DUSK_END:
        return "nightfall"
    if _DAWN_END < h < _DUSK_START:  # daylight: 7..19
        return (
            "morning"
            if h < _MORNING_END
            else "afternoon"
            if h < _AFTERNOON_END
            else "evening"
        )
    return "deep night" if (h >= 23 or h <= 4) else "late night"  # 22, 23, 0-4


def _situation_for(
    framing_hint: str,
    part: str,
    *,
    has_companion: bool,
    lead_remote: bool = False,
    companion_remote: bool = False,
) -> str:
    """The prose situation template for a (framing hint, daypart) pairing.

    A template with `{lead}`/`{companion}` placeholders (filled by the caller via
    `resolve_situation`). The two-host dayparts reproduce the exact wording the C1
    `show_frame` shipped; the other branches cover operator-authored programs whose
    framing/hour don't line up with the canon dawn/dusk boundaries.

    `lead_remote` / `companion_remote` mark FIELD hosts (the field-host audit fix):
    their presence is a recorded dispatch across the relay lag, and the prose says
    so — the studio never pretends a correspondent is in the booth.
    """
    # A field host's presence is a dispatch, whatever the hour — these branches
    # override the in-studio wording below. (A remote handover has no grid case;
    # it falls through to the generic wording, and the writers' room's dispatch
    # directive still governs how the exchange is written.)
    if framing_hint != "handover":
        if lead_remote and companion_remote:
            return (
                "the studio is carrying the " + part + " on dispatches from "
                "{lead} and {companion}, both recorded out among the worlds and "
                "sent across the relay"
            )
        if lead_remote:
            return (
                "the studio is giving the " + part + " to {lead}'s recorded "
                "dispatch from the field, sent across the relay"
                + (
                    "; {companion} holds the booth between transmissions"
                    if has_companion
                    else ""
                )
            )
        if companion_remote:
            return (
                "{lead} is anchoring the " + part + " from the studio; "
                "{companion} joins by recorded dispatch, sent across the relay "
                "lag from the field"
            )
    if framing_hint == "handover":
        if part == "first light":
            return (
                "{companion} is handing the broadcast over to {lead} as first light "
                "comes up — the quiet night shift giving way to the waking hours"
            )
        if part == "nightfall":
            return (
                "{companion} is handing the broadcast back to {lead} as the dark "
                "comes in — the day winding down into the long night shift"
            )
        return "{companion} is handing the broadcast over to {lead} for the " + part

    # solo / ensemble anchoring.
    if part in ("deep night", "late night"):
        night = "deep, quiet night" if part == "deep night" else "late night"
        base = (
            "{lead} is carrying the " + night + " shift, alone with the few "
            "listeners still awake"
        )
        return base + (
            "; {companion} has stopped in for a few minutes on air"
            if has_companion
            else ""
        )
    if part in ("morning", "afternoon", "evening"):
        base = (
            "{lead} is anchoring the " + part + " shift, the waking worlds well "
            "into their day"
        )
        return base + (
            "; {companion} has stayed on for a stretch on air" if has_companion else ""
        )
    # A solo/ensemble program sitting on a boundary daypart (operator-authored).
    base = "{lead} is anchoring the " + part + " shift"
    return base + ("; {companion} is alongside" if has_companion else "")


def _frame(
    now: datetime,
    *,
    lead: str,
    companion: str,
    framing_hint: str,
    remote: tuple[str, ...] = (),
) -> ShowFrame:
    """Assemble a `ShowFrame` from resolved hosts + a framing hint (general core)."""
    part = part_of_day(now)
    present = {lead, companion} - {""}
    remote_present = tuple(r for r in remote if r in present)
    return ShowFrame(
        part_of_day=part,
        lead=lead,
        companion=companion,
        is_handover=(framing_hint == "handover"),
        situation=_situation_for(
            framing_hint,
            part,
            has_companion=bool(companion),
            lead_remote=lead in remote_present,
            companion_remote=bool(companion) and companion in remote_present,
        ),
        remote=remote_present,
    )


def show_frame(
    now: datetime, *, night_host: str, day_host: str, remote: tuple[str, ...] = ()
) -> ShowFrame:
    """Map `now` to its `ShowFrame`, given the night- and day-shift host ids.

    Drives the writers' room's framing from the in-world wall-clock hour instead
    of a hardcoded handover, so a segment generated at any time of day is framed
    for that actual hour (C1). `night_host`/`day_host` are cast ids (e.g. the two
    `settings.convo_speaker_ids`, in canon handover order). This two-host mapping is
    also the `legacy` framing the D6 `default` program routes back through.
    """
    part = part_of_day(now)
    if part == "first light":  # Vell -> Wren
        lead, companion, hint = day_host, night_host, "handover"
    elif part == "nightfall":  # Wren -> Vell
        lead, companion, hint = night_host, day_host, "handover"
    elif part in ("deep night", "late night"):
        lead, companion, hint = night_host, day_host, "solo"
    else:  # morning / afternoon / evening
        lead, companion, hint = day_host, night_host, "solo"
    return _frame(now, lead=lead, companion=companion, framing_hint=hint, remote=remote)


def program_frame(
    now: datetime, program: Program, *, remote: tuple[str, ...] = ()
) -> ShowFrame:
    """The `ShowFrame` for `now` under `program` — the D6.1 generalisation.

    The program supplies *who* is on air (its `hosts`, lead-first: `hosts[0]` anchors,
    `hosts[1]` is the companion) and *whether* it's a handover (its `framing` hint);
    `part_of_day` stays hour-derived. The reserved `legacy` framing (the `default`
    program) routes straight back through `show_frame`, so a fallback slot — or an
    absent grid — frames exactly as it did before D6. Pure: no I/O, hosts passed in.

    `remote` (field-host audit fix) is the cast ids among the hosts who are FIELD
    correspondents (the caller reads `CastMember.based` — this module stays I/O-free);
    their hours are framed as dispatches across the relay, never in-studio presence.
    """
    hosts = program.hosts
    if program.framing == "legacy":
        night = hosts[0] if hosts else ""
        day = hosts[1] if len(hosts) > 1 else night
        return show_frame(now, night_host=night, day_host=day, remote=remote)
    lead = hosts[0] if hosts else ""
    companion = hosts[1] if len(hosts) > 1 else ""
    return _frame(
        now, lead=lead, companion=companion, framing_hint=program.framing, remote=remote
    )


def resolve_situation(frame: ShowFrame, names: dict[str, str]) -> str:
    """Fill a frame's `situation` template with host display names (id → name)."""
    return frame.situation.format(
        lead=names.get(frame.lead, frame.lead),
        companion=names.get(frame.companion, frame.companion),
    )

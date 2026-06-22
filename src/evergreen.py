"""C0 — the evergreen fallback: a safe, timeless segment that always airs clean.

When a producer's draft fails the safety gate or the continuity gate after the
bounded regeneration attempts, the station must NOT air the flawed draft and must
NOT go dead. It airs an *evergreen* instead: a short, pre-written, in-world
single-DJ piece that references no current event and no specific hour, so it is
always continuity-safe and (being human-authored canon-consistent text) skips the
gates entirely.

This is the minimal C0 fallback — render-on-demand from a small static set. C4
("Never-dead air") promotes it into a pre-rendered evergreen pool plus the full
playout fallback chain (scheduled → evergreen → bed → ident); the seam here is
what that builds on. The scripts are deliberately generic and hopeful, in the
night-host register, and name nothing real (CLAUDE.md IP + content-safety rules).
"""

from __future__ import annotations

from datetime import datetime

from .config import settings
from .logging_setup import get_logger
from .providers import tts
from .segment import Segment

log = get_logger(__name__)

# Static evergreen scripts — a NAMED domain constant (intrinsic content, not a
# tunable; config.py convention). Each is one single-voice block: timeless, with
# no time check and no event reference, so it can never collide with the clock or
# canon. Kept short (~110-140 words ≈ ~1 min spoken). Add to the pool freely.
_EVERGREEN_SCRIPTS: tuple[str, ...] = (
    (
        "You're listening to Settlement Radio, and whatever corner of the dark "
        "you're in tonight, I'm glad of the company. Somewhere out past the relay "
        "the lights of the settlements are turning slow against the black, each one "
        "a room full of people who decided to keep going. That's the whole of it, "
        "really — we keep the signal lit, and we keep each other company across the "
        "distance. No hurry here. Just the hum of the carrier and a voice that "
        "remembers you're out there. Stay warm. Stay curious. We'll keep the light "
        "on this end as long as there's a hand to hold the dial."
    ),
    (
        "Here's a small thought to keep you between the hours. Every signal you've "
        "ever heard left somewhere a long way back, and crossed an enormous quiet to "
        "reach you — and it still arrived. I find that steadying, on the long nights. "
        "Nothing out here is truly alone; it's all just in transit, on its way to "
        "someone. So wherever you are, take it easy a while. Let the dark be soft. "
        "This is Settlement Radio, holding the frequency open, the way we always have "
        "— a little warmth, sent the long way round, and meant for you."
    ),
    (
        "If you've only just found us, welcome — you've tuned into Settlement Radio, "
        "broadcasting out across the settled worlds for anyone awake to listen. "
        "There's no schedule that matters at this hour, no place you have to be. Just "
        "the steady company of a station that doesn't sleep, and the old comfort of a "
        "voice in the room. Settle in. Breathe out the day. The night is long and "
        "we've nowhere else to be — so let's spend a little of it together, and let "
        "the rest of the dark take care of itself."
    ),
)


def pick_evergreen_script(now: datetime) -> str:
    """Choose one evergreen script, rotating deterministically by the hour.

    Deterministic so two fallbacks at the same hour are stable/testable, but
    rotating so a run of fallbacks doesn't repeat one script back-to-back.
    """
    return _EVERGREEN_SCRIPTS[now.hour % len(_EVERGREEN_SCRIPTS)]


def evergreen_segment(
    now: datetime,
    *,
    fmt: str,
    seg_id: str,
    length_target_sec: int,
    reason: str,
) -> Segment:
    """Render a safe evergreen `Segment` to stand in for a gate-failed slot.

    Single-voice (the night host), so it serves as a fallback for any format. The
    `seg_id`/`length_target_sec`/`air_time` carry over from the slot it replaces so
    the scheduler's accounting is unaffected; `meta` records that this is a
    fallback and why, so a gate failure is loud and auditable, never silent.
    """
    script = pick_evergreen_script(now)
    # Always the night host's logical voice (already config): single-voice, so one
    # evergreen serves as a fallback for any format without a DB lookup.
    voice = settings.segment_vell_voice
    out_path = settings.segments_dir / f"{seg_id}.mp3"
    log.warning(
        "evergreen_fallback",
        seg_id=seg_id,
        replacing_format=fmt,
        reason=reason[:300],
    )
    tts.synthesize(script, voice=voice, out_path=str(out_path))
    return Segment(
        id=seg_id,
        format="evergreen",
        length_target_sec=length_target_sec,
        air_time=now.isoformat(),
        script=script,
        audio_path=str(out_path),
        disclosure=True,
        meta={
            "fallback": True,
            "replacing_format": fmt,
            "fallback_reason": reason,
        },
    )


def evergreen_script(now: datetime) -> str:
    """The script-only fallback for the single-DJ writer path (returns a str)."""
    return pick_evergreen_script(now)

"""The sponsor "Powered by" read — real supporter acknowledgements (D8.2).

The one place the station speaks about something REAL: a supporter whose
donation keeps the signal lit, acknowledged inside an ad break (the D8.1
placement mechanism). Two shapes, per the sponsor row:

  * a **voiced read** — the templated lead-in "…is powered by {name}." plus the
    sponsor's hand-entered blurb, run through the C0 safety gate and voiced
    like any segment (a one-shot render the C2.5 GC ages out normally);
  * a **supplied clip** — the sponsor's optional pre-recorded `audio_path`
    (curated under `assets/`, GC-safe, reused — never re-rendered).

The wording rule is BINDING (`docs/MARKETING.md`): always **"Powered by"**,
NEVER "Sponsored by". The lead-in is a template here, so it cannot drift; the
hand-entered blurb is corrected (`enforce_powered_by`) if it tries.

Which sponsor airs is `pick_sponsor` over `store.active_sponsors(now)` — only
sponsors inside their REAL wall-clock run window, weight-expanded into a
deterministic rotation. The table ships empty (populating real sponsors is
gated on CM — donations live), so this whole path airs nothing until then.
"""

from __future__ import annotations

import re
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..production import media
from ..providers import tts
from ..safety import safety_check
from ..segment import Segment
from ..world.store import Sponsor
from . import stamp_duration

log = get_logger(__name__)

# Nominal metadata length for a sponsor read (~10s; the scheduler times on the
# MEASURED render — domain constant, same role as placement's clip target).
_READ_LENGTH_TARGET_SEC = 15

# The binding lead-in template (MARKETING.md). "powered by" is IN the template —
# the one wording that cannot drift, whatever the blurb says.
_LEAD_IN = "This hour of Settlement Radio is powered by {name}."

_SPONSORED_BY_RE = re.compile(r"\bsponsor(ed|s)?\s+by\b", re.IGNORECASE)


def enforce_powered_by(text: str) -> str:
    """Correct any 'sponsored by' drift in hand-entered sponsor text (binding rule).

    The lead-in is templated and safe; this guards the blurb. A correction is
    logged loudly so the operator fixes the manifest — the air never carries
    the wrong wording either way.
    """
    corrected = _SPONSORED_BY_RE.sub("powered by", text)
    if corrected != text:
        log.warning("sponsor_wording_corrected", original=text[:200])
    return corrected


def powered_by_script(sponsor: Sponsor) -> str:
    """The full spoken read: the templated lead-in + the corrected blurb."""
    lead = _LEAD_IN.format(name=sponsor.name)
    blurb = enforce_powered_by(sponsor.powered_by_text.strip())
    return f"{lead} {blurb}".strip() if blurb else lead


def pick_sponsor(active: list[Sponsor], counter: int) -> Sponsor:
    """The sponsor to air for rotation position `counter` — deterministic, weighted.

    Each active sponsor appears `max(weight, 1)` times in a stable cycle (id
    order, as `active_sponsors` returns), indexed by the persisted counter — so
    concurrent sponsors share airtime by weight and the pick is testable.
    """
    if not active:
        raise ValueError("pick_sponsor: no active sponsors")
    cycle: list[Sponsor] = []
    for s in active:
        cycle.extend([s] * max(s.weight, 1))
    return cycle[counter % len(cycle)]


def sponsor_read_segment(now: datetime, sponsor: Sponsor) -> Segment | None:
    """One "Powered by" acknowledgement `Segment` for `sponsor`, or None.

    A supplied clip wins when its file is on disk (reused curated audio, no
    gate — it isn't generated text). Otherwise the templated read is gated
    (`safety_check` — hand-entered text still never bypasses C0) and voiced;
    a flagged blurb SKIPS the read (logged) rather than airing it. None means
    "place nothing this time" — never a crash, never dead air.
    """
    seg_id = f"sponsor-{sponsor.id}-{now:%Y%m%dT%H%M%S}"

    if sponsor.audio_path:
        clip = media.sponsor_clip(sponsor.audio_path)
        if clip is not None:
            return stamp_duration(
                Segment(
                    id=seg_id,
                    format="sponsor",
                    length_target_sec=_READ_LENGTH_TARGET_SEC,
                    air_time=now.isoformat(),
                    script=None,
                    audio_path=str(clip),
                    disclosure=False,  # supplied audio, not AI-generated speech
                    meta={"sponsor": sponsor.id, "name": sponsor.name, "kind": "clip"},
                )
            )
        # Missing clip file → degrade to the voiced read (logged by media).

    script = powered_by_script(sponsor)
    safety = safety_check(script)
    if not safety.ok:
        log.error("sponsor_read_safety_flag", sponsor=sponsor.id, reason=safety.reason)
        return None

    out_path = settings.segments_dir / f"{seg_id}.mp3"
    tts.synthesize(script, voice=settings.sponsor_read_voice, out_path=str(out_path))
    log.info("sponsor_read_rendered", sponsor=sponsor.id, seg_id=seg_id)
    return stamp_duration(
        Segment(
            id=seg_id,
            format="sponsor",
            length_target_sec=_READ_LENGTH_TARGET_SEC,
            air_time=now.isoformat(),
            script=script,
            audio_path=str(out_path),
            disclosure=True,
            meta={"sponsor": sponsor.id, "name": sponsor.name, "kind": "read"},
        )
    )

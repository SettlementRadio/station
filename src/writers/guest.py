"""Guest / non-host voices (D9.3) — a temporary speaker in a talk segment.

The way real radio plays a clip or runs an interview: a segment may include ONE
speaker who is not a rostered DJ —

  * a **figure soundbite** (the D9×D10 bridge): a person the world's stories are
    about, with an attributable quote from the story log, voiced for a moment
    ("here's what they said:" → the figure's line → back to studio); or
  * an **invited guest**: a one-off in-world persona appearing for a brief
    interview, invented by the room inside the fiction.

This module only DECIDES the guest — who (from the assembled context's D10.2
quotes, else an invited persona), which voice (the figure's own `voice_id` when
it names a registry voice, else a pool voice by stable hash so the same person
keeps the same voice across segments), and whether one appears at all (sparse,
deterministically seeded by air time — texture, not a parade of voices). The
conversation orchestrator does the weaving; `Turn`/`_render_turns` already
carry any number of voices.

Degrades cleanly: guests disabled, the dice saying no, or nothing to voice all
yield None — a host-only segment, exactly as before D9.3.
"""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..providers import tts
from ..world.context import AssembledContext

log = get_logger(__name__)

# The label the room uses for an INVITED guest's lines (their in-world name is
# spoken in the hosts' introduction; the label stays fixed so the turn parser
# recognises it without knowing the invented name upfront).
INVITED_LABEL = "Guest"

# The guest voice pool (config/voices.yaml, D9.3 section) — logical voices kept
# distinct from every host's. Domain constant, not config (config.py rule #1):
# the pool IS the registry data; entries missing from voices.yaml are skipped
# with a warning rather than failing a segment.
_GUEST_VOICE_POOL: tuple[str, ...] = (
    "guest_one",
    "guest_two",
    "guest_three",
    "guest_four",
)


@dataclass(frozen=True)
class Guest:
    """One non-host speaker for one segment: who, in which voice, and the brief."""

    label: str  # the speaker label in the script ("Tessa Aru" or "Guest")
    voice: str  # a logical voice from the registry (never a vendor id)
    kind: str  # "figure" (a D10 soundbite) | "invited" (a one-off persona)
    brief: str  # what the room is told: bio + the quote, or the invitation


def _pool_voices() -> list[str]:
    """The pool entries that actually exist in the voice registry (fail-soft)."""
    known = tts.known_voices()
    voices = [v for v in _GUEST_VOICE_POOL if v in known]
    missing = [v for v in _GUEST_VOICE_POOL if v not in known]
    if missing:
        log.warning("guest_pool_voices_missing", missing=missing)
    return voices


def _stable_voice(key: str, pool: list[str]) -> str:
    """A pool voice by stable hash of `key` — same figure, same voice, every time."""
    return pool[zlib.crc32(key.encode("utf-8")) % len(pool)]


def maybe_guest(ctx: AssembledContext, now: datetime, fmt: str) -> Guest | None:
    """Decide whether this segment carries a guest, and who — None for host-only.

    Sparse by design: a deterministic air-time-seeded draw against
    `settings.convo_guest_chance` (same slot → same decision; unit-checkable, the
    selector-jitter pattern). Only the `talk` format carries guests. When the
    context has attributable quotes (D10.2), the newest pair becomes a FIGURE
    soundbite — world-grounded; otherwise the room invites a one-off persona.
    """
    if not settings.convo_guest_enabled or fmt != "talk":
        return None
    if (
        random.Random(f"guest-{now.isoformat()}").random()
        >= settings.convo_guest_chance
    ):
        return None
    pool = _pool_voices()
    if not pool:
        log.warning("guest_no_pool_voices")
        return None

    if ctx.quotes:
        quote, figure = ctx.quotes[0]
        voice = figure.voice_id if figure.voice_id in tts.known_voices() else None
        if figure.voice_id and voice is None:
            log.warning(
                "guest_figure_voice_unknown",
                figure=figure.id,
                voice_id=figure.voice_id,
            )
        voice = voice or _stable_voice(figure.id, pool)
        stance = f" (said {quote.stance})" if quote.stance else ""
        brief = (
            f"{figure.name}, {figure.role}. {figure.card_text}\n"
            f'What they said{stance}: "{quote.text}"'
        )
        log.info("guest_selected", kind="figure", figure=figure.id, voice=voice)
        return Guest(label=figure.name, voice=voice, kind="figure", brief=brief)

    voice = _stable_voice(now.isoformat(), pool)
    log.info("guest_selected", kind="invited", voice=voice)
    return Guest(
        label=INVITED_LABEL,
        voice=voice,
        kind="invited",
        brief=(
            "An invited guest joins for this segment: invent ONE fitting "
            "settlement resident (a name and an everyday role), introduced by "
            "the hosts inside the fiction."
        ),
    )

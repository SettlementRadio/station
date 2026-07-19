"""The `talk` program format (PHASE_B_TASKS.md B5) — a two-DJ show, wrapping B4.

Backbone: open → banter on a current event/fact → a natural close. Since D12 the
backbone is POSITIONAL (driven by the slot's `ShowFlow`): a program opens once, the
middle segments come in cold and carry the thread, and it closes once — with a
spoken sign-on/sign-off by program name (D12.4). Talk-first: the backbone does NOT
assume a song follows (a music slot introduces its own track). This is the B4
conversation orchestrator (`writers/conversation.py`) given an explicit structural
directive: the format does not re-implement the writers' room (showrunner → dialogue
→ continuity → two-voice render), it reuses it via `conversation.compose_segment`,
then tags the Segment with the format template.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings
from ..flow import CLOSE, OPEN, ShowFlow
from ..logging_setup import get_logger
from ..segment import Segment
from ..world.context import AssembledContext
from ..writers import conversation
from . import common

log = get_logger(__name__)

# TALK-FIRST (D12.4): the backbones do NOT assume a song follows. Settlement Radio
# is mostly talk — a music slot is occasional and introduces its OWN track
# (formats/music.py), and news/breaks introduce themselves — so a talk segment ends
# on its content, never on a promise of "…and now some music" that a talk→talk
# hand-off would break. (Intra-show "coming up…" sign-posting, which needs reliable
# next-slot look-ahead, is deferred to Phase E per the D12.4 scope gate.)

# The STANDALONE backbone (flow=None, or D12 disabled): a complete little segment
# that opens AND closes — for the direct B4/B5 paths and a lone slot. Handed to the
# B4 orchestrator as its `extra_directive`.
_BACKBONE_STANDALONE = (
    "Open warmly; let the two of you banter and build on a single current event "
    "or world fact; then a short, natural close. Keep the settlement-time check near "
    "the open or the handover."
)

# D12.1 — POSITIONAL backbones for a flowing show. The scheduler tells us where this
# slot sits in its program run (D12.0's `flow`); each shape drops the redundant
# open/close so consecutive segments read as ONE show, not N mini-shows. The
# settlement-time check is left OUT of these strings — the orchestrator decides when
# a time-check is allowed (positional + `convo_flow_timecheck`), so it lives in one
# place. Tunable constants, not scattered literals (config.py convention).
_BACKBONE_OPEN = (
    "This segment OPENS the show. Open warmly and set the tone, then let the two of "
    "you banter and build on a single current event or world fact. Do NOT sign off, "
    "close, or say goodbye — the show continues after this."
)
_BACKBONE_CONTINUE = (
    "This is the MIDDLE of a show already in progress — the two of you never left "
    "the booth. Do NOT greet the audience, re-introduce yourselves or the topic, or "
    "open the show again: come in COLD, mid-thought, as if picking back up "
    "('…anyway, the thing about that is…'). Banter and build on a single current "
    "event or world fact, then carry the thread on — do NOT sign off, the show keeps "
    "going."
)
_BACKBONE_CLOSE = (
    "This segment CLOSES the show. Come in COLD (no fresh greeting — you've been on "
    "air all along), have a last exchange on a single current event or world fact, "
    "then give a genuine, warm close and sign-off — this is the end of the show."
)


# R2.3 — the SHORT-fixture tightening (flow.short_show): at the GRID_V2 density a
# 30-minute show that spends a minute on hellos has spent 5% of itself. One line
# each way; the 2h flagships keep the fuller welcome.
_SIGNON_SHORT = (
    " Keep the sign-on to ONE short line — name the programme and get straight to "
    "the item; no ceremony, no table-setting, no run-down of what's coming."
)
_SIGNOFF_SHORT = (
    " Keep the sign-off to ONE short line — name the programme, hand on, done; "
    "no recap, no long goodbyes."
)


def _signon_backbone(program_name: str | None, *, short: bool = False) -> str:
    """The `open` backbone, with a D12.4 SIGN-ON by name when the program is known."""
    if not program_name:
        return _BACKBONE_OPEN
    return (
        f"{_BACKBONE_OPEN} As you open, SIGN ON the programme by name — welcome the "
        f'listeners to "{program_name}" naturally, in your own words (not a jingle), '
        "just once." + (_SIGNON_SHORT if short else "")
    )


def _signoff_backbone(program_name: str | None, *, short: bool = False) -> str:
    """The `close` backbone, with a D12.4 SIGN-OFF by name when the program is known."""
    if not program_name:
        return _BACKBONE_CLOSE
    return (
        f"{_BACKBONE_CLOSE} As you close, SIGN OFF the programme by name — a warm "
        f'"that\'s \\"{program_name}\\" for now" beat, just once.'
        + (_SIGNOFF_SHORT if short else "")
    )


def _backbone_for(flow: ShowFlow | None) -> str:
    """The structural backbone for this slot's show position (D12.1 + D12.4).

    Standalone (no `flow`) or the D12 rollback (`convo_continuity_enabled=False`)
    keeps the self-contained open→close shape; otherwise the positional backbone for
    `flow.position` drives one open at the top, cold middles, and one close. On the
    `open`/`close` slots, D12.4 signs the program ON/OFF by name (when
    `convo_flow_signon` is on and the program name is known), tightened to ONE line
    for a short fixture (R2.3 — `flow.short_show`).
    """
    if flow is None or not settings.convo_continuity_enabled:
        return _BACKBONE_STANDALONE
    name = flow.program_name if settings.convo_flow_signon else None
    if flow.position == OPEN:
        return _signon_backbone(name, short=flow.short_show)
    if flow.position == CLOSE:
        return _signoff_backbone(name, short=flow.short_show)
    return _BACKBONE_CONTINUE


def talk(now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None) -> Segment:
    """Generate one two-DJ talk `Segment` for `now` on a position-aware backbone.

    `flow` (D12.0) carries the slot's show position + the prior talk hand-off. D12.1
    makes the backbone POSITIONAL from it — `open` opens, `continue` is cold-in/
    cold-out, `close` closes — and hands `flow` on to `compose_segment` so the
    orchestrator's time-check is positional too. `None` (the direct B5 path, or a
    lone slot) keeps the standalone open→close shape.
    """
    seg_id = common.make_seg_id("talk", now)
    log.info(
        "format_talk_start",
        seg_id=seg_id,
        speakers=[c.id for c in ctx.speakers],
        flow_position=flow.position if flow is not None else None,
    )
    seg = conversation.compose_segment(
        ctx,
        now,
        seg_id=seg_id,
        # R2.2 — the program's own item length (grid `talk_length_sec`, riding the
        # flow): a flagship's fast 3-5-min items vs a specialist's 6-8. None keeps
        # the global default (the direct B4/B5 paths are unchanged).
        length_target_sec=(flow.talk_length_sec if flow is not None else None),
        extra_directive=_backbone_for(flow),
        flow=flow,
    )
    seg.meta["format_template"] = "talk"
    log.info("format_talk_done", seg_id=seg_id, turns=seg.meta.get("turns"))
    return seg

"""The `talk` program format (PHASE_B_TASKS.md B5) — a two-DJ show, wrapping B4.

Backbone: open → banter on a current event/fact → a music lead-in line → close.
This is the B4 conversation orchestrator (`writers/conversation.py`) given an
explicit structural directive: the format does not re-implement the writers' room
(showrunner → dialogue → continuity → two-voice render), it reuses it via
`conversation.compose_segment`, then tags the Segment with the format template.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings
from ..flow import CLOSE, CONTINUE, OPEN, ShowFlow
from ..logging_setup import get_logger
from ..segment import Segment
from ..world.context import AssembledContext
from ..writers import conversation
from . import common

log = get_logger(__name__)

# The STANDALONE backbone (flow=None, or D12 disabled): a complete little segment
# that opens AND closes — today's shape, kept for the direct B4/B5 paths and a lone
# slot. Handed to the B4 orchestrator as its `extra_directive`.
_BACKBONE_STANDALONE = (
    "Open warmly; let the two of you banter and build on a single current event "
    "or world fact; slide into a natural lead-in to a piece of music (described "
    "in-world, not named); then a short close. Keep the settlement-time check near "
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
    "you banter and build on a single current event or world fact; slide into a "
    "natural lead-in to a piece of music (described in-world, not named). Do NOT "
    "sign off, close, or say goodbye — the show continues after this."
)
_BACKBONE_CONTINUE = (
    "This is the MIDDLE of a show already in progress — the two of you never left "
    "the booth. Do NOT greet the audience, re-introduce yourselves or the topic, or "
    "open the show again: come in COLD, mid-thought, as if picking back up after a "
    "song ('…anyway, the thing about that is…'). Banter and build on a single "
    "current event or world fact, then slide into a natural in-world music lead-in "
    "and hand off WITHOUT signing off — no goodbye, the show keeps going."
)
_BACKBONE_CLOSE = (
    "This segment CLOSES the show. Come in COLD (no fresh greeting — you've been on "
    "air all along), have a last exchange on a single current event or world fact, "
    "slide into a final in-world music lead-in, then give a genuine, warm close and "
    "sign-off — this is the end of the show."
)

_POSITIONAL_BACKBONES = {
    OPEN: _BACKBONE_OPEN,
    CONTINUE: _BACKBONE_CONTINUE,
    CLOSE: _BACKBONE_CLOSE,
}


def _backbone_for(flow: ShowFlow | None) -> str:
    """The structural backbone for this slot's show position (D12.1).

    Standalone (no `flow`) or the D12 rollback (`convo_continuity_enabled=False`)
    keeps the self-contained open→close shape; otherwise the positional backbone for
    `flow.position` drives one open at the top, cold middles, and one close.
    """
    if flow is None or not settings.convo_continuity_enabled:
        return _BACKBONE_STANDALONE
    return _POSITIONAL_BACKBONES.get(flow.position, _BACKBONE_STANDALONE)


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
        ctx, now, seg_id=seg_id, extra_directive=_backbone_for(flow), flow=flow
    )
    seg.meta["format_template"] = "talk"
    log.info("format_talk_done", seg_id=seg_id, turns=seg.meta.get("turns"))
    return seg

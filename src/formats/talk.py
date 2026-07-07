"""The `talk` program format (PHASE_B_TASKS.md B5) — a two-DJ show, wrapping B4.

Backbone: open → banter on a current event/fact → a music lead-in line → close.
This is the B4 conversation orchestrator (`writers/conversation.py`) given an
explicit structural directive: the format does not re-implement the writers' room
(showrunner → dialogue → continuity → two-voice render), it reuses it via
`conversation.compose_segment`, then tags the Segment with the format template.
"""

from __future__ import annotations

from datetime import datetime

from ..flow import ShowFlow
from ..logging_setup import get_logger
from ..segment import Segment
from ..world.context import AssembledContext
from ..writers import conversation
from . import common

log = get_logger(__name__)

# The structural backbone handed to the B4 orchestrator as its `extra_directive`.
_BACKBONE = (
    "Open warmly; let the two of you banter and build on a single current event "
    "or world fact; slide into a natural lead-in to a piece of music (described "
    "in-world, not named); then a short close. Keep the settlement-time check near "
    "the open or the handover."
)


def talk(now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None) -> Segment:
    """Generate one two-DJ talk `Segment` for `now` on the open→…→close backbone.

    `flow` (D12.0) carries the slot's show position + the prior talk hand-off; it is
    handed to `compose_segment` for the writers' room. `None` keeps the standalone
    open→close shape (the direct B5 path). D12.0 only threads it — the positional
    backbone (D12.1) and thread continuation (D12.2) read it in later tasks.
    """
    seg_id = common.make_seg_id("talk", now)
    log.info("format_talk_start", seg_id=seg_id, speakers=[c.id for c in ctx.speakers])
    seg = conversation.compose_segment(
        ctx, now, seg_id=seg_id, extra_directive=_BACKBONE, flow=flow
    )
    seg.meta["format_template"] = "talk"
    log.info("format_talk_done", seg_id=seg_id, turns=seg.meta.get("turns"))
    return seg

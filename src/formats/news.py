"""The `news` program format (PHASE_B_TASKS.md B5) — a single-DJ news desk.

Backbone: a short news sting/desk open → exactly N in-world headlines derived from
the current events → a brief sign-off. One DJ, one Claude call, one render.

Unlike the `talk` format, news is *reportage*: it is fine — expected — for the
anchor to state what happened plainly. The anti-recitation rule that governs the
two-DJ conversation does NOT apply here. The headlines are grounded in the events
near `now` (with their live relative phrasing from `events.py`); when there are
fewer than N, the anchor extends with plausible, canon-consistent settlement
happenings — never real-world news.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm
from ..segment import Segment
from ..world import clock
from ..world import events as events_mod
from ..world.context import AssembledContext
from ..writer import safety_check
from . import common

log = get_logger(__name__)


def _headlines_block(ctx: AssembledContext, now: datetime) -> str:
    """Render the events near `now` as a reportage-ready brief for the anchor."""
    if not ctx.events:
        return "(no scheduled events near now — invent grounded settlement headlines)"
    lines = [
        f"- {e.title} ({events_mod.relative_phrase(e, now)}, {e.status}): {e.body}"
        for e in ctx.events
    ]
    return "\n".join(lines)


def _build_system(ctx: AssembledContext, now: datetime, anchor: str) -> str:
    n = settings.format_news_headline_count
    return (
        "You are the writer for Settlement Radio's news desk, scripting the anchor "
        f"{anchor}. Write the SPOKEN SCRIPT ONLY — exactly the words {anchor} says "
        "aloud, with no stage directions, headings, speaker labels, or notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n\n"
        f"Current events to report on:\n{_headlines_block(ctx, now)}\n\n"
        "Structure (fill this skeleton):\n"
        "  1. A short news sting / desk open — one or two crisp lines that say this "
        "is the settlement news.\n"
        f"  2. Exactly {n} in-world headlines, each a few sentences, derived from "
        "the events above and grounded in the world facts in the cached context. "
        "Vary their weight and tone (one larger story, smaller items). If there are "
        f"fewer than {n} current events, extend with plausible, canon-consistent "
        "settlement happenings.\n"
        "  3. A brief sign-off handing back to the studio.\n\n"
        "This is reportage: stating clearly what is happening is correct here. Keep "
        "every item INSIDE the fiction — never real-world places, brands, franchises, "
        "people, or events; never mention being an AI. "
        f"Target {settings.format_news_words_low}-{settings.format_news_words_high} "
        "words total. Tone: clear, measured, lightly warm — a trusted settlement desk."
    )


def news(now: datetime, ctx: AssembledContext) -> Segment:
    """Generate one single-DJ news `Segment` for `now` from the assembled context."""
    anchor_card = common.require_speaker(ctx, "news")
    seg_id = common.make_seg_id("news", now)
    log.info("format_news_start", seg_id=seg_id, anchor=anchor_card.id)

    system = _build_system(ctx, now, anchor_card.name)
    script = llm.generate(
        "Write the news bulletin now.",
        system=system,
        model=settings.llm_default_tier,
        cached_context=ctx.cached_context,
        max_tokens=settings.format_news_max_tokens,
    )
    script = safety_check(script.strip())

    audio_path = common.render_single_voice([script], anchor_card.logical_voice, seg_id)
    log.info("format_news_done", seg_id=seg_id, words=len(script.split()))
    return Segment(
        id=seg_id,
        format="news",
        length_target_sec=settings.format_news_length_target_sec,
        air_time=now.isoformat(),
        script=script,
        audio_path=audio_path,
        disclosure=True,
        meta={
            "format_template": "news",
            "speaker": anchor_card.id,
            "headline_count": settings.format_news_headline_count,
            "events": [e.id for e in ctx.events],
        },
    )

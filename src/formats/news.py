"""The `news` program format — a story-log-driven news desk (D4.2).

Backbone: a short desk open → the hour's SELECTED stories, each framed by its tag
and beat date → a brief sign-off. One DJ, one Claude call, one render.

D4 turns the old one-shot bulletin (N flat headlines from a date-window, no memory)
into a desk that reads the living world (D3) like a real station. Each hour
`news_select.select_stories` (D4.1) picks a bounded, ranked MIX of running stories —
tagged breaking/trailed/ongoing (where they sit on the clock) and new/repeat/evolve
(how the desk has covered them before, D4.0) — and this producer builds a desk-ready
brief from that, framing each item by its arc stage and its relative temporal phrase
(`events.relative_phrase`: "tonight" / "tomorrow" / "yesterday"). An `evolve` story is
reported as an UPDATE (the delta beat since last coverage), a `repeat` as a light
"still developing" touch — never re-read word-for-word.

Unlike `talk`, news is *reportage*: the anchor states plainly what happened — the
anti-recitation rule that governs the two-DJ conversation does NOT apply here. But it
is reportage in the anchor's ACTUAL VOICE (their card, cached), not wire-service
officialese (the D4 "natural register" carry-over).

The gate + fallback discipline is unchanged (C0): generation is wrapped in
`generate_safe`; a persistent safety flag drops the slot to a safe `evergreen`
segment rather than airing it. After a successful render the desk RECORDS its coverage
(D4.0) of each reported story, so the next bulletin can repeat/evolve/stay consistent.
"""

from __future__ import annotations

from datetime import datetime

from .. import evergreen
from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm
from ..safety import generate_safe
from ..segment import Segment
from ..world import clock, store
from ..world import events as events_mod
from ..world.context import AssembledContext
from . import common, news_select
from .news_select import SelectedStory

log = get_logger(__name__)


# --- The desk brief (the selected stories, framed for the anchor) -----------


def _story_brief(sel: SelectedStory, now: datetime) -> str:
    """One selected story rendered as a framing brief for the anchor.

    Carries the handle, the tags (so the anchor knows whether to trail/report/update),
    the arc stage, and the relevant beat with its natural relative phrase. For an
    `evolve` story it spells out the delta since last coverage so the anchor can say
    "an update on …"; for a `repeat` it says to keep it light.
    """
    s = sel.story
    head = (
        f"• {s.title}  [{sel.temporal_kind} · {sel.coverage_tag} · arc: {s.arc_stage}]"
    )
    lines = [head]

    if sel.coverage_tag == news_select.COVERAGE_EVOLVE:
        delta = sel.new_beat or sel.lead_beat
        if delta is not None:
            phrase = events_mod.relative_phrase(delta, now)
            lines.append(
                f"  - UPDATE (since you last covered this) — {phrase}: "
                f"{delta.title} — {delta.body}"
            )
        else:
            lines.append(
                "  - UPDATE: this story has moved on since you last reported it."
            )
    elif sel.lead_beat is not None:
        phrase = events_mod.relative_phrase(sel.lead_beat, now)
        lines.append(f"  - {phrase}: {sel.lead_beat.title} — {sel.lead_beat.body}")
    else:
        lines.append(f"  - {s.summary}")

    if sel.coverage_tag == news_select.COVERAGE_REPEAT:
        lines.append(
            "  - (no new development since you last reported this — keep it brief, a "
            "'still developing' touch; don't re-read it word for word)"
        )
    return "\n".join(lines)


def _briefs_block(selected: list[SelectedStory], now: datetime) -> str:
    """The selected stories as a framing brief, or the empty-day instruction."""
    if not selected:
        return (
            "(quiet news day — the story log has nothing pressing near now. Give a "
            "short, plausible, canon-consistent settlement update grounded in the "
            "world facts you know; never invent real-world news.)"
        )
    return "\n".join(_story_brief(s, now) for s in selected)


def _build_system(
    ctx: AssembledContext, now: datetime, anchor: str, selected: list[SelectedStory]
) -> str:
    """The per-call system prompt: anchor's voice + the framed stories + the rules."""
    return (
        "You are the writer for Settlement Radio's news desk, scripting the anchor "
        f"{anchor}. Write the SPOKEN SCRIPT ONLY — exactly the words {anchor} says "
        "aloud, with no stage directions, headings, speaker labels, or notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n\n"
        f"Sound unmistakably like {anchor}: lean on the voice, habits, and cadence in "
        "their character card (cached above). This is a real person at the desk who "
        "knows this settlement — not a wire-service reader.\n\n"
        f"The stories to report this hour:\n{_briefs_block(selected, now)}\n\n"
        "How to handle them:\n"
        "  - This is reportage — state plainly what is happening; you may report it "
        "directly (the no-reciting rule is for the two-host show, not the desk).\n"
        "  - Frame each by its time: trail what's coming as upcoming, report what's "
        "happening now as now, refer to what's done as past — use the natural phrases "
        "given (tonight / tomorrow / yesterday).\n"
        "  - An UPDATE item is exactly that: lead it as 'an update on …' and give the "
        "new development, don't re-read the whole story. A 'still developing' item "
        "stays a brief touch. Weight the stories — lead with the biggest, let smaller "
        "ones be shorter.\n\n"
        "Shape: a short desk open (this is the settlement news) → the items above, in "
        "a natural order → a brief sign-off back to the studio. Keep every item INSIDE "
        "the fiction — never real-world places, brands, franchises, people, or events; "
        "never mention being an AI. "
        f"Aim roughly for {settings.format_news_words_low}-"
        f"{settings.format_news_words_high} words; let it breathe — read like spoken "
        "news, not clipped headlines."
    )


# --- Coverage recording (D4.0: remember what this bulletin said) ------------


def _record_coverage(selected: list[SelectedStory], now: datetime) -> None:
    """Record the desk's coverage of each reported story (D4.0), best-effort.

    `covered_at` is the bulletin's IN-WORLD air time (the same timeline as the beats),
    `last_beat_id` the story's newest beat (so the next bulletin's evolve check fires
    only on a genuinely newer beat), and `angle` the handle used — reusing the prior
    handle when there is one, else the story title — so naming stays consistent (D4.3).
    A write failure is logged, never fatal: the segment already rendered.
    """
    if not selected:
        return
    iw_now = clock.to_inworld(now)
    try:
        with store.connect() as conn:
            for sel in selected:
                prior = sel.prior_coverage
                angle = prior.angle if prior and prior.angle else sel.story.title
                last_beat = sel.latest_beat or sel.lead_beat
                store.record_coverage(
                    conn,
                    store.NewsCoverage(
                        story_id=sel.story.id,
                        covered_at=iw_now,
                        arc_stage=sel.story.arc_stage,
                        last_beat_id=last_beat.id if last_beat else None,
                        angle=angle,
                    ),
                )
    except Exception as exc:  # noqa: BLE001 — coverage memory is best-effort
        log.error(
            "format_news_coverage_record_failed",
            error=str(exc),
            stories=[s.story.id for s in selected],
        )


def _coverage_meta(selected: list[SelectedStory]) -> dict:
    """Auditable coverage fields for the Segment meta (which stories, tags, beats)."""
    return {
        "story_count": len(selected),
        "stories": [s.story.id for s in selected],
        "tags": {s.story.id: f"{s.temporal_kind}/{s.coverage_tag}" for s in selected},
        "beats": [s.lead_beat.id for s in selected if s.lead_beat is not None],
    }


def news(now: datetime, ctx: AssembledContext) -> Segment:
    """Generate one story-log-driven news `Segment` for `now` (D4.2)."""
    anchor_card = common.require_speaker(ctx, "news")
    seg_id = common.make_seg_id("news", now)

    # D4.1 — pick + tag the hour's stories from the living world (own short read txn).
    selected = news_select.select_stories(now)
    log.info(
        "format_news_start",
        seg_id=seg_id,
        anchor=anchor_card.id,
        selected=len(selected),
    )

    system = _build_system(ctx, now, anchor_card.name, selected)
    script, safety = generate_safe(
        lambda: llm.generate(
            "Write the news bulletin now.",
            system=system,
            model=settings.llm_default_tier,
            cached_context=ctx.cached_context,
            max_tokens=settings.format_news_max_tokens,
        )
    )
    if not safety.ok:
        # C0: regeneration didn't clear the safety gate — never air the flagged
        # draft; drop this slot to a safe evergreen instead (no coverage recorded).
        log.error("format_news_safety_fallback", seg_id=seg_id, reason=safety.reason)
        return evergreen.evergreen_segment(
            now,
            fmt="news",
            seg_id=seg_id,
            length_target_sec=settings.format_news_length_target_sec,
            reason=f"safety: {safety.reason}",
        )

    audio_path = common.render_single_voice([script], anchor_card.logical_voice, seg_id)

    # D4.0 — remember what aired, so the next bulletin can repeat/evolve consistently.
    _record_coverage(selected, now)

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
            **_coverage_meta(selected),
        },
    )

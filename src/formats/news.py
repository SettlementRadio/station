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

from .. import evergreen, freshness
from ..config import settings
from ..flow import ShowFlow
from ..logging_setup import get_logger
from ..providers import llm
from ..safety import safety_check
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
    lines += _quote_lines(sel, now)
    return "\n".join(lines)


def _quote_lines(sel: SelectedStory, now: datetime) -> list[str]:
    """Attributable quotes for a story's brief (D10.2) — who said what, when.

    Each quote is framed by its own in-world datetime (`events.phrase_for_datetime`), so
    the anchor can say "X, the relay-keeper, said yesterday: …". These are OPTIONAL
    colour: the anchor attributes one or two where they sharpen the report, not all.
    """
    if not sel.quotes:
        return []
    out = ["  - quotes you may attribute (use the ones that sharpen the report):"]
    for quote, figure in sel.quotes:
        phrase = events_mod.phrase_for_datetime(quote.in_world_datetime, now)
        out.append(f'    · {figure.name} ({figure.role}) said {phrase}: "{quote.text}"')
    return out


def _briefs_block(selected: list[SelectedStory], now: datetime) -> str:
    """The selected stories as a framing brief, or the empty-day instruction."""
    if not selected:
        return (
            "(quiet news day — the story log has nothing pressing near now. Give a "
            "short, plausible, canon-consistent settlement update grounded in the "
            "world facts you know; never invent real-world news.)"
        )
    return "\n".join(_story_brief(s, now) for s in selected)


def _continuity_block(selected: list[SelectedStory]) -> str:
    """Prior coverage of the re-reported stories (D4.3) — for consistent naming.

    For each story the desk has aired before, the handle/angle it used and the stage
    it last reported, so a re-report keeps the SAME name and doesn't contradict what
    already went out. Empty (no string) when nothing here has been covered before. The
    SAME block is shown to the writer (to stay consistent) and the continuity editor
    (to check the draft against).
    """
    covered = [s for s in selected if s.prior_coverage is not None]
    if not covered:
        return ""
    lines = []
    for s in covered:
        prior = s.prior_coverage
        handle = prior.angle if prior.angle else s.story.title
        lines.append(
            f"- \"{handle}\": you last reported this at the '{prior.arc_stage}' "
            "stage. Use the SAME name for it, and don't contradict that earlier report."
        )
    return "Continuity — you've reported some of these before:\n" + "\n".join(lines)


def _freshness_section(recent_openings: str) -> str:
    """The D5.2 anti-repetition block for the desk — vary WORDING, not the stories.

    `recent_openings` is recent news openings to avoid (from
    `freshness.recent_openings_block`, scoped to "news"). The note makes the D4-vs-D5
    boundary explicit: repeating a STORY
    across bulletins is intended (D4 drives which stories recur + how they evolve); only
    the WORDING must stay fresh (D5). Empty (no string) on a cold start / when disabled.
    """
    if not recent_openings:
        return ""
    return (
        f"{recent_openings}\n"
        "Repeating a STORY across bulletins is fine and expected — but vary the "
        "WORDING: don't open or phrase a story the way the recent bulletins above "
        "did.\n\n"
    )


def _build_system(
    ctx: AssembledContext,
    now: datetime,
    anchor: str,
    selected: list[SelectedStory],
    *,
    revision_note: str | None = None,
    recent_openings: str = "",
) -> str:
    """The per-call system prompt: anchor's voice + framed stories + continuity + rules.

    `revision_note` (set on a continuity-gate retry) is prepended so the next draft
    fixes the editor's flagged problem (the C0 regenerate-with-the-note path).

    `recent_openings` (D5.2) is the freshness steer — recent news openings to avoid —
    woven in as the `_freshness_section`, in the per-call prompt so the cache still
    hits.
    """
    revision = ""
    if revision_note:
        revision = (
            "A PREVIOUS DRAFT had continuity problems the editor flagged: "
            f"{revision_note}\nFix exactly those — keep the same stories and framing "
            "otherwise.\n\n"
        )
    continuity = _continuity_block(selected)
    continuity_section = f"{continuity}\n\n" if continuity else ""
    freshness_section = _freshness_section(recent_openings)
    return (
        f"{revision}"
        "You are the writer for Settlement Radio's news desk, scripting the anchor "
        f"{anchor}. Write the SPOKEN SCRIPT ONLY — exactly the words {anchor} says "
        "aloud, with no stage directions, headings, speaker labels, or notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n\n"
        f"{anchor} is a professional news anchor: composed, precise, plain-spoken.\n"
        "Register — formal broadcast news. Report the facts directly: who, what, when, "
        "the numbers and the names. Short, clear, declarative sentences. AVOID "
        "metaphor and simile, lyrical or poetic phrasing, editorial 'knowing' asides, "
        "invented studio colour (no recurring archivists pulling up old recordings); "
        "at most one light human note in the whole bulletin. Name the people, "
        "institutions, and places a story is about, and refer to each by the SAME name "
        "every time it comes up.\n\n"
        f"The stories to report this hour:\n{_briefs_block(selected, now)}\n\n"
        f"{continuity_section}"
        f"{freshness_section}"
        "How to handle them:\n"
        "  - This is reportage — state plainly what is happening; you may report it "
        "directly (the no-reciting rule is for the two-host show, not the desk).\n"
        "  - Frame each by its time: trail what's coming as upcoming, report what's "
        "happening now as now, refer to what's done as past — use the natural phrases "
        "given (tonight / tomorrow / yesterday).\n"
        "  - An UPDATE item is exactly that: lead it as 'an update on …' and give the "
        "new development, don't re-read the whole story. A 'still developing' item "
        "stays a brief touch. Weight the stories — lead with the biggest, let smaller "
        "ones be shorter.\n"
        "  - Where a story lists quotes, ATTRIBUTE one or two by name and role and "
        "frame them in time ('the relay-keeper said yesterday: …') — quote the words "
        "given, don't invent new ones; skip quotes that don't add to the report.\n\n"
        "Shape: a short desk open (this is the settlement news) → the items above, in "
        "a natural order → a brief sign-off back to the studio. Keep every item INSIDE "
        "the fiction — never real-world places, brands, franchises, people, or events; "
        "never mention being an AI. "
        f"Aim for {settings.format_news_words_low}-{settings.format_news_words_high} "
        "words — a full bulletin with real substance per story; pace it as a measured "
        "news read, not a summary."
    )


# --- Continuity gate (D4.3: the desk doesn't drift across bulletins) --------


def _is_ok(note: str) -> bool:
    """True when the editor's note signals no problems (starts with 'OK')."""
    return note.strip().upper().startswith("OK")


def _run_continuity(
    script: str, ctx: AssembledContext, selected: list[SelectedStory], tier: str
) -> str:
    """One continuity pass at `tier`; returns the editor's note ('OK' / 'ISSUES…').

    Checks the bulletin against the world bible (cached) and the desk's prior coverage
    of these stories — catching a renamed story, a contradiction of an earlier report,
    or an arc mis-framed (a finished event called upcoming, etc.).
    """
    continuity = _continuity_block(selected)
    prior_section = (
        f"\n\nThe desk's prior coverage:\n{continuity}" if continuity else ""
    )
    system = (
        "You are the continuity editor for Settlement Radio's news desk. Check the "
        "bulletin draft below against the world bible in the cached context and the "
        "desk's prior coverage. Flag ONLY real continuity faults: renaming a story the "
        "desk already named, contradicting an earlier report, mis-framing where a "
        "story sits in its arc (e.g. trailing something already past), or a real-world "
        "/ anachronistic reference. Reply with the single word OK if it is consistent, "
        "otherwise 'ISSUES:' followed by a terse list. Do not rewrite the draft."
        f"{prior_section}"
    )
    note = llm.generate(
        f"Draft to check:\n\n{script}",
        system=system,
        model=tier,
        cached_context=ctx.cached_context,
        max_tokens=settings.news_continuity_max_tokens,
    )
    return note.strip()


def _continuity_check(
    script: str, ctx: AssembledContext, selected: list[SelectedStory]
) -> tuple[bool, str]:
    """Continuity verdict for the bulletin, escalating to confirm a flag (D4.3).

    Runs at `news_continuity_tier`; if that smells a problem, re-checks at
    `news_continuity_escalation_tier` to confirm before the gate spends a retry —
    mirrors the two-DJ gate, sparing a good bulletin a false drop to evergreen.
    Returns `(ok, note)`; the gate in `news()` acts on it.
    """
    tier = settings.news_continuity_tier
    note = _run_continuity(script, ctx, selected, tier)
    ok = _is_ok(note)
    if not ok:
        log.warning("format_news_continuity_flagged", tier=tier, note=note[:300])
        tier = settings.news_continuity_escalation_tier
        note = _run_continuity(script, ctx, selected, tier)
        ok = _is_ok(note)
    log.info("format_news_continuity_done", tier=tier, ok=ok)
    return ok, note


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


def news(now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None) -> Segment:
    """Generate one story-log-driven news `Segment` for `now` (D4.1–D4.3).

    `flow` (D12.0) is accepted for the uniform format seam but unused — news
    continuity is its own coverage memory (D4), not the talk thread (see D12 pack).

    C0 — the GATE. Each attempt's draft must clear BOTH the content-safety check and
    the desk continuity check (against canon + prior coverage). A safety flag re-rolls
    a fresh draft; a continuity flag re-rolls with the editor's note fed back. Bounded
    by `settings.news_continuity_max_attempts`; if no draft clears both, the slot drops
    to an evergreen fallback — a flagged draft is NEVER rendered. Coverage is recorded
    only on a clean render, so the memory reflects what actually aired.
    """
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

    # D5.2 — recent news openings to vary against, read once for this bulletin (the
    # block is stable across this slot's retries). Degrades to "" on a cold start.
    recent_openings = freshness.recent_openings_block(now, "news")

    attempts = settings.news_continuity_max_attempts
    revision_note: str | None = None  # set when a continuity flag should guide a retry
    last_reason = "no draft cleared the gates"
    for attempt in range(1, attempts + 1):
        system = _build_system(
            ctx,
            now,
            anchor_card.name,
            selected,
            revision_note=revision_note,
            recent_openings=recent_openings,
        )
        script = llm.generate(
            "Write the news bulletin now.",
            system=system,
            model=settings.llm_default_tier,
            cached_context=ctx.cached_context,
            max_tokens=settings.format_news_max_tokens,
        ).strip()

        safety = safety_check(script)
        if not safety.ok:
            last_reason = f"safety: {safety.reason}"
            revision_note = None  # a safety flag re-rolls fresh, not note-guided
            log.warning(
                "format_news_safety_flag",
                seg_id=seg_id,
                attempt=attempt,
                reason=safety.reason,
            )
            continue

        cont_ok, cont_note = _continuity_check(script, ctx, selected)
        if not cont_ok:
            last_reason = f"continuity: {cont_note}"
            revision_note = cont_note  # feed the editor's note into the rewrite
            log.warning(
                "format_news_continuity_gate_flag", seg_id=seg_id, attempt=attempt
            )
            continue

        # Both gates cleared — render, record coverage, return.
        audio_path = common.render_single_voice(
            [script], anchor_card.logical_voice, seg_id
        )
        # D4.0 — remember what aired so the next bulletin can repeat/evolve/stay true.
        _record_coverage(selected, now)
        log.info(
            "format_news_done",
            seg_id=seg_id,
            attempt=attempt,
            words=len(script.split()),
        )
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
                "continuity_ok": True,
                **_coverage_meta(selected),
            },
        )

    # No draft cleared both gates — never air a flagged bulletin; drop to evergreen
    # (no coverage recorded, since nothing aired).
    log.error("format_news_gate_fallback", seg_id=seg_id, reason=last_reason)
    return evergreen.evergreen_segment(
        now,
        fmt="news",
        seg_id=seg_id,
        length_target_sec=settings.format_news_length_target_sec,
        reason=last_reason,
    )

"""The two-DJ conversation orchestrator (PHASE_B_TASKS.md B4) — the creative core.

A light "writers' room" that turns the assembled world into one talk `Segment`
where two DJs actually *talk to each other*, in character, glancing off a current
event — not two narrators reciting canon. Three Claude steps, all sharing the same
cached stable core (bible + both cards) so the prompt cache is reused across them:

  1. showrunner   — picks ONE beat/angle from the events near `now`, framed for the
                    actual hour via the clock-driven show frame (C1: night solo /
                    dawn handover / day / dusk handover, never a hardcoded
                    night→first-light). (tier: the default writing brain)
  2. orchestrator — writes the whole exchange in a SINGLE call (both personas in
                    one prompt: cheaper and more coherent than turn-by-turn, per
                    the B4 guidance). Output is speaker-labelled dialogue.
  3. continuity   — one check against canon on `sonnet`; ESCALATES to `opus` only
                    if that pass flags trouble. A real GATE since C0: a flagged
                    draft is regenerated with the editor's note fed back (bounded
                    by `convo_continuity_max_attempts`), then dropped to an
                    evergreen fallback — it never airs the flawed draft.

Every draft also passes the real content-safety gate (`safety.safety_check`, C0):
a safety flag triggers the same regenerate-then-evergreen path. Rendering voices
each turn separately — so each DJ gets their own logical voice — then stitches the
turns into one mp3 via `tts.concat_audio`.

Anti-recitation is baked into the orchestrator prompt: the facts are the DJs'
*shared knowledge to reference naturally*, never to explain to each other.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime

from .. import evergreen, freshness
from ..config import settings
from ..flow import CONTINUE, OPEN, ShowFlow
from ..logging_setup import get_logger
from ..providers import llm, tts
from ..safety import safety_check
from ..segment import Segment
from ..world import clock, context, framing, programming
from ..world.context import AssembledContext
from ..world.framing import ShowFrame
from ..world.store import CastMember
from . import guest as guest_mod
from . import memory as memory_mod
from .guest import Guest

log = get_logger(__name__)


@dataclass(frozen=True)
class Turn:
    """One spoken turn in the dialogue: who says it, in which voice, and what."""

    speaker: str  # the DJ's display name (e.g. "Vell")
    voice: str  # the logical voice name (e.g. "vell_night") for the TTS seam
    text: str  # the spoken words for this turn
    # D9.0 — optional logical emotion for THIS turn (from tts.EMOTIONS), set by
    # the orchestrator's `Name [emotion]:` tag; None falls back to the segment's
    # daypart default, then settings.tts_emotion_default, then engine default.
    emotion: str | None = None


# D9.0 — the per-segment DEFAULT emotion by daypart (the programme's mood
# floor): an un-tagged turn renders with this hour's mood instead of a flat
# engine default. Deliberately gentle — warm nights, bright mornings, neutral
# daylight (absent = engine default); per-LINE feeling comes from the
# orchestrator's [tags]. Keys are framing.part_of_day labels. Domain constant,
# not config (config.py convention #1); the operator's global override is
# `settings.tts_emotion_default`. Audible only on the flagship engine (C6).
_PART_OF_DAY_EMOTION: dict[str, str] = {
    "deep night": "warm",
    "late night": "warm",
    "first light": "bright",
    "morning": "bright",
    "nightfall": "warm",
}


@dataclass(frozen=True)
class ContinuityResult:
    """The continuity editor's verdict on a draft (advisory in B4)."""

    ok: bool
    tier: str  # which model tier produced this verdict ("sonnet" | "opus")
    note: str  # the editor's note ("OK" or "ISSUES: …")


# --- The show frame (C1): who's on air this hour, framed from the clock -------


def _frame_for(ctx: AssembledContext, now: datetime) -> ShowFrame:
    """The show frame for `now`, driven by the active program (D6.1).

    `programming.program_for(now)` reads the weekly grid and returns the show on air
    this slot — its hosts (lead-first) and framing hint — and `framing.program_frame`
    turns that into the `ShowFrame` (who anchors, who's alongside, is-it-a-handover,
    the situation prose). The reserved `default` program's `legacy` framing routes
    back through the C1 two-host `show_frame`, so with the initial grid (the two
    hosts) — or no grid at all — the frame is exactly what it was before D6.

    Field hosts (the audit fix): any assembled speaker whose card says
    `Based: field` is passed as `remote`, so the frame's situation prose casts
    them as a relay dispatch instead of an in-studio presence.
    """
    program = programming.program_for(now)
    remote = tuple(c.id for c in ctx.speakers if c.is_field)
    return framing.program_frame(now, program, remote=remote)


def _situation(frame: ShowFrame, ctx: AssembledContext) -> str:
    """Resolve the frame's prose situation with the hosts' display names."""
    return framing.resolve_situation(frame, {c.id: c.name for c in ctx.speakers})


# --- Step 1: showrunner -----------------------------------------------------


def _showrunner_thread(flow: ShowFlow | None) -> tuple[str, str]:
    """The showrunner's D12.2 thread context + task, for `(thread_block, task_block)`.

    Three cases: continue the ongoing thread (deepen the SAME beat), transition off a
    thread that has run its course (a deliberate move to a fresh subject), or the
    normal fresh pick (a lone slot, an open, or no active thread). Standalone /
    disabled always takes the fresh pick, so the direct paths are unchanged.
    """
    fresh_task = (
        "Pick exactly ONE current event or world fact for them to glance off, and a "
        "HUMAN angle — a feeling, a small concrete detail, a gentle disagreement, "
        "something one of them can't stop thinking about — not just a fact to report. "
        "The angle should suit both hosts AND the time of day above; do not assume "
        "night, morning, or a handover unless the time and the on-air note say so. "
        "Reply with a SHORT brief (2-4 sentences): the topic, the human angle, and "
        "who opens. Do not write any dialogue."
    )
    if flow is None or not settings.convo_continuity_enabled or flow.handoff is None:
        return "", fresh_task
    ho = flow.handoff
    if flow.continue_thread:
        thread_block = (
            "CONTINUE the on-air conversation already in progress — the hosts have not "
            "changed the subject. The thread so far:\n"
            f"  topic: {ho.topic or '(the previous exchange)'}\n"
            f"  they just said:\n{ho.tail}\n\n"
        )
        task_block = (
            "Give the NEXT beat on THIS SAME thread: deepen it, follow where it just "
            "went, or take the next angle — do NOT open a new topic. Reply with a "
            "SHORT brief (2-4 sentences): the next angle, the human hook, and who "
            "picks it back up. Do not write any dialogue."
        )
        return thread_block, task_block
    # The thread has run its course (spent, or the pacing budget is up) — move on.
    thread_block = (
        "The hosts have been on one thread for a while "
        f'("{ho.topic or "the last subject"}"). It has run its course: move ON to a '
        "FRESH subject now — a natural, deliberate transition, not a jarring reset.\n\n"
    )
    return thread_block, fresh_task


def showrunner(
    ctx: AssembledContext,
    now: datetime,
    *,
    frame: ShowFrame | None = None,
    recent_block: str = "",
    flow: ShowFlow | None = None,
) -> str:
    """Pick tonight's beat: ONE event/angle for the two DJs, framed for the hour.

    Returns a short brief (a few sentences), not dialogue — the orchestrator turns
    it into the exchange. The cached core (both cards) rides along so the beat fits
    these two personalities; the dynamic events/canon go in the per-call system.
    `frame` is the C1 show frame (computed once by `compose_segment`); if omitted it
    is derived from `now`, so the beat is framed for the actual time of day.

    `recent_block` (D5.2) is the anti-repetition steer — recently-aired topics/angles
    to avoid re-picking, from the airplay memory (`freshness.recent_topics_block`). It
    goes in the per-call system (not the cached core), so the cache still hits; empty on
    a cold start, in which case the showrunner picks freely as before.

    `flow` (D12.2) carries the talk hand-off + thread-pacing decision. When the slot
    should CONTINUE the prior thread the showrunner deepens the SAME beat instead of
    picking a fresh one; when the thread is spent / the pacing budget is up it
    transitions deliberately to a new subject; `None` (direct paths) always picks
    fresh.
    """
    names = _names(ctx)
    frame = frame or _frame_for(ctx, now)
    situation = _situation(frame, ctx)
    freshness_section = f"{recent_block}\n\n" if recent_block else ""
    thread_block, task_block = _showrunner_thread(flow)
    system = (
        "You are the showrunner for Settlement Radio, a tribute sci-fi radio "
        f"station. Choose the beat for a short on-air exchange between {names}.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)} "
        f"({frame.part_of_day}).\n"
        f"On air right now: {situation}.\n\n"
        f"What's true right now:\n{ctx.dynamic or '(nothing notable)'}\n\n"
        f"{thread_block}"
        f"{freshness_section}"
        f"{task_block}"
    )
    beat = llm.generate(
        "Pick tonight's beat.",
        system=system,
        model=settings.llm_default_tier,
        bible=ctx.bible,
        cards=ctx.cards_block,
        max_tokens=settings.convo_showrunner_max_tokens,
    )
    beat = beat.strip()
    log.info(
        "convo_showrunner_done",
        chars=len(beat),
        continue_thread=(flow.continue_thread if flow is not None else None),
    )
    return beat


# --- Step 2: orchestrator ---------------------------------------------------

# D12.1 — a talk slot airing within this many minutes of the top of the hour counts
# as "the top of the hour" for the `hourly` time-check policy. A domain constant
# (config.py convention): the schedule places slots back-to-back, so this is a
# tolerance, not an operator dial.
_TOP_OF_HOUR_WINDOW_MIN = 5


def _timecheck_allowed(position: str | None, frame: ShowFrame, now: datetime) -> bool:
    """Whether a spoken settlement-time check is allowed for this positional slot.

    Driven by `settings.convo_flow_timecheck` (never|handover|open|hourly). A dawn/
    dusk handover always time-stamps (that IS the moment); otherwise only an `open`
    slot (open/hourly), or a slot near the top of the hour (hourly), qualifies — a
    cold `continue`/`close` slot mid-show never does.
    """
    policy = settings.convo_flow_timecheck
    if policy == "never":
        return False
    if frame.is_handover:
        return True
    if policy == "handover":
        return False
    if position == OPEN:
        return True
    if policy == "hourly" and now.minute < _TOP_OF_HOUR_WINDOW_MIN:
        return True
    return False


def _timecheck_shown(frame: ShowFrame, flow: ShowFlow | None, now: datetime) -> bool:
    """Whether to HAND the room the exact clock time (else only the part of day).

    Standalone / the D12 rollback keeps the exact time (pre-D12). With a position the
    exact clock is shown only when a time-check is ALLOWED — so a cold `continue` slot
    isn't tempted to state a time it was just told not to (D12.1 fix).
    """
    if flow is None or not settings.convo_continuity_enabled:
        return True
    return _timecheck_allowed(flow.position, frame, now)


def _time_check_directive(
    frame: ShowFrame, flow: ShowFlow | None, now: datetime
) -> str:
    """The settlement-time-check instruction for the orchestrator (D12.1).

    Standalone (no `flow`) or the D12 rollback keeps the pre-D12 behaviour — always a
    time check, near the handover or the open. With a position, the check is included
    only where the policy allows; elsewhere the orchestrator is told NOT to time-stamp
    (it's mid-show, the hour was already established), which is what stops every
    consecutive segment restarting with "it's X hour".
    """
    if flow is None or not settings.convo_continuity_enabled:
        return (
            "A real time check ('settlement time') belongs near the handover."
            if frame.is_handover
            else "A real time check ('settlement time') belongs near the open."
        )
    if _timecheck_allowed(flow.position, frame, now):
        where = "the handover" if frame.is_handover else "the open"
        return f"A real time check ('settlement time') belongs near {where}."
    return (
        "Do NOT give a settlement-time check or state the clock time here — you're "
        "mid-show, the hour is already established. Even if this host usually opens "
        "with the time, come in COLD instead and keep the conversation going."
    )


def _pickup_section(flow: ShowFlow | None) -> str:
    """The D12.2 'pick up where you left off' block for a continuing `continue` slot.

    Only fires on a `continue` slot that is actually CONTINUING a thread (a real
    hand-off, within the pacing budget): the hosts open by carrying the prior
    exchange forward, not re-introducing the topic or themselves. Empty otherwise —
    an `open` starts fresh, a `close` has its own wrap backbone, and a transition /
    missing hand-off degrades to the cold soft-open the backbone already gives (no
    'welcome back', never a broken reference to a segment that didn't air).
    """
    if (
        flow is None
        or not settings.convo_continuity_enabled
        or flow.handoff is None
        or flow.position != CONTINUE
        or not flow.continue_thread
    ):
        return ""
    return (
        "PICK UP where you left off — this is the SAME conversation continuing, you "
        "never left the booth. Do NOT re-introduce the topic or yourselves and do NOT "
        "greet the audience. The last thing said was:\n"
        f"{flow.handoff.tail}\n"
        "Open by carrying that straight forward — a reaction, the next thought, a "
        "callback — then move the thread on.\n\n"
    )


def orchestrate(
    ctx: AssembledContext,
    beat: str,
    now: datetime,
    *,
    frame: ShowFrame | None = None,
    extra_directive: str | None = None,
    revision_note: str | None = None,
    recent_openings: str = "",
    guest: Guest | None = None,
    memory: str = "",
    flow: ShowFlow | None = None,
) -> str:
    """Write the two-DJ exchange in one call; return speaker-labelled dialogue.

    `frame` is the C1 show frame (the on-air situation for the hour); if omitted it
    is derived from `now`, so the dialogue is framed for the actual time of day
    instead of a hardcoded night→first-light handover.

    `extra_directive` is an optional structural instruction (e.g. the B5 `talk`
    format's open → banter → music lead-in → close backbone). It is woven in
    before the format rules; `None` keeps the default shape.

    `revision_note` (C0) carries the continuity editor's complaint from a rejected
    draft, so the rewrite fixes the named problem rather than re-rolling blind.

    `recent_openings` (D5.2) is the anti-repetition steer for the FIRST line — recent
    talk openings to NOT start like (from `freshness.recent_openings_block`). Woven in
    beside the beat (the reserved injection point below), in the per-call system so the
    cache still hits; empty on a cold start.

    `guest` (D9.3) is an optional non-host speaker for THIS segment — a figure
    soundbite or an invited persona (see `writers/guest.py`). The prompt tells the
    room to weave them in, bracketed by the hosts; None keeps the host-only shape.

    `memory` (D9.4) is the pre-rendered "what the hosts remember" block
    (`writers/memory.py`) — each host's lived history from the story log, joined
    to their card. Small + variable, so it rides HERE in the per-call system (the
    cache lever holds); "" keeps the memory-less shape.

    `flow` (D12.1/D12.2) is the slot's show position + talk thread. It makes the
    spoken settlement-time check POSITIONAL — dropped on cold `continue`/`close`
    slots so a flowing show doesn't restate the hour every segment (D12.1). On a
    `continue` slot that is CONTINUING a thread it also opens by picking up the prior
    exchange instead of re-introducing the topic (D12.2). `None` (the direct paths)
    keeps the pre-D12 always-a-time-check-near-open/handover, self-contained shape.
    """
    names = _names(ctx)
    labels = [f"{c.name}:" for c in ctx.speakers]
    if guest is not None:
        labels.append(f"{guest.label}:")
    label_help = " / ".join(labels)
    emotion_help = ", ".join(sorted(tts.EMOTIONS))  # D9.0: the allowed tag set
    guest_section = _guest_section(guest)
    dispatch_section = _dispatch_section(ctx)
    frame = frame or _frame_for(ctx, now)
    situation = _situation(frame, ctx)
    backbone = (
        f"Follow this shape for the exchange:\n{extra_directive}\n\n"
        if extra_directive
        else ""
    )
    revision = (
        "IMPORTANT — a previous draft was rejected by the continuity editor for "
        f"this reason; fix it in this rewrite:\n{revision_note}\n\n"
        if revision_note
        else ""
    )
    time_check = _time_check_directive(frame, flow, now)
    # --- Delivery register lives HERE (the on-air "way they speak"); the persona
    # itself lives in the cast cards (docs/canon/90-cast.md). Future Phase D packs
    # SLOT THEIR INPUTS INTO this prompt — they don't replace it — so keep the
    # showrunner→orchestrate→continuity structure intact as their injection points:
    #   * D5 (freshness): a "don't circle topics/openings aired recently: …" line
    #     from the recent-airplay memory, woven in beside the beat. [BUILT — D5.2:
    #     showrunner takes recent topics; orchestrate takes recent openings here.]
    #   * D9 (DJ memory): each host's history from the event log, joined to their card.
    #     [BUILT — D9.4: the `memory` block below, rendered by writers/memory.py.]
    #   * D10 (figures/quotes): an attributable quote a host can reference.
    freshness_section = f"{recent_openings}\n\n" if recent_openings else ""
    pickup = _pickup_section(flow)
    # D12.1 fix — only HAND the room the exact clock time when a time-check is allowed
    # (open/handover/hourly). On a cold `continue` slot we tell it not to time-stamp,
    # so showing "Settlement time right now: 2:14" (and a night card that opens with the
    # time) fights that — hide the clock, give only the part of day.
    if _timecheck_shown(frame, flow, now):
        time_line = (
            f"Settlement time right now: {clock.render_wall_clock(now)} "
            f"({frame.part_of_day}).\n"
        )
    else:
        time_line = (
            f"It is {frame.part_of_day} (you are mid-show — do NOT state the clock "
            "time or open with it, even if this host usually would).\n"
        )
    system = (
        "You are the writers' room for Settlement Radio, scripting a SPOKEN "
        f"on-air exchange between two hosts — {names}. Write the dialogue ONLY.\n\n"
        f"{time_line}"
        f"On air right now: {situation}. Frame the exchange for THIS part of day — "
        "match the on-air note above; do not write a night or dawn-handover scene "
        "unless it says so.\n\n"
        f"Tonight's beat (from the showrunner):\n{beat}\n\n"
        f"{pickup}"
        f"{freshness_section}"
        f"What's true right now:\n{ctx.dynamic or '(nothing notable)'}\n\n"
        f"{memory}"
        f"{guest_section}"
        f"{dispatch_section}"
        "Write a REAL conversation — two people who've shared this booth for years "
        "and are easy with each other, NOT two narrators taking turns. Make it sound "
        "spoken, not written:\n"
        "- Use contractions and plain, everyday phrasing; let lines run on or trail "
        "off the way real speech does.\n"
        "- Vary the rhythm: some turns are a quick reaction or half a sentence, some "
        "longer; they interrupt, agree, tease, think out loud, leave small silences "
        "implied.\n"
        "- They genuinely react to and build on what the other JUST said — pick up a "
        "word, push back gently, finish each other's thought.\n"
        "- Each sounds unmistakably like THEMSELVES: lean on the verbal tics, habits, "
        "and cadence in their character card (cached above), matching the feel of "
        "that card's sample lines. They are NOT interchangeable.\n\n"
        "The world facts and the event are their SHARED knowledge — reference them "
        "the way colleagues do: a glance, an in-joke, an assumption, a half-finished "
        "reference. Don't explain or recite canon to each other, and don't narrate "
        f"the setting. {time_check}\n\n"
        "Let it breathe — a natural rhythm matters more than an exact length; aim "
        f"roughly for {settings.convo_words_low}-{settings.convo_words_high} words "
        "total across both voices.\n\n"
        f"{revision}"
        f"{backbone}"
        "FORMAT (strict): every line is one turn, prefixed with the speaker's name "
        f"and a colon — {label_help} — then the words they say. When a line clearly "
        "carries ONE strong feeling, you MAY add an emotion tag in square brackets "
        "between the name and the colon — e.g. `Vell [somber]:` — chosen ONLY from: "
        f"{emotion_help}. Most lines take no tag; use a few per exchange at most. "
        "Alternate between "
        "them. No stage directions, no parentheticals, no narration, no headings, "
        "no blank-line markers. Stay entirely inside the fiction: never mention "
        "being an AI, never reference real-world brands, franchises, or people."
    )
    script = llm.generate(
        "Write the exchange now.",
        system=system,
        model=settings.llm_default_tier,
        bible=ctx.bible,
        cards=ctx.cards_block,
        max_tokens=settings.convo_max_tokens,
    )
    script = script.strip()
    log.info("convo_orchestrate_done", chars=len(script))
    return script


def _dispatch_section(ctx: AssembledContext) -> str:
    """The orchestrator prompt block for FIELD-based hosts ('' when all in-studio).

    The audit fix for the field-host conflict: Sera/Orin/Zhe are correspondents
    out among the worlds (`CastMember.based == "field"`), and canon fixes the
    relay lag (78-communication: core hours/days, frontier weeks, dark zones
    months) — so a field host can never trade live banter in the booth. The
    canon-blessed radio form instead: a STITCHED RELAY CORRESPONDENCE — both
    sides really did hear and answer each other, just not in real time, and the
    station assembled the exchange for air. This keeps the full conversational
    quality (it is a genuine back-and-forth) while staying honest about the lag.
    """
    field = [c for c in ctx.speakers if c.is_field]
    if not field:
        return ""
    names = " and ".join(c.name for c in field)
    verb = "are" if len(field) > 1 else "is"
    return (
        f"DISPATCH — {names} {verb} NOT in the studio: they are out among the "
        "worlds, and their side of this exchange crossed the relay lag as "
        "recordings (the lag is a fact of this world: hours to days from the "
        "core, weeks from the frontier, months from the dark zones). Write the "
        "exchange as the station AIRS it — a relay correspondence stitched "
        "together for broadcast: questions travelled out, answers came back, so "
        "both sides genuinely respond to each other and it reads as a real "
        "conversation — but let the seams show once or twice ('by the time you "
        "hear this…', 'when your question reached me…', a nod to how long the "
        "answer took). HARD rules: the field correspondent never claims to be in "
        "the studio and no one treats them as physically present — no shared "
        "objects or space (no handing things over, no galley, no 'come in, "
        "sit'); they name where they're recording from ONCE and stay in that one "
        "place for the whole exchange (travel between worlds takes weeks — they "
        "do not hop worlds between nearby segments; if the recent thread already "
        "placed them somewhere, keep them there). Where anything else in this "
        "brief implies a shared booth, THESE rules win.\n\n"
    )


def _guest_section(guest: Guest | None) -> str:
    """The orchestrator prompt block weaving in a D9.3 guest ('' when none).

    Both shapes keep the hosts in control — a host speaks first and last — and
    keep the guest SHORT (texture, not a takeover). The whole broadcast is
    AI-voiced fiction (the station's disclosure posture); the guest is part of
    that fiction, so the room invents/voices them inside it, never as a real
    person.
    """
    if guest is None:
        return ""
    if guest.kind == "figure":
        return (
            "This segment includes a short SOUNDBITE from someone in the news:\n"
            f"{guest.brief}\n"
            "Weave it in ONCE: a host sets it up in their own words ('here's what "
            f"they said' / 'we have them on the line'), then {guest.label} speaks "
            "1-2 SHORT turns — their actual words, consistent with the quote above "
            "— then the hosts react and move on. The hosts stay in control: a host "
            "opens the exchange and a host closes it; the guest never speaks first "
            f"or last. Label the guest's lines exactly `{guest.label}:`.\n\n"
        )
    return (
        f"This segment includes a brief in-studio interview. {guest.brief}\n"
        "Keep it short and easy: the hosts introduce the guest by name and role, "
        "the guest speaks 2-4 short turns in their own distinct voice (plainer "
        "than the hosts — a resident, not a broadcaster), and a host thanks them "
        "out. The hosts stay in control: a host opens the exchange and a host "
        "closes it; the guest never speaks first or last. Label the guest's lines "
        f"exactly `{guest.label}:`.\n\n"
    )


# --- Step 3: continuity -----------------------------------------------------


def continuity_check(
    script: str, ctx: AssembledContext, *, memory: str = ""
) -> ContinuityResult:
    """Check the draft against canon; escalate to opus only if sonnet flags trouble.

    Returns the verdict; the GATE that acts on it (regenerate with the note, then
    fall back to evergreen) lives in `compose_segment` (C0). The escalation to
    `opus` on a sonnet flag is the confirm step before that gate spends a retry.

    `memory` (D9.4) is the same lived-history block the orchestrator saw — shown
    to the editor so a host MISREMEMBERING a logged story (wrong outcome, wrong
    framing of a resolved arc) flags like any continuity error.
    """
    tier = settings.convo_continuity_tier
    note = _run_continuity(script, ctx, tier, memory)
    ok = _is_ok(note)
    if not ok:
        # The first pass smells a problem — spend a more careful model to confirm.
        log.warning("convo_continuity_flagged", tier=tier, note=note[:300])
        tier = settings.convo_continuity_escalation_tier
        note = _run_continuity(script, ctx, tier, memory)
        ok = _is_ok(note)
    log.info("convo_continuity_done", tier=tier, ok=ok)
    return ContinuityResult(ok=ok, tier=tier, note=note)


def _run_continuity(
    script: str, ctx: AssembledContext, tier: str, memory: str = ""
) -> str:
    """One continuity pass at `tier`; returns the editor's note ('OK' / 'ISSUES…')."""
    memory_block = (
        "The hosts' remembered history from the station log — the draft must not "
        f"contradict or misdate any of it:\n{memory}\n"
        if memory
        else ""
    )
    system = (
        "You are the continuity editor for Settlement Radio. Check the draft below "
        "against the world bible and the character cards in the cached context: any "
        "contradiction of canon, a host acting out of character, a real-world or "
        "anachronistic reference, or info-dumping/reciting facts. A FIELD-based "
        "correspondent (their card says `Based: field`) written as physically in "
        "the studio — sharing objects or space with the studio host, treated as "
        "live in the booth — is a continuity error: the relay lag makes it "
        "impossible; their side must read as a recorded dispatch. Reply with the "
        "single word OK if it is consistent and in character, otherwise 'ISSUES:' "
        "followed by a terse list. Do not rewrite the draft.\n\n"
        f"{memory_block}"
    )
    note = llm.generate(
        f"Draft to check:\n\n{script}",
        system=system,
        model=tier,
        bible=ctx.bible,
        cards=ctx.cards_block,
        max_tokens=settings.convo_continuity_max_tokens,
    )
    return note.strip()


def _is_ok(note: str) -> bool:
    """True when the continuity note signals no problems (starts with 'OK')."""
    return note.strip().upper().startswith("OK")


# --- Turn parsing + rendering -----------------------------------------------


def _tag_emotion(tag: str | None) -> str | None:
    """Validate an orchestrator-emitted `[emotion]` tag against the vocabulary.

    An unknown tag is logged and dropped (the turn renders with the defaults) —
    a stray model invention must never fail a segment.
    """
    if not tag:
        return None
    value = tag.strip().lower()
    if value not in tts.EMOTIONS:
        log.warning("convo_unknown_emotion_tag", tag=tag)
        return None
    return value


def parse_turns(
    script: str, cards: list[CastMember], guest: Guest | None = None
) -> list[Turn]:
    """Split speaker-labelled dialogue into per-voice `Turn`s.

    Recognises lines beginning with a known host name and a colon (tolerating
    surrounding `**bold**` and an optional D9.0 `[emotion]` tag between name and
    colon), and folds any wrapped continuation lines into the current turn.
    Lines before the first recognised label (stray preamble) are dropped. Each
    turn maps to its speaker's logical voice for the TTS seam. `guest` (D9.3)
    adds one recognised non-host label mapped to the guest's own voice.
    """
    # speaker label (lower) -> (display name, logical voice)
    by_name = {c.name.lower(): (c.name, c.logical_voice) for c in cards}
    if guest is not None:
        by_name[guest.label.lower()] = (guest.label, guest.voice)
    names = "|".join(re.escape(name) for name, _voice in by_name.values())
    label_re = re.compile(
        rf"^\s*\*{{0,2}}({names})\*{{0,2}}\s*(?:\[([^\]]+)\])?\s*:\s*(.*)$",
        re.IGNORECASE,
    )

    turns: list[Turn] = []
    cur: tuple[str, str] | None = None  # (display name, logical voice)
    cur_emotion: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if cur is None:
            return
        text = re.sub(r"\*\*", "", " ".join(b.strip() for b in buf)).strip()
        if text:
            turns.append(
                Turn(speaker=cur[0], voice=cur[1], text=text, emotion=cur_emotion)
            )

    for line in script.splitlines():
        m = label_re.match(line)
        if m:
            flush()
            cur = by_name[m.group(1).lower()]
            cur_emotion = _tag_emotion(m.group(2))
            buf = [m.group(3)]
        elif cur is not None and line.strip():
            buf.append(line)
    flush()
    return turns


def _render_turns(
    turns: list[Turn], seg_id: str, *, default_emotion: str | None = None
) -> str:
    """Voice each turn in its own DJ voice, then stitch them into one mp3.

    Returns the path to the stitched segment in `settings.segments_dir`. Per-turn
    clips are written to a temp dir and cleaned up; only the joined segment lands.
    D9.0: a turn's own emotion wins; an un-tagged turn takes `default_emotion`
    (the segment's daypart mood); the settings/engine defaults apply below the
    seam (`tts.resolve_emotion`).
    """
    out_path = settings.segments_dir / f"{seg_id}.mp3"
    tmpdir = tempfile.mkdtemp(prefix=f"{seg_id}-")
    try:
        parts: list[str] = []
        for i, turn in enumerate(turns):
            part = os.path.join(tmpdir, f"{i:03d}.mp3")
            tts.synthesize(
                turn.text,
                voice=turn.voice,
                emotion=turn.emotion or default_emotion,
                out_path=part,
            )
            parts.append(part)
        tts.concat_audio(parts, str(out_path))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return str(out_path)


# --- The whole step: world -> conversation Segment --------------------------


def make_conversation_segment(
    now_iso: str,
    *,
    topic: str | None = None,
    length_target_sec: int | None = None,
) -> Segment:
    """Generate one two-DJ talk Segment for `now_iso`: room → dialogue → audio.

    Args:
        now_iso: current real time (ISO 8601); the in-world clock and event window
            derive from it.
        topic: optional steer for canon retrieval (see `context.assemble`).
        length_target_sec: the DIAL; defaults to the segment default. Metadata
            only here — the spoken length is governed by the word-count guidance.

    Returns:
        A populated talk `Segment` (two voices stitched), with the beat and the
        continuity verdict in `meta`.
    """
    now = datetime.fromisoformat(now_iso)
    log.info("convo_make_segment_start", topic=topic)

    ctx = context.assemble(now, topic=topic, speakers=settings.convo_speaker_ids)
    seg = compose_segment(ctx, now, length_target_sec=length_target_sec)
    # C2: record the measured render length so this direct B4 path is timed on real
    # audio too (the format dispatcher stamps the scheduler's path). A probe failure
    # leaves it None rather than aborting a segment that rendered fine.
    if seg.audio_path:
        try:
            seg.actual_duration_sec = tts.probe_duration(seg.audio_path)
        except Exception as exc:
            log.warning("convo_duration_probe_failed", seg_id=seg.id, error=str(exc))
    return seg


def compose_segment(
    ctx: AssembledContext,
    now: datetime,
    *,
    seg_id: str | None = None,
    length_target_sec: int | None = None,
    extra_directive: str | None = None,
    fmt: str = "talk",
    flow: ShowFlow | None = None,
) -> Segment:
    """Turn an already-assembled context into a two-DJ talk `Segment`.

    The generation core shared by `make_conversation_segment` (B4) and the B5
    `talk` format: showrunner → (orchestrator → safety gate → continuity gate),
    looped → two-voice render. The caller assembles the context (so the speakers
    are already chosen) and may pass a `seg_id`, a `length_target_sec` DIAL, and an
    `extra_directive` (a structural backbone for the orchestrator — the B5 `talk`
    template uses it). `fmt` is the `Segment.format` label.

    `flow` (D12.0) is the show-position + talk hand-off substrate. D12.0 only
    RECORDS it on the segment meta (so it is visible/testable) and does NOT change
    any prompt — the positional backbone (D12.1) and thread continuation (D12.2)
    consume it in later tasks. `None` keeps today's standalone open→close shape.

    C0 — the GATE. Each attempt's draft must clear BOTH gates: the content-safety
    check (`safety.safety_check`) and continuity. A safety flag re-rolls a fresh
    draft; a continuity flag re-rolls with the editor's note fed back. Bounded by
    `settings.convo_continuity_max_attempts`; if no draft clears both, the slot
    drops to an evergreen fallback — a flagged draft is NEVER rendered or returned.
    """
    if length_target_sec is None:
        length_target_sec = settings.segment_default_length_target_sec
    if seg_id is None:
        seg_id = f"convo-{now:%Y%m%dT%H%M%S}"

    if len(ctx.speakers) < 2:
        raise ValueError(
            "a conversation needs at least two cast members; "
            f"got {[c.id for c in ctx.speakers]} (run `make seed`?)"
        )

    # C1: the show frame for this hour drives the room's framing (night solo /
    # dawn handover / day / dusk handover), computed once and shared by both steps.
    frame = _frame_for(ctx, now)
    log.info(
        "convo_compose_start",
        seg_id=seg_id,
        speakers=[c.id for c in ctx.speakers],
        part_of_day=frame.part_of_day,
        lead=frame.lead,
        handover=frame.is_handover,
    )
    # D5.2 — anti-repetition steers from the airplay memory, read once for this slot:
    # recent topics/angles for the beat pick, recent talk openings for the first line.
    # Both degrade to "" on a cold start, so a fresh station generates as it did before.
    #
    # D12.3 — reconcile freshness with continuity so the two don't fight. When this slot
    # is CONTINUING a live thread (D12.2): (a) keep the active thread's topic OUT of the
    # showrunner's avoid-list — anti-repetition should stop day-scale looping, not veto
    # the beat the hosts are mid-conversation on; and (b) drop the opening-fingerprint
    # steer entirely — a cold pickup has no "opening" to freshen. An `open`/transition
    # (or the direct path, flow=None) keeps BOTH steers, so a NEW thread still can't
    # start like a recently-aired topic or opening. News (D4) is untouched — its
    # coverage recurrence is its own memory.
    continuing = flow is not None and flow.continue_thread
    active_topic = flow.handoff.topic if continuing and flow.handoff else None
    recent_topics = freshness.recent_topics_block(now, exclude=active_topic)
    recent_openings = "" if continuing else freshness.recent_openings_block(now, fmt)
    # D9.3 — decide ONCE per slot whether a guest/soundbite joins (sparse,
    # air-time-seeded, so retries keep the same guest); None = host-only. D12.4 — the
    # program's own interview cadence (flow.guest_chance) overrides the global rate,
    # so an interview show runs guests often and a solo-desk show runs none.
    seg_guest = guest_mod.maybe_guest(
        ctx, now, fmt, chance=(flow.guest_chance if flow is not None else None)
    )
    # D9.4 — the hosts' lived history from the story log, read once per slot;
    # "" degrades to the memory-less room. The same block goes to the
    # orchestrator AND the continuity editor (misremembering flags).
    memory = memory_mod.memory_section(ctx.speakers, now)
    beat = showrunner(ctx, now, frame=frame, recent_block=recent_topics, flow=flow)

    attempts = settings.convo_continuity_max_attempts
    revision_note: str | None = (
        None  # set when a continuity flag should guide the retry
    )
    last_reason = "no draft cleared the gates"
    for attempt in range(1, attempts + 1):
        script = orchestrate(
            ctx,
            beat,
            now,
            frame=frame,
            extra_directive=extra_directive,
            revision_note=revision_note,
            recent_openings=recent_openings,
            guest=seg_guest,
            memory=memory,
            flow=flow,
        ).strip()

        safety = safety_check(script)
        if not safety.ok:
            last_reason = f"safety: {safety.reason}"
            revision_note = None  # a safety flag re-rolls fresh, not note-guided
            log.warning(
                "convo_safety_flag",
                seg_id=seg_id,
                attempt=attempt,
                reason=safety.reason,
            )
            continue

        turns = parse_turns(script, ctx.speakers, guest=seg_guest)
        if not turns:
            last_reason = "no dialogue turns parsed (speaker labels did not match)"
            revision_note = None
            log.warning("convo_parse_empty", seg_id=seg_id, attempt=attempt)
            continue

        # D9.3 — structural gate: the hosts stay in control. A draft that lets
        # the guest open or close the exchange is re-rolled with the note.
        if seg_guest is not None and (
            turns[0].speaker == seg_guest.label or turns[-1].speaker == seg_guest.label
        ):
            last_reason = "guest not bracketed by hosts"
            revision_note = (
                "The guest must be bracketed by the hosts: a host opens the "
                "exchange and a host closes it — the guest never speaks first "
                "or last."
            )
            log.warning("convo_guest_bracket_flag", seg_id=seg_id, attempt=attempt)
            continue

        continuity = continuity_check(script, ctx, memory=memory)
        if not continuity.ok:
            last_reason = f"continuity: {continuity.note}"
            revision_note = continuity.note  # feed the editor's note into the rewrite
            log.warning("convo_continuity_gate_flag", seg_id=seg_id, attempt=attempt)
            continue

        # Both gates cleared — render and return. D9.0: un-tagged turns take the
        # hour's mood floor as their emotion (audible on the flagship engine only).
        default_emotion = _PART_OF_DAY_EMOTION.get(frame.part_of_day)
        audio_path = _render_turns(turns, seg_id, default_emotion=default_emotion)
        log.info(
            "convo_compose_done",
            seg_id=seg_id,
            attempt=attempt,
            turns=len(turns),
            voices=sorted({t.voice for t in turns}),
            emotions=sorted({t.emotion for t in turns if t.emotion}),
            emotion_default=default_emotion,
            continuity_ok=True,
            audio_path=audio_path,
        )
        return Segment(
            id=seg_id,
            format=fmt,
            length_target_sec=length_target_sec,
            air_time=now.isoformat(),
            script=script,
            audio_path=audio_path,
            disclosure=True,
            meta={
                "speakers": [c.id for c in ctx.speakers],
                "turns": len(turns),
                "beat": beat,
                "attempts": attempt,
                "part_of_day": frame.part_of_day,
                "emotion_default": default_emotion,
                "emotions": sorted({t.emotion for t in turns if t.emotion}),
                "guest": (
                    {
                        "kind": seg_guest.kind,
                        "label": seg_guest.label,
                        "voice": seg_guest.voice,
                    }
                    if seg_guest is not None
                    else None
                ),
                "memory_used": bool(memory),
                # D12.0/D12.2 — the slot's show position (open/continue/close) and
                # whether it CONTINUED the prior thread, recorded for visibility/tests;
                # None on the standalone path.
                "flow_position": flow.position if flow is not None else None,
                "flow_continue_thread": (
                    flow.continue_thread if flow is not None else None
                ),
                "lead": frame.lead,
                "handover": frame.is_handover,
                "safety_stage": safety.stage,
                "continuity_ok": True,
                "continuity_tier": continuity.tier,
                "continuity_note": continuity.note,
            },
        )

    # Exhausted the attempts without a clean draft — never air the flawed text.
    log.error(
        "convo_compose_fallback",
        seg_id=seg_id,
        attempts=attempts,
        reason=last_reason[:300],
    )
    return evergreen.evergreen_segment(
        now,
        fmt=fmt,
        seg_id=seg_id,
        length_target_sec=length_target_sec,
        reason=last_reason,
    )


def _names(ctx: AssembledContext) -> str:
    """ "Vell and Wren" — the host names for a prompt's framing line."""
    return " and ".join(c.name for c in ctx.speakers)


if __name__ == "__main__":
    # Runnable check: generate a two-DJ conversation for the current time.
    #   .venv/bin/python -m src.writers.conversation     (needs `make seed`)
    segment = make_conversation_segment(datetime.now().isoformat())
    log.info(
        "convo_segment_written",
        seg_id=segment.id,
        audio_path=segment.audio_path,
        turns=segment.meta.get("turns"),
    )
    print("\n----- BEAT -----\n" + segment.meta["beat"])
    print("\n----- SCRIPT -----\n" + (segment.script or ""))
    print(f"\n----- AUDIO -----\n{segment.audio_path}")
    print(
        f"\ncontinuity[{segment.meta['continuity_tier']}] "
        f"ok={segment.meta['continuity_ok']}: {segment.meta['continuity_note']}"
    )

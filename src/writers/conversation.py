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

from .. import evergreen
from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm, tts
from ..safety import safety_check
from ..segment import Segment
from ..world import clock, context, framing
from ..world.context import AssembledContext
from ..world.framing import ShowFrame
from ..world.store import CastMember

log = get_logger(__name__)


@dataclass(frozen=True)
class Turn:
    """One spoken turn in the dialogue: who says it, in which voice, and what."""

    speaker: str  # the DJ's display name (e.g. "Vell")
    voice: str  # the logical voice name (e.g. "vell_night") for the TTS seam
    text: str  # the spoken words for this turn


@dataclass(frozen=True)
class ContinuityResult:
    """The continuity editor's verdict on a draft (advisory in B4)."""

    ok: bool
    tier: str  # which model tier produced this verdict ("sonnet" | "opus")
    note: str  # the editor's note ("OK" or "ISSUES: …")


# --- The show frame (C1): who's on air this hour, framed from the clock -------


def _frame_for(ctx: AssembledContext, now: datetime) -> ShowFrame:
    """The clock-driven show frame for `now`, using the two assembled hosts.

    The cards are in canon handover order (`settings.convo_speaker_ids` = night
    host then first-light host), so the first is the night anchor and the second
    the day anchor. Computed once per segment and passed to the room's steps.
    """
    night_host, day_host = ctx.speakers[0].id, ctx.speakers[1].id
    return framing.show_frame(now, night_host=night_host, day_host=day_host)


def _situation(frame: ShowFrame, ctx: AssembledContext) -> str:
    """Resolve the frame's prose situation with the hosts' display names."""
    return framing.resolve_situation(frame, {c.id: c.name for c in ctx.speakers})


# --- Step 1: showrunner -----------------------------------------------------


def showrunner(
    ctx: AssembledContext, now: datetime, *, frame: ShowFrame | None = None
) -> str:
    """Pick tonight's beat: ONE event/angle for the two DJs, framed for the hour.

    Returns a short brief (a few sentences), not dialogue — the orchestrator turns
    it into the exchange. The cached core (both cards) rides along so the beat fits
    these two personalities; the dynamic events/canon go in the per-call system.
    `frame` is the C1 show frame (computed once by `compose_segment`); if omitted it
    is derived from `now`, so the beat is framed for the actual time of day.
    """
    names = _names(ctx)
    frame = frame or _frame_for(ctx, now)
    situation = _situation(frame, ctx)
    system = (
        "You are the showrunner for Settlement Radio, a tribute sci-fi radio "
        f"station. Choose the beat for a short on-air exchange between {names}.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)} "
        f"({frame.part_of_day}).\n"
        f"On air right now: {situation}.\n\n"
        f"What's true right now:\n{ctx.dynamic or '(nothing notable)'}\n\n"
        "Pick exactly ONE current event or world fact for them to glance off, and a "
        "HUMAN angle — a feeling, a small concrete detail, a gentle disagreement, "
        "something one of them can't stop thinking about — not just a fact to report. "
        "The angle should suit both hosts AND the time of day above; do not assume "
        "night, morning, or a handover unless the time and the on-air note say so. "
        "Reply with a SHORT brief (2-4 sentences): the topic, the human angle, and "
        "who opens. Do not write any dialogue."
    )
    beat = llm.generate(
        "Pick tonight's beat.",
        system=system,
        model=settings.llm_default_tier,
        cached_context=ctx.cached_context,
        max_tokens=settings.convo_showrunner_max_tokens,
    )
    beat = beat.strip()
    log.info("convo_showrunner_done", chars=len(beat))
    return beat


# --- Step 2: orchestrator ---------------------------------------------------


def orchestrate(
    ctx: AssembledContext,
    beat: str,
    now: datetime,
    *,
    frame: ShowFrame | None = None,
    extra_directive: str | None = None,
    revision_note: str | None = None,
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
    """
    names = _names(ctx)
    label_help = " / ".join(f"{c.name}:" for c in ctx.speakers)
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
    time_check = (
        "A real time check ('settlement time') belongs near the handover."
        if frame.is_handover
        else "A real time check ('settlement time') belongs near the open."
    )
    # --- Delivery register lives HERE (the on-air "way they speak"); the persona
    # itself lives in the cast cards (docs/canon/90-cast.md). Future Phase D packs
    # SLOT THEIR INPUTS INTO this prompt — they don't replace it — so keep the
    # showrunner→orchestrate→continuity structure intact as their injection points:
    #   * D5 (freshness): a "don't circle topics/openings aired recently: …" line
    #     from the recent-airplay memory, woven in beside the beat.
    #   * D9 (DJ memory): each host's history from the event log, joined to their card.
    #   * D10 (figures/quotes): an attributable quote a host can reference.
    system = (
        "You are the writers' room for Settlement Radio, scripting a SPOKEN "
        f"on-air exchange between two hosts — {names}. Write the dialogue ONLY.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)} "
        f"({frame.part_of_day}).\n"
        f"On air right now: {situation}. Frame the exchange for THIS time of day — "
        "match the hour above; do not write a night or dawn-handover scene unless "
        "the on-air note says so.\n\n"
        f"Tonight's beat (from the showrunner):\n{beat}\n\n"
        f"What's true right now:\n{ctx.dynamic or '(nothing notable)'}\n\n"
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
        f"and a colon — {label_help} — then the words they say. Alternate between "
        "them. No stage directions, no parentheticals, no narration, no headings, "
        "no blank-line markers. Stay entirely inside the fiction: never mention "
        "being an AI, never reference real-world brands, franchises, or people."
    )
    script = llm.generate(
        "Write the exchange now.",
        system=system,
        model=settings.llm_default_tier,
        cached_context=ctx.cached_context,
        max_tokens=settings.convo_max_tokens,
    )
    script = script.strip()
    log.info("convo_orchestrate_done", chars=len(script))
    return script


# --- Step 3: continuity -----------------------------------------------------


def continuity_check(script: str, ctx: AssembledContext) -> ContinuityResult:
    """Check the draft against canon; escalate to opus only if sonnet flags trouble.

    Returns the verdict; the GATE that acts on it (regenerate with the note, then
    fall back to evergreen) lives in `compose_segment` (C0). The escalation to
    `opus` on a sonnet flag is the confirm step before that gate spends a retry.
    """
    tier = settings.convo_continuity_tier
    note = _run_continuity(script, ctx, tier)
    ok = _is_ok(note)
    if not ok:
        # The first pass smells a problem — spend a more careful model to confirm.
        log.warning("convo_continuity_flagged", tier=tier, note=note[:300])
        tier = settings.convo_continuity_escalation_tier
        note = _run_continuity(script, ctx, tier)
        ok = _is_ok(note)
    log.info("convo_continuity_done", tier=tier, ok=ok)
    return ContinuityResult(ok=ok, tier=tier, note=note)


def _run_continuity(script: str, ctx: AssembledContext, tier: str) -> str:
    """One continuity pass at `tier`; returns the editor's note ('OK' / 'ISSUES…')."""
    system = (
        "You are the continuity editor for Settlement Radio. Check the draft below "
        "against the world bible and the character cards in the cached context: any "
        "contradiction of canon, a host acting out of character, a real-world or "
        "anachronistic reference, or info-dumping/reciting facts. Reply with the "
        "single word OK if it is consistent and in character, otherwise 'ISSUES:' "
        "followed by a terse list. Do not rewrite the draft."
    )
    note = llm.generate(
        f"Draft to check:\n\n{script}",
        system=system,
        model=tier,
        cached_context=ctx.cached_context,
        max_tokens=settings.convo_continuity_max_tokens,
    )
    return note.strip()


def _is_ok(note: str) -> bool:
    """True when the continuity note signals no problems (starts with 'OK')."""
    return note.strip().upper().startswith("OK")


# --- Turn parsing + rendering -----------------------------------------------


def parse_turns(script: str, cards: list[CastMember]) -> list[Turn]:
    """Split speaker-labelled dialogue into per-voice `Turn`s.

    Recognises lines beginning with a known host name and a colon (tolerating
    surrounding `**bold**`), and folds any wrapped continuation lines into the
    current turn. Lines before the first recognised label (stray preamble) are
    dropped. Each turn maps to its host's logical voice for the TTS seam.
    """
    by_name = {c.name.lower(): c for c in cards}
    names = "|".join(re.escape(c.name) for c in cards)
    label_re = re.compile(
        rf"^\s*\*{{0,2}}({names})\*{{0,2}}\s*:\s*(.*)$", re.IGNORECASE
    )

    turns: list[Turn] = []
    cur: CastMember | None = None
    buf: list[str] = []

    def flush() -> None:
        if cur is None:
            return
        text = re.sub(r"\*\*", "", " ".join(b.strip() for b in buf)).strip()
        if text:
            turns.append(Turn(speaker=cur.name, voice=cur.logical_voice, text=text))

    for line in script.splitlines():
        m = label_re.match(line)
        if m:
            flush()
            cur = by_name[m.group(1).lower()]
            buf = [m.group(2)]
        elif cur is not None and line.strip():
            buf.append(line)
    flush()
    return turns


def _render_turns(turns: list[Turn], seg_id: str) -> str:
    """Voice each turn in its own DJ voice, then stitch them into one mp3.

    Returns the path to the stitched segment in `settings.segments_dir`. Per-turn
    clips are written to a temp dir and cleaned up; only the joined segment lands.
    """
    out_path = settings.segments_dir / f"{seg_id}.mp3"
    tmpdir = tempfile.mkdtemp(prefix=f"{seg_id}-")
    try:
        parts: list[str] = []
        for i, turn in enumerate(turns):
            part = os.path.join(tmpdir, f"{i:03d}.mp3")
            tts.synthesize(turn.text, voice=turn.voice, out_path=part)
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
) -> Segment:
    """Turn an already-assembled context into a two-DJ talk `Segment`.

    The generation core shared by `make_conversation_segment` (B4) and the B5
    `talk` format: showrunner → (orchestrator → safety gate → continuity gate),
    looped → two-voice render. The caller assembles the context (so the speakers
    are already chosen) and may pass a `seg_id`, a `length_target_sec` DIAL, and an
    `extra_directive` (a structural backbone for the orchestrator — the B5 `talk`
    template uses it). `fmt` is the `Segment.format` label.

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
    beat = showrunner(ctx, now, frame=frame)

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

        turns = parse_turns(script, ctx.speakers)
        if not turns:
            last_reason = "no dialogue turns parsed (speaker labels did not match)"
            revision_note = None
            log.warning("convo_parse_empty", seg_id=seg_id, attempt=attempt)
            continue

        continuity = continuity_check(script, ctx)
        if not continuity.ok:
            last_reason = f"continuity: {continuity.note}"
            revision_note = continuity.note  # feed the editor's note into the rewrite
            log.warning("convo_continuity_gate_flag", seg_id=seg_id, attempt=attempt)
            continue

        # Both gates cleared — render and return.
        audio_path = _render_turns(turns, seg_id)
        log.info(
            "convo_compose_done",
            seg_id=seg_id,
            attempt=attempt,
            turns=len(turns),
            voices=sorted({t.voice for t in turns}),
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

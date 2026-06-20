"""The two-DJ conversation orchestrator (PHASE_B_TASKS.md B4) — the creative core.

A light "writers' room" that turns the assembled world into one talk `Segment`
where two DJs actually *talk to each other*, in character, glancing off a current
event — not two narrators reciting canon. Three Claude steps, all sharing the same
cached stable core (bible + both cards) so the prompt cache is reused across them:

  1. showrunner   — picks ONE beat/angle from the events near `now` and frames the
                    night → first-light handover. (tier: the default writing brain)
  2. orchestrator — writes the whole exchange in a SINGLE call (both personas in
                    one prompt: cheaper and more coherent than turn-by-turn, per
                    the B4 guidance). Output is speaker-labelled dialogue.
  3. continuity   — one check against canon on `sonnet`; ESCALATES to `opus` only
                    if that pass flags trouble. Advisory in B4 (logged, attached to
                    the Segment meta); it exercises the seam a real gate slots into.

The draft also passes the existing `safety_check()` placeholder (CLAUDE.md content
safety seam). Rendering voices each turn separately — so each DJ gets their own
logical voice — then stitches the turns into one mp3 via `tts.concat_audio`.

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

from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm, tts
from ..segment import Segment
from ..world import clock, context
from ..world.context import AssembledContext
from ..world.store import CastMember
from ..writer import safety_check

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


# --- Step 1: showrunner -----------------------------------------------------


def showrunner(ctx: AssembledContext, now: datetime) -> str:
    """Pick tonight's beat: ONE event/angle for the two DJs and the handover feel.

    Returns a short brief (a few sentences), not dialogue — the orchestrator turns
    it into the exchange. The cached core (both cards) rides along so the beat fits
    these two personalities; the dynamic events/canon go in the per-call system.
    """
    names = _names(ctx)
    system = (
        "You are the showrunner for Settlement Radio, a tribute sci-fi radio "
        f"station. Choose the beat for a short on-air exchange between {names}, at "
        "the handover from the night shift to the first-light shift.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n\n"
        f"What's true right now:\n{ctx.dynamic or '(nothing notable)'}\n\n"
        "Pick exactly ONE current event or world fact for them to glance off, and "
        "an angle that suits both hosts and the night→morning handover. Reply with "
        "a SHORT brief (2-4 sentences): the topic, the angle, and who opens. Do not "
        "write any dialogue."
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
    extra_directive: str | None = None,
) -> str:
    """Write the two-DJ exchange in one call; return speaker-labelled dialogue.

    `extra_directive` is an optional structural instruction (e.g. the B5 `talk`
    format's open → banter → music lead-in → close backbone). It is woven in
    before the format rules; `None` keeps B4's default handover shape.
    """
    names = _names(ctx)
    label_help = " / ".join(f"{c.name}:" for c in ctx.speakers)
    backbone = (
        f"Follow this shape for the exchange:\n{extra_directive}\n\n"
        if extra_directive
        else ""
    )
    system = (
        "You are the writers' room for Settlement Radio, scripting a SPOKEN "
        f"on-air exchange between two hosts — {names} — at the handover from the "
        "night shift to the first light. Write the dialogue ONLY.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n\n"
        f"Tonight's beat (from the showrunner):\n{beat}\n\n"
        f"What's true right now:\n{ctx.dynamic or '(nothing notable)'}\n\n"
        "Write it as a real conversation between two distinct people who know each "
        "other well: short, natural turns; they react to and build on what the "
        "other just said; warmth and a little wit. Each must sound like THEMSELVES "
        "per their character card (in the cached context above) — not "
        "interchangeable.\n\n"
        "CRUCIAL — do not info-dump. The world facts and the event are their "
        "SHARED knowledge: reference them naturally and glancingly, the way "
        "colleagues do. NEVER explain canon to each other, never recite it, never "
        "narrate the setting. A real time check ('settlement time') belongs near "
        "the handover.\n\n"
        f"Target {settings.convo_words_low}-{settings.convo_words_high} words "
        "total, across both voices.\n\n"
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

    Advisory in B4: the verdict is logged and attached to the Segment meta, not
    auto-applied. It exercises the seam where a real continuity/safety gate lands.
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
    return compose_segment(ctx, now, length_target_sec=length_target_sec)


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
    `talk` format: showrunner → orchestrator → continuity → two-voice render. The
    caller assembles the context (so the speakers are already chosen) and may pass
    a `seg_id`, a `length_target_sec` DIAL, and an `extra_directive` (a structural
    backbone for the orchestrator — the B5 `talk` template uses it). `fmt` is the
    `Segment.format` label (kept "talk" — the format template, if any, is recorded
    in `meta`).
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

    log.info(
        "convo_compose_start", seg_id=seg_id, speakers=[c.id for c in ctx.speakers]
    )
    beat = showrunner(ctx, now)
    script = safety_check(
        orchestrate(ctx, beat, now, extra_directive=extra_directive).strip()
    )

    turns = parse_turns(script, ctx.speakers)
    if not turns:
        raise RuntimeError(
            "no dialogue turns parsed from the orchestrator output — the speaker "
            "labels did not match the cast names; check the draft format."
        )

    continuity = continuity_check(script, ctx)
    audio_path = _render_turns(turns, seg_id)

    log.info(
        "convo_compose_done",
        seg_id=seg_id,
        turns=len(turns),
        voices=sorted({t.voice for t in turns}),
        continuity_ok=continuity.ok,
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
            "continuity_ok": continuity.ok,
            "continuity_tier": continuity.tier,
            "continuity_note": continuity.note,
        },
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

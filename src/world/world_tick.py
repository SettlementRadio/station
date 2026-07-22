"""The generative world tick (PHASE_D_WORLD_ENGINE_TASKS.md D3.1) — the keystone.

Layer 3 machinery writing Layer 1 state: one `run_tick()` invents plausible NEW
happenings consistent with the world bible, models each as a dated, arced STORY
(D3.0's story log), gates every proposal through safety + a world-continuity check,
and writes only the accepted ones — never airing/writing unsafe or contradictory
content (the C0 discipline, applied to world state).

It is NOT a separate engine outside the seams: it uses `providers/llm` for every
model call (including the new BATCH path — the cost lever), `safety.safety_check`
for the safety gate, `world/store` for all SQL (the D3.0 writes), `world/clock` to
anchor beats in in-world time, and `providers/embeddings` to make the new world
semantically recall-able like canon (D2 reuse). The vendor batch SDK is imported
ONLY behind `llm.generate_batch` — this module never touches it directly.

D3.1 proposes + writes new stories; D3.2 advances running stories across ticks; D3.3
keeps the generated world varied (domain balance + de-duplication + new/advance
pacing); D3.4 exposes `run_tick` as a one-shot CLI job (`make world-tick` /
`python -m src.world.world_tick`, see `main()`) — the nightly WORLD-STATE batch the
C5 cron/systemd timer runs, kept SEPARATE from the C2 scheduler's audio top-up.

D10.1 PEOPLES the world: each proposed story (and each advancement) also carries
invented FIGURES — the people it is about — and attributable, dated QUOTES of what they
said. These are generated INSIDE the same proposal/advancement call, so they ride the
same safety + continuity gate and the Batch + caching cost levers: a flagged figure or
quote regenerates/drops with its story, and a continuing story REUSES its existing
figures (matched by name) rather than spawning a new person each beat. The figure/quote
SQL lives only in `world/store` (D10.0); voicing a quote as a soundbite is D9/D10.3.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from ..config import settings
from ..logging_setup import get_logger
from ..providers import embeddings, llm
from ..safety import safety_check
from . import canon_source, clock, store
from . import events as events_mod

log = get_logger(__name__)

# The world's domains — the D1 cornerstones double as the spread the tick generates
# across (history, literature, finance, war, nations, peoples, geography, religion,
# culture, technology), plus `sports` (D9.4: canon's bounded-leisure games and the
# live circuit Kael's card covers — added so the sports desk's beat actually happens
# in the generated world), plus `health` and `style` (R2.1: back the GRID_V2
# verticals The Ward and The Fit via 54-health.md / 56-style.md — a program without
# a domain starves, the D9.4 lesson). Intrinsic domain data, not config; D3.3 adds
# the *weighting* that keeps quiet domains from starving. Used here only to steer
# the proposal toward variety and to tag each story. These tags are also what a
# DJ's card tags match for on-air memory affinity (D9.4, writers/memory.py).
DOMAINS: tuple[str, ...] = (
    "history",
    "literature",
    "finance",
    "war",
    "nations",
    "peoples",
    "geography",
    "religion",
    "culture",
    "technology",
    "sports",
    "health",
    "style",
)

# State keys the tick owns (live in the `state` kv table; survive a canon refresh).
_TICK_COUNT_KEY = "world_tick_count"
_TICK_LAST_AT_KEY = "world_tick_last_at"
# The intra-day micro-tick (R4.1) keeps its OWN counter, separate from the nightly
# tick's — so a micro-run never pollutes the nightly pacing/resolve math (which is
# keyed off `stories.created_tick`/`last_advanced_tick` vs the nightly counter). The
# counter increments ONLY on a run that actually writes a beat, so beat ids stay unique
# and two quiet runs in a row change nothing (R4.1 done-when).
_MICRO_COUNT_KEY = "world_micro_tick_count"
_MICRO_LAST_AT_KEY = "world_micro_tick_last_at"


# --- Shapes -----------------------------------------------------------------


@dataclass(frozen=True)
class ProposedFigure:
    """One invented in-world person a proposed story is about (D10.1), pre-gate.

    The people the world *speaks through* — an official, an artist, a witness. `name`
    is how a quote references them (resolved by name at materialise time, so the same
    person reused across beats maps to ONE figure row). `role` is their in-world title;
    `bio` a short card the writers/news read. Invented people ONLY (CLAUDE.md IP
    boundary) — the gate checks this with the rest of the story.
    """

    name: str
    role: str
    bio: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProposedQuote:
    """One attributable statement a figure makes in a beat (D10.1), pre-gate.

    `figure` names the speaker (must resolve to one of the story's figures — declared
    or already-existing for a continuing story); an unresolved name is dropped at
    materialise time (we never attribute to a person who doesn't exist). The quote
    inherits its beat's in-world datetime, so the clock frames it (said yesterday/now).
    `stance` is an optional free-form tone hint ("defiant", "reassuring").
    """

    figure: str
    text: str
    stance: str | None = None


@dataclass(frozen=True)
class ProposedBeat:
    """One beat of a proposed story, before it becomes an `events` row.

    `day_offset` is whole in-world days from the tick's "today" (negative = already
    happened, 0 = today, positive = upcoming); `hour` is 0–23. These anchor the beat
    in in-world time so the B2 clock frames it future/now/past. `quotes` are the
    attributable statements made *in* this beat (D10.1) — they inherit its datetime.

    `planned` (R4.0) marks a later beat of a SAME-DAY ARC: authored now, but the plan
    rather than the record, so it stays off air until its hour passes. Only meaningful
    for a beat still ahead of the clock — `_beat_event` drops the flag on a beat dated
    at/behind now (it has already landed; there is nothing left to wait for).
    """

    title: str
    body: str
    beat_kind: str
    day_offset: int
    hour: int
    quotes: list[ProposedQuote] = field(default_factory=list)
    planned: bool = False


@dataclass(frozen=True)
class ProposedStory:
    """One happening the tick proposes, before gating + materialising to the store.

    `figures` (D10.1) are the invented people this story introduces; its beats' quotes
    attribute statements to them by name.
    """

    title: str
    summary: str
    scale: str  # "large" | "small"
    domain: str
    arc_stage: str
    beats: list[ProposedBeat]
    figures: list[ProposedFigure] = field(default_factory=list)


@dataclass(frozen=True)
class ProposedAdvance:
    """The next beat the tick proposes for a running story (D3.2), before gating.

    Carries the story being advanced + its prior beats (the history the gate checks
    against), the new arc stage (validated forward-only at write time), the new beat
    itself, and any NEW figures it introduces (D10.1 — a continuing story mostly REUSES
    its existing figures, matched by name at materialise time; `new_figures` is the few
    fresh people this beat brings in, bounded by `*_advance_new_figures_max`).
    """

    story: store.Story
    prior_beats: list[store.Event]
    new_stage: str
    beat: ProposedBeat
    new_figures: list[ProposedFigure] = field(default_factory=list)


@dataclass(frozen=True)
class _Verdict:
    """A gate outcome for one proposed story or advancement."""

    ok: bool
    reason: str


@dataclass(frozen=True)
class _TickContext:
    """The world slice the proposal + gate calls share for one run."""

    bible: str  # the cached stable prefix (cost lever)
    active_summary: str  # the running stories, for dedup/consistency awareness
    now: datetime
    iw_now: datetime
    quiet_domains: list[str] = field(default_factory=list)  # under-used lately (D3.3)
    new_max: int = 0  # this tick's new-story budget after the pacing cap (D3.3)


@dataclass
class TickResult:
    """What one `run_tick()` did — printed by the CLI (D3.4) and logged as telemetry."""

    tick: int
    proposed: int = 0
    accepted: int = 0
    dropped: int = 0
    duplicates: int = 0  # near-duplicate proposals rejected by de-dup (D3.3)
    regenerated: int = 0
    advanced: int = 0  # running stories moved on this tick (D3.2)
    resolved: int = 0  # of those, stories that reached `past` (stopped advancing)
    story_ids: list[str] = field(default_factory=list)  # new stories created
    advanced_ids: list[str] = field(default_factory=list)  # running stories advanced
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class MicroTickResult:
    """What one `run_micro_tick()` did (R4.1) — printed by the CLI + logged.

    `acted` is False on a quiet run (disabled, dice, no live story, model declined, or
    the gate dropped the beat) — the common, valid outcome that writes nothing.
    `micro_tick` is the counter AFTER this run: unchanged on a quiet run, +1 on an
    acting one. `reason` explains a quiet/dropped run for the logs + CLI.
    """

    micro_tick: int
    acted: bool = False
    story_id: str | None = None
    beat_id: str | None = None
    reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)


# --- The tick ---------------------------------------------------------------


def run_tick(now: datetime | None = None) -> TickResult:
    """Run one world tick: propose new happenings, gate them, write the accepted.

    Returns a `TickResult` summary. A tick is transactional via `store.connect` — a
    mid-write failure rolls back, never leaving a half-written story. Gating failures
    drop the offending story (logged loudly) rather than aborting the run.
    """
    now = now or datetime.now()
    iw_now = clock.to_inworld(now)
    log.info("world_tick_start", now=now.isoformat(), inworld=iw_now.isoformat())

    # Read the world as it stands BEFORE this tick: the running stories (for context
    # + as advancement candidates) and the prior beats of the stories we may advance.
    with store.connect() as conn:
        tick_no = (int(store.get_state(conn, _TICK_COUNT_KEY) or 0)) + 1
        active = store.active_stories(
            conn, limit=settings.world_tick_active_context_limit
        )
        candidates = active[: settings.world_tick_advance_max]
        prior_beats = {s.id: store.story_beats(conn, s.id) for s in candidates}
        # D10.1 — the figures each candidate already has, so an advancement REUSES them
        # (by name) instead of spawning a new person for the same role each beat.
        prior_figures = {s.id: store.figures_for_story(conn, s.id) for s in candidates}
        # D3.3 — recent stories (any stage) drive domain balance + de-duplication.
        recent = store.recent_stories(
            conn,
            since_tick=max(0, tick_no - settings.world_tick_domain_window_ticks),
        )

    # D3.3 pacing — when the living world is already at its soft cap, propose NO new
    # stories this tick (only advance/resolve), so it doesn't churn unboundedly.
    new_max = (
        0
        if len(active) >= settings.world_tick_max_active_stories
        else settings.world_tick_new_stories_max
    )
    ctx = _TickContext(
        bible=canon_source.load_bible(settings.canon_dir, settings.canon_path),
        active_summary=_summarise_active(active),
        now=now,
        iw_now=iw_now,
        quiet_domains=_quiet_domains(recent, settings.world_tick_quiet_domains),
        new_max=new_max,
    )
    result = TickResult(tick=tick_no)

    # Part 1 — propose + write NEW stories (D3.1), domain-balanced + de-duped (D3.3).
    accepted = _propose_and_gate(ctx, recent, result)

    # Part 2 — ADVANCE running stories (D3.2). Independent of whether new stories were
    # proposed, so the world keeps moving even on a quiet night.
    advances = _advance_and_gate(
        candidates, prior_beats, prior_figures, ctx, tick_no, result
    )

    with store.connect() as conn:
        for i, p in enumerate(accepted):
            story, beats = _materialise(p, tick_no, ctx, i)
            store.insert_story(conn, story)
            store.insert_beats(conn, beats)
            figures, quotes = _materialise_people(p, story, beats, tick_no)
            _write_people(conn, figures, quotes, result)
            result.usage["embeddings_written"] = (
                result.usage.get("embeddings_written", 0)
                + _embed_story(conn, story)
                + _embed_beats(conn, beats)
            )
            result.story_ids.append(story.id)
        result.accepted = len(accepted)

        for adv in advances:
            beat = _beat_event(adv.story.id, f"a{tick_no}", adv.beat, ctx)
            store.insert_beats(conn, [beat])
            store.advance_story(conn, adv.story.id, adv.new_stage, tick=tick_no)
            figures, quotes = _advance_people(
                adv, beat, prior_figures.get(adv.story.id, []), tick_no
            )
            _write_people(conn, figures, quotes, result)
            result.usage["embeddings_written"] = result.usage.get(
                "embeddings_written", 0
            ) + _embed_beats(conn, [beat])
            result.advanced_ids.append(adv.story.id)
            if store.is_resolved(adv.new_stage):
                result.resolved += 1
        result.advanced = len(advances)

        _finish_conn(conn, tick_no, now)

    log.info(
        "world_tick_done",
        tick=tick_no,
        proposed=result.proposed,
        accepted=result.accepted,
        dropped=result.dropped,
        duplicates=result.duplicates,
        regenerated=result.regenerated,
        advanced=result.advanced,
        resolved=result.resolved,
        **{f"usage_{k}": v for k, v in result.usage.items()},
    )
    return result


def _propose_and_gate(
    ctx: _TickContext, recent: list[store.Story], result: TickResult
) -> list[ProposedStory]:
    """Propose new happenings, gate them (regen-once-then-drop), then de-dup (D3.3)."""
    if ctx.new_max <= 0:  # pacing cap reached — advance/resolve only this tick
        log.info("world_tick_new_paced_out", tick=result.tick, active_at_cap=True)
        return []

    proposals = _propose(ctx)
    result.proposed = len(proposals)
    if not proposals:
        log.warning("world_tick_no_proposals", tick=result.tick)
        return []

    verdicts = _gate(proposals, ctx, result)
    accepted = [p for p, v in zip(proposals, verdicts, strict=True) if v.ok]
    flagged = [(p, v) for p, v in zip(proposals, verdicts, strict=True) if not v.ok]
    for p, v in flagged:
        log.warning("world_tick_proposal_flagged", title=p.title, reason=v.reason[:200])

    if flagged and settings.world_tick_max_attempts > 1:
        regenerated = _regenerate([p for p, _ in flagged], [v for _, v in flagged], ctx)
        result.regenerated = len(regenerated)
        regen_verdicts = _gate(regenerated, ctx, result)
        for p, v in zip(regenerated, regen_verdicts, strict=True):
            if v.ok:
                accepted.append(p)
            else:
                log.warning(
                    "world_tick_regen_dropped", title=p.title, reason=v.reason[:200]
                )

    accepted = _dedup(accepted, recent, result)
    result.dropped = result.proposed - len(accepted) - result.duplicates
    return accepted


# --- The intra-day micro-tick (R4.1) ----------------------------------------


def _random_unit() -> float:
    """A uniform draw in [0, 1) — the micro-tick's act-or-stay-quiet dice.

    Wrapped so a test can force an acting run (patch to 0.0) or a quiet one (patch to
    ~1.0) without touching global RNG state.
    """
    return random.random()


def run_micro_tick(now: datetime | None = None) -> MicroTickResult:
    """Run one intra-day micro-tick (R4.1): maybe advance ONE live story a small beat.

    The light counterpart to the nightly `run_tick`. It invents no new stories and
    moves no arc; at most it adds ONE small LANDED beat (a detail, a reaction, a
    complication) to a story that is live TODAY, through the SAME safety+continuity
    gates as the nightly advance but on the direct haiku path (latency over the Batch
    discount). A QUIET run — disabled, the dice, no live story, the model declining,
    or the gate dropping the beat — writes NOTHING (two quiet runs in a row leave the
    world byte-identical). It never touches the schedule.

    Transactional like the nightly tick: the single write happens in one short
    `store.connect` block after all network I/O, so a failure rolls back cleanly.
    """
    now = now or datetime.now()
    iw_now = clock.to_inworld(now)
    log.info("micro_tick_start", now=now.isoformat(), inworld=iw_now.isoformat())

    if not settings.micro_tick_enabled:
        return _micro_quiet(now, "disabled")

    # Read the world as it stands: the current micro counter + today's live stories.
    with store.connect() as conn:
        micro_count = int(store.get_state(conn, _MICRO_COUNT_KEY) or 0)
        active = store.active_stories(
            conn, limit=settings.world_tick_active_context_limit
        )
        live = _micro_live_stories(conn, active, iw_now)
        chosen = _micro_pick(live)
        prior_figures = store.figures_for_story(conn, chosen[0].id) if chosen else []
        bible = canon_source.load_bible(settings.canon_dir, settings.canon_path)

    if chosen is None:
        return _micro_quiet(now, "no live story today")

    # The dice: a quiet run is a valid, common outcome (dial the probability).
    if _random_unit() >= settings.micro_tick_advance_probability:
        return _micro_quiet(now, "quiet run (dice)")

    story, prior_beats, _newest = chosen
    ctx = _TickContext(
        bible=bible,
        active_summary=_summarise_active(active),
        now=now,
        iw_now=iw_now,
    )

    # Generate ONE small beat on the direct (non-batch) haiku path — near-live.
    adv = _micro_generate(story, prior_beats, prior_figures, ctx)
    if adv is None:
        return _micro_quiet(now, "model added nothing")

    verdict = _micro_gate(adv, ctx)
    if not verdict.ok:
        log.warning(
            "micro_tick_dropped", story_id=story.id, reason=verdict.reason[:200]
        )
        return _micro_quiet(now, f"gate: {verdict.reason}")

    # Act: write the one landed beat + any new people, bump the micro counter. The arc
    # stage is left untouched (the nightly tick owns progression) — we only add texture.
    micro_no = micro_count + 1
    result = MicroTickResult(micro_tick=micro_no, acted=True, story_id=story.id)
    beat = _beat_event(story.id, f"m{micro_no}", adv.beat, ctx)
    with store.connect() as conn:
        store.insert_beats(conn, [beat])
        figures, quotes = _advance_people(adv, beat, prior_figures, micro_no)
        _write_people(conn, figures, quotes, result)
        result.usage["embeddings_written"] = result.usage.get(
            "embeddings_written", 0
        ) + _embed_beats(conn, [beat])
        store.set_state(conn, _MICRO_COUNT_KEY, str(micro_no))
        store.set_state(conn, _MICRO_LAST_AT_KEY, now.isoformat())
    result.beat_id = beat.id

    log.info(
        "micro_tick_done",
        micro_tick=micro_no,
        acted=True,
        story_id=story.id,
        beat_id=beat.id,
        planned=beat.planned,
        **{f"usage_{k}": v for k, v in result.usage.items()},
    )
    return result


def _micro_quiet(now: datetime, reason: str) -> MicroTickResult:
    """A run that writes nothing (R4.1) — the counter is read only, not advanced."""
    with store.connect() as conn:
        micro_count = int(store.get_state(conn, _MICRO_COUNT_KEY) or 0)
    log.info("micro_tick_quiet", micro_tick=micro_count, reason=reason)
    return MicroTickResult(micro_tick=micro_count, acted=False, reason=reason)


_MICRO_BEAT_ID_RE = re.compile(r"-m\d+$")  # a micro-tick beat id suffix (R4.1)


def _micro_pick(
    live: list[tuple[store.Story, list[store.Event], store.Event]],
) -> tuple[store.Story, list[store.Event], store.Event] | None:
    """Choose which live story this micro-tick nudges — spreading attention (R4.1).

    Picking the plain freshest story every time would let ONE thread run away: each
    micro-beat it gets makes it the freshest again, so it would be re-picked forever
    and the rest of the day would go untouched. Instead prefer the live story with the
    FEWEST micro-beats so far, tie-broken by freshest — so the day's several threads
    take turns and a single story can't monopolise the intra-day updates.
    """
    if not live:
        return None

    def micro_beats(entry: tuple[store.Story, list[store.Event], store.Event]) -> int:
        return sum(1 for b in entry[1] if _MICRO_BEAT_ID_RE.search(b.id))

    # `live` is already freshest-first; `min` is stable, so among stories with an equal
    # micro-beat count it returns the freshest — the tie-break we want.
    return min(live, key=micro_beats)


def _micro_live_stories(
    conn, active: list[store.Story], iw_now: datetime
) -> list[tuple[store.Story, list[store.Event], store.Event]]:
    """Active stories live TODAY, freshest first (R4.1 candidate set).

    A story qualifies when its newest ALREADY-LANDED beat (not a planned future beat)
    is within `micro_tick_live_window_hours` of in-world now — a thread genuinely in
    play, not an old arc the micro-tick has no business poking. Returns
    `(story, all_beats, newest_landed_beat)`, most-recently-moved first, so the caller
    advances the story most in play right now.
    """
    window = timedelta(hours=settings.micro_tick_live_window_hours)
    out: list[tuple[store.Story, list[store.Event], store.Event]] = []
    for s in active:
        beats = store.story_beats(conn, s.id)
        landed = [b for b in beats if not b.planned and b.in_world_datetime <= iw_now]
        if not landed:
            continue
        newest = max(landed, key=lambda b: b.in_world_datetime)
        if iw_now - newest.in_world_datetime <= window:
            out.append((s, beats, newest))
    out.sort(key=lambda t: t[2].in_world_datetime, reverse=True)
    return out


def _micro_generate(
    story: store.Story,
    prior_beats: list[store.Event],
    prior_figures: list[store.Figure],
    ctx: _TickContext,
) -> ProposedAdvance | None:
    """Ask haiku (direct path) for ONE small intra-day beat, or None if it declines."""
    raw = llm.generate(
        "Write the story's small next development as a JSON object, "
        'or {"beat": null} if nothing new would plausibly have happened yet.',
        system=_micro_advance_system(story, prior_beats, prior_figures, ctx),
        model=settings.micro_tick_tier,
        bible=ctx.bible,  # CO2: the shared bible cache block
        max_tokens=settings.micro_tick_max_tokens,
    )
    return _parse_advance(raw, story, prior_beats)


def _micro_advance_system(
    story: store.Story,
    beats: list[store.Event],
    figures: list[store.Figure],
    ctx: _TickContext,
) -> str:
    """Instructions for ONE small intra-day beat (R4.1) — shares the cached bible."""
    people = (
        "PEOPLE: the beat's `quotes` are attributable statements. REUSE this story's "
        "EXISTING figures, quoted by their EXACT name:\n"
        f"{_figures_text(figures)}\n"
        "Only introduce a NEW person if the small beat truly needs one, then list them "
        f"in `new_figures` (at most {settings.world_tick_advance_new_figures_max}).\n\n"
        if settings.world_tick_figures_enabled
        else ""
    )
    return (
        "You are the world-simulation engine for Settlement Radio, a tribute "
        f"science-fiction station set in the year {ctx.iw_now.year}. This is a LIGHT "
        "intra-day update between the nightly world ticks, not a new chapter.\n\n"
        f"In-world now: {clock.render_wall_clock(ctx.now)}.\n\n"
        f"STORY: {story.title} — {story.summary}\n"
        f"Current arc stage: {story.arc_stage}\n"
        f"Prior beats (oldest first):\n{_beats_text(beats)}\n\n"
        f"{people}"
        "Add at most ONE SMALL development that would plausibly have emerged in the "
        "last hour or two — a new detail, a reaction quote, a minor complication. It "
        "is happening NOW: date it day_offset 0 at the current hour, and set "
        '"planned": false. Keep it small and consistent with the beats above — do NOT '
        "resolve the story, do NOT contradict a prior beat, and do NOT repeat one. If "
        'nothing new would realistically have happened yet, reply {"beat": null}.\n\n'
        "Return ONLY a JSON object (no prose, no code fence):\n"
        '{"beat": {"title": str, "body": str, "beat_kind": str, "day_offset": 0, '
        '"hour": int, "planned": false, '
        '"quotes": [{"figure": str, "text": str, "stance": str}]}, '
        '"new_figures": [{"name": str, "role": str, "bio": str, "tags": [str]}]}\n'
        "Original world only — never real franchises, people, or trademarks. Use "
        '{"beat": null} to add nothing.'
    )


def _micro_gate(adv: ProposedAdvance, ctx: _TickContext) -> _Verdict:
    """Safety + a single continuity check for one micro-beat (direct, non-batch path).

    Mirrors the nightly `_run_gate` logic but for exactly one item on the haiku path —
    the Batch discount isn't worth its async latency for a single near-live call.
    """
    text = _advance_text(adv)
    safety = safety_check(text)
    if not safety.ok:
        return _Verdict(False, f"safety: {safety.reason}")
    note = llm.generate(
        text,
        system=_advance_continuity_system(ctx, adv),
        model=settings.micro_tick_tier,
        bible=ctx.bible,  # CO2: the shared bible cache block
        max_tokens=settings.micro_tick_continuity_max_tokens,
    )
    if _is_ok(note):
        return _Verdict(True, "OK")
    return _Verdict(False, f"continuity: {note.strip()}")


# --- Step 1: propose --------------------------------------------------------


def _dayarc_instruction(ctx: _TickContext) -> str:
    """Ask for a few of tonight's stories to UNFOLD across the coming day (R4.0).

    The nightly tick otherwise lands each story whole, so the news desk has the same
    facts at 07:00 and at 19:00 and can only re-read them. A same-day arc gives the
    day motion: beats at distinct hours, the later ones `planned` so they reach air
    only once their hour passes. Empty when the dials are off.
    """
    stories = settings.world_tick_dayarc_stories_max
    beats = settings.world_tick_dayarc_beats_max
    if stories <= 0 or beats < 2:
        return ""
    return (
        f"SAME-DAY ARCS: up to {stories} of these stories must UNFOLD ACROSS THE "
        f"COMING DAY rather than land whole — give such a story {beats} beats at "
        "DISTINCT hours of day_offset 0 (spread across the broadcast day, e.g. a "
        "vessel missing at 07:00, located at 13:00, its crew reached at 19:00 — it "
        f"is currently {ctx.iw_now:%H:%M} in-world); a "
        "final beat may fall on day_offset 1. Each beat must add a REAL development "
        "(a discovery, a complication, a resolution) that the earlier beats do not "
        "already contain — not a restatement.\n"
        "Mark every beat of such an arc that is still AHEAD of the in-world clock "
        'with "planned": true — it is the plan for later today, not the record, and '
        "the news desk will hold it until its hour arrives. The beat that has "
        'already happened is "planned": false. Ordinary stories (and genuinely '
        'announced future events like a festival next week) stay "planned": false '
        "— those are trailed on air as things that are coming.\n\n"
    )


def _propose(ctx: _TickContext) -> list[ProposedStory]:
    """Ask the writing brain for a bounded, domain-balanced mix of new happenings."""
    hi = ctx.new_max  # the pacing-capped upper bound (D3.3)
    lo = min(settings.world_tick_new_stories_min, hi)
    quiet = (
        "These domains have been QUIET lately — deliberately favour them to keep the "
        f"world varied: {', '.join(ctx.quiet_domains)}.\n\n"
        if ctx.quiet_domains
        else ""
    )
    dayarc = _dayarc_instruction(ctx)
    people = (
        "PEOPLE: give each story a FEW invented in-world figures (the people it is "
        f"about — at most {settings.world_tick_figures_per_story_max}: an official, an "
        "artist, a witness) and attach one or more attributable QUOTES to its beats — "
        "what a figure said (a reaction, an announcement, a denial). Each quote's "
        "`figure` MUST be the exact name of one of that story's figures. A short, "
        "in-character line, not a speech. No more than "
        f"{settings.world_tick_quotes_per_story_max} quotes per story.\n\n"
        if settings.world_tick_figures_enabled
        else ""
    )
    system = (
        "You are the world-simulation engine for Settlement Radio, a tribute "
        f"science-fiction radio station broadcasting from the year {ctx.iw_now.year} "
        "(600 years ahead of the present). Invent NEW happenings in this world for "
        "tonight's world tick — fresh, plausible, and STRICTLY consistent with the "
        "world bible in the cached context above and with the currently-running "
        "stories below. Do NOT duplicate or contradict either.\n\n"
        f"In-world now: {clock.render_wall_clock(ctx.now)}.\n\n"
        f"Currently-running stories:\n{ctx.active_summary or '(none yet)'}\n\n"
        f"Generate between {lo} and {hi} new happenings — a MIX of large (a political "
        "shift, an economic swing, a new festival) and small (a cruise liner goes "
        "missing, a moon-president's child marries). Spread them across these domains: "
        f"{', '.join(DOMAINS)}.\n\n"
        f"{quiet}"
        "Each happening is a STORY with an arc. Choose an initial arc_stage from "
        f"{', '.join(store.ARC_STAGES)} and give it 1-3 dated BEATS. For each beat, "
        "day_offset is whole in-world days from today (negative = already happened, "
        "0 = today, positive = upcoming), within "
        f"±{settings.world_tick_beat_horizon_days} days; hour is 0-23.\n\n"
        f"{dayarc}"
        f"{people}"
        "Return ONLY a JSON array (no prose, no code fence). Each element:\n"
        '{"title": str, "summary": str, "scale": "large"|"small", "domain": str, '
        '"arc_stage": str, '
        '"figures": [{"name": str, "role": str, "bio": str, "tags": [str]}], '
        '"beats": [{"title": str, "body": str, "beat_kind": str, '
        '"day_offset": int, "hour": int, "planned": bool, '
        '"quotes": [{"figure": str, "text": str, "stance": str}]}]}\n\n'
        "Stay entirely inside the fiction: original world only — never real "
        "franchises, real people, or trademarks. The FIGURES are invented in-world "
        "people too — never a real or trademarked person."
    )
    raw = llm.generate(
        "Generate tonight's new happenings as a JSON array.",
        system=system,
        model=settings.world_tick_propose_tier,
        bible=ctx.bible,  # CO2: the shared bible cache block
        max_tokens=settings.world_tick_propose_max_tokens,
    )
    proposals = _parse_proposals(raw)[:hi]
    log.info(
        "world_tick_proposed", count=len(proposals), quiet_domains=ctx.quiet_domains
    )
    return proposals


def _regenerate(
    flagged: list[ProposedStory], verdicts: list[_Verdict], ctx: _TickContext
) -> list[ProposedStory]:
    """Re-propose flagged stories once, fed the gate's complaint, to fix the problem."""
    notes = "\n".join(
        f"- {p.title}: {v.reason}" for p, v in zip(flagged, verdicts, strict=True)
    )
    system = (
        "You are the world-simulation engine for Settlement Radio, fixing rejected "
        f"happenings for the year {ctx.iw_now.year}. The drafts below were flagged by "
        "the safety/continuity editor for the stated reasons. Rewrite each into a NEW "
        "happening that fixes the problem while staying strictly consistent with the "
        "world bible (cached above) and the running stories. Same arc + dated-beats "
        "shape.\n\n"
        f"In-world now: {clock.render_wall_clock(ctx.now)}.\n\n"
        f"Currently-running stories:\n{ctx.active_summary or '(none yet)'}\n\n"
        f"Rejected drafts and why:\n{notes}\n\n"
        "Return ONLY a JSON array in the SAME schema as before (title, summary, scale, "
        "domain, arc_stage, figures[name, role, bio, tags], beats[title, body, "
        "beat_kind, day_offset, hour, planned, quotes[figure, text, stance]]). A "
        "rewrite keeps its same-day-arc shape if the draft had one (beats at distinct "
        'hours of day 0, the ones still ahead of the clock "planned": true). Original '
        "world "
        "only — never real franchises, people, or trademarks (figures included)."
    )
    raw = llm.generate(
        "Rewrite the rejected happenings as a JSON array.",
        system=system,
        model=settings.world_tick_propose_tier,
        bible=ctx.bible,  # CO2: the shared bible cache block
        max_tokens=settings.world_tick_propose_max_tokens,
    )
    return _parse_proposals(raw)[: len(flagged)]


# --- Step 2: gate (safety + batched continuity) -----------------------------


def _gate(
    proposals: list[ProposedStory], ctx: _TickContext, result: TickResult
) -> list[_Verdict]:
    """Gate new proposals (safety + batched continuity vs canon + running stories)."""
    return _run_gate(
        ctx,
        len(proposals),
        text_for=lambda i: _story_text(proposals[i]),
        system_for=lambda _i: _continuity_system(ctx),
        result=result,
    )


def _run_gate(
    ctx: _TickContext,
    count: int,
    *,
    text_for,
    system_for,
    result: TickResult,
) -> list[_Verdict]:
    """The shared gate: the safety gate (per item), then a batched continuity check.

    `text_for(i)` is the item's gate text (safety + the continuity prompt body);
    `system_for(i)` is its continuity-editor instructions (shares the cached bible).
    An item passes only if BOTH pass. The continuity checks run through the BATCH
    path (`llm.generate_batch`) — the cost lever — so the high-volume gate is 50% off
    and shares the cached bible. Only safety-passed items are continuity-checked.
    Reused by both new proposals (D3.1) and story advancements (D3.2).
    """
    verdicts: list[_Verdict | None] = [None] * count

    to_check: list[int] = []
    for i in range(count):
        safety = safety_check(text_for(i))
        if not safety.ok:
            verdicts[i] = _Verdict(False, f"safety: {safety.reason}")
        else:
            to_check.append(i)

    if to_check:
        reqs = [
            llm.BatchRequest(
                custom_id=str(i),
                prompt=text_for(i),
                system=system_for(i),
                bible=ctx.bible,  # CO2: the shared bible cache block
                model=settings.world_tick_continuity_tier,
                max_tokens=settings.world_tick_continuity_max_tokens,
            )
            for i in to_check
        ]
        result.usage["continuity_calls"] = result.usage.get(
            "continuity_calls", 0
        ) + len(reqs)
        for r in llm.generate_batch(reqs):
            for k, v in r.usage.items():
                result.usage[k] = result.usage.get(k, 0) + v
            i = int(r.custom_id)
            if not r.ok:
                # Fail closed — never write something we couldn't verify.
                verdicts[i] = _Verdict(False, f"continuity check failed: {r.error}")
            elif _is_ok(r.text or ""):
                verdicts[i] = _Verdict(True, "OK")
            else:
                verdicts[i] = _Verdict(False, f"continuity: {(r.text or '').strip()}")

    return [v if v is not None else _Verdict(False, "ungated") for v in verdicts]


def _continuity_system(ctx: _TickContext) -> str:
    """The world-continuity editor's instructions (shares the cached bible)."""
    return (
        "You are the world-continuity editor for Settlement Radio, a tribute "
        f"science-fiction station set in the year {ctx.iw_now.year}. Check the "
        "proposed happening below against the world bible in the cached context and "
        "the currently-running stories. FLAG it if it contradicts an established "
        "canon fact, breaks the world's premise, duplicates or contradicts a running "
        "story, or is internally inconsistent. This is fiction: in-world tension, "
        "danger, and loss are fine.\n\n"
        f"Currently-running stories:\n{ctx.active_summary or '(none yet)'}\n\n"
        "Reply with the single word OK if it fits the world, otherwise 'ISSUES:' "
        "followed by a terse reason. Do not rewrite it."
    )


# --- Step 2b: advance running stories (D3.2) --------------------------------


def _advance_and_gate(
    candidates: list[store.Story],
    prior_beats: dict[str, list[store.Event]],
    prior_figures: dict[str, list[store.Figure]],
    ctx: _TickContext,
    tick_no: int,
    result: TickResult,
) -> list[ProposedAdvance]:
    """Generate + gate the next beat for each candidate running story.

    Resolved (`past`) stories never reach here — `store.active_stories` excludes
    them, so a resolved story stays in the log as history but stops advancing. A
    flagged advancement is SKIPPED this tick (the story remains active and is retried
    next tick); unlike a brand-new proposal, nothing is lost by waiting.
    """
    if not candidates:
        return []

    proposed = _advance_generate(candidates, prior_beats, prior_figures, ctx, tick_no)
    if not proposed:
        return []

    verdicts = _run_gate(
        ctx,
        len(proposed),
        text_for=lambda i: _advance_text(proposed[i]),
        system_for=lambda i: _advance_continuity_system(ctx, proposed[i]),
        result=result,
    )
    accepted: list[ProposedAdvance] = []
    for adv, v in zip(proposed, verdicts, strict=True):
        if v.ok:
            accepted.append(adv)
        else:
            log.warning(
                "world_tick_advance_skipped",
                story_id=adv.story.id,
                reason=v.reason[:200],
            )
    return accepted


def _advance_generate(
    candidates: list[store.Story],
    prior_beats: dict[str, list[store.Event]],
    prior_figures: dict[str, list[store.Figure]],
    ctx: _TickContext,
    tick_no: int,
) -> list[ProposedAdvance]:
    """Ask the writing brain (batched) for the next beat + new stage of each story."""
    reqs = [
        llm.BatchRequest(
            custom_id=str(i),
            prompt="Write the story's next beat as a JSON object.",
            system=_advance_system(
                s, prior_beats.get(s.id, []), prior_figures.get(s.id, []), ctx, tick_no
            ),
            bible=ctx.bible,  # CO2: the shared bible cache block
            model=settings.world_tick_propose_tier,
            max_tokens=settings.world_tick_continuity_max_tokens
            + settings.world_tick_propose_max_tokens // 2,
        )
        for i, s in enumerate(candidates)
    ]
    out: list[ProposedAdvance] = []
    for r in llm.generate_batch(reqs):
        if not r.ok:
            log.warning(
                "world_tick_advance_gen_failed", custom_id=r.custom_id, error=r.error
            )
            continue
        story = candidates[int(r.custom_id)]
        parsed = _parse_advance(r.text or "", story, prior_beats.get(story.id, []))
        if parsed is not None:
            out.append(parsed)
    log.info(
        "world_tick_advance_proposed", candidates=len(candidates), proposed=len(out)
    )
    return out


def _advance_system(
    story: store.Story,
    beats: list[store.Event],
    figures: list[store.Figure],
    ctx: _TickContext,
    tick_no: int,
) -> str:
    """Instructions to advance ONE running story by its next beat (shares the bible)."""
    age = tick_no - (story.created_tick or tick_no)
    forward = ", ".join(store.ARC_TRANSITIONS.get(story.arc_stage, ()))
    resolve_hint = (
        "This story has run long enough — RESOLVE it now: set arc_stage to 'past' "
        "with a concluding beat."
        if age >= settings.world_tick_resolve_after_ticks
        else "Move the stage forward only when the story earns it; a beat may keep it."
    )
    people = (
        "PEOPLE: the beat's `quotes` are attributable statements (what someone said "
        "about this development). REUSE this story's EXISTING figures — quote them by "
        "their EXACT name:\n"
        f"{_figures_text(figures)}\n"
        "Only introduce a NEW person if the beat truly needs one, then list them in "
        f"`new_figures` (at most {settings.world_tick_advance_new_figures_max}). A "
        f"quote's `figure` must be an existing name or a new one you declare.\n\n"
        if settings.world_tick_figures_enabled
        else ""
    )
    schema = (
        '{"arc_stage": str, '
        '"new_figures": [{"name": str, "role": str, "bio": str, "tags": [str]}], '
        '"beat": {"title": str, "body": str, "beat_kind": str, '
        '"day_offset": int, "hour": int, "planned": bool, '
        '"quotes": [{"figure": str, "text": str, "stance": str}]}}'
        if settings.world_tick_figures_enabled
        else '{"arc_stage": str, "beat": {"title": str, "body": str, '
        '"beat_kind": str, "day_offset": int, "hour": int, "planned": bool}}'
    )
    return (
        "You are the world-simulation engine for Settlement Radio, a tribute "
        f"science-fiction station set in the year {ctx.iw_now.year}. Advance the "
        "running story below by exactly ONE new beat — a development, a consequence, "
        "or a resolution — consistent with the world bible (cached above) and with "
        "the story's OWN prior beats (never contradict them).\n\n"
        f"In-world now: {clock.render_wall_clock(ctx.now)}.\n\n"
        f"STORY: {story.title} — {story.summary}\n"
        f"Current arc stage: {story.arc_stage}\n"
        f"Prior beats (oldest first):\n{_beats_text(beats)}\n\n"
        f"{people}"
        f"{resolve_hint}\n"
        f"Choose the new arc_stage: keep it the same or move FORWARD (one of: "
        f"{forward or 'past'}) — NEVER backward; 'past' resolves the story. day_offset "
        "is whole in-world days from today (within "
        f"±{settings.world_tick_beat_horizon_days}); hour is 0-23.\n\n"
        'Set "planned": true ONLY if you date this beat at an hour still AHEAD of the '
        "in-world clock and it is a step you are scheduling for later today rather "
        "than something that has happened — the news desk holds such a beat until its "
        'hour arrives. A beat that has already happened is "planned": false.\n\n'
        "Return ONLY a JSON object (no prose, no code fence):\n"
        f"{schema}"
    )


def _advance_continuity_system(ctx: _TickContext, adv: ProposedAdvance) -> str:
    """Continuity instructions for an advancement (checks the story's own history)."""
    return (
        "You are the world-continuity editor for Settlement Radio, set in the year "
        f"{ctx.iw_now.year}. The proposed NEXT beat below advances a running story. "
        "Check it against the world bible (cached above), the story's prior beats, and "
        "canon. FLAG it if it contradicts the bible, the story's own history, or the "
        "world's premise, repeats a prior beat, or moves the arc backward. This is "
        "fiction: in-world tension, danger, and loss are fine.\n\n"
        f"STORY SO FAR: {adv.story.title} — {adv.story.summary}\n"
        f"Prior beats (oldest first):\n{_beats_text(adv.prior_beats)}\n\n"
        "Reply with the single word OK if the next beat fits, otherwise 'ISSUES:' "
        "followed by a terse reason. Do not rewrite it."
    )


def _parse_advance(
    raw: str, story: store.Story, prior: list[store.Event]
) -> ProposedAdvance | None:
    """Parse one advancement JSON object into a `ProposedAdvance` (None if junk).

    Validates the arc transition forward-only via `store.can_transition`; an illegal
    or absent stage falls back to the story's current stage (a new beat, no move).
    """
    obj = _extract_json_object(raw)
    if obj is None:
        log.warning(
            "world_tick_advance_parse_failed", story_id=story.id, sample=raw[:160]
        )
        return None
    beat = _coerce_beat(obj.get("beat"))
    if beat is None:
        return None
    new_stage = str(obj.get("arc_stage", "")).strip().lower()
    if new_stage not in store.ARC_STAGES or not store.can_transition(
        story.arc_stage, new_stage
    ):
        new_stage = story.arc_stage  # illegal/backward -> stay put, just add a beat
    new_figures = _coerce_figures(
        obj.get("new_figures"), settings.world_tick_advance_new_figures_max
    )
    return ProposedAdvance(
        story=story,
        prior_beats=prior,
        new_stage=new_stage,
        beat=beat,
        new_figures=new_figures,
    )


# --- Step 3: materialise + write + embed ------------------------------------


def _materialise(
    p: ProposedStory, tick_no: int, ctx: _TickContext, index: int
) -> tuple[store.Story, list[store.Event]]:
    """Turn a gated proposal into a `Story` row + its beat `events` rows (D3.0)."""
    # A run-unique id namespace so a re-run never collides on the PK.
    story_id = f"st-{ctx.now:%Y%m%dT%H%M%S}-{tick_no}-{index}"
    arc_stage = p.arc_stage if p.arc_stage in store.ARC_STAGES else store.ARC_UPCOMING
    tags = list(dict.fromkeys([p.domain, p.scale]))  # dedupe, keep order

    story = store.Story(
        id=story_id,
        title=p.title,
        summary=p.summary,
        arc_stage=arc_stage,
        tags=tags,
        source=store.EVENT_SOURCE_TICK,
        created_tick=tick_no,
        last_advanced_tick=tick_no,
    )
    beats = [_beat_event(story_id, f"b{j}", b, ctx) for j, b in enumerate(p.beats)]
    return story, beats


def _beat_event(
    story_id: str, suffix: str, b: ProposedBeat, ctx: _TickContext
) -> store.Event:
    """Build one beat `events` row from a `ProposedBeat`, clamped + clock-framed.

    `suffix` makes the beat id unique within its story (`b{j}` for a creation beat,
    `a{tick}` for an advancement beat — one per tick per story, so never collides).

    R4.0: a `planned` beat (a same-day arc's later step) keeps the flag only while it
    is genuinely ahead of the clock. A beat the model marked planned but dated at or
    behind now has already landed — there is no hour left to wait for, so it is stored
    as an ordinary beat rather than one the news desk would suppress forever.
    """
    offset = max(
        -settings.world_tick_beat_horizon_days,
        min(settings.world_tick_beat_horizon_days, b.day_offset),
    )
    hour = max(0, min(23, b.hour))
    beat_dt = (ctx.iw_now + timedelta(days=offset)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    beat = store.Event(
        id=f"{story_id}-{suffix}",
        title=b.title,
        body=b.body,
        in_world_datetime=beat_dt,
        status="",  # set live below from the datetime vs the clock
        tags=[t for t in [b.beat_kind] if t],
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind=b.beat_kind,
        planned=b.planned and beat_dt > ctx.iw_now,
    )
    return events_mod.progressed(beat, ctx.now)


def _materialise_people(
    p: ProposedStory, story: store.Story, beats: list[store.Event], tick_no: int
) -> tuple[list[store.Figure], list[store.Quote]]:
    """Turn a new story's proposed figures + per-beat quotes into rows (D10.1).

    Figures are created once (id `{story}-fig{n}`), so a person quoted across several
    beats maps to ONE figure row. Quotes resolve their `figure` name against the story's
    declared figures and inherit their beat's in-world datetime (clock-frameable); a
    quote naming an undeclared figure is dropped (no attributing to a non-existent one).
    """
    if not settings.world_tick_figures_enabled:
        return [], []
    figures = [
        store.Figure(
            id=f"{story.id}-fig{n}",
            name=f.name,
            role=f.role,
            card_text=f.bio,
            tags=f.tags,
            source=store.FIGURE_SOURCE_TICK,
        )
        for n, f in enumerate(p.figures)
    ]
    name_to_id = {f.name.strip().lower(): f.id for f in figures}
    quotes = _quote_rows(story.id, beats, p.beats, name_to_id)
    return figures, quotes


def _advance_people(
    adv: ProposedAdvance,
    beat: store.Event,
    existing: list[store.Figure],
    tick_no: int,
) -> tuple[list[store.Figure], list[store.Quote]]:
    """Build the NEW figures + quotes an advancement adds (D10.1).

    A continuing story REUSES its existing figures: a quote naming one resolves to the
    stored figure id (no new row). Only genuinely new names declared in `new_figures`
    become new figure rows (id `{story}-fig-a{tick}-{n}`), and only if they don't
    collide with an existing name. Quotes attach to the new advancement `beat`.
    """
    if not settings.world_tick_figures_enabled:
        return [], []
    name_to_id = {f.name.strip().lower(): f.id for f in existing}
    new_figures: list[store.Figure] = []
    for n, f in enumerate(adv.new_figures):
        key = f.name.strip().lower()
        if not key or key in name_to_id:
            continue  # blank, or already exists -> reuse, don't duplicate
        fig = store.Figure(
            id=f"{adv.story.id}-fig-a{tick_no}-{n}",
            name=f.name,
            role=f.role,
            card_text=f.bio,
            tags=f.tags,
            source=store.FIGURE_SOURCE_TICK,
        )
        new_figures.append(fig)
        name_to_id[key] = fig.id
    quotes = _quote_rows(adv.story.id, [beat], [adv.beat], name_to_id)
    return new_figures, quotes


def _quote_rows(
    story_id: str,
    beats: list[store.Event],
    proposed: list[ProposedBeat],
    name_to_id: dict[str, str],
) -> list[store.Quote]:
    """Resolve proposed quotes to `Quote` rows, dropping any with an unknown figure.

    `beats` (the materialised `events`) and `proposed` (their `ProposedBeat` sources)
    are parallel; a quote takes its beat's `in_world_datetime` so the clock frames it.
    """
    rows: list[store.Quote] = []
    for beat, pb in zip(beats, proposed, strict=True):
        for m, q in enumerate(pb.quotes):
            figure_id = name_to_id.get(q.figure.strip().lower())
            if figure_id is None:
                log.warning(
                    "world_tick_quote_unattributed", figure=q.figure[:80], beat=beat.id
                )
                continue
            rows.append(
                store.Quote(
                    id=f"{beat.id}-q{m}",
                    story_id=story_id,
                    figure_id=figure_id,
                    text=q.text,
                    in_world_datetime=beat.in_world_datetime,
                    beat_id=beat.id,
                    stance=q.stance,
                    source=store.FIGURE_SOURCE_TICK,
                )
            )
    return rows


def _write_people(
    conn,
    figures: list[store.Figure],
    quotes: list[store.Quote],
    result: TickResult | MicroTickResult,
) -> None:
    """Write a story's figures + quotes, embed them (D10.1); update usage counters.

    Shared by the nightly tick and the R4.1 micro-tick — both carry a `usage` dict.
    """
    if figures:
        store.insert_figures(conn, figures)
        result.usage["figures_written"] = result.usage.get("figures_written", 0) + len(
            figures
        )
    if quotes:
        store.insert_quotes(conn, quotes)
        result.usage["quotes_written"] = result.usage.get("quotes_written", 0) + len(
            quotes
        )
    result.usage["embeddings_written"] = (
        result.usage.get("embeddings_written", 0)
        + _embed_figures(conn, figures)
        + _embed_quotes(conn, quotes)
    )


def _embed_figures(conn, figures: list[store.Figure]) -> int:
    """Embed figures into the D2 `figure` corpus (source='tick'); degrade on failure."""
    if not figures:
        return 0
    try:
        texts = [f"{f.name}. {f.role}. {f.card_text}" for f in figures]
        vecs = embeddings.embed(texts)
        rows = [
            store.EmbeddingRow(
                entity_id=f.id,
                text=t,
                source=store.FIGURE_SOURCE_TICK,
                embedding=vec,
                tags=f.tags,
            )
            for f, t, vec in zip(figures, texts, vecs, strict=True)
        ]
        return store.insert_embeddings(conn, "figure", rows)
    except Exception as exc:  # noqa: BLE001 — D2 is a recall aid, not a hard dep
        log.warning(
            "world_tick_embed_figures_failed", count=len(figures), error=str(exc)
        )
        return 0


def _embed_quotes(conn, quotes: list[store.Quote]) -> int:
    """Embed quotes into the D2 `quote` corpus (source='tick'); degrade on failure."""
    if not quotes:
        return 0
    try:
        vecs = embeddings.embed([q.text for q in quotes])
        rows = [
            store.EmbeddingRow(
                entity_id=q.id,
                text=q.text,
                source=store.FIGURE_SOURCE_TICK,
                embedding=vec,
                tags=q.tags,
            )
            for q, vec in zip(quotes, vecs, strict=True)
        ]
        return store.insert_embeddings(conn, "quote", rows)
    except Exception as exc:  # noqa: BLE001 — D2 is a recall aid, not a hard dep
        log.warning("world_tick_embed_quotes_failed", count=len(quotes), error=str(exc))
        return 0


def _embed_beats(conn, beats: list[store.Event]) -> int:
    """Embed beats into the D2 `event` corpus (`source='tick'`); degrade on failure."""
    if not beats:
        return 0
    try:
        vecs = embeddings.embed([f"{b.title}. {b.body}" for b in beats])
        rows = [
            store.EmbeddingRow(
                entity_id=b.id,
                text=f"{b.title}. {b.body}",
                source=store.EVENT_SOURCE_TICK,
                embedding=vec,
                tags=b.tags,
            )
            for b, vec in zip(beats, vecs, strict=True)
        ]
        return store.insert_embeddings(conn, "event", rows)
    except Exception as exc:  # noqa: BLE001 — D2 is a recall aid, not a hard dep
        log.warning("world_tick_embed_beats_failed", count=len(beats), error=str(exc))
        return 0


def _embed_story(conn, story: store.Story) -> int:
    """Embed a story into the D2 `story` corpus (source='tick'); degrade on failure."""
    try:
        vec = embeddings.embed([f"{story.title}. {story.summary}"])[0]
        return store.insert_embeddings(
            conn,
            "story",
            [
                store.EmbeddingRow(
                    entity_id=story.id,
                    text=f"{story.title}. {story.summary}",
                    source=store.EVENT_SOURCE_TICK,
                    embedding=vec,
                    tags=story.tags,
                )
            ],
        )
    except Exception as exc:  # noqa: BLE001 — D2 is a recall aid, not a hard dep
        log.warning("world_tick_embed_story_failed", story_id=story.id, error=str(exc))
        return 0


def _finish_conn(conn, tick_no: int, now: datetime) -> None:
    store.set_state(conn, _TICK_COUNT_KEY, str(tick_no))
    store.set_state(conn, _TICK_LAST_AT_KEY, now.isoformat())


# --- Helpers ----------------------------------------------------------------


def _summarise_active(stories: list[store.Story]) -> str:
    """A compact list of running stories for the proposal/continuity context."""
    return "\n".join(f"- [{s.arc_stage}] {s.title} — {s.summary}" for s in stories)


# --- Variety: domain balance + de-duplication (D3.3) ------------------------


def _quiet_domains(recent: list[store.Story], k: int) -> list[str]:
    """The `k` domains least-used across `recent` stories (the anti-clustering steer).

    Counts each story's domain tags (the D1 cornerstones) over the recency window and
    returns the quietest, so successive ticks rotate toward neglected ground rather
    than circling the same few topics.
    """
    counts = dict.fromkeys(DOMAINS, 0)
    for s in recent:
        for tag in s.tags:
            if tag in counts:
                counts[tag] += 1
    return sorted(DOMAINS, key=lambda d: (counts[d], d))[:k]


def _dedup(
    accepted: list[ProposedStory], recent: list[store.Story], result: TickResult
) -> list[ProposedStory]:
    """Drop proposals too close to an existing or already-kept story (D3.3).

    Two checks: SEMANTIC (D2 recall over the persisted `story` corpus) catches a
    meaning-level repeat of a prior-tick story; STRUCTURAL (title/summary token
    overlap) catches within-batch siblings AND is the functional fallback when D2 is
    unavailable (`embeddings.retrieve` degrades to `[]`). Rejected, not folded — the
    simplest way to guarantee no near-duplicate stories.
    """
    kept: list[ProposedStory] = []
    seen = [f"{s.title}. {s.summary}" for s in recent]
    for p in accepted:
        text = f"{p.title}. {p.summary}"
        if _semantic_dup(text) or _jaccard_dup(text, seen):
            result.duplicates += 1
            log.info("world_tick_dedup_rejected", title=p.title)
            continue
        kept.append(p)
        seen.append(text)  # later siblings de-dup against earlier kept ones too
    return kept


def _semantic_dup(text: str) -> bool:
    """True if `text` is within the cosine threshold of a persisted story (D2)."""
    hits = embeddings.retrieve(text, k=1, corpus="story")
    return bool(hits) and hits[0].score >= settings.world_tick_dedup_threshold


def _jaccard_dup(text: str, existing: list[str]) -> bool:
    """True if `text` overlaps any of `existing` above the Jaccard threshold."""
    t = _word_set(text)
    return any(
        _jaccard(t, _word_set(e)) >= settings.world_tick_dedup_jaccard for e in existing
    )


def _word_set(s: str) -> set[str]:
    """Lowercase word tokens of `s`, for structural similarity."""
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard overlap of two token sets (0.0 when either is empty)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _story_text(p: ProposedStory) -> str:
    """The gate's view of a proposal: title, summary, figures, beats, and quotes.

    Figures + quotes are included so the SAME safety + continuity gate that vets the
    story also vets its people and what they say (D10.1) — a flagged figure or quote
    flags (then regenerates/drops) the whole proposal; nothing bad is written.
    """
    lines = [f"{p.title} — {p.summary}"]
    lines += [f"  PERSON {f.name} ({f.role}): {f.bio}" for f in p.figures]
    for b in p.beats:
        lines.append(f"  [{b.beat_kind}] {b.title}: {b.body}")
        lines += [f'    {q.figure} said: "{q.text}"' for q in b.quotes]
    return "\n".join(lines)


def _advance_text(adv: ProposedAdvance) -> str:
    """The gate's view of an advancement: story, next beat, new people + quotes."""
    lines = [
        f"Advancing: {adv.story.title} (-> {adv.new_stage})",
        f"Next beat [{adv.beat.beat_kind}] {adv.beat.title}: {adv.beat.body}",
    ]
    lines += [f"  NEW PERSON {f.name} ({f.role}): {f.bio}" for f in adv.new_figures]
    lines += [f'  {q.figure} said: "{q.text}"' for q in adv.beat.quotes]
    return "\n".join(lines)


def _beats_text(beats: list[store.Event]) -> str:
    """Render a story's prior beats for the advance/continuity prompts.

    A `planned` beat (R4.0) is labelled as such, so the writer advancing the story
    knows which of its history has actually happened and which is still the day's
    plan — and doesn't write a beat that contradicts or pre-empts one.
    """
    if not beats:
        return "  (none yet)"
    return "\n".join(
        f"  [{b.beat_kind or 'beat'}{', PLANNED for later' if b.planned else ''}] "
        f"{b.title}: {b.body}"
        for b in beats
    )


def _figures_text(figures: list[store.Figure]) -> str:
    """Render a story's existing figures (name — role) for the advance reuse prompt."""
    if not figures:
        return "  (none yet)"
    return "\n".join(f"  {f.name} — {f.role}" for f in figures)


def _is_ok(note: str) -> bool:
    """True when a continuity note signals no problems (starts with 'OK')."""
    return note.strip().upper().startswith("OK")


def _parse_proposals(raw: str) -> list[ProposedStory]:
    """Parse the model's JSON array into stories, skipping malformed entries."""
    data = _extract_json_array(raw)
    if data is None:
        log.warning("world_tick_parse_failed", sample=raw[:200])
        return []
    out: list[ProposedStory] = []
    for item in data:
        story = _coerce_story(item)
        if story is not None:
            out.append(story)
    return out


def _extract_json_array(raw: str) -> list | None:
    """Pull the model's JSON array of stories out, tolerating fences, prose, AND a
    response truncated at `max_tokens` mid-array.

    Tries a clean parse first; otherwise SALVAGES every complete top-level object
    (`_salvage_json_objects`) — so a batch where the final object got cut off still
    yields the complete ones rather than dropping the whole array. Returns the list of
    objects, or None if nothing parseable is present.
    """
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    objs = _salvage_json_objects(text)
    return objs or None


def _extract_json_object(raw: str) -> dict | None:
    """Pull a single JSON object out of model output (fence/prose/cut-off tolerant)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip()).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    objs = _salvage_json_objects(text)
    return objs[0] if objs else None


def _salvage_json_objects(text: str) -> list[dict]:
    """Every complete, balanced top-level `{...}` object in `text`, parsed in order.

    A brace scanner that respects string literals/escapes, so it skips braces inside
    quoted values and ignores an incomplete trailing object (the common shape when the
    model is cut off at `max_tokens`). Each fragment is parsed independently; an
    unparseable fragment is dropped rather than sinking the whole batch.
    """
    objs: list[dict] = []
    depth = 0
    start: int | None = None
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    parsed = json.loads(text[start : i + 1])
                    if isinstance(parsed, dict):
                        objs.append(parsed)
                except json.JSONDecodeError:
                    pass
                start = None
    return objs


def _coerce_story(item: object) -> ProposedStory | None:
    """Validate/normalise one parsed object into a `ProposedStory`, or None if junk."""
    if not isinstance(item, dict):
        return None
    title = str(item.get("title", "")).strip()
    summary = str(item.get("summary", "")).strip()
    raw_beats = item.get("beats")
    if not title or not summary or not isinstance(raw_beats, list) or not raw_beats:
        return None
    beats = [b for b in (_coerce_beat(rb) for rb in raw_beats) if b is not None]
    if not beats:
        return None
    scale = str(item.get("scale", "small")).strip().lower()
    scale = scale if scale in ("large", "small") else "small"
    domain = str(item.get("domain", "")).strip().lower() or "culture"
    arc_stage = str(item.get("arc_stage", "")).strip().lower()
    figures = _coerce_figures(
        item.get("figures"), settings.world_tick_figures_per_story_max
    )
    return ProposedStory(
        title=title,
        summary=summary,
        scale=scale,
        domain=domain,
        arc_stage=arc_stage,
        beats=_cap_story_quotes(beats, settings.world_tick_quotes_per_story_max),
        figures=figures,
    )


def _coerce_beat(item: object) -> ProposedBeat | None:
    """Validate/normalise one parsed beat dict into a ProposedBeat, or None if junk."""
    if not isinstance(item, dict):
        return None
    title = str(item.get("title", "")).strip()
    body = str(item.get("body", "")).strip()
    if not title or not body:
        return None
    quotes = [
        q for q in (_coerce_quote(rq) for rq in _as_list(item.get("quotes"))) if q
    ]
    return ProposedBeat(
        title=title,
        body=body,
        beat_kind=str(item.get("beat_kind", "development")).strip() or "development",
        day_offset=_as_int(item.get("day_offset"), 0),
        hour=_as_int(item.get("hour"), 12),
        quotes=quotes,
        planned=bool(item.get("planned", False)),
    )


def _coerce_figure(item: object) -> ProposedFigure | None:
    """Validate/normalise one parsed figure dict into a `ProposedFigure`, or None."""
    if not isinstance(item, dict):
        return None
    name = str(item.get("name", "")).strip()
    role = str(item.get("role", "")).strip()
    if not name or not role:
        return None  # a figure needs a name to be quoted and a role to be placed
    tags = [str(t).strip() for t in _as_list(item.get("tags")) if str(t).strip()]
    return ProposedFigure(
        name=name, role=role, bio=str(item.get("bio", "")).strip(), tags=tags
    )


def _coerce_figures(raw: object, cap: int) -> list[ProposedFigure]:
    """Coerce + cap a list of proposed figures (drops junk, bounds the volume)."""
    if not settings.world_tick_figures_enabled:
        return []
    figs = [f for f in (_coerce_figure(r) for r in _as_list(raw)) if f]
    return figs[:cap]


def _coerce_quote(item: object) -> ProposedQuote | None:
    """Validate/normalise one parsed quote dict into a `ProposedQuote`, or None."""
    if not settings.world_tick_figures_enabled or not isinstance(item, dict):
        return None
    figure = str(item.get("figure", "")).strip()
    text = str(item.get("text", "")).strip()
    if not figure or not text:
        return None  # an unattributed or empty quote is unusable
    stance = str(item.get("stance", "")).strip() or None
    return ProposedQuote(figure=figure, text=text, stance=stance)


def _cap_story_quotes(beats: list[ProposedBeat], cap: int) -> list[ProposedBeat]:
    """Bound a story's TOTAL quotes to `cap`, trimming across beats (oldest kept first).

    The per-story dial is a whole-story budget, but quotes live under beats; this spends
    the budget beat-by-beat and drops the overflow so a story has a FEW voices, not a
    crowd.
    """
    remaining = cap
    out: list[ProposedBeat] = []
    for b in beats:
        if remaining <= 0:
            out.append(replace(b, quotes=[]))
            continue
        kept = b.quotes[:remaining]
        remaining -= len(kept)
        out.append(replace(b, quotes=kept))
    return out


def _as_int(value: object, default: int) -> int:
    """Best-effort int coercion (the model may emit a string or float)."""
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _as_list(value: object) -> list:
    """A list as-is, else empty — for optional array fields the model may omit."""
    return value if isinstance(value, list) else []


# --- CLI (D3.4): the nightly job C5's cron/systemd runs ---------------------


def main() -> int:
    """Run one world tick from the CLI; print a summary; return a process exit code.

    `python -m src.world.world_tick` / `make world-tick`. One-shot by design: the
    tick is the nightly WORLD-STATE batch, scheduled by the C5 cron/systemd timer
    (cadence + bounds are the `world_tick_*` settings, not a loop here). A failure is
    logged loudly and returns NON-ZERO so the timer can alert — but never corrupts the
    store, because `run_tick` does all its writes inside one `store.connect`
    transaction that rolls back on any error.

    Relationship to the C2 scheduler (kept SEPARATE — do not fold the tick into
    `scheduler.top_up`): the tick WRITES world state (stories/beats); the scheduler
    READS it to make audio and fill the rolling buffer. On the box both run on their
    own timers — the nightly tick feeds the buffer the scheduler tops up.
    """
    from .. import usage

    try:
        with usage.job("tick"):
            r = run_tick()
    except Exception as exc:  # noqa: BLE001 — fail loud for the timer; store rolled back
        log.error("world_tick_failed", error=str(exc))
        usage.flush()  # money spent on batch calls even if the tick rolled back
        print(f"World tick FAILED (store unchanged): {exc}")
        return 1
    usage.flush()  # R5.1 — persist the tick's LLM spend to the usage rollup

    print(
        f"\nWorld tick #{r.tick}: proposed {r.proposed}, accepted {r.accepted}, "
        f"dropped {r.dropped} (regenerated {r.regenerated}, "
        f"duplicates {r.duplicates}); advanced {r.advanced} "
        f"running stor{'y' if r.advanced == 1 else 'ies'} ({r.resolved} resolved)."
    )
    for sid in r.story_ids:
        print(f"  + {sid}  (new)")
    for sid in r.advanced_ids:
        print(f"  ~ {sid}  (advanced)")
    return 0


if __name__ == "__main__":
    # .venv/bin/python -m src.world.world_tick   (or: make world-tick)
    # Needs `make seed` + a populated .env. LLM_BATCH_ENABLED=false for a quick,
    # synchronous local run (no async batch wait); default True takes the 50% Batch
    # discount on the box.
    raise SystemExit(main())

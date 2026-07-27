"""Q0.1 — the API probe: the §1 numbers that only real generation can produce.

The free metrics (Q0.0) measure the machinery. This measures the *writing* — and there
is no way to do that without spending tokens, because a probe that mocks `llm.generate`
measures nothing. So `collect_probe` runs the REAL pipeline (`context.assemble` →
`conversation.showrunner` → `conversation.orchestrate`) with only the things that cost
money-for-nothing removed:

  * **TTS is mocked** — the audit is about scripts; synthesising them proves nothing and
    would dominate the bill.
  * **Every DB write lands in ONE rolled-back transaction** (the
    `acceptance.py::_sim_environment` pattern), so the world is byte-identical after.
    Unlike the acceptance sim, this probe does **not** delete and regenerate the world:
    it is measuring the world as it actually is tonight.
  * **`segments/`, the real schedule, airplay and the journal are never touched** — the
    paths are redirected into a temp dir and the txn covers the rest.

Four parts, matching §1's findings:

1. **Contrastive** (§1a) — four FIXED slots on four contrasting shows, generated `runs`
   times in independent contexts. The finding this exists to catch: three of four shows
   led on the same story, twice, with no shared state. `topic.*`.
2. **Register** (§1d) — the turn shape and plain-speech counters over every script the
   run generated. `register.*`.
3. **Continuity** (§1e) — five consecutive slots of one programme through the real
   `ShowFlow`, looking for the verbatim replay of the previous slot's close.
   `continuity.*`.
4. **Prompt shape** (§1f) — what each call actually shipped and how long it took, read
   off the usage listener and a wall clock. `context.*`.

**The pinned inputs are load-bearing.** `_SLOTS`, `_CONTINUITY_START` and the gap
between slots must not drift: Q8 re-runs this probe and compares to the committed
baseline, and a different slot list makes the comparison meaningless.

Cost: `--dry-run` prints the plan and spends nothing. A real run prints its estimate
before it starts.

    make audit-full                 # free metrics + this probe
    .venv/bin/python -m src.audit --full --dry-run
"""

from __future__ import annotations

import contextlib
import statistics
import tempfile
import time
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from ..config import settings
from ..flow import CLOSE, CONTINUE, OPEN, ShowFlow
from ..logging_setup import get_logger
from . import metrics, textstats

log = get_logger(__name__)

# THE FIXED SLOT LIST (§1a / seed README §2). Four contrasting shows on one Monday: the
# flagship, an economics vertical, a sports vertical, and the night. Q8 must reproduce
# these exactly — do not "refresh" the date.
_SLOTS: tuple[tuple[str, str], ...] = (
    ("2026-07-27T07:12", "morning_currents"),
    ("2026-07-27T10:12", "the_exchange"),
    ("2026-07-27T16:12", "the_circuit"),
    ("2026-07-27T22:12", "long_night"),
)

# The continuity run: five consecutive slots of one two-host programme, the shape
# `src/continuity_demo.py` drives. The Far Towns (Wed 10:00) is the programme §1e caught
# replaying its own close, so the probe watches the same show.
_CONTINUITY_START = datetime(2026, 7, 29, 10, 6)
_CONTINUITY_PROGRAM = "the_far_towns"
_CONTINUITY_SLOTS = 5
_CONTINUITY_GAP = timedelta(minutes=12)

# The grid energies R1 calls daytime — where the house-poetry ban must hold (§2b).
_DAYTIME_ENERGIES = frozenset({"steady", "bright"})

# Repetition n-gram width. Eight words is long enough that a shared run is a quotation
# rather than a turn of phrase two people might both reach for.
_NGRAM = 8


# --- isolation --------------------------------------------------------------


class _MockTTS:
    """A TTS stand-in that writes one byte and reports a plausible spoken duration."""

    _SEC_PER_WORD = 0.42  # ~145 wpm

    def __init__(self) -> None:
        self.durations: dict[str, float] = {}
        self.calls = 0

    def synthesize(self, text, *, voice, emotion=None, out_path):  # noqa: ANN001
        self.calls += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"\x00")
        self.durations[str(out_path)] = max(2.0, len(text.split()) * self._SEC_PER_WORD)
        return out_path

    def concat_audio(self, parts, out_path):  # noqa: ANN001
        return self._join(parts, out_path)

    def join_clips(self, paths, out_path):  # noqa: ANN001
        return self._join(paths, out_path)

    def _join(self, parts, out_path):  # noqa: ANN001
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"\x00")
        self.durations[str(out_path)] = sum(
            self.durations.get(str(p), 30.0) for p in parts
        )
        return out_path

    def probe_duration(self, path):  # noqa: ANN001
        return self.durations.get(str(path), 30.0)


class CallLog:
    """Per-call token split + wall clock for every real `llm.generate` call (§1f)."""

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self._usage: dict = {}

    def listener(self, event: dict) -> None:
        self._usage = dict(event)

    def wrap(self, real):  # noqa: ANN001, ANN201
        def timed(*args, **kwargs):
            self._usage = {}
            started = time.monotonic()
            try:
                return real(*args, **kwargs)
            finally:
                self.rows.append(
                    {"seconds": round(time.monotonic() - started, 2), **self._usage}
                )

        return timed

    def context_metrics(self) -> dict:
        """The §1f trio, over the calls whose cache was already warm.

        Filtering to `cache_read_input_tokens > 0` matters: the FIRST call of a run pays
        cache *creation* and would drag the median of a number that is supposed to
        describe steady-state production. Medians, not means, so one long call doesn't
        colour the latency figure.
        """
        warm = [r for r in self.rows if (r.get("cache_read_input_tokens") or 0) > 0]
        pool = warm or self.rows
        if not pool:
            return {}
        return {
            "cached_tokens": int(
                statistics.median(r.get("cache_read_input_tokens") or 0 for r in pool)
            ),
            "uncached_tokens": int(
                statistics.median(r.get("input_tokens") or 0 for r in pool)
            ),
            "seconds_per_call": round(
                statistics.median(r.get("seconds") or 0.0 for r in pool), 1
            ),
            "calls": len(self.rows),
            "warm_calls": len(warm),
        }


@contextlib.contextmanager
def isolated() -> Iterator[tuple[_MockTTS, CallLog]]:
    """Real Claude, mocked TTS, every write inside one rolled-back transaction.

    Yields `(tts, calls)` for telemetry. The world is left exactly as it was found: no
    deletes going in (unlike the acceptance sim, this probe measures tonight's real
    world), and a rollback coming out.
    """
    from ..production import mix as mix_mod
    from ..providers import llm as llm_mod
    from ..providers import tts as tts_mod
    from ..world import store

    cm = store.connect()
    conn = cm.__enter__()

    @contextlib.contextmanager
    def fake_connect() -> Iterator:
        yield conn  # shared + uncommitted: every write lands in the one rolled-back txn

    tts = _MockTTS()
    calls = CallLog()
    tmp = Path(tempfile.mkdtemp(prefix="sr-audit-probe-"))
    segdir = tmp / "segments"
    segdir.mkdir(parents=True, exist_ok=True)

    llm_mod.add_usage_listener(calls.listener)
    with contextlib.ExitStack() as stack:
        p = stack.enter_context
        p(mock.patch.object(store, "connect", fake_connect))
        # `llm.generate` stays REAL — only wrapped, to time it.
        p(mock.patch.object(llm_mod, "generate", calls.wrap(llm_mod.generate)))
        p(mock.patch.object(tts_mod, "synthesize", tts.synthesize))
        p(mock.patch.object(tts_mod, "concat_audio", tts.concat_audio))
        p(mock.patch.object(tts_mod, "probe_duration", tts.probe_duration))
        p(mock.patch.object(mix_mod, "join_clips", tts.join_clips))
        p(mock.patch.object(settings, "segments_dir", segdir))
        p(mock.patch.object(settings, "schedule_state_path", segdir / "schedule.json"))
        p(
            mock.patch.object(
                settings, "schedule_playlist_path", segdir / "playlist.txt"
            )
        )
        p(mock.patch.object(settings, "llm_batch_enabled", False))
        # A stalled stream must not be able to hang the whole audit — see the setting's
        # note. Scoped to the probe; the live station's timeout is untouched.
        p(
            mock.patch.object(
                settings, "llm_timeout_sec", settings.audit_probe_llm_timeout_sec
            )
        )
        p(mock.patch.object(settings, "production_bedded_programs", []))
        try:
            yield tts, calls
        finally:
            llm_mod.remove_usage_listener(calls.listener)
            conn.rollback()
            with contextlib.suppress(Exception):
                cm.__exit__(None, None, None)


# --- one generated segment --------------------------------------------------


def _hosts_for(program) -> list[str]:  # noqa: ANN001
    """The programme's two-host pair; falls back to the default room for a solo show."""
    hosts = list(program.hosts)[:2]
    return hosts if len(hosts) >= 2 else list(settings.convo_speaker_ids)


def _generate(now: datetime, flow: ShowFlow, program) -> tuple[str, str]:  # noqa: ANN001
    """One talk segment through the real writers' room: returns `(beat, script)`."""
    from ..formats import talk as talk_fmt
    from ..world import context
    from ..writers import conversation as convo

    ctx = context.assemble(now, speakers=_hosts_for(program), domains=program.domains)
    beat = convo.showrunner(ctx, now, flow=flow, program=program)
    script = convo.orchestrate(
        ctx,
        beat,
        now,
        extra_directive=talk_fmt._backbone_for(flow),
        flow=flow,
        program=program,
        # Pass the grid's own item length through, exactly as the seed probe did (0 is
        # falsy and leaves the default word dials alone) — so the word budgets, and
        # therefore the register numbers, are comparable with the baseline.
        length_target_sec=program.talk_length_sec,
    )
    return beat, script


# --- part 1: the contrastive probe (§1a) ------------------------------------


def contrastive(runs: int) -> list[dict]:
    """Generate the fixed slot list `runs` times, each in an independent context.

    Independence is the whole finding: nothing is shared between runs but the world
    itself, so two runs agreeing on the beat means the *supply* left no other choice.
    """
    from ..world import programming

    out: list[dict] = []
    for run in range(1, runs + 1):
        for iso, expected_program in _SLOTS:
            now = datetime.fromisoformat(iso)
            program = programming.program_for(now)
            if program.id != expected_program:
                # The grid moved under the pinned slot list; measure it, but say so —
                # the Q8 comparison depends on these being the same four shows.
                log.warning(
                    "audit_probe_slot_drift",
                    slot=iso,
                    expected=expected_program,
                    actual=program.id,
                )
            flow = ShowFlow(
                position=OPEN,
                handoff=None,
                thread_run=0,
                continue_thread=False,
                program_name=program.name,
            )
            beat, script = _generate(now, flow, program)
            out.append(
                {
                    "run": run,
                    "slot": iso,
                    "program": program.id,
                    "energy": program.energy,
                    "beat": beat,
                    "script": script,
                }
            )
            log.info(
                "audit_probe_segment",
                part="contrastive",
                run=run,
                slot=iso,
                program=program.id,
                script_chars=len(script),
            )
    return out


def topic_metrics(segments: list[dict], runs: int) -> dict:
    """`topic.*` — how concentrated the station's subject matter is (§1a)."""
    vocabulary, cast = metrics.world_vocabulary()
    per_slot: dict[str, list[str | None]] = {}
    total: Counter = Counter()
    distinct: list[int] = []

    for seg in segments:
        counts = textstats.entity_counts(
            f"{seg['beat']}\n{seg['script']}", vocabulary, exclude=cast
        )
        total += counts
        distinct.append(len(counts))
        top = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0] if counts else None
        per_slot.setdefault(seg["slot"], []).append(top)
        seg["dominant_entity"] = top

    # A slot "agrees across runs" when every run of it named the same dominant entity.
    comparable = [v for v in per_slot.values() if len(v) > 1 and any(v)]
    agreed = sum(1 for v in comparable if len(set(v)) == 1)
    mentions = sum(total.values())
    top_entity, top_total = (
        max(total.items(), key=lambda kv: (kv[1], kv[0])) if total else (None, 0)
    )
    # PER RUN, not per probe. §1a's headline ("Cold Harbor is named 23 times") counted
    # ONE pass of the four slots, so an absolute total would double with `--runs 2` and
    # the ≤12 gate would be measuring the probe's size instead of the station's
    # concentration. Divide by the runs and the number means the same thing either way.
    passes = max(1, runs)
    return {
        "cross_run_beat_identity_pct": (
            round(100 * agreed / len(comparable), 1) if comparable else None
        ),
        "top_entity": top_entity,
        "top_entity_mentions": round(top_total / passes, 1),
        "top_entity_mentions_total": top_total,
        "top_entity_share": (
            round(100 * top_total / mentions, 1) if mentions else None
        ),
        "distinct_entities_per_segment": (
            round(statistics.mean(distinct), 2) if distinct else None
        ),
        "entity_mentions_total": mentions,
        "top_entities": dict(total.most_common(10)),
        "segments": len(segments),
        "runs": runs,
    }


# --- part 2: the register probe (§1d) --------------------------------------


def register_metrics(segments: list[dict]) -> dict:
    """`register.*` — is this plain speech, or plain prose? (§1d)"""
    from ..writers.conversation import BANNED_ABSTRACTIONS

    scripts = [s["script"] for s in segments]
    daytime = [s["script"] for s in segments if s.get("energy") in _DAYTIME_ENERGIES]
    hits = textstats.banned_abstraction_hits(daytime, BANNED_ABSTRACTIONS)
    return {
        **textstats.script_register(scripts),
        "banned_abstractions_daytime": len(hits),
        "banned_phrases_found": hits,
        "daytime_segments": len(daytime),
    }


# --- part 3: the continuity probe (§1e) ------------------------------------


def continuity_run() -> list[dict]:
    """Five consecutive slots of one programme, carrying the real hand-off forward.

    Reproduces what the scheduler does per slot (the `continuity_demo.py` shape): derive
    the position, thread the `Handoff`, decide whether to continue — so the D12 pickup
    path is genuinely under test rather than five standalone segments.
    """
    from .. import flow as flow_mod
    from ..segment import Segment
    from ..world import programming

    program = programming.program_for(_CONTINUITY_START)
    if program.id != _CONTINUITY_PROGRAM:
        log.warning(
            "audit_probe_slot_drift",
            slot=_CONTINUITY_START.isoformat(),
            expected=_CONTINUITY_PROGRAM,
            actual=program.id,
        )
    out: list[dict] = []
    handoff = None
    thread_run = 0
    for i in range(_CONTINUITY_SLOTS):
        now = _CONTINUITY_START + i * _CONTINUITY_GAP
        position = OPEN if i == 0 else CLOSE if i == _CONTINUITY_SLOTS - 1 else CONTINUE
        continue_thread = (
            settings.convo_continuity_enabled
            and position != OPEN
            and handoff is not None
            and handoff.open_thread
            and thread_run < settings.convo_continuity_max_segments
        )
        flow = ShowFlow(
            position=position,
            handoff=handoff,
            thread_run=thread_run,
            continue_thread=continue_thread,
            program_name=program.name,
        )
        beat, script = _generate(now, flow, program)
        out.append(
            {
                "slot": now.isoformat(timespec="minutes"),
                "program": program.id,
                "energy": program.energy,
                "position": position,
                "continued": continue_thread,
                "beat": beat,
                "script": script,
            }
        )
        log.info(
            "audit_probe_segment",
            part="continuity",
            slot=now.isoformat(timespec="minutes"),
            position=position,
            continued=continue_thread,
        )
        seg = Segment(
            id=f"audit-continuity-{i}",
            format="talk",
            length_target_sec=program.talk_length_sec
            or settings.segment_default_length_target_sec,
            air_time=now.isoformat(),
            script=script,
            meta={"beat": beat},
        )
        new_handoff = flow_mod.handoff_from_segment(
            seg, program.id, position=position, prev=handoff, continued=continue_thread
        )
        if new_handoff is None:
            thread_run = 0
        elif continue_thread:
            thread_run += 1
        else:
            thread_run = 1
        handoff = new_handoff
    return out


def continuity_metrics(segments: list[dict]) -> dict:
    """`continuity.*` — does a continuing slot move forward, or re-read the close? (§1e)

    `distinct_beats_in_run` counts distinct DOMINANT ENTITIES across the run's beats,
    not distinct beat strings: two beats worded differently about the same story are one
    subject, which is exactly what the §1e finding (three slots on one cook) was about.
    """
    if len(segments) < 2:
        return {"slots": len(segments)}
    vocabulary, cast = metrics.world_vocabulary()
    overlaps: list[int] = []
    rates: list[float] = []
    for prev, cur in zip(segments, segments[1:], strict=False):
        overlaps.append(
            textstats.longest_common_substring_len(cur["script"], prev["script"])
        )
        rate = textstats.repeated_ngram_rate(cur["script"], prev["script"], n=_NGRAM)
        if rate is not None:
            rates.append(rate)
    subjects = []
    for seg in segments:
        top = textstats.dominant_entity(
            seg["beat"], seg["script"], vocabulary=vocabulary, exclude=cast
        )
        seg["dominant_entity"] = top
        subjects.append(top)
    return {
        "max_verbatim_overlap_chars": max(overlaps),
        "mean_verbatim_overlap_chars": round(statistics.mean(overlaps), 1),
        "repeated_ngram_rate": round(max(rates), 2) if rates else None,
        "mean_repeated_ngram_rate": round(statistics.mean(rates), 2) if rates else None,
        "distinct_beats_in_run": len({s for s in subjects if s}),
        "slots": len(segments),
        "program": segments[0]["program"],
    }


# --- the plan (what this is about to cost) ---------------------------------


def plan(runs: int = 2, *, continuity: bool = True) -> dict:
    """What a probe run will generate and roughly what it will cost, before it starts.

    The per-segment figure is the *measured* one from the usage ledger (`cost.*`), so
    the estimate tracks reality — including after Q2 takes it down by ~80%.
    """
    segments = len(_SLOTS) * runs + (_CONTINUITY_SLOTS if continuity else 0)
    try:
        per_segment = metrics.cost_metrics().get("usd_per_talk_segment")
    except Exception as exc:  # noqa: BLE001 — no ledger yet is not a failure
        log.warning("audit_plan_cost_unknown", error=str(exc))
        per_segment = None
    calls = segments * settings.audit_llm_calls_per_talk_segment
    return {
        "runs": runs,
        "slots": [iso for iso, _ in _SLOTS],
        "continuity_slots": _CONTINUITY_SLOTS if continuity else 0,
        "segments": segments,
        "estimated_llm_calls": calls,
        "measured_usd_per_segment": per_segment,
        "estimated_usd": (
            round(segments * per_segment, 2) if per_segment is not None else None
        ),
    }


def render_plan(p: dict) -> str:
    """The spend estimate the probe prints before spending anything."""
    if p["estimated_usd"] is None:
        estimate = "— (no usage ledger yet to price it from)"
    else:
        estimate = (
            f"${p['estimated_usd']:.2f}"
            f"  (at the ledger's measured ${p['measured_usd_per_segment']}/segment)"
        )
    return "\n".join(
        [
            "── PROBE PLAN (real Anthropic calls; TTS mocked; world rolled back) ──",
            f"  contrastive : {len(p['slots'])} fixed slots × {p['runs']} run(s)"
            f"  ({', '.join(p['slots'])})",
            f"  continuity  : {p['continuity_slots']} consecutive slots"
            f" of {_CONTINUITY_PROGRAM}",
            f"  total       : {p['segments']} segments"
            f" ≈ {p['estimated_llm_calls']} LLM calls",
            f"  estimate    : {estimate}",
        ]
    )


# --- the collector ----------------------------------------------------------


def collect_probe(
    runs: int = 2, *, dry_run: bool = False, continuity: bool = True
) -> dict:
    """The probe groups: `topic.*`, `register.*`, `continuity.*`, `context.*`.

    Spends real tokens. Prints its plan first; `dry_run=True` returns the plan and
    stops.
    Every write is rolled back, so the world is unchanged when this returns.

    The generated segments come back under `_segments` — the leading underscore marks it
    as out-of-band, so the caller can dump the transcripts for a spot-check or a blind
    read without the scripts bloating (and churning) the committed audit JSON.
    """
    p = plan(runs, continuity=continuity)
    print(render_plan(p))
    if dry_run:
        log.info("audit_probe_dry_run", **{k: v for k, v in p.items() if k != "slots"})
        return {"probe": {**p, "dry_run": True}}

    started = time.monotonic()
    with isolated() as (tts, calls):
        contrastive_segments = contrastive(runs)
        continuity_segments = continuity_run() if continuity else []
        all_segments = contrastive_segments + continuity_segments
        out = {
            "topic": metrics.normalise_group(
                "topic", topic_metrics(contrastive_segments, runs)
            ),
            "register": metrics.normalise_group(
                "register", register_metrics(all_segments)
            ),
            "continuity": metrics.normalise_group(
                "continuity", continuity_metrics(continuity_segments)
            ),
            "context": calls.context_metrics(),
            "probe": {
                **p,
                "actual_llm_calls": len(calls.rows),
                "tts_synths": tts.calls,
                "wall_seconds": round(time.monotonic() - started, 1),
                "segments_generated": len(all_segments),
            },
        }
    # The per-segment index (no scripts) is small and genuinely useful in the JSON: it
    # records WHICH beat each slot chose, which is the §1a finding in one line.
    out["probe"]["segments"] = [
        {
            k: v
            for k, v in seg.items()
            if k
            in ("run", "slot", "program", "position", "continued", "dominant_entity")
        }
        for seg in all_segments
    ]
    out["_segments"] = all_segments
    log.info(
        "audit_probe_done", **{k: v for k, v in out["probe"].items() if k != "segments"}
    )
    return out


def transcripts(segments: list[dict]) -> str:
    """The run's scripts as one readable transcript — for a read or a spot-check."""
    blocks = []
    for seg in segments:
        head = " · ".join(
            str(seg.get(k))
            for k in ("slot", "program", "position", "run")
            if seg.get(k)
        )
        blocks += [
            "=" * 88,
            head,
            f"BEAT: {(seg.get('beat') or '').strip()}",
            "-" * 88,
            (seg.get("script") or "").strip(),
            "",
        ]
    return "\n".join(blocks)


__all__ = [
    "CallLog",
    "collect_probe",
    "continuity_metrics",
    "continuity_run",
    "contrastive",
    "isolated",
    "plan",
    "register_metrics",
    "render_plan",
    "topic_metrics",
    "transcripts",
]

"""D11.3 — the integrated acceptance simulation (the Phase-D gate).

Beyond each pack's unit tests, Phase D must pass ONE end-to-end run that proves the
whole pipeline holds together *over time* — the dress rehearsal before the C9 live
7-day soak. This module drives the real spine — **world tick → news → freshness →
grid → music/commercials** — across an accelerated 24–48h window and asserts the nine
integration properties that only an end-to-end run catches:

  1. **No dead gaps** — the schedule is continuous audio; the never-dead fallback never
     fired for a *generation* gap (no evergreen slot in the content stream).
  2. **No repetition loops** — talk openings, news wording, and song/artist picks don't
     cycle (D5 + the news desk + the track selector actually working together).
  3. **Talk flow** — consecutive talk slots in one program read as ONE show: a show
     opens once, it doesn't re-open (and time-stamp) every segment (D12).
  4. **Stories evolve** — running stories advance through their arc across the window,
     with past/now/future beats correctly framed (D3 + D4).
  5. **Cost stays bounded** — the call telemetry over the window is within envelope (no
     runaway regeneration / call storms).
  6. **Schedule output is sane** — every slot has a measured duration, air order is
     monotonic, and the disclosure ident lands on its configured cadence.
  7. **The hosts remember themselves** — aired talk accrues `host_journal` rows
     (D13.1 capture at the chokepoint) and the recall block genuinely reaches both
     the writers' room prompt and the continuity editor (D13.2/D13.3).
  8. **Plain register by day** — the R1.2 daytime register ban genuinely reaches the
     writers' room on daytime (steady/bright) shows, and daytime talk scripts carry
     no banned house-poetry abstraction and meet a crude contraction floor (R1.4).
  9. **The living day** — a story is re-covered later in the day with a NEWER beat (the
     desk carried a development, not a re-read — R4.2), and no PLANNED same-day-arc beat
     was ever reported before its in-world hour (the R4.0 airable gate held end-to-end).

**How it stays cheap + repeatable.** The one thing we do NOT exercise is the *writing
quality* (that's the product, judged by ear) or the *voice* (Kokoro/ElevenLabs). So the
two provider seams are mocked: `llm.generate` returns purpose-aware, world-varied text
(so repetition detection is real), and `tts` writes placeholder files with realistic,
looked-up durations (so the scheduler's timing + the "durations measured" property are
real). EVERYTHING ELSE runs for real — story selection, temporal framing, the grid +
clocks, freshness steering, the music selector, gate fallbacks. The run is **isolated**:
it writes to a temp `segments/` + schedule state and, against a live Postgres, does all
its world writes inside ONE rolled-back transaction (the `tick_db` pattern), so it never
touches the operator's real world or schedule. That makes it a repeatable `make`/pytest
check, per the pack.

Run it:  `make acceptance`  (full window)  ·  `python -m src.acceptance --hours 24`
It exits non-zero if any property fails, logging a per-property pass/fail summary.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from . import flow
from .config import settings
from .logging_setup import get_logger
from .production import mix as mix_mod
from .providers import embeddings, llm
from .providers import tts as tts_mod
from .world import clock, events, programming, store, world_tick
from .writers.conversation import BANNED_ABSTRACTIONS

log = get_logger(__name__)

# --- Property thresholds (dials — the envelope the run is judged against) ----
GAP_TOLERANCE_SEC = 3.0  # contiguous-air slack between back-to-back slots
MIN_OPENING_DISTINCTNESS = 0.5  # unique / total openings per stream, minimum
MAX_CONSECUTIVE_REPEAT = 2  # a value may not appear >2 in a row (a loop)
MAX_LLM_CALLS_PER_CONTENT = 12  # gate retries are bounded; above this = a call storm
MIN_TRACK_BREADTH = 0.15  # distinct tracks / music slots floor (catalogue must rotate)
# R1.4 — daytime talk must average at least this many contractions per script (a
# crude plainness floor; live text clears it by an order of magnitude).
PLAIN_REGISTER_CONTRACTION_FLOOR = 1.0
_CONTRACTION_RE = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
# The R1.2 prompt markers the mock keys daytime/calm talk calls off (lowercase).
_REGISTER_BAN_MARKER = "banned here: the house-poetry register"
_DAYTIME_ENERGIES = frozenset({"steady", "bright"})
_CONTENT_FORMATS = frozenset({"talk", "news", "music", "commercial", "promo"})
# Spoken-wording streams whose OPENINGS must stay fresh (music is track-driven, judged
# by the song/artist checks instead).
_WORDING_FORMATS = frozenset({"talk", "news", "commercial", "promo"})
_EVERGREEN_PREFIX = "evergreen-"
_MOCK_SEC_PER_WORD = 5.0  # mock text is a stand-in for a full segment (→ minutes)
_MOCK_SYNTH_FLOOR_SEC = 45.0  # a single voiced part is never shorter than this
_DEFAULT_START = datetime(2026, 7, 1, 0, 0, 0)  # a fixed Wednesday 00:00 (reproducible)

# Word bank for the mock world tick — coprime-strided combinations give lexically
# distinct stories (low word overlap) so the tick's structural de-dup keeps them all.
_SUBJECTS = [
    "a relay station",
    "a frontier convoy",
    "an archive",
    "a light festival",
    "a settlement council",
    "a mining claim",
    "a field linguist",
    "a shipping lane",
    "an observatory",
    "an exchange house",
    "a seed vault",
    "a tide chorus",
]
_ACTIONS = [
    "reopens after years",
    "splits over a vote",
    "uncovers a lost record",
    "draws record crowds",
    "faces a quiet shutdown",
    "changes hands overnight",
    "reports a strange signal",
    "reroutes its traffic",
    "calibrates a new array",
    "posts a surprise loss",
    "petitions the council",
    "buries an old grievance",
]
_PLACES = [
    "above the dayside",
    "out past the lanes",
    "in the deep dark",
    "at the core",
    "on the far frontier",
    "near the exchange",
    "along the tide",
    "under the long night",
    "at meridian",
    "by the old archive",
    "beyond the beacons",
    "across the reach",
]
_DOMAINS = ["culture", "technology", "nations", "finance", "peoples", "religion"]


# --- The report -------------------------------------------------------------
@dataclass
class PropertyResult:
    """One integration property's verdict, with a specific reason on failure."""

    name: str
    ok: bool
    detail: str


@dataclass
class AcceptanceReport:
    """The whole run: the nine verdicts + the telemetry they were judged on."""

    window_hours: float
    results: list[PropertyResult] = field(default_factory=list)
    telemetry: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def summary(self) -> str:
        lines = [
            f"===== ACCEPTANCE SIMULATION — {self.window_hours:g}h window =====",
        ]
        for r in self.results:
            mark = "✅ PASS" if r.ok else "❌ FAIL"
            lines.append(f"  {mark}  {r.name}")
            lines.append(f"          {r.detail}")
        t = self.telemetry
        lines.append(
            "  telemetry: " + ", ".join(f"{k}={v}" for k, v in sorted(t.items()))
        )
        lines.append(
            "  RESULT: " + ("ALL PROPERTIES PASSED ✅" if self.ok else "FAILURES ❌")
        )
        return "\n".join(lines)


# --- The mocks (the two provider seams; everything else is real) ------------
class _MockGen:
    """A purpose-aware `llm.generate` stand-in that varies text with world state.

    Routes on the distinctive markers each caller's prompt/system carries (see the
    builders) to emit output the real parser accepts, while making the *content* vary
    (by a monotonic counter + the world facts in the prompt) so anti-repetition and
    story-evolution are genuinely exercised, not faked. Counts every call for the cost
    property. Cast names are loaded up front so dialogue turns use real rostered labels.
    """

    def __init__(self, cast_names: Sequence[str]) -> None:
        self.calls = 0
        self.by_kind: dict[str, int] = {}
        self._cast = list(cast_names)
        self._n = 0  # monotonic variation seed
        # D13 — did the journal recall block genuinely reach each side of the gate?
        # (The block's steer wording is the marker; asserted by the 7th property.)
        self.saw_journal_in_room = False
        self.saw_journal_at_editor = False
        # R1.4 — the plain-register plumbing: how many talk-script calls carried
        # the R1.2 daytime ban, and the scripts those calls aired (checked for
        # banned phrases + the contraction floor by the 8th property).
        self.register_daytime_prompts = 0
        self.daytime_talk_scripts: list[str] = []

    def _tick_kind(self, kind: str) -> None:
        self.by_kind[kind] = self.by_kind.get(kind, 0) + 1

    def __call__(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str | None = None,
        cached_context: str | None = None,
        bible: str | None = None,
        cards: str | None = None,
        max_tokens: int | None = None,
        on_token=None,
        timeout: float | None = None,
    ) -> str:
        self.calls += 1
        self._n += 1
        p = prompt.lower()
        s = (system or "").lower()
        # CO2 — the stable core now arrives as bible + cards (or the legacy single
        # cached_context); fold every shape in so the heuristics still see it.
        core = cached_context or f"{bible or ''}{cards or ''}"
        ctx = f"{system or ''}\n{core}"

        # 1. Gates (safety + every continuity editor) → clear it.
        if "continuity editor" in s or "draft to review" in p:
            self._tick_kind("gate")
            if "on-air history" in s:  # the D13.3 journal block reached the editor
                self.saw_journal_at_editor = True
            return "OK"

        # 1b. D13.1 — the journal archivist: return a small valid capture attributed
        # to the roster ids the prompt itself names, varied by the counter, so the
        # journal accrues (and recalls) across the window like the real thing.
        if "station archivist" in s:
            self._tick_kind("journal_extract")
            ids = re.findall(r'"([a-z0-9_-]+)" \(', system or "")
            if not ids:
                return "[]"
            captured = [
                {
                    "host": ids[0],
                    "kind": "opinion",
                    "text": f"holds that the hour turns on mark {self._n}",
                    "other_host": None,
                    "tags": ["sim"],
                }
            ]
            if len(ids) > 1:
                captured.append(
                    {
                        "host": ids[1],
                        "kind": "exchange",
                        "text": f"traded a running line about mark {self._n}",
                        "other_host": ids[0],
                        "tags": ["sim"],
                    }
                )
            return json.dumps(captured)

        # 2. World tick: advance beat (JSON object), else propose (JSON array).
        if "next beat as a json object" in p:
            self._tick_kind("tick_advance")
            return self._advance_json()
        if "world-simulation engine" in s:
            self._tick_kind("tick_propose")
            return self._propose_json()

        # 3. Talk: the writers'-room exchange → labelled turns with rostered names.
        if "write the exchange" in p or ("writers' room" in s and "spoken" in s):
            self._tick_kind("talk_script")
            if "on-air history" in s:  # the D13.2 journal block reached the room
                self.saw_journal_in_room = True
            script = self._dialogue(ctx)
            if _REGISTER_BAN_MARKER in s:  # the R1.2 daytime ban reached the room
                self.register_daytime_prompts += 1
                self.daytime_talk_scripts.append(script)
            return script
        if "pick" in p and "beat" in p:  # the showrunner's one-beat pick (free text)
            self._tick_kind("showrunner")
            return (
                f"Beat #{self._n}: a fresh angle on the moving world, hour {self._n}."
            )

        # 4. Music: intro + the [SONG] marker (never spoken) + back-announce.
        if "music intro" in p or "back-announce" in p:
            self._tick_kind("music_script")
            marker = settings.format_music_song_marker
            return (
                f"Opening line {self._n}: here is a piece from the library.\n"
                f"{marker}\n"
                f"That was the track — closing thought {self._n}."
            )

        # 5. Commercial / promo spot, and the single-DJ news bulletin → varied prose.
        if "write the spot" in p:
            self._tick_kind("spot_script")
            return self._prose(ctx, lead=f"Spot {self._n}:")
        if "news bulletin" in p:
            self._tick_kind("news_script")
            return self._prose(ctx, lead=f"News at beat {self._n}.")

        self._tick_kind("other")
        return self._prose(ctx, lead=f"Segment {self._n}.")

    # -- content generators (varied by the counter + the world in the prompt) --
    def _dialogue(self, ctx: str) -> str:
        # We don't know WHICH cast were routed, but the routed speakers' cards are in
        # the assembled context — so label a varied line for EVERY known cast name that
        # appears, and let parse_turns keep the ones actually rostered (it's given only
        # the routed cards). Guarantees the rostered speakers get valid, distinct turns.
        # Emit a line for EVERY known cast name that appears (many DJs are named in the
        # bible prose, so we can't guess the two routed — but parse_turns is handed only
        # the routed cards, so it keeps exactly their lines and drops the rest). The
        # counter keeps the opening fingerprint distinct across segments.
        names = [n for n in self._cast if n and n.lower() in ctx.lower()]
        if not names:
            names = self._cast[:2] or ["Vell"]
        return "\n".join(
            f"{name}: Line {self._n}.{i} — a distinct turn on tonight's moving world."
            for i, name in enumerate(names)
        )

    def _prose(self, ctx: str, *, lead: str) -> str:
        facts = _titles_in(ctx)[:2]
        tail = " ".join(f"On {t}, the picture shifts again." for t in facts)
        return (
            f"{lead} The settlements carry the hour together, mark {self._n}. {tail} "
            f"That is how it stands tonight, at reference {self._n}."
        )

    def _propose_json(self) -> str:
        import json

        # Two stories per call, each drawn from a lexically-varied word bank (low word
        # overlap keeps the tick's structural de-dup from collapsing them into one), and
        # each spanning the present: an OPENING beat at 00:00 today (frames PAST once
        # `now` moves past it) + a FUTURE beat, so a moving present exists to assert on.
        stories = []
        for _ in range(2):
            self._n += 1
            n = self._n
            subj = _SUBJECTS[n % len(_SUBJECTS)]
            act = _ACTIONS[(n * 3) % len(_ACTIONS)]
            place = _PLACES[(n * 7) % len(_PLACES)]
            domain = _DOMAINS[n % len(_DOMAINS)]
            stories.append(
                {
                    "title": f"{subj} {act} {place}".capitalize(),
                    "summary": f"{subj} {act} {place}; observers weigh what follows.",
                    "scale": "small" if n % 2 else "large",
                    "domain": domain,
                    "arc_stage": "happening",
                    "figures": [
                        {
                            "name": f"{subj.title()} Steward {n}",
                            "role": "an involved party",
                            "bio": "An invented in-world person.",
                            "tags": [domain],
                        }
                    ],
                    "beats": [
                        {
                            "title": f"{act.capitalize()} ({n})",
                            "body": f"{subj} {act} {place}.",
                            "beat_kind": "announcement",
                            "day_offset": 0,
                            "hour": 0,  # 00:00 today → PAST as the window advances
                        },
                        {
                            "title": f"What comes of it ({n})",
                            "body": f"The consequences of {subj} reach {place}.",
                            "beat_kind": "development",
                            "day_offset": 3,
                            "hour": 9,  # future → frames UPCOMING
                            "quotes": [
                                {
                                    "figure": f"{subj.title()} Steward {n}",
                                    "text": f"We watch {place} closely, note {n}.",
                                    "stance": "measured",
                                }
                            ],
                        },
                    ],
                }
            )
        # R4.4 — one SAME-DAY ARC (planned later beats) so the living-day property has
        # a real intraday evolution to observe: an opening now, then two beats that LAND
        # at 01:00 and 02:00, held until their hour by the R4.0 gate. The hours are
        # early so the arc evolves inside even the short 2h window; the FIXED identity
        # means the tick's de-dup keeps exactly one across the warmup + window ticks — a
        # single arc that unfolds through the compressed day.
        stories.append(
            {
                "title": "The Meridian Relay Vote",
                "summary": (
                    "Meridian station weighs a relay-bridge compact; the vote "
                    "unfolds hour by hour."
                ),
                "scale": "large",
                "domain": "nations",
                "arc_stage": "happening",
                "figures": [
                    {
                        "name": "Meridian Steward",
                        "role": "presiding officer",
                        "bio": "An invented in-world official.",
                        "tags": ["nations"],
                    }
                ],
                "beats": [
                    {
                        "title": "The vote opens",
                        "body": "Meridian convenes on the relay compact.",
                        "beat_kind": "announcement",
                        "day_offset": 0,
                        "hour": 0,  # lands as the window passes 00:00
                        "planned": False,
                    },
                    {
                        "title": "The first count",
                        "body": "An hour in, the tally splits the hall.",
                        "beat_kind": "development",
                        "day_offset": 0,
                        "hour": 1,  # PLANNED — held until 01:00
                        "planned": True,
                    },
                    {
                        "title": "The vote resolves",
                        "body": "By the second hour Meridian settles the compact.",
                        "beat_kind": "resolution",
                        "day_offset": 0,
                        "hour": 2,  # PLANNED — held until 02:00
                        "planned": True,
                    },
                ],
            }
        )
        return json.dumps(stories)

    def _advance_json(self) -> str:
        import json

        n = self._n
        # Progress the arc WITHOUT resolving (never jump to `past`) so stories stay
        # active + keep accumulating future beats — the "stories evolve" property.
        stage = ["happening", "developing"][n % 2]
        return json.dumps(
            {
                "arc_stage": stage,
                "beat": {
                    "title": f"The story moves on ({n})",
                    "body": f"A later development at step {n} shifts things again.",
                    "beat_kind": "development",
                    "day_offset": 1 + (n % 3),
                    "hour": 11,
                    "figures": [],
                    "quotes": [],
                },
            }
        )


_TITLE_RE = re.compile(r"[-•]\s*([A-Z][^:\n]{6,60})")


def _titles_in(text: str) -> list[str]:
    """Story-title-ish fragments pulled from a prompt, to seed varied prose."""
    return [m.group(1).strip() for m in _TITLE_RE.finditer(text)]


class _MockTTS:
    """A `tts` stand-in: writes placeholder audio and looks up realistic durations.

    No Kokoro/ffmpeg — `synthesize`/`concat_audio` touch a real file (so the
    scheduler's `Path(...).exists()` check passes) and record a duration scaled by word
    count (~150 wpm), which `probe_duration` returns. The scheduler then times the
    playlist on genuinely measured, deterministic lengths.
    """

    def __init__(self) -> None:
        self.dur: dict[str, float] = {}
        self.synth_calls = 0

    def synthesize(
        self,
        text: str,
        *,
        voice: str,
        emotion: str | None = None,
        out_path: str,
    ) -> str:
        self.synth_calls += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"\x00")  # placeholder; never aired in the sim
        # A realistic per-segment length matters: the scheduler fills to a TIME depth
        # but caps segments per run (`schedule_topup_max_segments`), so unrealistically
        # short clips hit the cap before the depth and the buffer would drain. Scale to
        # minutes (each mock stands in for a full segment), varied by the mock length.
        words = max(1, len(text.split()))
        self.dur[out_path] = max(_MOCK_SYNTH_FLOOR_SEC, words * _MOCK_SEC_PER_WORD)
        return out_path

    def concat_audio(self, parts: list[str], out_path: str) -> str:
        return self._join(parts, out_path)

    def join_clips(self, paths: list[str], out_path: str) -> str:
        # The music format stitches spoken parts + the real track via a REAL ffmpeg
        # re-encode (`production.mix.join_clips`); our placeholder bytes aren't valid
        # audio, so mock it too — else every music slot raises and gets skipped, and the
        # song-repetition property would pass vacuously on zero music slots.
        return self._join(paths, out_path)

    def _join(self, parts: list[str], out_path: str) -> str:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"\x00")
        self.dur[out_path] = sum(self.dur.get(p, _MOCK_SYNTH_FLOOR_SEC) for p in parts)
        return out_path

    def probe_duration(self, path: str) -> float:
        return self.dur.get(str(path), 30.0)


# --- The isolated simulation environment ------------------------------------
@contextlib.contextmanager
def _sim_environment(
    tmp: Path, *, buffer_depth_hours: float
) -> Iterator[tuple[_MockGen, _MockTTS]]:
    """Patch the two provider seams + the world DB + the output paths for a run.

    Yields the mock generator + tts (for telemetry). On a live Postgres the world work
    lands in ONE rolled-back transaction (nothing persists); without a DB the caller
    skips. The schedule state + renders go to `tmp`, never the operator's `segments/`.
    """
    try:
        cm = store.connect()
        conn = cm.__enter__()
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001 — no DB / no pgvector -> the run can't isolate
        raise _NoDatabaseError(str(exc)) from exc

    # Start from a clean living world (keep the folder-owned canon/cast + catalog): the
    # sim GENERATES the world it then asserts on, so tick-owned + runtime state resets.
    for stmt in (
        "DELETE FROM quotes",
        "DELETE FROM figures",
        "DELETE FROM news_coverage",
        "DELETE FROM airplay_history",
        "DELETE FROM host_journal",
        f"DELETE FROM events WHERE source = '{store.EVENT_SOURCE_TICK}'",
        "DELETE FROM stories",
        "DELETE FROM state WHERE key IN ('world_tick_count', 'world_tick_last_at')",
    ):
        conn.execute(stmt)

    cast_names = [c.name for c in store.all_cast(conn)]
    gen = _MockGen(cast_names)
    tts = _MockTTS()

    @contextlib.contextmanager
    def fake_connect() -> Iterator:
        yield conn  # shared, uncommitted — every write lands in the one rolled-back txn

    segdir = tmp / "segments"
    segdir.mkdir(parents=True, exist_ok=True)

    with contextlib.ExitStack() as stack:
        p = stack.enter_context
        p(mock.patch.object(store, "connect", fake_connect))
        p(mock.patch.object(llm, "generate", gen))
        p(mock.patch.object(tts_mod, "synthesize", tts.synthesize))
        p(mock.patch.object(tts_mod, "concat_audio", tts.concat_audio))
        p(mock.patch.object(tts_mod, "probe_duration", tts.probe_duration))
        p(mock.patch.object(mix_mod, "join_clips", tts.join_clips))
        p(
            mock.patch.object(
                embeddings,
                "embed",
                lambda texts: [[0.0] * settings.embeddings_dim for _ in texts],
            )
        )
        p(mock.patch.object(embeddings, "retrieve", lambda *a, **k: []))
        # Paths → temp; batch OFF (so the tick routes through the mocked generate); beds
        # OFF (a real ffmpeg duck over placeholder audio would noisily fall to dry).
        p(mock.patch.object(settings, "segments_dir", segdir))
        p(mock.patch.object(settings, "schedule_state_path", segdir / "schedule.json"))
        p(
            mock.patch.object(
                settings, "schedule_playlist_path", segdir / "playlist.txt"
            )
        )
        p(mock.patch.object(settings, "buffer_depth_hours", buffer_depth_hours))
        p(mock.patch.object(settings, "llm_batch_enabled", False))
        p(mock.patch.object(settings, "production_bedded_programs", []))
        try:
            yield gen, tts
        finally:
            conn.rollback()
            with contextlib.suppress(Exception):
                cm.__exit__(None, None, None)


class _NoDatabaseError(RuntimeError):
    """Raised when no Postgres/pgvector is reachable — the sim needs one to isolate."""


# --- The driver -------------------------------------------------------------
def run_acceptance(
    *,
    window_hours: float = 24.0,
    step_minutes: int = 60,
    tick_every_hours: float = 24.0,
    warmup_ticks: int = 3,
    buffer_depth_hours: float = 1.0,
    start: datetime | None = None,
    dump_path: str | None = None,
) -> AcceptanceReport:
    """Run the accelerated window end-to-end and return the nine-property report.

    Imports the scheduler lazily so patching the provider seams is already in force
    before any generation runs. Accumulates every placed slot across the window (past
    slots get pruned from live state, so we union each top-up's return), then evaluates
    the properties against the timeline + the final world + the call telemetry.
    """
    # Anchor to a FIXED reference so the gate is reproducible (a repeatable check, per
    # the pack): a floating `datetime.now()` would shift the daypart/track sequence run
    # to run. A Wednesday 00:00 makes the window cross every daypart deterministically.
    start = start or _DEFAULT_START
    # The buffer must never DRAIN between top-ups, or the captured timeline shows holes
    # the live stream would have papered over with fallback. Keep the clock step under
    # the buffer depth so each top-up's runway still overlaps the next `now`.
    step_minutes = min(step_minutes, int(buffer_depth_hours * 60 * 0.8) or 1)
    tmp = Path(tempfile.mkdtemp(prefix="sr-acceptance-"))
    log.info(
        "acceptance_start",
        window_hours=window_hours,
        step_minutes=step_minutes,
        tick_every_hours=tick_every_hours,
        tmp=str(tmp),
    )

    with _sim_environment(tmp, buffer_depth_hours=buffer_depth_hours) as (gen, tts):
        from . import scheduler  # lazy: seams are patched before any generation

        # Warm the world so there's a moving present before we start airing it.
        advanced_total = 0
        for _ in range(warmup_ticks):
            advanced_total += world_tick.run_tick(now=start).advanced

        entries: dict[str, dict] = {}
        tick_results = []
        next_tick = start + timedelta(hours=tick_every_hours)
        now = start
        end = start + timedelta(hours=window_hours)
        while now <= end:
            if now >= next_tick:
                tick_results.append(world_tick.run_tick(now=now))
                advanced_total += tick_results[-1].advanced
                next_tick += timedelta(hours=tick_every_hours)
            for e in scheduler.top_up(now=now):
                key = e.get("id") or f"{e.get('audio_path')}@{e.get('air_time')}"
                entries[key] = e
            now += timedelta(minutes=step_minutes)

        timeline = sorted(entries.values(), key=lambda e: e.get("air_time") or "")
        _maybe_dump_timeline(timeline, dump_path)
        final_world = _snapshot_world(end)
        telemetry = {
            "content_slots": sum(
                1 for e in timeline if e.get("format") in _CONTENT_FORMATS
            ),
            "total_slots": len(timeline),
            "llm_calls": gen.calls,
            "tts_synths": tts.synth_calls,
            "ticks": len(tick_results) + warmup_ticks,
            "stories_advanced": advanced_total,
            **{f"llm_{k}": v for k, v in gen.by_kind.items()},
        }

    report = AcceptanceReport(window_hours=window_hours, telemetry=telemetry)
    report.results = [
        _check_no_dead_gaps(timeline, start, end),
        _check_no_repetition(timeline, final_world["openings"]),
        _check_talk_flow(timeline),
        _check_stories_evolve(final_world, advanced_total, end),
        _check_living_day(final_world),
        _check_cost_bounded(telemetry),
        _check_schedule_sane(timeline),
        _check_journal_memory(timeline, final_world, gen),
        _check_plain_register(timeline, gen),
    ]
    log.info("acceptance_done", ok=report.ok, **telemetry)
    return report


def _maybe_dump_timeline(timeline: list[dict], path: str | None) -> None:
    """Write the placed timeline JSON to `path` (a debug aid to inspect a failure)."""
    if path:
        Path(path).write_text(json.dumps(timeline, indent=2))


def _snapshot_world(now: datetime) -> dict:
    """Read the generated world (stories/beats + airplay openings) for asserting on."""
    with store.connect() as c:
        stories = store.active_stories(c)
        beats = {s.id: store.story_beats(c, s.id) for s in stories}
        airplay = store.recent_airplay(c, now, within=timedelta(days=3))
        journal = store.journal_counts(c)  # D13: per-host accrual for the 7th property
        # R4.4 — the desk's coverage history over the whole window, for the living-day
        # property (which stories were reported, at what beat, when).
        coverage = store.coverage_since(c, clock.to_inworld(now) - timedelta(days=30))
        # Ensure every covered story's beats are in the map (a story that resolved
        # since airing isn't in `active_stories`), so the property can resolve a
        # coverage's `last_beat_id` to its beat.
        for sid in {cov.story_id for cov in coverage} - beats.keys():
            beats[sid] = store.story_beats(c, sid)
    total_beats = sum(len(b) for b in beats.values())
    log.info(
        "acceptance_world_snapshot",
        active_stories=len(stories),
        total_beats=total_beats,
        journal_rows=sum(journal.values()),
        coverage_rows=len(coverage),
    )
    return {
        "stories": stories,
        "beats": beats,
        "openings": [
            (r.format, r.opening, r.topic) for r in airplay if r.opening or r.topic
        ],
        "journal": journal,
        "coverage": coverage,
    }


# --- The nine property checks (pure — unit-testable in isolation) -----------
def _check_no_dead_gaps(
    timeline: list[dict], start: datetime, end: datetime
) -> PropertyResult:
    """Continuous audio: back-to-back slots + no generation-gap evergreen fallback."""
    if not timeline:
        return PropertyResult(
            "no_dead_gaps", False, "no segments were scheduled at all"
        )
    evergreen = [
        e for e in timeline if str(e.get("id", "")).startswith(_EVERGREEN_PREFIX)
    ]
    if evergreen:
        return PropertyResult(
            "no_dead_gaps",
            False,
            f"{len(evergreen)} evergreen fallback slot(s) aired — a generation gap "
            f"fired (first: {evergreen[0].get('id')})",
        )
    prev_end: datetime | None = None
    prev: dict | None = None
    for e in timeline:
        at = _parse(e.get("air_time"))
        if at is None:
            return PropertyResult(
                "no_dead_gaps", False, f"slot {e.get('id')} has no air_time"
            )
        if prev_end is not None:
            gap = (at - prev_end).total_seconds()
            if gap > GAP_TOLERANCE_SEC:
                pid = prev.get("id") if prev else None
                return PropertyResult(
                    "no_dead_gaps",
                    False,
                    f"{gap:.0f}s gap: {pid} "
                    f"(fmt={prev.get('format') if prev else '?'}, "
                    f"dur={_dur(prev) if prev else 0:.0f}s) ended "
                    f"{prev_end.isoformat()}, next {e.get('id')} "
                    f"at {e.get('air_time')}",
                )
        prev_end = at + timedelta(seconds=_dur(e))
        prev = e
    return PropertyResult(
        "no_dead_gaps",
        True,
        f"{len(timeline)} contiguous slots, no evergreen in the content stream",
    )


def _check_no_repetition(timeline: list[dict], openings: list[tuple]) -> PropertyResult:
    """Talk/news openings and song/artist picks don't cycle."""
    problems: list[str] = []

    # Openings/topics (from the freshness memory), per SPOKEN-WORDING stream. Music is
    # excluded here: its airplay "topic" is the track id, so re-airing a track (with a
    # fresh spoken intro each time) would look like a wording loop when it isn't — track
    # rotation is judged separately below by the song/artist checks.
    by_fmt: dict[str, list[str]] = {}
    for fmt, opening, topic in openings:
        if fmt not in _WORDING_FORMATS:
            continue
        by_fmt.setdefault(fmt, []).append((opening or "") + "|" + (topic or ""))
    for fmt, vals in by_fmt.items():
        if len(vals) >= 4:
            ratio = len(set(vals)) / len(vals)
            if ratio < MIN_OPENING_DISTINCTNESS:
                problems.append(
                    f"{fmt} openings only {ratio:.0%} distinct ({len(set(vals))}/"
                    f"{len(vals)})"
                )
        run = _longest_run(vals)
        if run > MAX_CONSECUTIVE_REPEAT:
            problems.append(f"{fmt} opening repeated {run}x in a row")

    # Song picks (from the music slots' public track lore). A "loop" is the SAME track
    # stuck on repeat or the catalogue barely rotating — NOT one artist recurring: with
    # a finite catalogue + the D5 freshness window an artist returns (with a different
    # track) once the window lapses, so a repeated artist is expected, not a loop. So:
    # no track back-to-back, no track 3x running, and healthy track breadth.
    titles = [
        e["track"]["title"]
        for e in timeline
        if e.get("format") == "music" and isinstance(e.get("track"), dict)
    ]
    if _has_adjacent_dup(titles):
        problems.append("the same song aired back-to-back")
    if _longest_run(titles) > MAX_CONSECUTIVE_REPEAT:
        problems.append("the same song aired 3+ times in a row")
    if len(titles) >= 10:
        breadth = len(set(titles))
        floor = max(8, int(len(titles) * MIN_TRACK_BREADTH))
        if breadth < floor:
            problems.append(
                f"music barely rotates: only {breadth} distinct tracks over "
                f"{len(titles)} slots (want ≥ {floor})"
            )

    if problems:
        return PropertyResult("no_repetition_loops", False, "; ".join(problems))
    streams = f"{len(by_fmt)} talk/news stream(s), {len(titles)} song pick(s)"
    return PropertyResult("no_repetition_loops", True, f"no loops across {streams}")


def _check_stories_evolve(
    world: dict, advanced_total: int, now: datetime
) -> PropertyResult:
    """Stories advance across the window, with past/now/future beats framed right."""
    if advanced_total <= 0:
        return PropertyResult(
            "stories_evolve", False, "no running story advanced across the window"
        )
    # A moving present: among active stories, beats straddle `now` — some frame as the
    # present-or-behind (today/past) and some still-ahead (upcoming). status_of frames
    # each by its date (a beat before now is never "upcoming"), so this also proves the
    # framing is internally correct, not just that beats exist. "today" counts on the
    # present side — that IS the "now" in past/now/future.
    past = today = future = 0
    for beats in world["beats"].values():
        for b in beats:
            st = events.status_of(b, now)
            if st == events.PAST:
                past += 1
            elif st == events.TODAY:
                today += 1
            elif st == events.UPCOMING:
                future += 1
    present_side = past + today
    if present_side == 0 or future == 0:
        return PropertyResult(
            "stories_evolve",
            False,
            f"no moving present: past={past}, now/today={today}, future={future} "
            f"(need present-or-past AND future > 0)",
        )
    return PropertyResult(
        "stories_evolve",
        True,
        f"{advanced_total} advancement(s); beats framed {past} past / {today} now / "
        f"{future} future around the clock",
    )


def _check_living_day(world: dict) -> PropertyResult:
    """R4.4 — the living day: a story EVOLVES on air, and no PLANNED beat airs early.

    Reads the desk's real coverage history (D4.0) against the world's beats:

    * **evolves** — some story was re-covered later in the day with a NEWER beat than a
      previous bulletin reported it at (the desk carried a development, not a re-read).
      This is the observable signature of the R4.2 evolve framing over the R4.0 arc.
    * **no early plan** — no coverage ever recorded a PLANNED beat as its latest before
      that beat's in-world hour: the R4.0 gate (`events.airable`) held end-to-end. The
      check is non-vacuous — the sim authors a same-day arc, so planned beats exist.
    """
    coverage = world.get("coverage", [])
    beats_by_id = {b.id: b for beats in world["beats"].values() for b in beats}
    planned = [b for b in beats_by_id.values() if b.planned]

    # No planned beat may be the desk's reported latest before its hour has arrived.
    for cov in coverage:
        beat = beats_by_id.get(cov.last_beat_id) if cov.last_beat_id else None
        if (
            beat is not None
            and beat.planned
            and (cov.covered_at < beat.in_world_datetime)
        ):
            return PropertyResult(
                "living_day",
                False,
                f"planned beat {beat.id} was reported at {cov.covered_at.isoformat()}, "
                f"before its hour {beat.in_world_datetime.isoformat()}",
            )

    # Some story must have been re-covered with a newer beat than a prior bulletin used.
    by_story: dict[str, list] = {}
    for cov in coverage:
        by_story.setdefault(cov.story_id, []).append(cov)
    evolved: str | None = None
    for sid, covs in by_story.items():
        seen: datetime | None = None
        for cov in sorted(covs, key=lambda c: c.covered_at):
            beat = beats_by_id.get(cov.last_beat_id) if cov.last_beat_id else None
            dt = beat.in_world_datetime if beat is not None else None
            if dt is None:
                continue
            if seen is not None and dt > seen:
                evolved = sid
                break
            seen = dt if seen is None else max(seen, dt)
        if evolved:
            break

    if evolved is None:
        return PropertyResult(
            "living_day",
            False,
            f"no story was re-covered with a newer beat across {len(coverage)} "
            "coverage record(s) — nothing evolved on air",
        )
    return PropertyResult(
        "living_day",
        True,
        f"story {evolved} evolved across bulletins; {len(planned)} planned beat(s) "
        f"held, none aired before its hour ({len(coverage)} coverage records)",
    )


def _check_cost_bounded(telemetry: dict) -> PropertyResult:
    """No runaway regeneration: LLM calls per content slot within envelope."""
    content = telemetry.get("content_slots", 0)
    calls = telemetry.get("llm_calls", 0)
    if content == 0:
        return PropertyResult("cost_bounded", False, "no content slots generated")
    per = calls / content
    if per > MAX_LLM_CALLS_PER_CONTENT:
        return PropertyResult(
            "cost_bounded",
            False,
            f"{per:.1f} LLM calls per content slot (> {MAX_LLM_CALLS_PER_CONTENT}) — a "
            f"call storm ({calls} calls / {content} slots)",
        )
    return PropertyResult(
        "cost_bounded",
        True,
        f"{per:.1f} LLM calls per content slot ({calls}/{content}), within envelope",
    )


def _check_journal_memory(
    timeline: list[dict], final_world: dict, gen: _MockGen
) -> PropertyResult:
    """The hosts remember themselves (D13): capture accrues, recall reaches the gate.

    Three sub-assertions in one property: aired talk left `host_journal` rows behind
    (the D13.1 chokepoint capture ran), the recall block reached the writers'-room
    prompt (D13.2), and the SAME block reached the continuity editor (D13.3 — the
    self-consistency gate is armed). Inconclusive-but-passing when the window held
    no talk (nothing to journal) or the journal is disabled.
    """
    if not settings.convo_journal_enabled:
        return PropertyResult(
            "journal_memory", True, "convo_journal_enabled=False (skipped)"
        )
    talk = sum(1 for e in timeline if e.get("format") == "talk")
    if talk == 0:
        return PropertyResult(
            "journal_memory", True, "no talk slots in window (inconclusive)"
        )
    per_host: dict = final_world.get("journal", {})
    rows = sum(per_host.values())
    if rows == 0:
        return PropertyResult(
            "journal_memory",
            False,
            f"{talk} talk slot(s) aired but no journal rows accrued (capture dead?)",
        )
    if not gen.saw_journal_in_room:
        return PropertyResult(
            "journal_memory",
            False,
            f"{rows} rows accrued but the recall block never reached the room",
        )
    if not gen.saw_journal_at_editor:
        return PropertyResult(
            "journal_memory",
            False,
            f"{rows} rows accrued but the block never reached the continuity editor",
        )
    return PropertyResult(
        "journal_memory",
        True,
        f"{rows} entries across {len(per_host)} host(s) from {talk} talk slot(s); "
        "recall reached the room AND the editor",
    )


def _check_plain_register(timeline: list[dict], gen: _MockGen) -> PropertyResult:
    """Daytime talk stays plain (R1.4): the ban reaches the room; scripts stay clean.

    Three sub-assertions in one property: (a) when the window aired talk on a
    daytime program (grid `energy` steady/bright), the R1.2 register-ban block
    genuinely reached the writers'-room prompt — deleting `_register_directive`
    or breaking the R1.0 program threading fails this; (b) no daytime talk script
    contains a `BANNED_ABSTRACTIONS` phrase; (c) daytime scripts average at least
    `PLAIN_REGISTER_CONTRACTION_FLOOR` contractions — crude, but a regression to
    written-not-spoken prose trips it. Inconclusive-but-passing when the window
    held no daytime talk.
    """
    energies = {pid: p.energy for pid, p in programming.all_programs().items()}
    daytime_talk = sum(
        1
        for e in timeline
        if e.get("format") == "talk"
        and energies.get(str(e.get("program"))) in _DAYTIME_ENERGIES
    )
    if daytime_talk == 0:
        return PropertyResult(
            "plain_register", True, "no daytime talk slots in window (inconclusive)"
        )
    problems: list[str] = []
    if gen.register_daytime_prompts == 0:
        problems.append(
            f"{daytime_talk} daytime talk slot(s) aired but the register ban never "
            "reached the writers' room (R1.2 directive missing?)"
        )
    hits = sorted(
        {
            phrase
            for script in gen.daytime_talk_scripts
            for phrase in BANNED_ABSTRACTIONS
            if phrase in script.lower()
        }
    )
    if hits:
        problems.append(f"banned abstraction(s) in daytime talk: {hits}")
    per_script = 0.0
    if gen.daytime_talk_scripts:
        per_script = sum(
            len(_CONTRACTION_RE.findall(s)) for s in gen.daytime_talk_scripts
        ) / len(gen.daytime_talk_scripts)
        if per_script < PLAIN_REGISTER_CONTRACTION_FLOOR:
            problems.append(
                f"contraction floor missed: {per_script:.1f}/script "
                f"(< {PLAIN_REGISTER_CONTRACTION_FLOOR})"
            )
    if problems:
        return PropertyResult("plain_register", False, "; ".join(problems))
    return PropertyResult(
        "plain_register",
        True,
        f"{daytime_talk} daytime talk slot(s): ban in "
        f"{gen.register_daytime_prompts} room prompt(s), scripts clean, "
        f"{per_script:.1f} contractions/script",
    )


def _check_talk_flow(timeline: list[dict]) -> PropertyResult:
    """Consecutive talk slots in ONE program read as one show, not N mini-shows (D12).

    Groups the timeline into program RUNS (a maximal stretch of one program id) and
    checks the talk slots' show position: a show OPENS once — no talk slot AFTER the
    first in a run may be `open` (a re-open would mean the "it's 2 a.m. …, welcome"
    reset D12 removed). `open` is the signal the writers' room keys the greeting AND
    the time-check off, so this one check covers both. Inconclusive (but not failing)
    if the window happens to hold no multi-talk run.
    """
    runs: list[list[str | None]] = []
    cur_prog: object = object()  # sentinel distinct from any program id / None
    cur: list[str | None] = []
    for e in timeline:
        prog = e.get("program")
        if prog != cur_prog:
            if cur:
                runs.append(cur)
            cur, cur_prog = [], prog
        if e.get("format") == "talk":
            cur.append(e.get("flow_position"))
    if cur:
        runs.append(cur)

    reopens = sum(1 for r in runs for p in r[1:] if p == flow.OPEN)
    multi = sum(1 for r in runs if len(r) >= 2)
    if reopens:
        return PropertyResult(
            "talk_flow", False, f"{reopens} talk slot(s) re-opened mid-show"
        )
    if multi == 0:
        return PropertyResult(
            "talk_flow", True, "no multi-talk program run in window (inconclusive)"
        )
    return PropertyResult(
        "talk_flow", True, f"one open per show across {multi} multi-talk run(s)"
    )


def _check_schedule_sane(timeline: list[dict]) -> PropertyResult:
    """Measured durations, monotonic air order, and the disclosure ident on cadence."""
    if not timeline:
        return PropertyResult("schedule_sane", False, "empty schedule")
    prev_at: datetime | None = None
    for e in timeline:
        if _dur(e) <= 0:
            return PropertyResult(
                "schedule_sane", False, f"slot {e.get('id')} has non-positive duration"
            )
        at = _parse(e.get("air_time"))
        if at is None:
            return PropertyResult(
                "schedule_sane", False, f"slot {e.get('id')} has no air_time"
            )
        if prev_at is not None and at < prev_at:
            return PropertyResult(
                "schedule_sane",
                False,
                f"air order goes backwards at {e.get('id')} ({e.get('air_time')})",
            )
        prev_at = at
    # The disclosure ident must recur (it weaves every `disclosure_every_n` content
    # slots). Over a multi-hour window with content flowing, at least one must land.
    idents = [
        e
        for e in timeline
        if str(e.get("id", "")).startswith("ident-")
        and not str(e.get("id", "")).startswith("ident-station-")
    ]
    content = sum(1 for e in timeline if e.get("format") in _CONTENT_FORMATS)
    if content >= settings.disclosure_every_n and not idents:
        return PropertyResult(
            "schedule_sane",
            False,
            f"{content} content slots but the disclosure ident never wove in",
        )
    return PropertyResult(
        "schedule_sane",
        True,
        f"{len(timeline)} slots: durations measured, order monotonic, "
        f"{len(idents)} disclosure ident(s) on cadence",
    )


# --- small helpers ----------------------------------------------------------
def _parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def _dur(entry: dict) -> float:
    measured = entry.get("actual_duration_sec")
    if measured and measured > 0:
        return float(measured)
    return float(entry.get("length_target_sec") or 0)


def _longest_run(seq: Sequence) -> int:
    best = cur = 0
    prev = object()
    for x in seq:
        cur = cur + 1 if x == prev else 1
        best = max(best, cur)
        prev = x
    return best


def _has_adjacent_dup(seq: Sequence) -> bool:
    return any(a == b for a, b in zip(seq, list(seq)[1:], strict=False))


# --- CLI --------------------------------------------------------------------
def main(argv: list[str]) -> int:
    """Run the simulation; exit non-zero if any property fails (the C9-soak gate)."""
    ap = argparse.ArgumentParser(
        description="Phase-D integrated acceptance simulation."
    )
    ap.add_argument("--hours", type=float, default=24.0, help="window length (h)")
    ap.add_argument("--step-minutes", type=int, default=60, help="clock step (min)")
    ap.add_argument(
        "--tick-every-hours", type=float, default=12.0, help="world-tick cadence (h)"
    )
    ap.add_argument(
        "--buffer-depth-hours", type=float, default=1.0, help="rolling buffer depth (h)"
    )
    ap.add_argument(
        "--dump", default=None, help="write the placed timeline JSON here (debug aid)"
    )
    args = ap.parse_args(argv)

    try:
        report = run_acceptance(
            window_hours=args.hours,
            step_minutes=args.step_minutes,
            tick_every_hours=args.tick_every_hours,
            buffer_depth_hours=args.buffer_depth_hours,
            dump_path=args.dump,
        )
    except _NoDatabaseError as exc:
        print(
            f"acceptance: needs a reachable Postgres/pgvector — {exc}", file=sys.stderr
        )
        return 2

    print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

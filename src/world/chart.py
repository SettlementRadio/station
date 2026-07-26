"""R6.1 — the daily chart: a top-N that actually MOVES, and its narrator.

The Count (`src/formats/chart.py`) counts down a chart; this module is the chart
itself — a cheap, deterministic-with-seed daily re-rank of the chart-eligible
catalogue, run once at the end of the nightly tick job (never in the scheduler
loop). No song "wins" by an LLM's opinion; the chart is a scoring problem, the
same shape as the D7.4 selector:

  * **Yesterday's ranks carry momentum** — a track in the prior chart keeps roughly
    its place, nudged by a bounded random walk, so the chart has continuity.
  * **Novelty lifts recent entries** — a boost that decays with `days_on`, so debuts
    and climbers have life and stale holdouts eventually slide.
  * **New entries debut off the relays** — an eligible track not in yesterday's chart
    gets a mid-pack baseline plus a seeded leap, so fresh names break in.
  * **`featured`/`pinned` is the human's thumb on the scale** — the one manual boost.

`compute_chart(tracks, prev, *, size, seed)` is a PURE function: the same eligible
tracks + previous chart + seed always produce the same new chart — so two different
days (different date-derived seeds) move plausibly, and a unit test can pin it.

Storage: one JSON blob in the `state` row `chart:daily` (§2a — RUNTIME state that
survives `seed-canon`, cleared by `reset-world`; never GC'd like audio). The update
is best-effort and wrapped like the tick digest: a failure here never fails the tick.

The optional day's **chart story** (climber / new entry / holdout) is picked
deterministically from the movement, then narrated by one hard-capped haiku call —
the line Orin opens The Count on. The narration is best-effort; the pick is not.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..production import media
from ..providers import llm
from . import store

log = get_logger(__name__)

CHART_KEY = "chart:daily"

_NUMBER_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
}
_FEATURE_TAGS = frozenset({"featured", "pinned"})


# --- The chart's shape -------------------------------------------------------


@dataclass(frozen=True)
class ChartEntry:
    """One ranked position in the daily chart (public-safe lore only)."""

    track_id: str
    title: str
    artist: str
    story_blurb: str | None
    rank: int  # 1 = the top
    prev_rank: int | None  # its rank yesterday, or None if it wasn't on the chart
    days_on: int  # consecutive days on the chart (1 = a new/re-entry this run)

    def movement(self) -> tuple[str, int]:
        """(kind, places) — how this position moved since yesterday.

        kind ∈ new | up | down | nonmover; `places` is the absolute jump (0 for
        a new entry or a non-mover). Climbing is a *lower* rank number.
        """
        if self.prev_rank is None:
            return ("new", 0)
        delta = self.prev_rank - self.rank
        if delta > 0:
            return ("up", delta)
        if delta < 0:
            return ("down", -delta)
        return ("nonmover", 0)

    def movement_phrase(self) -> str:
        """Broadcast movement language: 'new entry', 'up three', 'holds at four'."""
        kind, places = self.movement()
        if kind == "new":
            return "new entry"
        if kind == "nonmover":
            return f"holds at {_num(self.rank)}"
        word = _num(places)
        return f"up {word}" if kind == "up" else f"down {word}"


def _num(n: int) -> str:
    """A small integer as a word ('three'), falling back to digits past ten."""
    return _NUMBER_WORDS.get(n, str(n))


# --- Eligibility (the impure edge that reads the catalogue) ------------------


def eligible_tracks(conn) -> list[store.Track]:  # noqa: ANN001
    """Playable tracks the chart may rank: those tagged `chart_eligible_tag`.

    Falls back to ALL playable tracks when nothing is tagged yet, so the chart
    works before the manifest carries the tag (the catalogue is the source of
    truth; a missing tag shouldn't leave The Count with an empty chart).
    """
    playable = [t for t in store.all_tracks(conn) if media.is_playable(t)]
    tagged = [t for t in playable if settings.chart_eligible_tag in t.tags]
    if tagged:
        return tagged
    log.info("chart_no_tagged_tracks", playable=len(playable))
    return playable


# --- The pure update (the tested core) ---------------------------------------


def _prev_map(prev: dict | None) -> dict[str, tuple[int, int]]:
    """{track_id: (rank, days_on)} from a stored chart blob (empty if none)."""
    if not prev:
        return {}
    out: dict[str, tuple[int, int]] = {}
    for e in prev.get("entries", []):
        try:
            out[e["track_id"]] = (int(e["rank"]), int(e.get("days_on", 1)))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _score(
    track: store.Track, prev: dict[str, tuple[int, int]], size: int, rng
) -> float:  # noqa: ANN001
    """The documented momentum score for one track — pure, weights from settings."""
    prior = prev.get(track.id)
    if prior is not None:
        rank, days_on = prior
        # A holdover keeps its standing (top rank = high value), nudged by a walk.
        base = (size - rank + 1) + rng.uniform(
            -settings.chart_random_walk, settings.chart_random_walk
        )
    else:
        # A debut lands mid-pack with a seeded leap so fresh names can break high.
        days_on = 1
        base = settings.chart_new_entry_base + rng.uniform(
            0, settings.chart_new_entry_spread
        )
    # Novelty: recent entries get a lift that decays with time on the chart.
    base += settings.chart_freshness_weight / max(1, days_on)
    if _FEATURE_TAGS & set(track.tags):
        base += settings.chart_featured_weight
    return base


def compute_chart(
    tracks: list[store.Track], prev: dict | None, *, size: int, seed: int
) -> list[ChartEntry]:
    """Re-rank `tracks` into a new top-`size` chart — pure and deterministic.

    Scores every eligible track by the momentum policy, seeded so equal cases are
    stable, sorts descending (track id breaks exact ties), and takes the top `size`.
    Each entry carries its `prev_rank` (None if it wasn't charting yesterday) and an
    updated `days_on`. The same tracks + prev + seed always return the same chart.
    """
    import random

    prev_map = _prev_map(prev)
    rng = random.Random(seed)
    scored: list[tuple[float, str, store.Track]] = []
    for track in sorted(tracks, key=lambda t: t.id):  # stable rng consumption order
        scored.append((_score(track, prev_map, size, rng), track.id, track))
    # Higher score first; id ascending breaks ties (deterministic).
    scored.sort(key=lambda x: (-x[0], x[1]))

    entries: list[ChartEntry] = []
    for i, (_, _, track) in enumerate(scored[:size]):
        rank = i + 1
        prior = prev_map.get(track.id)
        prev_rank = prior[0] if prior else None
        days_on = (prior[1] + 1) if prior else 1
        entries.append(
            ChartEntry(
                track_id=track.id,
                title=track.title,
                artist=track.in_world_artist,
                story_blurb=track.story_blurb,
                rank=rank,
                prev_rank=prev_rank,
                days_on=days_on,
            )
        )
    return entries


# --- The day's chart story (deterministic pick, optional haiku narration) ----


def pick_story(entries: list[ChartEntry]) -> dict | None:
    """The day's chart headline, chosen deterministically from the movement.

    Priority: the biggest climber (≥2 places) → a new entry that debuted in the
    top half → the holdout sitting at number one. Returns a structured dict
    (`kind`/`track_id`/`title`/`artist`/`rank`/`detail`) or None on an empty chart.
    """
    if not entries:
        return None
    top_half = max(1, len(entries) // 2)

    climbers = [(e.movement()[1], e) for e in entries if e.movement()[0] == "up"]
    if climbers:
        places, e = max(climbers, key=lambda x: (x[0], -x[1].rank))
        if places >= 2:
            return _story("climber", e, f"up {_num(places)} to {_num(e.rank)}")

    new_top = [e for e in entries if e.movement()[0] == "new" and e.rank <= top_half]
    if new_top:
        e = min(new_top, key=lambda x: x.rank)
        return _story("new_entry", e, f"new entry at {_num(e.rank)}")

    top = entries[0]
    if top.movement()[0] == "nonmover" and top.days_on >= 2:
        return _story("holdout", top, f"holds at number one for {top.days_on} days")

    # Nothing dramatic — lead with the number one however it got there.
    return _story("number_one", top, top.movement_phrase())


def _story(kind: str, e: ChartEntry, detail: str) -> dict:
    return {
        "kind": kind,
        "track_id": e.track_id,
        "title": e.title,
        "artist": e.artist,
        "rank": e.rank,
        "detail": detail,
    }


def narrate_story(story: dict | None) -> str | None:
    """One hard-capped haiku line on the day's chart story (best-effort, optional).

    Returns None when disabled, when there's no story, or on any LLM failure — The
    Count still opens fine off the structured `detail` if this isn't there.
    """
    if story is None or not settings.chart_story_enabled:
        return None
    try:
        system = (
            "You write a single vivid sentence for a fictional radio station's daily "
            "music chart show — the 'story of the chart' the host opens on. Plain, "
            "excited-but-grounded, concrete; no preamble, no lists, no quote marks. "
            "Never mention being an AI; stay inside the fiction."
        )
        prompt = (
            f"Today's chart story: {story['kind'].replace('_', ' ')} — "
            f'"{story["title"]}" by {story["artist"]}, {story["detail"]}.\n'
            "Write the one-sentence chart-story line."
        )
        text = llm.generate(
            prompt,
            system=system,
            model=settings.chart_story_tier,
            max_tokens=settings.chart_story_max_tokens,
        ).strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 — narration must never fail the chart
        log.warning("chart_story_narrate_failed", error=str(exc))
        return None


# --- Persist + read ----------------------------------------------------------


def _blob(
    entries: list[ChartEntry],
    *,
    now: datetime,
    chart_no: int,
    story: dict | None,
    story_text: str | None,
) -> dict:
    return {
        "date": now.date().isoformat(),
        "generated_at": now.isoformat(timespec="seconds"),
        "chart_no": chart_no,
        "entries": [asdict(e) for e in entries],
        "story": story,
        "story_text": story_text,
    }


def current(conn) -> dict | None:  # noqa: ANN001
    """The stored chart blob (dict), or None if no chart has been built yet."""
    raw = store.get_state(conn, CHART_KEY)
    if not raw:
        return None
    try:
        blob = json.loads(raw)
    except ValueError:
        return None
    return blob if isinstance(blob, dict) else None


def top(conn, n: int) -> list[ChartEntry]:  # noqa: ANN001
    """The current chart's top `n` positions as `ChartEntry` (empty if no chart)."""
    blob = current(conn)
    if not blob:
        return []
    out: list[ChartEntry] = []
    for e in blob.get("entries", [])[:n]:
        try:
            out.append(ChartEntry(**{k: e.get(k) for k in ChartEntry.__annotations__}))
        except TypeError:
            continue
    return out


@dataclass
class ChartResult:
    """Summary of one chart update (for logging + the tick job's report)."""

    chart_no: int = 0
    size: int = 0
    new_entries: int = 0
    top_track_id: str | None = None
    story_kind: str | None = None
    ran: bool = False
    reason: str = ""


def update_and_store(now: datetime | None = None) -> ChartResult:
    """Re-rank the chart for `now`, store it, return a summary. Best-effort, not fatal.

    Reads the eligible catalogue + yesterday's chart, computes the new chart with a
    seed derived from the date (so each day is deterministic yet different), picks +
    narrates the day's story, and writes the `chart:daily` state row. Any failure is
    logged and swallowed — like the tick digest, the chart must never fail the tick.
    """
    now = now or datetime.now()
    if not settings.chart_enabled:
        return ChartResult(reason="disabled")
    try:
        with store.connect() as conn:
            tracks = eligible_tracks(conn)
            if len(tracks) < settings.chart_min_tracks:
                log.info("chart_too_few_tracks", eligible=len(tracks))
                return ChartResult(ran=False, reason="too few eligible tracks")
            prev = current(conn)
            chart_no = int(prev.get("chart_no", 0)) + 1 if prev else 1
            seed = int(now.strftime("%Y%m%d"))
            entries = compute_chart(tracks, prev, size=settings.chart_size, seed=seed)
            story = pick_story(entries)
            story_text = narrate_story(story)
            store.set_state(
                conn,
                CHART_KEY,
                json.dumps(
                    _blob(
                        entries,
                        now=now,
                        chart_no=chart_no,
                        story=story,
                        story_text=story_text,
                    )
                ),
            )
        new_entries = sum(1 for e in entries if e.prev_rank is None)
        result = ChartResult(
            chart_no=chart_no,
            size=len(entries),
            new_entries=new_entries,
            top_track_id=entries[0].track_id if entries else None,
            story_kind=story["kind"] if story else None,
            ran=True,
        )
        log.info(
            "chart_updated",
            chart_no=result.chart_no,
            size=result.size,
            new_entries=result.new_entries,
            top=result.top_track_id,
            story=result.story_kind,
        )
        return result
    except Exception as exc:  # noqa: BLE001 — the chart must never fail the tick
        log.warning("chart_update_failed", error=str(exc))
        return ChartResult(ran=False, reason=str(exc))


def main() -> int:
    """Run one chart update from the CLI (`make chart`)."""
    from .. import usage

    with usage.job("chart"):
        r = update_and_store()
    usage.flush()
    if not r.ran:
        print(f"Chart NOT updated: {r.reason}")
        return 0 if r.reason in ("disabled", "too few eligible tracks") else 1
    with store.connect() as conn:
        blob = current(conn)
    print(
        f"\nChart #{r.chart_no} — {blob['date']} ({r.size} positions, "
        f"{r.new_entries} new):"
    )
    for e in blob["entries"]:
        entry = ChartEntry(**{k: e.get(k) for k in ChartEntry.__annotations__})
        print(
            f"  {entry.rank:>2}. {entry.title} — {entry.artist}  "
            f"[{entry.movement_phrase()}]"
        )
    if blob.get("story_text"):
        print(f"\n  Story of the chart: {blob['story_text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

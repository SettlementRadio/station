"""Simulated-day news-desk demo (PHASE_D_NEWS_DESK_TASKS.md D4.4).

Advances the in-world clock across a day and shows the desk's STORY SELECTION +
FRAMING evolve bulletin to bulletin — **breaking → repeated → repeated-and-evolved →
referenced-as-past** — so the D4 behaviour is visible end-to-end without spending a
token. It seeds a tiny illustrative story log in a transaction that is ROLLED BACK at
the end, so it never touches your real world (safe to run anytime, even against a live
dev DB).

This is the deterministic *framing* view the D4.1 selection + D4.0 coverage memory
produce; the actual voiced bulletin (Claude + TTS) is `make format FMT=news`. If RAG
is configured the canon-grounding step loads the embedding model once — the framing
result is the same without it (recall degrades to no-op).

Run:  .venv/bin/python -m src.formats.news_demo   (or: make news-demo) — needs Postgres.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..logging_setup import get_logger
from ..world import clock, store
from ..world import events as events_mod
from . import news_select
from .news_select import SelectedStory

log = get_logger(__name__)

_TICK = store.EVENT_SOURCE_TICK


_DEMO_PREFIX = "demo-"  # the demo's own story/beat ids; display is filtered to these


def _seed_demo_world(conn) -> datetime:
    """Seed a tiny, illustrative story log in the rolled-back txn; return day D.

    Two stories: a breaking-then-evolving grain shortfall, and a festival that is only
    ever trailed (an upcoming beat). It does NOT clear the world (a TRUNCATE would take
    an exclusive lock and block on the scheduler/tick); the demo just adds its own
    `demo-` rows alongside whatever exists and filters the display to them — and the
    whole transaction is rolled back at the end, so nothing persists.
    """
    day = datetime(2626, 6, 24)

    store.insert_story(
        conn,
        store.Story(
            id="demo-harvest",
            title="The Westreach grain shortfall",
            summary="A failed cistern season leaves the Westreach granaries short.",
            arc_stage=store.ARC_HAPPENING,
            source=_TICK,
            created_tick=1,
        ),
    )
    store.insert_story(
        conn,
        store.Story(
            id="demo-festival",
            title="The Lantern Tide festival",
            summary="The harbour districts ready the year's Lantern Tide.",
            arc_stage=store.ARC_UPCOMING,
            source=_TICK,
            created_tick=1,
        ),
    )
    store.insert_beats(
        conn,
        [
            store.Event(
                id="demo-h1",
                title="Shortfall confirmed across the Westreach granaries",
                body="Stewards confirm the cistern season fell short; reserves thin.",
                in_world_datetime=day.replace(hour=9),
                status="today",
                source=_TICK,
                story_id="demo-harvest",
                beat_kind="announcement",
            ),
            store.Event(
                id="demo-f1",
                title="Lantern Tide to open on the harbour in two days",
                body="The harbour guilds set the Lantern Tide to open at dusk.",
                in_world_datetime=(day + timedelta(days=2)).replace(hour=19),
                status="upcoming",
                source=_TICK,
                story_id="demo-festival",
                beat_kind="announcement",
            ),
        ],
    )
    return day


def _record(conn, sel: SelectedStory, iw_now: datetime) -> None:
    """Record this bulletin's coverage of a story (mirrors the producer, in-txn)."""
    prior = sel.prior_coverage
    angle = prior.angle if prior and prior.angle else sel.story.title
    last = sel.latest_beat or sel.lead_beat
    store.record_coverage(
        conn,
        store.NewsCoverage(
            story_id=sel.story.id,
            covered_at=iw_now,
            arc_stage=sel.story.arc_stage,
            last_beat_id=last.id if last else None,
            angle=angle,
        ),
    )


def _bulletin(conn, iw_now: datetime, label: str) -> None:
    """Print this bulletin's selection + framing for the demo stories, record coverage.

    Selects over the whole active log with a high count (so the demo's stories are
    always in the result even on a busy dev DB), then filters the display to the
    `demo-` stories — the controlled arc this demo is illustrating.
    """
    now = clock.to_real(iw_now)
    everything = news_select.select_for(conn, now, count=10_000, ground=False)
    selected = [s for s in everything if s.story.id.startswith(_DEMO_PREFIX)]
    print(f"\n=== {label} — {clock.render_wall_clock(now)} ===")
    if not selected:
        print("  (quiet news day — nothing pressing near now)")
    for sel in selected:
        beat = sel.lead_beat
        phrase = events_mod.relative_phrase(beat, now) if beat is not None else "—"
        tag = f"{sel.temporal_kind}/{sel.coverage_tag}"
        extra = ""
        if sel.coverage_tag == news_select.COVERAGE_EVOLVE and sel.new_beat is not None:
            extra = f"   ↳ update: {sel.new_beat.title}"
        print(f"  • [{tag:<17}] {phrase:<22} {sel.story.title}{extra}")
    for sel in selected:
        _record(conn, sel, iw_now)


def main() -> int:
    """Run the simulated day; roll back so nothing the demo wrote persists."""
    print(
        "\nNews-desk simulated day (D4) — watch one story go "
        "breaking → repeated → repeated-and-evolved → referenced-as-past,\n"
        "while another is steadily trailed. Tags: [temporal_kind/coverage_tag]. "
        "(Demo writes are rolled back.)"
    )
    with store.connect() as conn:
        try:
            day = _seed_demo_world(conn)
            _bulletin(conn, day.replace(hour=10), "Bulletin 1  (morning)")
            _bulletin(conn, day.replace(hour=14), "Bulletin 2  (afternoon)")

            # A new development lands mid-day — the next bulletin should EVOLVE it.
            store.insert_beats(
                conn,
                [
                    store.Event(
                        id="demo-h2",
                        title="Council orders emergency rationing",
                        body="The settlement council moves the shortfall to rationing.",
                        in_world_datetime=day.replace(hour=15),
                        status="today",
                        source=_TICK,
                        story_id="demo-harvest",
                        beat_kind="development",
                    )
                ],
            )
            print("\n  …a new beat lands: 'Council orders emergency rationing'")

            _bulletin(conn, day.replace(hour=18), "Bulletin 3  (evening)")
            _bulletin(
                conn,
                (day + timedelta(days=1)).replace(hour=10),
                "Bulletin 4  (next morning)",
            )
        finally:
            conn.rollback()  # the demo's seed + coverage never persist
    print(
        "\nSame stories, different framing each hour — that's the desk reading the "
        "living world.\nFor a voiced bulletin: make format FMT=news\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

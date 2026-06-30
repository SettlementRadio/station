"""Figures & quotes demo (PHASE_D_FIGURES_QUOTES_TASKS.md D10.4).

Shows the world *speaking*: it seeds a tiny story peopled with invented FIGURES and
their attributable, dated QUOTES (D10.0/D10.1), then prints the two textual surfaces
D10.2 produces — **the news desk attributing a quote with correct temporal framing**,
and **the writers'-room "what people are saying" slice** the DJs reference — so the
behaviour is visible end-to-end without spending a token.

Deterministic + token-free (no Claude, no TTS): it mirrors `news_demo` — adds its own
`demo-` rows alongside whatever exists (no world-clearing TRUNCATE) and ROLLS BACK at
the end, so it never touches your real world. For the *generated* path (the tick
inventing figures + quotes) use `make world-tick`; for a voiced bulletin that attributes
them, `make format FMT=news`.

Run:  python -m src.formats.figures_demo   (or: make figures-demo) — needs Postgres.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..config import settings
from ..logging_setup import get_logger
from ..world import clock, context, store
from . import news, news_select

log = get_logger(__name__)

_TICK = store.EVENT_SOURCE_TICK
_BIBLE = store.FIGURE_SOURCE_BIBLE
_DEMO_PREFIX = "demo-"


def _seed_demo_world(conn) -> datetime:
    """Seed one peopled story (story + beats + figures + quotes) in the rolled-back txn.

    A relay rides out a solar storm: the relay-keeper reassures (yesterday), an engineer
    counts the cost (today). One figure is `bible`-sourced (a hand-authored canon
    person), one `tick`-sourced (the living world) — both attribute the same way.
    """
    day = datetime(2626, 6, 24)

    store.insert_story(
        conn,
        store.Story(
            id="demo-relay",
            title="The Halcyon relay holds",
            summary="An orbital relay survives a once-in-a-decade solar storm.",
            arc_stage=store.ARC_DEVELOPING,
            source=_TICK,
            created_tick=1,
        ),
    )
    store.insert_beats(
        conn,
        [
            store.Event(
                id="demo-r1",
                title="The relay rides out the storm",
                body="The Halcyon relay holds through the night's solar storm.",
                in_world_datetime=(day - timedelta(days=1)).replace(hour=20),
                status="past",
                source=_TICK,
                story_id="demo-relay",
                beat_kind="development",
            ),
            store.Event(
                id="demo-r2",
                title="Engineers tally the damage",
                body="Two array panels are scorched; replacements are queued.",
                in_world_datetime=day.replace(hour=9),
                status="today",
                source=_TICK,
                story_id="demo-relay",
                beat_kind="consequence",
            ),
        ],
    )
    store.insert_figures(
        conn,
        [
            store.Figure(
                id="demo-fig-mira",
                name="Mira Voss",
                role="relay-keeper",
                card_text="The steady hand who runs the Halcyon relay.",
                source=_BIBLE,
            ),
            store.Figure(
                id="demo-fig-joren",
                name="Joren Task",
                role="array engineer",
                card_text="Counts the cost in panels and hours.",
                source=_TICK,
            ),
        ],
    )
    store.insert_quotes(
        conn,
        [
            store.Quote(
                id="demo-r1-q0",
                story_id="demo-relay",
                figure_id="demo-fig-mira",
                text="We are not going dark tonight.",
                in_world_datetime=(day - timedelta(days=1)).replace(hour=20),
                beat_id="demo-r1",
                stance="reassuring",
                source=_BIBLE,
            ),
            store.Quote(
                id="demo-r2-q0",
                story_id="demo-relay",
                figure_id="demo-fig-joren",
                text="Two panels to replace, but the spine held.",
                in_world_datetime=day.replace(hour=9),
                beat_id="demo-r2",
                stance="matter-of-fact",
                source=_TICK,
            ),
        ],
    )
    return day


def _show_news(conn, now: datetime) -> None:
    """Print the desk's framing brief for the demo story — quotes attributed + dated."""
    everything = news_select.select_for(conn, now, count=10_000, ground=False)
    selected = [s for s in everything if s.story.id.startswith(_DEMO_PREFIX)]
    print("\n=== NEWS DESK — the brief the anchor is given ===")
    for sel in selected:
        print(news._story_brief(sel, now))


def _show_talk(conn, now: datetime) -> None:
    """Print the writers'-room 'what people are saying' slice the DJs reference."""
    iw_now = clock.to_inworld(now)
    window = timedelta(days=settings.context_event_window_days)
    quotes = context._select_quotes(conn, None, iw_now, window)
    quotes = [(q, f) for q, f in quotes if q.story_id == "demo-relay"]
    print("\n=== WRITERS' ROOM — the dynamic slice the DJs see ===")
    print(context._render_dynamic([], [], quotes, now) or "  (no quotes near now)")


def main() -> int:
    """Seed a peopled story, show both textual surfaces, roll back (nothing kept)."""
    print(
        "\nFigures & quotes (D10) — the world's people speak. One peopled story; the\n"
        "news desk ATTRIBUTES a dated quote and the writers' room SURFACES an opinion\n"
        "for the DJs. (Demo writes are rolled back. Invented in-world people only.)"
    )
    with store.connect() as conn:
        try:
            day = _seed_demo_world(conn)
            now = clock.to_real(day.replace(hour=10))
            _show_news(conn, now)
            _show_talk(conn, now)
        finally:
            conn.rollback()  # the demo's seed never persists
    print(
        "\nSame people, framed by when they spoke — that's attribution off the living "
        "world.\nFor the GENERATED path: make world-tick   ·   for a voiced bulletin: "
        "make format FMT=news\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

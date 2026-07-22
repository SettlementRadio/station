"""R5.2 (=E1.9) — the World screen's read side: digest + arcs + beat timeline.

A pure view over the world store: the latest post-tick DIGESTS (what changed and how
today should unfold), the ARCS in flight (each active story → stage → its next planned
beat), and today's expected BEAT TIMELINE (every beat dated to the in-world today,
hour-sorted, marked planned vs already landed). Nothing here writes or generates — the
tick/micro-tick run buttons on the page reuse the E1.1 actions machinery.

DB-backed, so it degrades to a readable note (never a 500) when the store is down.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..world import clock, digest, events, store

log = get_logger(__name__)


def _arc_row(conn, story, now: datetime) -> dict:  # noqa: ANN001
    """One active story as an arc row: stage, tags, latest beat, next planned beat."""
    beats = store.story_beats(conn, story.id)
    landed = [b for b in beats if events.has_landed(b, now)]
    latest = landed[-1] if landed else (beats[-1] if beats else None)
    next_planned = None
    for b in beats:
        if b.planned and not events.has_landed(b, now):
            next_planned = {
                "title": b.title,
                "phrase": events.relative_phrase(b, now),
                "when": b.in_world_datetime.strftime("%H:%M"),
            }
            break
    return {
        "id": story.id,
        "title": story.title,
        "stage": story.arc_stage,
        "tags": list(story.tags),
        "latest": latest.title if latest else None,
        "next_planned": next_planned,
    }


def _timeline(conn, stories, now: datetime) -> list[dict]:  # noqa: ANN001
    """Every active-story beat dated to the in-world TODAY, hour-sorted."""
    iw_today = clock.to_inworld(now).date()
    rows: list[dict] = []
    for story in stories:
        for b in store.story_beats(conn, story.id):
            if b.in_world_datetime.date() != iw_today:
                continue
            rows.append(
                {
                    "when": b.in_world_datetime.strftime("%H:%M"),
                    "sort": b.in_world_datetime,
                    "title": b.title,
                    "story": story.title,
                    "planned": b.planned,
                    "landed": events.has_landed(b, now),
                }
            )
    rows.sort(key=lambda r: r["sort"])
    for r in rows:
        del r["sort"]
    return rows


def view(now: datetime | None = None) -> dict:
    """Assemble the World view model (DB-backed; degrades to a note if store down)."""
    now = now or datetime.now()
    try:
        with store.connect() as conn:
            digests = digest.recent(conn, limit=settings.world_digest_keep)
            stories = store.active_stories(conn)
            arcs = [_arc_row(conn, s, now) for s in stories]
            timeline = _timeline(conn, stories, now)
    except Exception as exc:  # noqa: BLE001 — the page degrades, never 500s
        log.warning("panel_world_screen_unavailable", error=str(exc))
        return {"available": False, "error": str(exc)}

    return {
        "available": True,
        "error": None,
        "digests": digests,
        "arcs": arcs,
        "timeline": timeline,
        "in_world_today": clock.to_inworld(now).strftime("%A %Y-%m-%d"),
    }

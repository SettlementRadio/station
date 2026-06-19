"""Reproducibly seed the world-state DB from `docs/CANON.md` (PHASE_B_TASKS.md B1).

Run it with:

    .venv/bin/python -m src.world.seed     # (or: make seed)

It parses CANON.md (`canon_source`), then in ONE transaction creates the schema,
clears the world tables, and reloads them. Re-running reproduces the exact state
the source file describes — no orphans, no duplicates. CANON.md stays the thing a
human edits; this just projects it into the queryable store.
"""

from __future__ import annotations

from ..config import settings
from ..logging_setup import get_logger
from . import canon_source, store

log = get_logger(__name__)


def seed() -> dict[str, int]:
    """Load CANON.md into the DB, replacing any prior world state.

    Returns the per-table row counts after seeding (for verification/logging).
    """
    facts, cast, events = canon_source.load(settings.canon_path)
    log.info(
        "seed_parsed",
        source=str(settings.canon_path),
        facts=len(facts),
        cast=len(cast),
        events=len(events),
    )

    with store.connect() as conn:
        store.init_schema(conn)
        store.clear_world(conn)
        store.insert_canon(conn, facts)
        store.insert_cast(conn, cast)
        store.insert_events(conn, events)
        # Provenance state (stable, so re-seeding reproduces it exactly).
        store.set_state(conn, "seed_source", "docs/CANON.md")
        store.set_state(conn, "world_years_ahead", str(settings.world_years_ahead))
        result = store.counts(conn)

    log.info("seed_done", **result)
    return result


if __name__ == "__main__":
    counts = seed()
    log.info("seed_summary", **counts)

    # Done-when proof: a query returns events filtered by status (B1). Show the
    # upcoming events the seed just wrote.
    with store.connect() as conn:
        upcoming = store.events_by_status(conn, "upcoming")
    for event in upcoming:
        log.info(
            "upcoming_event",
            id=event.id,
            title=event.title,
            when=event.in_world_datetime.isoformat(),
            tags=event.tags,
        )

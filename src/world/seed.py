"""Seed / refresh the world-state DB from the canon bible (B1; split in D1.2).

Two operator commands, deliberately split so a routine bible edit never destroys
the living, tick-generated world (PHASE_D_OVERVIEW §2a):

    .venv/bin/python -m src.world.seed           # safe canon refresh (default)
    .venv/bin/python -m src.world.seed reset      # destructive full wipe (prompts)

* `seed_canon()` — the SAFE everyday command (`make seed-canon`): re-load the
  folder-owned canon/cast/SEED-events; leave any `source='tick'` events (the world
  the nightly tick generates, from D3) untouched.
* `reset_world()` — the DESTRUCTIVE full wipe (`make reset-world`): truncate the
  whole world+canon set and rebuild from the folder. The CLI warns + confirms.

Both read the bible via `canon_source` (the `docs/canon/` folder when populated,
else the legacy single `docs/CANON.md`) and load it behind the unchanged
`store.insert_*` seam. Re-running reproduces the state the source describes.
"""

from __future__ import annotations

import sys

from ..config import settings
from ..logging_setup import get_logger
from . import canon_source, store

log = get_logger(__name__)


def _seed(scope: str) -> dict[str, int]:
    """Load the bible and (re)insert it, clearing only the tables `scope` owns.

    `scope="canon"` is the safe refresh; `scope="world"` is the full wipe. See
    `store.clear_world` for exactly what each scope clears.
    """
    facts, cast, events = canon_source.load_world(
        settings.canon_dir, settings.canon_path
    )
    using_folder = canon_source.has_canon_folder(settings.canon_dir)
    source_path = settings.canon_dir if using_folder else settings.canon_path
    log.info(
        "seed_parsed",
        scope=scope,
        source=str(source_path),
        folder=using_folder,
        facts=len(facts),
        cast=len(cast),
        events=len(events),
    )

    with store.connect() as conn:
        store.init_schema(conn)
        store.clear_world(conn, scope=scope)
        store.insert_canon(conn, facts)
        store.insert_cast(conn, cast)
        store.insert_events(conn, events)
        # Provenance state (stable, so re-seeding reproduces it exactly).
        store.set_state(conn, "seed_source", str(source_path))
        store.set_state(conn, "world_years_ahead", str(settings.world_years_ahead))
        result = store.counts(conn)

    log.info("seed_done", scope=scope, **result)
    return result


def seed_canon() -> dict[str, int]:
    """SAFE everyday refresh: reload folder-owned canon/cast/seed-events.

    Leaves `source='tick'` events (the living world) intact. Returns the per-table
    row counts after seeding (for verification/logging).
    """
    return _seed("canon")


def reset_world() -> dict[str, int]:
    """DESTRUCTIVE full world+canon wipe, then rebuild from the folder.

    Truncates canon/cast/events/state — including the tick-generated world. The CLI
    wraps this in a warning + confirmation; call it directly only when you mean it.
    """
    return _seed("world")


# --- CLI --------------------------------------------------------------------


def _confirm_reset() -> bool:
    """Loud warning + an explicit typed confirmation for the destructive reset."""
    print("\n" + "!" * 70)
    print("reset-world is DESTRUCTIVE: it ERASES the entire living world —")
    print("all events (including tick-generated stories), canon, cast, and state.")
    print("This cannot be undone. (Station config/catalog are NOT touched.)")
    print("!" * 70)
    return input("Type 'reset-world' to confirm: ").strip() == "reset-world"


def _run_cli(argv: list[str]) -> dict[str, int]:
    args = argv[1:]
    force = "--force" in args
    positional = [a for a in args if not a.startswith("-")]
    cmd = positional[0] if positional else "canon"

    if cmd in ("canon", "seed-canon"):
        return seed_canon()
    if cmd in ("reset", "reset-world"):
        if not force and not _confirm_reset():
            log.warning("reset_world_aborted")
            print("Aborted — the world was not touched.")
            raise SystemExit(1)
        return reset_world()
    raise SystemExit(
        f"unknown command {cmd!r}; use 'canon' (safe, default) or 'reset' (destructive)"
    )


if __name__ == "__main__":
    counts = _run_cli(sys.argv)
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

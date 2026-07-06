"""Seed the hand-entered sponsors catalog from its manifest (D8.2).

    .venv/bin/python -m src.world.seed_sponsors      # or: make seed-sponsors

The manifest (`config/sponsors.yaml`) is the source of truth; this loader
conforms to ITS field shape. Sponsors are catalog, not world state (§2a): this
is their OWN refresh path — `seed-canon`/`reset-world` never touch the table.
Re-running reproduces exactly what the manifest describes.

⚠ Populating REAL sponsors is gated on CM (donations live), not on D8 — the
manifest ships with an empty list, which seeds an empty table (aired: nothing).

Date handling: YAML dates (`run_start: 2027-01-01`) parse as `date`; they are
widened to midnight `datetime`s, making `run_end` a half-open "first day it may
NOT air" boundary (see the manifest header).
"""

from __future__ import annotations

import sys
from datetime import date, datetime, time
from pathlib import Path

import yaml

from ..config import settings
from ..logging_setup import get_logger
from . import store

log = get_logger(__name__)


def _as_datetime(value: object, *, field: str, sponsor_id: str) -> datetime | None:
    """A manifest run-window value as a datetime (None passes through)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    raise ValueError(f"sponsor {sponsor_id!r}: {field} must be a date, got {value!r}")


def load_manifest(path: Path) -> list[store.Sponsor]:
    """Parse the sponsors manifest into `Sponsor` rows (no DB).

    Fails loudly on a missing file or a row missing its required fields — a
    malformed manifest should stop the seed, not half-load the catalog.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = raw.get("sponsors") or []
    sponsors: list[store.Sponsor] = []
    for row in rows:
        sid = row["id"]
        sponsors.append(
            store.Sponsor(
                id=sid,
                name=row["name"],
                powered_by_text=str(row.get("powered_by_text") or "").strip(),
                audio_path=row.get("audio_path"),
                run_start=_as_datetime(
                    row.get("run_start"), field="run_start", sponsor_id=sid
                ),
                run_end=_as_datetime(
                    row.get("run_end"), field="run_end", sponsor_id=sid
                ),
                weight=int(row.get("weight") or 1),
                tags=[str(t) for t in (row.get("tags") or [])],
            )
        )
    return sponsors


def seed_sponsors() -> dict[str, int]:
    """Refresh the `sponsors` table from the manifest; return summary counts."""
    sponsors = load_manifest(settings.sponsors_manifest_path)

    with store.connect() as conn:
        store.init_schema(conn)
        store.clear_sponsors(conn)
        inserted = store.insert_sponsors(conn, sponsors)
        active = len(store.active_sponsors(conn, datetime.now()))

    result = {"sponsors": inserted, "active_now": active}
    log.info("seed_sponsors_done", **result)
    return result


if __name__ == "__main__":
    counts = seed_sponsors()
    print(
        f"sponsors: {counts['sponsors']} seeded, "
        f"{counts['active_now']} inside their run window right now"
    )
    sys.exit(0)

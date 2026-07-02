"""D6.4 — the PUBLIC now-playing / program-info feed for the web player.

Writes a small JSON (`settings.nowplaying_feed_path`) the C8 web player reads to show
what's on: the current program + segment, what's next, and the AI-disclosure line. It
is written the way `schedule.json` / `playlist.txt` are — a plain file refreshed at the
end of each scheduler top-up, so it tracks the air — and stands alone (cat the JSON)
before the C8 player exists.

PUBLIC-SAFE BY CONSTRUCTION (audit fix). This feed is internet-facing (it drives the
public player), so it is an explicit ALLOW-LIST of publishable fields only:

    station · disclosure · updated_at · now{program, format, hosts, air_time} · next[…]

It NEVER carries internal/operator state — no buffer depth, health, cost, story-log/
world internals, segment ids, audio paths, or durations. Internal state lives in the
PRIVATE operator console (`src/console.py`, D6.3); this is its public counterpart. The
two are deliberately separate surfaces: internal → console; public subset → this feed.

The AI-disclosure line is sourced from `disclosure.DISCLOSURE_LINE` (kept identical to
the web copy in `web/src/lib/disclosure.ts`), so air and screen always agree — a
CLAUDE.md hard rule.

    .venv/bin/python -m src.nowplaying     # write + print the feed (make now-playing)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from .config import settings
from .disclosure import DISCLOSURE_LINE
from .logging_setup import get_logger
from .scheduler import _load_state, onair_hosts, split_schedule
from .world import programming, store

log = get_logger(__name__)

# Brand copy (intrinsic, like DISCLOSURE_LINE — not an operator dial).
STATION_NAME = "Settlement Radio"

# Friendly, public labels for the internal format ids (the player shows these).
_FORMAT_LABELS = {
    "talk": "Talk",
    "news": "The Settlement News",
    "music": "Music",
    "ident": "Station ID",
}


def _titlecase(host_id: str) -> str:
    """`vell` → `Vell`, `the-archivist` → `The Archivist` (fallback display name)."""
    return host_id.replace("-", " ").replace("_", " ").title()


def _onair_host_ids(entry: dict) -> list[str]:
    """The cast ids actually on air for an entry — via the shared `onair_hosts` helper.

    Empty for a non-programmed segment (an ident carries no program). Otherwise the
    program's hosts sliced to the format (the SAME answer the operator console shows).
    """
    if not entry.get("program"):  # idents etc. — no hosts to show
        return []
    try:
        program = programming.program_for(datetime.fromisoformat(entry["air_time"]))
    except (KeyError, TypeError, ValueError):
        return []
    return onair_hosts(program, entry.get("format"))


def _name_map(host_ids: set[str]) -> dict[str, str]:
    """Resolve cast ids to display names (best-effort; degrade to a titlecased id).

    One DB read for the whole feed; a store failure never breaks the public feed — it
    falls back to a readable name derived from the id, so the file always writes.
    """
    names = {h: _titlecase(h) for h in host_ids}
    if not host_ids:
        return names
    try:
        with store.connect() as conn:
            for hid in host_ids:
                member = store.get_cast_member(conn, hid)
                if member is not None:
                    names[hid] = member.name
    except Exception as exc:  # noqa: BLE001 — the public feed must always write
        log.warning("nowplaying_cast_lookup_failed", error=str(exc))
    return names


def _public_entry(entry: dict, names: dict[str, str]) -> dict:
    """One schedule entry as a PUBLIC-SAFE item — the allow-list only, nothing else."""
    fmt = entry.get("format")
    return {
        "program": entry.get("program_name"),  # None for a non-programmed segment
        "format": fmt,
        "format_label": _FORMAT_LABELS.get(fmt, _titlecase(fmt) if fmt else None),
        "hosts": [names[h] for h in _onair_host_ids(entry)],
        "air_time": entry.get("air_time"),  # when it airs — public "on now / next"
    }


def build_feed(now: datetime, state: dict) -> dict:
    """Assemble the public now-playing feed dict from the live schedule (read-only)."""
    current, upcoming = split_schedule(now, state)
    upcoming = upcoming[: settings.nowplaying_next_count]

    # Resolve every host id shown (now + next) in one pass.
    ids: set[str] = set()
    for e in filter(None, [current, *upcoming]):
        ids.update(_onair_host_ids(e))
    names = _name_map(ids)

    return {
        "station": STATION_NAME,
        "disclosure": DISCLOSURE_LINE,  # kept in sync with web/src/lib/disclosure.ts
        "updated_at": now.isoformat(),
        "now": _public_entry(current, names) if current is not None else None,
        "next": [_public_entry(e, names) for e in upcoming],
    }


def write_feed(now: datetime | None = None) -> dict:
    """Build + write the public feed to `settings.nowplaying_feed_path`; return it.

    Called at the end of each scheduler top-up (best-effort there) and by the CLI. The
    write is atomic-ish (temp + replace) so a reader never sees a half-written file.
    """
    now = now or datetime.now()
    feed = build_feed(now, _load_state())
    path: Path = settings.nowplaying_feed_path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(feed, indent=2), encoding="utf-8")
    tmp.replace(path)
    log.info(
        "nowplaying_written",
        path=str(path),
        now=feed["now"]["format"] if feed["now"] else None,
        next=len(feed["next"]),
    )
    return feed


def main(argv: list[str]) -> int:
    """CLI: write the public feed and print it (verification before the C8 player)."""
    feed = write_feed()
    print(json.dumps(feed, indent=2, ensure_ascii=False))
    print(f"\n----- wrote {settings.nowplaying_feed_path} -----")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

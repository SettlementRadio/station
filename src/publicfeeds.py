"""R7.0 — the two SLOW public feeds the web station front reads.

`src/nowplaying.py` publishes the FAST feed (what is on air this minute). This module
publishes the two that change rarely, so the site can render a real station front:

    schedule-public.json   today + the week's resolved programme tiling
    djs-public.json        the public cast slice (the `/voices` page)

Both are written beside `nowplaying.json` on the same scheduler top-up cadence, and
both follow the SAME allow-list discipline (`nowplaying`'s docstring is the rule):
every field is enumerated here in code, so nothing internal can leak by accident.

    schedule: station · disclosure · updated_at · programs{id: {name, tagline, hosts}}
              · days[{date, weekday, entries[{program, start, end}]}]
    djs:      station · disclosure · updated_at
              · djs[{id, name, role, bio, based, shows[{id, name}]}]

What is deliberately NOT here: `brief` (internal editorial direction — the public line
is `tagline`), `card_text` (a prompt, not copy — only the operator-authored `Public
bio:` bullet is published), `energy`/`clock`/`break_every`/`guest_chance`/`domains`/
`talk_length_sec` (production dials), and anything from the world store beyond the
cast's two public fields.

TIMES ARE SETTLEMENT WALL CLOCK, naive ISO (no zone suffix) — exactly like
`nowplaying`'s `air_time`. The in-world wall clock equals the station's real wall clock
(the world clock shifts only the YEAR), and the site prints these strings as given —
"settlement time (yours)". A viewer must never see them re-zoned by a browser.

    .venv/bin/python -m src.publicfeeds     # write + print both (make public-feeds)
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from .config import settings
from .disclosure import DISCLOSURE_LINE
from .logging_setup import get_logger
from .nowplaying import STATION_NAME, titlecase
from .world import programming, store

log = get_logger(__name__)

_WEEKDAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


# --- Shared cast lookup ------------------------------------------------------


def cast_map() -> dict[str, store.CastMember]:
    """Every cast row by id — best-effort ({} when the store is unreachable).

    One DB read serves both feeds. A store failure is logged and degrades (the
    schedule feed falls back to titlecased host ids; the DJs feed is skipped rather
    than published empty — see `write_djs_feed`), so a public surface is never
    replaced by a worse version of itself because Postgres blinked.
    """
    try:
        with store.connect() as conn:
            return {m.id: m for m in store.all_cast(conn)}
    except Exception as exc:  # noqa: BLE001 — a public feed must never hard-fail
        log.warning("publicfeeds_cast_lookup_failed", error=str(exc))
        return {}


def _host_names(
    host_ids: tuple[str, ...], cast: dict[str, store.CastMember]
) -> list[str]:
    """Display names for a program's hosts (titlecased id when the cast is missing)."""
    return [cast[h].name if h in cast else titlecase(h) for h in host_ids]


def _envelope(now: datetime) -> dict:
    """The three fields every public feed carries (brand + the disclosure hard rule)."""
    return {
        "station": STATION_NAME,
        "disclosure": DISCLOSURE_LINE,  # in sync with web/src/lib/disclosure.ts
        "updated_at": now.isoformat(),
    }


# --- The schedule feed -------------------------------------------------------


def build_schedule_feed(
    now: datetime, cast: dict[str, store.CastMember] | None = None
) -> dict:
    """The resolved grid as a public feed: a programme directory + N days of tiling.

    `days[0]` is today, and each day's `entries` tile it gap-free with half-open
    `[start, end)` runs (`programming.day_tiling`, which resolves every boundary
    through `program_for` — so the feed can never disagree with what airs). Entries
    carry only a programme ID; the details live once in `programs`, keyed by that ID,
    which keeps a week's payload small.

    "On air now" is deliberately NOT baked in: the entries carry real times, so the
    page computes the highlight itself and it moves without a reload (R7.2).
    """
    cast = cast_map() if cast is None else cast
    today: date = now.date()
    week = programming.week_tiling(today, settings.schedule_feed_days)

    days: list[dict] = []
    programs: dict[str, dict] = {}
    for day, runs in week:
        entries = []
        for start, end, program in runs:
            if program.id not in programs:
                programs[program.id] = {
                    "name": program.name,
                    "tagline": program.public_tagline,
                    "hosts": _host_names(program.hosts, cast),
                }
            entries.append(
                {
                    "program": program.id,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                }
            )
        days.append(
            {
                "date": day.isoformat(),
                "weekday": _WEEKDAY_NAMES[day.weekday()],
                "entries": entries,
            }
        )

    return {**_envelope(now), "programs": programs, "days": days}


# --- The DJs feed ------------------------------------------------------------


def _scheduled_shows(start: date, days: int) -> dict[str, list[dict]]:
    """host id → the shows they present in the published week, first-on-air order.

    Derived from the TILING, not the program table, so a benched programme (kept as a
    definition but off the grid, D12.4) never appears on a host's page. A show hosted
    twice a week is listed once. The window is the SAME one the schedule feed
    publishes, so the two feeds always agree.
    """
    shows: dict[str, list[dict]] = {}
    seen: set[tuple[str, str]] = set()
    for _day, runs in programming.week_tiling(start, days):
        for _start, _end, program in runs:
            for host in program.hosts:
                if (host, program.id) in seen:
                    continue
                seen.add((host, program.id))
                shows.setdefault(host, []).append(
                    {"id": program.id, "name": program.name}
                )
    return shows


def build_djs_feed(
    now: datetime, cast: dict[str, store.CastMember] | None = None
) -> dict:
    """The public cast slice: name, role line, public bio, station-vs-field, shows.

    Only the two publishable card fields are used (`role` from the card heading,
    `public_bio` from the operator-authored bullet) — `card_text` is a prompt and
    never leaves the box. The `cast` table holds the DJs only (the tech staff live in
    a different canon section and are not projected to rows), so nobody who never
    speaks on air is published here.
    """
    cast = cast_map() if cast is None else cast
    shows = _scheduled_shows(now.date(), settings.schedule_feed_days)
    djs = [
        {
            "id": m.id,
            "name": m.name,
            "role": m.role,
            "bio": m.public_bio,
            "based": m.based,  # 'station' | 'field' — the correspondent badge
            "shows": shows.get(m.id, []),
        }
        for m in sorted(cast.values(), key=lambda m: m.name)
    ]
    return {**_envelope(now), "djs": djs}


# --- Writing -----------------------------------------------------------------


def _write_json(path: Path, feed: dict) -> None:
    """Atomic-ish write (temp + replace) so a reader never sees a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(feed, indent=2), encoding="utf-8")
    tmp.replace(path)


def write_schedule_feed(
    now: datetime | None = None, cast: dict[str, store.CastMember] | None = None
) -> dict:
    """Build + write `settings.schedule_feed_path`; return the feed."""
    now = now or datetime.now()
    feed = build_schedule_feed(now, cast)
    _write_json(settings.schedule_feed_path, feed)
    log.info(
        "schedule_feed_written",
        path=str(settings.schedule_feed_path),
        programs=len(feed["programs"]),
        days=len(feed["days"]),
    )
    return feed


def write_djs_feed(
    now: datetime | None = None, cast: dict[str, store.CastMember] | None = None
) -> dict | None:
    """Build + write `settings.djs_feed_path`; return the feed, or None if skipped.

    An empty cast means the store was unreachable (or unseeded) — publishing an empty
    `/voices` page would be strictly worse than leaving the last good file in place,
    so the write is SKIPPED and logged loudly instead.
    """
    now = now or datetime.now()
    cast = cast_map() if cast is None else cast
    if not cast:
        log.warning("djs_feed_skipped_empty_cast", path=str(settings.djs_feed_path))
        return None
    feed = build_djs_feed(now, cast)
    _write_json(settings.djs_feed_path, feed)
    log.info("djs_feed_written", path=str(settings.djs_feed_path), djs=len(feed["djs"]))
    return feed


def write_feeds(now: datetime | None = None) -> dict[str, dict | None]:
    """Write both slow feeds from ONE cast read; return `{"schedule": …, "djs": …}`."""
    now = now or datetime.now()
    cast = cast_map()
    return {
        "schedule": write_schedule_feed(now, cast),
        "djs": write_djs_feed(now, cast),
    }


def main(argv: list[str]) -> int:
    """CLI: write both slow public feeds and print them (standalone verification)."""
    feeds = write_feeds()
    print(json.dumps(feeds["schedule"], indent=2, ensure_ascii=False))
    print(json.dumps(feeds["djs"], indent=2, ensure_ascii=False))
    print(f"\n----- wrote {settings.schedule_feed_path} -----")
    print(f"----- wrote {settings.djs_feed_path} -----")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

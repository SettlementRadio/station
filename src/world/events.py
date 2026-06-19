"""Event progression + the relative-time renderer (PHASE_B_TASKS.md B2).

This is the time-awareness spine: given a stored `Event` (its in-world datetime)
and the current real `now`, it computes

* `status_of(event, now)` — upcoming | today | past, and
* `relative_phrase(event, now)` — "in five days" / "tonight" / "yesterday" /
  "last week" — the natural phrase a DJ would actually say.

Both compare the event against the in-world `now` from `clock.to_inworld`. They
are PURE (no DB, no I/O) so the brittle bit — the phrasing thresholds — is
trivially testable, and so `context.assemble` (B3) can call them on rows it has
already fetched. The `__main__` demo renders the SAME event at two `now` values
and shows the phrase flip ("in five days" -> "yesterday"), the progressing-event
proof the phase is built around.

The thresholds and number words below are intrinsic to this renderer's logic, so
they live here as named module constants rather than in `config.py` (see the
config-vs-constant rule in that file).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from ..logging_setup import get_logger
from . import clock
from .store import Event

log = get_logger(__name__)

# Status values (also the strings seeded into the DB by CANON.md).
UPCOMING = "upcoming"
TODAY = "today"
PAST = "past"

# Day-count thresholds for the relative phrasing, in whole calendar days.
_WEEK = 7
_FORTNIGHT = 14  # past this, phrase in weeks
_MONTH = 28  # past this, phrase in months

# Small-number words so the DJ says "in five days", not "in 5 days".
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
    11: "eleven",
    12: "twelve",
}


def _word(n: int) -> str:
    """ "5" -> "five" for small counts; fall back to the digits beyond the table."""
    return _NUMBER_WORDS.get(n, str(n))


def status_of(event: Event, now: datetime) -> str:
    """Compute the event's live status from its in-world datetime vs the clock."""
    iw_now = clock.to_inworld(now)
    event_day = event.in_world_datetime.date()
    if event_day == iw_now.date():
        return TODAY
    return UPCOMING if event.in_world_datetime > iw_now else PAST


def progressed(event: Event, now: datetime) -> Event:
    """Return a copy of `event` with its `status` recomputed for `now`.

    A convenience for callers (B3 context assembly) that want the row with a
    live status; the stored snapshot from the seed is left untouched.
    """
    return replace(event, status=status_of(event, now))


def relative_phrase(event: Event, now: datetime) -> str:
    """A natural, spoken relative-time phrase for the event as of `now`.

    Examples: "tomorrow", "in five days", "tonight", "yesterday", "last week".
    Granularity is whole calendar days; same-day events use a time-of-day phrase.
    """
    iw_now = clock.to_inworld(now)
    day_delta = (event.in_world_datetime.date() - iw_now.date()).days

    if day_delta == 0:
        return _same_day_phrase(event.in_world_datetime)

    future = day_delta > 0
    n = abs(day_delta)

    if n == 1:
        return "tomorrow" if future else "yesterday"
    if n == 2:
        return "the day after tomorrow" if future else "the day before yesterday"
    if n < _WEEK:
        return f"in {_word(n)} days" if future else f"{_word(n)} days ago"
    if n < _FORTNIGHT:
        return "next week" if future else "last week"
    if n <= _MONTH:
        weeks = round(n / 7)
        return f"in {_word(weeks)} weeks" if future else f"{_word(weeks)} weeks ago"

    months = round(n / 30)
    if months <= 1:
        return "next month" if future else "last month"
    return f"in {_word(months)} months" if future else f"{_word(months)} months ago"


def _same_day_phrase(event_dt: datetime) -> str:
    """A time-of-day phrase for an event happening today ("tonight", etc.)."""
    hour = event_dt.hour
    if hour < 12:
        return "this morning"
    if hour < 17:
        return "this afternoon"
    return "tonight"


# --- Demo: the progressing-event proof (B2 done-when) -----------------------


def _demo(event_id: str = "lumen-festival") -> None:
    """Render one event at two `now` values and show the relative-phrase flip.

    Anchors `now` on the event's own real-world face so the proof is deterministic
    (independent of the wall clock): five days before -> "in five days"
    (upcoming), one day after -> "yesterday" (past). Reads the event from the DB
    so it exercises the real seeded row — run `make seed` first.
    """
    from datetime import timedelta

    from . import store

    with store.connect() as conn:
        event = store.get_event(conn, event_id)

    if event is None:
        log.error("demo_event_missing", event_id=event_id, hint="run `make seed`")
        print(f"Event {event_id!r} not found — run `make seed` first.")
        return

    event_real = clock.to_real(event.in_world_datetime)
    points = {
        "now − 5 days": event_real - timedelta(days=5),
        "now + 1 day": event_real + timedelta(days=1),
    }

    print(f"\nProgressing-event demo — {event.title}")
    print(f"  in-world datetime: {event.in_world_datetime.isoformat()}\n")
    for label, now in points.items():
        status = status_of(event, now)
        phrase = relative_phrase(event, now)
        print(f'  {label:<12} (now={now:%Y-%m-%d}):  [{status:<8}] "{phrase}"')
        log.info(
            "demo_point",
            label=label,
            now=now.isoformat(),
            inworld_now=clock.to_inworld(now).isoformat(),
            status=status,
            phrase=phrase,
        )
    print()


if __name__ == "__main__":
    # Runnable proof:  .venv/bin/python -m src.world.events   (or: make demo)
    _demo()

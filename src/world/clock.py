"""The world clock — the single source of the real -> in-world time mapping.

CANON.md ("The time concept"): the station lives `real year + 600`, and a real
Tuesday 02:00 is an in-world Tuesday 02:00, six centuries on. Phase A computed
that inline inside `writer.py`; B2 formalizes it HERE so there is exactly one
place that knows the offset (`settings.world_years_ahead`) and everything —
the writer's time check (display) and event progression (arithmetic) — reads it.

Two distinct uses, deliberately kept apart:

* **Display** (`render_wall_clock`) — the spoken time check. It keeps the REAL
  weekday/day/month and only relabels the year (+600), honouring CANON's "a real
  Tuesday is an in-world Tuesday" rule. The result is a *fiction*: 2626-06-16
  would not really fall on that weekday, but the station speaks it that way.
* **Arithmetic** (`to_inworld` / `to_real`) — used by `events.py` to measure the
  distance between `now` and an event's stored in-world datetime. Only durations
  and dates matter here (never the weekday), so shifting the year by +600 on both
  sides is exact: the gap to an event is identical in real and in-world frames.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings


def _shift_year(dt: datetime, delta: int) -> datetime:
    """Return `dt` with its year moved by `delta`, keeping the wall clock.

    Handles the one calendar trap: 29 February can map onto a non-leap year,
    because years 600 apart can differ under the Gregorian 400-year rule (2000 is
    a leap year, 2600 is not). In that rare case we land on 28 February rather
    than raise.
    """
    try:
        return dt.replace(year=dt.year + delta)
    except ValueError:
        return dt.replace(year=dt.year + delta, day=28)


def to_inworld(now: datetime) -> datetime:
    """Map a real datetime to its in-world face (same wall clock, year + 600)."""
    return _shift_year(now, settings.world_years_ahead)


def to_real(inworld: datetime) -> datetime:
    """Inverse of `to_inworld`: map an in-world datetime back to real time."""
    return _shift_year(inworld, -settings.world_years_ahead)


def inworld_year(real_year: int) -> int:
    """The in-world year for a given real year (`real_year + 600`)."""
    return real_year + settings.world_years_ahead


def render_wall_clock(now: datetime) -> str:
    """Render `now` as the in-world wall clock for a spoken time check.

    Keeps the real weekday, day, month and time exactly and shifts only the year,
    e.g. "Tuesday, 16 June 2626, 02:14". This is the display fiction (see module
    docstring) — the weekday is the real one, not recomputed for the +600yr date.
    """
    return f"{now:%A}, {now:%-d %B} {inworld_year(now.year)}, {now:%H:%M}"

"""Tests for event progression + the relative-time renderer (src/world/events.py).

CLAUDE.md flags "the relative-time renderer" as exactly the kind of brittle logic
to test. These are pure (no DB): we build an `Event` by hand and assert the status
and the spoken phrase across the boundaries that matter — including the B2 hero
flip ("in five days" -> "yesterday").
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.world import events
from src.world.store import Event

# An in-world event at 2626-06-24 20:00 (real-world face: 2026-06-24 20:00).
_EVENT = Event(
    id="lumen-festival",
    title="Lumen Festival",
    body="A festival of light.",
    in_world_datetime=datetime(2626, 6, 24, 20, 0),
    status="upcoming",
)

# The real-world face of the event; offset from here to drive `now`.
_NOW0 = datetime(2026, 6, 24, 20, 0)


def _at(days: int) -> datetime:
    """A real `now` `days` away from the event's real-world face."""
    return _NOW0 + timedelta(days=days)


def test_progressing_flip_in_five_days_to_yesterday():
    # The B2 done-when, exactly: five days before vs one day after.
    assert events.relative_phrase(_EVENT, _at(-5)) == "in five days"
    assert events.status_of(_EVENT, _at(-5)) == events.UPCOMING
    assert events.relative_phrase(_EVENT, _at(+1)) == "yesterday"
    assert events.status_of(_EVENT, _at(+1)) == events.PAST


def test_same_day_is_today_and_tonight():
    # 20:00 is evening, so a same-day render says "tonight".
    assert events.status_of(_EVENT, _at(0)) == events.TODAY
    assert events.relative_phrase(_EVENT, _at(0)) == "tonight"


def test_tomorrow_and_yesterday_boundaries():
    assert events.relative_phrase(_EVENT, _at(-1)) == "tomorrow"
    assert events.relative_phrase(_EVENT, _at(-2)) == "the day after tomorrow"
    assert events.relative_phrase(_EVENT, _at(+2)) == "the day before yesterday"


def test_week_scale_phrases():
    assert events.relative_phrase(_EVENT, _at(-7)) == "next week"
    assert events.relative_phrase(_EVENT, _at(+7)) == "last week"


def test_progressed_returns_copy_with_live_status_only():
    progressed = events.progressed(_EVENT, _at(+1))
    assert progressed.status == events.PAST
    assert _EVENT.status == "upcoming"  # original snapshot untouched
    assert progressed.title == _EVENT.title

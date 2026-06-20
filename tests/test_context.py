"""Tests for the pure logic in context assembly (src/world/context.py).

`assemble()` itself needs the DB, so it is exercised by `make context`. Here we
test the brittle, DB-free bits a silent bug would hurt: the topic→tags tokenizer
that drives canon retrieval, and the dynamic-block renderer (the time-aware slice
the writer actually sees — it must surface the relative phrase and the facts, and
collapse to empty when there is nothing).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.world import clock, context
from src.world import events as events_mod
from src.world.store import CanonFact, Event


def test_topic_tags_tokenizes_freetext():
    assert context._topic_tags("Lights & Music!") == ["lights", "music"]
    assert context._topic_tags("festival") == ["festival"]
    assert context._topic_tags("") == []


def test_render_dynamic_surfaces_relative_phrase_and_facts():
    now = datetime(2026, 6, 19, 23, 0)
    # Five days out in-world -> the renderer should speak "in five days".
    event_dt = clock.to_inworld(now) + timedelta(days=5)
    event = events_mod.progressed(
        Event("lumen", "Lumen Festival", "Lamps are lit.", event_dt, "upcoming", []),
        now,
    )
    facts = [CanonFact("canon-1", "Radio connects the worlds.", [])]

    out = context._render_dynamic([event], facts, now)

    assert "Lumen Festival" in out
    assert "in five days" in out
    assert "(upcoming)" in out
    assert "Radio connects the worlds." in out


def test_render_dynamic_is_empty_with_no_world():
    assert context._render_dynamic([], [], datetime(2026, 6, 19)) == ""

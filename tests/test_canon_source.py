"""Tests for the CANON.md parser (src/world/canon_source.py).

The parser is the one piece of B1 with real, brittle logic: it turns hand-edited
markdown into the rows the seed loads, so a silent bug here means the world is
seeded wrong. We test the three section parsers against a small, representative
document (numbered facts, two DJ cards, one dated event) — not the live CANON.md,
so the test stays stable as the canon is edited.
"""

from __future__ import annotations

from datetime import datetime

from src.world import canon_source

_DOC = """\
# CANON.md — test fixture

## The station

Prose that is NOT a parsed section — must be ignored.

## Canon facts (keep small)

1. First fact, on one line.
2. **Bolded lead-in.** A second fact that wraps
   onto a continuation line.
3. Third fact.

## Cast — the DJs

### Vell — the night shift

- **Logical voice:** `vell_night`
- **Tags:** night, warmth
- **Personality:** calm and kind.

### Wren — the first-light shift

- **Logical voice:** `dj_two`
- **Tags:** morning, wonder
- **Personality:** bright and quick.

## Events — the world timeline

### Lumen Festival

- **In-world datetime:** 2626-06-24T20:00
- **Status:** upcoming
- **Tags:** festival, lights
- **Body:** A festival of light.
"""


def _load(tmp_path):
    path = tmp_path / "CANON.md"
    path.write_text(_DOC)
    return canon_source.load(path)


def test_canon_facts_are_numbered_and_cleaned(tmp_path):
    facts, _, _ = _load(tmp_path)
    assert [f.id for f in facts] == ["canon-1", "canon-2", "canon-3"]
    assert facts[0].text == "First fact, on one line."
    # Bold markers stripped, wrapped continuation joined into one fact.
    assert facts[1].text == (
        "Bolded lead-in. A second fact that wraps onto a continuation line."
    )
    assert facts[0].tags == []


def test_cast_cards_parse_name_voice_tags_and_keep_full_card(tmp_path):
    _, cast, _ = _load(tmp_path)
    assert [c.id for c in cast] == ["vell", "wren"]
    vell = cast[0]
    assert vell.name == "Vell"
    assert vell.logical_voice == "vell_night"  # backticks stripped
    assert vell.tags == ["night", "warmth"]
    # The whole card is retained for the writers' room, not just the fields.
    assert "calm and kind" in vell.card_text


def test_event_parses_datetime_status_and_tags(tmp_path):
    _, _, events = _load(tmp_path)
    assert len(events) == 1
    event = events[0]
    assert event.id == "lumen-festival"
    assert event.title == "Lumen Festival"
    assert event.in_world_datetime == datetime(2626, 6, 24, 20, 0)
    assert event.status == "upcoming"
    assert event.tags == ["festival", "lights"]
    assert event.body == "A festival of light."


def test_ignores_non_target_sections(tmp_path):
    # "## The station" prose must not leak into any parsed collection.
    facts, cast, events = _load(tmp_path)
    assert len(facts) == 3 and len(cast) == 2 and len(events) == 1


def test_series_bible_keeps_narrative_prose_only(tmp_path):
    # B3 cached core: the bible loader keeps the standing narrative section (with
    # its heading) and drops the structured sections (facts/cast/events).
    path = tmp_path / "CANON.md"
    path.write_text(_DOC)
    bible = canon_source.load_series_bible(path)
    assert "## The station" in bible
    assert "Prose that is NOT a parsed section" in bible
    # None of the structured rows leak into the cached core.
    assert "Lumen Festival" not in bible
    assert "vell_night" not in bible
    assert "First fact" not in bible

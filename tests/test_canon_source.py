"""Tests for the CANON.md parser (src/world/canon_source.py).

The parser is the one piece of B1 with real, brittle logic: it turns hand-edited
markdown into the rows the seed loads, so a silent bug here means the world is
seeded wrong. We test the three section parsers against a small, representative
document (numbered facts, two DJ cards, one dated event) — not the live CANON.md,
so the test stays stable as the canon is edited.
"""

from __future__ import annotations

from datetime import datetime

import pytest
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


# --- Folder loading (D1.1) --------------------------------------------------
# The bible grows from one CANON.md into a docs/canon/ folder of cornerstone
# files. These tests use a small fixture folder (not the live bible) so they stay
# stable as the canon is authored.

_HISTORY = """\
# 10-history.md

## History of the long quiet

Earth fell out of easy reach; the worlds learned to keep their own company.

## Canon facts

1. Earth is distant history, spoken of fondly.
   - **Tags:** earth, history
2. Travel between worlds takes weeks.
"""

_NATIONS = """\
# 20-nations.md

## The settled polities

A loose weave of worlds, each governing itself, bound by the relays.

## Canon facts

1. No single power rules the settlements.
"""

_CAST = """\
# 90-cast.md

## Cast — the DJs

### Vell — the night shift

- **Logical voice:** `vell_night`
- **Personality:** calm and kind.
"""

_EVENTS = """\
# 95-events.md

## Events — the world timeline

### Lumen Festival

- **In-world datetime:** 2626-06-24T20:00
- **Body:** A festival of light.
"""


def _make_folder(tmp_path, files: dict[str, str], name: str = "canon"):
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    for fname, text in files.items():
        (folder / fname).write_text(text)
    return folder


def test_folder_load_merges_files_with_globally_unique_ids(tmp_path):
    folder = _make_folder(
        tmp_path,
        {
            "10-history.md": _HISTORY,
            "20-nations.md": _NATIONS,
            "90-cast.md": _CAST,
            "95-events.md": _EVENTS,
            "README.md": "# not world content — must be skipped",
        },
    )
    facts, cast, events = canon_source.load_folder(folder)

    # Fact ids are namespaced by file stem, so they never collide across files.
    assert [f.id for f in facts] == [
        "canon-history-1",
        "canon-history-2",
        "canon-nations-1",
    ]
    assert len({f.id for f in facts}) == 3
    assert [c.id for c in cast] == ["vell"]
    assert [e.id for e in events] == ["lumen-festival"]


def test_folder_load_parses_tags_else_empty(tmp_path):
    folder = _make_folder(tmp_path, {"10-history.md": _HISTORY})
    facts, _, _ = canon_source.load_folder(folder)
    assert facts[0].tags == ["earth", "history"]  # from the - **Tags:** bullet
    # The tags bullet is consumed as tags, not folded into the prose text.
    assert facts[0].text == "Earth is distant history, spoken of fondly."
    assert facts[1].tags == []  # absent -> empty, never an error


def test_folder_sorts_by_numeric_prefix_not_string(tmp_path):
    # 2 < 20 < 100 as integers (string order would put 100 before 20).
    one_fact = "## Canon facts\n\n1. A fact.\n"
    folder = _make_folder(
        tmp_path,
        {
            "100-c.md": one_fact,
            "2-a.md": one_fact,
            "20-b.md": one_fact,
        },
    )
    facts, _, _ = canon_source.load_folder(folder)
    assert [f.id for f in facts] == ["canon-a-1", "canon-b-1", "canon-c-1"]


def test_series_bible_folder_concatenates_new_cornerstone_prose(tmp_path):
    folder = _make_folder(
        tmp_path,
        {"10-history.md": _HISTORY, "20-nations.md": _NATIONS, "95-events.md": _EVENTS},
    )
    bible = canon_source.load_series_bible_folder(folder)
    # New cornerstone prose is included automatically (no registration step).
    assert "## History of the long quiet" in bible
    assert "## The settled polities" in bible
    # History precedes nations (numeric-prefix order).
    assert bible.index("long quiet") < bible.index("settled polities")
    # Structured sections never leak into the cached core.
    assert "Lumen Festival" not in bible
    assert "Earth is distant history" not in bible


def test_duplicate_cast_slug_across_files_raises(tmp_path):
    folder = _make_folder(
        tmp_path,
        {"90-cast.md": _CAST, "91-more-cast.md": _CAST},  # both define Vell -> "vell"
    )
    with pytest.raises(ValueError, match="duplicate cast id 'vell'"):
        canon_source.load_folder(folder)


def test_duplicate_event_slug_across_files_raises(tmp_path):
    folder = _make_folder(
        tmp_path,
        {"95-events.md": _EVENTS, "96-more-events.md": _EVENTS},
    )
    with pytest.raises(ValueError, match="duplicate event id 'lumen-festival'"):
        canon_source.load_folder(folder)


def test_duplicate_file_stem_raises(tmp_path):
    # Two files reducing to the same stem would collide fact ids.
    folder = _make_folder(
        tmp_path,
        {"10-history.md": _HISTORY, "30-history.md": _NATIONS},
    )
    with pytest.raises(ValueError, match="duplicate canon file stem 'history'"):
        canon_source.load_folder(folder)


def test_file_stem_strips_numeric_prefix(tmp_path):
    from pathlib import Path

    assert canon_source._file_stem(Path("10-history.md")) == "history"
    assert canon_source._file_stem(Path("100-alien-races.md")) == "alien-races"
    assert canon_source._file_stem(Path("CANON.md")) == "canon"  # no prefix


# --- File-vs-folder selection (D1.2) ----------------------------------------
# seed/context auto-select the folder when it has cornerstone files, else fall
# back to the single CANON.md. A silent bug here would seed the wrong source.


def test_has_canon_folder_ignores_readme_and_missing(tmp_path):
    missing = tmp_path / "nope"
    assert canon_source.has_canon_folder(missing) is False

    only_readme = _make_folder(tmp_path, {"README.md": "# just the guide"}, name="r")
    assert canon_source.has_canon_folder(only_readme) is False

    populated = _make_folder(tmp_path, {"10-history.md": _HISTORY}, name="p")
    assert canon_source.has_canon_folder(populated) is True


def test_load_world_prefers_folder_when_populated_else_file(tmp_path):
    folder = _make_folder(tmp_path, {"10-history.md": _HISTORY}, name="canon")
    single = tmp_path / "CANON.md"
    single.write_text(_DOC)

    # Populated folder wins: ids are namespaced (folder scheme), not legacy canon-N.
    facts, _, _ = canon_source.load_world(folder, single)
    assert [f.id for f in facts] == ["canon-history-1", "canon-history-2"]

    # Empty/missing folder falls back to the single file (legacy canon-N ids).
    empty = _make_folder(tmp_path, {}, name="empty")
    facts, _, _ = canon_source.load_world(empty, single)
    assert [f.id for f in facts] == ["canon-1", "canon-2", "canon-3"]


def test_load_bible_prefers_folder_when_populated_else_file(tmp_path):
    folder = _make_folder(tmp_path, {"10-history.md": _HISTORY}, name="canon")
    single = tmp_path / "CANON.md"
    single.write_text(_DOC)

    assert "long quiet" in canon_source.load_bible(folder, single)  # folder prose

    empty = _make_folder(tmp_path, {}, name="empty")
    assert "## The station" in canon_source.load_bible(empty, single)  # file prose

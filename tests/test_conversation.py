"""Tests for the DB-free logic in the conversation orchestrator (src/writers/).

The creative steps need Claude + TTS, so they are exercised by `make
conversation`. Here we pin the brittle, pure bits a silent bug would corrupt: the
turn parser (it maps speaker-labelled dialogue to per-voice turns — get this wrong
and the wrong DJ speaks, or turns vanish) and the continuity verdict reader.
"""

from __future__ import annotations

from src.world.store import CastMember
from src.writers import conversation as convo

VELL = CastMember("vell", "Vell", "card text", "vell_night", [])
WREN = CastMember("wren", "Wren", "card text", "dj_two", [])
CARDS = [VELL, WREN]


def test_parse_turns_maps_names_to_voices_in_order():
    script = "Vell: Evening, you.\nWren: Morning, Vell.\nVell: Stay warm."
    turns = convo.parse_turns(script, CARDS)
    assert [t.speaker for t in turns] == ["Vell", "Wren", "Vell"]
    assert [t.voice for t in turns] == ["vell_night", "dj_two", "vell_night"]
    assert turns[0].text == "Evening, you."


def test_parse_turns_handles_bold_continuation_and_preamble():
    script = (
        "Here is the exchange:\n"
        "**Vell:** It's coming up on two,\n"
        "settlement time.\n"
        "**Wren:** The relay's warm.\n"
    )
    turns = convo.parse_turns(script, CARDS)
    assert len(turns) == 2
    # Stray preamble dropped; the wrapped line folded in; bold markers stripped.
    assert turns[0].speaker == "Vell"
    assert turns[0].text == "It's coming up on two, settlement time."
    assert turns[1].text == "The relay's warm."


def test_parse_turns_empty_without_recognised_labels():
    assert convo.parse_turns("Just prose, no speaker labels.", CARDS) == []


def test_is_ok_reads_the_continuity_verdict():
    assert convo._is_ok("OK")
    assert convo._is_ok("ok, consistent and in character")
    assert not convo._is_ok("ISSUES: Vell references a real brand")

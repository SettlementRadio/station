"""Tests for the DB-free logic in the conversation orchestrator (src/writers/).

The creative steps need Claude + TTS, so they are exercised by `make
conversation`. Here we pin the brittle, pure bits a silent bug would corrupt: the
turn parser (it maps speaker-labelled dialogue to per-voice turns — get this wrong
and the wrong DJ speaks, or turns vanish) and the continuity verdict reader.
"""

from __future__ import annotations

from datetime import datetime

from src.world.context import AssembledContext
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


# --- D9.0: the optional per-turn [emotion] tag -------------------------------


def test_parse_turns_reads_emotion_tags():
    script = (
        "Vell [somber]: The relay went quiet tonight.\n"
        "Wren: It does that.\n"
        "**Vell [wry]:** Not like this."
    )
    turns = convo.parse_turns(script, CARDS)
    assert [t.emotion for t in turns] == ["somber", None, "wry"]
    # The tag is consumed, never spoken.
    assert turns[0].text == "The relay went quiet tonight."
    assert turns[2].text == "Not like this."


def test_parse_turns_drops_unknown_emotion_tag():
    turns = convo.parse_turns("Vell [melodramatic]: Ahem.", CARDS)
    assert len(turns) == 1
    assert turns[0].emotion is None
    assert turns[0].text == "Ahem."


def test_render_turns_applies_turn_emotion_then_segment_default(monkeypatch):
    # D9.0/D9.5 — a tagged turn keeps its own emotion; an un-annotated turn
    # renders with the segment default (the daypart mood floor).
    seen: list[str | None] = []

    def fake_synthesize(text, *, voice, emotion=None, out_path):
        seen.append(emotion)
        return out_path

    monkeypatch.setattr(convo.tts, "synthesize", fake_synthesize)
    monkeypatch.setattr(convo.tts, "concat_audio", lambda parts, out: out)
    turns = [
        convo.Turn("Vell", "vell_night", "Quiet night.", emotion="somber"),
        convo.Turn("Wren", "dj_two", "It is."),
    ]
    convo._render_turns(turns, "emo-test", default_emotion="warm")
    assert seen == ["somber", "warm"]


def test_orchestrate_prompt_offers_the_emotion_vocabulary(monkeypatch):
    from src.providers import tts

    seen = _capture_system(monkeypatch)
    convo.orchestrate(_ctx(), "the beat", datetime(2026, 6, 30, 21, 0))
    for emotion in tts.EMOTIONS:
        assert emotion in seen["system"]


def test_is_ok_reads_the_continuity_verdict():
    assert convo._is_ok("OK")
    assert convo._is_ok("ok, consistent and in character")
    assert not convo._is_ok("ISSUES: Vell references a real brand")


# --- D5.2: the freshness steer reaches the talk prompts ---------------------


def _ctx() -> AssembledContext:
    return AssembledContext(bible="", dynamic="the relay is warm", speakers=CARDS)


def _capture_system(monkeypatch) -> dict:
    """Stub convo.llm.generate to record the system prompt it was called with."""
    seen: dict = {}

    def fake_generate(user, *, system, **kwargs):
        seen["system"] = system
        return "Vell: hi.\nWren: hi."

    monkeypatch.setattr(convo.llm, "generate", fake_generate)
    return seen


def test_showrunner_injects_recent_topics(monkeypatch):
    seen = _capture_system(monkeypatch)
    convo.showrunner(
        _ctx(), datetime(2026, 6, 30, 21, 0), recent_block="AVOID-TOPIC-ZZZ"
    )
    assert "AVOID-TOPIC-ZZZ" in seen["system"]


def test_orchestrate_injects_recent_openings(monkeypatch):
    seen = _capture_system(monkeypatch)
    convo.orchestrate(
        _ctx(),
        "the beat",
        datetime(2026, 6, 30, 21, 0),
        recent_openings="AVOID-OPEN-ZZZ",
    )
    assert "AVOID-OPEN-ZZZ" in seen["system"]


def test_talk_prompts_omit_freshness_when_empty(monkeypatch):
    # No recent block -> no dangling header; the prompt is the pre-D5 shape.
    seen = _capture_system(monkeypatch)
    convo.showrunner(_ctx(), datetime(2026, 6, 30, 21, 0), recent_block="")
    assert "Recently on air" not in seen["system"]

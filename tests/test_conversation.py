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


# --- R1.0: the ON THIS SHOW editorial block ----------------------------------


def _program(pid: str, name: str, brief: str = "", energy: str = ""):
    from src.world import programming

    return programming.Program(
        id=pid,
        name=name,
        hosts=("vell", "wren"),
        framing="solo",
        daypart="",
        clock=(),
        rotation=(),
        brief=brief,
        energy=energy,
    )


EXCHANGE = _program(
    "the_exchange",
    "The Exchange",
    brief="Trade and the markets: prices, cargoes, a deal gone sour.",
    energy="steady",
)
GALLERY = _program(
    "the_gallery",
    "The Gallery",
    brief="The arts in depth: a new work, a celebrated figure, an opening.",
    energy="bright",
)


def test_two_programs_briefs_land_in_their_showrunner_prompts(monkeypatch):
    # The R1.0 acceptance: different shows reach the beat-picker with DIFFERENT
    # editorial identities — the missing seam, closed.
    seen = _capture_system(monkeypatch)
    now = datetime(2026, 6, 30, 14, 0)
    convo.showrunner(_ctx(), now, program=EXCHANGE)
    assert "ON THIS SHOW — The Exchange:" in seen["system"]
    assert EXCHANGE.brief in seen["system"]
    assert "Energy: steady" in seen["system"]
    assert "belongs on THIS show" in seen["system"]  # the scoped fresh pick
    convo.showrunner(_ctx(), now, program=GALLERY)
    assert "ON THIS SHOW — The Gallery:" in seen["system"]
    assert GALLERY.brief in seen["system"]
    assert EXCHANGE.brief not in seen["system"]


def test_orchestrate_carries_the_show_block_too(monkeypatch):
    seen = _capture_system(monkeypatch)
    convo.orchestrate(_ctx(), "the beat", datetime(2026, 6, 30, 14, 0), program=GALLERY)
    assert "ON THIS SHOW — The Gallery:" in seen["system"]
    assert "Energy: bright" in seen["system"]


def test_no_brief_keeps_the_pre_r1_prompts_exactly(monkeypatch, tmp_path):
    # Back-compat: a briefless program (the default program, a pre-R1 grid)
    # contributes NO block and leaves the fresh-pick task unscoped — the prompt
    # keeps its pre-R1 shape, whether the program is passed or derived. (Since
    # R1.1 every shipped program HAS a brief, so the derived-path check uses a
    # missing grid file — the synthesised, briefless default program.)
    from src.config import settings
    from src.world import programming

    seen = _capture_system(monkeypatch)
    now = datetime(2026, 6, 30, 21, 0)
    briefless = _program("default", "Settlement Radio")
    convo.showrunner(_ctx(), now, program=briefless)
    assert "ON THIS SHOW" not in seen["system"]
    assert "belongs on THIS show" not in seen["system"]
    assert "Pick exactly ONE current event" in seen["system"]  # the unscoped task
    monkeypatch.setattr(settings, "programming_grid_path", tmp_path / "nope.yaml")
    programming.reload()
    try:
        convo.showrunner(_ctx(), now)  # derived program: the synthesised default
        assert "ON THIS SHOW" not in seen["system"]
    finally:
        programming.reload()
    convo.orchestrate(_ctx(), "the beat", now, program=briefless)
    assert "ON THIS SHOW" not in seen["system"]


# --- R1.2: the register pass — plain by day, lyric by night ------------------


def test_daytime_energy_bans_the_house_poetry(monkeypatch):
    seen = _capture_system(monkeypatch)
    convo.orchestrate(
        _ctx(), "the beat", datetime(2026, 6, 30, 14, 0), program=EXCHANGE
    )
    assert "BANNED here: the house-poetry register" in seen["system"]
    # The exemplar phrases from the shared vocabulary reach the prompt.
    assert convo.BANNED_ABSTRACTIONS[0] in seen["system"]


def test_calm_energy_keeps_the_night_register(monkeypatch):
    seen = _capture_system(monkeypatch)
    night = _program(
        "long_night", "The Long Night", brief="Warm night talk.", energy="calm"
    )
    convo.orchestrate(_ctx(), "the beat", datetime(2026, 6, 30, 23, 0), program=night)
    assert "lyric register is at home" in seen["system"]
    assert "BANNED here" not in seen["system"]


def test_no_energy_adds_no_register_block(monkeypatch):
    seen = _capture_system(monkeypatch)
    briefless = _program("default", "Settlement Radio")
    convo.orchestrate(
        _ctx(), "the beat", datetime(2026, 6, 30, 21, 0), program=briefless
    )
    assert "BANNED here" not in seen["system"]
    assert "lyric register is at home" not in seen["system"]


def test_orchestrate_invites_opinions_and_card_humour(monkeypatch):
    # The strengthened base delivery block applies to ALL talk, register aside.
    seen = _capture_system(monkeypatch)
    convo.orchestrate(_ctx(), "the beat", datetime(2026, 6, 30, 21, 0))
    assert "OPINIONS" in seen["system"]
    assert "`Humour:`" in seen["system"]


def test_showrunner_daytime_angle_is_a_concrete_stake(monkeypatch):
    seen = _capture_system(monkeypatch)
    now = datetime(2026, 6, 30, 14, 0)
    convo.showrunner(_ctx(), now, program=EXCHANGE)  # steady -> the concrete stake
    assert "not a meditation" in seen["system"]
    assert "can't stop thinking about" not in seen["system"]
    night = _program("long_night", "The Long Night", brief="Warm.", energy="calm")
    convo.showrunner(_ctx(), now, program=night)  # calm -> the original angle
    assert "can't stop thinking about" in seen["system"]
    assert "not a meditation" not in seen["system"]


# --- Field hosts (the audit fix): the dispatch directive ---------------------

SERA = CastMember("sera", "Sera", "card text", "sera_field", [], based="field")


def test_orchestrate_flags_field_hosts_as_dispatch(monkeypatch):
    seen = _capture_system(monkeypatch)
    ctx = AssembledContext(bible="", dynamic="", speakers=[VELL, SERA])
    convo.orchestrate(ctx, "the beat", datetime(2026, 6, 30, 21, 0))
    assert "DISPATCH" in seen["system"]
    assert "Sera is NOT in the studio" in seen["system"]
    assert "never claims to be in the studio" in seen["system"]


def test_orchestrate_omits_dispatch_when_all_in_studio(monkeypatch):
    seen = _capture_system(monkeypatch)
    convo.orchestrate(_ctx(), "the beat", datetime(2026, 6, 30, 21, 0))
    assert "DISPATCH" not in seen["system"]


def test_continuity_editor_checks_field_presence(monkeypatch):
    seen = _capture_system(monkeypatch)
    convo.continuity_check("Vell: hi.\nSera: hi.", _ctx())
    assert "Based: field" in seen["system"]


# --- R2.2: the per-program talk-item length scales the word budget -----------


def test_word_budget_scales_with_the_item_length():
    from src.config import settings

    low, high = settings.convo_words_low, settings.convo_words_high
    default = settings.segment_default_length_target_sec
    # None / the default length itself -> the dials untouched (pre-R2.2 parity).
    assert convo._word_budget(None) == (low, high)
    assert convo._word_budget(default) == (low, high)
    # A shorter item scales the budget proportionally (same words-per-second).
    lo, hi = convo._word_budget(default // 2)
    assert lo == round(low * (default // 2) / default)
    assert hi == round(high * (default // 2) / default)
    assert lo < low and hi < high


def test_orchestrate_word_budget_scales_in_the_prompt(monkeypatch):
    from src.config import settings

    seen = _capture_system(monkeypatch)
    half = settings.segment_default_length_target_sec // 2
    lo, hi = convo._word_budget(half)
    convo.orchestrate(
        _ctx(), "the beat", datetime(2026, 6, 30, 21, 0), length_target_sec=half
    )
    assert f"{lo}-{hi} words" in seen["system"]
    # The unscaled dial range must be gone from the prompt.
    full = f"{settings.convo_words_low}-{settings.convo_words_high} words"
    assert full not in seen["system"]

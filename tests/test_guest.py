"""Tests for D9.3 guest selection (src/writers/guest.py) + the guest turn path.

What's pinned: the sparse deterministic gate (same slot → same decision), the
figure-vs-invited choice (quotes present → a world-grounded soundbite), voice
resolution (a figure's own registered voice wins; unknown falls back to a
stable pool pick), and the parser/prompt honouring the extra label. The weave
itself is the orchestrator's job and is gated in test_compose_gate.
"""

from __future__ import annotations

from datetime import datetime

from src.config import settings
from src.providers import tts
from src.world.context import AssembledContext
from src.world.store import CastMember, Figure, Quote
from src.writers import conversation as convo
from src.writers import guest as guest_mod

VELL = CastMember("vell", "Vell", "card", "vell_night", [])
WREN = CastMember("wren", "Wren", "card", "dj_two", [])
NOW = datetime(2026, 7, 6, 21, 0)

FIGURE = Figure(
    id="fig-tessa",
    name="Tessa Aru",
    role="relay-keeper",
    card_text="Keeps the mid-route relay.",
)
QUOTE = Quote(
    id="q1",
    story_id="s1",
    figure_id="fig-tessa",
    text="The relay held. It always holds.",
    in_world_datetime=datetime(2626, 7, 5, 12, 0),
    stance="steady",
)


def _ctx(quotes=()) -> AssembledContext:
    return AssembledContext(
        bible="", dynamic="now", speakers=[VELL, WREN], quotes=list(quotes)
    )


def _always(monkeypatch):
    monkeypatch.setattr(settings, "convo_guest_enabled", True)
    monkeypatch.setattr(settings, "convo_guest_chance", 1.0)


def test_disabled_or_wrong_format_yields_no_guest(monkeypatch):
    _always(monkeypatch)
    assert guest_mod.maybe_guest(_ctx(), NOW, "news") is None
    monkeypatch.setattr(settings, "convo_guest_enabled", False)
    assert guest_mod.maybe_guest(_ctx(), NOW, "talk") is None


def test_zero_chance_yields_no_guest(monkeypatch):
    monkeypatch.setattr(settings, "convo_guest_enabled", True)
    monkeypatch.setattr(settings, "convo_guest_chance", 0.0)
    assert guest_mod.maybe_guest(_ctx(), NOW, "talk") is None


def test_program_chance_overrides_the_global(monkeypatch):
    # D12.4 — a show's own guest cadence beats the global rate, both ways:
    monkeypatch.setattr(settings, "convo_guest_enabled", True)
    # global says never, but an interview show forces a guest...
    monkeypatch.setattr(settings, "convo_guest_chance", 0.0)
    assert guest_mod.maybe_guest(_ctx(), NOW, "talk", chance=1.0) is not None
    # ...and global says always, but a solo-desk show suppresses it.
    monkeypatch.setattr(settings, "convo_guest_chance", 1.0)
    assert guest_mod.maybe_guest(_ctx(), NOW, "talk", chance=0.0) is None


def test_quotes_become_a_figure_soundbite(monkeypatch):
    _always(monkeypatch)
    g = guest_mod.maybe_guest(_ctx(quotes=[(QUOTE, FIGURE)]), NOW, "talk")
    assert g is not None and g.kind == "figure"
    assert g.label == "Tessa Aru"
    assert QUOTE.text in g.brief and FIGURE.role in g.brief
    assert g.voice in tts.known_voices()


def test_figure_registered_voice_wins(monkeypatch):
    _always(monkeypatch)
    fig = Figure(
        id="f2", name="Odo", role="captain", card_text="", voice_id="guest_two"
    )
    g = guest_mod.maybe_guest(_ctx(quotes=[(QUOTE, fig)]), NOW, "talk")
    assert g is not None and g.voice == "guest_two"


def test_figure_unknown_voice_falls_back_to_stable_pool(monkeypatch):
    _always(monkeypatch)
    fig = Figure(id="f3", name="Odo", role="captain", card_text="", voice_id="no_such")
    first = guest_mod.maybe_guest(_ctx(quotes=[(QUOTE, fig)]), NOW, "talk")
    again = guest_mod.maybe_guest(_ctx(quotes=[(QUOTE, fig)]), NOW, "talk")
    assert first is not None and first.voice in guest_mod._GUEST_VOICE_POOL
    assert again is not None and again.voice == first.voice  # stable per figure


def test_no_quotes_invites_a_generic_guest(monkeypatch):
    _always(monkeypatch)
    g = guest_mod.maybe_guest(_ctx(), NOW, "talk")
    assert g is not None and g.kind == "invited"
    assert g.label == guest_mod.INVITED_LABEL
    assert g.voice in guest_mod._GUEST_VOICE_POOL


def test_draw_is_deterministic_per_slot(monkeypatch):
    monkeypatch.setattr(settings, "convo_guest_enabled", True)
    monkeypatch.setattr(settings, "convo_guest_chance", 0.5)
    results = {guest_mod.maybe_guest(_ctx(), NOW, "talk") is None for _ in range(5)}
    assert len(results) == 1  # same slot, same decision, every time


# --- The guest label flows through the parser and the prompt ------------------


def test_parse_turns_maps_guest_label_to_guest_voice():
    from src.writers.guest import Guest

    g = Guest(label="Tessa Aru", voice="guest_one", kind="figure", brief="b")
    script = (
        "Vell: Here's what she told us.\n"
        "Tessa Aru [somber]: The relay held. It always holds.\n"
        "Wren: There you have it."
    )
    turns = convo.parse_turns(script, [VELL, WREN], guest=g)
    assert [t.voice for t in turns] == ["vell_night", "guest_one", "dj_two"]
    assert turns[1].emotion == "somber"  # guest turns carry emotion tags too


def test_orchestrate_prompt_carries_the_guest_brief(monkeypatch):
    from src.writers.guest import Guest

    seen: dict = {}

    def fake_generate(user, *, system, **kwargs):
        seen["system"] = system
        return "Vell: hi.\nWren: hi."

    monkeypatch.setattr(convo.llm, "generate", fake_generate)
    g = Guest(label="Tessa Aru", voice="guest_one", kind="figure", brief="THE-BRIEF")
    convo.orchestrate(_ctx(), "beat", NOW, guest=g)
    assert "THE-BRIEF" in seen["system"]
    assert "Tessa Aru:" in seen["system"]  # the label joins the FORMAT line

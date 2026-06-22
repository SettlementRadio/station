"""Tests for the C0 gate in compose_segment (src/writers/conversation.py).

The gate is the load-bearing C0 promise: a draft that fails safety OR continuity
is regenerated (bounded), and if it never clears, the slot drops to an evergreen
fallback — a flagged draft is NEVER rendered or returned. The LLM/TTS seams are
monkeypatched so we test the control flow, not the models.
"""

from __future__ import annotations

from datetime import datetime

from src.world.context import AssembledContext
from src.world.store import CastMember
from src.writers import conversation as convo
from src.writers.conversation import ContinuityResult

VELL = CastMember("vell", "Vell", "card", "vell_night", [])
WREN = CastMember("wren", "Wren", "card", "dj_two", [])
NOW = datetime(2026, 6, 22, 14, 0)
SCRIPT = "Vell: Evening, you.\nWren: Morning, Vell."


def _ctx() -> AssembledContext:
    return AssembledContext(cached_context="core", dynamic="now", speakers=[VELL, WREN])


def _patch_common(monkeypatch):
    """Stub the model/TTS-touching steps shared by every case."""
    monkeypatch.setattr(convo, "showrunner", lambda ctx, now, *, frame=None: "the beat")
    monkeypatch.setattr(
        convo, "_render_turns", lambda turns, seg_id: f"/x/{seg_id}.mp3"
    )


def test_clean_draft_passes_both_gates(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(convo, "orchestrate", lambda *a, **k: SCRIPT)
    monkeypatch.setattr(convo, "safety_check", lambda text: _ok_safety())
    monkeypatch.setattr(
        convo, "continuity_check", lambda s, c: ContinuityResult(True, "sonnet", "OK")
    )

    seg = convo.compose_segment(_ctx(), NOW, seg_id="talk-1")
    assert seg.format == "talk"
    assert seg.meta["continuity_ok"] is True
    assert seg.meta.get("fallback") is None
    assert seg.audio_path == "/x/talk-1.mp3"


def test_continuity_flag_regenerates_with_note_then_falls_back(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(convo, "safety_check", lambda text: _ok_safety())
    # Continuity always flags: the gate exhausts its attempts and falls back.
    monkeypatch.setattr(
        convo,
        "continuity_check",
        lambda s, c: ContinuityResult(False, "opus", "ISSUES: time collision"),
    )
    seen_notes: list[str | None] = []

    def _orchestrate(
        ctx, beat, now, *, frame=None, extra_directive=None, revision_note=None
    ):
        seen_notes.append(revision_note)
        return SCRIPT

    monkeypatch.setattr(convo, "orchestrate", _orchestrate)
    monkeypatch.setattr(convo.settings, "convo_continuity_max_attempts", 2)

    fallback = object()
    monkeypatch.setattr(convo.evergreen, "evergreen_segment", lambda *a, **k: fallback)

    result = convo.compose_segment(_ctx(), NOW, seg_id="talk-2")
    assert result is fallback  # never returns the flagged draft
    # Two attempts: the first blind, the second guided by the editor's note.
    assert seen_notes == [None, "ISSUES: time collision"]


def test_safety_flag_regenerates_fresh_then_succeeds(monkeypatch):
    _patch_common(monkeypatch)
    # First draft fails safety, second passes; continuity then OK.
    safety_verdicts = iter([_flag_safety(), _ok_safety()])
    monkeypatch.setattr(convo, "safety_check", lambda text: next(safety_verdicts))
    monkeypatch.setattr(
        convo, "continuity_check", lambda s, c: ContinuityResult(True, "sonnet", "OK")
    )
    notes: list[str | None] = []

    def _orchestrate(
        ctx, beat, now, *, frame=None, extra_directive=None, revision_note=None
    ):
        notes.append(revision_note)
        return SCRIPT

    monkeypatch.setattr(convo, "orchestrate", _orchestrate)
    monkeypatch.setattr(convo.settings, "convo_continuity_max_attempts", 2)

    seg = convo.compose_segment(_ctx(), NOW, seg_id="talk-3")
    assert seg.meta["continuity_ok"] is True
    assert seg.meta["attempts"] == 2
    # A safety flag re-rolls fresh (no editor note fed back).
    assert notes == [None, None]


# --- tiny verdict helpers (avoid importing the SafetyResult shape everywhere) ---


def _ok_safety():
    from src.safety import SafetyResult

    return SafetyResult(ok=True, reason="OK", stage="llm")


def _flag_safety():
    from src.safety import SafetyResult

    return SafetyResult(ok=False, reason="unsafe", stage="llm")

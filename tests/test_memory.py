"""Tests for D9.4 DJ memory (src/writers/memory.py + the room injection).

What's pinned: the pure ranking/rendering (persona-weighted pick, past-tense
clock framing, the resolved/unfolding label), the bounded degrade paths (off,
empty log, DB failure → ""), and the injection contracts — the block reaches
the orchestrator's per-call prompt AND the continuity editor, never the cached
core. The live read (`store.remembered_stories`) is SQL-behind-the-seam; here
it is stubbed.
"""

from __future__ import annotations

from datetime import datetime

from src.config import settings
from src.world.context import AssembledContext
from src.world.store import ARC_DEVELOPING, ARC_PAST, CastMember, Story
from src.writers import conversation as convo
from src.writers import memory as memory_mod

VELL = CastMember("vell", "Vell", "card", "vell_night", ["night", "relay"])
KAEL = CastMember("kael", "Kael", "card", "kael_sports", ["sports"])
NOW = datetime(2026, 7, 6, 21, 0)  # in-world 2626-07-06

RELAY = Story(
    id="s-relay",
    title="The mid-route relay outage",
    summary="Three nights dark, then the thread held.",
    arc_stage=ARC_PAST,
    tags=["relay", "infrastructure"],
)
MATCH = Story(
    id="s-match",
    title="The circuit finals",
    summary="Meridian took the pennant.",
    arc_stage=ARC_DEVELOPING,
    tags=["sports"],
)

CANDIDATES = [
    (RELAY, datetime(2626, 7, 5, 23, 0)),  # yesterday, resolved
    (MATCH, datetime(2626, 6, 30, 20, 0)),  # last week, unfolding
]


def _stub_read(monkeypatch, candidates):
    monkeypatch.setattr(settings, "convo_memory_enabled", True)
    monkeypatch.setattr(memory_mod.store, "connect", lambda: _FakeConn())
    monkeypatch.setattr(
        memory_mod.store, "remembered_stories", lambda conn, **kw: candidates
    )


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_memory_section_frames_past_and_state(monkeypatch):
    _stub_read(monkeypatch, CANDIDATES)
    block = memory_mod.memory_section([VELL], NOW)
    assert "What Vell remembers:" in block
    assert "yesterday" in block and "resolved" in block  # clock-framed, arc-labelled
    assert "still unfolding" in block
    assert "never re-announce" in block  # the in-character steer rides along


def test_memory_is_persona_weighted_per_host(monkeypatch):
    _stub_read(monkeypatch, CANDIDATES)
    monkeypatch.setattr(settings, "convo_memory_per_host", 1)
    block = memory_mod.memory_section([VELL, KAEL], NOW)
    vell_part, kael_part = block.split("What Kael remembers:")
    assert RELAY.title in vell_part and MATCH.title not in vell_part
    assert MATCH.title in kael_part  # the sports story sticks with the sports host


def test_memory_lines_are_clipped_handles():
    long = Story(
        id="s-long",
        title="The long one",
        summary="First sentence of the memory. " + "Detail that follows. " * 30,
        arc_stage=ARC_PAST,
        tags=[],
    )
    line = memory_mod._line(long, datetime(2626, 7, 5, 12, 0), NOW)
    assert "First sentence of the memory." in line
    assert "Detail that follows" not in line  # a handle, not a re-report


def test_memory_degrades_to_empty(monkeypatch):
    monkeypatch.setattr(settings, "convo_memory_enabled", False)
    assert memory_mod.memory_section([VELL], NOW) == ""

    monkeypatch.setattr(settings, "convo_memory_enabled", True)
    _stub_read(monkeypatch, [])
    assert memory_mod.memory_section([VELL], NOW) == ""


def test_memory_db_failure_never_kills_a_slot(monkeypatch):
    monkeypatch.setattr(settings, "convo_memory_enabled", True)

    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(memory_mod.store, "connect", _boom)
    assert memory_mod.memory_section([VELL], NOW) == ""


# --- Injection contracts ------------------------------------------------------


def _ctx() -> AssembledContext:
    return AssembledContext(bible="", dynamic="now", speakers=[VELL, KAEL])


def _capture(monkeypatch) -> dict:
    seen: dict = {}

    def fake_generate(user, *, system, **kwargs):
        seen["system"] = system
        # CO2 — the stable core arrives as bible + cards now (or the legacy single
        # cached_context); fold every shape in so "memory stays out of the cache"
        # is actually asserted against the cached blocks.
        seen["cached"] = (
            (kwargs.get("cached_context") or "")
            + (kwargs.get("bible") or "")
            + (kwargs.get("cards") or "")
        )
        return "OK"

    monkeypatch.setattr(convo.llm, "generate", fake_generate)
    return seen


def test_orchestrate_carries_memory_in_the_per_call_prompt(monkeypatch):
    seen = _capture(monkeypatch)
    convo.orchestrate(_ctx(), "beat", NOW, memory="MEM-MARKER\n\n")
    assert "MEM-MARKER" in seen["system"]
    assert "MEM-MARKER" not in (seen["cached"] or "")  # the cache lever holds


def test_continuity_editor_sees_the_memory(monkeypatch):
    seen = _capture(monkeypatch)
    convo.continuity_check("Vell: hi.", _ctx(), memory="MEM-MARKER")
    assert "MEM-MARKER" in seen["system"]
    assert "must not contradict" in seen["system"]

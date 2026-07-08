"""CO1 — the equivalence guardrail for the CO2 cache split (providers/llm.py).

Prompt caching must be transparent to generation: `cache_control` breakpoints
change what is BILLED, never what the model SEES. These tests capture the exact
request the seam sends (a fake SDK client records `messages.stream` kwargs) and
pin the model-visible bytes. The invariant, stated once and asserted throughout:

    "".join(block["text"] for block in kwargs["system"]) + <user prompt>

must be byte-identical before and after the CO2 bible/cards split — only the
NUMBER and PLACEMENT of `cache_control` markers may differ. If the split alters
the model input by even one byte (e.g. the cards block loses its leading blank
line), these tests go red. See docs/CACHE_OPTIMIZATION_TASKS.md (CO1).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from src.providers import llm
from src.world import context


class _FakeStream:
    """Stands in for the SDK's message stream context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(("OK",))

    def get_final_message(self):
        return SimpleNamespace(usage=None)  # zeros in the usage telemetry


class _FakeClient:
    """Records every `messages.stream(**kwargs)` request the seam builds."""

    def __init__(self):
        self.requests: list[dict] = []
        self.messages = SimpleNamespace(stream=self._stream)

    def with_options(self, **kwargs):
        return self

    def _stream(self, **kwargs):
        self.requests.append(kwargs)
        return _FakeStream()


@pytest.fixture()
def capture(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(llm, "_get_client", lambda: fake)
    return fake


def test_co1_system_blocks_concatenate_with_no_separator(capture):
    # The load-bearing byte-level property: the API concatenates system text
    # blocks with NOTHING between them. So a CO2 split must carry its own
    # separators inside the block text (e.g. the cards block starts "\n\n").
    llm.generate("p", system="SMALL PER-CALL PART", cached_context="STABLE CORE")
    req = capture.requests[-1]
    joined = "".join(b["text"] for b in req["system"])
    assert joined == "STABLE CORESMALL PER-CALL PART"  # golden: no inserted bytes


def test_co1_model_visible_bytes_pinned_per_format(co1_world, capture):
    # End-to-end (context -> seam), per format speaker set: what the model sees
    # is exactly cached_context + the caller's per-call system, then the user
    # prompt — byte-for-byte, regardless of how the cache blocks are cut.
    for fmt, ids in co1_world.speaker_sets.items():
        ctx = context.assemble(co1_world.now, speakers=ids)
        system = f"Per-call instructions for {fmt}.\n\nNow:\n{ctx.dynamic}"
        prompt = f"Write the {fmt} segment now."

        llm.generate(prompt, system=system, cached_context=ctx.cached_context)

        req = capture.requests[-1]
        joined = "".join(b["text"] for b in req["system"])
        assert joined == ctx.cached_context + system, fmt
        assert req["messages"] == [{"role": "user", "content": prompt}], fmt


def test_co1_cache_markers_stay_on_stable_prefix_only(capture):
    # Marker-placement invariant (survives the split): every system block is a
    # text block; the stable prefix carries the breakpoint(s) — within the API's
    # 4-breakpoint limit — and the volatile per-call system block is NEVER
    # cached (a marker there would key the cache to per-call bytes).
    llm.generate("p", system="volatile", cached_context="stable")
    blocks = capture.requests[-1]["system"]

    assert all(b["type"] == "text" for b in blocks)
    marked = [b for b in blocks if "cache_control" in b]
    assert 1 <= len(marked) <= 4
    assert "cache_control" not in blocks[-1]  # the per-call system block


def test_co1_no_cached_context_means_plain_system(capture):
    # Without a stable core there is nothing to cache: one unmarked system
    # block, same bytes.
    llm.generate("p", system="only the per-call part")
    blocks = capture.requests[-1]["system"]
    assert [b["text"] for b in blocks] == ["only the per-call part"]
    assert all("cache_control" not in b for b in blocks)

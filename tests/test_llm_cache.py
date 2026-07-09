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


# --- CO2: the split is transparent — two blocks == one, byte-for-byte ---------


def test_co2_bible_plus_cards_equals_single_cached_context(co1_world, capture):
    # The core equivalence claim: for every speaker set, sending the stable core
    # as two blocks (bible + cards) reaches the model byte-identical to sending it
    # as the one `cached_context` it replaces. Same tokens, same order.
    for fmt, ids in co1_world.speaker_sets.items():
        ctx = context.assemble(co1_world.now, speakers=ids)

        llm.generate("p", system="S", bible=ctx.bible, cards=ctx.cards_block)
        two_block = "".join(b["text"] for b in capture.requests[-1]["system"])

        llm.generate("p", system="S", cached_context=ctx.cached_context)
        one_block = "".join(b["text"] for b in capture.requests[-1]["system"])

        assert two_block == one_block == ctx.cached_context + "S", fmt


def test_co2_bible_is_its_own_block_before_the_cards(co1_world, capture):
    # The bible caches as a SEPARATE, shared block ahead of the cards — that is
    # what lets every speaker set (and the world tick) read one bible entry.
    ctx = context.assemble(co1_world.now, speakers=["vell", "wren"])
    llm.generate("p", system="S", bible=ctx.bible, cards=ctx.cards_block)
    blocks = capture.requests[-1]["system"]

    assert blocks[0]["text"] == ctx.bible  # the shared block, raw bible
    assert "cache_control" in blocks[0]  # cached
    assert blocks[1]["text"] == ctx.cards_block  # the per-speaker-set block
    assert "cache_control" in blocks[1]  # cached
    assert blocks[2]["text"] == "S"  # the volatile per-call part
    assert "cache_control" not in blocks[2]  # never cached


def test_co2_bible_block_is_identical_across_speaker_sets(co1_world, capture):
    # The whole point: the bible block bytes do NOT depend on who's speaking, so
    # talk / news / music / commercial / the world tick all share one cache entry.
    bibles = set()
    for ids in co1_world.speaker_sets.values():
        ctx = context.assemble(co1_world.now, speakers=ids)
        llm.generate("p", system="S", bible=ctx.bible, cards=ctx.cards_block)
        bibles.add(capture.requests[-1]["system"][0]["text"])
    assert len(bibles) == 1  # one shared bible block across every speaker set


# --- CO3: the 1h TTL rides on the bible block only ----------------------------


def test_co3_bible_block_carries_the_configured_ttl(capture, monkeypatch):
    # The long TTL keeps the static bible warm across top-ups; the cards (which
    # vary per speaker set) stay on the default 5-min ephemeral.
    monkeypatch.setattr(llm.settings, "llm_cache_bible_ttl", "1h")
    llm.generate("p", system="S", bible="BIBLE", cards="\n\nCARDS")
    bible_blk, cards_blk, sys_blk = capture.requests[-1]["system"]

    assert bible_blk["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert cards_blk["cache_control"] == {"type": "ephemeral"}  # default 5-min
    assert "cache_control" not in sys_blk  # the volatile per-call part is never cached


def test_co3_default_ttl_leaves_the_bible_on_plain_ephemeral(capture, monkeypatch):
    # "5m" (or "ephemeral") reverts the bible to the default TTL — no ttl field, so
    # it matches the world tick / any caller that didn't opt into the long TTL.
    monkeypatch.setattr(llm.settings, "llm_cache_bible_ttl", "5m")
    llm.generate("p", system="S", bible="BIBLE", cards="\n\nCARDS")
    bible_blk = capture.requests[-1]["system"][0]
    assert bible_blk["cache_control"] == {"type": "ephemeral"}


def test_co3_single_cached_context_stays_on_default_ttl(capture, monkeypatch):
    # The long TTL applies to the dedicated bible block only. The back-compat
    # single-`cached_context` block (bible+cards combined) varies per speaker set,
    # so it must NOT inherit the 1h TTL.
    monkeypatch.setattr(llm.settings, "llm_cache_bible_ttl", "1h")
    llm.generate("p", system="S", cached_context="BIBLE\n\nCARDS")
    blk = capture.requests[-1]["system"][0]
    assert blk["cache_control"] == {"type": "ephemeral"}

"""Tests for the pure logic in context assembly (src/world/context.py).

`assemble()` itself needs the DB, so it is exercised by `make context`. Here we
test the brittle, DB-free bits a silent bug would hurt: the topic→tags tokenizer
that drives canon retrieval, the dynamic-block renderer (the time-aware slice the
writer actually sees), and the D2.4 hybrid `_select_canon` (semantic + tag union,
with a clean fallback) — with the embedding provider and the store mocked, so no
model or DB is touched.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src.providers import embeddings
from src.world import clock, context, store
from src.world import events as events_mod
from src.world.store import CanonFact, Event, Figure, Quote


def test_topic_tags_tokenizes_freetext():
    assert context._topic_tags("Lights & Music!") == ["lights", "music"]
    assert context._topic_tags("festival") == ["festival"]
    assert context._topic_tags("") == []


def test_render_dynamic_surfaces_relative_phrase_and_facts():
    now = datetime(2026, 6, 19, 23, 0)
    # Five days out in-world -> the renderer should speak "in five days".
    event_dt = clock.to_inworld(now) + timedelta(days=5)
    event = events_mod.progressed(
        Event("lumen", "Lumen Festival", "Lamps are lit.", event_dt, "upcoming", []),
        now,
    )
    facts = [CanonFact("canon-1", "Radio connects the worlds.", [])]

    out = context._render_dynamic([event], facts, [], now)

    assert "Lumen Festival" in out
    assert "in five days" in out
    assert "(upcoming)" in out
    assert "Radio connects the worlds." in out


def test_assemble_fails_loud_on_unknown_cast_id(monkeypatch):
    # D9.2 — the roster is table-driven, so a stale id (a removed DJ still named
    # by the grid/config) must raise, never silently drop the persona.
    import pytest

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(context.canon_source, "load_bible", lambda *a: "bible")
    monkeypatch.setattr(context.store, "connect", lambda: _Conn())
    monkeypatch.setattr(context.store, "get_cast_member", lambda conn, sid: None)

    with pytest.raises(ValueError, match="unknown speaker cast id 'ghost'"):
        context.assemble(datetime(2026, 7, 6, 21, 0), speakers=["ghost"])


def test_render_dynamic_surfaces_attributed_quote():
    # D10.2 — a quote with its figure becomes a "what people are saying" line, framed.
    now = datetime(2026, 6, 19, 23, 0)
    said_dt = clock.to_inworld(now) - timedelta(days=1)  # -> "yesterday"
    quote = Quote(
        id="q1",
        story_id="s1",
        figure_id="f1",
        text="The relay held.",
        in_world_datetime=said_dt,
    )
    figure = Figure(id="f1", name="Mira Voss", role="relay-keeper", card_text="Steady.")

    out = context._render_dynamic([], [], [(quote, figure)], now)

    assert "Mira Voss (relay-keeper)" in out
    assert "yesterday" in out
    assert "The relay held." in out
    assert "What people are saying" in out


def test_render_dynamic_is_empty_with_no_world():
    assert context._render_dynamic([], [], [], datetime(2026, 6, 19)) == ""


# --- _select_canon: the D2.4 hybrid (semantic + tag), DB/model mocked -------


def test_select_canon_no_topic_returns_all(monkeypatch):
    sentinel = [CanonFact("all-1", "x", [])]
    monkeypatch.setattr(store, "all_canon", lambda conn: sentinel)
    assert context._select_canon(object(), None) is sentinel


def test_select_canon_hybrid_unions_semantic_then_tag(monkeypatch):
    # semantic returns 2 ranked ids; the tag path adds one the vectors missed and
    # repeats one already found -> union is semantic-first, then the tag-only extra.
    monkeypatch.setattr(
        embeddings,
        "retrieve",
        lambda topic, *, k, corpus: [
            embeddings.Retrieved("c-sem1", "", 0.9),
            embeddings.Retrieved("c-sem2", "", 0.5),
        ],
    )
    monkeypatch.setattr(
        store,
        "canon_by_tags",
        lambda conn, tags: [
            CanonFact("c-tag1", "", ["x"]),
            CanonFact("c-sem2", "", []),
        ],
    )
    captured: dict[str, list[str]] = {}

    def fake_by_ids(conn, ids):
        captured["ids"] = list(ids)
        return [CanonFact(i, "", []) for i in ids]

    monkeypatch.setattr(store, "canon_by_ids", fake_by_ids)

    out = context._select_canon(object(), "loneliness")

    # off-tag-safe: semantic hits lead (meaning-rank preserved), tag-only de-duped in.
    assert captured["ids"] == ["c-sem1", "c-sem2", "c-tag1"]
    assert [f.id for f in out] == ["c-sem1", "c-sem2", "c-tag1"]


def test_select_canon_falls_back_to_all_when_no_hits(monkeypatch):
    # vectors unavailable (retrieve -> []) AND no tag match -> whole canon, no error.
    monkeypatch.setattr(embeddings, "retrieve", lambda topic, *, k, corpus: [])
    monkeypatch.setattr(store, "canon_by_tags", lambda conn, tags: [])
    sentinel = [CanonFact("all-1", "x", [])]
    monkeypatch.setattr(store, "all_canon", lambda conn: sentinel)

    assert context._select_canon(object(), "loneliness") is sentinel


# --- CO1: model-input equivalence goldens (fixed clock + fixture world) ------
# The CO2 cache split may change how the stable core is CACHED, never what the
# model SEES. These goldens pin the exact bytes `assemble` produces for each
# format's speaker set today (pre-split), on the `co1_world` fixture (conftest).
# After CO2, the concatenation of whatever parts the context exposes must still
# equal these bytes — see tests/test_llm_cache.py for the seam-side half.


def _golden_core(world, ids: list[str]) -> str:
    # The pre-split rendering shape, restated LITERALLY (bible, then one
    # "## Character —" section per speaker, joined by blank lines). This is the
    # golden: if _render_core (or its CO2 successor) changes a byte, this fails.
    parts = [world.bible] + [
        f"## Character — {world.cast[i].name}\n\n{world.cast[i].card_text}" for i in ids
    ]
    return "\n\n".join(parts)


def test_co1_cached_core_bytes_pinned_per_format(co1_world):
    for fmt, ids in co1_world.speaker_sets.items():
        ctx = context.assemble(co1_world.now, speakers=ids)
        assert ctx.cached_context == _golden_core(co1_world, ids), fmt


def test_co1_dynamic_bytes_pinned(co1_world):
    # The dynamic slice rides AFTER the cache breakpoint (in the per-call
    # system), so CO2 must leave it untouched too — pin it byte-for-byte.
    ctx = context.assemble(co1_world.now, speakers=["vell"])
    assert ctx.dynamic == (
        "Current events (reference naturally, don't recite):\n"
        "- Lumen Festival — in five days (upcoming): Lamps are lit.\n\n"
        "World facts you simply know:\n"
        "- Radio connects the settlements."
    )

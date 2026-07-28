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


# --- R4.3: a vertical prefers its own domain's beats ------------------------


def _ev(eid: str, story_id: str, title: str) -> Event:
    return Event(
        id=eid,
        title=title,
        body=f"body of {eid}",
        in_world_datetime=datetime(2626, 6, 24, 9, 0),
        status="past",
        story_id=story_id,
        beat_kind="development",
    )


def test_split_by_domain_partitions_in_domain_first():
    fin = _ev("f1", "fin-story", "A convoy runs late")
    hea = _ev("h1", "health-story", "A ward fills up")
    tags = {"fin-story": ["finance", "large"], "health-story": ["health"]}

    preferred, rest = context._split_by_domain([hea, fin], ["finance"], tags)
    assert [e.id for e in preferred] == ["f1"]
    assert [e.id for e in rest] == ["h1"]


def test_split_by_domain_no_domain_or_no_match_keeps_full_mix():
    fin = _ev("f1", "fin-story", "A convoy runs late")
    tags = {"fin-story": ["finance"]}
    # No program domain -> the whole list stays as the undifferentiated mix.
    assert context._split_by_domain([fin], None, {}) == ([], [fin])
    # A domain with no matching story yet -> full mix, not silence.
    assert context._split_by_domain([fin], ["sports"], tags) == ([], [fin])


def test_render_dynamic_leads_with_the_shows_own_subject():
    now = datetime(2026, 6, 24, 12, 0)
    fin = events_mod.progressed(_ev("f1", "fin-story", "A convoy runs late"), now)
    hea = events_mod.progressed(_ev("h1", "health-story", "A ward fills up"), now)

    out = context._render_dynamic([hea], [], [], now, preferred_events=[fin])

    assert "On THIS show's subject" in out
    assert "Also happening elsewhere" in out
    # The show's own beat leads; the background beat follows it.
    assert out.index("A convoy runs late") < out.index("A ward fills up")


def test_assemble_prefers_the_program_domain(monkeypatch):
    from src.world.store import CastMember

    now = datetime(2026, 6, 24, 12, 0)
    fin = _ev("f1", "fin-story", "A convoy runs late")
    hea = _ev("h1", "health-story", "A ward fills up")
    tags = {"fin-story": ["finance"], "health-story": ["health"]}

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(context.canon_source, "load_bible", lambda *a: "bible")
    monkeypatch.setattr(context.store, "connect", lambda: _Conn())
    monkeypatch.setattr(
        context.store,
        "get_cast_member",
        lambda conn, sid: CastMember(sid, sid.title(), "host", "voice-a"),
    )
    monkeypatch.setattr(context.store, "events_in_range", lambda conn, a, b: [hea, fin])
    monkeypatch.setattr(context.store, "all_canon", lambda conn: [])
    monkeypatch.setattr(
        context.store, "attributed_quotes_near", lambda conn, a, b, limit=0: []
    )
    monkeypatch.setattr(context.store, "story_tags_for", lambda conn, ids: tags)
    monkeypatch.setattr(context.store, "story_arcs_for", lambda conn, ids: {})
    monkeypatch.setattr(context.store, "items_in_range", lambda conn, a, b, **kw: [])

    # The finance vertical leads with its own story; the health beat is background.
    fin_ctx = context.assemble(now, speakers="vell", domains=["finance"])
    assert fin_ctx.events[0].story_id == "fin-story"
    assert "On THIS show's subject" in fin_ctx.dynamic
    assert fin_ctx.dynamic.index("A convoy runs late") < fin_ctx.dynamic.index(
        "A ward fills up"
    )

    # A general show (no domains) keeps the undifferentiated mix — no prefer header.
    gen_ctx = context.assemble(now, speakers="vell")
    assert "On THIS show's subject" not in gen_ctx.dynamic
    assert "Current events" in gen_ctx.dynamic


# --- Q2.0: rank_events — the bounded, ranked event block --------------------
#
# The baseline shipped 74-82 flat event bodies per call. These pin the four scoring
# factors (recency / arc stage / domain match / breaking-ness), the reserved domain
# sub-quota, and the fact that ranking never LOSES an event — it only orders it, so
# the caller can slice a bodied head and a title-only tail out of the same list.

_RANK_NOW = datetime(2026, 6, 24, 12, 0)


def _rev(
    eid: str,
    *,
    hours: float = 0.0,
    story_id: str | None = None,
    beat_kind: str | None = None,
) -> Event:
    """An event `hours` from the in-world now (negative = in the past)."""
    return Event(
        id=eid,
        title=f"title {eid}",
        body=f"body of {eid}",
        in_world_datetime=clock.to_inworld(_RANK_NOW) + timedelta(hours=hours),
        status="past",
        story_id=story_id,
        beat_kind=beat_kind,
    )


def test_rank_events_prefers_the_recent_over_the_distant():
    fresh, stale = _rev("fresh", hours=-2), _rev("stale", hours=-24 * 10)
    ranked = context.rank_events([stale, fresh], _RANK_NOW)
    assert [e.id for e in ranked] == ["fresh", "stale"]


def test_rank_events_discounts_the_future_against_the_past():
    # Same distance either side of now: what happened outranks what will.
    past, future = _rev("past", hours=-30), _rev("future", hours=30)
    ranked = context.rank_events([future, past], _RANK_NOW)
    assert [e.id for e in ranked] == ["past", "future"]


def test_rank_events_prefers_a_live_arc_over_a_resolved_one():
    live = _rev("live", hours=-6, story_id="s-live")
    done = _rev("done", hours=-6, story_id="s-done")
    arcs = {"s-live": store.ARC_HAPPENING, "s-done": store.ARC_PAST}
    ranked = context.rank_events([done, live], _RANK_NOW, story_arcs=arcs)
    assert [e.id for e in ranked] == ["live", "done"]


def test_rank_events_prefers_a_breaking_beat_kind_at_equal_age():
    ann = _rev("ann", hours=-6, beat_kind="announcement")
    rum = _rev("rum", hours=-6, beat_kind="rumour")
    ranked = context.rank_events([rum, ann], _RANK_NOW)
    assert [e.id for e in ranked] == ["ann", "rum"]


def test_rank_events_lifts_the_programme_own_domain():
    # The in-domain beat is OLDER, and still leads for the finance vertical — that is
    # what stops a louder story elsewhere taking a vertical's own field off its desk.
    mine = _rev("mine", hours=-20, story_id="fin")
    loud = _rev("loud", hours=-6, story_id="hea")
    tags = {"fin": ["finance"], "hea": ["health"]}
    ranked = context.rank_events([loud, mine], _RANK_NOW, ["finance"], story_tags=tags)
    assert [e.id for e in ranked] == ["mine", "loud"]
    # …and for a general show (no domains) the plain recency order returns.
    assert [e.id for e in context.rank_events([mine, loud], _RANK_NOW)] == [
        "loud",
        "mine",
    ]


def test_rank_events_reserves_a_domain_subquota_inside_the_bodied_head():
    from src.config import settings

    head, floor = settings.context_events_max, settings.context_events_domain_min
    # A wall of fresh out-of-field beats, and a handful of stale in-field ones that
    # score far below them even with the domain boost.
    loud = [_rev(f"loud{i}", hours=-i, story_id="hea") for i in range(head + 10)]
    mine = [_rev(f"mine{i}", hours=-24 * 12, story_id="fin") for i in range(floor + 2)]
    tags = {"fin": ["finance"], "hea": ["health"]}

    ranked = context.rank_events(loud + mine, _RANK_NOW, ["finance"], story_tags=tags)
    in_head = [e.id for e in ranked[:head] if e.id.startswith("mine")]
    assert len(in_head) == floor  # the floor, and not one more than the floor
    assert len(ranked) == len(loud) + len(mine)  # nothing was dropped
    # The displaced out-of-field beats fall to just behind the head, not off the end.
    assert ranked[head].id.startswith("loud")


def test_rank_events_keeps_every_event_and_is_deterministic():
    events = [_rev(f"e{i}", hours=-i * 3) for i in range(30)]
    first = context.rank_events(events, _RANK_NOW)
    second = context.rank_events(list(reversed(events)), _RANK_NOW)
    assert [e.id for e in first] == [e.id for e in second]
    assert sorted(e.id for e in first) == sorted(e.id for e in events)


def test_render_dynamic_tail_is_titles_only():
    now = _RANK_NOW
    bodied = events_mod.progressed(_rev("b1", hours=-2), now)
    tail = events_mod.progressed(_rev("t1", hours=-48), now)
    out = context._render_dynamic([bodied], [], [], now, tail_events=[tail])
    assert "body of b1" in out
    assert "title t1" in out
    assert "body of t1" not in out  # the whole point: a title costs ~60 chars


def test_assemble_caps_the_bodied_events_and_keeps_a_titles_tail(monkeypatch):
    from src.config import settings
    from src.world.store import CastMember

    head, tail_n = settings.context_events_max, settings.context_events_tail
    events = [_rev(f"e{i}", hours=-i) for i in range(head + tail_n + 20)]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(context.canon_source, "load_bible", lambda *a: "bible")
    monkeypatch.setattr(context.store, "connect", lambda: _Conn())
    monkeypatch.setattr(
        context.store,
        "get_cast_member",
        lambda conn, sid: CastMember(sid, sid.title(), "host", "voice-a"),
    )
    monkeypatch.setattr(context.store, "events_in_range", lambda conn, a, b: events)
    monkeypatch.setattr(context.store, "all_canon", lambda conn: [])
    monkeypatch.setattr(
        context.store, "attributed_quotes_near", lambda conn, a, b, limit=0: []
    )
    monkeypatch.setattr(context.store, "story_tags_for", lambda conn, ids: {})
    monkeypatch.setattr(context.store, "story_arcs_for", lambda conn, ids: {})
    monkeypatch.setattr(context.store, "items_in_range", lambda conn, a, b, **kw: [])

    ctx = context.assemble(_RANK_NOW, speakers="vell")
    assert len(ctx.events) == head
    assert len(ctx.tail_events) == tail_n
    # The 20 beyond head+tail are in the window but reach the prompt not at all.
    assert ctx.dynamic.count("body of ") == head
    assert "Also running, headlines only" in ctx.dynamic


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


def test_select_canon_bounds_the_union_to_top_k(monkeypatch):
    """Q2.1 — a programme BRIEF as topic tag-matches most of the canon; bound it.

    `_topic_tags` tokenises three sentences into dozens of ordinary words, so without
    the bound the "hybrid" union was 80 facts uncached on every live call — the exact
    cost the RAG was supposed to remove.
    """
    from src.config import settings

    k = settings.context_canon_top_k
    monkeypatch.setattr(
        embeddings,
        "retrieve",
        lambda topic, *, k, corpus: [
            embeddings.Retrieved(f"c-sem{i}", "", 1.0 - i / 100) for i in range(k)
        ],
    )
    monkeypatch.setattr(
        store,
        "canon_by_tags",
        lambda conn, tags: [CanonFact(f"c-tag{i}", "", ["x"]) for i in range(80)],
    )
    monkeypatch.setattr(
        store, "canon_by_ids", lambda conn, ids: [CanonFact(i, "", []) for i in ids]
    )

    out = context._select_canon(object(), "a three sentence editorial brief")
    assert len(out) == k
    assert all(f.id.startswith("c-sem") for f in out)  # semantic rank decides the cut


def test_topic_for_prefers_the_brief_then_the_tagline():
    from types import SimpleNamespace

    assert context.topic_for(None) is None
    assert context.topic_for(SimpleNamespace(brief="", tagline="")) is None
    assert context.topic_for(SimpleNamespace(brief="", tagline="t")) == "t"
    assert context.topic_for(SimpleNamespace(brief="b", tagline="t")) == "b"


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


def test_co2_bible_and_cards_block_rejoin_to_cached_context(co1_world):
    # CO2 — the split parts must reconstitute the pre-split single string exactly:
    # the shared bible block + the per-speaker-set cards block == cached_context.
    for fmt, ids in co1_world.speaker_sets.items():
        ctx = context.assemble(co1_world.now, speakers=ids)
        assert ctx.bible + ctx.cards_block == ctx.cached_context, fmt
        assert ctx.bible == co1_world.bible, fmt  # bible is the raw, shared prose

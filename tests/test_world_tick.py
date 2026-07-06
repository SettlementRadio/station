"""Tests for the generative world tick (src/world/world_tick.py) — D3.1.

Surgical, on the real logic CLAUDE.md flags: the gate path must DROP a contradictory
proposal (nothing contradictory lands in the store), `_materialise` must place beats
in in-world time with correct clock framing, the JSON parser must survive messy model
output, and the `llm.generate_batch` sync fallback must map results back by request.
The LLM is always mocked (no tokens spent); DB-backed tests roll back at teardown so
they never mutate a developer's seeded dev DB.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime

import pytest
from src.config import settings
from src.providers import embeddings, llm
from src.safety import SafetyResult
from src.world import clock, store
from src.world import world_tick as wt

# --- A canned proposal the mocked `llm.generate` returns --------------------

_NOW = datetime(2026, 6, 24, 20, 0)


def _proposal_json(title: str = "The Lumen Accord") -> str:
    return json.dumps(
        [
            {
                "title": title,
                "summary": "Two orbital settlements sign a light-trade accord.",
                "scale": "large",
                "domain": "nations",
                "arc_stage": "upcoming",
                "beats": [
                    {
                        "title": "Talks open",
                        "body": "Delegates convene above the dayside.",
                        "beat_kind": "announcement",
                        "day_offset": 3,
                        "hour": 9,
                    }
                ],
            }
        ]
    )


# --- Pure: JSON parsing + coercion ------------------------------------------


def test_parse_proposals_plain_array():
    out = wt._parse_proposals(_proposal_json())
    assert len(out) == 1
    assert out[0].title == "The Lumen Accord"
    assert out[0].beats[0].beat_kind == "announcement"


def test_parse_proposals_tolerates_code_fence_and_prose():
    raw = "Here you go:\n```json\n" + _proposal_json() + "\n```"
    assert len(wt._parse_proposals(raw)) == 1


def test_parse_proposals_skips_malformed_and_empty():
    assert wt._parse_proposals("not json at all") == []
    # An object missing beats is skipped; a valid one is kept.
    raw = json.dumps(
        [
            {"title": "No beats", "summary": "x", "beats": []},
            json.loads(_proposal_json())[0],
        ]
    )
    assert len(wt._parse_proposals(raw)) == 1


def test_parse_proposals_salvages_truncated_array():
    # The model hit max_tokens mid-array: 2 complete stories, then a cut-off 3rd.
    full = json.loads(_proposal_json())[0]
    second = {**full, "title": "The Tideglass Pact"}
    truncated = (
        "[\n"
        + json.dumps(full)
        + ",\n"
        + json.dumps(second)
        + ',\n  {"title": "Half a stor'  # cut off here — no closing brace/bracket
    )
    out = wt._parse_proposals(truncated)
    assert [p.title for p in out] == ["The Lumen Accord", "The Tideglass Pact"]


def test_is_ok_matches_continuity_contract():
    assert wt._is_ok("OK")
    assert wt._is_ok("  ok, consistent ")
    assert not wt._is_ok("ISSUES: contradicts the bible")


# --- Pure: materialise (clock framing, clamping, arc validation) ------------


def _ctx() -> wt._TickContext:
    return wt._TickContext(
        bible="", active_summary="", now=_NOW, iw_now=clock.to_inworld(_NOW)
    )


def test_materialise_frames_and_clamps_beats():
    p = wt.ProposedStory(
        title="Drifting Liner",
        summary="A cruise liner goes missing.",
        scale="small",
        domain="geography",
        arc_stage="not-a-real-stage",  # invalid -> defaults to upcoming
        beats=[
            wt.ProposedBeat("Vanished", "Last ping at dusk.", "rumour", -2, 31),
            wt.ProposedBeat("Search", "Tugs sweep the lane.", "development", 999, 9),
        ],
    )
    story, beats = wt._materialise(p, tick_no=1, ctx=_ctx(), index=0)

    assert story.id.startswith("st-")
    assert story.arc_stage == store.ARC_UPCOMING  # invalid stage fell back
    assert story.source == store.EVENT_SOURCE_TICK
    assert story.created_tick == 1
    assert "geography" in story.tags

    # Beat 0: 2 days before in-world now, hour clamped to 23 -> past.
    assert beats[0].story_id == story.id
    assert beats[0].in_world_datetime.hour == 23
    assert beats[0].status == events_status(beats[0])
    assert beats[0].status == "past"
    # Beat 1: day_offset clamped to the horizon -> still upcoming, hour kept.
    horizon = settings.world_tick_beat_horizon_days
    assert (
        beats[1].in_world_datetime.date() - clock.to_inworld(_NOW).date()
    ).days == horizon
    assert beats[1].status == "upcoming"


def events_status(beat: store.Event) -> str:
    from src.world import events as events_mod

    return events_mod.status_of(beat, _NOW)


# --- llm.generate_batch sync fallback (no API, no tokens) -------------------


def test_generate_batch_sync_maps_results_by_request(monkeypatch):
    monkeypatch.setattr(settings, "llm_batch_enabled", False)
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: f"echo:{prompt}")

    reqs = [
        llm.BatchRequest(custom_id="a", prompt="one"),
        llm.BatchRequest(custom_id="b", prompt="two"),
    ]
    results = llm.generate_batch(reqs)

    assert [r.custom_id for r in results] == ["a", "b"]  # request order preserved
    assert all(r.ok for r in results)
    assert results[0].text == "echo:one"


def test_generate_batch_empty_short_circuits():
    assert llm.generate_batch([]) == []


# --- DB-backed run_tick (mocked LLM); rolls back at teardown ----------------


@pytest.fixture
def tick_db(monkeypatch):
    """Patch store.connect to a single rolled-back connection so run_tick's writes
    never persist. Skips cleanly without Postgres/pgvector."""
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001 - no DB -> skip
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001 - pgvector unavailable
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"pgvector unavailable: {exc}")

    # Isolate the tick tests from whatever the dev DB already has COMMITTED: the shared
    # connection reads committed rows, so a leftover tick counter/stories/figures would
    # make tick numbering non-deterministic or leave stray figures a "nothing written"
    # assertion trips on. Clear ALL tick-owned state in THIS (rolled-back) transaction
    # so every test starts from tick 0 with an empty story log. quotes CASCADE from
    # stories, but figures carry no story FK — so clear figures/quotes explicitly
    # (quotes first, they FK figures), else a committed dev-DB `world-tick` leaks in.
    conn.execute("DELETE FROM quotes")
    conn.execute("DELETE FROM figures")
    conn.execute("DELETE FROM events WHERE source = %s", (store.EVENT_SOURCE_TICK,))
    conn.execute("DELETE FROM stories")
    conn.execute(
        "DELETE FROM state WHERE key IN ('world_tick_count', 'world_tick_last_at')"
    )

    @contextlib.contextmanager
    def fake_connect():
        yield conn  # shared, uncommitted — all run_tick DB work lands in one txn

    monkeypatch.setattr(store, "connect", fake_connect)
    # Embeddings: don't load a model in the suite — return right-width zero vectors,
    # and make semantic de-dup a no-op (structural Jaccard still runs). Tests that
    # want semantic de-dup override `embeddings.retrieve` themselves.
    monkeypatch.setattr(
        embeddings,
        "embed",
        lambda texts: [[0.0] * settings.embeddings_dim for _ in texts],
    )
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [])
    monkeypatch.setattr(
        wt, "safety_check", lambda text: SafetyResult(True, "OK", "disabled")
    )
    try:
        yield conn
    finally:
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def test_run_tick_writes_accepted_story(tick_db, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json())
    monkeypatch.setattr(
        llm,
        "generate_batch",
        lambda reqs, **kw: [llm.BatchResult(r.custom_id, "OK", ok=True) for r in reqs],
    )

    result = wt.run_tick(now=_NOW)

    assert result.proposed == 1
    assert result.accepted == 1
    assert result.dropped == 0
    assert len(result.story_ids) == 1

    story = store.get_story(tick_db, result.story_ids[0])
    assert story is not None and story.source == store.EVENT_SOURCE_TICK
    beats = store.story_beats(tick_db, story.id)
    assert beats and all(b.story_id == story.id for b in beats)
    # The tick counter advanced (state is tick-owned, survives a canon refresh).
    assert store.get_state(tick_db, "world_tick_count") == "1"


def test_run_tick_drops_contradictory_proposal(tick_db, monkeypatch):
    # No regeneration: a single flag must drop the story; nothing contradictory lands.
    monkeypatch.setattr(settings, "world_tick_max_attempts", 1)
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json())
    monkeypatch.setattr(
        llm,
        "generate_batch",
        lambda reqs, **kw: [
            llm.BatchResult(r.custom_id, "ISSUES: contradicts canon", ok=True)
            for r in reqs
        ],
    )

    result = wt.run_tick(now=_NOW)

    assert result.proposed == 1
    assert result.accepted == 0
    assert result.dropped == 1
    assert result.story_ids == []
    assert store.active_stories(tick_db) == []  # nothing written


def test_run_tick_regenerates_then_accepts(tick_db, monkeypatch):
    # Flagged on the first gate, OK after the one allowed regeneration.
    calls = {"batch": 0}

    def fake_batch(reqs, **kw):
        calls["batch"] += 1
        verdict = (
            "ISSUES: too close to a running story" if calls["batch"] == 1 else "OK"
        )
        return [llm.BatchResult(r.custom_id, verdict, ok=True) for r in reqs]

    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json())
    monkeypatch.setattr(llm, "generate_batch", fake_batch)

    result = wt.run_tick(now=_NOW)

    assert calls["batch"] == 2  # initial gate + re-gate after regeneration
    assert result.regenerated == 1
    assert result.accepted == 1
    assert result.dropped == 0


def test_run_tick_safety_flag_skips_continuity(tick_db, monkeypatch):
    # A safety-flagged proposal must never reach the continuity batch.
    monkeypatch.setattr(settings, "world_tick_max_attempts", 1)
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json())
    monkeypatch.setattr(
        wt,
        "safety_check",
        lambda text: SafetyResult(False, "blocklisted term", "keyword"),
    )

    def boom(reqs, **kw):  # pragma: no cover - must not run when nothing is safe
        raise AssertionError("continuity batch called for a safety-flagged proposal")

    monkeypatch.setattr(llm, "generate_batch", boom)

    result = wt.run_tick(now=_NOW)
    assert result.accepted == 0
    assert result.dropped == 1


# --- D3.2: advancing running stories across ticks ---------------------------


def _advance_json(stage: str = "happening") -> str:
    return json.dumps(
        {
            "arc_stage": stage,
            "beat": {
                "title": "The pact deepens",
                "body": "New terms emerge as the settlements trade light.",
                "beat_kind": "development",
                "day_offset": 1,
                "hour": 10,
            },
        }
    )


def _smart_batch(advance_stage: str = "happening"):
    """A generate_batch mock: JSON for advance-generation requests, OK for gates."""

    def fake_batch(reqs, **kw):
        out = []
        for r in reqs:
            if "next beat as a JSON object" in r.prompt:
                out.append(
                    llm.BatchResult(r.custom_id, _advance_json(advance_stage), ok=True)
                )
            else:
                out.append(llm.BatchResult(r.custom_id, "OK", ok=True))
        return out

    return fake_batch


def test_parse_advance_enforces_forward_only():
    story = store.Story(id="s1", title="T", summary="S", arc_stage=store.ARC_HAPPENING)
    fwd = wt._parse_advance(_advance_json("developing"), story, [])
    assert fwd is not None and fwd.new_stage == "developing"  # forward kept
    # Backward (happening -> upcoming) is illegal -> falls back to the current stage.
    back = wt._parse_advance(_advance_json("upcoming"), story, [])
    assert back is not None and back.new_stage == store.ARC_HAPPENING
    assert wt._parse_advance("not json", story, []) is None


def test_run_tick_advances_running_story(tick_db, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json())
    monkeypatch.setattr(llm, "generate_batch", _smart_batch("happening"))

    first = wt.run_tick(now=_NOW)
    assert first.accepted == 1
    assert first.advanced == 0  # nothing pre-existing to advance on the first tick
    created_id = first.story_ids[0]

    second = wt.run_tick(now=_NOW)
    assert created_id in second.advanced_ids
    assert second.advanced >= 1

    moved = store.get_story(tick_db, created_id)
    assert moved.arc_stage == "happening"  # upcoming -> happening
    assert moved.last_advanced_tick == 2  # stamped with the advancing tick
    beats = store.story_beats(tick_db, created_id)
    assert any(b.id.endswith("-a2") for b in beats)  # a new advancement beat appended


def test_resolved_story_stops_advancing(tick_db, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json())
    monkeypatch.setattr(llm, "generate_batch", _smart_batch("past"))

    created_id = wt.run_tick(now=_NOW).story_ids[0]
    second = wt.run_tick(now=_NOW)  # advances + resolves the tick-1 story
    assert second.resolved == 1
    assert store.get_story(tick_db, created_id).arc_stage == store.ARC_PAST

    third = wt.run_tick(now=_NOW)  # resolved story must be excluded from candidates
    assert created_id not in third.advanced_ids


# --- D3.3: variety, balance & de-duplication --------------------------------


def _story(domain: str, *, title: str = "T", summary: str = "S") -> store.Story:
    return store.Story(
        id=title, title=title, summary=summary, arc_stage="upcoming", tags=[domain]
    )


def test_quiet_domains_surfaces_underused():
    # A world heavy on `nations` should steer toward domains it has ignored.
    recent = [_story("nations", title=f"n{i}") for i in range(5)]
    recent += [_story("finance", title="f0")]
    quiet = wt._quiet_domains(recent, k=3)

    assert "nations" not in quiet  # the busy domain is not spotlighted
    assert "finance" not in quiet  # used once — still busier than the untouched ones
    assert all(d in wt.DOMAINS for d in quiet)
    assert len(quiet) == 3


def test_jaccard_dedup_catches_near_duplicate_text():
    a = "A cruise liner goes missing near the dayside lane"
    near = "A cruise liner goes missing along the dayside lane"
    far = "The lunar exchange posts record quarterly gains"
    assert wt._jaccard_dup(a, [near])  # almost the same words -> duplicate
    assert not wt._jaccard_dup(a, [far])  # unrelated -> kept


def test_dedup_rejects_within_batch_duplicate(monkeypatch):
    monkeypatch.setattr(embeddings, "retrieve", lambda *a, **k: [])  # structural only
    p1 = wt.ProposedStory(
        title="Liner Vanishes",
        summary="A cruise liner goes missing near the dayside lane.",
        scale="small",
        domain="geography",
        arc_stage="happening",
        beats=[wt.ProposedBeat("Gone", "Last ping at dusk.", "rumour", 0, 20)],
    )
    p2 = wt.ProposedStory(  # a near-restatement of p1
        title="Liner Vanishes",
        summary="A cruise liner goes missing near the dayside lane.",
        scale="small",
        domain="geography",
        arc_stage="happening",
        beats=[wt.ProposedBeat("Gone", "Last ping at dusk.", "rumour", 0, 21)],
    )
    result = wt.TickResult(tick=1)
    kept = wt._dedup([p1, p2], [], result)

    assert len(kept) == 1
    assert result.duplicates == 1


def test_dedup_semantic_rejects_against_persisted(monkeypatch):
    # A high-scoring D2 hit against an existing story rejects the proposal.
    from src.providers.embeddings import Retrieved

    monkeypatch.setattr(
        embeddings, "retrieve", lambda *a, **k: [Retrieved("old", "old story", 0.95)]
    )
    p = wt.ProposedStory(
        title="Brand new",
        summary="Totally distinct words here entirely.",
        scale="large",
        domain="finance",
        arc_stage="upcoming",
        beats=[wt.ProposedBeat("Beat", "Body.", "development", 1, 9)],
    )
    result = wt.TickResult(tick=1)
    assert wt._dedup([p], [], result) == []  # semantic hit -> rejected
    assert result.duplicates == 1


def test_pacing_cap_blocks_new_stories(tick_db, monkeypatch):
    # At/over the active-story cap, the tick proposes NO new stories (advance-only).
    monkeypatch.setattr(settings, "world_tick_max_active_stories", 0)

    def boom(*a, **k):  # pragma: no cover - propose must be skipped under the cap
        raise AssertionError("proposed new stories despite the pacing cap")

    monkeypatch.setattr(llm, "generate", boom)
    monkeypatch.setattr(llm, "generate_batch", lambda reqs, **k: [])

    result = wt.run_tick(now=_NOW)
    assert result.proposed == 0
    assert result.accepted == 0
    assert result.story_ids == []


# --- D10.1: the tick peoples its stories (figures + quotes) -----------------


def _proposal_json_people(figure: str = "Mira Voss") -> str:
    """A proposal carrying one figure + a beat that quotes them, plus a junk quote."""
    return json.dumps(
        [
            {
                "title": "The Relay Holds",
                "summary": "An orbital relay survives a solar storm.",
                "scale": "small",
                "domain": "technology",
                "arc_stage": "happening",
                "figures": [
                    {"name": figure, "role": "relay-keeper", "bio": "Steady hand."}
                ],
                "beats": [
                    {
                        "title": "It held",
                        "body": "The relay rode out the storm.",
                        "beat_kind": "development",
                        "day_offset": 0,
                        "hour": 20,
                        "quotes": [
                            {
                                "figure": figure,
                                "text": "We are not going dark.",
                                "stance": "reassuring",
                            },
                            {"figure": "Nobody At All", "text": "ignore me"},
                        ],
                    }
                ],
            }
        ]
    )


def _advance_json_people(stage: str = "developing", figure: str = "Mira Voss") -> str:
    return json.dumps(
        {
            "arc_stage": stage,
            "new_figures": [],
            "beat": {
                "title": "Aftermath",
                "body": "The keeper assesses the damage.",
                "beat_kind": "consequence",
                "day_offset": 1,
                "hour": 9,
                "quotes": [
                    {
                        "figure": figure,
                        "text": "Two panels to replace.",
                        "stance": "matter-of-fact",
                    }
                ],
            },
        }
    )


def test_coerce_story_parses_figures_and_caps_quotes(monkeypatch):
    monkeypatch.setattr(settings, "world_tick_quotes_per_story_max", 1)
    p = wt._parse_proposals(_proposal_json_people())[0]
    assert [f.name for f in p.figures] == ["Mira Voss"]
    assert p.figures[0].role == "relay-keeper"
    # Two quotes proposed, but the per-story cap trims to 1 (a few voices, not a crowd).
    assert sum(len(b.quotes) for b in p.beats) == 1


def test_materialise_people_links_quotes_and_drops_unattributed():
    p = wt._parse_proposals(_proposal_json_people())[0]
    story, beats = wt._materialise(p, tick_no=1, ctx=_ctx(), index=0)
    figures, quotes = wt._materialise_people(p, story, beats, tick_no=1)

    assert [f.name for f in figures] == ["Mira Voss"]
    assert all(f.source == store.FIGURE_SOURCE_TICK for f in figures)
    # The quote to "Nobody At All" (an undeclared figure) is dropped; only Mira's lands.
    assert len(quotes) == 1
    assert quotes[0].figure_id == figures[0].id
    assert quotes[0].beat_id == beats[0].id
    assert quotes[0].in_world_datetime == beats[0].in_world_datetime  # from the beat


def test_figures_disabled_yields_no_people(monkeypatch):
    monkeypatch.setattr(settings, "world_tick_figures_enabled", False)
    p = wt._parse_proposals(_proposal_json_people())[0]
    assert p.figures == []
    story, beats = wt._materialise(p, tick_no=1, ctx=_ctx(), index=0)
    assert wt._materialise_people(p, story, beats, tick_no=1) == ([], [])


def test_run_tick_writes_figures_and_quotes(tick_db, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json_people())
    monkeypatch.setattr(
        llm,
        "generate_batch",
        lambda reqs, **kw: [llm.BatchResult(r.custom_id, "OK", ok=True) for r in reqs],
    )

    result = wt.run_tick(now=_NOW)
    sid = result.story_ids[0]

    figs = store.figures_for_story(tick_db, sid)
    assert [f.name for f in figs] == ["Mira Voss"]
    quotes = store.quotes_for_story(tick_db, sid)
    assert len(quotes) == 1  # the unattributed second quote was dropped
    assert quotes[0].figure_id == figs[0].id
    assert result.usage.get("figures_written") == 1
    assert result.usage.get("quotes_written") == 1


def test_run_tick_advance_reuses_existing_figure(tick_db, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json_people())

    def smart(reqs, **kw):
        out = []
        for r in reqs:
            if "next beat as a JSON object" in r.prompt:
                out.append(
                    llm.BatchResult(r.custom_id, _advance_json_people(), ok=True)
                )
            else:
                out.append(llm.BatchResult(r.custom_id, "OK", ok=True))
        return out

    monkeypatch.setattr(llm, "generate_batch", smart)

    sid = wt.run_tick(now=_NOW).story_ids[0]
    second = wt.run_tick(now=_NOW)  # advances the story; quote reuses Mira by name

    assert sid in second.advanced_ids
    figs = store.figures_for_story(tick_db, sid)
    assert [f.name for f in figs] == ["Mira Voss"]  # NO duplicate figure created
    quotes = store.quotes_for_story(tick_db, sid)
    assert len(quotes) == 2  # the original + the advancement's, both attributed to Mira
    assert {q.figure_id for q in quotes} == {figs[0].id}
    assert any(q.beat_id and q.beat_id.endswith("-a2") for q in quotes)  # advance beat


def test_run_tick_flagged_quote_drops_whole_story(tick_db, monkeypatch):
    # A figure/quote rides the story's gate: one flag drops the lot — nothing written.
    monkeypatch.setattr(settings, "world_tick_max_attempts", 1)
    monkeypatch.setattr(llm, "generate", lambda prompt, **kw: _proposal_json_people())
    monkeypatch.setattr(
        llm,
        "generate_batch",
        lambda reqs, **kw: [
            llm.BatchResult(r.custom_id, "ISSUES: a quote names a real person", ok=True)
            for r in reqs
        ],
    )

    result = wt.run_tick(now=_NOW)
    assert result.accepted == 0
    assert result.story_ids == []
    # Nothing bad written: no stray figures/quotes left behind.
    assert store.counts(tick_db)["figures"] == 0
    assert store.counts(tick_db)["quotes"] == 0


# --- D3.4: the CLI job (loud failure, non-zero exit, store untouched) --------


def test_cli_main_returns_zero_on_success(monkeypatch, capsys):
    monkeypatch.setattr(wt, "run_tick", lambda: wt.TickResult(tick=7, accepted=2))
    assert wt.main() == 0
    assert "World tick #7" in capsys.readouterr().out


def test_cli_main_fails_loud_nonzero(monkeypatch, capsys):
    def boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(wt, "run_tick", boom)
    assert wt.main() == 1  # non-zero so a C5 timer can alert; no exception escapes
    assert "FAILED" in capsys.readouterr().out

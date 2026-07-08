"""Tests for the story-log-driven news producer (src/formats/news.py) — D4.2 + D4.3.

The creative step (Claude + TTS) is exercised by the D4.4 demo; here we pin the pure,
brittle logic a silent bug would corrupt:

* the desk BRIEF frames each story by its tag — an `evolve` item reads as an update
  carrying the delta beat, a `repeat` as a light "still developing" touch, a plain
  item reports its lead beat with the right relative phrase;
* an empty selection yields the quiet-day instruction (the desk never goes blank);
* coverage RECORDING writes the story's newest beat + the consistent handle, and
  reuses a prior angle (the D4.0 round-trip the next bulletin reads);
* CONTINUITY (D4.3) — prior coverage is fed into the prompt for consistent naming,
  and the gate regenerates on a flagged draft then falls back to evergreen (C0).

DB tests roll back at teardown and skip cleanly without Postgres; the gate tests mock
Claude + TTS so no tokens are spent.
"""

from __future__ import annotations

import contextlib
from datetime import datetime

import pytest
from src.formats import news, news_select
from src.world import store
from src.world.context import AssembledContext

# A fixed real `now`; in-world face is +600 (2626-06-24 12:00).
NOW = datetime(2026, 6, 24, 12, 0)


def _story(story_id: str, *, stage: str = store.ARC_DEVELOPING) -> store.Story:
    return store.Story(
        id=story_id,
        title=f"The {story_id} Affair",
        summary="A happening in the +600y world.",
        arc_stage=stage,
        source=store.EVENT_SOURCE_TICK,
        created_tick=1,
    )


def _beat(beat_id: str, story_id: str, when: datetime) -> store.Event:
    return store.Event(
        id=beat_id,
        title=f"Beat {beat_id}",
        body=f"the {beat_id} development",
        in_world_datetime=when,
        status="today",
        source=store.EVENT_SOURCE_TICK,
        story_id=story_id,
        beat_kind="development",
    )


def _sel(
    story: store.Story,
    *,
    coverage_tag: str,
    temporal_kind: str,
    lead_beat=None,
    new_beat=None,
    latest_beat=None,
    prior_coverage=None,
    quotes=None,
) -> news_select.SelectedStory:
    return news_select.SelectedStory(
        story=story,
        coverage_tag=coverage_tag,
        temporal_kind=temporal_kind,
        lead_beat=lead_beat,
        new_beat=new_beat,
        latest_beat=latest_beat if latest_beat is not None else lead_beat,
        prior_coverage=prior_coverage,
        canon_score=0.0,
        score=1.0,
        quotes=quotes or [],
    )


# --- Brief framing (pure; no DB) --------------------------------------------


def test_brief_evolve_reads_as_an_update_with_the_delta():
    story = _story("orbital")
    new_beat = _beat("nb", "orbital", datetime(2626, 6, 23, 20, 0))  # yesterday
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_EVOLVE,
        temporal_kind=news_select.KIND_ONGOING,
        lead_beat=new_beat,
        new_beat=new_beat,
    )
    brief = news._story_brief(sel, NOW)
    assert "UPDATE" in brief
    assert "yesterday" in brief  # relative phrase off the delta beat
    assert "the nb development" in brief  # the delta body is spelled out
    assert news_select.COVERAGE_EVOLVE in brief  # tagged for the anchor


def test_brief_repeat_is_a_light_touch():
    story = _story("levee")
    lead = _beat("lb", "levee", datetime(2626, 6, 20, 9, 0))
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_REPEAT,
        temporal_kind=news_select.KIND_ONGOING,
        lead_beat=lead,
    )
    brief = news._story_brief(sel, NOW)
    assert "still developing" in brief
    assert "don't re-read" in brief


def test_brief_plain_item_reports_lead_beat_with_phrase():
    story = _story("market")
    lead = _beat("mb", "market", datetime(2626, 6, 24, 12, 0))  # today
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_NEW,
        temporal_kind=news_select.KIND_BREAKING,
        lead_beat=lead,
    )
    brief = news._story_brief(sel, NOW)
    assert "the mb development" in brief
    assert "this afternoon" in brief  # same-day midday phrase
    assert "UPDATE" not in brief  # a fresh item, not an update


def test_brief_includes_attributed_quotes_with_temporal_framing():
    # D10.2 — a story's quotes become attribution lines, each framed by its own date.
    story = _story("relay")
    lead = _beat("rb", "relay", datetime(2626, 6, 24, 9, 0))
    quote = store.Quote(
        id="rq",
        story_id="relay",
        figure_id="rf",
        text="We are not going dark.",
        in_world_datetime=datetime(2626, 6, 23, 20, 0),  # yesterday vs NOW
    )
    figure = store.Figure(
        id="rf", name="Mira Voss", role="relay-keeper", card_text="Steady."
    )
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_NEW,
        temporal_kind=news_select.KIND_BREAKING,
        lead_beat=lead,
        quotes=[(quote, figure)],
    )
    brief = news._story_brief(sel, NOW)
    assert "Mira Voss (relay-keeper)" in brief
    assert "yesterday" in brief  # the quote's own date, framed
    assert "We are not going dark." in brief


def test_empty_selection_gives_the_quiet_day_instruction():
    block = news._briefs_block([], NOW)
    assert "quiet news day" in block
    assert "never invent real-world news" in block


def test_coverage_meta_is_auditable():
    story = _story("a")
    lead = _beat("ab", "a", datetime(2626, 6, 24, 11, 0))
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_NEW,
        temporal_kind=news_select.KIND_BREAKING,
        lead_beat=lead,
    )
    meta = news._coverage_meta([sel])
    assert meta["story_count"] == 1
    assert meta["stories"] == ["a"]
    assert meta["tags"] == {"a": "breaking/new"}
    assert meta["beats"] == ["ab"]


# --- Coverage recording (DB; skips without Postgres) ------------------------


@pytest.fixture
def db():
    """A store connection with the schema, that ALWAYS rolls back at teardown."""
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"pgvector unavailable: {exc}")
    try:
        yield conn
    finally:
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def test_record_coverage_writes_latest_beat_and_title_handle(db, monkeypatch):
    # _record_coverage opens its own store.connect(); point it at this txn's conn so
    # the write rolls back with the test.
    monkeypatch.setattr(store, "connect", lambda: _SameConn(db))

    story = _story("d42-rec")
    db_insert(
        db,
        story,
        [("b1", datetime(2626, 6, 22, 9, 0)), ("b2", datetime(2626, 6, 24, 9, 0))],
    )
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_NEW,
        temporal_kind=news_select.KIND_BREAKING,
        lead_beat=None,
        latest_beat=_beat("b2", "d42-rec", datetime(2626, 6, 24, 9, 0)),
    )

    news._record_coverage([sel], NOW)

    got = store.last_coverage(db, "d42-rec")
    assert got is not None
    assert got.last_beat_id == "b2"  # the story's NEWEST beat, not the lead
    assert got.angle == "The d42-rec Affair"  # title used as the handle
    assert got.covered_at == datetime(2626, 6, 24, 12, 0)  # in-world air time


def test_record_coverage_reuses_prior_angle(db, monkeypatch):
    monkeypatch.setattr(store, "connect", lambda: _SameConn(db))

    story = _story("d42-angle")
    db_insert(db, story, [("c1", datetime(2626, 6, 24, 8, 0))])
    prior = store.NewsCoverage(
        story_id="d42-angle",
        covered_at=datetime(2626, 6, 24, 6, 0),
        arc_stage=store.ARC_DEVELOPING,
        last_beat_id="c1",
        angle="the river crisis",  # the handle the desk used last time
    )
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_REPEAT,
        temporal_kind=news_select.KIND_ONGOING,
        lead_beat=_beat("c1", "d42-angle", datetime(2626, 6, 24, 8, 0)),
        prior_coverage=prior,
    )

    news._record_coverage([sel], NOW)
    got = store.last_coverage(db, "d42-angle")
    assert got.angle == "the river crisis"  # consistent naming carried forward


# --- helpers for the DB tests -----------------------------------------------


def db_insert(db, story, beats):
    store.insert_story(db, story)
    store.insert_beats(db, [_beat(bid, story.id, when) for bid, when in beats])


class _SameConn:
    """A context manager that yields an existing connection WITHOUT closing it.

    Lets `_record_coverage`'s `with store.connect() as conn` reuse the test's rolled-
    back transaction (so the write never persists), instead of opening a real one.
    """

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *exc):
        return False


# --- Continuity: prior-coverage feed (pure; no DB) --------------------------


def _prior(story_id: str, *, stage: str, angle: str) -> store.NewsCoverage:
    return store.NewsCoverage(
        story_id=story_id,
        covered_at=datetime(2626, 6, 24, 6, 0),
        arc_stage=stage,
        last_beat_id=None,
        angle=angle,
    )


def test_continuity_block_lists_prior_handles_and_stage():
    story = _story("levee")
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_REPEAT,
        temporal_kind=news_select.KIND_ONGOING,
        prior_coverage=_prior(
            "levee", stage=store.ARC_HAPPENING, angle="the levee row"
        ),
    )
    block = news._continuity_block([sel])
    assert "the levee row" in block  # the handle to keep using
    assert store.ARC_HAPPENING in block  # the stage last reported
    assert "SAME name" in block


def test_continuity_block_empty_without_prior_coverage():
    story = _story("fresh")
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_NEW,
        temporal_kind=news_select.KIND_BREAKING,
    )
    assert news._continuity_block([sel]) == ""


def test_build_system_weaves_continuity_and_revision_note():
    story = _story("levee")
    sel = _sel(
        story,
        coverage_tag=news_select.COVERAGE_REPEAT,
        temporal_kind=news_select.KIND_ONGOING,
        prior_coverage=_prior(
            "levee", stage=store.ARC_HAPPENING, angle="the levee row"
        ),
    )
    ctx = AssembledContext(bible="BIBLE", dynamic="")
    system = news._build_system(
        ctx, NOW, "Vell", [sel], revision_note="you renamed the levee story"
    )
    assert "the levee row" in system  # prior coverage fed to the writer
    assert "PREVIOUS DRAFT" in system  # the revision note guides the retry
    assert "you renamed the levee story" in system


def test_build_system_weaves_freshness_with_d4_vs_d5_distinction():
    # D5.2 — recent openings reach the desk prompt, and the note makes clear that
    # repeating a STORY is fine (D4) but the WORDING must vary (D5).
    ctx = AssembledContext(bible="BIBLE", dynamic="")
    system = news._build_system(
        ctx,
        NOW,
        "Vell",
        [],
        recent_openings=(
            "Recent openings (open differently):\n- good evening from the desk"
        ),
    )
    assert "good evening from the desk" in system  # the steer reached the prompt
    assert "Repeating a STORY" in system  # the D4/D5 boundary is spelled out
    assert "vary the" in system.lower()


def test_build_system_omits_freshness_when_empty():
    ctx = AssembledContext(bible="BIBLE", dynamic="")
    system = news._build_system(ctx, NOW, "Vell", [])
    assert "Repeating a STORY" not in system  # no dangling freshness note


# --- Continuity gate loop (mocks Claude + TTS; no tokens, no DB) -------------


def _ctx_with_anchor() -> AssembledContext:
    anchor = store.CastMember(
        id="vell", name="Vell", card_text="dry, precise", logical_voice="vell_night"
    )
    return AssembledContext(bible="BIBLE", dynamic="", speakers=[anchor])


def _one_selection() -> list[news_select.SelectedStory]:
    story = _story("levee")
    lead = _beat("lb", "levee", datetime(2626, 6, 24, 11, 0))
    return [
        _sel(
            story,
            coverage_tag=news_select.COVERAGE_NEW,
            temporal_kind=news_select.KIND_BREAKING,
            lead_beat=lead,
        )
    ]


def _wire_gate(monkeypatch, editor):
    """Mock selection, TTS, coverage, and route llm.generate to writer/editor stubs.

    `editor(draft) -> note` decides the continuity verdict per draft; the writer
    returns DRAFT-1, DRAFT-2, … so the editor can vary its verdict across retries.
    Returns the list that records coverage calls.
    """
    monkeypatch.setattr(
        news.news_select, "select_stories", lambda now: _one_selection()
    )
    monkeypatch.setattr(
        news.common, "render_single_voice", lambda parts, voice, seg_id: "/fake.mp3"
    )
    monkeypatch.setattr(news, "safety_check", lambda text: _ok_safety())
    recorded: list = []
    monkeypatch.setattr(news, "_record_coverage", lambda sel, now: recorded.append(sel))

    writer_calls = {"n": 0}

    def fake_generate(prompt, *, system, model, max_tokens=None, **kwargs):
        if prompt.startswith("Draft to check"):
            draft = prompt.split("Draft to check:", 1)[1]
            return editor(draft)
        writer_calls["n"] += 1
        return f"DRAFT-{writer_calls['n']}"

    monkeypatch.setattr(news.llm, "generate", fake_generate)
    return recorded, writer_calls


def _ok_safety():
    from src.safety import SafetyResult

    return SafetyResult(ok=True, reason="ok", stage="llm")


def test_continuity_gate_regenerates_then_renders(monkeypatch):
    # DRAFT-1 is flagged (both base + escalation passes), DRAFT-2 clears.
    def editor(draft: str) -> str:
        return "ISSUES: you renamed the levee story" if "DRAFT-1" in draft else "OK"

    recorded, writer_calls = _wire_gate(monkeypatch, editor)
    seg = news.news(NOW, _ctx_with_anchor())

    assert seg.script == "DRAFT-2"  # the clean draft aired, not the flagged one
    assert seg.meta["continuity_ok"] is True
    assert writer_calls["n"] == 2  # regenerated once
    assert len(recorded) == 1  # coverage recorded on the clean render


def test_continuity_gate_falls_back_to_evergreen(monkeypatch):
    # Every draft is flagged -> no draft clears -> evergreen, nothing aired/recorded.
    recorded, _ = _wire_gate(monkeypatch, lambda draft: "ISSUES: contradicts canon")
    sentinel = object()
    monkeypatch.setattr(
        news.evergreen,
        "evergreen_segment",
        lambda now, **kw: sentinel,
    )

    result = news.news(NOW, _ctx_with_anchor())
    assert result is sentinel  # dropped to evergreen
    assert recorded == []  # no coverage recorded — nothing aired


def test_safety_gate_falls_back_to_evergreen_and_writes_nothing(monkeypatch):
    # Continuity would pass, but every draft trips the SAFETY gate -> evergreen,
    # nothing flagged is rendered, no coverage recorded.
    from src.safety import SafetyResult

    recorded, _ = _wire_gate(monkeypatch, lambda draft: "OK")
    monkeypatch.setattr(
        news,
        "safety_check",
        lambda text: SafetyResult(ok=False, reason="blocklisted term", stage="keyword"),
    )
    sentinel = object()
    monkeypatch.setattr(news.evergreen, "evergreen_segment", lambda now, **kw: sentinel)

    result = news.news(NOW, _ctx_with_anchor())
    assert result is sentinel  # safety flag drops the slot to evergreen
    assert recorded == []  # nothing aired -> nothing recorded

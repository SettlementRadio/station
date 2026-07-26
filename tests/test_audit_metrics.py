"""Q0.0 — the free audit metrics: the key contract, the maths, the code reads.

The harness is what every later Phase Q gate is asserted against, so the bits with real
logic get tested: the declared-key contract (a group that fails must degrade to explicit
`null`, never vanish), the register/title maths, and the two code reads that measure
whether a fix landed (`topic_passed_on_live_path`, `batch_enabled_paths`). The DB-backed
collectors are glue over `store` reads and are covered by running `make audit`.
"""

from __future__ import annotations

from datetime import datetime

from src.audit import metrics

# --- the key contract -------------------------------------------------------


def test_declared_keys_cover_the_phase_q_groups():
    """§1's groups, by name — Q8 and gates.yaml read these, so they may not drift."""
    assert set(metrics.GROUP_KEYS) == {
        "world",
        "quotes",
        "grid",
        "context",
        "freshness",
        "models",
        "cost",
    }
    assert "usd_per_talk_segment" in metrics.GROUP_KEYS["cost"]
    # The two-count distinction (seed README §4) — conflating them misreads supply 2x.
    assert {"active_stories", "stories_status_active_rows"} <= set(
        metrics.GROUP_KEYS["world"]
    )


def test_a_failed_group_degrades_to_explicit_nulls(monkeypatch):
    """An unreachable DB must not make a metric *missing* — "not measured" != "fine"."""

    def boom(*a, **kw):
        raise RuntimeError("no postgres here")

    monkeypatch.setattr(metrics.store, "connect", boom)
    data = metrics.collect_free(datetime(2026, 7, 27, 9, 0))

    assert set(data["world"]) >= set(metrics.GROUP_KEYS["world"])
    assert all(data["world"][k] is None for k in metrics.GROUP_KEYS["world"])
    assert "no postgres here" in data["world"]["error"]
    # The token-free groups still measured, so a dead DB costs only its own numbers.
    assert data["freshness"]["window_hours"] is not None
    assert data["grid"]["registered_formats"] >= 6
    # And it renders rather than crashing.
    assert "not measured" in metrics.render_table(data)


def test_reference_clock_is_pinned_to_noon():
    """Two runs minutes apart must agree — the reference clock can't be `now()`."""
    a = metrics.reference_now(datetime(2026, 7, 27, 3, 14, 15))
    b = metrics.reference_now(datetime(2026, 7, 27, 23, 59, 59))
    assert a == b == datetime(2026, 7, 27, 12, 0)


# --- the register + title maths ---------------------------------------------


def test_register_stats_counts_contractions_hedges_and_length():
    stats = metrics.register_stats(
        [
            "We'll see how it goes, I think.",  # contraction + 2 hedges
            "The line is closed until the survey finishes and the crew signs it off.",
        ]
    )
    assert stats["count"] == 2
    assert stats["pct_with_contraction"] == 50.0
    assert stats["hedges_per_1000w"] > 0
    assert stats["pct_under_12w"] == 50.0


def test_register_stats_on_nothing_reports_a_zero_count_not_a_crash():
    assert metrics.register_stats([]) == {"count": 0}


# --- the code reads: the two "did the fix land?" measurements ---------------


def test_topic_passed_on_live_path_reads_the_real_call_site(tmp_path):
    """False until Q2.1 threads a topic through the scheduler; True after."""
    before = tmp_path / "before.py"
    before.write_text(
        "seg = make_format_segment(\n"
        "    name, air_cursor.isoformat(), speakers=speakers, flow=flow\n"
        ")\n"
    )
    after = tmp_path / "after.py"
    after.write_text(
        "seg = make_format_segment(\n"
        "    name, air_cursor.isoformat(), topic=program.brief, speakers=speakers\n"
        ")\n"
    )
    assert metrics.topic_passed_on_live_path(before) is False
    assert metrics.topic_passed_on_live_path(after) is True
    # A missing file is a False, never an exception — the audit never crashes on a read.
    assert metrics.topic_passed_on_live_path(tmp_path / "gone.py") is False


def test_topic_is_not_passed_on_the_live_path_today():
    """The §1f baseline finding, asserted against the real scheduler."""
    assert metrics.topic_passed_on_live_path() is False


def test_batch_enabled_paths_finds_calls_not_docstring_mentions(tmp_path):
    """§1h: only the tick batches. Prose about `llm.generate_batch` must not count."""
    src = tmp_path / "src"
    (src / "world").mkdir(parents=True)
    (src / "world" / "world_tick.py").write_text(
        "for r in llm.generate_batch(reqs):\n    pass\n"
    )
    (src / "scheduler.py").write_text(
        '"""The near-live path; it never calls `llm.generate_batch`."""\n'
    )
    assert metrics.batch_enabled_paths(src) == ["src/world/world_tick.py"]


def test_batch_enabled_paths_on_the_real_tree_is_the_tick_only():
    """The unclaimed-50% finding Q7.2 exists to change."""
    assert metrics.batch_enabled_paths() == ["src/world/world_tick.py"]


# --- the grid walk ----------------------------------------------------------


def test_grid_metrics_measures_a_whole_pinned_week():
    """Format share + host load over the pinned Monday — no DB, no tokens."""
    grid = metrics.grid_metrics()
    assert (
        sum(grid["format_share"].values()) == 100.0
        or abs(sum(grid["format_share"].values()) - 100.0) < 0.5
    )
    assert grid["programs"] > 1
    assert grid["max_host_hours_per_day"] >= grid["min_host_hours_per_day"]
    # Nobody can carry more than the day (the walk is 15-min slots over 7 days).
    assert grid["max_host_hours_per_day"] <= 24.0
    assert grid["news_anchor_count"] >= 1

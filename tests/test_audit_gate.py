"""Q0.2 — the gate, the compare table, and the committed thresholds.

This is the machinery that decides whether a Phase Q pack is done, so the tests are
about the ways a gate can lie: passing something it never measured, rounding a miss
up to a pass, losing a threshold in transcription, or — the one the pack calls out
explicitly — not being able to fail at all.
"""

from __future__ import annotations

import json

import pytest
import yaml
from src.audit import compare as compare_mod
from src.audit import gate as gate_mod
from src.audit import runs as runs_mod
from src.config import settings

# --- flattening: the vocabulary the thresholds are written in ----------------


def test_flatten_reaches_nested_entries_both_ways():
    """`grid.format_share` AND `grid.format_share.talk` — whole-map rules need both."""
    flat = runs_mod.flatten(
        {
            "collected_at": "2026-07-26T12:00:00",  # not a metric
            "grid": {"format_share": {"talk": 63.5, "news": 23.6}, "programs": 35},
            "probe": {"wall_seconds": 665.7},  # bookkeeping, excluded
            "_segments": [{"slot": "x"}],  # out-of-band, excluded
        }
    )
    assert flat["grid.format_share"] == {"talk": 63.5, "news": 23.6}
    assert flat["grid.format_share.talk"] == 63.5
    assert flat["grid.programs"] == 35
    assert "collected_at" not in flat
    assert not [k for k in flat if k.startswith(("probe.", "_"))]


def test_flatten_keeps_nulls_because_a_null_must_be_able_to_fail():
    flat = runs_mod.flatten({"context": {"uncached_tokens": None, "error": "no db"}})
    assert flat["context.uncached_tokens"] is None
    assert "context.error" not in flat


# --- the rule vocabulary ----------------------------------------------------


@pytest.mark.parametrize(
    ("rule", "value", "baseline", "ok"),
    [
        ({"min": 30}, 41, None, True),
        ({"min": 30}, 29, None, False),
        ({"max": 12}, 12, None, True),
        ({"max": 12}, 14, None, False),
        ({"equals": True}, True, None, True),
        ({"equals": True}, False, None, False),
        ({"equals": "claude-sonnet-5"}, "claude-sonnet-5", None, True),
        ({"equals": "claude-sonnet-5"}, "claude-sonnet-4-6", None, False),
        ({"min_ratio_to_baseline": 1.5}, 30.0, 20.0, True),
        ({"min_ratio_to_baseline": 1.5}, 29.0, 20.0, False),
        ({"max_ratio_to_baseline": 1.0}, 16, 16, True),
        ({"max_ratio_to_baseline": 1.0}, 17, 16, False),
        ({"ratio_to_baseline_within": 0.05}, 40_000, 40_291, True),
        ({"ratio_to_baseline_within": 0.05}, 30_000, 40_291, False),
    ],
)
def test_rule_vocabulary(rule, value, baseline, ok):
    assert gate_mod.check_rule("k", rule, value, baseline)[0] is ok


def test_a_missing_metric_is_a_failure_never_a_pass():
    """§2a: "not measured" must never be silently green — for every rule shape."""
    for rule in (
        {"min": 30},
        {"max": 12},
        {"equals": True},
        {"min_ratio_to_baseline": 1.5},
        {"min_each": 3.0},
    ):
        ok, _, why = gate_mod.check_rule("k", rule, None, 20.0)
        assert ok is False
        assert "not measured" in why


def test_a_relative_rule_without_a_baseline_fails_rather_than_guessing():
    ok, _, why = gate_mod.check_rule("k", {"min_ratio_to_baseline": 1.5}, 99, None)
    assert ok is False
    assert "baseline" in why


def test_min_each_polices_a_mapping_with_exemptions():
    """Q3's "no format below 3% except chart"."""
    rule = {"min_each": 3.0, "except": ["chart"]}
    assert gate_mod.check_rule("k", rule, {"talk": 40, "chart": 2.1}, None)[0] is True
    ok, _, why = gate_mod.check_rule(
        "k", rule, {"talk": 40, "letters": 1.2, "chart": 2.1}, None
    )
    assert ok is False
    assert "letters" in why and "chart" not in why


# --- guards vs pack overrides -----------------------------------------------


def test_a_pack_rule_overrides_the_global_guard_for_the_same_key():
    """How §2b's "cost ≤ 0.40 until Q2, ≤ 0.12 after" is expressed."""
    gates = {
        "guards": {"cost.usd_per_talk_segment": {"max": 0.40}},
        "packs": {"Q1": {}, "Q2": {"cost.usd_per_talk_segment": {"max": 0.12}}},
    }
    assert gate_mod.rules_for(gates, "Q1")["cost.usd_per_talk_segment"]["max"] == 0.40
    q2 = gate_mod.rules_for(gates, "Q2")["cost.usd_per_talk_segment"]
    assert q2["max"] == 0.12
    assert not q2.get("guard")  # an override is the pack's own rule, not a guard


def test_an_unknown_pack_is_an_error_not_an_empty_pass():
    with pytest.raises(KeyError, match="unknown pack"):
        gate_mod.rules_for({"packs": {"Q0": {}}}, "Q99")


# --- the committed gates.yaml ------------------------------------------------


def test_the_committed_gates_file_covers_every_pack_and_the_2b_guards():
    gates = gate_mod.load_gates()
    assert set(gates["packs"]) == {f"Q{i}" for i in range(9)}
    guards = gates["guards"]
    # The §2b table, transcribed. The contraction floor is 3.5 by operator ruling
    # (2026-07-26) — the metric measures 3.7–5.4 on unchanged code; see gates.yaml.
    assert guards["register.contractions_per_100w"] == {"min": 3.5}
    assert guards["register.banned_abstractions_daytime"] == {"max": 0}
    assert guards["acceptance.properties_passed"] == {"min": 9}
    assert guards["tests.failed"] == {"max": 0}
    # Ratchets upward as packs add tests; never downward (§2b "may not regress").
    assert guards["tests.passed"]["min"] >= 721
    assert guards["cost.usd_per_talk_segment"] == {"max": 0.40}


def test_every_gates_key_is_a_metric_the_harness_can_actually_produce():
    """A threshold on a key nothing emits would be a permanent, meaningless ✗.

    Keys a later pack introduces (`world.items_per_night` in Q1,
    `grid.formats_in_clocks` in Q3) are the deliberate exceptions — they SHOULD fail
    until their pack builds them, so this pins the list; a typo can't hide among them.
    """
    from src.audit.metrics import ALL_GROUP_KEYS

    known = {f"{group}.{key}" for group, keys in ALL_GROUP_KEYS.items() for key in keys}
    not_yet_built = {"world.items_per_night", "grid.formats_in_clocks"}
    gates = gate_mod.load_gates()
    for pack, rules in gates["packs"].items():
        for key in rules:
            base = key.split(".")[0] + "." + key.split(".")[1]
            assert base in known or key in not_yet_built, f"{pack}: unknown key {key}"


def test_every_rule_in_the_committed_file_uses_a_supported_verb():
    supported = {
        "min",
        "max",
        "equals",
        "min_ratio_to_baseline",
        "max_ratio_to_baseline",
        "ratio_to_baseline_within",
        "min_each",
        "except",
        "guard",
    }
    gates = gate_mod.load_gates()
    blocks = [gates["guards"], *gates["packs"].values()]
    for block in blocks:
        for key, rule in block.items():
            unknown = set(rule) - supported
            assert not unknown, f"{key}: unsupported {unknown}"


# --- the end-to-end gate, including its ability to fail ---------------------


def _run(**groups) -> dict:
    return {"collected_at": "2026-07-26T12:00:00", **groups}


@pytest.fixture()
def gated(tmp_path, monkeypatch):
    """A tiny gates file + baseline + head run, wired into settings."""
    gates = {
        "guards": {"register.contractions_per_100w": {"min": 3.5}},
        "packs": {"Q0": {}, "Q1": {"world.active_stories": {"min": 20}}},
    }
    gates_path = tmp_path / "gates.yaml"
    gates_path.write_text(yaml.safe_dump(gates))
    baseline = tmp_path / "2026-07-26-baseline.json"
    baseline.write_text(
        json.dumps(
            _run(world={"active_stories": 23}, register={"contractions_per_100w": 5.4})
        )
    )
    head = tmp_path / "2026-08-02-q1.json"
    head.write_text(
        json.dumps(
            _run(world={"active_stories": 41}, register={"contractions_per_100w": 5.6})
        )
    )
    monkeypatch.setattr(settings, "audit_dir", tmp_path)
    monkeypatch.setattr(settings, "audit_gates_path", gates_path)
    monkeypatch.setattr(settings, "audit_baseline_path", baseline)
    return tmp_path, gates_path, baseline, head


def test_gate_passes_and_exits_zero_when_every_threshold_is_met(gated, capsys):
    assert gate_mod.main(["--pack", "Q1"]) == 0
    out = capsys.readouterr().out
    assert "GATE PASSED" in out
    assert "world.active_stories" in out


def test_a_broken_threshold_makes_the_gate_exit_one(gated, capsys):
    """§2a's proof requirement: a gate that cannot fail is not a gate."""
    tmp_path, gates_path, *_ = gated
    gates = yaml.safe_load(gates_path.read_text())
    gates["packs"]["Q1"]["world.active_stories"] = {"min": 9999}
    gates_path.write_text(yaml.safe_dump(gates))

    assert gate_mod.main(["--pack", "Q1"]) == 1
    out = capsys.readouterr().out
    assert "GATE FAILED" in out
    assert "FAIL" in out


def test_gate_fails_on_a_run_that_never_measured_the_metric(gated, capsys):
    tmp_path, gates_path, _baseline, head = gated
    head.write_text(json.dumps(_run(world={"active_stories": None})))
    assert gate_mod.main(["--pack", "Q1"]) == 1
    assert "not measured" in capsys.readouterr().out


def test_gate_reports_a_bad_pack_name_as_exit_two(gated, capsys):
    """Exit 2 = the gate could not run; it is never confused with a pass."""
    assert gate_mod.main(["--pack", "Q42"]) == 2


# --- the compare table ------------------------------------------------------


def test_comparing_a_run_with_itself_is_all_zero_deltas():
    """Q0.2's own "done when": BASE=baseline HEAD=baseline shows nothing moved.

    Guards are passed in deliberately: a satisfied guard on an unchanged value must
    still read "—". Marking every guarded row ✓ would make the self-compare — the check
    that proves the diff is honest — report movement that did not happen.
    """
    run = _run(
        world={"active_stories": 23, "title_colon_schema_pct": 92.5},
        grid={"format_share": {"talk": 63.5}},
        register={"contractions_per_100w": 4.2, "banned_abstractions_daytime": 0},
        cost={"usd_per_talk_segment": 0.3722},
    )
    guards = {
        "register.contractions_per_100w": {"min": 3.5},
        "register.banned_abstractions_daytime": {"max": 0},
        "cost.usd_per_talk_segment": {"max": 0.40},
    }
    rows = compare_mod.compare(run, run, guards=guards)
    assert rows
    assert all(r.delta in (0, None) for r in rows)
    assert [r.key for r in rows if r.marker != "—"] == []


def test_a_breached_guard_is_flagged_even_when_the_value_did_not_move():
    """The other half of that precedence: unchanged-but-failing is still a ✗."""
    run = _run(register={"contractions_per_100w": 2.0})
    guards = {"register.contractions_per_100w": {"min": 3.5}}
    row = next(iter(compare_mod.compare(run, run, guards=guards)))
    assert row.marker == "✗"
    assert "guard" in row.note


def test_compare_shows_deltas_and_flags_a_guard_regression():
    base = _run(world={"active_stories": 23}, register={"contractions_per_100w": 5.4})
    head = _run(world={"active_stories": 41}, register={"contractions_per_100w": 2.0})
    guards = {"register.contractions_per_100w": {"min": 3.5}}
    by_key = {r.key: r for r in compare_mod.compare(base, head, guards=guards)}

    assert by_key["world.active_stories"].delta == 18
    assert by_key["world.active_stories"].marker == "✓"
    assert by_key["register.contractions_per_100w"].marker == "✗"
    assert "guard" in by_key["register.contractions_per_100w"].note


def test_compare_flags_a_metric_head_stopped_measuring():
    base = _run(context={"uncached_tokens": 28342})
    head = _run(context={"uncached_tokens": None})
    row = next(
        r for r in compare_mod.compare(base, head) if r.key == "context.uncached_tokens"
    )
    assert row.marker == "✗"
    assert "did not measure" in row.note


# --- run resolution ---------------------------------------------------------


def test_runs_resolve_by_short_label_and_newest_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audit_dir", tmp_path)
    old = tmp_path / "2026-07-01-q1.json"
    new = tmp_path / "2026-08-02-q1.json"
    for p in (old, new):
        p.write_text("{}")
    import os
    import time

    os.utime(old, (time.time() - 100, time.time() - 100))
    assert runs_mod.resolve_run("q1") == new
    assert runs_mod.resolve_run(str(old)) == old
    with pytest.raises(FileNotFoundError, match="no audit run matching"):
        runs_mod.resolve_run("nope")


def test_newest_run_can_exclude_the_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "audit_dir", tmp_path)
    baseline = tmp_path / "2026-07-26-baseline.json"
    baseline.write_text("{}")
    assert runs_mod.newest_run() == baseline
    with pytest.raises(FileNotFoundError):
        runs_mod.newest_run(exclude=baseline)


# --- the §2b check parsers --------------------------------------------------


def test_pytest_summary_parsing():
    from src.audit.checks import _parse_pytest

    assert _parse_pytest("686 passed, 1 warning in 70.89s")["passed"] == 686
    both = _parse_pytest("2 failed, 684 passed, 1 skipped in 71s")
    assert (both["failed"], both["passed"], both["skipped"]) == (2, 684, 1)
    assert _parse_pytest("no summary here") == {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
    }

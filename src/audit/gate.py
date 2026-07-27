"""Q0.2 — `make gate PACK=Qn`: the check that fails by itself, with no one's opinion.

PHASE_Q_TASKS.md §2a: *"That is the answer — not the agent's summary of it."* This
module reads the committed thresholds in `docs/audit/gates.yaml`, evaluates them against
an audit run, prints a pass/fail table and **exits non-zero on any miss**. It is the one
place in Phase Q where a pack is declared done, and it cannot see anybody's judgement.

Two rules it exists to enforce (§2a, §2d):

1. **A missing or null metric is a FAIL, never a pass.** "Not measured" must never be
   silently green — so gating on a free-only run fails the probe-measured thresholds,
   and gating before a pack has built its metric fails that pack. Both are correct.
2. **A gate is never "passed on balance".** Any ✗ means the pack is not done. The
   operator may still choose "accept and record", but that is a human writing it in the
   DEVLOG, not this module rounding up.

Rule vocabulary (everything §3 needs, and nothing more):

    {min: 30}                      value >= 30
    {max: 12}                      value <= 12
    {equals: true}                 value == true
    {min_ratio_to_baseline: 1.5}   value >= 1.5 x the committed baseline's value
    {max_ratio_to_baseline: 1.0}   value <= 1.0 x baseline (i.e. "unchanged or lower")
    {ratio_to_baseline_within: 0.05}   |value/baseline - 1| <= 0.05  ("within +/-5%")
    {min_each: 3.0, except: [chart]}   every entry of a mapping >= 3.0, bar those named

A pack block's rule for a key overrides the global guard for that key (that is how §2b's
`cost.usd_per_talk_segment <= 0.40 until Q2, <= 0.12 after` is expressed).

    make gate PACK=Q0 ; echo "exit=$?"
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..config import settings
from ..logging_setup import get_logger
from .cli import logs_to_stderr
from .runs import flatten, load_run, newest_run, resolve_run

log = get_logger(__name__)


@dataclass(frozen=True)
class Check:
    """One threshold's verdict."""

    key: str
    value: object
    expected: str
    ok: bool
    guard: bool
    why: str = ""


def load_gates(path: Path | None = None) -> dict:
    """Read `docs/audit/gates.yaml` (the committed thresholds)."""
    p = path or settings.audit_gates_path
    if not p.is_file():
        raise FileNotFoundError(f"no gates file at {p} — Q0.2 commits it")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def rules_for(gates: dict, pack: str) -> dict[str, dict]:
    """The rules that apply to `pack`: the global guards, with its own block on top."""
    packs = gates.get("packs") or {}
    if pack not in packs:
        raise KeyError(
            f"unknown pack {pack!r}; gates.yaml defines "
            + (", ".join(sorted(packs)) or "none")
        )
    # A guard-sourced rule is tagged so the table can mark it; a pack block overriding
    # the same key replaces it outright (that is how §2b's "≤ 0.40 until Q2, ≤ 0.12
    # after" is written), and the override is the pack's own rule, not a guard.
    merged = {k: {**v, "guard": True} for k, v in (gates.get("guards") or {}).items()}
    merged.update(packs.get(pack) or {})
    return merged


def check_rule(
    key: str, rule: dict, value: object, baseline: float | None
) -> tuple[bool, str, str]:
    """Evaluate one rule. Returns `(ok, expected_text, why_not)`.

    A `None` value fails everything: §2a's "a metric that is missing from the audit JSON
    counts as FAIL". A relative rule with no baseline value also fails — it cannot be
    judged, and "cannot judge" is not "fine".
    """
    if "min_each" in rule:
        return _check_min_each(rule, value)

    expected = _expected_text(rule, baseline)
    if value is None:
        return False, expected, "not measured"

    if "equals" in rule:
        return value == rule["equals"], expected, f"is {value!r}"

    number = _numeric(value)
    if number is None:
        return False, expected, f"not a number ({value!r})"

    if "min" in rule and number < float(rule["min"]):
        return False, expected, f"is {number:g}"
    if "max" in rule and number > float(rule["max"]):
        return False, expected, f"is {number:g}"

    relative = {
        "min_ratio_to_baseline",
        "max_ratio_to_baseline",
        "ratio_to_baseline_within",
    }
    if relative & rule.keys():
        if not baseline:
            return False, expected, "no baseline value to compare against"
        ratio = number / baseline
        low = float(rule.get("min_ratio_to_baseline", 0))
        high = float(rule.get("max_ratio_to_baseline", float("inf")))
        if ratio < low or ratio > high:
            return False, expected, f"is {ratio:.2f}x baseline ({baseline:g})"
        if "ratio_to_baseline_within" in rule:
            if abs(ratio - 1.0) > float(rule["ratio_to_baseline_within"]):
                return False, expected, f"is {ratio:.3f}x baseline ({baseline:g})"
    return True, expected, ""


def _check_min_each(rule: dict, value: object) -> tuple[bool, str, str]:
    """ "No entry of this mapping below N (bar these)" — Q3's format-share floor."""
    floor = float(rule["min_each"])
    exempt = {str(e) for e in (rule.get("except") or [])}
    expected = f"each ≥ {floor:g}" + (f" except {sorted(exempt)}" if exempt else "")
    if not isinstance(value, dict):
        why = "not measured" if value is None else "not a mapping"
        return False, expected, why
    low = {
        k: v
        for k, v in value.items()
        if k not in exempt and (_numeric(v) is None or _numeric(v) < floor)
    }
    return (
        not low,
        expected,
        ("below: " + ", ".join(f"{k}={v}" for k, v in low.items())),
    )


def _numeric(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    return float(value) if isinstance(value, int | float) else None


def _expected_text(rule: dict, baseline: float | None) -> str:
    parts = []
    if "min" in rule:
        parts.append(f"≥ {rule['min']}")
    if "max" in rule:
        parts.append(f"≤ {rule['max']}")
    if "equals" in rule:
        parts.append(f"= {rule['equals']}")
    base = f" (baseline {baseline:g})" if baseline else ""
    if "min_ratio_to_baseline" in rule:
        parts.append(f"≥ {rule['min_ratio_to_baseline']}× baseline{base}")
    if "max_ratio_to_baseline" in rule:
        parts.append(f"≤ {rule['max_ratio_to_baseline']}× baseline{base}")
    if "ratio_to_baseline_within" in rule:
        parts.append(
            f"within ±{float(rule['ratio_to_baseline_within']) * 100:g}%{base}"
        )
    return " and ".join(parts) or "?"


def evaluate(rules: dict[str, dict], head: dict, baseline: dict) -> list[Check]:
    """Run every rule against the HEAD run, ordered guards last so fixes read first."""
    flat_head, flat_base = flatten(head), flatten(baseline)
    checks: list[Check] = []
    for key, rule in rules.items():
        ok, expected, why = check_rule(
            key, rule, flat_head.get(key), _numeric(flat_base.get(key))
        )
        checks.append(
            Check(key, flat_head.get(key), expected, ok, bool(rule.get("guard")), why)
        )
    return sorted(checks, key=lambda c: (c.guard, c.key))


def render(checks: list[Check], *, pack: str, head: Path, baseline: Path) -> str:
    """The pass/fail table — the shape §2a specifies."""
    lines = [f"{pack} GATE  ({head.name} vs {baseline.name})"]
    for c in checks:
        mark = "✓" if c.ok else "✗"
        value = "—" if c.value is None else _short(c.value)
        tail = "  guard" if c.guard else ""
        fail = f"   FAIL ({c.why})" if not c.ok else ""
        lines.append(
            f"  {mark} {c.key:<42s} {value:>10s}  {c.expected:<26s}{tail}{fail}"
        )
    misses = [c for c in checks if not c.ok]
    if misses:
        lines.append(f"GATE FAILED — {len(misses)} of {len(checks)} checks.  exit 1")
    else:
        lines.append(f"GATE PASSED — {len(checks)} of {len(checks)} checks.  exit 0")
    return "\n".join(lines)


def _short(value: object) -> str:
    if isinstance(value, dict):
        return "{" + ",".join(f"{k}:{v}" for k, v in list(value.items())[:3]) + "}"
    if isinstance(value, list):
        return f"[{len(value)}]"
    return str(value)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.audit.gate", description=__doc__
    )
    parser.add_argument("--pack", required=True, help="which pack's gate (e.g. Q1)")
    parser.add_argument(
        "--head", help="run path or label to judge (default: the newest run)"
    )
    parser.add_argument("--gates", help="override the gates.yaml path")
    parser.add_argument(
        "--baseline", help="override the committed baseline used by relative rules"
    )
    args = parser.parse_args(argv)

    logs_to_stderr()

    try:
        gates = load_gates(Path(args.gates) if args.gates else None)
        rules = rules_for(gates, args.pack)
        baseline_path = (
            resolve_run(args.baseline)
            if args.baseline
            else settings.audit_baseline_path
        )
        head_path = (
            resolve_run(args.head) if args.head else newest_run(exclude=baseline_path)
        )
    except (FileNotFoundError, KeyError) as exc:
        print(f"gate: {exc}", file=sys.stderr)
        return 2

    baseline = load_run(baseline_path) if baseline_path.is_file() else {}
    if not baseline:
        log.warning("audit_gate_no_baseline", path=str(baseline_path))
    checks = evaluate(rules, load_run(head_path), baseline)
    print(render(checks, pack=args.pack, head=head_path, baseline=baseline_path))
    failed = [c.key for c in checks if not c.ok]
    log.info("audit_gate_done", pack=args.pack, checks=len(checks), failed=failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

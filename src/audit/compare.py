"""Q0.2 — `make audit-compare`: two audit runs, one delta table.

The descriptive half of the feedback loop (§2a). It answers "what moved?" and nothing
else — no verdict on whether the movement was good, except where a §2b guard says a
direction is forbidden. The *judging* half is `gate.py`; only that one has an exit code.

Marker column:

  * `—` the metric did not move (or was unmeasured in both runs)
  * `✓` it moved, and no guard objects
  * `✗` a §2b guard applies and HEAD fails it — or HEAD stopped measuring something BASE
    had measured, which is the same kind of problem wearing a different hat

    make audit-compare BASE=baseline HEAD=q1
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from ..logging_setup import get_logger
from . import gate as gate_mod
from .cli import logs_to_stderr
from .runs import flatten, load_run, resolve_run

log = get_logger(__name__)


@dataclass(frozen=True)
class Row:
    """One metric across two runs."""

    key: str
    base: object
    head: object
    delta: float | None
    marker: str
    note: str = ""


def _numeric(value: object) -> float | None:
    """The value as a float, or None when it isn't a number (a bool is not a number)."""
    if isinstance(value, bool) or value is None:
        return None
    return float(value) if isinstance(value, int | float) else None


def compare(base: dict, head: dict, *, guards: dict | None = None) -> list[Row]:
    """One row per metric in either run, ordered by key."""
    guards = guards or {}
    flat_base, flat_head = flatten(base), flatten(head)
    rows: list[Row] = []
    for key in sorted(set(flat_base) | set(flat_head)):
        b, h = flat_base.get(key), flat_head.get(key)
        nb, nh = _numeric(b), _numeric(h)
        delta = round(nh - nb, 4) if nb is not None and nh is not None else None
        note = ""
        guard_ok: bool | None = None
        if key in guards:
            guard_ok, expected, why = gate_mod.check_rule(key, guards[key], h, nb)
            note = f"guard {expected}" + (f" — {why}" if why and not guard_ok else "")
        # A breached guard is a ✗ whether or not the value moved. Otherwise "did it
        # move?" decides — so comparing a run with ITSELF is all dashes, guards
        # included, which is what makes the self-compare a meaningful sanity check.
        if guard_ok is False:
            marker = "✗"
        elif h is None and b is not None:
            marker, note = "✗", "HEAD did not measure it"
        elif b == h:
            marker = "—"
        else:
            marker = "✓"
        rows.append(Row(key, b, h, delta, marker, note))
    return rows


def _cell(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}={v}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def render(rows: list[Row], *, base_name: str, head_name: str) -> str:
    """The delta table."""
    lines = [
        f"AUDIT COMPARE  ({head_name}  vs  {base_name})",
        f"  {'metric':<44s} {'base':>16s} {'head':>16s} {'delta':>11s}",
    ]
    for r in rows:
        delta = "" if r.delta is None else f"{r.delta:+g}"
        lines.append(
            f"{r.marker} {r.key:<44s} {_cell(r.base)[:16]:>16s} "
            f"{_cell(r.head)[:16]:>16s} {delta:>11s}"
            + (f"   {r.note}" if r.note else "")
        )
    moved = sum(1 for r in rows if r.marker != "—")
    failed = sum(1 for r in rows if r.marker == "✗")
    lines.append("")
    lines.append(
        f"{len(rows)} metrics · {moved} moved · {failed} guard failure(s)."
        " `make gate PACK=Qn` is what decides a pack."
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.audit.compare", description=__doc__
    )
    parser.add_argument(
        "--base", required=True, help="run path or label (e.g. baseline)"
    )
    parser.add_argument("--head", required=True, help="run path or label (e.g. q1)")
    args = parser.parse_args(argv)

    logs_to_stderr()
    try:
        base_path, head_path = resolve_run(args.base), resolve_run(args.head)
    except FileNotFoundError as exc:
        print(f"audit-compare: {exc}", file=sys.stderr)
        return 2

    guards = gate_mod.load_gates().get("guards") or {}
    rows = compare(load_run(base_path), load_run(head_path), guards=guards)
    print(render(rows, base_name=base_path.name, head_name=head_path.name))
    # Descriptive by design: the exit code belongs to `make gate`, not to a diff.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

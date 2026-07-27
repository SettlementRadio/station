"""Loading and flattening audit runs — the layer `compare` and `gate` share.

An audit run on disk is `docs/audit/<YYYY-MM-DD>-<label>.json`, a dict of groups. Both
the compare table and the gate need the same three things from it: find a run by a short
name, read it, and flatten it into the dotted keys the pack's thresholds are written in
(`world.active_stories`, `grid.format_share.talk`).

**Dotted keys are the gate's vocabulary.** `docs/audit/gates.yaml` is written against
them, `PHASE_Q_TASKS.md` §3 quotes them, and Q8 reads them by name — so flattening
has to be boring and total: every leaf reachable, nothing renamed, a nested dict
reachable both as its own key (for whole-dict rules) and one level down.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger

log = get_logger(__name__)

# Keys that are run bookkeeping, not measurements: excluded from the compare table and
# never gate-able. `probe` records what the run *did* (wall time, estimated spend, which
# beat each slot picked) — real diagnostics, but they change every run by design, and a
# diff that flags them buries the metrics that matter.
_NON_METRIC_GROUPS = frozenset({"probe"})


def resolve_run(spec: str, *, directory: Path | None = None) -> Path:
    """Find a run from a path or a short label — `baseline`, `q1`, or a full path.

    So the operator can type `make audit-compare BASE=baseline HEAD=q1` instead of two
    dated paths. A label matches on the filename's `-<label>.json` tail; the newest wins
    if several days carry the same label.
    """
    direct = Path(spec)
    if direct.is_file():
        return direct
    directory = directory or settings.audit_dir
    matches = sorted(
        directory.glob(f"*-{spec}.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not matches:
        raise FileNotFoundError(
            f"no audit run matching {spec!r} in {directory} (have: "
            + (", ".join(sorted(p.name for p in directory.glob("*.json"))) or "none")
            + ")"
        )
    return matches[0]


def newest_run(*, directory: Path | None = None, exclude: Path | None = None) -> Path:
    """The most recently written run — what `make gate` judges when given no HEAD."""
    directory = directory or settings.audit_dir
    runs = [
        p
        for p in directory.glob("*.json")
        if exclude is None or p.resolve() != exclude.resolve()
    ]
    if not runs:
        raise FileNotFoundError(f"no audit runs in {directory} — run `make audit-full`")
    return max(runs, key=lambda p: p.stat().st_mtime)


def load_run(path: Path) -> dict:
    """Read one run's JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def flatten(data: dict) -> dict[str, object]:
    """A run as dotted metric keys — the form gates.yaml and §3 are written in.

    A nested dict (`grid.format_share`) appears BOTH as `grid.format_share` (so a rule
    can speak about the whole mapping, e.g. "no format below 3%") and as
    `grid.format_share.talk` per entry. `error` markers and the non-metric groups are
    dropped; a group that degraded to nulls keeps its keys, because a null must be
    visible in order to FAIL.
    """
    out: dict[str, object] = {}
    for group, body in data.items():
        if group.startswith("_") or group in _NON_METRIC_GROUPS:
            continue
        if not isinstance(body, dict):
            continue  # top-level scalars (collected_at, reference_now) aren't metrics
        for key, value in body.items():
            if key == "error":
                continue
            dotted = f"{group}.{key}"
            out[dotted] = value
            if isinstance(value, dict):
                for sub, sub_value in value.items():
                    out[f"{dotted}.{sub}"] = sub_value
    return out


def baseline_path() -> Path:
    """The committed baseline — the anchor every relative threshold is measured from."""
    return settings.audit_baseline_path


__all__ = [
    "baseline_path",
    "flatten",
    "load_run",
    "newest_run",
    "resolve_run",
]

"""The two §2b guards that are facts about the repo, not measurements of the world.

`acceptance.properties_passed` and `tests.passed` are listed in PHASE_Q_TASKS.md §2b as
guards checked on *every* pack, and the pack's own `gates.yaml` sketch asserts on
`acceptance.properties_passed` — so the gate has to be able to see them. They are not
readable from the DB or the grid, so they get their own group here:

  * **acceptance** — `run_acceptance()` called directly (both provider seams mocked, so
    it is free and makes no API calls), reading `.results` rather than parsing stdout.
  * **tests** — `pytest -q` in a subprocess, its summary line parsed.

Both are minutes, not seconds, which is why they are opt-in (`--with-checks`, implied by
`--full`) and stay out of the seconds-long `make audit`. That has a consequence worth
being explicit about: **a free-only run reports them as `null`, and a gate reads null as
FAIL.** That is correct, not a bug — a pack should not be declared green by a run that
never checked whether the tests pass.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger

log = get_logger(__name__)

# pytest's summary line: "686 passed, 1 warning in 70.89s" / "2 failed, 684 passed…".
_PYTEST_COUNT = re.compile(r"(\d+) (passed|failed|error|errors|skipped)")


def acceptance_metrics(hours: float | None = None) -> dict:
    """Run the D11.3 acceptance simulation and report its verdict count (§2b, §1g).

    Free: `acceptance` mocks `llm.generate` and TTS, so this spends nothing. It measures
    mechanism, not writing — §1g explains why that is a different question from the rest
    of the audit, and why the audit reports it alongside rather than folding it in.

    Runs the sim in `acceptance.CLI_DEFAULTS` shape — exactly what `make acceptance`
    runs. That matters: the function's own keyword defaults use a 24h tick cadence, too
    little story advancement for `stories_evolve`, which reports 8/9 on a station the
    CLI calls green. The guard must measure the same thing the operator runs.
    """
    from .. import acceptance as acceptance_mod

    shape = dict(acceptance_mod.CLI_DEFAULTS)
    if hours is not None:
        shape["window_hours"] = hours
    elif settings.audit_acceptance_hours:
        shape["window_hours"] = settings.audit_acceptance_hours
    hours = shape["window_hours"]
    report = acceptance_mod.run_acceptance(**shape)
    passed = sum(1 for r in report.results if r.ok)
    failed = [r.name for r in report.results if not r.ok]
    return {
        "properties_passed": passed,
        "properties_total": len(report.results),
        "properties_failed": failed,
        "window_hours": hours,
    }


def test_metrics(repo_root: Path | None = None) -> dict:
    """Run the test suite and report the counts (§2b: `tests.passed` may not fall)."""
    root = repo_root or Path(__file__).resolve().parent.parent.parent
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=settings.audit_checks_timeout_sec,
        check=False,
    )
    counts = _parse_pytest(proc.stdout + proc.stderr)
    log.info("audit_tests_measured", exit_code=proc.returncode, **counts)
    return {**counts, "exit_code": proc.returncode}


def _parse_pytest(output: str) -> dict:
    """Pull passed/failed/error counts out of pytest's summary line."""
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    # Scan every match in the tail: the summary line is last, but a progress line can
    # carry the same shape, so later matches win.
    for count, kind in _PYTEST_COUNT.findall(output):
        key = "errors" if kind.startswith("error") else kind
        counts[key] = int(count)
    return counts


def collect_checks(*, acceptance: bool = True, tests: bool = True) -> dict:
    """The `acceptance.*` and `tests.*` groups. Slow (minutes), free (no API calls).

    A check that cannot run (no Postgres for the acceptance sim) degrades to nulls plus
    an `error`, exactly like a free group — so it reads "not measured", never "passing".
    """
    out: dict = {}
    if acceptance:
        try:
            out["acceptance"] = acceptance_metrics()
        except Exception as exc:  # noqa: BLE001 — a missing DB is a measurement outcome
            log.warning("audit_acceptance_unavailable", error=str(exc))
            out["acceptance"] = {
                "properties_passed": None,
                "properties_total": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
    if tests:
        try:
            out["tests"] = test_metrics()
        except Exception as exc:  # noqa: BLE001
            log.warning("audit_tests_unavailable", error=str(exc))
            out["tests"] = {
                "passed": None,
                "failed": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
    return out


__all__ = ["acceptance_metrics", "collect_checks", "test_metrics"]

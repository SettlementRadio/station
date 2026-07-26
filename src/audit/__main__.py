"""CLI for the audit harness (Q0.0): print the table, write the run's JSON.

    make audit                      # free metrics -> docs/audit/<date>-free.json
    make audit LABEL=baseline       # ... -> docs/audit/<date>-baseline.json
    .venv/bin/python -m src.audit --json --no-write --now 2026-07-27T12:00

Pure reads — safe to run against a live station. Exits 0 even when a group degrades to
`null` (an unreachable DB is a measurement, not a harness failure); the gate (Q0.2) is
what turns a null into a non-zero exit.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import structlog

from ..config import settings
from ..logging_setup import configure_logging, get_logger
from .metrics import collect_free, render_table

log = get_logger(__name__)


def _logs_to_stderr() -> None:
    """Route this CLI's structured logs to stderr so stdout is only the report.

    The station's logger prints JSON lines to stdout (right for an unattended 24/7
    process); here stdout carries the audit itself, and `--json` has to be pipeable
    into `jq`. Local to this entry point — nothing else's logging changes.
    """
    configure_logging()
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))


def write_run(data: dict, label: str, *, out_dir: Path | None = None) -> Path:
    """Write one audit run to `<audit_dir>/<YYYY-MM-DD>-<label>.json` and return it."""
    directory = out_dir or settings.audit_dir
    directory.mkdir(parents=True, exist_ok=True)
    day = str(data.get("collected_at") or datetime.now().isoformat())[:10]
    path = directory / f"{day}-{label}.json"
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    log.info("audit_run_written", path=str(path), label=label)
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.audit", description=__doc__)
    parser.add_argument(
        "--label",
        default="free",
        help="names the run's JSON file (docs/audit/<date>-<label>.json)",
    )
    parser.add_argument(
        "--now",
        help="pin the reference clock (ISO) instead of noon today — for reproduction",
    )
    parser.add_argument("--json", action="store_true", help="print JSON, not the table")
    parser.add_argument(
        "--no-write", action="store_true", help="print only; write no JSON file"
    )
    args = parser.parse_args(argv)

    _logs_to_stderr()
    now = datetime.fromisoformat(args.now) if args.now else None
    data = collect_free(now)

    print(json.dumps(data, indent=2, default=str) if args.json else render_table(data))
    if not args.no_write:
        path = write_run(data, args.label)
        print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

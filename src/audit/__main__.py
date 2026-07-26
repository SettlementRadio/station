"""CLI for the audit harness: print the table, write the run's JSON.

    make audit                      # free metrics -> docs/audit/<date>-free.json
    make audit LABEL=baseline       # ... -> docs/audit/<date>-baseline.json
    make audit-full LABEL=q1        # + the API probe (real Anthropic calls)
    make audit-full DRY=1           # print the probe plan + estimate, spend nothing
    .venv/bin/python -m src.audit --json --no-write --now 2026-07-27T12:00

`--full` adds the Q0.1 probe: real generation, TTS mocked, every DB write rolled back.
It prints its estimated spend before starting. Without `--full` the run is free and pure
reads, safe against a live station.

Exits 0 even when a group degrades to `null` (an unreachable DB is a measurement, not a
harness failure); the gate (Q0.2) is what turns a null into a non-zero exit.
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
from .metrics import collect_free, merge_probe, render_table

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


def write_transcripts(segments: list[dict], json_path: Path) -> Path:
    """Dump the probe's scripts beside its JSON — for a spot-check or a blind read.

    Deliberately a sibling `.txt` rather than a field in the JSON: the scripts are large
    and change every run, and the JSON is a metrics artifact that gets diffed and
    committed.
    """
    from .probe import transcripts

    path = json_path.with_suffix(".transcripts.txt")
    path.write_text(transcripts(segments), encoding="utf-8")
    log.info("audit_transcripts_written", path=str(path), segments=len(segments))
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m src.audit", description=__doc__)
    parser.add_argument(
        "--label",
        help="names the run's JSON file (docs/audit/<date>-<label>.json); "
        "defaults to 'free', or 'full' with --full",
    )
    parser.add_argument(
        "--now",
        help="pin the reference clock (ISO) instead of noon today — for reproduction",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="also run the API probe (real Anthropic calls; TTS mocked; rolled back)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="runs of the fixed slot list (2 = the cross-run comparison; --full only)",
    )
    parser.add_argument(
        "--no-continuity",
        action="store_true",
        help="skip the probe's 5-slot continuity run (--full only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="with --full: print the probe plan + spend estimate and spend nothing",
    )
    parser.add_argument("--json", action="store_true", help="print JSON, not the table")
    parser.add_argument(
        "--no-write", action="store_true", help="print only; write no JSON file"
    )
    args = parser.parse_args(argv)

    _logs_to_stderr()
    now = datetime.fromisoformat(args.now) if args.now else None
    data = collect_free(now)

    segments: list[dict] = []
    if args.full:
        from .probe import collect_probe

        probe = collect_probe(
            args.runs, dry_run=args.dry_run, continuity=not args.no_continuity
        )
        segments = probe.pop("_segments", [])
        data = merge_probe(data, probe)

    print(json.dumps(data, indent=2, default=str) if args.json else render_table(data))
    if not args.no_write:
        label = args.label or ("full" if args.full else "free")
        path = write_run(data, label)
        print(f"\nwrote {path}")
        if segments:
            print(f"wrote {write_transcripts(segments, path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

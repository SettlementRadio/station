"""Shared CLI plumbing for the audit commands.

One job: keep the station's structured logs off stdout while an audit command runs, so
that stdout carries only the report and `--json` can be piped into `jq`. The station's
logger prints JSON lines to stdout, which is right for an unattended 24/7 process and
wrong for a command whose output *is* the artifact.

The factory is deliberately **lazy** — it resolves `sys.stderr` at each log call rather
than capturing it once. Binding it eagerly (`PrintLoggerFactory(file=sys.stderr)`) holds
a reference to whatever stream was installed at configure time, which explodes with
"I/O operation on closed file" the moment anything swaps that stream out underneath it
(pytest's capture does exactly that, once per test).
"""

from __future__ import annotations

import sys

import structlog

from ..logging_setup import configure_logging


def _stderr_logger(*_args, **_kwargs) -> structlog.PrintLogger:
    """A logger writing to whatever `sys.stderr` is at the moment of the call."""
    return structlog.PrintLogger(file=sys.stderr)


def logs_to_stderr() -> None:
    """Send this process's structured logs to stderr. Call once, at an entry point."""
    configure_logging()
    structlog.configure(
        logger_factory=_stderr_logger,
        # Re-resolve per call; a cached bound logger would pin one stream again.
        cache_logger_on_first_use=False,
    )


__all__ = ["logs_to_stderr"]

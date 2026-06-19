"""Structured logging, configured once for the whole station backend.

CLAUDE.md "Engineering standards": structured logging, never `print()`. This is
how you diagnose a 3 a.m. failure you didn't watch — every external call and
batch step logs start/outcome. We use `structlog` rendering JSON by default (for
an unattended 24/7 process whose logs are grepped/shipped), with a console-pretty
mode for local dev (`LOG_JSON=false`).

Usage:

    from .logging_setup import configure_logging, get_logger
    configure_logging()          # idempotent; call once at an entry point
    log = get_logger(__name__)
    log.info("segment_start", seg_id=seg_id, fmt="talk")
"""

from __future__ import annotations

import logging

import structlog

from .config import settings

_configured = False


def configure_logging() -> None:
    """Configure structlog + stdlib logging once. Safe to call repeatedly.

    Reads the level and JSON/console choice from `settings`. Subsequent calls are
    no-ops, so library entry points can each call it without fighting over config.
    """
    global _configured
    if _configured:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=level)

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger, configuring logging on first use if needed."""
    if not _configured:
        configure_logging()
    return structlog.get_logger(name)

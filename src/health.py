"""C4 — health checks + alerts: catch a stalled stream / drained buffer / dead run.

The fallback chain (config/radio.liq + src/fallback.py) keeps the AIR alive through
a single failure; these checks make that failure VISIBLE so a human — or an uptime
service — knows to intervene before the buffer is gone for good. Three independent
checks, each a pure read (no generation, no Claude/TTS):

  - buffer depth   — is the scheduler's upcoming runway above a safe floor
                     (`health_min_runway_minutes`)?
  - generation run — did a top-up complete recently? The scheduler writes a
                     `last_topup_at` heartbeat into the schedule state on every
                     run; if it's older than `health_max_run_age_minutes`, or
                     missing, the generator isn't running.
  - stream liveness— is the Icecast mount reachable (optional; needs
                     `health_stream_url`)?

On ANY issue: log at error AND, if configured, POST to `health_alert_webhook_url`
and ping `health_ping_url` failure. On a CLEAN pass: ping `health_ping_url` success
— a healthchecks.io-style dead-man's switch, so a scheduler/health timer that stops
running ENTIRELY (no heartbeat, no ping) is itself caught externally. The two
detectors are complementary: `last_topup_at` catches "the job isn't running" while
the buffer/stream checks catch "the job runs but the air is at risk".

Run on a cadence (cron/systemd in C5) via `python -m src.health` / `make health`;
the exit code is non-zero when unhealthy so a monitor can act on it. All alert URLs
default empty (log-only) — set them in `.env` on the VPS.
"""

from __future__ import annotations

import sys
from datetime import datetime

import requests

from .config import settings
from .logging_setup import get_logger
from .scheduler import _end_of, _load_state

log = get_logger(__name__)


def _runway_seconds(now: datetime) -> tuple[float, int]:
    """Upcoming un-aired audio depth (seconds) + segment count from the live schedule.

    Mirrors the scheduler's runway calc (segments are placed back-to-back, so the
    span to the last entry's end IS the queued audio depth), reusing its state +
    end-of-entry helpers so the two never disagree.
    """
    state = _load_state()
    upcoming = [
        e for e in state.get("entries", []) if e.get("air_time") and _end_of(e) > now
    ]
    if not upcoming:
        return 0.0, 0
    runway = (max(_end_of(e) for e in upcoming) - now).total_seconds()
    return max(runway, 0.0), len(upcoming)


def check_buffer(now: datetime) -> str | None:
    """Flag when the rolling buffer's runway has fallen below the safe floor."""
    runway, n = _runway_seconds(now)
    floor_min = settings.health_min_runway_minutes
    if runway < floor_min * 60:
        return (
            f"low buffer: {runway / 60:.1f} min of audio queued ({n} segment(s)), "
            f"below the {floor_min:.0f} min floor"
        )
    return None


def check_last_run(now: datetime) -> str | None:
    """Flag when no scheduler top-up has completed within the allowed window.

    Reads the `last_topup_at` heartbeat the scheduler writes into the schedule
    state on every run — the detector for "the generator stopped running at all"
    (a crashed/disabled cron, a hung process, a rebooted-but-not-restarted box).
    """
    last = _load_state().get("last_topup_at")
    if not last:
        return "no scheduler run recorded yet (last_topup_at missing)"
    try:
        age_sec = (now - datetime.fromisoformat(last)).total_seconds()
    except ValueError:
        return f"unparseable last_topup_at: {last!r}"
    limit_min = settings.health_max_run_age_minutes
    if age_sec > limit_min * 60:
        return (
            f"stale generation: last top-up {age_sec / 60:.0f} min ago, "
            f"over the {limit_min:.0f} min limit"
        )
    return None


def check_stream() -> str | None:
    """Flag when the configured stream mount is unreachable (optional check)."""
    url = settings.health_stream_url.strip()
    if not url:
        return None  # no URL configured -> skip the stream check
    try:
        resp = requests.get(
            url, timeout=settings.health_request_timeout_sec, stream=True
        )
        status = resp.status_code
        resp.close()
    except requests.RequestException as exc:
        return f"stream unreachable at {url}: {exc}"
    if status != 200:
        return f"stream unhealthy at {url}: HTTP {status}"
    return None


def _post_webhook(message: str) -> None:
    """POST an alert to `health_alert_webhook_url` if set (Slack/Discord/generic)."""
    url = settings.health_alert_webhook_url.strip()
    if not url:
        return
    try:
        requests.post(
            url, json={"text": message}, timeout=settings.health_request_timeout_sec
        )
    except requests.RequestException as exc:
        log.error("health_webhook_failed", error=str(exc))


def _ping(url: str, *, suffix: str = "") -> None:
    """Best-effort GET of an uptime ping URL (healthchecks.io-style)."""
    if not url:
        return
    try:
        requests.get(
            url.rstrip("/") + suffix, timeout=settings.health_request_timeout_sec
        )
    except requests.RequestException as exc:
        log.warning("health_ping_failed", url=url, suffix=suffix, error=str(exc))


def run_checks(now: datetime | None = None) -> list[str]:
    """Run every health check; alert on any issue, ping success on a clean pass.

    Returns the list of issue messages (empty = healthy), so callers/tests can
    assert on the outcome without parsing logs.
    """
    now = now or datetime.now()
    issues = [
        msg for msg in (check_buffer(now), check_last_run(now), check_stream()) if msg
    ]
    if issues:
        log.error("health_alert", issues=issues)
        _post_webhook("Settlement Radio health alert: " + "; ".join(issues))
        _ping(settings.health_ping_url, suffix="/fail")
    else:
        log.info("health_ok")
        _ping(settings.health_ping_url)
    return issues


def main(argv: list[str]) -> int:
    """CLI: run the checks, print a summary, exit non-zero when unhealthy."""
    issues = run_checks()
    print("\n----- HEALTH CHECK (C4) -----")
    if not issues:
        print("  ✓ all checks passed (buffer depth, last run, stream)")
        return 0
    for issue in issues:
        print(f"  ✗ {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

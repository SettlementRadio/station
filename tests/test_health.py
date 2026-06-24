"""Tests for the C4 health checks + alerts (src/health.py).

The promise: read the live schedule + stream and make a failure VISIBLE — flag a
drained buffer, a generator that has stopped running, or an unreachable stream, and
on any issue alert (log + optional webhook/ping). We drive the checks off a sandbox
schedule.json and a fake `requests`, so we test the detection + alert control flow,
not the network.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from src import health, scheduler

NOW = datetime(2026, 6, 24, 2, 0, 0)


def _state(tmp_path, entries, *, last_topup_at=None):
    doc = {"entries": entries}
    if last_topup_at is not None:
        doc["last_topup_at"] = last_topup_at
    (tmp_path / "schedule.json").write_text(json.dumps(doc))


def _entry(air_time, duration):
    return {
        "id": "x",
        "format": "news",
        "audio_path": "x.mp3",
        "air_time": air_time.isoformat(),
        "actual_duration_sec": duration,
        "length_target_sec": 150,
    }


def _wire(monkeypatch, tmp_path):
    monkeypatch.setattr(
        scheduler.settings, "schedule_state_path", tmp_path / "schedule.json"
    )
    # Default the optional/alert knobs off so a check is purely about the state.
    monkeypatch.setattr(health.settings, "health_stream_url", "")
    monkeypatch.setattr(health.settings, "health_ping_url", "")
    monkeypatch.setattr(health.settings, "health_alert_webhook_url", "")
    monkeypatch.setattr(health.settings, "health_min_runway_minutes", 20.0)
    monkeypatch.setattr(health.settings, "health_max_run_age_minutes", 90.0)


class _FakeRequests:
    """Records get/post calls; reuses the real RequestException for error paths."""

    RequestException = health.requests.RequestException

    def __init__(self):
        self.gets: list[str] = []
        self.posts: list[tuple[str, dict]] = []

    def get(self, url, **kw):
        self.gets.append(url)

        class _R:
            status_code = 200

            def close(self):
                pass

        return _R()

    def post(self, url, *, json=None, **kw):
        self.posts.append((url, json))


# --- buffer depth -----------------------------------------------------------


def test_check_buffer_flags_drained(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(tmp_path, [])  # nothing queued -> runway 0
    assert health.check_buffer(NOW) is not None


def test_check_buffer_ok_with_ample_runway(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(tmp_path, [_entry(NOW, 3600.0)])  # an hour queued, above the 20-min floor
    assert health.check_buffer(NOW) is None


def test_check_buffer_ignores_aired_entries(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    # An entry that fully aired before NOW contributes no runway -> still drained.
    _state(tmp_path, [_entry(NOW - timedelta(hours=2), 120.0)])
    assert health.check_buffer(NOW) is not None


# --- last scheduler run -----------------------------------------------------


def test_check_last_run_missing(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(tmp_path, [])  # no last_topup_at written
    assert health.check_last_run(NOW) is not None


def test_check_last_run_stale(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(tmp_path, [], last_topup_at=(NOW - timedelta(hours=3)).isoformat())
    assert health.check_last_run(NOW) is not None


def test_check_last_run_recent_is_ok(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(tmp_path, [], last_topup_at=(NOW - timedelta(minutes=10)).isoformat())
    assert health.check_last_run(NOW) is None


# --- stream liveness --------------------------------------------------------


def test_check_stream_skipped_without_url(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    assert health.check_stream() is None  # no URL configured -> skip


def test_check_stream_flags_unreachable(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    monkeypatch.setattr(health.settings, "health_stream_url", "http://x/stream")

    class _Boom:
        RequestException = health.requests.RequestException

        def get(self, *a, **k):
            raise health.requests.RequestException("refused")

    monkeypatch.setattr(health, "requests", _Boom())
    assert health.check_stream() is not None


# --- run_checks: alert vs. success ping -------------------------------------


def test_run_checks_alerts_and_pings_fail_on_issue(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(tmp_path, [])  # drained + no last run -> issues
    monkeypatch.setattr(health.settings, "health_ping_url", "http://ping/uuid")
    monkeypatch.setattr(health.settings, "health_alert_webhook_url", "http://hook")
    fake = _FakeRequests()
    monkeypatch.setattr(health, "requests", fake)

    issues = health.run_checks(NOW)

    assert issues, "a drained buffer + missing last run must report issues"
    assert fake.posts and fake.posts[0][0] == "http://hook"  # alert webhook fired
    assert fake.gets == ["http://ping/uuid/fail"]  # failure ping, not success


def test_run_checks_pings_success_when_healthy(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    _state(
        tmp_path,
        [_entry(NOW, 3600.0)],
        last_topup_at=(NOW - timedelta(minutes=5)).isoformat(),
    )
    monkeypatch.setattr(health.settings, "health_ping_url", "http://ping/uuid")
    fake = _FakeRequests()
    monkeypatch.setattr(health, "requests", fake)

    issues = health.run_checks(NOW)

    assert issues == []
    assert fake.gets == ["http://ping/uuid"]  # success ping, no /fail suffix
    assert fake.posts == []  # no alert webhook on a clean pass

"""Tests for the operator panel (src/panel/) — E1.0.

Surgical, on the two things where a silent bug would hurt:

  1. the SECURITY invariant (E1 principle #2): the panel refuses a non-loopback
     bind unless the escape hatch is set — the whole "admin private" hard rule
     rests on this;
  2. the dashboard renders from a fixture schedule and DEGRADES readably (200,
     not 500) when the world DB is down.

No real server, no DB, no generation — the schedule maths (`split_schedule`) and
health checks have their own tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from src.config import settings
from src.panel import app as panelapp
from src.panel import views

NOW = datetime(2026, 6, 22, 14, 30, 0)  # a Monday afternoon (grid: the_workshop)


def _state(now=NOW) -> dict:
    return {
        "last_topup_at": (now - timedelta(minutes=2)).isoformat(),
        "entries": [
            {
                "id": "talk-001",
                "format": "talk",
                "program": "the_workshop",
                "program_name": "The Workshop",
                "air_time": (now - timedelta(minutes=1)).isoformat(),
                "actual_duration_sec": 240.0,
                "length_target_sec": 240,
            },
            {
                "id": "news-002",
                "format": "news",
                "program": "the_workshop",
                "program_name": "The Workshop",
                "air_time": (now + timedelta(minutes=3)).isoformat(),
                "actual_duration_sec": 120.0,
                "length_target_sec": 150,
            },
        ],
    }


# --- 1. the loopback security invariant --------------------------------------


def test_is_loopback():
    assert panelapp.is_loopback("127.0.0.1")
    assert panelapp.is_loopback("127.1.2.3")
    assert panelapp.is_loopback("::1")
    assert panelapp.is_loopback("localhost")
    assert not panelapp.is_loopback("0.0.0.0")
    assert not panelapp.is_loopback("10.0.0.5")


def test_run_refuses_nonlocal_bind(monkeypatch):
    """A non-loopback bind without the escape hatch never starts the server."""
    started = {"called": False}

    import uvicorn

    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: started.update(called=True))
    monkeypatch.setattr(settings, "panel_host", "0.0.0.0")
    monkeypatch.setattr(settings, "panel_allow_nonlocal", False)

    assert panelapp.run() == 2  # refused
    assert started["called"] is False  # uvicorn never invoked


def test_run_allows_nonlocal_with_escape_hatch(monkeypatch):
    """The explicit escape hatch permits the bind (and actually serves)."""
    started = {"called": False, "host": None}

    import uvicorn

    def _fake_run(app, host, port, **k):  # noqa: ANN001
        started.update(called=True, host=host)

    monkeypatch.setattr(uvicorn, "run", _fake_run)
    monkeypatch.setattr(settings, "panel_host", "0.0.0.0")
    monkeypatch.setattr(settings, "panel_allow_nonlocal", True)

    assert panelapp.run() == 0
    assert started["called"] and started["host"] == "0.0.0.0"


# --- 2. the dashboard renders + degrades -------------------------------------


def test_dashboard_renders_from_fixture(monkeypatch):
    """The dashboard names on-air/next and stays a 200 with the DB unavailable."""
    # Base the fixture on the REAL clock: the dashboard route calls
    # views.dashboard() with no `now`, so it renders against datetime.now().
    monkeypatch.setattr(views, "_load_state", lambda: _state(datetime.now()))
    # Force the world panel down (no DB in the test) — it must degrade, not raise.
    monkeypatch.setattr(
        views, "world_panels", lambda now: {"available": False, "error": "no DB"}
    )

    client = TestClient(panelapp.app)
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    # on-air + queued, the same answer the console gives
    assert "The Workshop" in body  # the on-air program name
    assert "talk-001" in body  # the on-air segment id
    assert "queued" in body  # the "next N of M queued" upcoming label
    # the DB-down note is shown, not a 500
    assert "unavailable" in body.lower()
    # the security posture is visible on the page
    assert "private (loopback)" in body


def test_world_panel_returns_unavailable_when_db_down(monkeypatch):
    """world_panels swallows a store failure into a readable note (never raises)."""

    def _boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(views.store, "connect", _boom)
    out = views.world_panels(NOW)
    assert out["available"] is False
    assert "connection refused" in out["error"]

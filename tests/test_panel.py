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

import pytest
from fastapi.testclient import TestClient
from src.config import settings
from src.panel import actions, views
from src.panel import app as panelapp

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


# --- E1.1: the actions page + mutation lock + reset gate ----------------------


class _FakeThread:
    """A no-op Thread: start() does nothing, so _execute never runs (no subprocess).

    Lets us exercise start_action's validation + LOCK logic without launching real
    seeds/ticks — crucially never the DESTRUCTIVE `reset --force`.
    """

    def __init__(self, target=None, args=(), daemon=None):  # noqa: ANN001
        pass

    def start(self) -> None:
        pass


@pytest.fixture
def no_launch(monkeypatch):
    """Stub the background thread + reset the module run/lock state around a test."""
    monkeypatch.setattr(actions.threading, "Thread", _FakeThread)
    actions._RUNS.clear()
    actions._current_mutation = None
    yield
    actions._RUNS.clear()
    actions._current_mutation = None


def test_action_argv_mirrors_make_commands():
    """Each action's argv is the exact `.venv/bin/python -m <module …>` make runs."""
    a = actions.ACTIONS
    assert a["seed-canon"].argv[-2:] == ["src.world.seed", "canon"]
    assert a["seed-tracks"].argv[-1] == "src.world.seed_tracks"
    assert a["prune"].argv[-2:] == ["src.scheduler", "--prune"]
    assert a["health"].argv[-1] == "src.health"
    # reset is destructive, gated, and --force (the panel's phrase replaces the prompt)
    reset = a["reset-world"]
    assert reset.destructive and reset.confirm_phrase == "reset the world"
    assert reset.argv[-3:] == ["src.world.seed", "reset", "--force"]
    assert a["health"].mutating is False  # read-only → no lock


def test_mutation_lock_blocks_a_second_mutating_action(no_launch):
    """Two mutating actions can't overlap; the read-only one is exempt."""
    first = actions.start_action("world-tick")
    assert actions.current_mutation() is first

    with pytest.raises(actions.Busy) as exc:
        actions.start_action("schedule")
    assert exc.value.holder is first

    # a NON-mutating action is allowed alongside a held lock
    actions.start_action("health")

    # once the holder finishes, the slot frees and the next mutation proceeds
    first.status = "done"
    actions._release_mutation(first)
    assert actions.current_mutation() is None
    second = actions.start_action("schedule")
    assert actions.current_mutation() is second


def test_reset_requires_exact_phrase(no_launch):
    """The destructive wipe never starts without the exact confirmation phrase."""
    with pytest.raises(PermissionError):
        actions.start_action("reset-world", phrase="")
    with pytest.raises(PermissionError):
        actions.start_action("reset-world", phrase="reset-world")  # close, but wrong
    assert actions.recent_runs() == []  # nothing launched

    run = actions.start_action("reset-world", phrase="reset the world")
    assert run.action_id == "reset-world"  # the exact phrase starts it


def test_run_route_refuses_destructive_and_reports_busy(no_launch):
    """The generic run route sends destructive to the gated page and blocks on busy."""
    client = TestClient(panelapp.app, follow_redirects=False)

    # destructive is never runnable from the generic button
    r = client.post("/actions/run", data={"action_id": "reset-world"})
    assert r.status_code == 303 and r.headers["location"] == "/actions/reset-world"

    # hold the lock, then a second mutating action redirects with a busy message
    held = actions.start_action("world-tick")
    r = client.post("/actions/run", data={"action_id": "schedule"})
    assert r.status_code == 303 and "busy" in r.headers["location"]
    held.status = "done"
    actions._release_mutation(held)


def test_reset_page_and_wrong_phrase_are_inert(no_launch):
    """The reset page renders the phrase; a wrong phrase creates no run."""
    client = TestClient(panelapp.app, follow_redirects=False)
    page = client.get("/actions/reset-world")
    assert page.status_code == 200 and "reset the world" in page.text

    r = client.post("/actions/reset-world", data={"phrase": "nope"})
    assert r.status_code == 303 and "did+not+match" in r.headers["location"]
    assert actions.recent_runs() == []  # inert — nothing launched

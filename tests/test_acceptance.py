"""Tests for the D11.3 integrated acceptance simulation (`src/acceptance.py`).

Two layers, matching how the harness is trusted:

* the **property evaluators** are PURE (dicts/lists/Events in → a verdict out), so we
  unit-test each one BOTH ways — it passes clean data AND *fails loudly* on a planted
  defect (a silent gap, a repetition loop, a story that never moved, a call storm, a
  backwards schedule). A gate that can't fail is worthless, so the failing cases are the
  point.
* the **end-to-end run** is exercised on a small isolated window against a live Postgres
  (skipped cleanly without one): all eight properties must pass on the real spine driven
  through the mocked provider seams. This is the same `run_acceptance` the `make`
  target/C9 gate calls, just short.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from src import acceptance as acc
from src.world import clock, store


# --- tiny builders ----------------------------------------------------------
def _entry(seg_id, fmt, air_time, dur, *, track=None):
    return {
        "id": seg_id,
        "format": fmt,
        "air_time": air_time.isoformat()
        if isinstance(air_time, datetime)
        else air_time,
        "actual_duration_sec": dur,
        "length_target_sec": dur,
        "track": track,
    }


def _contiguous(n, *, fmt="talk", dur=120.0, start=None):
    """`n` back-to-back slots from `start`, each `dur` seconds, distinct openings."""
    start = start or datetime(2026, 7, 6, 20, 0, 0)
    out = []
    t = start
    for i in range(n):
        out.append(_entry(f"{fmt}-{i}", fmt, t, dur))
        t += timedelta(seconds=dur)
    return out


def _beat(title, iso_dt):
    return store.Event(
        id=title,
        title=title,
        body="",
        in_world_datetime=datetime.fromisoformat(iso_dt),
        status="",
    )


# --- no_dead_gaps -----------------------------------------------------------
def test_no_dead_gaps_passes_on_contiguous():
    tl = _contiguous(6)
    r = acc._check_no_dead_gaps(tl, tl[0], tl[-1])
    assert r.ok, r.detail


def test_no_dead_gaps_fails_on_silent_gap():
    tl = _contiguous(3)
    # Shove the last slot 10 minutes into the future — a silent hole opens.
    tl[-1]["air_time"] = (
        datetime.fromisoformat(tl[-1]["air_time"]) + timedelta(minutes=10)
    ).isoformat()
    r = acc._check_no_dead_gaps(tl, None, None)
    assert not r.ok
    assert "gap" in r.detail


def test_no_dead_gaps_fails_when_evergreen_fired():
    tl = _contiguous(3)
    tl.insert(1, _entry("evergreen-2-kokoro-vell", "evergreen", tl[0]["air_time"], 60))
    r = acc._check_no_dead_gaps(tl, None, None)
    assert not r.ok
    assert "evergreen" in r.detail


# --- no_repetition_loops ----------------------------------------------------
def test_no_repetition_passes_on_varied():
    tl = _contiguous(3, fmt="music", dur=120)
    tl[0]["track"] = {"title": "A", "artist": "X"}
    tl[1]["track"] = {"title": "B", "artist": "Y"}
    tl[2]["track"] = {"title": "C", "artist": "Z"}
    openings = [("talk", f"open number {i}", f"topic {i}") for i in range(6)]
    r = acc._check_no_repetition(tl, openings)
    assert r.ok, r.detail


def test_no_repetition_fails_on_looped_openings():
    openings = [("talk", "the same open", "the same topic") for _ in range(6)]
    r = acc._check_no_repetition([], openings)
    assert not r.ok
    assert "talk" in r.detail


def test_no_repetition_fails_on_back_to_back_song():
    tl = _contiguous(2, fmt="music", dur=120)
    tl[0]["track"] = {"title": "Same", "artist": "X"}
    tl[1]["track"] = {"title": "Same", "artist": "X"}
    r = acc._check_no_repetition(tl, [])
    assert not r.ok
    assert "song" in r.detail


# --- talk_flow (D12) --------------------------------------------------------
def _talk_run(program, positions, *, start=None):
    """Consecutive talk slots in one program, each stamped with its show position."""
    start = start or datetime(2026, 7, 1, 22, 0, 0)
    out = []
    for i, pos in enumerate(positions):
        e = _entry(f"{program}-{i}", "talk", start + timedelta(minutes=5 * i), 120.0)
        e["program"] = program
        e["flow_position"] = pos
        out.append(e)
    return out


def test_talk_flow_passes_when_a_show_opens_once():
    # open → continue → continue → close: one show, not four mini-shows.
    tl = _talk_run("long_night", ["open", "continue", "continue", "close"])
    r = acc._check_talk_flow(tl)
    assert r.ok
    assert "one open per show" in r.detail


def test_talk_flow_fails_on_a_mid_show_reopen():
    # a second `open` inside the same program run = the reset D12 removed.
    tl = _talk_run("long_night", ["open", "continue", "open", "close"])
    r = acc._check_talk_flow(tl)
    assert not r.ok
    assert "re-opened" in r.detail


def test_talk_flow_resets_open_at_each_new_program():
    # each program's FIRST talk may open; that is not a re-open.
    tl = _talk_run("long_night", ["open", "continue"]) + _talk_run(
        "first_light", ["open", "continue"], start=datetime(2026, 7, 2, 5, 0, 0)
    )
    r = acc._check_talk_flow(tl)
    assert r.ok


# --- stories_evolve ---------------------------------------------------------
def test_stories_evolve_passes_with_moving_present():
    now = datetime(2026, 7, 6, 20, 0, 0)
    iw = clock.to_inworld(now)
    world = {
        "beats": {
            "s1": [
                _beat("past", (iw - timedelta(days=2)).isoformat()),
                _beat("future", (iw + timedelta(days=2)).isoformat()),
            ]
        }
    }
    r = acc._check_stories_evolve(world, advanced_total=3, now=now)
    assert r.ok, r.detail


def test_stories_evolve_fails_when_nothing_advanced():
    r = acc._check_stories_evolve({"beats": {}}, advanced_total=0, now=datetime.now())
    assert not r.ok
    assert "advanced" in r.detail


def test_stories_evolve_fails_without_moving_present():
    now = datetime(2026, 7, 6, 20, 0, 0)
    iw = clock.to_inworld(now)
    # All beats in the future → no past side → not a moving present.
    world = {"beats": {"s1": [_beat("f", (iw + timedelta(days=3)).isoformat())]}}
    r = acc._check_stories_evolve(world, advanced_total=2, now=now)
    assert not r.ok
    assert "moving present" in r.detail


# --- cost_bounded -----------------------------------------------------------
def test_cost_bounded_passes_within_envelope():
    r = acc._check_cost_bounded({"content_slots": 100, "llm_calls": 500})
    assert r.ok, r.detail


def test_cost_bounded_fails_on_call_storm():
    r = acc._check_cost_bounded({"content_slots": 10, "llm_calls": 1000})
    assert not r.ok
    assert "storm" in r.detail


# --- schedule_sane ----------------------------------------------------------
def test_schedule_sane_passes_on_clean_schedule():
    tl = _contiguous(5)
    tl.append(_entry("ident-20260706T210000", "ident", tl[-1]["air_time"], 14))
    r = acc._check_schedule_sane(tl)
    assert r.ok, r.detail


def test_schedule_sane_fails_on_backwards_order():
    tl = _contiguous(3)
    tl[1]["air_time"] = (
        datetime.fromisoformat(tl[0]["air_time"]) - timedelta(minutes=5)
    ).isoformat()
    r = acc._check_schedule_sane(tl)
    assert not r.ok
    assert "backwards" in r.detail


def test_schedule_sane_fails_on_zero_duration():
    tl = _contiguous(3)
    tl[1]["actual_duration_sec"] = 0
    tl[1]["length_target_sec"] = 0
    r = acc._check_schedule_sane(tl)
    assert not r.ok
    assert "duration" in r.detail


# --- end-to-end (DB-gated) --------------------------------------------------
# --- plain_register (R1.4) --------------------------------------------------
def _register_gen(prompts=1, scripts=None):
    """A gen stub carrying only the fields `_check_plain_register` reads."""
    from types import SimpleNamespace

    return SimpleNamespace(
        register_daytime_prompts=prompts, daytime_talk_scripts=scripts or []
    )


def _talk_on(program, n=3):
    """`n` talk slots stamped with a program id (energy read from the real grid)."""
    entries = _contiguous(n, fmt="talk")
    for e in entries:
        e["program"] = program
    return entries


def test_plain_register_passes_on_clean_daytime_talk():
    timeline = _talk_on("the_exchange")  # steady in the shipped grid
    scripts = ["Vell: It's fine, don't worry — the price didn't move."] * 3
    r = acc._check_plain_register(timeline, _register_gen(3, scripts))
    assert r.ok


def test_plain_register_inconclusive_without_daytime_talk():
    timeline = _talk_on("long_night")  # calm — the night is exempt
    r = acc._check_plain_register(timeline, _register_gen(0, []))
    assert r.ok
    assert "inconclusive" in r.detail


def test_plain_register_fails_when_ban_never_reached_room():
    timeline = _talk_on("the_exchange")
    r = acc._check_plain_register(timeline, _register_gen(0, []))
    assert not r.ok
    assert "never reached" in r.detail


def test_plain_register_fails_on_banned_phrase():
    timeline = _talk_on("the_exchange")
    bad = f"Vell: It's {acc.BANNED_ABSTRACTIONS[0]} again, isn't it."
    r = acc._check_plain_register(timeline, _register_gen(1, [bad]))
    assert not r.ok
    assert "banned abstraction" in r.detail


def test_plain_register_fails_below_contraction_floor():
    timeline = _talk_on("the_exchange")
    stiff = ["Vell: The council convened. The matter was resolved."] * 3
    r = acc._check_plain_register(timeline, _register_gen(3, stiff))
    assert not r.ok
    assert "contraction floor" in r.detail


def test_run_acceptance_end_to_end():
    """A short isolated run on the real spine — all eight properties must pass.

    Skips cleanly without Postgres/pgvector; otherwise it seeds nothing of its own and
    rolls the whole world back (isolated), so it never touches the operator's DB.
    """
    try:
        report = acc.run_acceptance(
            window_hours=2.0,
            step_minutes=60,  # clamped to the buffer depth internally
            tick_every_hours=1.0,
            warmup_ticks=2,
            buffer_depth_hours=0.5,
        )
    except acc._NoDatabaseError as exc:
        pytest.skip(f"no Postgres/pgvector: {exc}")

    assert report.telemetry["content_slots"] > 0
    failures = [f"{r.name}: {r.detail}" for r in report.results if not r.ok]
    assert report.ok, "acceptance properties failed:\n" + "\n".join(failures)
    assert len(report.results) == 8

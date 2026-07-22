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

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from src import scheduler
from src.config import settings
from src.panel import actions, grid_edit, schedule_view, views
from src.panel import app as panelapp
from src.world import programming

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


# --- E1.2: the grid editor (round-trip fidelity + validation + write flow) -----


@pytest.fixture
def grid_tmp(tmp_path, monkeypatch):
    """A throwaway COPY of the real grid.yaml as the live grid, with a known cast.

    Points settings + the programming loader at the temp file so writes never touch
    the repo's grid, and fixes the cast set (every host the grid uses + `joss`) so
    host validation is deterministic without a DB.
    """
    real = programming.settings.programming_grid_path
    tmp = tmp_path / "grid.yaml"
    tmp.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(settings, "programming_grid_path", tmp)
    programming.reload()
    # the cast = every host referenced in the grid (so existing hosts all validate)
    known = {h for p in programming.all_programs().values() for h in p.hosts}
    monkeypatch.setattr(grid_edit, "_cast_ids", lambda: known)
    yield tmp
    programming.reload()


def test_grid_noop_edit_is_byte_identical(grid_tmp):
    """Re-applying a program's own current values reproduces the file exactly."""
    original = grid_edit.current_text()
    for pid in grid_edit.program_ids():
        form = grid_edit.program_form(pid)
        assert grid_edit.apply_program_edit(pid, form) == original, pid


def test_grid_host_swap_is_a_minimal_diff(grid_tmp):
    """A host change touches only the hosts line (hand-quality diff)."""
    form = grid_edit.program_form("morning_currents")
    form.hosts = "thorn, joss"
    candidate = grid_edit.apply_program_edit("morning_currents", form)
    v = grid_edit.validate_text(candidate, focus="morning_currents")
    assert v.ok
    changed = [
        ln
        for ln in grid_edit.unified_diff(
            grid_edit.current_text(), candidate
        ).splitlines()
        if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
    ]
    assert changed == ["-    hosts: [thorn, wren]", "+    hosts: [thorn, joss]"]


def test_grid_validation_rejects_bad_edits(grid_tmp):
    """The real parser catches an unknown host, clock format, framing, and bad YAML."""
    form = grid_edit.program_form("the_gallery")
    form.hosts = "thorn, ghost_host"
    v = grid_edit.validate_text(
        grid_edit.apply_program_edit("the_gallery", form), focus="the_gallery"
    )
    assert not v.ok and any("unknown host id" in e for e in v.errors)

    form = grid_edit.program_form("the_gallery")
    form.clock = "talk talkk"
    v = grid_edit.validate_text(
        grid_edit.apply_program_edit("the_gallery", form), focus="the_gallery"
    )
    assert not v.ok and any("unknown clock format" in e for e in v.errors)

    form = grid_edit.program_form("the_gallery")
    form.framing = "duet"
    v = grid_edit.validate_text(
        grid_edit.apply_program_edit("the_gallery", form), focus="the_gallery"
    )
    assert not v.ok and any("unknown framing" in e for e in v.errors)

    v = grid_edit.validate_text("programs: [broken: yaml")
    assert not v.ok and any("YAML syntax error" in e for e in v.errors)


def test_grid_route_flow_diff_then_write(grid_tmp):
    """POST edit → diff (no write); confirm → atomic write + .bak; loader re-reads."""
    client = TestClient(panelapp.app, follow_redirects=False)
    morning = datetime(2026, 7, 21, 7, 30)  # a Tuesday → morning_currents on air
    assert programming.program_for(morning).hosts == ("thorn", "wren")  # baseline

    form = grid_edit.program_form("morning_currents")
    data = {
        k: getattr(form, k)
        for k in (
            "name",
            "framing",
            "daypart",
            "clock",
            "break_every",
            "guest_chance",
            "brief",
            "energy",
            "talk_length_sec",
            "domains",
        )
    }

    # an invalid edit is rejected and NOT written (no diff page); loader unchanged
    bad = {**data, "hosts": "thorn, ghost_host"}
    r = client.post("/grid/program/morning_currents", data=bad)
    assert r.status_code == 200 and "Confirm" not in r.text
    programming.reload()
    assert programming.program_for(morning).hosts == ("thorn", "wren")

    # a valid edit shows the diff but does NOT write (the diff step is unskippable)
    good = {**data, "hosts": "thorn, mira"}
    r = client.post("/grid/program/morning_currents", data=good)
    assert r.status_code == 200 and "Confirm &amp; write" in r.text
    programming.reload()
    assert programming.program_for(morning).hosts == (
        "thorn",
        "wren",
    )  # still unwritten

    # confirm the candidate → atomic write + one-deep backup + live reload
    import html
    import re

    candidate = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post(
        "/grid/program/morning_currents/confirm", data={"candidate": candidate}
    )
    assert r.status_code == 303 and "saved=morning_currents" in r.headers["location"]
    # the backup is named like write_grid makes it (grid.yaml.bak)
    assert grid_tmp.with_suffix(grid_tmp.suffix + ".bak").exists()
    # the edit is a MINIMAL diff and the loader now returns the new hosts
    changed = [
        ln
        for ln in grid_edit.unified_diff(
            grid_tmp.with_suffix(grid_tmp.suffix + ".bak").read_text(),
            grid_edit.current_text(),
        ).splitlines()
        if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
    ]
    assert changed == ["-    hosts: [thorn, wren]", "+    hosts: [thorn, mira]"]
    assert programming.program_for(morning).hosts == ("thorn", "mira")


# --- E1.3: the catalog editors (tracks + sponsors) ----------------------------


@pytest.fixture
def catalog_tmp(tmp_path, monkeypatch):
    """Throwaway COPIES of the four catalog files as the live catalogs."""

    mapping = {
        "tracks_manifest_path": "tracks.yaml",
        "sponsors_manifest_path": "sponsors.yaml",
        "tts_lexicon_path": "pronunciation.yaml",
        "tts_voices_path": "voices.yaml",
    }
    for attr, name in mapping.items():
        dst = tmp_path / name
        dst.write_text(getattr(settings, attr).read_text(encoding="utf-8"), "utf-8")
        monkeypatch.setattr(settings, attr, dst)
    return tmp_path


def test_catalog_tracks_noop_fidelity(catalog_tmp):
    """Re-applying a track's own values reproduces the manifest byte-identically."""
    from src.panel import catalog_edit as ce

    cat = ce.catalog("tracks")
    original = ce.current_text(cat)
    bad = [
        r["_key"]
        for r in ce.list_rows(cat)
        if ce.apply_row(cat, r["_key"], ce.row_form(cat, r["_key"])) != original
    ]
    assert bad == [], bad


def test_catalog_tracks_edit_and_validate(catalog_tmp):
    """A valid edit is a minimal diff; a cleared required field is rejected."""
    from src.panel import catalog_edit as ce

    cat = ce.catalog("tracks")
    key = ce.list_rows(cat)[0]["_key"]
    form = ce.row_form(cat, key)
    form["mood"] = "zzz-testmood"
    candidate = ce.apply_row(cat, key, form)
    assert cat.validate(candidate).ok
    changed = [
        ln
        for ln in ce.unified_diff(ce.current_text(cat), candidate).splitlines()
        if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
    ]
    assert changed == ['-    mood: "melancholy"', '+    mood: "zzz-testmood"']

    form = ce.row_form(cat, key)
    form["title"] = ""  # clearing a required field removes the key
    v = cat.validate(ce.apply_row(cat, key, form))
    assert not v.ok and any("missing required field" in e for e in v.errors)


def test_catalog_tracks_write_flow(catalog_tmp):
    """POST save → diff (no write); confirm → write + .bak; featured tag added."""
    from src.panel import catalog_edit as ce

    client = TestClient(panelapp.app, follow_redirects=False)
    cat = ce.catalog("tracks")
    key = ce.list_rows(cat)[0]["_key"]
    data = {f.name: ce.row_form(cat, key)[f.name] for f in cat.fields}
    data.update(
        {"_adding": "0", "_key": key, "mood": "zzz-testmood", "flag_featured": "on"}
    )

    r = client.post("/catalog/tracks/save", data=data)
    assert r.status_code == 200 and "Confirm &amp; write" in r.text
    assert ce.row_form(cat, key)["mood"] == "melancholy"  # not written yet

    import html
    import re

    cand = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post("/catalog/tracks/write", data={"candidate": cand, "key": key})
    assert r.status_code == 303 and f"saved={key}" in r.headers["location"]
    assert (catalog_tmp / "tracks.yaml.bak").exists()
    assert ce.row_form(cat, key)["mood"] == "zzz-testmood"
    assert "featured" in ce.row_form(cat, key)["tags"]


def test_catalog_sponsors_add_delete_with_date(catalog_tmp):
    """Add a sponsor with a date window (validated by the seeder), then delete."""
    from src.panel import catalog_edit as ce

    client = TestClient(panelapp.app, follow_redirects=False)
    sp = ce.catalog("sponsors")

    import html
    import re

    add = {
        "_adding": "1",
        "id": "sig-friend",
        "name": "a friend of the signal",
        "powered_by_text": "lit",
        "audio_path": "",
        "run_start": "2027-01-01",
        "run_end": "",
        "weight": "1",
        "tags": "",
    }
    r = client.post("/catalog/sponsors/save", data=add)
    assert r.status_code == 200 and "Confirm &amp; write" in r.text
    cand = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post(
        "/catalog/sponsors/write", data={"candidate": cand, "key": "sig-friend"}
    )
    assert r.status_code == 303
    assert any(row["_key"] == "sig-friend" for row in ce.list_rows(sp))

    # a bad date is rejected by the seeder's parser
    bad = {**add, "run_start": "not-a-date", "id": "bad-date"}
    assert not sp.validate(ce.apply_row(sp, "bad-date", bad, adding=True)).ok

    # delete → diff → write
    r = client.post("/catalog/sponsors/delete", data={"_key": "sig-friend"})
    assert r.status_code == 200 and "Remove" in r.text
    cand = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post(
        "/catalog/sponsors/write", data={"candidate": cand, "key": "sig-friend"}
    )
    assert r.status_code == 303
    assert not any(row["_key"] == "sig-friend" for row in ce.list_rows(sp))


@pytest.mark.parametrize("slug", ["pronunciation", "voices"])
def test_catalog_registry_noop_fidelity(catalog_tmp, slug):
    """Pronunciation (top-level list) + voices (map) round-trip byte-identically."""
    from src.panel import catalog_edit as ce

    cat = ce.catalog(slug)
    original = ce.current_text(cat)
    bad = [
        r["_key"]
        for r in ce.list_rows(cat)
        if ce.apply_row(cat, r["_key"], ce.row_form(cat, r["_key"])) != original
    ]
    assert bad == [], bad


def test_catalog_pronunciation_edit_and_validate(catalog_tmp):
    """A respell edit is a minimal diff; a missing respell is rejected."""
    from src.panel import catalog_edit as ce

    cat = ce.catalog("pronunciation")
    key = ce.list_rows(cat)[0]["_key"]
    form = ce.row_form(cat, key)
    form["respell"] = "TEST-RESPELL"
    candidate = ce.apply_row(cat, key, form)
    assert cat.validate(candidate).ok
    changed = [
        ln
        for ln in ce.unified_diff(ce.current_text(cat), candidate).splitlines()
        if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
    ]
    assert changed == ["-  respell: Vell", "+  respell: TEST-RESPELL"]

    form = ce.row_form(cat, key)
    form["respell"] = ""
    assert not cat.validate(ce.apply_row(cat, key, form)).ok


def test_catalog_voices_edit_add_validate(catalog_tmp):
    """A voices (map) edit is minimal; a new voice missing an engine is rejected."""
    from src.panel import catalog_edit as ce

    cat = ce.catalog("voices")
    key = ce.list_rows(cat)[0]["_key"]
    form = ce.row_form(cat, key)
    form["kokoro"] = "bm_test"
    candidate = ce.apply_row(cat, key, form)
    assert cat.validate(candidate).ok
    changed = [
        ln
        for ln in ce.unified_diff(ce.current_text(cat), candidate).splitlines()
        if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
    ]
    assert changed == ["-  kokoro: bm_george", "+  kokoro: bm_test"]

    # a new voice missing an engine mapping is rejected by the real registry loader
    cand = ce.apply_row(
        cat,
        "test_voice",
        {"kokoro": "bm_x", "elevenlabs": "", "say": "Alex", "_flags": {}},
        adding=True,
    )
    v = cat.validate(cand)
    assert not v.ok and any("missing elevenlabs" in e for e in v.errors)


def test_catalog_voices_map_write_flow(catalog_tmp):
    """POST save → diff → confirm writes a map entry; the .bak is kept."""
    from src.panel import catalog_edit as ce

    client = TestClient(panelapp.app, follow_redirects=False)
    cat = ce.catalog("voices")
    key = ce.list_rows(cat)[0]["_key"]
    data = {f.name: ce.row_form(cat, key)[f.name] for f in cat.fields}
    data.update({"_adding": "0", "_key": key, "kokoro": "bm_test"})
    r = client.post("/catalog/voices/save", data=data)
    assert r.status_code == 200 and "Confirm &amp; write" in r.text

    import html
    import re

    cand = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post("/catalog/voices/write", data={"candidate": cand, "key": key})
    assert r.status_code == 303 and (catalog_tmp / "voices.yaml.bak").exists()
    assert ce.row_form(cat, key)["kokoro"] == "bm_test"


# --- E1.4: the cast manager ---------------------------------------------------


@pytest.fixture
def cast_tmp(tmp_path, monkeypatch):
    """A throwaway COPY of the canon folder + voices.yaml as the live sources."""
    import shutil

    canon = tmp_path / "canon"
    shutil.copytree(settings.canon_dir, canon)
    monkeypatch.setattr(settings, "canon_dir", canon)
    vdst = tmp_path / "voices.yaml"
    vdst.write_text(settings.tts_voices_path.read_text("utf-8"), "utf-8")
    monkeypatch.setattr(settings, "tts_voices_path", vdst)
    return tmp_path


def test_cast_noop_fidelity(cast_tmp):
    """Re-applying a card's own values reproduces 90-cast.md byte-identically."""
    from src.panel import cast_edit as ce

    original = ce.current_text()
    bad = [
        c["id"]
        for c in ce.list_cards()
        if ce.apply_card_edit(c["id"], ce.card_form(c["id"])) != original
    ]
    assert bad == [], bad


def test_cast_edit_minimal_diff_and_validate(cast_tmp):
    """A tags edit is a one-line diff; a bad logical voice is rejected."""
    from src.panel import cast_edit as ce

    form = ce.card_form("vell")
    form["tags"] = "night, warmth, calm"
    candidate = ce.apply_card_edit("vell", form)
    assert ce.validate(candidate).ok
    changed = [
        ln
        for ln in ce.unified_diff(ce.current_text(), candidate).splitlines()
        if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
    ]
    assert len(changed) == 2 and changed[1].startswith(
        "+- **Tags:** night, warmth, calm"
    )

    form = ce.card_form("vell")
    form["logical_voice"] = "ghost_voice"
    v = ce.validate(ce.apply_card_edit("vell", form))
    assert not v.ok and any("has no entry" in e for e in v.errors)


def test_cast_add_dj_with_new_voice_two_file_write(cast_tmp):
    """Adding a DJ with a new voice writes both 90-cast.md and voices.yaml."""
    from src.panel import cast_edit as ce
    from src.panel import catalog_edit as cate

    client = TestClient(panelapp.app, follow_redirects=False)
    add = {
        "_adding": "1",
        "name": "Nova Test",
        "logical_voice": "nova_test",
        "based": "station",
        "tags": "test, night",
        "role": "the test shift",
        "background": "a test",
        "personality": "calm",
        "humour": "dry",
        "voice_tts": "flat",
        "verbal_tics": "says test",
        "never": "breaks character",
        "sample_lines": "Hello.\nBye.",
        "voice_kokoro": "bm_george",
        "voice_elevenlabs": "xyz",
        "voice_say": "Alex",
    }
    r = client.post("/cast/save", data=add)
    assert r.status_code == 200 and "config/voices.yaml (new voice entry)" in r.text

    import html
    import re

    ccand = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    vcand = html.unescape(
        re.search(
            r'<textarea name="voices_candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post(
        "/cast/write",
        data={"candidate": ccand, "cid": "nova-test", "voices_candidate": vcand},
    )
    assert r.status_code == 303
    assert ce.card_form("nova-test") is not None
    assert "nova_test" in cate.current_text(cate.catalog("voices"))


def test_cast_retire_warns_on_grid_usage(cast_tmp):
    """Retiring a scheduled host warns; removing it keeps the file valid."""
    from src.panel import cast_edit as ce

    client = TestClient(panelapp.app, follow_redirects=False)
    assert ce.grid_uses("vell")  # vell is scheduled somewhere
    r = client.post("/cast/delete", data={"_cid": "vell"})
    assert r.status_code == 200 and "grid still schedules" in r.text
    candidate = ce.remove_card("vell")
    assert "### Vell" not in candidate and ce.validate(candidate).ok


# --- E1.5: the dials page -----------------------------------------------------


@pytest.fixture
def dials_tmp(tmp_path, monkeypatch):
    """A throwaway COPY of .env as the live dials file."""
    from src.panel import dials

    dst = tmp_path / ".env"
    src = dials._ENV_PATH
    dst.write_text(src.read_text("utf-8") if src.exists() else "# test\n", "utf-8")
    monkeypatch.setattr(dials, "_ENV_PATH", dst)
    return dst


def test_dials_grouping_and_state(dials_tmp):
    """Rows carry effective/default/file state and the right editability + warnings."""
    from src.panel import dials

    rows = {r.name: r for r in dials.group_rows(dials.group_by_slug("world_tick"))}
    r = rows["world_tick_new_stories_min"]
    assert r.effective == "2" and r.default == "2" and r.file_value is None
    assert r.editable and r.kind == "int"

    safety = {r.name: r for r in dials.group_rows(dials.group_by_slug("safety"))}
    assert safety["safety_enabled"].warn and safety["safety_enabled"].kind == "bool"


def test_dials_stage_set_reset_and_bad_type(dials_tmp):
    """Staging: a change sets an override; the default removes it; bad type errors."""
    from src.panel import dials

    g = dials.group_by_slug("world_tick")
    staged = dials.stage_group_edit(g, {"world_tick_new_stories_min": "3"})
    assert staged.changes == {"WORLD_TICK_NEW_STORIES_MIN": "3"} and not staged.errors

    bad = dials.stage_group_edit(g, {"world_tick_large_ratio": "notafloat"})
    assert bad.errors and not bad.changes

    # write the override, then setting it to the default removes it
    dials.write(dials.apply_changes(staged.changes))
    reset = dials.stage_group_edit(g, {"world_tick_new_stories_min": "2"})
    assert reset.changes == {"WORLD_TICK_NEW_STORIES_MIN": None}


def test_dials_route_write_and_truthful_state(dials_tmp):
    """A dial changed in the browser lands in .env; effective stays truthfully stale."""
    import html
    import re

    from src.panel import dials

    client = TestClient(panelapp.app, follow_redirects=False)
    r = client.post("/dials/world_tick/save", data={"world_tick_new_stories_max": "9"})
    assert r.status_code == 200 and "WORLD_TICK_NEW_STORIES_MAX=9" in r.text
    assert "9" not in dials.env_overrides().get(
        "WORLD_TICK_NEW_STORIES_MAX", ""
    )  # unwritten

    cand = html.unescape(
        re.search(
            r'<textarea name="candidate" hidden>(.*?)</textarea>', r.text, re.S
        ).group(1)
    )
    r = client.post("/dials/write", data={"candidate": cand, "slug": "world_tick"})
    assert r.status_code == 303 and (dials._ENV_PATH.parent / ".env.bak").exists()
    assert dials.env_overrides()["WORLD_TICK_NEW_STORIES_MAX"] == "9"  # file truth

    rows = {r.name: r for r in dials.group_rows(dials.group_by_slug("world_tick"))}
    row = rows["world_tick_new_stories_max"]
    assert row.file_value == "9"  # .env truth
    assert row.effective == "4"  # live settings (loaded at import) — truthfully stale


def test_dials_bad_type_route_rejected(dials_tmp):
    """The save route rejects a bad type without writing."""
    client = TestClient(panelapp.app, follow_redirects=False)
    r = client.post("/dials/music/save", data={"music_select_jitter": "abc"})
    assert r.status_code == 303 and "rejected" in r.headers["location"]


def test_dials_env_writer_preserves_unrelated_lines(tmp_path, monkeypatch):
    """A dial write is a surgical line edit — comments + other keys are untouched."""
    from src.panel import dials

    env = tmp_path / ".env"
    env.write_text(
        "# a header comment\n"
        "ANTHROPIC_API_KEY=secret-xyz\n"
        "# WORLD_TICK_NEW_STORIES_MIN is unset here\n"
        "LOG_LEVEL=info\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dials, "_ENV_PATH", env)

    # append a brand-new override
    g = dials.group_by_slug("world_tick")
    dials.write(
        dials.apply_changes(
            dials.stage_group_edit(g, {"world_tick_new_stories_min": "3"}).changes
        )
    )
    text = dials.current_text()
    assert "# a header comment" in text  # comment preserved
    assert "ANTHROPIC_API_KEY=secret-xyz" in text  # unrelated secret untouched
    assert "LOG_LEVEL=info" in text  # unrelated dial untouched
    assert "WORLD_TICK_NEW_STORIES_MIN=3" in text  # the override appended

    # update an EXISTING active line in place (no duplicate)
    dials.write(
        dials.apply_changes(
            dials.stage_group_edit(
                dials.group_by_slug("freshness"), {"freshness_mode": "avoid"}
            ).changes
        )
    )
    text = dials.current_text()
    assert text.count("LOG_LEVEL=info") == 1 and "ANTHROPIC_API_KEY=secret-xyz" in text
    assert "FRESHNESS_MODE=avoid" in text


# --- R5.0 (=E1.7): the schedule screen (queue / history / retry) -------------


@pytest.fixture
def sched_tmp(tmp_path, monkeypatch):
    """Point the schedule state, playlist, and segments dir at a scratch tmp dir."""
    seg = tmp_path / "segments"
    seg.mkdir()
    monkeypatch.setattr(settings, "segments_dir", seg)
    monkeypatch.setattr(settings, "schedule_state_path", seg / "schedule.json")
    monkeypatch.setattr(settings, "schedule_playlist_path", seg / "playlist.txt")
    return seg


def _sidecar(seg, sid, air_time, *, script=None, audio=False, dur=120.0):
    """Write a segment sidecar (a `Segment` asdict) into the scratch segments dir."""
    (seg / f"{sid}.json").write_text(
        json.dumps(
            {
                "id": sid,
                "format": "talk",
                "air_time": air_time,
                "actual_duration_sec": dur,
                "length_target_sec": int(dur),
                "script": script,
                "audio_path": str(seg / f"{sid}.mp3") if audio else None,
                "meta": {"program": "the_workshop", "program_name": "The Workshop"},
            }
        ),
        encoding="utf-8",
    )
    if audio:
        (seg / f"{sid}.mp3").write_bytes(b"x")


def test_drop_upcoming_only_removes_future(sched_tmp):
    """`drop_upcoming` drops a future slot; on-air/aired/unknown are immutable."""
    now = datetime(2026, 6, 22, 14, 30)
    state = {
        "entries": [
            {
                "id": "past-1",
                "format": "talk",
                "air_time": (now - timedelta(minutes=5)).isoformat(),
                "actual_duration_sec": 120,
            },
            {
                "id": "up-1",
                "format": "talk",
                "air_time": (now + timedelta(minutes=5)).isoformat(),
                "actual_duration_sec": 120,
            },
            {
                "id": "up-2",
                "format": "news",
                "air_time": (now + timedelta(minutes=10)).isoformat(),
                "actual_duration_sec": 120,
            },
        ]
    }
    scheduler._save_state(state)

    assert schedule_view.drop_upcoming("nope", now) is None  # unknown id
    assert schedule_view.drop_upcoming("past-1", now) is None  # already aired
    removed = schedule_view.drop_upcoming("up-1", now)
    assert removed is not None and removed["id"] == "up-1"
    ids = [e["id"] for e in scheduler._load_state()["entries"]]
    assert ids == ["past-1", "up-2"]  # only the one future slot is gone


def test_aired_history_paginates_and_reads_scripts(sched_tmp):
    """History is sidecar-sourced, newest-first, paginated, with scripts + audio."""
    now = datetime(2026, 6, 22, 14, 30)
    for i, off in enumerate((-30, -20, -10)):  # three aired
        at = (now + timedelta(minutes=off)).isoformat()
        _sidecar(sched_tmp, f"seg{i}", at, script=f"script {i}", audio=(i == 0))
    # a not-yet-aired sidecar must be excluded from history
    _sidecar(sched_tmp, "future", (now + timedelta(minutes=30)).isoformat())

    h = schedule_view.aired_history(now, page=0, per_page=2)
    assert h["total"] == 3 and h["pages"] == 2 and h["has_next"] and not h["has_prev"]
    assert [r["id"] for r in h["rows"]] == ["seg2", "seg1"]  # newest first
    assert h["rows"][0]["script"] == "script 2"

    h2 = schedule_view.aired_history(now, page=1, per_page=2)
    assert [r["id"] for r in h2["rows"]] == ["seg0"] and h2["rows"][0]["has_audio"]
    assert h2["has_prev"] and not h2["has_next"]


def test_audio_path_guard(sched_tmp):
    """Only a plain, existing segment id resolves to a file — no path traversal."""
    (sched_tmp / "ok.mp3").write_bytes(b"x")
    assert schedule_view.audio_path_for("ok") == (sched_tmp / "ok.mp3").resolve()
    assert schedule_view.audio_path_for("missing") is None
    assert schedule_view.audio_path_for("../secret") is None
    assert schedule_view.audio_path_for("a/b") is None


def test_playout_actions_wrap_service_commands_and_share_the_lock(no_launch):
    """Playout start/stop/restart exist, chain stop→start, and take the E1.1 lock."""
    assert set(actions.PLAYOUT_ACTIONS) == {
        "playout-start",
        "playout-stop",
        "playout-restart",
    }
    # an empty restart command means "stop then start" (two chained commands)
    assert actions.PLAYOUT_ACTIONS["playout-restart"].commands == [
        ["make", "stop"],
        ["make", "serve"],
    ]

    client = TestClient(panelapp.app, follow_redirects=False)
    r = client.post("/schedule/playout", data={"action_id": "nope"})
    assert r.status_code == 303 and "unknown" in r.headers["location"]

    r = client.post("/schedule/playout", data={"action_id": "playout-start"})
    assert r.status_code == 303 and "started" in r.headers["location"]
    assert actions.current_mutation() is not None  # start holds the mutation lock

    r = client.post("/schedule/playout", data={"action_id": "playout-stop"})
    assert "busy" in r.headers["location"]  # blocked while start still holds it


def test_skip_and_regenerate_routes(sched_tmp, no_launch):
    """Skip drops a slot; regenerate drops it then launches the top-up path."""
    now = datetime.now()
    scheduler._save_state(
        {
            "entries": [
                {
                    "id": "up-x",
                    "format": "talk",
                    "air_time": (now + timedelta(minutes=5)).isoformat(),
                    "actual_duration_sec": 120,
                },
                {
                    "id": "up-y",
                    "format": "news",
                    "air_time": (now + timedelta(minutes=10)).isoformat(),
                    "actual_duration_sec": 120,
                },
            ]
        }
    )
    client = TestClient(panelapp.app, follow_redirects=False)

    r = client.post("/schedule/segment/up-x/skip")
    assert r.status_code == 303 and "skipped" in r.headers["location"]
    assert [e["id"] for e in scheduler._load_state()["entries"]] == ["up-y"]

    r = client.post("/schedule/segment/up-y/regenerate")
    assert r.status_code == 303 and "started" in r.headers["location"]
    assert scheduler._load_state()["entries"] == []  # dropped
    assert actions.current_mutation() is not None  # top-up holds the lock


def test_schedule_page_renders(sched_tmp, no_launch):
    """The schedule screen renders (200) from a scratch state + one aired sidecar."""
    now = datetime.now()
    scheduler._save_state(
        {
            "entries": [
                {
                    "id": "up-z",
                    "format": "talk",
                    "program": "the_workshop",
                    "program_name": "The Workshop",
                    "air_time": (now + timedelta(minutes=4)).isoformat(),
                    "actual_duration_sec": 200,
                }
            ]
        }
    )
    _sidecar(
        sched_tmp,
        "aired-1",
        (now - timedelta(minutes=20)).isoformat(),
        script="hello world",
        audio=True,
    )

    client = TestClient(panelapp.app)
    resp = client.get("/schedule")
    assert resp.status_code == 200
    assert "Upcoming queue" in resp.text and "Aired history" in resp.text
    assert "regenerate" in resp.text and "Restart playout" in resp.text


# --- R5.1 (=E1.8): budgets — the usage ledger + the screen --------------------

from src import usage  # noqa: E402
from src.panel import budgets  # noqa: E402


@pytest.fixture
def clean_usage():
    """Reset the in-process usage accumulator around a test."""
    with usage._lock:
        usage._accum.clear()
    yield
    with usage._lock:
        usage._accum.clear()


def test_llm_cost_matches_pricing(monkeypatch):
    """Token→USD matches the price list (the costprobe rollup done-when)."""
    monkeypatch.setattr(
        settings,
        "model_prices",
        {
            "sonnet": {"input": 3.0, "output": 15.0},
            "haiku": {"input": 1.0, "output": 5.0},
        },
    )
    monkeypatch.setattr(settings, "price_cache_write_mult", 1.25)
    monkeypatch.setattr(settings, "price_cache_read_mult", 0.1)

    # a costprobe-style pass-1 row: bible cache created once
    fields = {
        "input_tokens": 50,
        "output_tokens": 16,
        "cache_creation_input_tokens": 50_000,
        "cache_read_input_tokens": 0,
    }
    expected = (50 * 3 + 50_000 * 3 * 1.25 + 16 * 15) / 1_000_000
    assert usage.llm_cost_usd("sonnet", fields) == pytest.approx(expected)

    # a cache-read row on haiku
    f2 = {
        "input_tokens": 2130,
        "output_tokens": 253,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 37_584,
    }
    exp2 = (2130 * 1 + 37_584 * 1 * 0.1 + 253 * 5) / 1_000_000
    assert usage.llm_cost_usd("haiku", f2) == pytest.approx(exp2)
    assert usage.llm_cost_usd("unknown-tier", fields) == 0.0  # unpriced → 0


def test_usage_records_by_job_and_merges(clean_usage):
    """LLM spend attributes to the job scope; TTS + embeddings track their kinds."""
    with usage.job("news"):
        usage._on_llm_usage(
            {
                "tier": "sonnet",
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }
        )
    with usage.job("talk"):
        usage._on_llm_usage(
            {
                "tier": "haiku",
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }
        )
    usage.record_tts(300, "kokoro")  # 300 chars ≈ 20s at 15 chars/s
    usage.record_embeddings(3)

    rollup = usage._merge({}, {k: dict(v) for k, v in usage._accum.items()})
    day = rollup["days"][usage.date.today().isoformat()]
    assert set(day) == {"news", "talk", "tts", "embeddings"}
    assert day["news"]["usd"] == pytest.approx((100 * 3 + 50 * 15) / 1_000_000)
    assert day["tts"]["tts_sec"] == pytest.approx(20.0)
    assert day["embeddings"]["emb_count"] == 3


def test_flush_persists_and_clears(clean_usage, monkeypatch):
    """flush() merges the tally into the rollup row and clears the accumulator."""

    class _FakeConn:
        def __init__(self):
            self.stored = None

        def execute(self, sql, params=()):  # noqa: ANN001
            conn = self

            class _Res:
                def fetchone(self_inner):  # noqa: ANN001, N805
                    return None  # empty rollup to start

            if sql.strip().upper().startswith("INSERT"):
                conn.stored = params  # set_state's (key, value)
            return _Res()

    with usage.job("tick"):
        usage._on_llm_usage(
            {
                "tier": "sonnet",
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
            }
        )
    fake = _FakeConn()
    assert usage.flush(conn=fake) is True
    assert fake.stored is not None and fake.stored[0] == usage.USAGE_ROLLUP_KEY
    written = json.loads(fake.stored[1])
    day = written["days"][usage.date.today().isoformat()]
    assert day["tick"]["usd"] == pytest.approx((1000 * 3 + 200 * 15) / 1_000_000)
    with usage._lock:
        assert not usage._accum  # cleared after a successful flush


def test_budget_alert_at_forced_low_threshold(monkeypatch):
    """The alert flips on when spend crosses the (forced low) threshold."""
    today = datetime.now().date().isoformat()
    rollup = {"days": {today: {"tick": {"usd": 0.9}}}}
    monkeypatch.setattr(settings, "budget_daily_usd", 1.0)
    monkeypatch.setattr(settings, "budget_alert_pct", 80.0)
    status = usage.budget_status(rollup)
    assert status["pct"] == pytest.approx(90.0)
    assert status["alert"] and not status["over"]
    # a tiny budget makes today's spend blow past the line
    monkeypatch.setattr(settings, "budget_daily_usd", 0.5)
    over = usage.budget_status(rollup)
    assert over["over"] and over["alert"]


def test_budgets_page_renders_and_degrades(monkeypatch):
    """/budgets renders the bar from a seeded rollup, and 200s when the DB is down."""
    from contextlib import contextmanager

    today = datetime.now().date().isoformat()
    rollup = {
        "days": {
            today: {
                "tick": {
                    "usd": 0.4,
                    "calls": 2,
                    "input_tokens": 1000,
                    "output_tokens": 100,
                    "cache_read_input_tokens": 0,
                },
                "tts": {"usd": 0.0, "tts_sec": 120},
            }
        }
    }

    @contextmanager
    def _fake_connect():
        yield object()

    monkeypatch.setattr(budgets.store, "connect", _fake_connect)
    monkeypatch.setattr(budgets.usage, "load_rollup", lambda conn: rollup)
    monkeypatch.setattr(settings, "budget_daily_usd", 1.0)

    client = TestClient(panelapp.app)
    resp = client.get("/budgets")
    assert resp.status_code == 200
    assert "World tick" in resp.text and "Today by job" in resp.text

    # DB down → the page degrades to a note, never a 500
    def _boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(budgets.store, "connect", _boom)
    resp2 = client.get("/budgets")
    assert resp2.status_code == 200 and "unavailable" in resp2.text.lower()


# --- R5.2 (=E1.9): the world screen — digest + arcs + timeline ----------------

from datetime import datetime as _dt  # noqa: E402

from src.panel import world_view  # noqa: E402
from src.world import digest  # noqa: E402


class _FakeStory:
    def __init__(self, sid, title, stage="rumour", tags=()):
        self.id = sid
        self.title = title
        self.arc_stage = stage
        self.tags = list(tags)


class _FakeBeat:
    def __init__(self, title, when, planned=False):
        self.title = title
        self.in_world_datetime = when
        self.planned = planned


def test_digest_build_facts_from_tick_result(monkeypatch):
    """build_facts turns a TickResult + store reads into the digest's raw material."""
    from src.world import clock
    from src.world.world_tick import TickResult

    now = _dt(2026, 6, 22, 3, 0)
    iw = clock.to_inworld(now)  # beats live in in-world time (year + offset)
    stories = {
        "st-new": _FakeStory("st-new", "The relay goes dark", tags=["tech"]),
        "st-adv": _FakeStory(
            "st-adv", "The harvest dispute", "developing", ["economy"]
        ),
    }
    # a still-to-come planned beat later "today" (in-world 15:00 > in-world now 03:00)
    beats = {
        "st-new": [_FakeBeat("first reports", iw)],
        "st-adv": [
            _FakeBeat("morning: a claim", iw),
            _FakeBeat("afternoon: a ruling", iw.replace(hour=15), planned=True),
        ],
    }
    monkeypatch.setattr(digest.store, "get_story", lambda conn, sid: stories.get(sid))
    monkeypatch.setattr(
        digest.store, "story_beats", lambda conn, sid: beats.get(sid, [])
    )
    monkeypatch.setattr(digest.store, "figures_for_story", lambda conn, sid: [1, 2])
    monkeypatch.setattr(digest.store, "quotes_for_story", lambda conn, sid: [1])

    result = TickResult(
        tick=7,
        proposed=3,
        accepted=1,
        dropped=1,
        advanced=1,
        story_ids=["st-new"],
        advanced_ids=["st-adv"],
    )
    facts = digest.build_facts(object(), result, kind="tick", now=now)

    assert facts["tick"] == 7 and facts["accepted"] == 1
    assert facts["new_stories"][0]["title"] == "The relay goes dark"
    assert facts["new_figures"] == 2 and facts["new_quotes"] == 1
    adv = facts["advanced"][0]
    assert adv["title"] == "The harvest dispute" and adv["stage"] == "developing"
    assert adv["next_planned"]["title"] == "afternoon: a ruling"  # the planned beat


def test_digest_generate_and_store_guards(monkeypatch):
    """Disabled → None; a quiet micro-tick → None; an acting run stores the text."""
    from src.world.world_tick import MicroTickResult

    monkeypatch.setattr(settings, "world_digest_enabled", False)
    assert digest.generate_and_store(object(), kind="tick") is None  # disabled

    monkeypatch.setattr(settings, "world_digest_enabled", True)
    quiet = MicroTickResult(micro_tick=2, acted=False, reason="dice")
    assert digest.generate_and_store(quiet, kind="micro-tick") is None  # quiet run

    # an acting micro-tick stores a digest (LLM + DB stubbed)
    from contextlib import contextmanager

    saved = {}

    class _Conn:
        pass

    @contextmanager
    def _fake_connect():
        yield _Conn()

    monkeypatch.setattr(digest.store, "connect", _fake_connect)
    monkeypatch.setattr(digest.store, "get_state", lambda conn, key: None)
    monkeypatch.setattr(
        digest.store, "set_state", lambda conn, key, value: saved.update({key: value})
    )
    monkeypatch.setattr(
        digest.store,
        "get_story",
        lambda conn, sid: _FakeStory(sid, "A late complication"),
    )
    monkeypatch.setattr(
        digest, "generate_text", lambda facts: "Something moved tonight."
    )

    acted = MicroTickResult(micro_tick=3, acted=True, story_id="st-x", beat_id="b1")
    text = digest.generate_and_store(acted, kind="micro-tick")
    assert text == "Something moved tonight."
    stored = json.loads(saved[digest.DIGEST_KEY])
    assert stored[0]["kind"] == "micro-tick" and stored[0]["text"] == text


def test_world_view_assembles_arcs_and_timeline(monkeypatch):
    """view() builds arcs (next planned beat) + today's beats; degrades on DB down."""
    from contextlib import contextmanager

    from src.world import clock

    now = _dt(2026, 6, 22, 9, 0)
    iw_today = clock.to_inworld(now).date()
    story = _FakeStory("st-1", "The water tariff", "developing", ["economy"])
    beats = [
        _FakeBeat("morning claim", clock.to_inworld(now).replace(hour=7)),
        _FakeBeat(
            "afternoon ruling", clock.to_inworld(now).replace(hour=15), planned=True
        ),
    ]

    @contextmanager
    def _fake_connect():
        yield object()

    monkeypatch.setattr(world_view.store, "connect", _fake_connect)
    monkeypatch.setattr(world_view.store, "active_stories", lambda conn: [story])
    monkeypatch.setattr(world_view.store, "story_beats", lambda conn, sid: beats)
    monkeypatch.setattr(
        world_view.digest,
        "recent",
        lambda conn, limit=None: [
            {"kind": "tick", "text": "hi", "when": now.isoformat()}
        ],
    )

    out = world_view.view(now)
    assert out["available"] and out["arcs"][0]["title"] == "The water tariff"
    assert out["arcs"][0]["next_planned"]["title"] == "afternoon ruling"
    # both beats are dated to in-world today → both on the timeline, hour-sorted
    assert [b["when"] for b in out["timeline"]] == ["07:00", "15:00"]
    assert iw_today == clock.to_inworld(now).date()  # sanity: same in-world day

    # DB down → readable note, not a 500
    def _boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(world_view.store, "connect", _boom)
    assert world_view.view(now)["available"] is False


def test_world_page_renders_and_run_button(monkeypatch, no_launch):
    """/world renders from a stubbed view; /world/run starts the tick under the lock."""
    monkeypatch.setattr(
        world_view,
        "view",
        lambda now=None: {
            "available": True,
            "error": None,
            "digests": [
                {
                    "kind": "tick",
                    "tick": 5,
                    "when": "2026-06-22T03:00:00",
                    "text": "The relay recovered overnight.",
                }
            ],
            "arcs": [
                {
                    "id": "s1",
                    "title": "The relay",
                    "stage": "developing",
                    "tags": ["tech"],
                    "latest": "first reports",
                    "next_planned": None,
                }
            ],
            "timeline": [],
            "in_world_today": "Monday 2626-06-22",
        },
    )
    client = TestClient(panelapp.app, follow_redirects=False)
    resp = client.get("/world")
    assert resp.status_code == 200
    assert "The relay recovered overnight." in resp.text
    assert "Arcs in flight" in resp.text and "World tick" in resp.text

    r = client.post("/world/run", data={"action_id": "world-tick"})
    assert r.status_code == 303 and "started" in r.headers["location"]
    assert actions.current_mutation() is not None  # the tick holds the lock

    r = client.post("/world/run", data={"action_id": "nope"})
    assert "unknown" in r.headers["location"]

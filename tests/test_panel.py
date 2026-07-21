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
from src.panel import actions, grid_edit, views
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

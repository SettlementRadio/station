"""D8 — commercials & sponsorship: the spot builder, the break cadence, sponsors.

Surgical, token-free (PHASE_D_COMMERCIALS_TASKS D8.3): `llm.generate` / TTS are
mocked everywhere; the DB tests use the rollback fixture and skip without
Postgres. Covered: the commercial/promo builder (mode + meta + IP rules in the
prompt), the C0 gate fallback (a planted flag lands on evergreen, never air),
the production-level degrades, the daypart break cadence + per-break cap, the
sponsors run window, the binding "Powered by" wording, and that an empty
sponsors table airs nothing.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from src import scheduler
from src.config import settings
from src.formats import commercial, sponsor
from src.safety import SafetyResult
from src.segment import Segment
from src.world import store
from src.world.context import AssembledContext
from src.world.programming import ClockStep, Program
from src.world.store import CastMember, Sponsor

NOW = datetime(2026, 7, 6, 12, 0)  # a Monday midday

CARD = CastMember(
    id="vell", name="Vell", card_text="the calm night host", logical_voice="vell_night"
)


def _ctx() -> AssembledContext:
    return AssembledContext(
        cached_context="canon", dynamic="A quiet day on the relay.", speakers=[CARD]
    )


def _fake_tts(text, voice, out_path, **kw):
    from pathlib import Path

    Path(out_path).write_bytes(b"mp3")
    return out_path


@contextlib.contextmanager
def _spot_mocks(reply: str = "Visit the Relay Noodle Counter tonight."):
    """The builder's externals, mocked: LLM reply, safety OK, TTS to fake bytes.

    `commercial.py` and `safety.py` share ONE `providers.llm` module, so a single
    dispatcher answers both calls (patching each import separately would just
    re-patch the same attribute). Yields the list of spot system prompts.
    """
    spot_systems: list[str] = []

    def fake_generate(prompt, *, system="", **kw):
        if "content-safety reviewer" in system:
            return "OK"
        spot_systems.append(system)
        return reply

    with (
        patch("src.providers.llm.generate", side_effect=fake_generate),
        patch("src.formats.common.tts.synthesize", side_effect=_fake_tts),
        patch("src.evergreen.tts.synthesize", side_effect=_fake_tts),
    ):
        yield spot_systems


# --- The builder: modes, meta, prompt rules (D8.0) ----------------------------


def test_commercial_produces_spot(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    with _spot_mocks() as spot_systems:
        seg = commercial.spot(NOW, _ctx(), mode="commercial")
    assert seg.format == "commercial"
    assert seg.disclosure is True
    assert seg.meta["mode"] == "commercial"
    assert seg.meta["production_level_effective"] == 1
    # The IP boundary is enforced IN the prompt (the gate backs it up).
    system = spot_systems[0]
    assert "NEVER name a real brand" in system
    assert "never mention being an AI" in system


def test_promo_records_what_it_promotes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    with _spot_mocks(reply="Stay with us through the deep night."):
        seg = commercial.spot(NOW, _ctx(), mode="promo")
    assert seg.format == "promo"
    assert seg.meta["mode"] == "promo"
    # The subject is picked in code (truthful meta): a named grid show or the station.
    assert seg.meta["promoted"]


def test_unknown_mode_raises():
    with pytest.raises(ValueError, match="unknown spot mode"):
        commercial.spot(NOW, _ctx(), mode="jingle")


def test_flagged_draft_falls_back_to_evergreen(tmp_path, monkeypatch):
    """C0: a persistently flagged spot NEVER airs — the slot drops to evergreen."""
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    flagged = ("Buy RealBrand now!!", SafetyResult(False, "FLAG: real brand", "llm"))
    with (
        patch("src.formats.commercial.generate_safe", return_value=flagged),
        patch("src.evergreen.tts.synthesize", side_effect=_fake_tts),
    ):
        seg = commercial.spot(NOW, _ctx(), mode="commercial")
    assert seg.format == "evergreen"
    assert seg.meta["fallback"] is True
    assert seg.meta["replacing_format"] == "commercial"
    assert "RealBrand" not in (seg.script or "")  # the flagged text is not the air


@pytest.mark.parametrize("level", [3, 4])
def test_unbuilt_levels_degrade_to_plain_read(tmp_path, monkeypatch, level):
    """L3 needs D9/D10; L4 needs a curated brand clip — both degrade to L1."""
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    monkeypatch.setattr(settings, "format_commercial_production_level", level)
    with _spot_mocks():
        seg = commercial.spot(NOW, _ctx(), mode="commercial")
    assert seg.meta["production_level"] == level
    assert seg.meta["production_level_effective"] == 1


# --- The break cadence (D8.1): daypart-driven, capped, bracketed --------------

_BREAKY = Program(
    id="breaky",
    name="Breaky Show",
    hosts=("vell", "wren"),
    framing="solo",
    daypart="daytime",
    clock=(ClockStep("talk"),),
    rotation=(),
    break_every=2,
)


def _fake_make_format_segment(name, now_iso, *, topic=None, speakers=None):
    from pathlib import Path

    seg_id = f"{name}-{now_iso.replace(':', '').replace('-', '')}"
    audio = settings.segments_dir / f"{seg_id}.mp3"
    Path(audio).write_bytes(b"fake")
    return Segment(
        id=seg_id,
        format=name,
        length_target_sec=300,
        air_time=now_iso,
        script="fake",
        audio_path=str(audio),
        disclosure=True,
        meta={},
    )


def _sting_stub(moment, now):
    return Segment(
        id=f"sting-{moment}-{now:%Y%m%dT%H%M%S}",
        format="sting",
        length_target_sec=2,
        air_time=now.isoformat(),
        script=None,
        audio_path=None,
        disclosure=False,
        meta={"sting": moment},
    )


@contextlib.contextmanager
def _topup_mocks(program: Program):
    """A hermetic top_up: fixed program, fake generation, stub stings, no DB/IO."""

    @contextlib.contextmanager
    def _no_db():
        yield None

    with (
        patch.object(scheduler, "make_format_segment", _fake_make_format_segment),
        patch.object(scheduler, "ensure_fallback_assets", lambda: None),
        patch.object(scheduler, "record_airplay_features", lambda seg: None),
        patch.object(scheduler, "sweep_airplay", lambda now: None),
        patch.object(scheduler, "apply_bed", lambda seg, program: seg),
        patch.object(scheduler, "break_sting_segment", _sting_stub),
        patch.object(scheduler.programming, "program_for", lambda now: program),
        patch.object(scheduler.store, "connect", _no_db),
        patch.object(scheduler.store, "active_sponsors", lambda conn, now: []),
    ):
        yield


def _redirect_scheduler_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    monkeypatch.setattr(settings, "schedule_state_path", tmp_path / "schedule.json")
    monkeypatch.setattr(settings, "schedule_playlist_path", tmp_path / "playlist.txt")
    monkeypatch.setattr(settings, "nowplaying_feed_path", tmp_path / "nowplaying.json")
    monkeypatch.setattr(settings, "disclosure_enabled", False)
    monkeypatch.setattr(settings, "production_ident_every_n", 0)
    monkeypatch.setattr(settings, "production_theme_at_boundary", False)
    monkeypatch.setattr(settings, "buffer_depth_hours", 0.6)  # ~7 fake 300s slots


def test_break_fires_on_program_cadence_bracketed(tmp_path, monkeypatch):
    _redirect_scheduler_paths(tmp_path, monkeypatch)
    with _topup_mocks(_BREAKY):
        entries = scheduler.top_up(NOW)
    fmts = [e["format"] for e in entries]
    first_spot = fmts.index("commercial")
    # break_every=2: exactly two content segments precede the first break.
    assert fmts[:first_spot].count("talk") == 2
    # Bracketed: sting immediately before and after the spot.
    assert fmts[first_spot - 1] == "sting"
    assert entries[first_spot - 1]["id"].startswith("sting-break_in")
    assert fmts[first_spot + 1] == "sting"
    assert entries[first_spot + 1]["id"].startswith("sting-break_out")


def test_break_respects_max_spots_cap(tmp_path, monkeypatch):
    _redirect_scheduler_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "commercial_break_max_segments", 2)
    monkeypatch.setattr(settings, "commercial_break_promo_every_n", 0)
    with _topup_mocks(_BREAKY):
        entries = scheduler.top_up(NOW)
    fmts = [e["format"] for e in entries]
    # Every run of consecutive spots is at most the cap.
    run, longest = 0, 0
    for f in fmts:
        run = run + 1 if f == "commercial" else 0
        longest = max(longest, run)
    assert 0 < longest <= 2


def test_no_breaks_when_program_declares_none(tmp_path, monkeypatch):
    _redirect_scheduler_paths(tmp_path, monkeypatch)
    quiet = Program(
        id="quiet",
        name="Quiet Show",
        hosts=("vell",),
        framing="solo",
        daypart="deep night",
        clock=(ClockStep("talk"),),
        rotation=(),
        break_every=0,
    )
    with _topup_mocks(quiet):
        entries = scheduler.top_up(NOW)
    assert not [e for e in entries if e["format"] in ("commercial", "promo")]


def test_promo_rotation_within_breaks(tmp_path, monkeypatch):
    """Every Nth spot across breaks is a station promo (the persisted counter)."""
    _redirect_scheduler_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "buffer_depth_hours", 1.5)
    monkeypatch.setattr(settings, "commercial_break_promo_every_n", 2)
    with _topup_mocks(_BREAKY):
        entries = scheduler.top_up(NOW)
    spots = [e["format"] for e in entries if e["format"] in ("commercial", "promo")]
    assert len(spots) >= 2
    assert spots[0] == "commercial" and spots[1] == "promo"  # every 2nd is a promo


# --- Sponsors (D8.2): run window, wording, rotation, empty table --------------


@pytest.fixture
def db():
    """A store connection with the schema, that ALWAYS rolls back at teardown."""
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001 - any connect failure -> skip, not fail
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001 - e.g. CREATE EXTENSION unavailable
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"schema unavailable: {exc}")
    try:
        yield conn
    finally:
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _sponsor(sid="test-sp", **kw) -> Sponsor:
    defaults: dict = {
        "name": "a friend of the signal",
        "powered_by_text": "Keeping the long night lit.",
        "run_start": NOW - timedelta(days=5),
        "run_end": NOW + timedelta(days=5),
    }
    defaults.update(kw)
    return Sponsor(id=sid, **defaults)


def test_active_sponsors_honours_run_window(db):
    store.insert_sponsors(db, [_sponsor()])
    assert "test-sp" in {s.id for s in store.active_sponsors(db, NOW)}
    assert "test-sp" not in {
        s.id for s in store.active_sponsors(db, NOW - timedelta(days=10))
    }
    assert "test-sp" not in {
        s.id for s in store.active_sponsors(db, NOW + timedelta(days=10))
    }
    # Half-open: the run_end instant itself is already outside.
    assert "test-sp" not in {
        s.id for s in store.active_sponsors(db, NOW + timedelta(days=5))
    }


def test_open_ended_window_and_counts(db):
    store.insert_sponsors(db, [_sponsor("open-sp", run_start=None, run_end=None)])
    assert "open-sp" in {s.id for s in store.active_sponsors(db, NOW)}
    assert store.counts(db)["sponsors"] >= 1  # catalog counted, never world-wiped


def test_powered_by_wording_is_enforced():
    # The lead-in is templated — "powered by" is structural.
    sp = _sponsor(powered_by_text="Proudly Sponsored By the relay guild.")
    script = sponsor.powered_by_script(sp)
    assert script.startswith(
        "This hour of Settlement Radio is powered by a friend of the signal."
    )
    assert "sponsored by" not in script.lower()
    assert "powered by the relay guild" in script


def test_blank_blurb_is_lead_in_only():
    script = sponsor.powered_by_script(_sponsor(powered_by_text=""))
    lead_only = "This hour of Settlement Radio is powered by a friend of the signal."
    assert script == lead_only


def test_pick_sponsor_weighted_rotation():
    a = _sponsor("a", weight=2)
    b = _sponsor("b", weight=1)
    picks = [sponsor.pick_sponsor([a, b], i).id for i in range(6)]
    assert picks == ["a", "a", "b", "a", "a", "b"]
    with pytest.raises(ValueError):
        sponsor.pick_sponsor([], 0)


def test_sponsor_read_renders_gated_text(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    with (
        patch("src.formats.sponsor.tts.synthesize", side_effect=_fake_tts),
        patch("src.safety.llm.generate", return_value="OK"),
    ):
        seg = sponsor.sponsor_read_segment(NOW, _sponsor())
    assert seg is not None
    assert seg.format == "sponsor"
    assert seg.meta["kind"] == "read"
    assert "powered by" in seg.script.lower()


def test_flagged_sponsor_blurb_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    flagged = SafetyResult(False, "FLAG: bad", "llm")
    with patch("src.formats.sponsor.safety_check", return_value=flagged):
        seg = sponsor.sponsor_read_segment(NOW, _sponsor())
    assert seg is None  # skipped, never aired


def test_empty_sponsors_table_airs_no_reads(tmp_path, monkeypatch):
    """The pre-CM state: breaks fire, but no sponsor read is ever placed."""
    _redirect_scheduler_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "sponsor_read_every_n_breaks", 1)
    with _topup_mocks(_BREAKY):  # active_sponsors -> [] inside
        entries = scheduler.top_up(NOW)
    assert [e for e in entries if e["format"] == "commercial"]  # breaks ran
    assert not [e for e in entries if e["format"] == "sponsor"]


def test_sponsor_read_placed_inside_break_bracket(tmp_path, monkeypatch):
    _redirect_scheduler_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(settings, "sponsor_read_every_n_breaks", 1)
    read = Segment(
        id="sponsor-test-sp-x",
        format="sponsor",
        length_target_sec=15,
        air_time=NOW.isoformat(),
        script="Powered by a friend of the signal.",
        audio_path=None,
        disclosure=True,
        meta={"sponsor": "test-sp", "kind": "read"},
    )
    with (
        _topup_mocks(_BREAKY),
        patch.object(scheduler.store, "active_sponsors", lambda c, n: [_sponsor()]),
        patch.object(scheduler, "sponsor_read_segment", lambda now, sp: read),
    ):
        entries = scheduler.top_up(NOW)
    fmts = [e["format"] for e in entries]
    j = fmts.index("sponsor")
    # Inside the bracket: after the spot(s), before the break_out sting.
    assert fmts[j - 1] in ("commercial", "promo")
    assert entries[j + 1]["id"].startswith("sting-break_out")

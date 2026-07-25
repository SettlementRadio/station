"""Tests for R7.0 — the two SLOW public feeds (src/publicfeeds.py) + the tiling.

Three promises: (1) the published schedule is the SAME answer the air gives — the
tiling is gap-free and agrees with `program_for` at every spot-checked minute; (2) both
feeds are PUBLIC-SAFE — an explicit allow-list, and in particular the internal
editorial `brief` and the DJ `card_text` (a prompt, not copy) never appear; (3) they
degrade rather than publish something worse (no cast → no DJs file, not an empty one).

Postgres is stubbed (a fixture cast); the grid is the real `docs/programming/grid.yaml`,
because "the feed matches the grid" is the property under test.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from src import nowplaying, publicfeeds
from src.disclosure import DISCLOSURE_LINE
from src.formats import music
from src.world import programming
from src.world.store import CastMember, Track

NOW = datetime(2026, 6, 22, 5, 30, 0)  # a Monday, in First Light


def _cast() -> dict[str, CastMember]:
    """A fixture cast with the two R7.0 public fields filled in."""
    return {
        m.id: m
        for m in [
            CastMember(
                id="vell",
                name="Vell",
                card_text="SECRET PROMPT: Vell never breaks character.",
                logical_voice="vell_night",
                tags=["night"],
                based="station",
                role="the night shift",
                public_bio="Vell keeps the night shift.",
            ),
            CastMember(
                id="sera",
                name="Sera",
                card_text="SECRET PROMPT: Sera is never live in the booth.",
                logical_voice="sera_field",
                tags=["travel"],
                based="field",
                role="the travelling correspondent",
                public_bio="Sera has been travelling for twelve years.",
            ),
        ]
    }


def _track() -> Track:
    """A curated track, for the public-lore allow-list check."""
    return Track(
        id="t-001",
        title="The Slow Star",
        in_world_artist="Halcyon Drift",
        mood="warm",
        audio_path="assets/music/t-001.mp3",
        album="Long Way Round",
        era="24th century",
        in_world_year=2611,
        story_blurb="Written on a six-month crossing.",
    )


def _nowplaying_state() -> dict:
    """One on-air entry in the shape the scheduler persists (see test_nowplaying)."""
    return {
        "entries": [
            {
                "id": "talk-001",
                "format": "talk",
                "program": "first_light",
                "program_name": "First Light",
                "audio_path": "/segments/talk-001.mp3",
                "air_time": (NOW - timedelta(minutes=2)).isoformat(),
                "actual_duration_sec": 300.0,
                "length_target_sec": 300,
            }
        ],
        "last_topup_at": NOW.isoformat(),
    }


def _stub_names(monkeypatch) -> None:
    """Keep the now-playing host lookup DB-free."""
    monkeypatch.setattr(
        nowplaying, "_name_map", lambda ids: {i: i.title() for i in ids}
    )


# --- The tiling is the same answer the air gives -----------------------------


def test_day_tiling_covers_the_whole_day_without_gaps():
    day = date(2026, 6, 22)
    runs = programming.day_tiling(day)

    assert runs, "a tiled grid must produce runs"
    assert runs[0][0] == datetime(2026, 6, 22, 0, 0)
    assert runs[-1][1] == datetime(2026, 6, 23, 0, 0)
    for (_s1, e1, _p1), (s2, _e2, _p2) in zip(runs, runs[1:], strict=False):
        assert e1 == s2, "runs must be contiguous — no gaps, no overlaps"
    # Merged: no two adjacent runs are the same show.
    ids = [p.id for _s, _e, p in runs]
    assert all(a != b for a, b in zip(ids, ids[1:], strict=False))


@pytest.mark.parametrize(
    "minute", [0, 7, 61, 330, 449, 450, 719, 900, 1199, 1200, 1439]
)
def test_day_tiling_agrees_with_program_for(minute):
    """The published schedule can never disagree with what actually airs."""
    at = datetime(2026, 6, 22) + timedelta(minutes=minute)
    runs = programming.day_tiling(at.date())
    covering = [p for s, e, p in runs if s <= at < e]
    assert len(covering) == 1
    assert covering[0].id == programming.program_for(at).id


def test_week_tiling_returns_seven_consecutive_days():
    week = programming.week_tiling(date(2026, 6, 22), 7)
    assert [d for d, _runs in week] == [
        date(2026, 6, 22) + timedelta(days=i) for i in range(7)
    ]


# --- The schedule feed -------------------------------------------------------


def test_schedule_feed_shape_and_allow_list():
    feed = publicfeeds.build_schedule_feed(NOW, _cast())

    assert set(feed) == {
        "station",
        "disclosure",
        "updated_at",
        "programs",
        "days",
    }
    assert feed["disclosure"] == DISCLOSURE_LINE  # the hard rule, on every feed
    for program in feed["programs"].values():
        assert set(program) == {"name", "tagline", "hosts"}
    for day in feed["days"]:
        assert set(day) == {"date", "weekday", "entries"}
        for entry in day["entries"]:
            assert set(entry) == {"program", "start", "end"}
            # every entry resolves in the programme directory
            assert entry["program"] in feed["programs"]

    assert feed["days"][0]["date"] == NOW.date().isoformat()
    assert feed["days"][0]["weekday"] == "mon"
    assert len(feed["days"]) == publicfeeds.settings.schedule_feed_days


def test_schedule_feed_publishes_taglines_never_briefs():
    feed = publicfeeds.build_schedule_feed(NOW, _cast())
    blob = json.dumps(feed)

    for pid, published in feed["programs"].items():
        program = programming.all_programs()[pid]
        assert published["tagline"] == program.public_tagline
        if program.brief:
            assert program.brief not in blob, f"{pid}'s internal brief leaked"
    # A spot-check that the direction language itself is absent from the payload.
    assert "never muse" not in blob.lower()


def test_schedule_feed_times_are_naive_settlement_wall_clock():
    feed = publicfeeds.build_schedule_feed(NOW, _cast())
    for entry in feed["days"][0]["entries"]:
        # No zone suffix — the site prints these as given ("settlement time (yours)").
        assert not entry["start"].endswith("Z") and "+" not in entry["start"]
        assert datetime.fromisoformat(entry["start"]).tzinfo is None


def test_schedule_feed_host_names_degrade_without_a_cast():
    """A store outage costs display names, never the file."""
    feed = publicfeeds.build_schedule_feed(NOW, {})
    hosts = {h for p in feed["programs"].values() for h in p["hosts"]}
    assert "Vell" in hosts  # titlecased from the id `vell`
    assert "The Archivist" in hosts  # `the-archivist` → readable fallback


def test_write_schedule_feed_writes_rereadable_json(monkeypatch, tmp_path):
    path = tmp_path / "schedule-public.json"
    monkeypatch.setattr(publicfeeds.settings, "schedule_feed_path", path)
    returned = publicfeeds.write_schedule_feed(NOW, _cast())
    assert json.loads(path.read_text(encoding="utf-8")) == returned


# --- The DJs feed ------------------------------------------------------------


def test_djs_feed_shape_and_allow_list():
    feed = publicfeeds.build_djs_feed(NOW, _cast())

    assert set(feed) == {"station", "disclosure", "updated_at", "djs"}
    for dj in feed["djs"]:
        assert set(dj) == {"id", "name", "role", "bio", "based", "shows"}
        for show in dj["shows"]:
            assert set(show) == {"id", "name"}
    assert [d["name"] for d in feed["djs"]] == ["Sera", "Vell"]  # sorted by name


def test_djs_feed_never_publishes_the_card_text():
    """The card is a PROMPT. Only the operator-authored bio may go out."""
    feed = publicfeeds.build_djs_feed(NOW, _cast())
    blob = json.dumps(feed)

    assert "SECRET PROMPT" not in blob
    assert "card_text" not in blob
    by_id = {d["id"]: d for d in feed["djs"]}
    assert by_id["vell"]["bio"] == "Vell keeps the night shift."
    assert by_id["vell"]["role"] == "the night shift"
    assert by_id["sera"]["based"] == "field"  # the correspondent badge


def test_djs_feed_shows_come_from_the_grid():
    feed = publicfeeds.build_djs_feed(NOW, _cast())
    by_id = {d["id"]: d for d in feed["djs"]}

    vell_shows = {s["id"] for s in by_id["vell"]["shows"]}
    assert "long_night" in vell_shows  # Vell's own night
    assert "the_circuit" not in vell_shows  # Kael's desk, not Vell's
    # no duplicates even though a daily show tiles seven times
    ids = [s["id"] for s in by_id["vell"]["shows"]]
    assert len(ids) == len(set(ids))
    for show in by_id["vell"]["shows"]:
        assert programming.all_programs()[show["id"]].name == show["name"]


def test_djs_feed_is_skipped_rather_than_published_empty(monkeypatch, tmp_path):
    """No cast (store down / unseeded) must leave the last good file standing."""
    path = tmp_path / "djs-public.json"
    monkeypatch.setattr(publicfeeds.settings, "djs_feed_path", path)

    good = publicfeeds.write_djs_feed(NOW, _cast())
    assert good is not None and path.exists()

    assert publicfeeds.write_djs_feed(NOW, {}) is None
    assert json.loads(path.read_text(encoding="utf-8")) == good  # untouched


def test_write_feeds_writes_both_from_one_cast_read(monkeypatch, tmp_path):
    monkeypatch.setattr(
        publicfeeds.settings, "schedule_feed_path", tmp_path / "schedule.json"
    )
    monkeypatch.setattr(publicfeeds.settings, "djs_feed_path", tmp_path / "djs.json")
    reads = {"n": 0}

    def _one_read():
        reads["n"] += 1
        return _cast()

    monkeypatch.setattr(publicfeeds, "cast_map", _one_read)
    feeds = publicfeeds.write_feeds(NOW)

    assert reads["n"] == 1, "both feeds share ONE cast read"
    assert set(feeds) == {"schedule", "djs"}
    assert (tmp_path / "schedule.json").exists() and (tmp_path / "djs.json").exists()


# --- The tagline fallback ----------------------------------------------------


def test_public_tagline_falls_back_to_the_briefs_first_sentence():
    tagged = programming.Program(
        id="p",
        name="P",
        hosts=(),
        framing="solo",
        daypart="",
        clock=(),
        rotation=(),
        tagline="The public line.",
        brief="An internal first sentence. Never do the other thing.",
    )
    assert tagged.public_tagline == "The public line."

    untagged = programming.Program(
        id="p",
        name="P",
        hosts=(),
        framing="solo",
        daypart="",
        clock=(),
        rotation=(),
        brief="An internal first sentence. Never do the other thing.",
    )
    assert untagged.public_tagline == "An internal first sentence."

    bare = programming.Program(
        id="p", name="P", hosts=(), framing="solo", daypart="", clock=(), rotation=()
    )
    assert bare.public_tagline == ""


# --- The web contract: the checked-in TS types must match what we publish -----

_TYPES_TS = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "types.ts"


def _ts_interfaces() -> dict[str, set[str]]:
    """`web/src/lib/types.ts` → {interface name: field names}, `extends` resolved.

    A deliberately crude parse (field lines are `name: type;`): the point is to catch
    DRIFT between the published JSON and the types the site fetches with, not to
    reimplement TypeScript.
    """
    text = _TYPES_TS.read_text(encoding="utf-8")
    raw: dict[str, tuple[str | None, set[str]]] = {}
    for m in re.finditer(
        r"export interface (\w+)(?:\s+extends\s+(\w+))?\s*\{(.*?)\n\}", text, re.S
    ):
        name, parent, body = m.group(1), m.group(2), m.group(3)
        fields = set(re.findall(r"^\s{2}(\w+)\??:", body, re.M))
        raw[name] = (parent, fields)

    def resolve(name: str) -> set[str]:
        parent, fields = raw[name]
        return fields | (resolve(parent) if parent else set())

    return {name: resolve(name) for name in raw}


def test_ts_types_match_the_published_feeds(monkeypatch):
    """The site's types and the station's feeds are one contract — keep them equal."""
    ts = _ts_interfaces()
    schedule = publicfeeds.build_schedule_feed(NOW, _cast())
    djs = publicfeeds.build_djs_feed(NOW, _cast())

    _stub_names(monkeypatch)
    nowfeed = nowplaying.build_feed(NOW, _nowplaying_state())

    assert ts["ScheduleFeed"] == set(schedule)
    assert ts["PublicProgram"] == set(next(iter(schedule["programs"].values())))
    assert ts["ScheduleDay"] == set(schedule["days"][0])
    assert ts["ScheduleEntry"] == set(schedule["days"][0]["entries"][0])
    assert ts["DjsFeed"] == set(djs)
    assert ts["PublicDj"] == set(djs["djs"][0])
    assert ts["DjShow"] == set(djs["djs"][0]["shows"][0])
    assert ts["NowPlayingFeed"] == set(nowfeed)
    assert ts["NowPlayingEntry"] == set(nowfeed["now"])
    assert ts["NowPlayingTrack"] == set(music.public_track_lore(_track()))

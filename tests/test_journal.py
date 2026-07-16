"""Tests for the hosts' self/interpersonal memory substrate (store.py) — D13.0.

The journal the rest of D13 reads and writes: durable, bounded records of what a host
said/revealed ON AIR (opinions, personal details, jokes, host-to-host exchanges), so
future segments can call back correctly and the continuity editor can flag
self-contradiction. Surgical, on the real logic a silent bug would corrupt:

* an entry round-trips (all fields, including the nullable pair/in-world ones);
* `journal_for_host` windows by real air time, newest first, scoped to one host;
* `journal_for_pair` is SYMMETRIC (A-about-B and B-about-A are one shared history);
* an unknown `kind` is rejected loudly at insert (and at prune);
* `prune_journal` keeps the newest N of a kind (the bounded-biography cap);
* the reads degrade cleanly on a cold start (empty journal);
* the seed/reset + persistence contract: the journal SURVIVES a `seed-canon` refresh,
  is CLEARED by the destructive `reset-world`, and is counted by `counts`.

Every DB test rolls back at teardown, so the suite never mutates a dev DB and skips
cleanly without Postgres/pgvector.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime, timedelta

import pytest
from src.world import store


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
    except Exception as exc:  # noqa: BLE001 - e.g. CREATE EXTENSION vector unavailable
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"pgvector unavailable: {exc}")
    try:
        yield conn
    finally:
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _entry(
    host_id: str,
    *,
    kind: str = store.JOURNAL_KIND_OPINION,
    text: str = "thinks the renewal vote is a ritual, not a rule",
    segment_id: str = "d130-seg",
    when: datetime,
    other_host: str | None = None,
    in_world_time: datetime | None = None,
    tags: list[str] | None = None,
) -> store.JournalEntry:
    return store.JournalEntry(
        host_id=host_id,
        kind=kind,
        text=text,
        segment_id=segment_id,
        air_time=when,
        other_host=other_host,
        in_world_time=in_world_time,
        tags=tags if tags is not None else ["renewal-vote"],
    )


def test_entry_round_trips_all_fields(db):
    when = datetime(2026, 7, 16, 21, 0)
    iw = datetime(2626, 7, 16, 21, 0)
    ids = store.insert_journal_entries(
        db,
        [
            _entry(
                "vell",
                kind=store.JOURNAL_KIND_DETAIL,
                text="admitted he still writes to Meridian",
                segment_id="d130-s1",
                when=when,
                other_host="asha",
                in_world_time=iw,
                tags=["meridian", "letters"],
            )
        ],
    )
    assert len(ids) == 1  # the DB-assigned ids come back, in input order

    got = store.journal_for_host(db, "vell", when, within=timedelta(days=7))
    mine = [e for e in got if e.segment_id == "d130-s1"]
    assert len(mine) == 1
    e = mine[0]
    assert e.host_id == "vell"
    assert e.other_host == "asha"
    assert e.kind == store.JOURNAL_KIND_DETAIL
    assert e.text == "admitted he still writes to Meridian"
    assert e.air_time == when
    assert e.in_world_time == iw
    assert e.tags == ["meridian", "letters"]
    assert e.id is not None  # DB assigned the identity


def test_journal_for_host_windows_scopes_and_orders_newest_first(db):
    now = datetime(2026, 7, 16, 20, 0)
    store.insert_journal_entries(
        db,
        [
            _entry("vell", segment_id="d130-old", when=now - timedelta(days=30)),
            _entry("vell", segment_id="d130-mid", when=now - timedelta(days=2)),
            _entry("vell", segment_id="d130-new", when=now - timedelta(hours=1)),
            _entry("asha", segment_id="d130-other-host", when=now),
        ],
    )

    got = store.journal_for_host(db, "vell", now, within=timedelta(days=7))
    segs = [e.segment_id for e in got if e.segment_id.startswith("d130-")]
    assert "d130-old" not in segs  # outside the window
    assert "d130-other-host" not in segs  # another host's memory
    assert segs.index("d130-new") < segs.index("d130-mid")  # newest first


def test_journal_for_host_includes_entries_captured_ahead_of_now(db):
    # The buffer model: segments render (and journal) AHEAD of broadcast `now`; a
    # future-placed segment's memory is still the host's history for the next write.
    now = datetime(2026, 7, 16, 20, 0)
    store.insert_journal_entries(
        db, [_entry("vell", segment_id="d130-ahead", when=now + timedelta(hours=2))]
    )
    got = store.journal_for_host(db, "vell", now, within=timedelta(days=7))
    assert any(e.segment_id == "d130-ahead" for e in got)


def test_journal_for_host_limit_caps_rows(db):
    now = datetime(2026, 7, 16, 20, 0)
    store.insert_journal_entries(
        db,
        [
            _entry("vell", segment_id=f"d130-cap-{i}", when=now - timedelta(hours=i))
            for i in range(5)
        ],
    )
    got = store.journal_for_host(db, "vell", now, within=timedelta(days=7), limit=2)
    assert len(got) <= 2


def test_journal_for_pair_is_symmetric_and_excludes_non_pair(db):
    now = datetime(2026, 7, 16, 20, 0)
    store.insert_journal_entries(
        db,
        [
            _entry(
                "vell",
                kind=store.JOURNAL_KIND_EXCHANGE,
                segment_id="d130-a-about-b",
                when=now - timedelta(hours=3),
                other_host="asha",
            ),
            _entry(
                "asha",
                kind=store.JOURNAL_KIND_EXCHANGE,
                segment_id="d130-b-about-a",
                when=now - timedelta(hours=1),
                other_host="vell",
            ),
            # Same hosts but SOLO entries (no pair) — must not appear in the pair read.
            _entry("vell", segment_id="d130-solo", when=now),
            # A different pair entirely.
            _entry(
                "vell",
                kind=store.JOURNAL_KIND_EXCHANGE,
                segment_id="d130-other-pair",
                when=now,
                other_host="sera",
            ),
        ],
    )

    got = store.journal_for_pair(db, "asha", "vell", now, within=timedelta(days=7))
    segs = [e.segment_id for e in got if e.segment_id.startswith("d130-")]
    assert "d130-a-about-b" in segs  # both directions returned
    assert "d130-b-about-a" in segs
    assert "d130-solo" not in segs
    assert "d130-other-pair" not in segs
    # newest first regardless of direction
    assert segs.index("d130-b-about-a") < segs.index("d130-a-about-b")


def test_unknown_kind_rejected_loudly(db):
    when = datetime(2026, 7, 16, 20, 0)
    with pytest.raises(ValueError, match="unknown kind"):
        store.insert_journal_entries(db, [_entry("vell", kind="vibe", when=when)])
    # Nothing was written (the validation runs before any insert).
    assert store.journal_for_host(db, "vell", when, within=timedelta(days=1)) == []
    with pytest.raises(ValueError, match="unknown kind"):
        store.prune_journal(db, "vell", kind="vibe", keep=1)


def test_prune_journal_keeps_newest_n_of_one_kind_per_host(db):
    now = datetime(2026, 7, 16, 20, 0)
    store.insert_journal_entries(
        db,
        [
            _entry(
                "vell",
                kind=store.JOURNAL_KIND_DETAIL,
                segment_id=f"d130-det-{i}",
                when=now - timedelta(days=i),
            )
            for i in range(4)
        ]
        + [
            # Another kind and another host — both must be untouched by the sweep.
            _entry(
                "vell",
                kind=store.JOURNAL_KIND_OPINION,
                segment_id="d130-op",
                when=now - timedelta(days=10),
            ),
            _entry(
                "asha",
                kind=store.JOURNAL_KIND_DETAIL,
                segment_id="d130-asha-det",
                when=now - timedelta(days=10),
            ),
        ],
    )

    removed = store.prune_journal(db, "vell", kind=store.JOURNAL_KIND_DETAIL, keep=2)
    assert removed == 2  # the two oldest details dropped

    vell = store.journal_for_host(db, "vell", now, within=timedelta(days=30))
    segs = [e.segment_id for e in vell]
    assert "d130-det-0" in segs and "d130-det-1" in segs  # newest two stand
    assert "d130-det-2" not in segs and "d130-det-3" not in segs
    assert "d130-op" in segs  # other kind untouched
    asha = store.journal_for_host(db, "asha", now, within=timedelta(days=30))
    assert any(e.segment_id == "d130-asha-det" for e in asha)  # other host untouched


def test_reads_degrade_on_cold_start(db):
    far = datetime(3000, 1, 1, 0, 0)
    assert store.journal_for_host(db, "vell", far, within=timedelta(days=1)) == []
    assert (
        store.journal_for_pair(db, "vell", "asha", far, within=timedelta(days=1)) == []
    )
    # Pruning an empty journal removes nothing and doesn't error.
    assert store.prune_journal(db, "nobody", keep=5) == 0


def test_journal_counts_groups_per_host(db):
    when = datetime(2026, 7, 16, 12, 0)
    base = store.journal_counts(db).get("vell", 0)
    store.insert_journal_entries(
        db,
        [
            _entry("vell", segment_id="d130-c1", when=when),
            _entry("vell", segment_id="d130-c2", when=when),
        ],
    )
    assert store.journal_counts(db)["vell"] == base + 2


def test_journal_counted_survives_canon_refresh_cleared_by_reset(db):
    # Delta-count, not absolute: a real dev DB may already hold journal rows (a
    # rolled-back txn hides this test's writes, not pre-committed rows).
    base = store.counts(db)["host_journal"]
    when = datetime(2026, 7, 16, 12, 0)
    store.insert_journal_entries(
        db,
        [
            _entry("vell", segment_id="d130-x", when=when),
            _entry("asha", segment_id="d130-y", when=when),
        ],
    )

    assert store.counts(db)["host_journal"] == base + 2  # folded into counts

    store.clear_world(db, scope="canon")  # SAFE refresh — the journal SURVIVES
    assert store.counts(db)["host_journal"] == base + 2

    store.clear_world(db, scope="world")  # DESTRUCTIVE wipe — the journal is cleared
    assert store.counts(db)["host_journal"] == 0


# --- D13.1: the post-air capture (src/writers/journal.py) --------------------
# No DB and no LLM: `parse_entries` is pure, and `capture_segment` is exercised with
# the LLM + store seams stubbed — what's under test is the skip discipline, the
# parse/validation of the extractor's output shape, and the best-effort guarantee
# (a failure never raises out of the chokepoint).

from src.segment import Segment  # noqa: E402
from src.writers import journal as journal_mod  # noqa: E402

_AIR = datetime(2026, 7, 16, 20, 0)


def _talk_seg(
    script: str = "Vell: I still think the vote is a ritual.\nWren: Ha!",
    *,
    fmt: str = "talk",
    speakers: tuple[str, ...] = ("vell", "wren"),
) -> Segment:
    return Segment(
        id="d131-seg",
        format=fmt,
        length_target_sec=300,
        air_time=_AIR.isoformat(),
        script=script,
        meta={"speakers": list(speakers)},
    )


_GOOD_PAYLOAD = """[
  {"host": "vell", "kind": "opinion",
   "text": "thinks the renewal vote is a ritual, not a rule",
   "other_host": null, "tags": ["renewal-vote"]},
  {"host": "wren", "kind": "detail",
   "text": "grew up on the far side of the relay",
   "other_host": "vell", "tags": ["Childhood "]}
]"""


@pytest.fixture
def capture_env(monkeypatch):
    """Stub every seam `capture_segment` touches; hand back the recorders."""
    calls: dict = {"llm": [], "inserted": [], "pruned": [], "embedded": []}

    monkeypatch.setattr(
        journal_mod,
        "_cards_block",
        lambda hosts: ("CARDS", {h: h.title() for h in hosts}),
    )
    monkeypatch.setattr(
        journal_mod.llm,
        "generate",
        lambda prompt, **kw: calls["llm"].append((prompt, kw)) or _GOOD_PAYLOAD,
    )
    monkeypatch.setattr(
        journal_mod.store, "connect", contextlib.nullcontext, raising=True
    )
    monkeypatch.setattr(
        journal_mod.store,
        "insert_journal_entries",
        lambda conn, entries: (
            calls["inserted"].extend(entries) or list(range(1, len(entries) + 1))
        ),
    )
    monkeypatch.setattr(
        journal_mod.store,
        "prune_journal",
        lambda conn, host, **kw: calls["pruned"].append((host, kw)) or 0,
    )
    monkeypatch.setattr(
        journal_mod,
        "_embed_entries",
        lambda ids, entries: calls["embedded"].append((ids, entries)),
    )
    return calls


def test_capture_writes_entries_from_a_talk_segment(capture_env):
    n = journal_mod.capture_segment(_talk_seg())
    assert n == 2
    inserted = capture_env["inserted"]
    assert [e.host_id for e in inserted] == ["vell", "wren"]
    assert inserted[0].kind == store.JOURNAL_KIND_OPINION
    assert inserted[0].segment_id == "d131-seg"
    assert inserted[0].air_time == _AIR
    assert inserted[0].in_world_time is not None  # the in-world face is filled
    assert inserted[1].other_host == "vell"
    assert inserted[1].tags == ["childhood"]  # cleaned + lowercased
    # The cheap tier + the cards cache block reached the LLM seam.
    _prompt, kw = capture_env["llm"][0]
    from src.config import settings

    assert kw["model"] == settings.convo_journal_tier
    assert kw["cards"] == "CARDS"
    # The detail host got its bounded-biography sweep; entries were embedded.
    assert [h for h, _ in capture_env["pruned"]] == ["wren"]
    assert len(capture_env["embedded"]) == 1


def test_capture_skips_non_talk_evergreen_and_disabled(capture_env, monkeypatch):
    assert journal_mod.capture_segment(_talk_seg(fmt="news")) == 0
    assert journal_mod.capture_segment(_talk_seg(fmt="evergreen")) == 0
    assert journal_mod.capture_segment(_talk_seg(script="")) == 0
    assert journal_mod.capture_segment(_talk_seg(speakers=())) == 0
    monkeypatch.setattr(journal_mod.settings, "convo_journal_enabled", False)
    assert journal_mod.capture_segment(_talk_seg()) == 0
    assert capture_env["llm"] == []  # none of the skips reached the LLM


def test_capture_nothing_durable_writes_zero_rows(capture_env, monkeypatch):
    monkeypatch.setattr(journal_mod.llm, "generate", lambda prompt, **kw: "[]")
    assert journal_mod.capture_segment(_talk_seg()) == 0
    assert capture_env["inserted"] == []


def test_capture_is_best_effort_on_llm_failure(capture_env, monkeypatch):
    def boom(prompt, **kw):
        raise RuntimeError("api down")

    monkeypatch.setattr(journal_mod.llm, "generate", boom)
    assert journal_mod.capture_segment(_talk_seg()) == 0  # logged, never raised


def test_capture_is_best_effort_on_db_failure(capture_env, monkeypatch):
    def boom(conn, entries):
        raise RuntimeError("db down")

    monkeypatch.setattr(journal_mod.store, "insert_journal_entries", boom)
    assert journal_mod.capture_segment(_talk_seg()) == 0


def test_parse_accepts_fenced_json():
    raw = f"```json\n{_GOOD_PAYLOAD}\n```"
    entries = journal_mod.parse_entries(
        raw, hosts=["vell", "wren"], segment_id="s", air_time=_AIR
    )
    assert len(entries) == 2


def test_parse_drops_invalid_items_keeps_good_ones():
    raw = """[
      {"host": "guest-arbiter", "kind": "opinion", "text": "a guest opinion"},
      {"host": "vell", "kind": "vibe", "text": "unknown kind"},
      {"host": "vell", "kind": "joke", "text": ""},
      {"host": "vell", "kind": "joke", "text": "calls the relay 'the long ear'"},
      "not-a-dict"
    ]"""
    entries = journal_mod.parse_entries(
        raw, hosts=["vell", "wren"], segment_id="s", air_time=_AIR
    )
    assert [e.text for e in entries] == ["calls the relay 'the long ear'"]


def test_parse_nulls_bad_other_host_but_keeps_entry():
    raw = """[
      {"host": "vell", "kind": "exchange", "text": "teased Wren about the charts",
       "other_host": "guest-arbiter"},
      {"host": "vell", "kind": "exchange", "text": "argued with himself",
       "other_host": "vell"}
    ]"""
    entries = journal_mod.parse_entries(
        raw, hosts=["vell", "wren"], segment_id="s", air_time=_AIR
    )
    assert len(entries) == 2
    assert all(e.other_host is None for e in entries)


def test_parse_caps_entries_at_the_dial(monkeypatch):
    monkeypatch.setattr(
        journal_mod.settings, "convo_journal_max_entries_per_segment", 2
    )
    raw = json.dumps(
        [{"host": "vell", "kind": "opinion", "text": f"opinion {i}"} for i in range(5)]
    )
    entries = journal_mod.parse_entries(
        raw, hosts=["vell"], segment_id="s", air_time=_AIR
    )
    assert len(entries) == 2


def test_parse_clips_rambling_text_and_normalises_whitespace():
    rambling = "spaced   out\n\ntext " + "x" * 400
    raw = json.dumps([{"host": "vell", "kind": "opinion", "text": rambling}])
    entries = journal_mod.parse_entries(
        raw, hosts=["vell"], segment_id="s", air_time=_AIR
    )
    assert entries[0].text.startswith("spaced out text")
    assert len(entries[0].text) <= 300


def test_parse_raises_on_malformed_payload():
    with pytest.raises(Exception):  # noqa: B017 — json error or ValueError, both fine
        journal_mod.parse_entries(
            "not json at all", hosts=["vell"], segment_id="s", air_time=_AIR
        )
    with pytest.raises(ValueError, match="expected a JSON array"):
        journal_mod.parse_entries(
            '{"host": "vell"}', hosts=["vell"], segment_id="s", air_time=_AIR
        )

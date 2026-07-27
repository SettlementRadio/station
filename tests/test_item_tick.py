"""Tests for the nightly small-items tick (src/world/items.py) — Q1.1.

The logic worth testing is the part that decides what reaches the world:

* **coercion** — one sentence, a KNOWN domain, a sane hour; anything else is dropped
  rather than mislabelled (the domain is what a programme's filter reads);
* **dating** — an item is always already true, so an hour ahead of the in-world clock
  resolves to yesterday, never to a "planned" item;
* **the gate + de-dup** — a safety-flagged item is dropped and never regenerated, and a
  near-repeat of a recent item (or of an earlier sibling in the same batch) is rejected;
* **the run** — the batch path is used (the cost lever), items are written, the expiry
  sweep runs, and a disabled tick writes nothing.

The LLM + safety seams are mocked (no tokens); DB writes roll back at teardown and the
suite skips cleanly without Postgres.
"""

from __future__ import annotations

import contextlib
import json
from datetime import datetime, timedelta

import pytest
from src.config import settings
from src.providers import llm
from src.safety import SafetyResult
from src.world import items as it
from src.world import store

# A fixed real `now`; the in-world face is +600 (2626-06-24 15:00).
NOW = datetime(2026, 6, 24, 15, 0)
IW_NOW = datetime(2626, 6, 24, 15, 0)


def _entry(
    text: str, *, domain: str = "finance", hour: int = 9, category: str = "prices"
):
    return {"text": text, "domain": domain, "category": category, "hour": hour}


# --- Coercion + dating (pure) ------------------------------------------------


def test_coerce_item_normalises_and_bounds():
    got = it._coerce_item(_entry("  The ferry   was late again.  ", hour="7"))
    assert got is not None
    assert got.text == "The ferry was late again."  # whitespace collapsed
    assert got.hour == 7  # a string hour still parses

    assert it._coerce_item(_entry("x", hour=99)).hour == 23  # clamped


def test_coerce_item_drops_junk_and_unknown_domains():
    assert it._coerce_item("not a dict") is None
    assert it._coerce_item(_entry("")) is None
    # A domain outside DOMAINS would surface the item on the wrong programme.
    assert it._coerce_item(_entry("A thing happened.", domain="gossip")) is None


def test_materialise_dates_items_in_the_last_24_inworld_hours():
    past = it._materialise(it.ProposedItem("A.", "finance", "prices", 9), 4, IW_NOW, 1)
    ahead = it._materialise(
        it.ProposedItem("B.", "finance", "prices", 22), 4, IW_NOW, 2
    )

    assert past.in_world_datetime.date() == IW_NOW.date()  # 09:00 has happened
    assert ahead.in_world_datetime.date() == (IW_NOW - timedelta(days=1)).date()
    assert ahead.in_world_datetime < IW_NOW  # never a planned/future item
    assert past.id == "i4-1" and ahead.id == "i4-2"
    assert past.tags == ["finance", "prices"]  # domain first, category alongside
    assert past.created_tick == 4


def test_request_groups_cover_every_category():
    groups = it._request_groups()
    assert len(groups) <= settings.item_tick_requests
    assert [c for g in groups for c in g] == list(it.CATEGORIES)


# --- Gate + de-dup -----------------------------------------------------------


def test_gate_drops_a_flagged_item_and_never_regenerates(monkeypatch):
    seen: list[str] = []

    def _check(text: str) -> SafetyResult:
        seen.append(text)
        return SafetyResult("bomb" not in text, "no", "keyword")

    monkeypatch.setattr(it, "safety_check", _check)
    result = it.ItemTickResult(tick=1)
    kept = it._gate(
        [
            it.ProposedItem("The ferry was late.", "geography", "delays", 9),
            it.ProposedItem("How to make a bomb.", "war", "small crime", 9),
        ],
        result,
    )

    assert [k.text for k in kept] == ["The ferry was late."]
    assert result.dropped == 1
    assert len(seen) == 2  # one check each, no retry — items are disposable


def test_dedup_rejects_recent_and_sibling_repeats():
    result = it.ItemTickResult(tick=1)
    kept = it._dedup(
        [
            it.ProposedItem("The grain price rose a quarter.", "finance", "prices", 9),
            it.ProposedItem(
                "The grain price rose by a quarter.", "finance", "prices", 10
            ),
            it.ProposedItem("A pipe failed on Deck Four.", "technology", "repairs", 11),
        ],
        ["Nothing like these at all, entirely different words here."],
        result,
    )

    assert len(kept) == 2  # the near-identical sibling went
    assert result.duplicates == 1


# --- The run (DB + mocked seams) ---------------------------------------------


@pytest.fixture
def item_db(monkeypatch):
    """One rolled-back connection shared across the tick's read+write transactions."""
    try:
        cm = store.connect()
        conn = cm.__enter__()
    except Exception as exc:  # noqa: BLE001 - no DB -> skip
        pytest.skip(f"no Postgres available: {exc}")
    try:
        store.init_schema(conn)
    except Exception as exc:  # noqa: BLE001 - pgvector unavailable
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)
        pytest.skip(f"pgvector unavailable: {exc}")

    conn.execute("DELETE FROM items")
    conn.execute(
        "DELETE FROM state WHERE key IN "
        "('world_item_tick_count', 'world_item_tick_last_at')"
    )

    @contextlib.contextmanager
    def fake_connect():
        yield conn  # shared, uncommitted — every txn in a run lands here

    monkeypatch.setattr(store, "connect", fake_connect)
    monkeypatch.setattr(
        it, "safety_check", lambda text: SafetyResult(True, "OK", "disabled")
    )
    try:
        yield conn
    finally:
        conn.rollback()
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def _mock_batch(monkeypatch, per_request: int = 3):
    """Stand in for `llm.generate_batch`: a distinct little array per request."""
    calls: list[list[llm.BatchRequest]] = []

    def _batch(reqs, **_kw):
        calls.append(list(reqs))
        out = []
        for r in reqs:
            entries = [
                _entry(f"Item {r.custom_id}-{n} happened at the docks.", hour=n % 24)
                for n in range(per_request)
            ]
            out.append(
                llm.BatchResult(
                    custom_id=r.custom_id, text=json.dumps(entries), ok=True
                )
            )
        return out

    monkeypatch.setattr(it.llm, "generate_batch", _batch)
    return calls


def test_run_item_tick_writes_items_through_the_batch_path(item_db, monkeypatch):
    calls = _mock_batch(monkeypatch)

    result = it.run_item_tick(NOW)

    assert calls, "the item tick must go through the BATCH path (the cost lever)"
    reqs = calls[0]
    assert len(reqs) == len(it._request_groups())
    assert all(r.model == settings.item_tick_tier for r in reqs)  # haiku
    assert all(r.bible for r in reqs)  # the shared cached bible block

    written = store.items_in_range(
        item_db, IW_NOW - timedelta(hours=48), IW_NOW, limit=200
    )
    assert len(written) == result.accepted > 0
    assert result.tick == 1
    assert store.get_state(item_db, "world_item_tick_count") == "1"


def test_run_item_tick_sweeps_expired_items(item_db, monkeypatch):
    _mock_batch(monkeypatch)
    store.insert_items(
        item_db,
        [
            store.Item(
                id="q11-old",
                text="An ancient small thing.",
                domain="finance",
                in_world_datetime=IW_NOW - timedelta(days=30),
            )
        ],
    )

    result = it.run_item_tick(NOW)

    assert result.pruned == 1
    assert (
        item_db.execute("SELECT count(*) FROM items WHERE id = 'q11-old'").fetchone()[0]
        == 0
    )


def test_disabled_item_tick_writes_nothing(item_db, monkeypatch):
    _mock_batch(monkeypatch)
    monkeypatch.setattr(settings, "item_tick_enabled", False)

    result = it.run_item_tick(NOW)

    assert result.accepted == 0
    assert item_db.execute("SELECT count(*) FROM items").fetchone()[0] == 0

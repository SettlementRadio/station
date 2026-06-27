"""Tests for the embedding seam (src/providers/embeddings.py) + the vector store
ordering (src/world/store.py) — D2 (semantic retrieval / RAG).

Surgical, where a silent bug bites: the fail-loud dimension guard, the empty
short-circuit, and the `retrieve()` degrade-to-`[]` contract callers rely on. The
embedding MODEL is never loaded here (we mock the provider), so the suite stays
fast and offline. The one SQL-ordering test runs against the configured Postgres
only when pgvector is available and SKIPS cleanly otherwise — the suite must stay
green on a machine without it (mirrors how `assemble()` is left to `make context`).
"""

from __future__ import annotations

import contextlib

import pytest
from src.config import settings
from src.providers import embeddings
from src.world import store

# --- embed(): dimension guard + empty short-circuit (no model needed) -------


def test_validate_dims_passes_on_correct_width():
    embeddings._validate_dims([[0.0] * settings.embeddings_dim])  # no raise


def test_validate_dims_fails_loud_on_mismatch():
    # A wrong model is silent-garbage; the guard must raise, not return.
    with pytest.raises(ValueError, match="embedding dimension"):
        embeddings._validate_dims([[0.0] * (settings.embeddings_dim + 1)])


def test_embed_empty_short_circuits(monkeypatch):
    def boom(_items):  # pragma: no cover - must never run for empty input
        raise AssertionError("provider called for empty input")

    monkeypatch.setattr(embeddings, "_embed_local", boom)
    assert embeddings.embed([]) == []


# --- retrieve(): degrade-to-[] + row mapping (provider + store mocked) ------


def test_retrieve_degrades_to_empty_when_backend_fails(monkeypatch):
    # embed raises (model missing / pgvector off / DB down) -> [] not an exception,
    # so the writers' room falls back to structured retrieval instead of dying.
    def boom(_texts):
        raise RuntimeError("backend down")

    monkeypatch.setattr(embeddings, "embed", boom)
    assert embeddings.retrieve("anything", corpus="canon") == []


def test_retrieve_maps_search_rows_to_retrieved(monkeypatch):
    monkeypatch.setattr(
        embeddings, "embed", lambda texts: [[0.1] * settings.embeddings_dim]
    )

    @contextlib.contextmanager
    def fake_connect():
        yield object()  # dummy conn; search is mocked, so it is never used

    monkeypatch.setattr(store, "connect", fake_connect)
    monkeypatch.setattr(
        store,
        "search",
        lambda conn, vec, *, corpus, k: [("canon-1", "a", 0.9), ("canon-2", "b", 0.4)],
    )

    hits = embeddings.retrieve("topic", k=2, corpus="canon")

    assert all(isinstance(h, embeddings.Retrieved) for h in hits)
    assert [(h.id, h.text, h.score) for h in hits] == [
        ("canon-1", "a", 0.9),
        ("canon-2", "b", 0.4),
    ]


# --- store.search(): real cosine ordering (integration; skips without pgvector) --


@pytest.fixture
def db_conn():
    """A store connection with the vector schema, or skip if PG/pgvector is absent."""
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
        with contextlib.suppress(Exception):
            cm.__exit__(None, None, None)


def test_search_orders_by_cosine_similarity(db_conn):
    d = settings.embeddings_dim
    corpus = "__d26_test__"  # a throwaway corpus, never the real canon

    def onehot(i: int) -> list[float]:
        v = [0.0] * d
        v[i] = 1.0
        return v

    near = onehot(0)
    mid = [0.7, 0.7] + [0.0] * (d - 2)  # ~45° from `near` -> cosine ~0.707
    far = onehot(1)  # orthogonal to `near` -> cosine 0.0

    store.delete_embeddings(db_conn, corpus)
    try:
        store.insert_embeddings(
            db_conn,
            corpus,
            [
                store.EmbeddingRow("near", "n", "seed", near),
                store.EmbeddingRow("mid", "m", "seed", mid),
                store.EmbeddingRow("far", "f", "seed", far),
            ],
        )

        rows = store.search(db_conn, near, corpus=corpus, k=3)
        ids = [r[0] for r in rows]
        scores = [r[2] for r in rows]

        assert ids == ["near", "mid", "far"]  # closest-first
        assert scores == sorted(scores, reverse=True)  # similarity descending
        assert scores[0] > scores[-1]
    finally:
        store.delete_embeddings(db_conn, corpus)

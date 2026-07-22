"""Seam #1c — the ONLY module that imports an embedding model/SDK.

Same seam discipline as `providers/llm.py` and `providers/tts.py`: the embedding
model lives ONLY behind this module, and nothing else imports an embeddings SDK.
`embed()` turns text into vectors; the vector STORAGE + nearest-neighbour SQL live
behind `world/store.py` (the `embeddings` table + `search`), and `world/context.py`
calls the `retrieve()` contract below.

Provider (D2.0 decision — recorded in `settings`): Anthropic has NO first-party
text-embedding endpoint, so the embedder is a genuine third-party pick, not a Claude
call. The default is a LOCAL open sentence-transformer (`settings.embeddings_model`,
384-d, free, no key, no network at run time once cached) — the Kokoro stance. A
hosted provider (e.g. Voyage) stays switchable here via `settings.embeddings_provider`
but is not built unless quality demands it.

Status:
  * `embed()` — IMPLEMENTED (D2.2): real vectors, model loaded once per process,
    retried + logged, output dimension validated against `settings.embeddings_dim`.
  * `retrieve()` — IMPLEMENTED (D2.4): `embed([query])` -> `store.search` ->
    `Retrieved`; used by `context._select_canon`. Degrades to `[]` on any backend
    failure so callers fall back to structured retrieval.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..config import settings
from ..logging_setup import get_logger
from ..retry import call_with_retry

log = get_logger(__name__)


@dataclass(frozen=True)
class Retrieved:
    """One semantically-retrieved hit (the shape `retrieve()` yields).

    `id` is the `embeddings.entity_id` (joins back to the source row, e.g. a `canon`
    id); `score` is the similarity (higher = closer).
    """

    id: str
    text: str
    score: float


# A SentenceTransformer loads model weights on construction (slow, ~seconds, and a
# one-time HuggingFace download), so cache one per model name across calls in a
# process — the same "load once" pattern as the Kokoro pipeline cache in tts.py.
_local_models: dict[str, object] = {}


def embed(texts: Sequence[str]) -> list[list[float]]:
    """Map texts to embedding vectors via the configured provider (D2.2).

    Returns one vector per input, each of length `settings.embeddings_dim`. The
    external call (model load + encode) is retried and logged; the output dimension
    is validated (a wrong model is a silent-garbage risk, so we fail loud). An empty
    input returns `[]` without loading the model.
    """
    items = list(texts)
    if not items:
        return []

    provider = settings.embeddings_provider
    log.info(
        "embeddings_embed_start",
        provider=provider,
        model=settings.embeddings_model,
        count=len(items),
    )

    if provider == "local":
        vectors = call_with_retry("embeddings.embed", lambda: _embed_local(items))
    else:
        raise NotImplementedError(
            f"embeddings_provider={provider!r} is not implemented; only 'local' "
            "(sentence-transformers) ships in D2. A hosted provider (e.g. Voyage) "
            "slots in here behind the seam — add its branch + an api-key setting."
        )

    _validate_dims(vectors)
    log.info("embeddings_embed_done", count=len(vectors), dim=len(vectors[0]))
    # R5.1 — record embedding volume for the budgets ledger (local model = free).
    try:
        from .. import usage

        usage.record_embeddings(len(vectors))
    except Exception:  # noqa: BLE001 — accounting must never break embedding
        pass
    return vectors


def retrieve(query: str, *, k: int = 5, corpus: str | None = None) -> list[Retrieved]:
    """Semantic search: embed `query`, return the `k` nearest stored rows by meaning.

    `embed([query])` -> `store.search` -> `Retrieved`. `corpus=None` searches across
    ALL corpora (D3/D4/D10); pass a name (e.g. "canon") to scope to one — D2's caller
    does. Manages its own short read connection so it stays a clean self-contained
    contract.

    Degrades to `[]` on ANY failure (embeddings backend missing, pgvector disabled,
    DB unreachable) — logged at warning, never raised — so the writers' room falls
    back to structured retrieval rather than going dead. This is the "vectors absent"
    safety the callers rely on.
    """
    # Imported here (not at module top) to keep the embeddings seam from importing
    # the store at load time, and to mirror the lazy-dependency style of the SDK call.
    from ..world import store

    try:
        vector = embed([query])[0]
        with store.connect() as conn:
            rows = store.search(conn, vector, corpus=corpus, k=k)
        hits = [Retrieved(id=eid, text=text, score=score) for eid, text, score in rows]
        log.debug("embeddings_retrieve", k=k, corpus=corpus, hits=len(hits))
        return hits
    except Exception as exc:  # noqa: BLE001 — degrade to structured retrieval, never die
        log.warning(
            "embeddings_retrieve_unavailable",
            query=query,
            corpus=corpus,
            error=str(exc),
        )
        return []


# --- Local provider (sentence-transformers) — the only embedding SDK import ---


def _local_model(name: str):
    """Return a cached SentenceTransformer for `name`, loading it on first use.

    Construction downloads the model from HuggingFace on first run (then cached
    locally by `huggingface_hub`) and loads weights, so we build one per model name
    and reuse it across calls within a process.
    """
    model = _local_models.get(name)
    if model is None:
        from sentence_transformers import SentenceTransformer

        log.info("embeddings_model_load", model=name)
        model = SentenceTransformer(name)
        _local_models[name] = model
    return model


def _embed_local(items: list[str]) -> list[list[float]]:
    """Encode `items` with the local model, L2-normalised (for cosine similarity).

    `normalize_embeddings=True` returns unit vectors, which is what the store's
    cosine (`vector_cosine_ops`) index expects.
    """
    model = _local_model(settings.embeddings_model)
    matrix = model.encode(items, normalize_embeddings=True, show_progress_bar=False)
    return [row.tolist() for row in matrix]


def _validate_dims(vectors: list[list[float]]) -> None:
    """Fail loud if the model's output dimension != `settings.embeddings_dim`.

    The dimension is baked into the pgvector `vector(N)` column, so a mismatch means
    the wrong model is configured — a silent-garbage / insert-failure risk we catch
    here rather than at the DB.
    """
    expected = settings.embeddings_dim
    got = len(vectors[0])
    if got != expected:
        raise ValueError(
            f"embedding dimension {got} != settings.embeddings_dim {expected} "
            f"(model={settings.embeddings_model!r}); fix embeddings_dim/model so they "
            "match, then re-embed."
        )

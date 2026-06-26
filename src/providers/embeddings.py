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
  * `retrieve()` — still the no-op contract stub; it is wired to
    `store.search` + `context._select_canon` in D2.4. Until then it returns `[]`, so
    a caller degrades cleanly to structured retrieval.
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
    return vectors


def retrieve(query: str, *, k: int = 5, corpus: str | None = None) -> list[Retrieved]:
    """Semantic search — the vector seam, NOT yet wired (lands in D2.4).

    Returns `[]` today (no embed-then-search path here yet), so a caller that unions
    structured hits with semantic ones degrades cleanly to structured-only. D2.4
    implements this as `embed([query])` -> `store.search(corpus=…)` -> `Retrieved`
    rows, with `corpus` defaulting to canon for D2's caller and `None`/a list later
    letting D3/D4/D10 search across corpora.
    """
    log.debug("embeddings_retrieve_noop", query=query, k=k, corpus=corpus)
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

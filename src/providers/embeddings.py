"""Seam stub for semantic (vector) retrieval — INTENTIONALLY UNUSED in Phase B.

Same seam discipline as `providers/llm.py` and `providers/tts.py`: when semantic
search lands, the embedding model and the vector store live ONLY behind this
module, and nothing else imports an embeddings SDK. This file exists now so that
adding vectors later is a drop-in, not a refactor — `world/context.py` is written
against the `retrieve()` contract below, even though today it relies entirely on
structured (date / status / tag) queries instead.

Why structured-only for now: the canon is tiny and date/tag recall is enough, so
the right, fast, cheap retrieval is a SQL query in `world/store.py`. Vectors would
be premature machinery.

------------------------------------------------------------------------------
TRIGGER — implement this for real ONLY when EITHER becomes true:

  * the assembled context outgrows the prompt-cache window — the stable core plus
    the relevant facts/events no longer fit in what you can afford to cache, so
    you must retrieve a *subset* of canon by relevance, OR
  * you need semantic recall — matching on *meaning* rather than date or tag (e.g.
    "find canon about loneliness" when nothing is tagged `loneliness`).

Until one of those holds, structured retrieval wins; leave this stubbed.
------------------------------------------------------------------------------

When you do implement it (all behind this seam):
  1. pick an embedding provider and put the SDK call behind `embed()`;
  2. enable pgvector and add a `canon_embeddings(canon_id, embedding vector(N))`
     table + a `search_canon()` query in `world/store.py` (see the FUTURE note
     there) — the ONLY place SQL lives;
  3. have `retrieve()` embed the query and return the nearest canon rows.
Keep the signatures below stable; they are the contract callers depend on.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Retrieved:
    """One semantically-retrieved canon hit (the shape `retrieve()` will yield).

    `id` joins back to a `canon` row; `score` is the similarity (higher = closer).
    """

    id: str
    text: str
    score: float


def embed(texts: Sequence[str]) -> list[list[float]]:
    """Map texts to embedding vectors. NOT IMPLEMENTED — see the module TRIGGER.

    Raises rather than returning a fake vector so a premature caller fails loudly
    instead of silently retrieving garbage.
    """
    raise NotImplementedError(
        "embeddings.embed() is a deferred seam — vector search is not enabled in "
        "Phase B. See the TRIGGER note in this module before implementing it."
    )


def retrieve(query: str, *, k: int = 5) -> list[Retrieved]:
    """Semantic search over canon — the vector seam, UNUSED in Phase B.

    Returns an empty list today (no semantic backend), so a caller that one day
    unions structured hits with semantic ones degrades cleanly to structured-only
    until `embed()` and the pgvector path are implemented. `world/context.py`
    deliberately does not call this yet; it is here purely to fix the contract.
    """
    log.debug("embeddings_retrieve_noop", query=query, k=k)
    return []

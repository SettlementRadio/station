# PHASE_D_RAG_TASKS.md — D2: Semantic Retrieval (RAG goes live)

> Sub-pack **D2** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the seam is already stubbed and
> documented — `providers/embeddings.py` (`embed()` raises, `retrieve()` returns `[]`, `Retrieved`
> dataclass), the FUTURE vector note in `src/world/store.py` (`CREATE EXTENSION vector` +
> `canon_embeddings(canon_id, embedding vector(N))` + `search_canon()`), and `context._select_canon`
> (tag-match → `all_canon` fallback). **Depends on D1** (a foldered, taggable, larger canon).
>
> **Read first:** `docs/PHASE_C_ORIENTATION.md` §9 ("RAG goes live"); `src/providers/embeddings.py`
> (the stub + its TRIGGER note); `src/world/store.py` (the documented FUTURE vector seam, lines ~20–29);
> `src/world/context.py` (`_select_canon`); the **`claude-api` skill** (the embeddings-provider
> question — see D2.0).

**Why now.** The embeddings stub's own TRIGGER says: implement when *either* the assembled context
outgrows the prompt cache *or* you need semantic (meaning-based) recall. After D1 the bible is big and
multi-file — both triggers fire. RAG lets the writers' room and (later) the world engine + news desk
recall canon **by meaning**, not just by date/tag, so segments stay grounded as the bible grows.

**The seam discipline (unchanged).** All SQL stays in `store.py`; the embedding model + any vector
SDK live **only** behind `providers/embeddings.py`; `context.py` calls the `retrieve()` contract.
Keep the existing signatures (`embed(texts) -> list[list[float]]`, `retrieve(query, *, k) ->
list[Retrieved]`) stable — they are the contract callers depend on.

**Definition of done for D2:** pgvector is installed and reproducible from the README; canon (and
events) are embedded on seed; `context.assemble(topic=…)` returns canon selected by **semantic
similarity**, degrading cleanly to structured/`all_canon` when vectors are absent; canon facts carry
tags so the structured path also narrows; `ruff` + `pytest` green.

---

## D2.0 — Decide the embedding provider (DECISION — write it down)
**Goal:** pick what computes the vectors, behind `embeddings.embed()`, and record why.
**Do:**
- **Consult the `claude-api` skill before deciding** — and note the key fact: **Anthropic has no
  first-party text-embedding endpoint.** So the embedding model is a genuine provider choice, not a
  Claude call. Do not invent an Anthropic embeddings model.
- Weigh two options against the project's ethos (local/free, like Kokoro; secrets minimal; runs on the
  CX33):
  - **(a) Local / open model** (e.g. a small sentence-transformers / open embedding model) — free,
    no quota, no new secret, matches the Kokoro stance; CPU cost on the box (bounded — embedding is
    far cheaper than TTS). **Recommended default.**
  - **(b) Hosted** (e.g. Voyage AI or similar) — higher quality, a new API key + cost + network
    dependency. Keep it possible behind the seam, but don't make it the default unless quality demands.
- Pick the model and record its **embedding dimension N** — it is hardcoded into the pgvector column
  (`vector(N)`), so it must be a settings value (`settings.embeddings_dim`) and the table/migration
  must match. A later model change means a re-embed + column change; note that.
- Add the provider/model/dimension as config (`# --- Embeddings (D2) ---`: `embeddings_provider`,
  `embeddings_model`, `embeddings_dim`, any `embeddings_*_api_key` only if hosted) — never a literal.
**Done when:** the provider + model + dimension are chosen and in `settings`, with the rationale in
the task summary + DEVLOG; `.env.example` updated if a key is needed.

## D2.1 — Enable pgvector + the vector schema/query in `store.py` (the only SQL)
**Goal:** the database can store and nearest-neighbour-search embeddings — all behind the store seam.
**Do:**
- Add `CREATE EXTENSION IF NOT EXISTS vector;` to the schema init (the README must document the
  pgvector system install — Homebrew/`pg_*` — so it's reproducible on the CX33).
- Add the `canon_embeddings(canon_id text references canon(id) on delete cascade, embedding
  vector(N))` table (N = `settings.embeddings_dim`) + an appropriate vector index (e.g. ivfflat/hnsw
  with a cosine/L2 opclass — pick per the chosen model's similarity).
- Add writes: `insert_canon_embeddings(conn, rows)` (canon_id → vector); make `clear_world` / the
  re-seed flow handle the new table (include it in `_WORLD_TABLES` or cascade).
- Add the read: `search_canon(conn, query_embedding, *, k) -> list[(CanonFact, score)]` (or a
  `Retrieved`-shaped result) ordered by similarity. **This is the only place the vector SQL lives**
  (matches the documented FUTURE note).
**Done when:** schema init creates the extension + table + index idempotently; insert + `search_canon`
work against a hand-inserted vector; nothing outside `store.py` writes vector SQL.

## D2.2 — Implement `embeddings.embed()` behind the seam
**Goal:** real vectors, vendor-isolated, retried, logged.
**Do:**
- Implement `embed(texts) -> list[list[float]]` for the chosen provider behind
  `providers/embeddings.py` — the **only** module importing the embedding SDK/model (seam rule, like
  `llm`/`tts`). Wrap external calls in `retry.call_with_retry`; log start/outcome; load any local
  model once per process (cache it, like the Kokoro pipeline pattern).
- Keep `embed`'s signature and the `Retrieved` shape unchanged. Validate output dimension ==
  `settings.embeddings_dim` (fail loud on mismatch — a wrong model is a silent-garbage risk).
**Done when:** `embed(["hello", "world"])` returns two N-dim vectors; a transient failure retries; the
embedding SDK/model is imported nowhere else.

## D2.3 — Embed canon (+ events) on seed
**Goal:** the corpus is vectorised whenever the world is seeded, reproducibly.
**Do:**
- In `seed.py`, after inserting canon, embed each fact's text via `embeddings.embed` and store via
  `store.insert_canon_embeddings`. Re-embed on re-seed (the `clear_world` flow already truncates).
- Decide whether to also embed **events** now or defer to D3 (the world tick will write events
  continuously and should embed them on write). Recommend: embed events too if the table exists, with
  a small helper the D3 tick can reuse — but keep D2's scope to canon if events complicate it; note
  the decision.
- Batch the embed calls (don't call per-fact in a tight loop if the provider supports batching) and
  log counts. Consider the Batch path only if volume warrants (small at D2; revisit in D3).
**Done when:** `make seed` populates `canon_embeddings` for every fact (count matches `canon`);
re-seed re-embeds cleanly; logs show the embed step.

## D2.4 — Wire `retrieve()` into context assembly (semantic, with clean fallback)
**Goal:** the writers' room selects canon by meaning, degrading safely when vectors are absent.
**Do:**
- Implement `retrieve(query, *, k) -> list[Retrieved]`: `embed([query])` → `store.search_canon` →
  `Retrieved` rows. Returns `[]` if embeddings/pgvector are unavailable (so callers degrade), per the
  existing contract.
- Update `context._select_canon(conn, topic)`: when a `topic` is given, use semantic retrieval
  (top-k by meaning), **unioned with or falling back to** the existing tag-match → `all_canon` path —
  so a topic with no good vector hit still gets the structured fallback, and the writer never loses
  the core facts. Make k a config dial (`settings.context_canon_top_k`).
- Keep the no-topic path returning the (small, or now larger) canon as today — or, if the bible is
  now too big to include wholesale, cap it and note that the dynamic block is where relevance lives.
**Done when:** `context.assemble(topic="loneliness")` (or similar) returns canon ranked by meaning
even when nothing is tagged `loneliness`; with pgvector disabled it falls back to structured/all
canon without error; k is a dial.

## D2.5 — Tag the canon facts (so the structured path also narrows)
**Goal:** populate the tags the D1 format supports, so `canon_by_tags` (inert since B3) finally works
as the structured complement to semantic recall.
**Do:**
- Populate tags on the canon facts — either authored in the bible files (the D1 tag affordance) or
  derived. Recommend: a mix — author tags on the hard facts, and optionally a one-off
  tagging pass. Keep it simple; the goal is that `canon_by_tags` returns sensible rows.
- Confirm `context._select_canon`'s tag path now returns real hits (no longer always falling back to
  `all_canon`), complementing the semantic path.
**Done when:** seeded facts carry tags; `store.canon_by_tags` returns matching facts; the hybrid
selection (semantic + tag) is exercised by a test.

## D2.6 — Tests + verification + docs
**Goal:** retrieval is covered where a silent bug bites, and reproducible from scratch.
**Do:**
- Tests (surgical, real logic): `search_canon` orders by similarity for a known set of vectors;
  `retrieve` degrades to `[]` / fallback when embeddings are off; `_select_canon` returns semantic
  hits for an off-tag query and falls back cleanly; dimension-mismatch fails loud. Mock the embedding
  *provider* (don't hit a network/model in unit tests) but exercise the SQL against a test DB or a
  deterministic fixture.
- Update `README.md` (pgvector install; the embeddings provider + how seed embeds) and `.env.example`
  (new embeddings config / key). DEVLOG entry (Phase D — D2), recording the provider DECISION.
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; a manual
`context.assemble(topic=…)` shows meaning-based recall.

---

## Explicitly NOT in D2 (→ later sub-packs)
- **Generating new world content / story arcs / the world tick** → **D3** (D2 retrieves over the
  *existing* corpus; D3 writes new events — and should embed them on write, reusing D2's helper).
- **The news desk reading the story log** → **D4**.
- **Anti-repetition / recent-airplay memory** → **D5** (distinct from semantic recall: D5 avoids
  *repeating* recent output; D2 *finds relevant* canon).
- **Re-embedding on a model change at scale / multi-corpus RAG** → revisit if/when the bible or the
  event log grows large; D2 ships canon (+ optionally events) embedding only.

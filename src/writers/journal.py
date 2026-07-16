"""The hosts' on-air journal (D13) — what a host said STAYS said.

Two halves, one memory. **Capture** (D13.1): after a scheduled talk segment
clears both gates and renders, ONE cheap extraction (the `convo_journal_tier`,
haiku per CLAUDE.md routing) distills the segment script into 0–N durable
`host_journal` rows: opinions a host voiced, personal details they revealed,
jokes with callback potential, and the gist of notable host-to-host exchanges.
**Recall** (D13.2): `journal_section` renders those rows back into the room as
the D9.4 sibling — per host a bounded, persona-weighted pick of their own past
statements, plus a per-pair "what you two last talked about" line; the
showrunner gets ONLY the pair line (`pair_section` — the beat-picker needs the
relationship, not the full journal). D13.3 shows the same block to the
continuity editor. This is the memory the persona audit named missing: the
hosts remembered the *world* (D9.4) but not *themselves or each other*.

Recall placement is deliberate (the prompt-cache lever, OVERVIEW §2): the block
is small and VARIABLE, so it rides the per-call system prompt, never the cached
bible/cards. Bounded by the `convo_journal_per_host` / `convo_journal_window_days`
/ `convo_journal_top_k` dials; degrades to "" on disabled/empty/DB-failure, so
the room writes exactly as the pre-D13 room did. The D5 boundary is stated in
the block itself: a remembered topic is a CALLBACK, never a licence to re-run it.

Discipline (the pack's load-bearing rules):

* **Post-gate, best-effort, never load-bearing.** Capture runs at the scheduler's
  `top_up` post-render chokepoint (beside the D5.1 airplay record and the D12.0
  hand-off). Any failure — LLM, parse, DB — logs a warning and the segment stands;
  a segment never waits on, or fails because of, its journal. Non-talk formats and
  evergreen fallbacks are skipped; direct CLI paths (`make conversation`) never
  reach this module, so only AIRED segments become memory (mirroring D4/D5).
* **The card wins.** The extractor sees the speakers' cards (as the `cards=`
  cache block — successive talk segments with the same pair hit the prompt cache)
  and is told to DROP anything contradicting a card. A journal entry contradicting
  the card is a capture bug, never a canon change.
* **Speakers only.** Hosts in `seg.meta["speakers"]` (field hosts included — a
  dispatch is Sera's on-air life). One-off guests (D9.3) are texture, not cast —
  the parse drops any entry attributed outside the speaker set.
* **Bounded.** At most `convo_journal_max_entries_per_segment` entries per
  segment; `detail` rows are capped per host (`convo_journal_max_details_per_host`,
  pruned right after capture). Each stored entry is embedded into the
  `JOURNAL_CORPUS` (best-effort, like canon embeddings) for D13.2 semantic recall.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from itertools import combinations

from ..config import settings
from ..logging_setup import get_logger
from ..providers import embeddings, llm
from ..segment import Segment
from ..world import clock, events, store
from ..world.store import CastMember, JournalEntry

log = get_logger(__name__)

# A journal entry is ONE compact sentence — distilled recall, never a transcript.
# Anything longer is clipped (the extractor is told to be brief; this is the seam's
# own bound so a rambling model can't bloat the memory).
_TEXT_MAX_CHARS = 300
_TAGS_MAX = 5


def _cards_block(hosts: list[str]) -> tuple[str, dict[str, str]]:
    """The speakers' character cards as a stable cache block + an id→name map.

    Rendered in the same "## Character — Name" shape the context assembler uses,
    joined in host-id order — STABLE across calls, so successive extractions for
    the same speaker pair hit the prompt cache (the cache lever; haiku's cache is
    its own — it never shares the sonnet room's — but extraction-to-extraction
    reuse is what matters at one call per talk segment). A host id with no cast
    row still appears in the name map (as itself) so attribution never breaks.
    """
    blocks: list[str] = []
    names: dict[str, str] = {}
    with store.connect() as conn:
        for host_id in hosts:
            member = store.get_cast_member(conn, host_id)
            if member is None:
                names[host_id] = host_id
                continue
            names[host_id] = member.name
            blocks.append(f"## Character — {member.name}\n\n{member.card_text}")
    return "\n\n---\n\n".join(blocks), names


def _system_prompt(names: dict[str, str], max_entries: int) -> str:
    """The per-call extraction instructions (the small, variable system part)."""
    roster = ", ".join(f'"{hid}" ({name})' for hid, name in names.items())
    return (
        "You are the station archivist for Settlement Radio. From the talk-segment "
        "transcript in the user message, extract the few DURABLE things worth "
        "remembering about the HOSTS THEMSELVES — not the world's news (the story "
        "log already keeps that).\n\n"
        "Kinds:\n"
        '- "opinion": a stance or position a host explicitly voiced.\n'
        '- "detail": a personal fact a host revealed about their own life.\n'
        '- "joke": a joke or running gag with genuine callback potential.\n'
        '- "exchange": the gist of a notable exchange between two hosts '
        '(set "other_host").\n\n'
        "Rules:\n"
        f"- Hosts (the only valid ids): {roster}. Ignore guests, soundbites and "
        "quoted figures entirely.\n"
        f"- At most {max_entries} entries; FEWER IS BETTER — most segments hold "
        "0-2 durable moments. Return [] when nothing durable was said.\n"
        '- "text": ONE compact, self-contained sentence in third person, present '
        'tense for standing facts ("thinks the renewal vote is a ritual, not a '
        'rule"; "still writes letters to Meridian"). Recall, not transcript — '
        "no verbatim quoting needed.\n"
        "- Durable only: skip pleasantries, time checks, segues, reactions to "
        "songs, and anything any host might say on any day.\n"
        "- THE CARD WINS: each host's character card is above. DROP any candidate "
        "that contradicts a card — a contradiction is extraction noise, never a "
        "new fact.\n"
        '- "tags": 1-3 short lowercase topic tags.\n\n'
        "Return STRICT JSON — an array of objects "
        '{"host": id, "kind": ..., "text": ..., "other_host": id or null, '
        '"tags": [...]} — and nothing else: no prose, no code fences.'
    )


def _strip_fences(raw: str) -> str:
    """The model's text with any ```-fence wrapper removed (defensive parse aid)."""
    text = raw.strip()
    if text.startswith("```"):
        first_break = text.find("\n")
        if first_break != -1:
            text = text[first_break + 1 :]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_entries(
    raw: str,
    *,
    hosts: list[str],
    segment_id: str,
    air_time: datetime,
    in_world_time: datetime | None = None,
) -> list[store.JournalEntry]:
    """Parse + validate the extractor's output into `JournalEntry` rows (pure).

    Tolerant of the model, strict about the memory: a malformed payload raises
    (the caller logs and moves on — best-effort); a well-formed payload has each
    item validated and the bad ones DROPPED (an unknown host — e.g. a guest — an
    unknown kind, or empty text), because one junk candidate must not cost the
    segment its good entries. `other_host` outside the speaker set (or
    self-referential) is nulled rather than dropping the entry — the self-memory
    stands even when the pair link is noise. Bounded by
    `convo_journal_max_entries_per_segment`; `text` clipped to one compact
    sentence's worth of characters.
    """
    payload = json.loads(_strip_fences(raw) or "[]")
    if not isinstance(payload, list):
        raise ValueError(
            f"journal extraction: expected a JSON array, got {type(payload).__name__}"
        )

    valid = set(hosts)
    entries: list[store.JournalEntry] = []
    dropped = 0
    for item in payload:
        if len(entries) >= settings.convo_journal_max_entries_per_segment:
            break
        if not isinstance(item, dict):
            dropped += 1
            continue
        host = str(item.get("host") or "").strip()
        kind = str(item.get("kind") or "").strip()
        text = " ".join(str(item.get("text") or "").split())
        if host not in valid or kind not in store.JOURNAL_KINDS or not text:
            dropped += 1
            continue
        other = item.get("other_host")
        other = str(other).strip() if other else None
        if other is not None and (other not in valid or other == host):
            other = None
        raw_tags = item.get("tags") or []
        tags = [
            str(t).strip().lower()
            for t in (raw_tags if isinstance(raw_tags, list) else [])
            if str(t).strip()
        ][:_TAGS_MAX]
        entries.append(
            store.JournalEntry(
                host_id=host,
                kind=kind,
                text=text[:_TEXT_MAX_CHARS],
                segment_id=segment_id,
                air_time=air_time,
                other_host=other,
                in_world_time=in_world_time,
                tags=tags,
            )
        )
    if dropped:
        log.warning("journal_entries_dropped", segment_id=segment_id, dropped=dropped)
    return entries


def _embed_entries(ids: list[int], entries: list[store.JournalEntry]) -> None:
    """Best-effort: embed stored entries into the `JOURNAL_CORPUS` (D13.2 recall).

    Keyed by journal row id (so `prune_journal` can drop the vector with the row);
    tagged with the host/kind/pair so semantic recall can filter. A failure logs —
    the structured recency read is the always-works fallback, so a missing vector
    never costs anything but recall quality.
    """
    try:
        vectors = embeddings.embed([e.text for e in entries])
        rows = [
            store.EmbeddingRow(
                entity_id=str(row_id),
                text=e.text,
                source=store.JOURNAL_SOURCE_AIR,
                tags=[
                    f"host:{e.host_id}",
                    f"kind:{e.kind}",
                    *([f"with:{e.other_host}"] if e.other_host else []),
                    *e.tags,
                ],
                embedding=vec,
            )
            for row_id, e, vec in zip(ids, entries, vectors, strict=True)
        ]
        with store.connect() as conn:
            store.insert_embeddings(conn, store.JOURNAL_CORPUS, rows)
    except Exception as exc:  # noqa: BLE001 — vectors are recall quality, not memory
        log.warning("journal_embed_failed", count=len(entries), error=str(exc))


def capture_segment(seg: Segment) -> int:
    """Best-effort: extract + persist a placed talk segment's journal (D13.1).

    Called at the scheduler chokepoint, beside the D5.1 airplay record, AFTER the
    segment cleared the gates and rendered. Returns how many entries were written
    (0 on skip, nothing-durable, or any failure — the segment always stands).
    Skips internally: disabled, non-talk formats (evergreen fallbacks carry
    `format="evergreen"`), no script, or no speakers recorded.
    """
    if not settings.convo_journal_enabled:
        return 0
    if seg.format != "talk" or not seg.script:
        return 0
    hosts = [str(h) for h in (seg.meta.get("speakers") or []) if h]
    if not hosts or not seg.air_time:
        return 0

    try:
        air_time = datetime.fromisoformat(seg.air_time)
        cards, names = _cards_block(hosts)
        max_entries = settings.convo_journal_max_entries_per_segment
        raw = llm.generate(
            f"TRANSCRIPT:\n\n{seg.script}",
            system=_system_prompt(names, max_entries),
            cards=cards or None,
            model=settings.convo_journal_tier,
            max_tokens=settings.convo_journal_max_tokens,
        )
        entries = parse_entries(
            raw,
            hosts=hosts,
            segment_id=seg.id,
            air_time=air_time,
            in_world_time=clock.to_inworld(air_time),
        )
        if not entries:
            log.info("journal_nothing_durable", seg_id=seg.id)
            return 0
        with store.connect() as conn:
            ids = store.insert_journal_entries(conn, entries)
            # The bounded-biography cap: hosts that just gained a personal detail
            # get their `detail` rows swept back to the dial (oldest drop).
            for host in {
                e.host_id for e in entries if e.kind == store.JOURNAL_KIND_DETAIL
            }:
                store.prune_journal(
                    conn, host, keep=settings.convo_journal_max_details_per_host
                )
        _embed_entries(ids, entries)
        log.info(
            "journal_captured",
            seg_id=seg.id,
            entries=len(entries),
            hosts=sorted({e.host_id for e in entries}),
            kinds=sorted({e.kind for e in entries}),
        )
        return len(entries)
    except Exception as exc:  # noqa: BLE001 — the journal must never cost a segment
        log.warning("journal_capture_failed", seg_id=seg.id, error=str(exc))
        return 0


# --- Recall (D13.2): the "what you've said before" block ----------------------
# The D9.4 sibling — same shape, same discipline: read once per slot, rank per
# host, render a small VARIABLE block for the per-call system prompt (the cache
# lever holds), degrade to "" on anything. The division of labour stays sharp:
# D9.4 is the hosts remembering the WORLD; this is the hosts remembering
# THEMSELVES and each other. The block's steer states the D5 boundary — a
# remembered topic is a callback, never a licence to re-run it.

# A semantic hit from the `journal` corpus outranks a couple of card-tag overlaps
# in the pick (topic relevance beats persona affinity when a topic is in play, but
# a strong persona match still competes). A domain constant, not an operator dial.
_SEMANTIC_BOOST = 2

# How a kind reads inside the recall parenthetical — a joke needs "a running bit"
# so the room calls it back AS a bit; the other kinds read naturally bare.
_KIND_QUALIFIER = {store.JOURNAL_KIND_JOKE: ", a bit that landed"}


def _phrase_for(entry: JournalEntry, now: datetime) -> str:
    """The clock phrase for an entry ("yesterday", "last week") at real `now`.

    Frames on the in-world face (`in_world_time`, filled at capture; derived from
    `air_time` when absent — same constant offset) through the B2 clock renderer,
    like every other dated thing the hosts say.
    """
    iw = entry.in_world_time or clock.to_inworld(entry.air_time)
    return events.phrase_for_datetime(iw, now)


def _entry_line(entry: JournalEntry, now: datetime) -> str:
    """One journal entry as a prompt bullet, clock-framed for `now`."""
    qualifier = _KIND_QUALIFIER.get(entry.kind, "")
    return f"- ({_phrase_for(entry, now)}{qualifier}) {entry.text}"


def _rank_for(
    card: CastMember,
    entries: list[JournalEntry],
    per_host: int,
    semantic_ids: set[int],
) -> list[JournalEntry]:
    """The entries THIS host recalls: relevance + persona-weighted, bounded, stable.

    The D9.4 ranking pattern: card-tag overlap ranks (a sports memory sticks with
    the sports host), a semantic hit for the slot's topic ranks harder
    (`_SEMANTIC_BOOST`), and ties keep the store order (newest first).
    """
    tags = set(card.tags)

    def score(e: JournalEntry) -> int:
        boost = _SEMANTIC_BOOST if e.id is not None and e.id in semantic_ids else 0
        return len(set(e.tags) & tags) + boost

    ranked = sorted(enumerate(entries), key=lambda pair: (-score(pair[1]), pair[0]))
    return [e for _i, e in ranked[:per_host]]


# A semantic hit must actually RESEMBLE the topic to earn the boost: on a small
# journal, top-k alone returns everything (making the boost a no-op), so hits
# below this cosine similarity are discarded. A property of the embedding model's
# similarity scale (unrelated sentences score ~0.0-0.2 on the chosen
# L2-normalised model), so a domain constant, not an operator dial.
_SEMANTIC_MIN_SCORE = 0.35


def _semantic_ids(topic: str | None) -> set[int]:
    """Journal row ids semantically near `topic` (best-effort; {} without vectors)."""
    if not topic or settings.convo_journal_top_k <= 0:
        return set()
    try:
        hits = embeddings.retrieve(
            topic, k=settings.convo_journal_top_k, corpus=store.JOURNAL_CORPUS
        )
        return {
            int(h.id)
            for h in hits
            if str(h.id).isdigit() and h.score >= _SEMANTIC_MIN_SCORE
        }
    except Exception as exc:  # noqa: BLE001 — vectors are recall quality, not memory
        log.warning("journal_semantic_recall_failed", error=str(exc))
        return set()


def _pair_lines(
    conn, speakers: list[CastMember], now: datetime, within: timedelta
) -> list[str]:
    """One line per host pair with shared history: what they last talked about."""
    names = {c.id: c.name for c in speakers}
    lines: list[str] = []
    for a, b in combinations(speakers, 2):
        shared = store.journal_for_pair(conn, a.id, b.id, now, within=within, limit=1)
        if not shared:
            continue
        e = shared[0]
        who = names.get(e.host_id, e.host_id)
        lines.append(
            f"- Last time {a.name} and {b.name} shared a segment "
            f"({_phrase_for(e, now)}): {who} {e.text}"
        )
    return lines


def journal_section(
    speakers: list[CastMember], now: datetime, topic: str | None = None
) -> str:
    """The per-host "what you've said on air before" block ('' if none) — D13.2.

    Reads each speaker's journal once (bounded by the window/per-host dials),
    ranks per host (card-tag overlap + a semantic boost from the `journal` corpus
    when a `topic` is in play and vectors are up — else pure structured recency),
    and appends the per-pair "what you two last talked about" line where both
    hosts share history. Rendered for the PER-CALL system prompt only. Any
    failure (off, no DB, empty journal) degrades to "" — the pre-D13 room.
    """
    if not settings.convo_journal_enabled or not speakers:
        return ""
    per_host = settings.convo_journal_per_host
    if per_host <= 0:
        return ""
    within = timedelta(days=settings.convo_journal_window_days)
    semantic = _semantic_ids(topic)
    try:
        blocks: list[str] = []
        with store.connect() as conn:
            for card in speakers:
                # Headroom over the per-host cut so the ranking has real choices
                # (the D9.4 pattern); the read itself stays bounded.
                candidates = store.journal_for_host(
                    conn, card.id, now, within=within, limit=per_host * 4
                )
                picked = _rank_for(card, candidates, per_host, semantic)
                if not picked:
                    continue
                lines = "\n".join(_entry_line(e, now) for e in picked)
                blocks.append(f"What {card.name} has said on air before:\n{lines}")
            pair = _pair_lines(conn, speakers, now, within)
    except Exception as exc:  # noqa: BLE001 — recall must never kill a slot
        log.warning("journal_recall_failed", error=str(exc))
        return ""
    if pair:
        blocks.append("Between them:\n" + "\n".join(pair))
    if not blocks:
        return ""

    body = "\n\n".join(blocks)
    log.info(
        "journal_recall_assembled",
        hosts=len(speakers),
        blocks=len(blocks),
        semantic=len(semantic),
    )
    return (
        "The hosts' own on-air history — things THEY said on past shows (they "
        "must stay consistent with it). Reference naturally and SPARINGLY, as "
        "people with a shared past: a callback, a held opinion, a running bit — "
        "never a recap. Anything listed here already aired — call it back in "
        f"passing, do NOT re-run it as this segment's topic:\n{body}\n\n"
    )


def pair_section(speakers: list[CastMember], now: datetime) -> str:
    """The pair line(s) alone, for the showrunner ('' if none) — D13.2.

    The beat-picker needs the hosts' RELATIONSHIP (what they last talked about,
    so a beat can build on it), not their full journals — those go to the
    orchestrator via `journal_section`. Same dials, same degrade-to-"".
    """
    if not settings.convo_journal_enabled or not speakers:
        return ""
    within = timedelta(days=settings.convo_journal_window_days)
    try:
        with store.connect() as conn:
            lines = _pair_lines(conn, speakers, now, within)
    except Exception as exc:  # noqa: BLE001 — recall must never kill a slot
        log.warning("journal_recall_failed", error=str(exc))
        return ""
    if not lines:
        return ""
    return (
        "The hosts' shared on-air history (context for the beat — build on the "
        "relationship if it fits, but do NOT re-pick these topics):\n"
        + "\n".join(lines)
        + "\n\n"
    )

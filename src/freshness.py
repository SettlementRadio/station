"""D5 — on-air freshness / anti-repetition: extract + record what aired.

The application layer over the airplay memory (the SQL lives ONLY in `world/store.py`,
the dial in `config.py`). One place turns a generated `Segment` into the salient
FEATURES the memory stores — a topic/beat handle, an opening fingerprint, a few key
phrases — and decides which segments are EXEMPT (idents / evergreen fallback, which are
*meant* to repeat). The scheduler chokepoint (D5.1) calls `record_segment` once per
placed slot (every content segment passes through it, so producers don't each need
wiring); `sweep` bounds the table from the same housekeeping. The writers' room (D5.2)
reads the memory back via `store.recent_airplay` to steer the next segment off recent
ground.

DISTINCT from the news desk's coverage memory (D4): that tracks INTENDED per-story
recurrence (which story to re-report, how it evolves); this is broad, cross-format,
output-phrasing freshness (don't reuse this opening/phrasing). D5 layers on D4.

Feature extraction is deliberately CHEAP — string heuristics over what the producers
already put on the `Segment` (`meta["beat"]`, `meta["stories"]`, the script), never an
extra LLM call (per CLAUDE.md routing, reach for `haiku` only if heuristics prove
insufficient — they don't here).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from .config import settings
from .logging_setup import get_logger
from .segment import Segment
from .world import store

log = get_logger(__name__)

# Segments that are MEANT to repeat are exempt from the airplay memory: the spoken
# AI-disclosure ident and the evergreen fallback pool (both render-once / reuse-forever,
# static content). Everything else is generated CONTENT whose wording should stay fresh.
# A gate-failed slot that fell back to evergreen also carries `meta["fallback"]`, caught
# below — belt and braces with the format check. Intrinsic domain data, not a config
# dial (CLAUDE.md: a named constant next to its logic, not in config.py).
_EXEMPT_FORMATS = ("ident", "evergreen")

# Opening fingerprint = the first N spoken words, normalized — short enough that
# near-identical openings collapse to the SAME fingerprint (D5.2 shows these as "don't
# open like these"), long enough to tell genuinely different openings apart.
_OPENING_WORDS = 8

# How many distinctive key phrases to keep per segment (a few structural beats, not the
# whole script).
_KEY_PHRASES = 5

# D7.4 — how a music slot's ARTIST is marked in its airplay `features` (the topic
# carries the track id). The music selector reads these back to avoid repeating a
# song/artist inside the freshness window (production/selector.py).
ARTIST_FEATURE_PREFIX = "artist:"

# A leading speaker label to strip before reading the opening words, e.g. "**Vell:** …"
# (talk dialogue) — so the fingerprint reflects what was SAID, not who said it. A short
# capitalised name token followed by a colon; tolerates surrounding `**` markdown.
_LABEL_RE = re.compile(r"^\s*\*{0,2}\s*[A-Za-z][\w'’.\- ]{0,30}\*{0,2}\s*:\s+")

# Reduce a fragment to comparable word tokens: lowercase, keep letters/digits, split on
# everything else. So "Tonight, we open—" and "tonight we open!" normalize alike.
_WORD_RE = re.compile(r"[a-z0-9]+")

# Common words carry no topical signal — dropped from key-phrase extraction. A small
# named constant (intrinsic data), deliberately short; this is a cheap heuristic, not a
# linguistics engine.
_STOPWORDS = frozenset(
    """
    a an and are as at be been but by for from had has have he her his i in into is it
    its of on or our she that the their them then there these they this to up us was we
    were what when which who will with would you your now here tonight today good back
    one two three new just like get got go going well right okay yeah youre im weve
    """.split()
)


def _tokens(text: str) -> list[str]:
    """Lowercased word tokens of `text` (letters/digits only)."""
    return _WORD_RE.findall(text.lower())


def _short_handle(text: str, *, max_chars: int = 100) -> str | None:
    """A normalized one-line handle for a topic/beat — first line, capped (D5.1).

    Not the full text: the beat brief can be several lines; the handle is the first
    non-empty line, whitespace-collapsed, lowercased, and truncated — enough to name the
    angle without storing the whole brief.
    """
    for raw in text.splitlines():
        line = " ".join(raw.replace("*", "").split()).strip()
        if line:
            line = line.lower()
            return line[:max_chars]
    return None


def _opening_fingerprint(script: str, *, words: int = _OPENING_WORDS) -> str | None:
    """A fingerprint of how the segment OPENED — first `words` spoken words, normalized.

    Drops a leading speaker label (so a talk turn's "Vell:" prefix doesn't count) and
    normalizes to lowercase word tokens, so two near-identical openings produce the same
    fingerprint while different ones diverge. None when the script has no words.
    """
    for raw in script.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = _LABEL_RE.sub("", line.replace("*", ""), count=1)
        toks = _tokens(line)
        if toks:
            return " ".join(toks[:words])
    return None


def _key_phrases(script: str, *, limit: int = _KEY_PHRASES) -> list[str]:
    """A few distinctive content words from the script — a cheap topical signature.

    Frequency-ranked non-stopword tokens (length > 3), de-duped, capped at `limit`. A
    crude "what was this about" handle the writers' room can compare against, extracted
    with no LLM call. Ties break by first appearance (stable).
    """
    counts: dict[str, int] = {}
    order: dict[str, int] = {}
    for i, tok in enumerate(_tokens(script)):
        if len(tok) <= 3 or tok in _STOPWORDS:
            continue
        counts[tok] = counts.get(tok, 0) + 1
        order.setdefault(tok, i)
    ranked = sorted(counts, key=lambda t: (-counts[t], order[t]))
    return ranked[:limit]


def _topic_handle(seg: Segment) -> str | None:
    """The topic/beat handle for a segment, by format (D5.1).

    Reads what the producers already put on the `Segment`: talk's showrunner beat
    (`meta["beat"]`), news's covered story ids (`meta["stories"]`, D4). A normalized
    handle, never the full text. Unknown/future formats fall back to None (the opening +
    key phrases still record).
    """
    if seg.format == "talk":
        beat = seg.meta.get("beat")
        return _short_handle(beat) if isinstance(beat, str) and beat else None
    if seg.format == "news":
        stories = seg.meta.get("stories") or []
        return ", ".join(str(s) for s in stories) if stories else None
    if seg.format == "music":  # D7.4 — the spun track's id IS the topic
        track_id = seg.meta.get("track_id")
        return str(track_id) if track_id else None
    return None


def _should_record(seg: Segment) -> bool:
    """Whether a placed segment's features belong in the airplay memory (D5.1).

    Skips the static, meant-to-repeat segments (idents, evergreen) — by format AND the
    `meta["fallback"]` marker a gate-failed slot carries.
    """
    if seg.format in _EXEMPT_FORMATS:
        return False
    if seg.meta.get("fallback"):
        return False
    return True


def extract_features(seg: Segment) -> store.AirplayRecord | None:
    """Build the airplay record for a placed segment, or None if it is exempt (D5.1).

    Returns None for exempt segments (idents/evergreen) and for a segment without a
    pinned `air_time` (it can't be anchored on the broadcast timeline). Otherwise it
    extracts the topic handle, opening fingerprint, and key phrases — features only,
    never the audio.
    """
    if not _should_record(seg):
        return None
    if not seg.air_time:
        log.debug("airplay_skip_no_air_time", seg_id=seg.id)
        return None
    try:
        aired_at = datetime.fromisoformat(seg.air_time)
    except ValueError:
        log.warning("airplay_bad_air_time", seg_id=seg.id, air_time=seg.air_time)
        return None
    script = seg.script or ""
    features = _key_phrases(script)
    # D7.4 — a music slot also marks its ARTIST so the selector can steer off a
    # recently-played artist, not just the exact track (the topic is the track id).
    artist = seg.meta.get("track_artist")
    if seg.format == "music" and artist:
        features = [f"{ARTIST_FEATURE_PREFIX}{artist}", *features[: _KEY_PHRASES - 1]]
    return store.AirplayRecord(
        seg_id=seg.id,
        format=seg.format,
        aired_at=aired_at,
        topic=_topic_handle(seg),
        opening=_opening_fingerprint(script),
        features=features,
    )


def record_segment(seg: Segment) -> bool:
    """Best-effort: extract + persist a placed segment's airplay features (D5.1).

    Called at the scheduler chokepoint, next to `_write_sidecar`. Best-effort like the
    sidecar/disk-GC housekeeping — a DB hiccup here is logged, never fatal (the audio
    aired fine; only the freshness memory misses one row). Returns True if a row was
    written.
    """
    record = extract_features(seg)
    if record is None:
        return False
    try:
        with store.connect() as conn:
            store.record_airplay(conn, record)
        return True
    except Exception as exc:  # noqa: BLE001 — freshness memory must not break playout
        log.warning("airplay_record_failed", seg_id=seg.id, error=str(exc))
        return False


def _keep_window() -> timedelta:
    """The airplay retention window: freshness window × the margin (config dials)."""
    hours = settings.freshness_window_hours * settings.freshness_retention_margin
    return timedelta(hours=hours)


def sweep(now: datetime) -> int:
    """Best-effort: bound the airplay table (drop rows past the keep window), D5.1.

    Folded into the scheduler housekeeping (next to the C2.5 disk `prune`). This is the
    airplay memory's OWN sweep — NOT the audio GC: the memory must outlive the audio it
    describes, so it is bounded by its own (much wider) window. Best-effort; returns the
    rows removed.
    """
    try:
        with store.connect() as conn:
            return store.prune_airplay(conn, now, keep=_keep_window())
    except Exception as exc:  # noqa: BLE001 — housekeeping must not break playout
        log.warning("airplay_sweep_failed", error=str(exc))
        return 0


# --- Reading the memory back into the writers' room (D5.2) -------------------
# The producers call these to get a small, ready-to-inject prompt block of what aired
# recently, so generation steers off recent ground. The block is small + variable, so
# the caller weaves it into the PER-CALL system prompt (never the cached bible) — the
# prompt cache still hits. Every read degrades to "" on an empty memory (cold start) or
# a DB hiccup, so a missing memory never blocks generation.


def _distinct(items: object, limit: int) -> list[str]:
    """De-dupe (case-insensitively, order-preserving) up to `limit` non-empty items."""
    seen: set[str] = set()
    out: list[str] = []
    for it in items:  # type: ignore[attr-defined]
        if not it:
            continue
        key = it.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it.strip())
        if len(out) >= limit:
            break
    return out


def _read_recent(now: datetime, *, fmt: str | None = None) -> list[store.AirplayRecord]:
    """The recent-airplay window for `now` (all formats, or one), best-effort."""
    within = timedelta(hours=settings.freshness_window_hours)
    try:
        with store.connect() as conn:
            if fmt is not None:
                return store.recent_by_format(conn, now, fmt, within=within)
            return store.recent_airplay(conn, now, within=within)
    except Exception as exc:  # noqa: BLE001 — a missing memory must not block generation
        log.warning("airplay_read_failed", fmt=fmt or "*", error=str(exc))
        return []


def _avoid_block(kind: str, items: list[str]) -> str:
    """Format recent topic/opening items into a prompt block, mode-aware ('' empty)."""
    if not items:
        return ""
    bullets = "\n".join(f"- {it}" for it in items)
    hard = settings.freshness_mode == "avoid"
    if kind == "topic":
        head = (
            "Recently on air — do NOT pick a beat that circles these topics/angles "
            "again; choose a different one:"
            if hard
            else "Recently on air (these ran lately — prefer a fresh angle over these):"
        )
    else:  # opening
        head = (
            "Recent openings — do NOT open like any of these; start differently:"
            if hard
            else "Recent openings (how recent segments started — open differently):"
        )
    return f"{head}\n{bullets}"


def recent_topics_block(now: datetime) -> str:
    """Recent topics/beats (all formats) to steer the showrunner off (D5.2).

    Returns "" when the memory is empty or freshness is disabled — the showrunner then
    just picks freely (the cold-start path).
    """
    if not settings.freshness_enabled:
        return ""
    records = _read_recent(now)
    topics = _distinct((r.topic for r in records), settings.freshness_recent_limit)
    return _avoid_block("topic", topics)


def recent_openings_block(now: datetime, fmt: str) -> str:
    """Recent openings (scoped to `fmt`) to steer a producer's first line off (D5.2).

    Format-scoped so a producer varies its OWN openings without being constrained by
    another format's wording. "" on an empty memory / when disabled.
    """
    if not settings.freshness_enabled:
        return ""
    records = _read_recent(now, fmt=fmt)
    openings = _distinct((r.opening for r in records), settings.freshness_recent_limit)
    return _avoid_block("opening", openings)

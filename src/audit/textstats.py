"""Pure text maths for the audit: register, entities, repetition.

Every number the audit derives from *words* is computed here — over stored world
quotes (`metrics.py`) and over generated scripts (`probe.py`) alike — so "how plain is
this" and "what is this segment about" are measured one way everywhere. Nothing here
touches the DB, the network or the clock: it is pure functions over strings, which is
why it carries the unit tests while `probe.py` carries the spend.

Two deliberately different hedge counters, because §1d measures two different things:

  * `QUOTE_HEDGES` — over stored world quotes ("1 of 120 contains any hedge"). Catches
    the *written* hedge: "I think", "probably", "we'll have to see".
  * `SCRIPT_DISFLUENCY` — over generated dialogue ("1.7 per 1000 words vs 30–60 in real
    speech"). Catches spoken dead weight too: fillers, repair, false starts.

Both regexes are transcribed from `scripts/audit_seed/` unchanged, so the committed
baseline stays comparable with the external audit's own findings. Do not "improve" them
without re-baselining — the numbers are only meaningful against each other.

Entity counting replaces the seed's crude proper-noun regex (which scored "That" and
"Because" as names). A candidate phrase counts as an entity only if the world actually
knows it — the gazetteer's places, the `figures` table's people, the story log's names —
or if it is multi-word/numbered, so a name the tick invented tonight still registers.
Cast names are excluded: two hosts saying each other's name is not a topic.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from collections.abc import Iterable, Sequence

# --- the register regexes (transcribed from the audit seed) ------------------

CONTRACTIONS = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.I)

# Stored world quotes: does anyone in this world ever sound unsure? (§1d)
QUOTE_HEDGES = re.compile(
    r"\b(um|uh|sort of|kind of|you know|I mean|I guess|maybe|probably|"
    r"honestly|look,|well,|I think|we'll see)\b",
    re.I,
)

# Generated dialogue: fillers, false starts, repair — the dead weight real speech has
# and the station's does not (1.7/1000w against 30–60 in real transcripts).
SCRIPT_DISFLUENCY = re.compile(
    r"\b(erm|um|uh|sorry\W|hang on|what\?|say again|wait,|no, I mean|"
    r"I mean\b|you know\b|sort of\b|kind of\b|like,|anyway\b|whatever\b)",
    re.I,
)

# A dialogue line: "Vell: …" or "Vell [warm]: …". The ≤3-word speaker guard keeps a
# sentence that merely contains a colon from being read as a turn.
TURN = re.compile(r"^([A-Z][A-Za-z'’ \-]{1,24})(?: \[[a-z]+\])?:\s*(.*)$")

# A run of capitalised words, allowing possessives and a trailing designation
# ("Cold Harbor", "Sael's Reach", "Theta-9", "Relay 12").
PROPER_PHRASE = re.compile(
    r"\b[A-Z][a-z’']+(?:-\d+)?(?:[ -](?:[A-Z][a-z’']+(?:-\d+)?|\d+))*"
)

# Capitalised words that open sentences and are never names. Only ever consulted for
# SINGLE-word candidates — a multi-word phrase is judged by its first token.
_NOT_A_NAME = frozenset(
    """a an the and but or so then now well look listen right okay yes no not if when
    while because that this these those there here it its i you we they he she his her
    their our my your what who how why every each some most all both few many more much
    good bad fine sure maybe probably honestly anyway still just even only also again
    today tonight tomorrow yesterday morning afternoon evening night monday tuesday
    wednesday thursday friday saturday sunday january february march april may june july
    august september october november december one two three four five six seven eight
    nine ten first second third last next new old""".split()
)


# --- turns and register ------------------------------------------------------


def turns(script: str) -> list[str]:
    """The spoken text of each dialogue turn in a script (labels stripped)."""
    out: list[str] = []
    for line in script.splitlines():
        m = TURN.match(line.strip())
        if m and len(m.group(1).split()) <= 3:
            out.append(m.group(2))
    return out


def _pct(n: float, d: float) -> float | None:
    return round(100 * n / d, 1) if d else None


def register_stats(texts: Sequence[str]) -> dict:
    """Register maths over short texts — the `quotes.*` group's shape (§1d)."""
    if not texts:
        return {"count": 0}
    words = [len(t.split()) for t in texts]
    joined = " ".join(texts)
    n_words = max(1, len(joined.split()))
    return {
        "count": len(texts),
        "mean_words": round(statistics.mean(words), 1),
        "median_words": statistics.median(words),
        "pct_with_contraction": _pct(
            sum(1 for t in texts if CONTRACTIONS.search(t)), len(texts)
        ),
        "hedges_per_1000w": round(
            1000 * len(QUOTE_HEDGES.findall(joined)) / n_words, 1
        ),
        "pct_under_12w": _pct(sum(1 for w in words if w <= 12), len(texts)),
    }


def script_register(scripts: Sequence[str]) -> dict:
    """The `register.*` group over generated dialogue (§1d), minus the daytime ban.

    Turn-level shape (median length, the monologue and one-word tails) plus the two
    plain-speech counters. `banned_abstractions_daytime` is added by the caller, which
    is the only thing that knows which programme each script came from.
    """
    turn_words: list[int] = []
    spoken: list[str] = []
    for script in scripts:
        for turn in turns(script):
            turn_words.append(len(turn.split()))
            spoken.append(turn)
    if not turn_words:
        return {"segments": len(scripts), "turns": 0}
    text = " ".join(spoken)
    n_words = max(1, len(text.split()))
    return {
        "segments": len(scripts),
        "turns": len(turn_words),
        "median_turn_words": statistics.median(turn_words),
        "mean_turn_words": round(statistics.mean(turn_words), 1),
        "pct_turns_over_40w": _pct(
            sum(1 for w in turn_words if w >= 40), len(turn_words)
        ),
        "pct_turns_under_4w": _pct(
            sum(1 for w in turn_words if w <= 3), len(turn_words)
        ),
        "contractions_per_100w": round(
            100 * len(CONTRACTIONS.findall(text)) / n_words, 1
        ),
        "hedges_per_1000w": round(
            1000 * len(SCRIPT_DISFLUENCY.findall(text)) / n_words, 1
        ),
    }


def banned_abstraction_hits(scripts: Iterable[str], banned: Iterable[str]) -> list[str]:
    """Which banned house-poetry phrases appear at all — R1's hard guard (§2b)."""
    lowered = [s.lower() for s in scripts]
    return sorted({p for p in banned for s in lowered if p in s})


# --- entities: what is this segment actually about? -------------------------


def normalise_name(phrase: str) -> str:
    """A name's counting key: whitespace collapsed, possessives dropped.

    Without this, "Cold Harbor" and "Cold Harbor's" score as two different entities and
    the dominance the §1a finding is about is split in half.
    """
    words = []
    for word in phrase.split():
        word = word.strip("'’,.;:!?")
        for suffix in ("'s", "’s"):
            if word.casefold().endswith(suffix) and len(word) > len(suffix) + 1:
                word = word[: -len(suffix)]
        if word:
            words.append(word)
    return " ".join(words)


def vocabulary_from(texts: Iterable[str]) -> set[str]:
    """The named things mentioned in `texts` — for building the world's entity list.

    Emits each capitalised phrase AND its individual capitalised words, because a script
    names the short form: the story titled "The Meridian Accords" is discussed as
    "Accords". Stopwords are dropped, so a title's leading "The" or "A" never enters.
    """
    out: set[str] = set()
    for text in texts:
        for phrase in PROPER_PHRASE.findall(text or ""):
            words = normalise_name(phrase).split()
            if len(words) > 1 and words[0].casefold() not in _NOT_A_NAME:
                out.add(" ".join(words))
            for word in words:
                if word.casefold() not in _NOT_A_NAME and len(word) > 2:
                    out.add(word)
    return out


def entity_counts(
    text: str, vocabulary: Iterable[str], *, exclude: Iterable[str] = ()
) -> Counter:
    """Count the world's named things in `text`, maximal phrase first.

    Maximal-phrase-first matters: "Cold Harbor" scores once as a place, not twice as
    "Cold" and "Harbor". A phrase counts when the world knows it (`vocabulary`), or when
    it is multi-word / numbered — so a name tonight's tick invented is not invisible,
    while "That" and "Because" never count. `exclude` drops the cast: the hosts naming
    each other is not a topic.
    """
    known = {normalise_name(v).casefold() for v in vocabulary}
    skip = {normalise_name(v).casefold() for v in exclude}
    counts: Counter = Counter()
    for raw in PROPER_PHRASE.findall(text):
        phrase = normalise_name(raw)
        # A sentence-initial capital gets swallowed into the match ("Because Cold
        # Harbor"), so peel stopword heads off until a name is left — but only after
        # checking the whole phrase, since the world has places like "The Old System".
        while phrase:
            fold = phrase.casefold()
            if fold in skip or any(fold.startswith(f"{s} ") for s in skip):
                break
            head = fold.split()[0].split("-")[0]
            multi = " " in phrase or "-" in phrase or any(c.isdigit() for c in phrase)
            if fold in known or (multi and head not in _NOT_A_NAME):
                counts[phrase] += 1
                break
            if head in _NOT_A_NAME and " " in phrase:
                phrase = phrase.split(" ", 1)[1]
                continue
            break
    return counts


def dominant_entity(
    *texts: str, vocabulary: Iterable[str], exclude: Iterable[str] = ()
):
    """The most-named entity across `texts` — a segment's subject in one string."""
    vocab = list(vocabulary)
    excl = list(exclude)
    total: Counter = Counter()
    for text in texts:
        total += entity_counts(text or "", vocab, exclude=excl)
    if not total:
        return None
    # Ties break on the name so two runs of the same world can't disagree by luck.
    top = max(total.items(), key=lambda kv: (kv[1], kv[0]))
    return top[0]


# --- repetition between consecutive segments (§1e) --------------------------


def longest_common_substring_len(a: str, b: str, *, cap: int = 2000) -> int:
    """Longest shared run of characters between two scripts, in characters.

    Binary search over the length with a window set per probe: O(n log n) rather than
    the O(n·m) table, which matters on 4,000-character scripts. Saturates at `cap` (well
    above anything the §1e finding needs — a verbatim two-line exchange is ~120).
    """
    a, b = " ".join(a.split()), " ".join(b.split())
    lo, hi = 0, min(len(a), len(b), cap)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _shares_window(a, b, mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def _shares_window(a: str, b: str, n: int) -> bool:
    """Do `a` and `b` share any substring of exactly length `n`?"""
    if n <= 0 or n > min(len(a), len(b)):
        return False
    windows = {a[i : i + n] for i in range(len(a) - n + 1)}
    return any(b[i : i + n] in windows for i in range(len(b) - n + 1))


def _word_ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9']+", text.casefold())
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def repeated_ngram_rate(current: str, previous: str, *, n: int = 8) -> float | None:
    """Share of `current`'s n-grams that also appear in `previous` (§1e), as a percent.

    The soft counterpart to the longest-substring measure: a segment paraphrasing the
    last one's close scores here even when no single run of characters is long.
    """
    cur = _word_ngrams(current, n)
    if not cur:
        return None
    prev = _word_ngrams(previous, n)
    return round(100 * len(cur & prev) / len(cur), 2)


__all__ = [
    "CONTRACTIONS",
    "PROPER_PHRASE",
    "QUOTE_HEDGES",
    "SCRIPT_DISFLUENCY",
    "TURN",
    "banned_abstraction_hits",
    "dominant_entity",
    "entity_counts",
    "longest_common_substring_len",
    "normalise_name",
    "register_stats",
    "repeated_ngram_rate",
    "script_register",
    "turns",
    "vocabulary_from",
]

"""Pronunciation lexicon (D9.1) — invented names spoken right, behind the TTS seam.

The world is full of invented proper nouns (Zhe, the Lumen Festival) that a
grapheme-to-phoneme engine guesses at — and each engine guesses differently.
This module applies the human-edited lexicon (`settings.tts_lexicon_path`,
config/pronunciation.yaml) to a script's text just before synthesis, so a known
name is spoken as intended and CONSISTENTLY on whichever engine is active.

Only `providers/tts.py` calls this (it is part of the seam): callers of
`synthesize` never know the mechanism. Per engine:

  * kokoro — an entry's `phonemes` string is injected via misaki's
    `[Name](/phonemes/)` markup, which pins the exact phonemes (verified: the
    KPipeline honours it, including a trailing possessive 's). Entries without
    `phonemes` fall back to the plain `respell` substitution.
  * elevenlabs / say — the `respell` (a phonetic respelling like "Zhay") is
    substituted for the name. TODO(D9.1→C6): ElevenLabs also has a hosted
    pronunciation-dictionary mechanism (`pronunciation_dictionary_locators` on
    the convert call, fed by uploaded PLS dictionaries; phoneme support is
    model-dependent). Wiring it means an upload + locator-id lifecycle and a
    funded key to verify — revisit with the C6 flagship listen; the respelling
    substitution is the working path until then.

An unknown name simply doesn't match and passes through to the engine default,
unharmed. A missing/malformed lexicon file degrades to "no substitutions" with
a log line — the lexicon must never fail a render.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import settings
from ..logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class LexiconEntry:
    """One pronunciation: a spelled name and how to say it."""

    name: str  # the spelling as it appears in scripts (whole-word, case-sensitive)
    respell: str  # phonetic respelling any engine can read ("Zhay", "LOO-men")
    phonemes: str | None = None  # optional misaki/IPA string for Kokoro ("ʒeɪ")


# The parsed lexicon + its compiled matcher, cached per (path, mtime) so a
# long-running scheduler picks up a hand-edit without a restart, while a buffer
# run voicing many segments parses the file once.
_cache: tuple[tuple[str, float], list[LexiconEntry], re.Pattern[str] | None] | None = (
    None
)


def _load() -> tuple[list[LexiconEntry], re.Pattern[str] | None]:
    """Load (and cache) the lexicon entries + their single alternation regex."""
    global _cache
    path = settings.tts_lexicon_path
    try:
        key = (str(path), path.stat().st_mtime)
    except OSError:
        # No lexicon file — a valid state (fresh checkout, lexicon deleted).
        return [], None

    if _cache is not None and _cache[0] == key:
        return _cache[1], _cache[2]

    import yaml

    entries: list[LexiconEntry] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for item in raw:
            name = str(item.get("name", "")).strip()
            respell = str(item.get("respell", "")).strip()
            phonemes = str(item.get("phonemes", "")).strip() or None
            if not name or not respell:
                log.warning("lexicon_entry_skipped", entry=item)
                continue
            entries.append(LexiconEntry(name=name, respell=respell, phonemes=phonemes))
    except Exception as exc:  # a broken lexicon must never fail a render
        log.error("lexicon_load_failed", path=str(path), error=str(exc))
        return [], None

    # One whole-word alternation, longest name first so a longer name wins over
    # a shorter prefix of itself. Case-sensitive: proper nouns as authored.
    pattern = None
    if entries:
        names = sorted((e.name for e in entries), key=len, reverse=True)
        pattern = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in names) + r")\b")

    _cache = (key, entries, pattern)
    log.debug("lexicon_loaded", path=str(path), entries=len(entries))
    return entries, pattern


def apply_lexicon(text: str, provider: str) -> str:
    """Substitute known invented names with their pronunciation for `provider`.

    kokoro gets misaki `[Name](/phonemes/)` markup (or the respell when an entry
    has no phonemes); every other engine gets the phonetic respelling. Unknown
    names don't match and pass through unchanged.
    """
    if not settings.tts_lexicon_enabled:
        return text
    entries, pattern = _load()
    if pattern is None:
        return text

    by_name = {e.name: e for e in entries}
    count = 0

    def _sub(m: re.Match[str]) -> str:
        nonlocal count
        entry = by_name[m.group(0)]
        count += 1
        if provider == "kokoro" and entry.phonemes:
            return f"[{entry.name}](/{entry.phonemes}/)"
        return entry.respell

    result = pattern.sub(_sub, text)
    if count:
        log.debug("lexicon_applied", provider=provider, substitutions=count)
    return result

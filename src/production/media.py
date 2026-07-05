"""Curated media registry — which clip plays where (D7.0).

The ident/theme/sting→placement mapping from docs/JINGLE_PROMPTS.md §3, keyed by
the exact §4 filenames. This is intrinsic domain data (the config-vs-constant rule
in config.py — like the voice registries in providers/tts.py): the *names* are the
contract with the human's Suno production workflow, so they live here as named
module constants, not in settings. Only the root (`settings.assets_dir`) is config.

Everything here is CURATED media under `assets/` — gitignored, backed up (C5),
and automatically safe from the C2.5 disk GC (`prune` only ever scans
`segments_dir`). Nothing is discovered by scanning: a clip is resolved by its
registered path, and a missing file degrades to None (log + skip — the station
simply doesn't play that clip yet), never a crash. D7.2 places these as ordered
playlist entries; D7.3 ducks the `*_bed` variants under speech.

The songs catalogue (`assets/music/` + the `tracks` table) is separate — see
`track_audio_path` / `is_playable` at the bottom: a track's `audio_path` (repo-
root-relative, from config/tracks.yaml) is the only file↔lore link, and a track
is playable iff that file exists right now.
"""

from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger
from ..world.store import Track

log = get_logger(__name__)

# Repo root, for resolving the manifest's repo-relative `audio_path` strings
# (e.g. "assets/music/…"); same pattern as config.py's _REPO_ROOT.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# --- The §3/§4 placement registry (paths relative to assets_dir) -------------

# Station idents (Group A) — the core identity clips.
IDENTS: dict[str, str] = {
    "signature": "idents/a1_signature.mp3",  # between programs; the sung logo
    "top_of_hour": "idents/a2_top_of_hour.mp3",  # hourly station ID, under DJ
    "disclosure_bed": "idents/a3_disclosure_bed.mp3",  # under the spoken C3 ident
}

# Program themes — the opener that airs at a program boundary (D7.2 "top of
# show"), keyed by the D6 grid's program ids (docs/programming/grid.yaml).
PROGRAM_THEMES: dict[str, str] = {
    "long_night": "themes/b4_night.mp3",  # B4 — Vell's night signature
    "first_light": "themes/b5_first_light.mp3",  # B5 — Wren's sunrise lift
    "daywatch": "themes/b5a_daywatch.mp3",  # B5a — the long steady day
    "nightfall": "themes/b5b_nightfall.mp3",  # B5b — the dusk handover
}

# Format themes — the opener for a *format* (not a daypart program): the news
# desk and the talk show carry their own signatures wherever they air.
FORMAT_THEMES: dict[str, str] = {
    "news": "themes/c7_news.mp3",  # C7 — "headlines are starting"
    "talk": "themes/c9_talk.mp3",  # C9 — "pull up a chair"
}

# Loopable BED variants for D7.3 ducking (longer trims of the same generations):
# a soft bed under the night talk show, the talk bed under conversation. Beds are
# selective by design — news (and anything unmapped) stays dry.
PROGRAM_BEDS: dict[str, str] = {
    "long_night": "themes/b4_night_bed.mp3",
}
FORMAT_BEDS: dict[str, str] = {
    "talk": "themes/c9_talk_bed.mp3",
}

# Stings — short punctuation, by moment. "news" fires before the pinned
# `news@:00` clock entry (D7.2); "handover" at the first_light/nightfall
# boundaries (Vell↔Wren, both directions); "music_bumper" right before the
# `[SONG]` slot (D7.4); the D18 break pair belongs to D8's ad breaks.
STINGS: dict[str, str] = {
    "news": "stings/c8_news_sting.mp3",
    "handover": "stings/b6_handover.mp3",
    "music_bumper": "stings/c10_music_bumper.mp3",
    "time_check": "stings/d13_time_check.mp3",
    "advisory": "stings/d15_advisory.mp3",
    "break_in": "stings/d18_break_in.mp3",  # D8
    "break_out": "stings/d18_break_out.mp3",  # D8
}

# Transition sweepers (A4 ×3) by the D6 grid's `daypart` label — the quick
# segment-to-segment joins, picked by daypart energy (§0's three tiers).
SWEEPERS: dict[str, str] = {
    "deep night": "stings/a4_sweeper_calm.mp3",
    "first light": "stings/a4_sweeper_mid.mp3",
    "daytime": "stings/a4_sweeper_bright.mp3",
    "nightfall": "stings/a4_sweeper_mid.mp3",
}
_SWEEPER_DEFAULT = "stings/a4_sweeper_mid.mp3"  # unmapped daypart (e.g. `default`)

# Special/event themes — placed by their own moments, not the daily grid:
# "conditions" for the space-weather segment, "letters" for Phase E dedications,
# "lumen" for the one fixed canon event, "special_coverage" for any D3-generated
# big event the station carries (event-agnostic — the D17 workhorse).
SPECIAL_THEMES: dict[str, str] = {
    "conditions": "themes/d14_conditions.mp3",
    "letters": "themes/c11_letters.mp3",
    "games": "themes/c12_games.mp3",
    "lumen": "themes/d16_lumen.mp3",
    "special_coverage": "themes/d17_special_coverage.mp3",
}


# --- Resolution (registered name -> playable file, or None) ------------------


def _resolve(rel_path: str | None, *, kind: str, key: str) -> Path | None:
    """Resolve an assets-relative clip path to an absolute Path, or None.

    None when the key isn't registered OR the file isn't on disk yet (the human
    generates media over time — a missing clip means "skip this placement",
    logged at warning so it shows up, never a crash)."""
    if rel_path is None:
        log.warning("media_unmapped", kind=kind, key=key)
        return None
    path = settings.assets_dir / rel_path
    if not path.is_file():
        log.warning("media_file_missing", kind=kind, key=key, path=str(path))
        return None
    return path


def ident(name: str) -> Path | None:
    """A core station ident by name ("signature" | "top_of_hour" | …)."""
    return _resolve(IDENTS.get(name), kind="ident", key=name)


def theme_for_program(program_id: str) -> Path | None:
    """The theme that opens a program boundary, by D6 grid program id."""
    return _resolve(PROGRAM_THEMES.get(program_id), kind="theme", key=program_id)


def theme_for_format(fmt: str) -> Path | None:
    """The theme that opens a format (news/talk), by format name."""
    return _resolve(FORMAT_THEMES.get(fmt), kind="format_theme", key=fmt)


def bed_for_program(program_id: str) -> Path | None:
    """The loopable bed ducked under a program's speech (D7.3), or None (dry)."""
    rel = PROGRAM_BEDS.get(program_id)
    if rel is None:
        return None  # most programs are deliberately dry — not a warning
    return _resolve(rel, kind="bed", key=program_id)


def bed_for_format(fmt: str) -> Path | None:
    """The loopable bed ducked under a format's speech (D7.3), or None (dry)."""
    rel = FORMAT_BEDS.get(fmt)
    if rel is None:
        return None
    return _resolve(rel, kind="format_bed", key=fmt)


def sting(name: str) -> Path | None:
    """A sting by moment name ("news" | "handover" | "music_bumper" | …)."""
    return _resolve(STINGS.get(name), kind="sting", key=name)


def sweeper_for_daypart(daypart: str) -> Path | None:
    """The A4 transition sweeper matching a daypart's energy (mid if unmapped)."""
    rel = SWEEPERS.get(daypart, _SWEEPER_DEFAULT)
    return _resolve(rel, kind="sweeper", key=daypart)


# --- Track audio (the songs catalogue's file side) ----------------------------


def track_audio_path(track: Track) -> Path:
    """The absolute path of a track's audio file (repo-root-relative manifest path)."""
    return _REPO_ROOT / track.audio_path


def is_playable(track: Track) -> bool:
    """Whether a track can actually air: its manifest-named file exists on disk.

    The load-bearing D7 boundary: lore without a file is still referenceable
    world culture, but only a track whose `audio_path` resolves is PLAYABLE
    (checked live — dropping the file in makes the row playable, no re-seed)."""
    return track_audio_path(track).is_file()

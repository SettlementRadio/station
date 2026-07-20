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
# show"). This dict holds only the OVERRIDES: the batch-1 daypart files (whose
# names don't match their program id) and the two reuse cases. Every other
# program resolves by CONVENTION in `theme_for_program` — `themes/<program_id>.mp3`
# (docs/JINGLE_PROMPTS_2.md) — so a new grid program wires its opener the moment
# the clip lands, with no edit here.
PROGRAM_THEMES: dict[str, str] = {
    # Legacy daypart themes (batch-1 files, name ≠ program id) — kept as overrides.
    "long_night": "themes/b4_night.mp3",  # B4 — Vell's night signature
    "first_light": "themes/b5_first_light.mp3",  # B5 — Wren's sunrise lift
    "nightfall": "themes/b5b_nightfall.mp3",  # B5b — the dusk handover
    # Reuse existing special themes (no bespoke clip needed).
    "the_mailbag": "themes/c11_letters.mp3",  # the Letters show reuses C11
    "the_circuit": "themes/c12_games.mp3",  # the Sport show reuses C12
    "conditions": "themes/d14_conditions.mp3",  # R3.1 — Conditions reuses D14
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
    # The warm night bed (B4) ducks under the deep-night talk shows. Reused for
    # all of them for now: the daytime talk bed (FORMAT_BEDS) would be tonally
    # wrong under the night, so map the night shows here to the night bed until
    # dedicated per-show beds are curated.
    "long_night": "themes/b4_night_bed.mp3",
    "deep_hours": "themes/b4_night_bed.mp3",
    "deep_field": "themes/b4_night_bed.mp3",
}
FORMAT_BEDS: dict[str, str] = {
    "talk": "themes/c9_talk_bed.mp3",
    # D8.0 L2 — a spot opted into "read over a bed" reuses the talk bed until a
    # dedicated ad bed is curated (JINGLE_PROMPTS is the human's media pipeline).
    "commercial": "themes/c9_talk_bed.mp3",
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
    # D8.0 L4 — the sparse ~2s brand-sting bookend, the ONLY prerecorded ad
    # audio (curated by the human; L4 degrades to a plain read until it exists).
    "brand": "stings/d8_brand.mp3",
    # R3.1 — The Count's chart-countdown ramp (docs/JINGLE_PROMPTS_3.md D20) and
    # The Relay Round's scoring ding (D21). Registered ahead of the machinery that
    # calls them (R6.1 wires the chart countdown; the quiz format doesn't exist
    # yet), same as C12's games theme in batch 1 — speculative/extensible: the
    # name resolves the moment the human drops the file in, whichever pack ends
    # up placing it.
    "chart_countdown_approaching": "stings/d20a_chart_approaching.mp3",
    "chart_countdown_climbing": "stings/d20b_chart_climbing.mp3",
    "chart_countdown_number_one": "stings/d20c_chart_number_one.mp3",
    "quiz_point": "stings/d21_quiz_point.mp3",
}

# Transition sweepers (A4 ×3) by the grid's `daypart` label — the quick
# segment-to-segment joins, picked by daypart energy (§0's three tiers). Covers
# the current grid's dayparts; anything unmapped falls to the mid sweeper.
SWEEPERS: dict[str, str] = {
    # deep-night — calm
    "deep night": "stings/a4_sweeper_calm.mp3",
    # day energy — bright
    "morning": "stings/a4_sweeper_bright.mp3",
    "late morning": "stings/a4_sweeper_bright.mp3",
    "midday": "stings/a4_sweeper_bright.mp3",
    "afternoon": "stings/a4_sweeper_bright.mp3",
    "weekend morning": "stings/a4_sweeper_bright.mp3",
    "daytime": "stings/a4_sweeper_bright.mp3",
    # edges / transitions — mid
    "first light": "stings/a4_sweeper_mid.mp3",
    "evening": "stings/a4_sweeper_mid.mp3",
    "nightfall": "stings/a4_sweeper_mid.mp3",
    "weekend": "stings/a4_sweeper_mid.mp3",
}
_SWEEPER_DEFAULT = "stings/a4_sweeper_mid.mp3"  # unmapped daypart (e.g. `default`)

# R2.3 — the same A4 set keyed by the program's `energy` dial (R1.0), the direct
# match GRID_V2 asked for: the grid's calm|steady|bright IS the sweeper tier.
# The daypart table above stays as the fallback for programs without an energy.
ENERGY_SWEEPERS: dict[str, str] = {
    "calm": "stings/a4_sweeper_calm.mp3",
    "steady": "stings/a4_sweeper_mid.mp3",
    "bright": "stings/a4_sweeper_bright.mp3",
}

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
    """The theme that opens a program boundary, by grid program id.

    An explicit `PROGRAM_THEMES` override wins (the legacy daypart files + the
    reuse cases); otherwise the CONVENTION path `themes/<program_id>.mp3` — so a
    new grid program wires its opener the moment the clip lands, no registry edit
    (docs/JINGLE_PROMPTS_2.md). Missing file -> None (logged + skipped; the
    boundary then falls back to the format theme — see placement.py).
    """
    rel = PROGRAM_THEMES.get(program_id, f"themes/{program_id}.mp3")
    return _resolve(rel, kind="theme", key=program_id)


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


def sweeper_for_energy(energy: str) -> Path | None:
    """The A4 sweeper matching a program's `energy` (R2.3), or None if unmapped.

    None (not the mid default) when the energy isn't one of calm|steady|bright,
    so the caller can fall back to the daypart mapping instead."""
    rel = ENERGY_SWEEPERS.get(energy)
    if rel is None:
        log.warning("media_unmapped", kind="sweeper_energy", key=energy)
        return None
    return _resolve(rel, kind="sweeper_energy", key=energy)


# --- Track audio (the songs catalogue's file side) ----------------------------


def sponsor_clip(rel_path: str) -> Path | None:
    """A sponsor's supplied clip (repo-root-relative, kept under `assets/`), or None.

    D8.2: the optional pre-recorded acknowledgement a sponsor provides instead
    of a voiced read. Curated media like everything here — under `assets/` the
    C2.5 GC never touches it. Missing file → None (the caller degrades to the
    voiced "Powered by" read; never a crash).
    """
    path = _REPO_ROOT / rel_path
    if not path.is_file():
        log.warning(
            "media_file_missing", kind="sponsor_clip", key=rel_path, path=str(path)
        )
        return None
    return path


def track_audio_path(track: Track) -> Path:
    """The absolute path of a track's audio file (repo-root-relative manifest path)."""
    return _REPO_ROOT / track.audio_path


def is_playable(track: Track) -> bool:
    """Whether a track can actually air: its manifest-named file exists on disk.

    The load-bearing D7 boundary: lore without a file is still referenceable
    world culture, but only a track whose `audio_path` resolves is PLAYABLE
    (checked live — dropping the file in makes the row playable, no re-seed)."""
    return track_audio_path(track).is_file()

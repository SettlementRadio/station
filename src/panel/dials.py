"""E1.5 — the dials page: the tagged `.env` groups, editable with honest state.

The dials are the operator's tuning knobs (`settings.*`, from `src/config.py`).
This groups them by the ADMIN_MANUAL sections and, for each, shows three truths:

  * EFFECTIVE — the LIVE value on the running `settings` object (what the process
    is actually using; may lag `.env` until a restart);
  * DEFAULT  — the field's default in `src/config.py`;
  * FILE     — the value written in `.env` (an override), or "unset".

Writes go to `.env` as a **comment-preserving line edit**: an active `KEY=` line
is replaced in place; a new override is appended; setting a dial back to its
DEFAULT removes the override line. The write is atomic, diffed first, with a
one-deep `.bak` — the same habit as the other editors.

Honest about restart: `settings` is read ONCE at import, so a change takes effect
on a consumer's NEXT process start — the cron scheduler/tick pick it up on their
next run; a long-running `serve`/this panel needs a restart. The effective column
tells the truth in the meantime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import TypeAdapter

from ..config import Settings, settings
from ..logging_setup import get_logger

log = get_logger(__name__)

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


# --- The dial groups (the ADMIN_MANUAL section map) --------------------------


@dataclass(frozen=True)
class Group:
    slug: str
    title: str
    note: str
    fields: tuple[str, ...]


# Curated groups — the tags ADMIN_MANUAL points the panel at. List dials (e.g.
# rotations/speaker sets) are shown read-only (env list-parsing is JSON, not a
# knob); scalars (int/float/bool/str) are editable.
DIAL_GROUPS: tuple[Group, ...] = (
    Group(
        "world_tick",
        "World tick",
        "The nightly world engine (D3/R4.0).",
        (
            "world_tick_new_stories_min",
            "world_tick_new_stories_max",
            "world_tick_large_ratio",
            "world_tick_dayarc_stories_max",
            "world_tick_dayarc_beats_max",
            "world_tick_advance_max",
            "world_tick_resolve_after_ticks",
            "world_tick_max_active_stories",
            "world_tick_quiet_domains",
            "world_tick_dedup_threshold",
            "world_tick_dedup_jaccard",
            "world_tick_beat_horizon_days",
        ),
    ),
    Group(
        "micro_tick",
        "Micro-tick",
        "The intra-day nudge (R4.1).",
        (
            "micro_tick_enabled",
            "micro_tick_advance_probability",
            "micro_tick_live_window_hours",
        ),
    ),
    Group(
        "news",
        "News desk",
        "Story selection + the living day (D4/R4.2).",
        (
            "news_story_count",
            "news_target_breaking",
            "news_target_trailed",
            "news_target_ongoing",
            "news_breaking_window_hours",
            "news_trail_horizon_days",
            "news_repeat_max_stale_hours",
            "news_canon_weight",
            "news_breaking_bonus",
            "news_evolve_bonus",
            "news_story_count_short",
            "news_trail_max_stale_hours",
            "news_trail_proximity_bonus",
            "news_quotes_per_story",
        ),
    ),
    Group(
        "freshness",
        "Freshness",
        "On-air anti-repetition (D5).",
        (
            "freshness_enabled",
            "freshness_window_hours",
            "freshness_recent_limit",
            "freshness_mode",
        ),
    ),
    Group(
        "figures",
        "Figures & quotes",
        "The world's people (D10).",
        (
            "world_tick_figures_enabled",
            "world_tick_figures_per_story_max",
            "world_tick_quotes_per_story_max",
            "context_quotes_limit",
            "context_quotes_top_k",
            "news_quotes_per_story",
        ),
    ),
    Group(
        "flow",
        "Talk continuity / flow",
        "Single-show flow (D12).",
        (
            "convo_continuity_enabled",
            "convo_continuity_max_segments",
            "convo_continuity_handoff_max_age_min",
            "convo_flow_timecheck",
            "convo_flow_signon",
            "convo_flow_short_show_max_min",
        ),
    ),
    Group(
        "ads",
        "Ad load",
        "Break cadence (D8).",
        (
            "commercial_break_enabled",
            "commercial_break_max_segments",
            "commercial_break_promo_every_n",
            "sponsor_read_every_n_breaks",
        ),
    ),
    Group(
        "emotion",
        "Emotion",
        "The default logical emotion (D9.0).",
        ("tts_emotion_default",),
    ),
    Group(
        "guests",
        "Guests / soundbites",
        "Non-host voices (D9.3).",
        (
            "convo_guest_enabled",
            "convo_guest_chance",
        ),
    ),
    Group(
        "memory",
        "DJ memory",
        "World recall + on-air journal (D9.4/D13).",
        (
            "convo_memory_enabled",
            "convo_memory_per_host",
            "convo_memory_window_days",
            "convo_journal_enabled",
            "convo_journal_per_host",
            "convo_journal_window_days",
        ),
    ),
    Group(
        "embeddings",
        "Embeddings",
        "Semantic recall breadth (D2).",
        (
            "context_canon_top_k",
            "news_canon_recall_k",
        ),
    ),
    Group(
        "cache",
        "Cache TTL",
        "The shared-bible prompt cache (CO3).",
        ("llm_cache_bible_ttl",),
    ),
    Group(
        "music",
        "Music selector weights",
        "The song-pick policy (D7.4).",
        (
            "music_select_daypart_weight",
            "music_select_world_weight",
            "music_select_featured_weight",
            "music_select_repeat_track_penalty",
            "music_select_repeat_artist_penalty",
            "music_select_era_repeat_penalty",
            "music_select_jitter",
        ),
    ),
    Group(
        "safety",
        "Safety & disclosure",
        "Production must stay ON (CLAUDE.md).",
        (
            "safety_enabled",
            "disclosure_enabled",
            "disclosure_every_n",
        ),
    ),
)

# Toggles that must stay ON in production — rendered with a loud warning.
_PRODUCTION_ON = frozenset({"safety_enabled", "disclosure_enabled"})


# --- .env parsing / writing (comment-preserving) -----------------------------


def env_key(name: str) -> str:
    """The `.env` KEY for a field (upper-case; pydantic is case-insensitive)."""
    return name.upper()


def _env_lines() -> list[str]:
    if not _ENV_PATH.exists():
        return []
    return _ENV_PATH.read_text(encoding="utf-8").splitlines()


def current_text() -> str:
    return _ENV_PATH.read_text(encoding="utf-8") if _ENV_PATH.exists() else ""


def _active_index(lines: list[str], key: str) -> int | None:
    """Index of an ACTIVE (uncommented) `KEY=…` line, or None."""
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith("#"):
            continue
        if "=" in s and s.split("=", 1)[0].strip() == key:
            return i
    return None


def env_overrides() -> dict[str, str]:
    """Every active override in `.env`: KEY → raw value string."""
    out: dict[str, str] = {}
    for ln in _env_lines():
        s = ln.strip()
        if s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


# --- Coercion + validation (via the pydantic field types) --------------------


def _adapter(name: str) -> TypeAdapter:
    return TypeAdapter(Settings.model_fields[name].annotation)


def default_of(name: str):
    return Settings.model_fields[name].default


def is_editable(name: str) -> bool:
    """Scalars are editable; list/complex dials are shown read-only."""
    return Settings.model_fields[name].annotation in (int, float, bool, str)


def coerce(name: str, value: str):
    """Coerce a form string to the field's Python value (raises on a bad type)."""
    return _adapter(name).validate_python(value)


def env_str(value) -> str:
    """Canonical `.env` string for a coerced value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def validate_value(name: str, value: str) -> str | None:
    """None if `value` is a valid value for the field, else the error message."""
    try:
        coerce(name, value)
        return None
    except Exception as exc:  # noqa: BLE001 — pydantic's message is the operator-facing one
        return str(exc).splitlines()[0]


# --- View model --------------------------------------------------------------


@dataclass
class DialRow:
    name: str
    key: str
    effective: str
    default: str
    file_value: str | None  # the active .env override, or None
    editable: bool
    kind: str  # int | float | bool | str | list
    warn: bool


def _kind(name: str) -> str:
    ann = Settings.model_fields[name].annotation
    return {int: "int", float: "float", bool: "bool", str: "str"}.get(ann, "list")


def group_rows(group: Group) -> list[DialRow]:
    overrides = env_overrides()
    rows: list[DialRow] = []
    for name in group.fields:
        key = env_key(name)
        rows.append(
            DialRow(
                name=name,
                key=key,
                effective=env_str(getattr(settings, name)),
                default=env_str(default_of(name)),
                file_value=overrides.get(key),
                editable=is_editable(name),
                kind=_kind(name),
                warn=name in _PRODUCTION_ON,
            )
        )
    return rows


def group_by_slug(slug: str) -> Group | None:
    return next((g for g in DIAL_GROUPS if g.slug == slug), None)


# --- Building a candidate .env from a group submission -----------------------


@dataclass
class Staged:
    changes: dict[str, str | None] = field(default_factory=dict)  # key -> value|None
    errors: list[str] = field(default_factory=list)


def stage_group_edit(group: Group, submitted: dict[str, str]) -> Staged:
    """Compute the .env changes for a group form: set/update, or remove on default.

    A field whose submitted value coerces to the DEFAULT drops its override (reset);
    a differing value sets/updates it. Type errors are collected, not written.
    """
    staged = Staged()
    overrides = env_overrides()
    for name in group.fields:
        if not is_editable(name):
            continue
        raw = submitted.get(name)
        if raw is None:
            continue
        # An empty numeric/bool input means "no value entered" → leave unchanged;
        # only a `str` dial accepts "" as a real value (e.g. the default emotion).
        if raw == "" and Settings.model_fields[name].annotation is not str:
            continue
        err = validate_value(name, raw)
        if err:
            staged.errors.append(f"{name}: {err}")
            continue
        coerced = coerce(name, raw)
        key = env_key(name)
        want = env_str(coerced)
        default = env_str(default_of(name))
        active = overrides.get(key)
        if want == default:
            if active is not None:  # setting to default removes the override
                staged.changes[key] = None
        elif active != want:
            staged.changes[key] = want
    return staged


def apply_changes(changes: dict[str, str | None]) -> str:
    """Return the candidate `.env` text with `changes` applied (comment-preserving)."""
    lines = _env_lines()
    for key, value in changes.items():
        idx = _active_index(lines, key)
        if value is None:
            if idx is not None:
                del lines[idx]
        elif idx is not None:
            lines[idx] = f"{key}={value}"
        else:
            lines.append(f"{key}={value}")
    text = "\n".join(lines)
    return text + "\n" if text and not text.endswith("\n") else text


def write(candidate: str) -> Path:
    """Back up `.env`, then atomically replace it with `candidate`."""
    backup = _ENV_PATH.with_suffix(_ENV_PATH.suffix + ".bak")
    if _ENV_PATH.exists():
        backup.write_text(_ENV_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = _ENV_PATH.with_suffix(_ENV_PATH.suffix + ".tmp")
    tmp.write_text(candidate, encoding="utf-8")
    os.replace(tmp, _ENV_PATH)
    log.info("dials_env_written", path=str(_ENV_PATH), bytes=len(candidate))
    return backup


def unified_diff(current: str, candidate: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            candidate.splitlines(keepends=True),
            fromfile=".env (current)",
            tofile=".env (candidate)",
        )
    )

"""E1.3 — the catalog editors' core: read / mutate / validate / write config YAMLs.

The four config catalogs (tracks, sponsors, pronunciation, voices) STAY the source
of truth (E1 principle #1): this edits the existing human-authored YAML in place and
runs the EXISTING seed/refresh path. Same discipline as the grid editor (E1.2):
comment-preserving **ruamel** round-trip, change-only field mutation (untouched rows
stay byte-identical), validation through the REAL consumer (the seeder's own
`load_manifest`), a unified diff before the write, an atomic write with a one-deep
`.bak`, and — for a seed-backed catalog — the existing `make seed-*` button (E1.1).

This module carries the shared machinery + the two seed-backed, id-row catalogs
(tracks, sponsors). The two live-reload registries (pronunciation, voices) plug into
the same `Catalog` shape.
"""

from __future__ import annotations

import io
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from ..config import settings
from ..logging_setup import get_logger
from ..world import seed_sponsors, seed_tracks

log = get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]

# One ruamel instance per (mapping, sequence, offset) indent spec — different
# catalogs indent their block sequences differently (tracks/sponsors put the dash
# at column 2 under `tracks:`; a top-level list like pronunciation puts it at 0),
# and matching the file's own indent is what keeps a no-op edit byte-identical.
_yaml_cache: dict[tuple[int, int, int], YAML] = {}


def _represent_none(representer, _data):
    """Emit Python None as an explicit `null` — the manifests write `null`, and
    ruamel's default (an empty value) would rewrite every such line on any dump."""
    return representer.represent_scalar("tag:yaml.org,2002:null", "null")


def _yaml_for(indent: tuple[int, int, int]) -> YAML:
    y = _yaml_cache.get(indent)
    if y is None:
        y = YAML()
        y.preserve_quotes = True
        y.width = 4096
        y.indent(mapping=indent[0], sequence=indent[1], offset=indent[2])
        y.representer.add_representer(type(None), _represent_none)
        _yaml_cache[indent] = y
    return y


# --- Field + Catalog descriptors ---------------------------------------------


@dataclass(frozen=True)
class Field:
    """One editable field of a catalog row."""

    name: str
    label: str
    kind: str = "text"  # text | int | float | list | textarea | date | quoted
    hint: str = ""
    prominent: bool = False  # rendered highlighted (e.g. the licence note)
    required: bool = False


@dataclass
class Validation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class Catalog:
    """A YAML catalog the panel edits: its file, shape, fields, seed path, validator."""

    slug: str  # url slug + display id
    title: str
    path_setting: str  # attribute on `settings` holding the file Path
    top_key: str  # the top-level list key (tracks: / sponsors:); "" for toplist/map
    key_field: str  # the identity field (id/name) or, for a map, the mapping key
    fields: tuple[Field, ...]
    validate: Callable[[str], Validation]
    # The YAML shape: "list" = doc[top_key] is a list of id-rows (tracks/sponsors);
    # "toplist" = the doc itself is a list of {key_field: …} entries (pronunciation);
    # "map" = the doc is {key: {field: …}} (voices — key_field names the map key).
    kind: str = "list"
    seed_action: str | None = None  # E1.1 action id (None = live-reload, no seed)
    live_reload: bool = False
    feature_tags: tuple[str, ...] = ()  # tags surfaced as checkboxes (featured/pinned)
    intro: str = ""
    indent: tuple[int, int, int] = (2, 4, 2)  # ruamel (mapping, sequence, offset)

    def path(self) -> Path:
        return getattr(settings, self.path_setting)


# --- ruamel helpers (shared with the grid editor's approach) -----------------


def _load_doc(cat: Catalog, text: str | None = None):
    return _yaml_for(cat.indent).load(text if text is not None else current_text(cat))


def _dump(cat: Catalog, doc) -> str:
    buf = io.StringIO()
    _yaml_for(cat.indent).dump(doc, buf)
    return buf.getvalue()


def current_text(cat: Catalog) -> str:
    return cat.path().read_text(encoding="utf-8")


def _scalar(v) -> str:
    return "" if v is None else str(v)


def _field_value(row, f: Field) -> str:
    """A field's current value as a form STRING (list fields joined by ', ')."""
    if f.kind == "list":
        return ", ".join(str(x) for x in (row.get(f.name) or []))
    return _scalar(row.get(f.name))


def _seq(doc, cat: Catalog) -> CommentedSeq:
    """The row sequence: doc[top_key] for a `list`, else the doc itself (`toplist`)."""
    if cat.kind == "toplist":
        return doc
    if cat.top_key not in doc or doc[cat.top_key] is None:
        doc[cat.top_key] = CommentedSeq()
    return doc[cat.top_key]


def _iter_entries(doc, cat: Catalog):
    """Yield (key, entry_map) for every entry, across all three shapes."""
    if cat.kind == "map":
        for k, v in doc.items():
            yield str(k), v
    else:
        for row in _seq(doc, cat):
            yield str(row.get(cat.key_field)), row


def _get_entry(doc, cat: Catalog, key: str):
    """The entry map for `key` (None if absent)."""
    if cat.kind == "map":
        return doc.get(key)
    for k, row in _iter_entries(doc, cat):
        if k == key:
            return row
    return None


def _find(rows: CommentedSeq, cat: Catalog, key: str):  # kept for the list callers
    for row in rows:
        if str(row.get(cat.key_field)) == key:
            return row
    return None


def unified_diff(current: str, candidate: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            candidate.splitlines(keepends=True),
            fromfile="current",
            tofile="candidate",
        )
    )


# --- Reading rows into forms -------------------------------------------------


def list_rows(cat: Catalog) -> list[dict]:
    """Every row as a display dict: its fields + (for tracks) playable state."""
    doc = _load_doc(cat)
    out: list[dict] = []
    for key, row in _iter_entries(doc, cat):
        d = {f.name: _field_value(row, f) for f in cat.fields}
        d["_key"] = key
        tags = [str(t) for t in (row.get("tags") or [])]
        d["_flags"] = [t for t in cat.feature_tags if t in tags]
        d["_playable"] = _playable(row)
        out.append(d)
    return out


def _playable(row) -> bool | None:
    """For a track row: does its audio_path file exist? None if no audio_path field."""
    ap = row.get("audio_path")
    if not ap:
        return None
    return (_REPO_ROOT / str(ap)).exists()


def row_form(cat: Catalog, key: str) -> dict | None:
    """The form values for one row (None if the key is unknown)."""
    doc = _load_doc(cat)
    row = _get_entry(doc, cat, key)
    if row is None:
        return None
    form = {f.name: _field_value(row, f) for f in cat.fields}
    tags = [str(t) for t in (row.get("tags") or [])]
    form["_flags"] = {t: (t in tags) for t in cat.feature_tags}
    return form


def blank_form(cat: Catalog) -> dict:
    form = {f.name: "" for f in cat.fields}
    form["_flags"] = dict.fromkeys(cat.feature_tags, False)
    return form


# --- Mutating (change-only, style-preserving) --------------------------------


def _tokens(value: str) -> list[str]:
    return [t for t in value.replace(",", " ").split() if t]


def _flow_seq(items: list[str]) -> CommentedSeq:
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def _coerce(field_: Field, value: str):
    """Turn a form string into the typed YAML value for a field (or None to drop)."""
    value = value.strip()
    if value == "":
        return None
    if field_.kind == "int":
        return int(value) if value.lstrip("-").isdigit() else value
    if field_.kind == "float":
        try:
            return float(value)
        except ValueError:
            return value
    if field_.kind == "date":
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value  # invalid → left as string so the validator rejects it
    if field_.kind == "quoted":
        return DoubleQuotedScalarString(value)
    return value


def _set_field(row, field_: Field, value: str) -> None:
    """Apply one field change-only; "" drops an optional key (required stays)."""
    if field_.kind == "list":
        current = [str(x) for x in (row.get(field_.name) or [])]
        items = _tokens(value)
        if current == items:
            return
        if not items:
            if not field_.required:
                row.pop(field_.name, None)
            else:
                row[field_.name] = _flow_seq(items)
            return
        row[field_.name] = _flow_seq(items)
        return

    new = _coerce(field_, value)
    cur = row.get(field_.name)
    if _same(cur, new):
        return
    if new is None:
        # Clearing a field REMOVES its key. For a required field this makes the
        # seeder's own parser raise (KeyError → "missing required field") — the
        # rejection comes from the real consumer, not a second validator here.
        row.pop(field_.name, None)
        return
    row[field_.name] = new


def _same(cur, new) -> bool:
    """Whether a current YAML value equals the coerced new value (fidelity check)."""
    if cur is None and new is None:
        return True
    if isinstance(cur, (date, datetime)) or isinstance(new, (date, datetime)):
        return str(cur) == str(new)
    return _scalar(cur) == _scalar(new)


def _apply_flags(row, cat: Catalog, flags: dict[str, bool]) -> None:
    """Add/remove the feature TAGS (featured/pinned) in the row's tag list."""
    if not cat.feature_tags:
        return
    tags = [str(t) for t in (row.get("tags") or [])]
    changed = False
    for tag in cat.feature_tags:
        want = flags.get(tag, False)
        if want and tag not in tags:
            tags.append(tag)
            changed = True
        elif not want and tag in tags:
            tags.remove(tag)
            changed = True
    if changed:
        if tags:
            row["tags"] = _flow_seq(tags)
        else:
            row.pop("tags", None)


def apply_row(cat: Catalog, key: str, values: dict, *, adding: bool = False) -> str:
    """Return candidate text with `key`'s changed fields applied (add or edit)."""
    doc = _load_doc(cat)
    row = _get_entry(doc, cat, key)

    if adding:
        if row is not None:
            raise ValueError(f"{cat.key_field} {key!r} already exists")
        row = CommentedMap()
        if cat.kind == "map":
            doc[key] = row  # the mapping key IS the identity; fields fill the submap
        else:
            row[cat.key_field] = values.get(cat.key_field, key).strip()
            _seq(doc, cat).append(row)
    elif row is None:
        raise KeyError(key)

    for f in cat.fields:
        if f.name == cat.key_field and cat.kind != "map" and not adding:
            continue  # the identity key isn't renamed here (map key isn't a field)
        if f.name == cat.key_field and cat.kind == "map":
            continue  # voices: the field set never includes the mapping key
        _set_field(row, f, values.get(f.name, ""))
    _apply_flags(row, cat, values.get("_flags", {}))
    return _dump(cat, doc)


def delete_row(cat: Catalog, key: str) -> str:
    """Return candidate text with `key`'s entry removed."""
    doc = _load_doc(cat)
    if cat.kind == "map":
        if key not in doc:
            raise KeyError(key)
        del doc[key]
        return _dump(cat, doc)
    rows = _seq(doc, cat)
    row = _find(rows, cat, key)
    if row is None:
        raise KeyError(key)
    rows.remove(row)
    return _dump(cat, doc)


# --- Writing (atomic + one-deep backup) --------------------------------------


def write(cat: Catalog, candidate: str) -> Path:
    """Re-validate, back up, then atomically replace the catalog file."""
    v = cat.validate(candidate)
    if not v.ok:
        raise ValueError("; ".join(v.errors))
    path = cat.path()
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(candidate, encoding="utf-8")
    os.replace(tmp, path)
    log.info("catalog_written", catalog=cat.slug, path=str(path), bytes=len(candidate))
    return backup


# --- Per-catalog validators (through the REAL seeder parsers) -----------------


def _validate_via_manifest(loader, label: str):
    """Build a validator that writes the candidate to a temp file and loads it via
    the seeder's own `load_manifest` (the SAME code the seed button runs)."""

    def _validate(candidate: str) -> Validation:
        v = Validation()
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(candidate)
            tmp_path = Path(tmp.name)
        try:
            rows = loader(tmp_path)
        except Exception as exc:  # noqa: BLE001 — surface the real parser error
            v.errors.append(f"{label}: {exc}")
            return v
        finally:
            tmp_path.unlink(missing_ok=True)
        ids = [r.id for r in rows]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            v.errors.append(f"duplicate id(s): {', '.join(sorted(dupes))}")
        return v

    return _validate


def _validate_pronunciation(candidate: str) -> Validation:
    """Structural validation mirroring the lexicon's rules (name + respell required).

    The lexicon (the consumer) is lenient — it silently skips a bad entry — so there
    is no hard parser to lean on; the editor enforces the entry contract itself.
    """
    import yaml

    v = Validation()
    try:
        raw = yaml.safe_load(candidate)
    except yaml.YAMLError as exc:
        v.errors.append(f"YAML syntax error: {exc}")
        return v
    raw = raw or []
    if not isinstance(raw, list):
        v.errors.append("pronunciation must be a top-level list of entries")
        return v
    seen: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            v.errors.append(f"entry {i}: not a mapping")
            continue
        name = str(item.get("name", "")).strip()
        respell = str(item.get("respell", "")).strip()
        if not name:
            v.errors.append(f"entry {i}: missing name")
        if not respell:
            v.errors.append(f"entry {name or i}: missing respell (required)")
        if name and name in seen:
            v.errors.append(f"duplicate name {name!r}")
        seen.add(name)
    return v


def _validate_voices(candidate: str) -> Validation:
    """Validate through the REAL tts registry loader (temp file + repointed setting).

    Hard errors: the loader raising (missing/empty), or an entry missing one of the
    three engine mappings (the file's stated invariant — a render on an unmapped
    engine fails loud). Warning: a cast id in the DB whose logical voice has no entry
    (seeding pre-validates this, so it is a heads-up, not a block)."""
    import tempfile

    from ..providers import tts
    from ..world import store

    v = Validation()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(candidate)
        tmp_path = Path(tmp.name)
    old = settings.tts_voices_path
    try:
        settings.tts_voices_path = tmp_path
        registry = tts._voice_registry()  # raises on missing/empty (the real loader)
    except Exception as exc:  # noqa: BLE001 — surface the loader's real error
        v.errors.append(f"voice registry: {exc}")
        return v
    finally:
        settings.tts_voices_path = old
        tmp_path.unlink(missing_ok=True)

    for voice, engines in registry.items():
        for eng in ("kokoro", "elevenlabs", "say"):
            if not str(engines.get(eng) or "").strip():
                v.errors.append(f"voice {voice!r}: missing {eng} mapping")
    try:
        with store.connect() as conn:
            for m in store.all_cast(conn):
                if m.logical_voice and m.logical_voice not in registry:
                    v.warnings.append(
                        f"cast {m.id!r} uses voice {m.logical_voice!r} with no entry "
                        f"(seeding pre-validates this)"
                    )
    except Exception as exc:  # noqa: BLE001 — DB down → skip the cast cross-check
        log.warning("voices_cast_crosscheck_skipped", error=str(exc))
    return v


# --- The catalog registry ----------------------------------------------------


_TRACKS = Catalog(
    slug="tracks",
    title="Tracks",
    path_setting="tracks_manifest_path",
    top_key="tracks",
    key_field="id",
    seed_action="seed-tracks",
    feature_tags=("featured", "pinned"),
    intro="The curated music catalogue. A row is PLAYABLE only once its audio_path "
    "file exists in assets/music/. Save → seed with the button to load it.",
    fields=(
        Field("id", "id", required=True, hint="stable slug (seed key)"),
        Field("title", "Title", kind="quoted", required=True),
        Field("artist", "Artist", kind="quoted", required=True),
        Field("mood", "Mood", kind="quoted", required=True, hint="e.g. melancholy"),
        Field(
            "audio_path",
            "Audio path",
            required=True,
            hint="assets/music/<file>.mp3 — the row is unplayable until it exists",
        ),
        Field("album", "Album", kind="quoted"),
        Field("era", "Era", kind="quoted"),
        Field("in_world_year", "In-world year", kind="int"),
        Field(
            "duration_sec",
            "Duration (sec)",
            kind="float",
            hint="blank = probed from the file at seed time",
        ),
        Field("tags", "Tags", kind="list", hint="comma/space separated"),
        Field("story_blurb", "Story blurb", kind="textarea"),
        Field(
            "licence_note",
            "Licence note",
            kind="textarea",
            prominent=True,
            hint="blank = the manifest's licence_default. The clearance call is human.",
        ),
    ),
    validate=_validate_via_manifest(seed_tracks.load_manifest, "tracks manifest"),
)

_SPONSORS = Catalog(
    slug="sponsors",
    title="Sponsors",
    path_setting="sponsors_manifest_path",
    top_key="sponsors",
    key_field="id",
    seed_action="seed-sponsors",
    intro="Real supporter acknowledgements. The on-air lead-in is ALWAYS "
    '"Powered by …", never "Sponsored by" (binding). Ships empty until CM.',
    fields=(
        Field("id", "id", required=True, hint="stable slug (seed key)"),
        Field(
            "name",
            "Name",
            kind="quoted",
            required=True,
            hint='spoken: "… is powered by {name}."',
        ),
        Field(
            "powered_by_text",
            "Powered-by text",
            kind="textarea",
            hint="short blurb spoken after the lead-in (blank = lead-in only)",
        ),
        Field(
            "audio_path",
            "Audio path",
            hint="optional clip under assets/sponsors/ (missing = voiced read)",
        ),
        Field(
            "run_start",
            "Run start",
            kind="date",
            hint="YYYY-MM-DD (blank = already running)",
        ),
        Field(
            "run_end",
            "Run end",
            kind="date",
            hint="YYYY-MM-DD, half-open (blank = open-ended)",
        ),
        Field("weight", "Weight", kind="int", hint="rotation share (default 1)"),
        Field("tags", "Tags", kind="list"),
    ),
    validate=_validate_via_manifest(seed_sponsors.load_manifest, "sponsors manifest"),
)

_PRONUNCIATION = Catalog(
    slug="pronunciation",
    title="Pronunciation",
    path_setting="tts_lexicon_path",
    top_key="",
    key_field="name",
    kind="toplist",
    indent=(2, 2, 0),  # a top-level list: the dash sits at column 0
    live_reload=True,
    intro="How the station SAYS the world's invented names. Live-reloaded — no "
    "seed. Use “test it” to hear a name on the current TTS engine.",
    fields=(
        Field(
            "name",
            "Name",
            required=True,
            hint="the spelling as it appears in scripts (whole-word, case-sensitive)",
        ),
        Field(
            "respell",
            "Respell",
            required=True,
            hint='a phonetic respelling any engine can read ("Zhay", "LOO-men")',
        ),
        Field(
            "phonemes",
            "Phonemes",
            kind="quoted",
            hint='optional misaki/IPA string for Kokoro ("ʒeɪ") — blank = respell',
        ),
    ),
    validate=_validate_pronunciation,
)

_VOICES = Catalog(
    slug="voices",
    title="Voices",
    path_setting="tts_voices_path",
    top_key="",
    key_field="voice",  # the MAP key (a logical voice name) — not a field in the submap
    kind="map",
    indent=(2, 2, 0),
    live_reload=True,
    intro="The voice registry: a logical voice → a vendor preset per engine. Every "
    "entry must map all three engines (a missing one fails loud at render).",
    fields=(
        Field(
            "kokoro",
            "Kokoro",
            required=True,
            hint="Kokoro-82M preset id (e.g. bm_george)",
        ),
        Field("elevenlabs", "ElevenLabs", required=True, hint="vendor voice id"),
        Field("say", "say (macOS)", required=True, hint="a `say -v '?'` voice name"),
    ),
    validate=_validate_voices,
)


CATALOGS: dict[str, Catalog] = {
    c.slug: c for c in (_TRACKS, _SPONSORS, _PRONUNCIATION, _VOICES)
}


def catalog(slug: str) -> Catalog | None:
    return CATALOGS.get(slug)

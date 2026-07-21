"""E1.4 — the cast manager's core: edit / add / retire a DJ in 90-cast.md.

The cast bible (`docs/canon/90-cast.md`) STAYS the source of truth (E1 principle
#1): this edits the markdown cards in place and runs the existing `make seed-canon`
path. There is no markdown serializer, so — like the grid/catalog editors — we edit
SURGICALLY: each card's `- **Field:** …` bullets are updated line-by-line, and a
bullet is only rewritten when its value actually changes, so a panel edit diffs
exactly like a hand edit (an untouched card stays byte-identical).

Validation runs the candidate through the REAL parser (`world.canon_source`) and
checks each card's logical voice against the TTS registry (`providers.tts` —
what `make seed-canon` itself pre-validates). Retiring a host also checks the grid
(`world.programming`) and warns if it still schedules them.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger
from ..providers import tts
from ..world import canon_source, programming, store

log = get_logger(__name__)

# The cast cornerstone file inside the canon folder (D1). The `## Cast` section's
# `### ` cards are the DJs; the seed projects each to a `cast` row.
CAST_FILENAME = "90-cast.md"

# The editable card bullets, in canonical order — (form field, markdown label, kind).
# `voice`/`based`/`tags` feed the DB (structural); the rest is card_text prose the
# writers' room reads. `Sample lines` is a multi-line sub-bullet block (handled apart).
_BULLETS: tuple[tuple[str, str, str], ...] = (
    ("logical_voice", "Logical voice", "voice"),
    ("based", "Based", "based"),
    ("tags", "Tags", "list"),
    ("role", "Role", "text"),
    ("background", "Background", "textarea"),
    ("personality", "Personality", "textarea"),
    ("humour", "Humour", "textarea"),
    ("voice_tts", "Voice (for TTS)", "text"),
    ("verbal_tics", "Verbal tics", "textarea"),
    ("never", "Never", "textarea"),
)
_SAMPLE_LABEL = "Sample lines"
_BASED_VALUES = ("station", "field")


@dataclass
class Validation:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


# --- Reading -----------------------------------------------------------------


def cast_path() -> Path:
    return settings.canon_dir / CAST_FILENAME


def current_text() -> str:
    return cast_path().read_text(encoding="utf-8")


@dataclass
class _CardSpan:
    id: str
    name: str
    heading: str
    start: int  # index of the `### ` line
    end: int  # exclusive; the next `### `/`## ` line or EOF


def _cards(lines: list[str]) -> list[_CardSpan]:
    """Locate every `### ` card block (ends at the next `###`/`##` or EOF)."""
    starts = [i for i, ln in enumerate(lines) if re.match(r"^###\s+", ln)]
    spans: list[_CardSpan] = []
    for start in starts:
        end = len(lines)
        for j in range(start + 1, len(lines)):
            if re.match(r"^###\s+", lines[j]) or re.match(r"^##\s+", lines[j]):
                end = j
                break
        heading = re.sub(r"^###\s+", "", lines[start]).strip()
        name = re.split(r"\s+[—-]\s+", heading, maxsplit=1)[0].strip()
        spans.append(_CardSpan(_slug(name), name, heading, start, end))
    return spans


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _find_card(lines: list[str], cid: str) -> _CardSpan | None:
    for span in _cards(lines):
        if span.id == cid:
            return span
    return None


_BULLET_RE = r"^(\s*-\s*\*\*{label}:\*\*)\s*(.*)$"


def _bullet_line(
    lines: list[str], span: _CardSpan, label: str
) -> tuple[int, str] | None:
    """(line index, raw value) of a card's `- **label:** value` bullet, or None."""
    pat = re.compile(_BULLET_RE.format(label=re.escape(label)), re.IGNORECASE)
    for i in range(span.start + 1, span.end):
        m = pat.match(lines[i])
        if m:
            return i, m.group(2).strip()
    return None


def _sample_block(
    lines: list[str], span: _CardSpan
) -> tuple[int, int, list[str]] | None:
    """The `- **Sample lines:**` bullet + its indented sub-bullets.

    Returns (bullet index, end index exclusive, [sample texts]) or None.
    """
    pat = re.compile(_BULLET_RE.format(label=re.escape(_SAMPLE_LABEL)), re.IGNORECASE)
    for i in range(span.start + 1, span.end):
        if pat.match(lines[i]):
            samples: list[str] = []
            j = i + 1
            while j < span.end and re.match(r"^\s+-\s+", lines[j]):
                samples.append(re.sub(r"^\s+-\s+", "", lines[j]).strip().strip('"'))
                j += 1
            return i, j, samples
    return None


def _clean(raw: str, kind: str) -> str:
    """The comparable/displayable value of a bullet's raw text, by kind."""
    if kind == "voice" or kind == "based":
        return raw.strip().strip("`").strip()
    return raw.strip()


def card_form(cid: str) -> dict | None:
    """The form values for one card (None if the id is unknown)."""
    lines = current_text().splitlines()
    span = _find_card(lines, cid)
    if span is None:
        return None
    form: dict = {"id": cid, "name": span.name, "heading": span.heading}
    for fname, label, kind in _BULLETS:
        found = _bullet_line(lines, span, label)
        form[fname] = _clean(found[1], kind) if found else ""
    block = _sample_block(lines, span)
    form["sample_lines"] = "\n".join(block[2]) if block else ""
    return form


def list_cards() -> list[dict]:
    """Every card: id/name/voice/based/tags + whether it's currently seeded (in DB)."""
    lines = current_text().splitlines()
    seeded = _seeded_ids()
    out: list[dict] = []
    for span in _cards(lines):
        voice = _bullet_line(lines, span, "Logical voice")
        based = _bullet_line(lines, span, "Based")
        tags = _bullet_line(lines, span, "Tags")
        out.append(
            {
                "id": span.id,
                "name": span.name,
                "voice": _clean(voice[1], "voice") if voice else "",
                "based": _clean(based[1], "based") if based else "station",
                "tags": tags[1] if tags else "",
                "in_db": span.id in seeded if seeded is not None else None,
            }
        )
    return out


def _seeded_ids() -> set[str] | None:
    try:
        with store.connect() as conn:
            return {m.id for m in store.all_cast(conn)}
    except Exception as exc:  # noqa: BLE001 — DB down → the "seeded?" column is unknown
        log.warning("cast_edit_db_unavailable", error=str(exc))
        return None


# --- Mutating (change-only, surgical) ----------------------------------------


def _format_value(value: str, kind: str) -> str:
    if kind in ("voice", "based"):
        return f"`{value}`"
    return value


def _set_bullet(
    lines: list[str], span: _CardSpan, label: str, kind: str, new_clean: str
) -> None:
    """Update (or insert/remove) a single-line bullet, change-only."""
    found = _bullet_line(lines, span, label)
    cur_clean = _clean(found[1], kind) if found else ""
    if new_clean == cur_clean:
        return  # unchanged → leave the raw line untouched (fidelity)
    if found is None:
        if not new_clean:
            return
        # insert before the Sample-lines block if present, else at the card's end
        block = _sample_block(lines, span)
        at = block[0] if block else span.end
        lines.insert(at, f"- **{label}:** {_format_value(new_clean, kind)}")
        return
    idx, _raw = found
    prefix = re.match(
        _BULLET_RE.format(label=re.escape(label)), lines[idx], re.IGNORECASE
    ).group(1)
    if not new_clean and kind not in ("voice",):  # blanking an optional prose bullet
        del lines[idx]
        return
    lines[idx] = f"{prefix} {_format_value(new_clean, kind)}"


def _set_samples(lines: list[str], span: _CardSpan, text: str) -> None:
    """Replace the Sample-lines sub-bullets, change-only."""
    new = [s.strip() for s in text.splitlines() if s.strip()]
    block = _sample_block(lines, span)
    cur = block[2] if block else []
    if new == cur:
        return
    rendered = [f'  - "{s.strip(chr(34))}"' for s in new]
    if block is not None:
        bullet_i, end_i, _ = block
        lines[bullet_i + 1 : end_i] = rendered  # keep the bullet, swap sub-bullets
    elif new:
        at = span.end
        lines.insert(at, "- **Sample lines:**")
        lines[at + 1 : at + 1] = rendered


def apply_card_edit(cid: str, values: dict) -> str:
    """Return candidate text with card `cid`'s changed bullets applied."""
    lines = current_text().splitlines()
    span = _find_card(lines, cid)
    if span is None:
        raise KeyError(cid)
    # Apply from the BOTTOM up would shift indices; instead re-locate the span after
    # each edit (cheap — the file is small) so inserts/deletes stay consistent.
    for fname, label, kind in _BULLETS:
        span = _find_card(lines, cid)
        _set_bullet(lines, span, label, kind, values.get(fname, "").strip())
    span = _find_card(lines, cid)
    _set_samples(lines, span, values.get("sample_lines", ""))
    return "\n".join(lines) + ("\n" if current_text().endswith("\n") else "")


def _card_template(values: dict) -> list[str]:
    """A fresh card block from the add form (canonical bullet order)."""
    name = values.get("name", "").strip()
    role = values.get("role", "").strip()
    heading = f"### {name}" + (f" — {role}" if role else "")
    out = [heading]
    for fname, label, kind in _BULLETS:
        v = values.get(fname, "").strip()
        if not v and fname not in ("logical_voice", "based"):
            continue
        out.append(f"- **{label}:** {_format_value(v or 'station', kind)}")
    samples = [
        s.strip() for s in values.get("sample_lines", "").splitlines() if s.strip()
    ]
    if samples:
        out.append("- **Sample lines:**")
        out += [f'  - "{s.strip(chr(34))}"' for s in samples]
    return out


def add_card(values: dict) -> str:
    """Return candidate text with a new card appended to the cast file."""
    name = values.get("name", "").strip()
    if not name:
        raise ValueError("a name is required")
    lines = current_text().splitlines()
    if _find_card(lines, _slug(name)) is not None:
        raise ValueError(f"a DJ with id {_slug(name)!r} already exists")
    block = ["", *_card_template(values)]
    lines.extend(block)
    return "\n".join(lines) + "\n"


def remove_card(cid: str) -> str:
    """Return candidate text with card `cid` removed (trailing blank line too)."""
    lines = current_text().splitlines()
    span = _find_card(lines, cid)
    if span is None:
        raise KeyError(cid)
    start = span.start
    while start > 0 and lines[start - 1].strip() == "":
        start -= 1  # eat the blank line(s) before the card
    del lines[start : span.end]
    return "\n".join(lines) + "\n"


# --- Validation (real parser + voice registry + grid) ------------------------


def grid_uses(cid: str) -> list[str]:
    """Program names whose hosts include this cast id (for the retire warning)."""
    return [p.name for p in programming.all_programs().values() if cid in p.hosts]


def validate(candidate: str) -> Validation:
    """Parse the candidate with the REAL canon parser + check the voice registry."""
    v = Validation()
    import tempfile

    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(candidate)
        tmp_path = Path(tmp.name)
    try:
        _facts, cast, _events = canon_source.load(tmp_path)
    except Exception as exc:  # noqa: BLE001 — surface the parser's real error
        v.errors.append(str(exc))
        return v
    finally:
        tmp_path.unlink(missing_ok=True)

    try:
        registry = tts.known_voices()
    except Exception as exc:  # noqa: BLE001 — registry unreadable → can't verify voices
        registry = None
        v.warnings.append(f"voice registry unreadable ({exc}); voices not checked")
    ids = [m.id for m in cast]
    for dup in {i for i in ids if ids.count(i) > 1}:
        v.errors.append(f"duplicate cast id {dup!r}")
    if registry is not None:
        for m in cast:
            if m.logical_voice not in registry:
                v.errors.append(
                    f"{m.name}: logical voice {m.logical_voice!r} has no entry in "
                    f"config/voices.yaml (seeding would fail)"
                )
    return v


# --- Writing (atomic + one-deep backup) --------------------------------------


def write(candidate: str) -> Path:
    """Re-validate, back up, then atomically replace the cast file."""
    v = validate(candidate)
    if not v.ok:
        raise ValueError("; ".join(v.errors))
    path = cast_path()
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(candidate, encoding="utf-8")
    os.replace(tmp, path)
    log.info("cast_written", path=str(path), bytes=len(candidate))
    return backup


def unified_diff(current: str, candidate: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            candidate.splitlines(keepends=True),
            fromfile="90-cast.md (current)",
            tofile="90-cast.md (candidate)",
        )
    )

"""Parse the world bible (markdown) into structured world records for the seed.

The bible is the human-editable source of truth. Phase A/B kept it in a single
`docs/CANON.md`; Phase D (D1) grows it into a `docs/canon/` **folder** of
cornerstone files (`docs/canon/README.md` is the authoring contract). This module
reads the well-marked sections into the row shapes `store.py` owns, so `seed.py`
can load them into the DB. Parsing — not a second machine-readable copy — keeps ONE
source a person edits by hand.

Two read paths share the same per-section parsers:

* `load(path)` / `load_series_bible(path)` — a single file (back-compat + tests).
* `load_folder(dir)` / `load_series_bible_folder(dir)` — the whole `docs/canon/`
  folder, merged in numeric-prefix order with globally-unique fact ids (D1).

It reads three structured sections per file (every other `## ` section is series
bible — narrative prose picked up as cached context in B3, not projected to rows):

* `## Canon facts` — a numbered list; each item becomes a `CanonFact`.
* `## Cast` — `### Name — role` subsections; each becomes a `CastMember`. The
  whole subsection is kept as `card_text` (so the writer later gets the rich
  card); `logical voice` and `tags` are also pulled from their bullet lines.
* `## Events` — `### Title` subsections; each becomes an `Event` from its
  `in-world datetime`, `status`, `tags`, and `body` bullet lines.

The bullet-field convention is `- **Field:** value` (case-insensitive field).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .store import CanonFact, CastMember, Event


def load(canon_path: Path) -> tuple[list[CanonFact], list[CastMember], list[Event]]:
    """Read a single bible file and return (canon facts, cast, events).

    Back-compat / test path: fact ids stay the legacy `canon-1, canon-2, …`. Folder
    loading (`load_folder`) namespaces ids by file so they're unique across files.
    """
    text = canon_path.read_text()
    sections = _split_sections(text)
    facts = _parse_canon_facts(sections.get("canon facts", ""), stem=None)
    cast = _parse_cast(sections.get("cast", ""))
    events = _parse_events(sections.get("events", ""))
    return facts, cast, events


def load_folder(
    canon_dir: Path,
) -> tuple[list[CanonFact], list[CastMember], list[Event]]:
    """Read every `*.md` in `canon_dir` (the bible folder) and merge into rows.

    Files load in numeric-prefix order (`_sorted_canon_files`). Each file is parsed
    with the same per-section parsers as `load`, but fact ids are namespaced by the
    file stem (`canon-<stem>-<n>`) so they're globally unique across files. Cast and
    event ids stay name-slugs; a slug — or a file stem — that repeats across files is
    a collision we **fail loud** on (the same stance as a missing required field),
    rather than silently merging two personas/timelines into one id.
    """
    facts: list[CanonFact] = []
    cast: list[CastMember] = []
    events: list[Event] = []
    seen_stems: dict[str, str] = {}  # stem -> file it first appeared in
    seen_cast: dict[str, str] = {}  # cast id -> file
    seen_events: dict[str, str] = {}  # event id -> file

    for path in _sorted_canon_files(canon_dir):
        stem = _file_stem(path)
        if stem in seen_stems:
            raise ValueError(
                f"duplicate canon file stem {stem!r}: {path.name} collides with "
                f"{seen_stems[stem]} (stems drive fact ids and must be unique)"
            )
        seen_stems[stem] = path.name

        sections = _split_sections(path.read_text())
        facts.extend(_parse_canon_facts(sections.get("canon facts", ""), stem=stem))
        for member in _parse_cast(sections.get("cast", "")):
            _guard_unique(seen_cast, member.id, path.name, "cast")
            cast.append(member)
        for event in _parse_events(sections.get("events", "")):
            _guard_unique(seen_events, event.id, path.name, "event")
            events.append(event)

    return facts, cast, events


def _guard_unique(seen: dict[str, str], id_: str, file_name: str, kind: str) -> None:
    """Record `id_` for `kind`; raise if it already came from another file."""
    if id_ in seen:
        raise ValueError(
            f"duplicate {kind} id {id_!r}: {file_name} collides with {seen[id_]}"
        )
    seen[id_] = file_name


# --- Folder file discovery --------------------------------------------------


def _sorted_canon_files(canon_dir: Path) -> list[Path]:
    """The bible's `*.md` files in numeric-prefix order (README.md excluded).

    Sorted by the leading integer prefix (`2 < 20 < 100`, NOT string order), so a
    wide prefix never sorts to the wrong place; unprefixed files sort last by name.
    `README.md` is the authoring guide, not world content, so it is skipped.
    """
    files = [p for p in canon_dir.glob("*.md") if p.name.lower() != "readme.md"]
    return sorted(files, key=_file_sort_key)


def _file_sort_key(path: Path) -> tuple[int, str]:
    m = re.match(r"^(\d+)", path.name)
    num = int(m.group(1)) if m else 1_000_000  # unprefixed files sort last
    return (num, path.name)


def _file_stem(path: Path) -> str:
    """`10-history.md` -> `history`; `100-alien-races.md` -> `alien-races`.

    Strips the leading numeric ordering prefix and the extension, lowercased, so a
    fact id (`canon-<stem>-<n>`) derives stably from the filename. A file with no
    numeric prefix (e.g. `CANON.md`) keeps its bare name (`canon`).
    """
    stripped = re.sub(r"^\d+[-_]?", "", path.stem).strip("-_").lower()
    return stripped or path.stem.lower()


# The three `## ` sections that ARE projected into structured rows. Everything
# else is "series bible" — standing narrative prose that forms the cached stable
# core in context.assemble (B3). Defining the bible as "not structured" (rather
# than an allow-list of headings) means new cornerstone prose is picked up
# automatically, with no registration step (D1).
_STRUCTURED_HEADINGS = ("canon facts", "cast", "events")


def load_series_bible(canon_path: Path) -> str:
    """Return the standing narrative prose (the 'series bible') from one file.

    Every `## ` section that isn't one of the structured three (canon facts / cast
    / events) is series bible — the stable, slow-changing world description that is
    *not* seeded as rows. `context.assemble` (B3) passes this as the cached stable
    core, so reading it here keeps the bible the single human-editable source.
    Original `## ` headings are preserved so the cached text reads naturally.
    """
    return _bible_prose(canon_path.read_text())


def load_series_bible_folder(canon_dir: Path) -> str:
    """The series bible concatenated across the whole `docs/canon/` folder.

    Same rule as `load_series_bible`, applied file-by-file in numeric-prefix order:
    every non-structured `## ` section from every cornerstone file, joined so the
    cached core reads top-to-bottom the way the files are numbered.
    """
    parts = [_bible_prose(p.read_text()) for p in _sorted_canon_files(canon_dir)]
    return "\n\n".join(p for p in parts if p).strip()


def _bible_prose(text: str) -> str:
    """The non-structured `## ` sections of one document, headings preserved."""
    out: list[str] = []
    keep = False
    for line in text.splitlines():
        m = re.match(r"^##\s+(?!#)(.+)$", line)  # H2 only
        if m:
            keep = _normalize_heading(m.group(1)) not in _STRUCTURED_HEADINGS
        if keep:
            out.append(line)
    return "\n".join(out).strip()


# --- Section splitting ------------------------------------------------------


def _split_sections(text: str) -> dict[str, str]:
    """Split the document on `## ` headings into {normalized-heading: body}.

    The heading key is lowercased and truncated at the first ` — `/` -`/`(` so
    "## Canon facts (keep small…)" and "## Cast — the DJs" key as "canon facts"
    and "cast".
    """
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(?!#)(.+)$", line)  # H2 only, not H3+
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = _normalize_heading(m.group(1))
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _normalize_heading(heading: str) -> str:
    """ "Canon facts (keep small…)" / "Cast — the DJs" -> "canon facts" / "cast"."""
    head = re.split(r"\s+[—-]\s+|\s*\(", heading, maxsplit=1)[0]
    return head.strip().lower()


def _subsections(body: str) -> list[tuple[str, str]]:
    """Split a section body on `### ` headings into [(heading, sub-body), …]."""
    out: list[tuple[str, str]] = []
    heading: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            if heading is not None:
                out.append((heading, "\n".join(buf).strip()))
            heading = m.group(1).strip()
            buf = []
        elif heading is not None:
            buf.append(line)
    if heading is not None:
        out.append((heading, "\n".join(buf).strip()))
    return out


# --- Field helpers ----------------------------------------------------------


def _field(body: str, name: str) -> str | None:
    """Value of a `- **Name:** value` bullet (case-insensitive), or None."""
    m = re.search(
        rf"^\s*-\s*\*\*{re.escape(name)}:\*\*\s*(.+)$",
        body,
        re.IGNORECASE | re.MULTILINE,
    )
    return m.group(1).strip() if m else None


def _tags(value: str | None) -> list[str]:
    """ "festival, lights, music" -> ["festival", "lights", "music"]."""
    if not value:
        return []
    return [t.strip().strip("`") for t in value.split(",") if t.strip()]


def _slug(name: str) -> str:
    """ "Lumen Festival" -> "lumen-festival"; a stable id for re-seed idempotency."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _name_from_heading(heading: str) -> str:
    """ "Vell — the night shift" -> "Vell"; "Lumen Festival" -> "Lumen Festival"."""
    return re.split(r"\s+[—-]\s+", heading, maxsplit=1)[0].strip()


# --- Per-section parsers ----------------------------------------------------


def _parse_canon_facts(body: str, *, stem: str | None) -> list[CanonFact]:
    """Parse the numbered list into CanonFacts.

    Ids are `canon-<n>` when `stem` is None (single-file back-compat) or
    `canon-<stem>-<n>` for folder loading, where `<n>` is the fact's position
    within this file's list — so ids are globally unique and stable across
    re-seeds (D1). Multi-line wrapped items join into one fact; an optional
    `- **Tags:** a, b` child bullet is pulled into the fact's tags (else `[]`,
    populated later in D2).
    """
    facts: list[CanonFact] = []
    current: list[str] | None = None
    for line in body.splitlines():
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if current is not None:
                facts.append(_make_fact(stem, len(facts) + 1, current))
            current = [m.group(1)]
        elif current is not None and line.strip():
            current.append(line.strip())  # continuation: wrapped prose or field bullet
        elif current is not None:
            facts.append(_make_fact(stem, len(facts) + 1, current))
            current = None
    if current is not None:
        facts.append(_make_fact(stem, len(facts) + 1, current))
    return facts


# A fact's optional tag affordance: a `- **Tags:** a, b` child bullet (D1.0).
_FACT_TAGS_BULLET = re.compile(r"^\s*-\s*\*\*tags:\*\*", re.IGNORECASE)


def _make_fact(stem: str | None, n: int, lines: list[str]) -> CanonFact:
    fid = f"canon-{n}" if stem is None else f"canon-{stem}-{n}"
    block = "\n".join(lines)
    tags = _tags(_field(block, "tags"))
    # The tags bullet is consumed as tags, not folded into the prose text.
    prose = [ln for ln in lines if not _FACT_TAGS_BULLET.match(ln)]
    # Drop markdown bold markers so the stored fact is clean prose for the prompt.
    text = re.sub(r"\*\*", "", " ".join(prose)).strip()
    return CanonFact(id=fid, text=text, tags=tags)


def _parse_cast(body: str) -> list[CastMember]:
    """Parse `### Name — role` subsections into CastMembers."""
    members: list[CastMember] = []
    for heading, sub in _subsections(body):
        name = _name_from_heading(heading)
        voice = _field(sub, "logical voice")
        if not voice:
            raise ValueError(f"cast member {name!r} is missing a 'Logical voice' field")
        members.append(
            CastMember(
                id=_slug(name),
                name=name,
                card_text=sub.strip(),  # the whole card, for the writer later
                logical_voice=voice.strip().strip("`"),
                tags=_tags(_field(sub, "tags")),
            )
        )
    return members


def _parse_events(body: str) -> list[Event]:
    """Parse `### Title` subsections into Events."""
    events: list[Event] = []
    for heading, sub in _subsections(body):
        title = _name_from_heading(heading)
        when = _field(sub, "in-world datetime")
        if not when:
            raise ValueError(f"event {title!r} is missing an 'In-world datetime' field")
        status = _field(sub, "status") or "upcoming"
        body_text = _field(sub, "body") or ""
        events.append(
            Event(
                id=_slug(title),
                title=title,
                body=body_text,
                in_world_datetime=datetime.fromisoformat(when.strip()),
                status=status.strip().lower(),
                tags=_tags(_field(sub, "tags")),
            )
        )
    return events

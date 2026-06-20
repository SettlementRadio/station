"""Parse `docs/CANON.md` into structured world records for the seed.

`CANON.md` is the human-editable source of truth (CLAUDE.md: "the canon lives in
docs/CANON.md"); this module reads its well-marked sections into the row shapes
`store.py` owns, so `seed.py` can load them into the DB. Parsing — not a second
machine-readable copy — keeps ONE source a person edits by hand.

It reads three sections (other prose sections, e.g. the series bible, are ignored
here and picked up as cached context in B3):

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
    """Read `canon_path` and return (canon facts, cast, events)."""
    text = canon_path.read_text()
    sections = _split_sections(text)
    facts = _parse_canon_facts(sections.get("canon facts", ""))
    cast = _parse_cast(sections.get("cast", ""))
    events = _parse_events(sections.get("events", ""))
    return facts, cast, events


# The standing narrative sections that make up the "series bible": stable world
# description that is NOT projected into structured rows (unlike canon facts /
# cast / events). These form the cached stable core in context.assemble (B3).
_BIBLE_HEADINGS = ("the station", "the time concept")


def load_series_bible(canon_path: Path) -> str:
    """Return the standing narrative prose (the 'series bible') from CANON.md.

    These are the stable, slow-changing world-description sections (the station's
    identity and the time concept) — the parts that are *not* seeded as rows.
    `context.assemble` (B3) passes this as the cached stable core, so reading it
    here keeps CANON.md the single human-editable source. Original `## ` headings
    are preserved so the cached text reads naturally to the model.
    """
    out: list[str] = []
    keep = False
    for line in canon_path.read_text().splitlines():
        m = re.match(r"^##\s+(?!#)(.+)$", line)  # H2 only
        if m:
            keep = _normalize_heading(m.group(1)) in _BIBLE_HEADINGS
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


def _parse_canon_facts(body: str) -> list[CanonFact]:
    """Parse the numbered list into CanonFacts (`canon-1`, `canon-2`, …).

    Tags are left empty for now (the standing prose facts carry none in the
    source); B3 enriches/queries them when tag-matched canon retrieval lands.
    Multi-line wrapped items are joined into one fact.
    """
    facts: list[CanonFact] = []
    current: list[str] | None = None
    for line in body.splitlines():
        m = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if m:
            if current is not None:
                facts.append(_make_fact(len(facts) + 1, current))
            current = [m.group(1)]
        elif current is not None and line.strip():
            current.append(line.strip())  # continuation of a wrapped item
        elif current is not None:
            facts.append(_make_fact(len(facts) + 1, current))
            current = None
    if current is not None:
        facts.append(_make_fact(len(facts) + 1, current))
    return facts


def _make_fact(n: int, lines: list[str]) -> CanonFact:
    # Drop markdown bold markers so the stored fact is clean prose for the prompt.
    text = re.sub(r"\*\*", "", " ".join(lines)).strip()
    return CanonFact(id=f"canon-{n}", text=text, tags=[])


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

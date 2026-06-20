"""The world-state store — the ONLY module that speaks SQL (Seam discipline).

Same rule as `providers/`: every database read/write goes through a function
here, and nothing outside this module imports `psycopg` or writes SQL. That keeps
the storage choice swappable (Postgres now; a managed DB or pgvector-enabled
instance later) and the query surface small and logged.

The schema is deliberately minimal but real (PHASE_B_TASKS.md B1):

    canon(id, text, tags)                           — the world's standing facts
    cast(id, name, card_text, logical_voice, tags)  — the DJs (note: "cast" is a
                                                       SQL keyword, always quoted)
    events(id, title, body, in_world_datetime, status, tags)  — dated occurrences
    state(key, value)                               — small key/value world state

`docs/CANON.md` stays the human-editable source of truth; `world/seed.py` parses
it (`world/canon_source.py`) and loads it here. Connection details come from
`settings.database_url` (B0.5) — never a hardcoded string.

------------------------------------------------------------------------------
FUTURE — vector search (a documented, UNUSED seam as of B3; see PHASE_B_TASKS.md):
Structured queries over `events`/`canon` (by date / status / tag) are the right,
fast retrieval for now, so pgvector is intentionally NOT enabled yet. The seam
contract lives stubbed in `providers/embeddings.py`. When the assembled context
outgrows the prompt cache or needs semantic (not date/tag) recall, it slots in
HERE: `CREATE EXTENSION vector`, add a `canon_embeddings(canon_id, embedding
vector(N))` table joined to `canon`, and a `search_canon()` query — driven by that
seam. Nothing outside this module should need to change.
------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

import psycopg

from ..config import settings
from ..logging_setup import get_logger

log = get_logger(__name__)


# --- Row shapes (1:1 with the tables) --------------------------------------
# Defined here because they mirror the schema this module owns; the parser
# (canon_source.py) and seed.py import them, so the row shape has one home.


@dataclass(frozen=True)
class CanonFact:
    """One standing world fact (a `canon` row)."""

    id: str
    text: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CastMember:
    """One DJ / presenter (a `cast` row)."""

    id: str
    name: str
    card_text: str
    logical_voice: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Event:
    """One dated, progressing occurrence (an `events` row).

    `status` is a stored snapshot (upcoming/today/past) seeded from CANON.md; B2
    will (re)compute it from `in_world_datetime` relative to the world clock.
    """

    id: str
    title: str
    body: str
    in_world_datetime: datetime
    status: str
    tags: list[str] = field(default_factory=list)


# --- Schema -----------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS canon (
    id   text PRIMARY KEY,
    text text NOT NULL,
    tags text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "cast" (
    id            text PRIMARY KEY,
    name          text NOT NULL,
    card_text     text NOT NULL,
    logical_voice text NOT NULL,
    tags          text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS events (
    id                text PRIMARY KEY,
    title             text NOT NULL,
    body              text NOT NULL,
    in_world_datetime timestamp NOT NULL,
    status            text NOT NULL,
    tags              text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS state (
    key   text PRIMARY KEY,
    value text NOT NULL
);

-- Indexes for the structured event retrieval B2/B3 lean on (by status, by date).
CREATE INDEX IF NOT EXISTS events_status_idx   ON events (status);
CREATE INDEX IF NOT EXISTS events_datetime_idx ON events (in_world_datetime);
"""

# The four world tables, in FK-safe order (none today, but keep it stable for a
# single TRUNCATE that reproduces the world cleanly on re-seed).
_WORLD_TABLES = ("canon", '"cast"', "events", "state")


# --- Connection -------------------------------------------------------------


def _redacted_url(url: str) -> str:
    """Hide any password in the DB URL before it touches the logs."""
    # postgresql://user:password@host/db -> postgresql://user:***@host/db
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        creds, _, tail = rest.partition("@")
        if ":" in creds:
            user = creds.split(":", 1)[0]
            return f"{scheme}://{user}:***@{tail}"
    return url


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    """Yield a connection to `settings.database_url` as one transaction.

    Commits on clean exit, rolls back and logs loudly on any exception, and
    always closes. This is the single entry point for a unit of DB work.
    """
    safe_url = _redacted_url(settings.database_url)
    log.debug("db_connect", url=safe_url)
    conn = psycopg.connect(settings.database_url)
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        log.error("db_transaction_failed", url=safe_url, error=str(exc))
        raise
    finally:
        conn.close()


# --- Schema / reset ---------------------------------------------------------


def init_schema(conn: psycopg.Connection) -> None:
    """Create the world tables and indexes if they do not exist (idempotent)."""
    log.info("db_init_schema")
    conn.execute(_SCHEMA_SQL)


def clear_world(conn: psycopg.Connection) -> None:
    """Empty all world tables so a re-seed reproduces the state from CANON.md.

    TRUNCATE (not DELETE) so a removed canon fact leaves no orphan — the DB
    becomes exactly what the source file now says.
    """
    log.info("db_clear_world", tables=_WORLD_TABLES)
    conn.execute(f"TRUNCATE {', '.join(_WORLD_TABLES)}")


# --- Writes -----------------------------------------------------------------


def insert_canon(conn: psycopg.Connection, facts: Iterable[CanonFact]) -> int:
    """Insert canon facts; return how many rows were written."""
    rows = [(f.id, f.text, f.tags) for f in facts]
    conn.cursor().executemany(
        "INSERT INTO canon (id, text, tags) VALUES (%s, %s, %s)", rows
    )
    log.info("db_insert_canon", count=len(rows))
    return len(rows)


def insert_cast(conn: psycopg.Connection, members: Iterable[CastMember]) -> int:
    """Insert cast members; return how many rows were written."""
    rows = [(m.id, m.name, m.card_text, m.logical_voice, m.tags) for m in members]
    conn.cursor().executemany(
        'INSERT INTO "cast" (id, name, card_text, logical_voice, tags) '
        "VALUES (%s, %s, %s, %s, %s)",
        rows,
    )
    log.info("db_insert_cast", count=len(rows))
    return len(rows)


def insert_events(conn: psycopg.Connection, events: Iterable[Event]) -> int:
    """Insert events; return how many rows were written."""
    rows = [
        (e.id, e.title, e.body, e.in_world_datetime, e.status, e.tags) for e in events
    ]
    conn.cursor().executemany(
        "INSERT INTO events (id, title, body, in_world_datetime, status, tags) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        rows,
    )
    log.info("db_insert_events", count=len(rows))
    return len(rows)


def set_state(conn: psycopg.Connection, key: str, value: str) -> None:
    """Upsert one key/value world-state row."""
    conn.execute(
        "INSERT INTO state (key, value) VALUES (%s, %s) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (key, value),
    )
    log.debug("db_set_state", key=key)


# --- Reads ------------------------------------------------------------------


def all_canon(conn: psycopg.Connection) -> list[CanonFact]:
    """All canon facts, ordered by id."""
    rows = conn.execute("SELECT id, text, tags FROM canon ORDER BY id").fetchall()
    return [CanonFact(id, text, list(tags)) for id, text, tags in rows]


def canon_by_tags(conn: psycopg.Connection, tags: Iterable[str]) -> list[CanonFact]:
    """Canon facts whose tags overlap any of `tags`, ordered by id.

    The tag-matched retrieval B3's `context.assemble` uses to pull only the canon
    relevant to a topic. Uses Postgres array overlap (`&&`). An empty `tags` (or no
    overlap) returns no rows — the caller decides whether to fall back to the full
    set. NOTE: the seeded canon facts currently carry empty tags (the parser leaves
    them blank), so this returns nothing until facts are tagged; the seam is in
    place for when they are. Until then context.assemble falls back to `all_canon`.
    """
    tag_list = list(tags)
    log.debug("db_canon_by_tags", tags=tag_list)
    if not tag_list:
        return []
    rows = conn.execute(
        "SELECT id, text, tags FROM canon WHERE tags && %s ORDER BY id",
        (tag_list,),
    ).fetchall()
    return [CanonFact(id, text, list(tags)) for id, text, tags in rows]


def all_cast(conn: psycopg.Connection) -> list[CastMember]:
    """All cast members, ordered by id."""
    rows = conn.execute(
        'SELECT id, name, card_text, logical_voice, tags FROM "cast" ORDER BY id'
    ).fetchall()
    return [
        CastMember(id, name, card, voice, list(tags))
        for id, name, card, voice, tags in rows
    ]


def get_cast_member(conn: psycopg.Connection, member_id: str) -> CastMember | None:
    """One cast member by id, or None."""
    row = conn.execute(
        'SELECT id, name, card_text, logical_voice, tags FROM "cast" WHERE id = %s',
        (member_id,),
    ).fetchone()
    if row is None:
        return None
    id, name, card, voice, tags = row
    return CastMember(id, name, card, voice, list(tags))


def get_event(conn: psycopg.Connection, event_id: str) -> Event | None:
    """One event by id, or None (used by the B2 progression demo)."""
    row = conn.execute(
        "SELECT id, title, body, in_world_datetime, status, tags FROM events "
        "WHERE id = %s",
        (event_id,),
    ).fetchone()
    return None if row is None else Event(*row[:5], list(row[5]))


def events_by_status(conn: psycopg.Connection, status: str) -> list[Event]:
    """Events with the given status, soonest first."""
    log.debug("db_events_by_status", status=status)
    rows = conn.execute(
        "SELECT id, title, body, in_world_datetime, status, tags FROM events "
        "WHERE status = %s ORDER BY in_world_datetime",
        (status,),
    ).fetchall()
    return [Event(*r[:5], list(r[5])) for r in rows]


def events_in_range(
    conn: psycopg.Connection, start: datetime, end: datetime
) -> list[Event]:
    """Events whose in-world datetime falls within [start, end], soonest first.

    The date-window query B2/B3 use to find what is happening near `now`.
    """
    log.debug("db_events_in_range", start=start.isoformat(), end=end.isoformat())
    rows = conn.execute(
        "SELECT id, title, body, in_world_datetime, status, tags FROM events "
        "WHERE in_world_datetime BETWEEN %s AND %s ORDER BY in_world_datetime",
        (start, end),
    ).fetchall()
    return [Event(*r[:5], list(r[5])) for r in rows]


def get_state(conn: psycopg.Connection, key: str) -> str | None:
    """One state value by key, or None."""
    row = conn.execute("SELECT value FROM state WHERE key = %s", (key,)).fetchone()
    return row[0] if row else None


def counts(conn: psycopg.Connection) -> dict[str, int]:
    """Row counts per world table — for seed verification and health checks."""
    out: dict[str, int] = {}
    for table in _WORLD_TABLES:
        n = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        out[table.strip('"')] = n
    return out

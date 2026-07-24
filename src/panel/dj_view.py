"""R5.4 (=E1.11) — the per-DJ page: "who is this host *now*".

A read-only join, beside the E1.4 cast-card editor, of one host's hand-authored CARD
(the bible) with the LIVED state that accrues around it:
  * recent **journal** entries (D13 `host_journal`) — what they've said/felt on air;
  * world-memory **affinities** (D9.4 tags on the cast row) — the domains they favour;
  * the **shows** they're scheduled on (grid usage) — where the grid puts them;
  * their **recent segments** (from the live schedule + aired sidecars).

Pure view: it never writes. The card stays editable on the E1.4 screen; this page is
the "state" half of the D13 card-is-bible / journal-is-state split. DB-backed, so it
degrades to a readable note (never a 500) when the store is down.
"""

from __future__ import annotations

from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..world import programming, store
from . import cast_edit, schedule_view
from .views import _hhmm

log = get_logger(__name__)


def dj_ids() -> list[str]:
    """Every cast id that has a card (the DJ list), in card order."""
    return [c["id"] for c in cast_edit.list_cards()]


def _split_tags(raw: str | None) -> list[str]:
    """A card's comma/space `Tags:` line → a clean list (fallback when the DB is down)."""  # noqa: E501
    if not raw:
        return []
    return [t.strip() for t in raw.replace(",", " ").split() if t.strip()]


def _journal_row(entry) -> dict:  # noqa: ANN001
    """One journal entry as a template-friendly row."""
    return {
        "kind": entry.kind,
        "text": entry.text,
        "other_host": entry.other_host,
        "segment_id": entry.segment_id,
        "when": entry.air_time.strftime("%Y-%m-%d %H:%M") if entry.air_time else "—",
        "tags": list(entry.tags),
    }


def _recent_segments(cid: str, progs: dict, now: datetime) -> list[dict]:
    """This host's recent segments — live queue + aired sidecars, newest first.

    Host membership is the grid's: a segment belongs to a program (its `program` id),
    and the host is "on it" when the grid lists them among that program's hosts (the
    same notion as `grid_uses`). Dedupes live vs sidecar by segment id.
    """
    seen: set[str] = set()
    rows: list[dict] = []
    live = schedule_view._load_state().get("entries", [])
    sidecars = [
        schedule_view._entry_from_sidecar(d) for d in schedule_view._iter_sidecars()
    ]
    for e in [*live, *sidecars]:
        sid = e.get("id")
        if not sid or sid in seen:
            continue
        prog = progs.get(e.get("program"))
        if prog is None or cid not in prog.hosts:
            continue
        seen.add(sid)
        rows.append(
            {
                "id": sid,
                "when": _hhmm(e.get("air_time")),
                "air_time": e.get("air_time") or "",
                "program": e.get("program_name") or prog.name,
                "format": e.get("format") or "—",
            }
        )
    rows.sort(key=lambda r: r["air_time"], reverse=True)
    return rows[: settings.panel_dj_segments_limit]


def view(cid: str, now: datetime | None = None) -> dict | None:
    """Assemble one DJ's page (None if the id has no card; degrades if the DB is down)."""  # noqa: E501
    now = now or datetime.now()
    card = cast_edit.card_form(cid)
    if card is None:
        return None

    member = None
    journal: list[dict] = []
    journal_total = 0
    db_error = None
    try:
        with store.connect() as conn:
            member = store.get_cast_member(conn, cid)
            journal = [
                _journal_row(e)
                for e in store.journal_recent_for_host(
                    conn, cid, limit=settings.panel_dj_journal_limit
                )
            ]
            journal_total = store.journal_counts(conn).get(cid, 0)
    except Exception as exc:  # noqa: BLE001 — the page degrades, never 500s
        log.warning("panel_dj_page_db_unavailable", cid=cid, error=str(exc))
        db_error = str(exc)

    # D9.4 affinities = the DB cast tags (fall back to the card's Tags line if DB down).
    affinities = list(member.tags) if member else _split_tags(card.get("tags"))
    based = (member.based if member else card.get("based")) or "station"

    progs = programming.all_programs()
    shows = [{"id": pid, "name": p.name} for pid, p in progs.items() if cid in p.hosts]
    segments = _recent_segments(cid, progs, now)

    return {
        "available": True,
        "cid": cid,
        "card": card,
        "in_db": member is not None,
        "db_error": db_error,
        "affinities": affinities,
        "based": based,
        "shows": shows,
        "segments": segments,
        "journal": journal,
        "journal_total": journal_total,
    }

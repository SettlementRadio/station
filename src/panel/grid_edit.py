"""E1.2 — the grid editor's core: read / mutate / validate / write grid.yaml.

The grid file STAYS the source of truth (E1 principle #1): this edits the existing
human-authored `docs/programming/grid.yaml` in place and the live mtime-cached
loader picks it up — no DB projection, no second store, no seed step. So the edit
must diff like a HAND edit: comments, key order, quote styles, and the folded
`>-` briefs all survive. That rules out `yaml.safe_dump` (it discards every
comment); we use **ruamel.yaml** round-trip mode and mutate ONLY the fields the
operator actually changed, so an untouched program stays byte-identical.

Validation reuses the REAL consumer (principle #5): the candidate is parsed by
`programming`'s own `_parse_program` + slot parsers, and the parsed Programs are
checked against `programming`'s own constants (framings, energies, markers) and
`formats.FORMATS` — never a second, drifting validator. Errors block the write;
warnings (e.g. an unknown host id while the DB is down) are shown but allowed.

The write is atomic (tmp + os.replace) and keeps a one-deep `grid.yaml.bak`.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, FoldedScalarString

from ..config import settings
from ..formats import FORMATS
from ..logging_setup import get_logger
from ..world import programming, store

log = get_logger(__name__)

# The known enumerations the editor validates against — pulled from the REAL
# consumer so they can't drift (programming coerces silently; the editor flags).
_FRAMINGS = frozenset({"solo", "handover", "ensemble", "legacy"})
_CLOCK_FORMATS = frozenset(FORMATS) | programming._MARKERS  # talk/news/… + markers

# ruamel in round-trip mode: preserve quotes; a very wide column so long flow
# lists / briefs are never re-wrapped (which would spuriously enlarge the diff).
_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.width = 4096


# --- Reading -----------------------------------------------------------------


def grid_path() -> Path:
    return settings.programming_grid_path


def current_text() -> str:
    """The grid file exactly as on disk."""
    return grid_path().read_text(encoding="utf-8")


def _load_doc(text: str | None = None):
    """Load the round-trip document (from `text`, else the live file)."""
    return _yaml.load(text if text is not None else current_text())


def _dump(doc) -> str:
    buf = io.StringIO()
    _yaml.dump(doc, buf)
    return buf.getvalue()


@dataclass
class ProgramForm:
    """The editable per-program fields, as strings for the HTML form."""

    id: str
    name: str = ""
    hosts: str = ""  # space/comma separated cast ids
    framing: str = "solo"
    daypart: str = ""
    clock: str = ""  # space/comma separated clock tokens
    break_every: str = ""  # int; "" or 0 = no breaks
    guest_chance: str = ""  # float 0..1; "" = global default
    brief: str = ""
    energy: str = ""  # "" | calm | steady | bright
    talk_length_sec: str = ""  # int; "" or 0 = global default
    domains: str = ""  # space/comma separated domain tags


def _join(seq) -> str:
    return ", ".join(str(x) for x in (seq or []))


def _scalar(v) -> str:
    return "" if v is None else str(v)


def program_ids() -> list[str]:
    """Every program id defined in the grid, file order preserved."""
    doc = _load_doc()
    return list((doc.get("programs") or {}).keys())


def program_form(pid: str) -> ProgramForm:
    """Build the form's initial values from the RAW YAML (a no-op save is identical)."""
    doc = _load_doc()
    pmap = (doc.get("programs") or {}).get(pid)
    if pmap is None:
        raise KeyError(pid)
    return ProgramForm(
        id=pid,
        name=_scalar(pmap.get("name")),
        hosts=_join(pmap.get("hosts")),
        framing=_scalar(pmap.get("framing")) or "solo",
        daypart=_scalar(pmap.get("daypart")),
        clock=_join(pmap.get("clock")),
        break_every=_scalar(pmap.get("break_every")),
        guest_chance=_scalar(pmap.get("guest_chance")),
        brief=_scalar(pmap.get("brief")).strip(),
        energy=_scalar(pmap.get("energy")),
        talk_length_sec=_scalar(pmap.get("talk_length_sec")),
        domains=_join(pmap.get("domains")),
    )


def program_display(pid: str):
    """The PARSED Program (for the list view — resolved hosts, clock label, dials)."""
    return programming.all_programs().get(pid)


def slot_map() -> list[tuple[str, list[tuple[str, str, str]]]]:
    """The weekly tiling as (weekday_key, [(time_range, program_id, program_name)]).

    Read-only in E1.2: the program CARDS are the highest-pain, frequently-edited
    YAML (hosts, briefs, clocks, dials). Re-tiling the week is rare and gap-risky
    (the grid must tile with no holes), so it stays a file edit for now — the map
    is shown here for context. A gap-safe slot editor is a natural follow-up.
    """
    doc = _load_doc()
    names = {
        pid: _scalar(p.get("name")) or pid
        for pid, p in (doc.get("programs") or {}).items()
    }
    out: list[tuple[str, list[tuple[str, str, str]]]] = []
    for wk_key, ranges in (doc.get("grid") or {}).items():
        rows = [
            (str(rng), str(pid), names.get(str(pid), str(pid)))
            for rng, pid in (ranges or {}).items()
        ]
        out.append((str(wk_key), rows))
    return out


def unified_diff(current: str, candidate: str) -> str:
    """A unified diff (current file → candidate) for the confirm step."""
    import difflib

    lines = difflib.unified_diff(
        current.splitlines(keepends=True),
        candidate.splitlines(keepends=True),
        fromfile="grid.yaml (current)",
        tofile="grid.yaml (candidate)",
    )
    return "".join(lines)


# --- Mutating (change-only, style-preserving) --------------------------------


def _tokens(value: str) -> list[str]:
    """Split a form list field on commas/whitespace into clean tokens."""
    return [t for t in value.replace(",", " ").split() if t]


def _flow_seq(items: list[str]) -> CommentedSeq:
    """A flow-style sequence (`[a, b, c]`) — matches the grid's list convention."""
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def _set_list(pmap, key: str, items: list[str]) -> None:
    """Set/clear a flow list field, only when its VALUES change (fidelity)."""
    current = [str(x) for x in (pmap.get(key) or [])]
    if current == items:
        return
    if not items:
        pmap.pop(key, None)
        return
    pmap[key] = _flow_seq(items)


def _set_opt_scalar(pmap, key: str, value: str, *, quoted: bool = False) -> None:
    """Set/clear an optional scalar, only on change; "" removes the key."""
    value = value.strip()
    current = _scalar(pmap.get(key)).strip()
    if value == current:
        return
    if not value:
        pmap.pop(key, None)
        return
    pmap[key] = DoubleQuotedScalarString(value) if quoted else value


def _set_req_scalar(pmap, key: str, value: str, *, quoted: bool = False) -> None:
    """Set a required scalar (name/framing) only on change; never removes it."""
    value = value.strip()
    if value == _scalar(pmap.get(key)).strip():
        return
    pmap[key] = DoubleQuotedScalarString(value) if quoted and value else value


def _set_opt_int(pmap, key: str, value: str) -> None:
    """Set/clear an int dial where 0/"" means 'absent = default'."""
    value = value.strip()
    n = int(value) if value.lstrip("-").isdigit() else 0
    current = pmap.get(key)
    current_n = int(current) if isinstance(current, int) else 0
    if n == current_n:
        return
    if n <= 0:
        pmap.pop(key, None)
        return
    pmap[key] = n


def _set_opt_float(pmap, key: str, value: str) -> None:
    """Set/clear a float dial; "" removes the key (falls back to the global default)."""
    value = value.strip()
    current = pmap.get(key)
    if not value:
        if key in pmap:
            pmap.pop(key, None)
        return
    try:
        f = float(value)
    except ValueError:
        return  # validation reports it; don't corrupt the doc
    if isinstance(current, (int, float)) and float(current) == f:
        return
    pmap[key] = f


def _set_brief(pmap, value: str) -> None:
    """Set/clear the brief as a folded `>-` block, only on change (fidelity)."""
    value = value.strip()
    current = _scalar(pmap.get("brief")).strip()
    if value == current:
        return
    if not value:
        pmap.pop("brief", None)
        return
    pmap["brief"] = FoldedScalarString(value)


def apply_program_edit(pid: str, form: ProgramForm) -> str:
    """Return the candidate file text with `pid`'s changed fields applied (no write)."""
    doc = _load_doc()
    programs = doc.get("programs") or {}
    if pid not in programs:
        raise KeyError(pid)
    pmap = programs[pid]

    _set_req_scalar(pmap, "name", form.name, quoted=True)
    _set_list(pmap, "hosts", _tokens(form.hosts))
    _set_req_scalar(pmap, "framing", form.framing or "solo")
    _set_opt_scalar(pmap, "daypart", form.daypart)
    _set_list(pmap, "clock", _tokens(form.clock))
    _set_opt_int(pmap, "break_every", form.break_every)
    _set_opt_float(pmap, "guest_chance", form.guest_chance)
    _set_brief(pmap, form.brief)
    _set_opt_scalar(pmap, "energy", form.energy)
    _set_opt_int(pmap, "talk_length_sec", form.talk_length_sec)
    _set_list(pmap, "domains", _tokens(form.domains))

    return _dump(doc)


# --- Validation (the real consumer) ------------------------------------------


@dataclass
class Validation:
    """The outcome of validating a candidate: hard errors + soft warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _cast_ids() -> set[str] | None:
    """The known cast ids (for host validation); None when the DB is unreachable."""
    try:
        with store.connect() as conn:
            return {m.id for m in store.all_cast(conn)}
    except Exception as exc:  # noqa: BLE001 — DB down → host check downgrades to a warning
        log.warning("grid_edit_cast_lookup_failed", error=str(exc))
        return None


def validate_text(candidate: str, *, focus: str | None = None) -> Validation:
    """Validate a candidate grid by parsing it with the REAL programming parser.

    Hard errors (block the write): YAML syntax, a missing `programs` map, a bad
    framing/energy/clock-format, an unknown host id, or a grid slot pointing at an
    undefined program. Soft warnings (shown, allowed): host ids unchecked (DB down).

    `focus` scopes the PER-PROGRAM semantic checks (framing/energy/clock/hosts) to a
    single edited program, so a pre-existing quirk in an untouched show never blocks
    the operator's edit. The GLOBAL structural checks (YAML shape, slot→program
    references) always run over the whole file.
    """
    v = Validation()

    # 1) YAML syntax + top-level shape (pyyaml — the same lib programming loads with).
    try:
        raw = yaml.safe_load(candidate) or {}
    except yaml.YAMLError as exc:
        v.errors.append(f"YAML syntax error: {exc}")
        return v
    if not isinstance(raw, dict) or not isinstance(raw.get("programs"), dict):
        v.errors.append("the grid must have a top-level 'programs:' mapping")
        return v

    # 2) Parse every program through the REAL parser (for slot-reference validation);
    #    run the SEMANTIC checks on the focused program only (else all programs).
    cast = _cast_ids()
    programs = {}
    for pid, data in raw["programs"].items():
        pid = str(pid)
        try:
            prog = programming._parse_program(pid, dict(data or {}))
        except Exception as exc:  # noqa: BLE001 — surface a parse failure as an error
            v.errors.append(f"program {pid!r}: cannot parse ({exc})")
            continue
        programs[pid] = prog

        if focus is not None and pid != focus:
            continue  # only the edited program is semantically checked

        if prog.framing not in _FRAMINGS:
            v.errors.append(
                f"program {pid!r}: unknown framing {prog.framing!r} "
                f"(use one of {', '.join(sorted(_FRAMINGS))})"
            )
        if prog.energy and prog.energy not in programming._ENERGIES:
            v.errors.append(
                f"program {pid!r}: unknown energy {prog.energy!r} "
                f"(use calm | steady | bright, or blank)"
            )
        for step in prog.clock:
            if step.format not in _CLOCK_FORMATS:
                v.errors.append(
                    f"program {pid!r}: unknown clock format {step.format!r} "
                    f"(use one of {', '.join(sorted(_CLOCK_FORMATS))})"
                )
        if cast is not None:
            for hid in prog.hosts:
                if hid not in cast:
                    v.errors.append(f"program {pid!r}: unknown host id {hid!r}")
        elif prog.hosts:
            v.warnings.append(
                f"program {pid!r}: host ids not checked (world DB unreachable)"
            )

    # 3) Every grid slot must point at a defined program (a dangling id = a silent
    #    fallback-to-default hole at air time).
    for wk_key, ranges in (raw.get("grid") or {}).items():
        for rng, program_id in (ranges or {}).items():
            if str(program_id) not in programs:
                v.errors.append(
                    f"grid slot {wk_key} {rng}: undefined program {program_id!r}"
                )

    return v


# --- Writing (atomic + one-deep backup) --------------------------------------


def write_grid(candidate: str, *, focus: str | None = None) -> Path:
    """Back up the current grid, then atomically replace it with `candidate`.

    Re-validates first (defence in depth — never write an invalid grid even if a
    stale confirm slips through), scoped to the same `focus` as the diff step.
    Returns the backup path.
    """
    v = validate_text(candidate, focus=focus)
    if not v.ok:
        raise ValueError("; ".join(v.errors))

    path = grid_path()
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(candidate, encoding="utf-8")
    os.replace(tmp, path)
    programming.reload()  # drop the mtime cache so the next program_for re-reads
    log.info("grid_written", path=str(path), backup=str(backup), bytes=len(candidate))
    return backup

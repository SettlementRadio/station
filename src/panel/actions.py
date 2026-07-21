"""E1.1 — the operator ACTIONS: the make verbs, run as background jobs.

Each action is the EXACT command its Make target runs, invoked as a SUBPROCESS of
the same venv interpreter. Subprocess (not in-process) is deliberate: a seed/tick
crash can never take the panel down, output capture is trivial, and the command
matches `make X` faithfully. Every action runs in a background thread so the page
never hangs on a 30-minute batch; its output streams line-by-line into the run
record for the page to show.

Concurrency: a single MUTATION LOCK means two *mutating* panel actions can't
overlap (read-only ones like `health` are exempt). The lock is the panel's OWN
guard — the C5 cron/systemd top-up runs in a SEPARATE process and is NOT blocked
by it; the panel's `schedule` button is a manual extra, not the driver (see
ADMIN_MANUAL). A lock file beside the schedule state makes the held state visible
across processes; the in-process slot is the real gate (so a panel restart never
leaves a stale lock).

`reset-world` is DESTRUCTIVE: it is marked so, carries a typed confirmation phrase
the route enforces, and is invoked with `--force` (the panel's own gate replaces
the CLI's interactive prompt). See docs/PHASE_E_PANEL_TASKS.md E1.1 + principle #4.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger

log = get_logger(__name__)

# The venv interpreter running the panel — the same `$(PY)` the Make targets use,
# so a subprocess action runs the exact `.venv/bin/python -m <module>` command.
_PY = sys.executable
# repo root: src/panel/actions.py -> parents[2]. Actions run with this cwd so the
# child's relative paths (.env, docs/, segments/) resolve exactly as `make` does.
_REPO_ROOT = Path(__file__).resolve().parents[2]

# The mutation lock file (visible across processes); the in-process slot is the
# real gate. Lives beside the schedule state, under the existing segments_dir dial.
_LOCK_PATH = settings.segments_dir / "panel-action.lock"

_MAX_RUNS = 25  # how many recent runs the page keeps


# --- The action registry -----------------------------------------------------


@dataclass(frozen=True)
class Action:
    """One operator command: its faithful argv + how the panel must treat it."""

    id: str
    label: str
    desc: str
    args: tuple[str, ...]  # the `-m` module + args (the exact Make command)
    group: str  # UI grouping: seed | world | air | ops | danger
    mutating: bool = True  # takes the mutation lock (read-only actions don't)
    destructive: bool = False  # own page + typed-phrase gate (principle #4)
    confirm_phrase: str | None = None

    @property
    def argv(self) -> list[str]:
        return [_PY, "-m", *self.args]


# Ordered as the page groups them. Each `args` mirrors the Makefile target exactly.
_ACTION_LIST: tuple[Action, ...] = (
    Action(
        "seed-canon",
        "Seed canon",
        "Refresh the world from docs/canon/ (safe — keeps tick-generated world).",
        ("src.world.seed", "canon"),
        "seed",
    ),
    Action(
        "seed-tracks",
        "Seed tracks",
        "Refresh the tracks catalogue from config/tracks.yaml.",
        ("src.world.seed_tracks",),
        "seed",
    ),
    Action(
        "seed-sponsors",
        "Seed sponsors",
        "Refresh the sponsors catalog from config/sponsors.yaml.",
        ("src.world.seed_sponsors",),
        "seed",
    ),
    Action(
        "world-tick",
        "World tick",
        "Run one nightly world tick — invent + "
        "advance stories (long-running with Batch on).",
        ("src.world.world_tick",),
        "world",
    ),
    Action(
        "micro-tick",
        "Micro-tick",
        "Run one intra-day micro-tick — a small near-live nudge, or a quiet run.",
        ("src.world.micro_tick",),
        "world",
    ),
    Action(
        "schedule",
        "Schedule top-up",
        "Top up the rolling buffer to depth + "
        "write the playlist (long-running; live TTS).",
        ("src.scheduler",),
        "air",
    ),
    Action(
        "prune",
        "Prune audio",
        "GC aired, unreferenced segment audio past the retention window.",
        ("src.scheduler", "--prune"),
        "air",
    ),
    Action(
        "fallback",
        "Fallback assets",
        "Pre-render the never-dead fallback (evergreen pool + disclosure ident).",
        ("src.fallback",),
        "air",
    ),
    Action(
        "ident",
        "Disclosure ident",
        "Render (or reuse) the spoken AI-disclosure ident.",
        ("src.disclosure",),
        "air",
    ),
    Action(
        "health",
        "Health check",
        "Run the C4 health checks + alerting (buffer / last run / stream).",
        ("src.health",),
        "ops",
        mutating=False,
    ),
    Action(
        "reset-world",
        "Reset the world",
        "DESTRUCTIVE — wipe the entire living "
        "world + canon and rebuild from the bible.",
        ("src.world.seed", "reset", "--force"),
        "danger",
        destructive=True,
        confirm_phrase="reset the world",
    ),
)

ACTIONS: dict[str, Action] = {a.id: a for a in _ACTION_LIST}


# --- Run records -------------------------------------------------------------


@dataclass
class Run:
    """One invocation of an action: its live status + streamed output."""

    id: str
    action_id: str
    label: str
    started_at: datetime
    status: str = "running"  # running | done | failed
    returncode: int | None = None
    finished_at: datetime | None = None
    _lines: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, text: str) -> None:
        with self._lock:
            self._lines.append(text)

    @property
    def output(self) -> str:
        with self._lock:
            return "".join(self._lines)

    @property
    def duration_sec(self) -> float:
        end = self.finished_at or datetime.now()
        return (end - self.started_at).total_seconds()


_RUNS: list[Run] = []  # most-recent first
_RUNS_LOCK = threading.Lock()


def recent_runs() -> list[Run]:
    """A snapshot of recent runs, most-recent first (for the page)."""
    with _RUNS_LOCK:
        return list(_RUNS)


def _record(run: Run) -> None:
    with _RUNS_LOCK:
        _RUNS.insert(0, run)
        del _RUNS[_MAX_RUNS:]


# --- The mutation lock -------------------------------------------------------


class Busy(Exception):  # noqa: N818 — reads as `actions.Busy`; not an error condition
    """Raised when a mutating action is asked for while one already runs."""

    def __init__(self, holder: Run) -> None:
        super().__init__(f"{holder.label} is already running")
        self.holder = holder


_INPROC = threading.Lock()
_current_mutation: Run | None = None


def current_mutation() -> Run | None:
    """The mutating run holding the lock right now, if any (for the page/banner)."""
    with _INPROC:
        if _current_mutation is not None and _current_mutation.status == "running":
            return _current_mutation
        return None


def _acquire_mutation(run: Run) -> None:
    """Take the single mutation slot; raise Busy if one is already running."""
    global _current_mutation
    with _INPROC:
        if _current_mutation is not None and _current_mutation.status == "running":
            raise Busy(_current_mutation)
        _current_mutation = run
        try:  # best-effort cross-process breadcrumb; the in-proc slot is the gate
            _LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
            _LOCK_PATH.write_text(
                f"{os.getpid()} {run.action_id} {run.started_at.isoformat()}\n",
                encoding="utf-8",
            )
        except OSError as exc:
            log.warning("panel_lockfile_write_failed", error=str(exc))


def _release_mutation(run: Run) -> None:
    global _current_mutation
    with _INPROC:
        if _current_mutation is run:
            _current_mutation = None
            try:
                _LOCK_PATH.unlink()
            except OSError:
                pass


# --- Running an action -------------------------------------------------------


def start_action(action_id: str, *, phrase: str | None = None) -> Run:
    """Validate, take the lock if mutating, and launch the action in a thread.

    Raises KeyError (unknown action), PermissionError (destructive w/o the phrase),
    or Busy (a mutation is already running). Returns the live Run on success.
    """
    action = ACTIONS[action_id]  # KeyError propagates for an unknown id
    if action.destructive and (phrase or "").strip() != action.confirm_phrase:
        raise PermissionError(f"confirmation phrase required for {action_id}")

    run = Run(
        id=uuid.uuid4().hex[:8],
        action_id=action.id,
        label=action.label,
        started_at=datetime.now(),
    )
    if action.mutating:
        _acquire_mutation(run)  # raises Busy if the slot is taken

    _record(run)
    threading.Thread(target=_execute, args=(action, run), daemon=True).start()
    return run


def _execute(action: Action, run: Run) -> None:
    """Run the subprocess, streaming combined stdout/stderr into the run record."""
    log.info("panel_action_start", action=action.id, run=run.id, argv=action.argv)
    run.append(f"$ {' '.join(action.argv)}\n\n")
    try:
        proc = subprocess.Popen(
            action.argv,
            cwd=str(_REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:  # streams as the child prints
            run.append(line)
        proc.wait()
        run.returncode = proc.returncode
        run.status = "done" if proc.returncode == 0 else "failed"
    except Exception as exc:  # noqa: BLE001 — a launch failure must be visible, not fatal
        run.append(f"\n[panel] failed to launch: {exc}\n")
        run.returncode = -1
        run.status = "failed"
    finally:
        run.finished_at = datetime.now()
        if action.mutating:
            _release_mutation(run)
        log.info(
            "panel_action_done",
            action=action.id,
            run=run.id,
            status=run.status,
            returncode=run.returncode,
            duration_sec=round(run.duration_sec, 1),
        )

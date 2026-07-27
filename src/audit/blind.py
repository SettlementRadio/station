"""Q0.2 — `make audit-blind`: the shuffled, unlabelled script pool Q8 scores.

Q8's qualitative read is only worth anything if the reader cannot tell which scripts
came from before the fixes and which came after. So this builds the pool mechanically:

  * **base arm** — scripts regenerated from the pre-Q0 commit, reached through a
    throwaway `git worktree`, so it is genuinely that revision's prompts and not today's
    code with a flag flipped.
  * **head arm** — scripts from the working tree.
  * both arms shuffled into `docs/audit/blind/<uuid>.txt`, one script per file, with
    **no label in the file**, and the answer key written to a **gitignored** `key.json`.

**Why the base arm uses `scripts/audit_seed/contrastive_probe.py`.** At the pre-Q0
commit `src/audit/` does not exist, so the probe cannot run there. The seed script does
exist there and drives the same four pinned slots through that revision's own writers'
room — which is exactly why the seed directory was kept rather than deleted. It is
copied into the worktree with its hardcoded repo path rewritten to the worktree root;
without that rewrite it would import the *current* `src/` and both arms would match.

Nothing here is needed until Q8; it is built now so it exists then (Q8's checklist).

    make audit-blind DRY=1                  # the plan and the spend estimate
    make audit-blind BASE_REF=q0-baseline N=10
"""

from __future__ import annotations

import argparse
import contextlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from ..config import settings
from ..logging_setup import get_logger
from . import metrics, probe
from .cli import logs_to_stderr

log = get_logger(__name__)

# The pre-Q0 revision. A TAG, not a hash, so the intent is legible in git — and it must
# be created deliberately by the operator rather than guessed at by this helper.
DEFAULT_BASE_REF = "q0-baseline"

# Rewritten into the worktree's copy of the seed probe. Without it the seed's
# `sys.path.insert(0, "/Users/pavel/station")` pulls in today's code (see above).
_SEED_PATH_LINE = 'sys.path.insert(0, "/Users/pavel/station")'


def plan(n_per_arm: int, base_ref: str) -> dict:
    """What the pool will contain and roughly what it will cost."""
    per_segment = None
    try:
        per_segment = metrics.cost_metrics().get("usd_per_talk_segment")
    except Exception as exc:  # noqa: BLE001
        log.warning("audit_blind_cost_unknown", error=str(exc))
    total = n_per_arm * 2
    return {
        "base_ref": base_ref,
        "per_arm": n_per_arm,
        "total_scripts": total,
        "estimated_usd": round(total * per_segment, 2) if per_segment else None,
        "out_dir": str(settings.audit_dir / "blind"),
    }


def render_plan(p: dict) -> str:
    usd = p["estimated_usd"]
    return "\n".join(
        [
            "── BLIND POOL PLAN (real Anthropic calls in BOTH arms) ──",
            f"  base arm : {p['per_arm']} scripts from git ref {p['base_ref']!r}"
            " (throwaway worktree)",
            f"  head arm : {p['per_arm']} scripts from the working tree",
            f"  output   : {p['total_scripts']} unlabelled files in {p['out_dir']}",
            f"  key      : {p['out_dir']}/key.json  (GITIGNORED — do not commit)",
            f"  estimate : {f'${usd:.2f}' if usd else '— (no usage ledger yet)'}",
        ]
    )


def _git(*args: str, cwd: Path | None = None) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def ref_exists(ref: str, *, repo: Path | None = None) -> bool:
    try:
        _git("rev-parse", "--verify", f"{ref}^{{commit}}", cwd=repo)
        return True
    except subprocess.CalledProcessError:
        return False


def prepare_worktree(base_ref: str, dest: Path, *, repo: Path) -> Path:
    """Check `base_ref` out into `dest` and make it runnable.

    The worktree gets the repo's tracked files only, so `.env` and `.venv` (both
    gitignored, both required) are symlinked in from the main tree, and the seed probe
    is copied with its repo path rewritten so it imports the WORKTREE's `src/`.
    """
    _git("worktree", "add", "--detach", str(dest), base_ref, cwd=repo)
    for name in (".env", ".venv"):
        source = repo / name
        if source.exists() and not (dest / name).exists():
            (dest / name).symlink_to(source)
    seed = dest / "scripts" / "audit_seed" / "contrastive_probe.py"
    if not seed.is_file():
        raise FileNotFoundError(
            f"{base_ref} has no scripts/audit_seed/contrastive_probe.py — "
            "the base arm needs that revision's own generator"
        )
    text = seed.read_text(encoding="utf-8")
    if _SEED_PATH_LINE not in text:
        log.warning("audit_blind_seed_path_line_absent", path=str(seed))
    seed.write_text(
        text.replace(_SEED_PATH_LINE, f'sys.path.insert(0, "{dest}")'), encoding="utf-8"
    )
    return dest


def _scripts_from_seed_output(text: str) -> list[str]:
    """Split the seed probe's stdout into one script per pinned slot."""
    out: list[str] = []
    for block in text.split("=" * 90):
        if "-" * 90 not in block:
            continue
        # The seed prints: header / rule / BEAT: … / rule / script
        parts = block.split("-" * 90)
        if len(parts) >= 3 and parts[-1].strip():
            out.append(parts[-1].strip())
    return out


def base_arm(base_ref: str, n: int, *, repo: Path) -> list[str]:
    """Generate `n` scripts from the pre-Q0 revision, via a throwaway worktree."""
    tmp = Path(tempfile.mkdtemp(prefix="sr-blind-base-"))
    tree = tmp / "tree"
    scripts: list[str] = []
    try:
        prepare_worktree(base_ref, tree, repo=repo)
        while len(scripts) < n:
            proc = subprocess.run(
                [sys.executable, "scripts/audit_seed/contrastive_probe.py"],
                cwd=tree,
                capture_output=True,
                text=True,
                check=True,
                timeout=settings.audit_checks_timeout_sec,
            )
            found = _scripts_from_seed_output(proc.stdout)
            if not found:
                raise RuntimeError("the base arm's generator produced no scripts")
            scripts += found
            log.info("audit_blind_base_pass", produced=len(found), total=len(scripts))
    finally:
        with contextlib.suppress(Exception):
            _git("worktree", "remove", "--force", str(tree), cwd=repo)
        shutil.rmtree(tmp, ignore_errors=True)
    return scripts[:n]


def head_arm(n: int) -> list[str]:
    """Generate `n` scripts from the working tree, inside the probe's isolation."""
    scripts: list[str] = []
    runs = max(1, -(-n // len(probe._SLOTS)))  # ceil: passes of the pinned slot list
    with probe.isolated():
        for seg in probe.contrastive(runs):
            scripts.append(seg["script"].strip())
    return scripts[:n]


def write_pool(base: list[str], head: list[str], *, out_dir: Path) -> Path:
    """Shuffle both arms into unlabelled files and write the gitignored key."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = [("base", s) for s in base] + [("head", s) for s in head]
    random.shuffle(entries)
    key: dict[str, str] = {}
    for arm, script in entries:
        name = f"{uuid.uuid4()}.txt"
        (out_dir / name).write_text(script + "\n", encoding="utf-8")
        key[name] = arm
    key_path = out_dir / "key.json"
    key_path.write_text(
        json.dumps(key, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    log.info(
        "audit_blind_pool_written",
        out_dir=str(out_dir),
        files=len(key),
        key=str(key_path),
    )
    return key_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m src.audit.blind", description=__doc__
    )
    parser.add_argument("--base-ref", default=DEFAULT_BASE_REF)
    parser.add_argument(
        "--n", type=int, default=10, help="scripts per arm (default 10)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--seed", type=int, help="shuffle seed (for a reproducible pool)"
    )
    args = parser.parse_args(argv)

    logs_to_stderr()

    p = plan(args.n, args.base_ref)
    print(render_plan(p))
    if args.dry_run:
        return 0

    repo = Path(__file__).resolve().parent.parent.parent
    if not ref_exists(args.base_ref, repo=repo):
        print(
            f"\naudit-blind: git ref {args.base_ref!r} does not exist.\n"
            "  The base arm must be a real pre-Q0 revision. Create the tag first:\n"
            f"    git tag {args.base_ref} <the commit before Q0 landed>\n",
            file=sys.stderr,
        )
        return 2

    if args.seed is not None:
        random.seed(args.seed)
    base = base_arm(args.base_ref, args.n, repo=repo)
    head = head_arm(args.n)
    key_path = write_pool(base, head, out_dir=settings.audit_dir / "blind")
    print(
        f"\nwrote {len(base) + len(head)} unlabelled scripts to {key_path.parent}\n"
        f"key (gitignored, do not show the auditor): {key_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

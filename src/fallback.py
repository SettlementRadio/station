"""C4 — prepare the never-dead PLAYOUT fallback assets.

config/radio.liq airs a fallback CHAIN so the stream is never silent, even if the
generator is fully down and the rolling buffer has drained:

    scheduled playlist -> evergreen pool -> music bed -> disclosure ident -> tone

The scheduled playlist (Layer 5) is written by the scheduler. This module prepares
the *lower* tiers that must already be ready BEFORE they're ever needed —
pre-rendered while the system is healthy, so they survive a Claude/Kokoro/Postgres
outage:

  - the evergreen POOL (src/evergreen.py): timeless, in-world spoken segments,
    rendered once to GC-exempt clips and listed in an evergreen playlist
    Liquidsoap watches;
  - the spoken AI-disclosure IDENT (src/disclosure.py): the same reused clip the
    scheduler weaves on a cadence, here also the deepest spoken last-resort.

The music bed (`assets/bed.mp3`) is an optional human-dropped file and the sine
tone is built into radio.liq, so neither needs preparing here.

`ensure_fallback_assets()` runs best-effort at the top of every scheduler top-up
(so the pool refreshes while things are healthy and cached clips are reused) and
is exposed as `python -m src.fallback` / `make fallback` for a one-off prepare +
verify.
"""

from __future__ import annotations

from pathlib import Path

from .config import settings
from .disclosure import render_ident_audio
from .evergreen import render_evergreen_pool
from .logging_setup import get_logger

log = get_logger(__name__)


def _write_evergreen_playlist(paths: list[str]) -> Path:
    """Write the evergreen pool's existing clips as a playlist Liquidsoap watches.

    One absolute path per line, in pool order — the same shape as the scheduler's
    playout playlist. Only files that actually exist are listed. Always written
    (even empty) so playout has a stable file to watch.
    """
    out = settings.fallback_evergreen_playlist_path
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [str(Path(p).resolve()) for p in paths if Path(p).exists()]
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return out


def ensure_fallback_assets(*, force: bool = False) -> dict:
    """Render + list the never-dead fallback assets; return a summary.

    Best-effort and idempotent: cached clips are reused (rendering only on the
    first run, after `force`, or after a provider/voice change). Each piece is
    guarded so one failure (e.g. TTS down) still prepares the rest — and a prior
    healthy run's cached clips remain on disk regardless, which is the whole point:
    the fallback must be ready before the outage that needs it.
    """
    summary: dict = {"evergreen": 0, "ident": None, "playlist": None}

    try:
        pool = render_evergreen_pool(force=force)
        playlist = _write_evergreen_playlist(pool)
        summary["evergreen"] = len(pool)
        summary["playlist"] = str(playlist)
    except Exception as exc:  # noqa: BLE001 — prep must never raise into a top-up
        log.error("fallback_evergreen_failed", error=str(exc))

    try:
        summary["ident"] = render_ident_audio(force=force)
    except Exception as exc:  # noqa: BLE001
        log.error("fallback_ident_failed", error=str(exc))

    log.info(
        "fallback_assets_ready",
        evergreen=summary["evergreen"],
        ident=bool(summary["ident"]),
        playlist=summary["playlist"],
    )
    return summary


def main(argv: list[str]) -> int:
    """CLI: prepare the fallback assets and print what's ready (verification).

    .venv/bin/python -m src.fallback           (render or reuse the cached clips)
    .venv/bin/python -m src.fallback --force     (force a fresh render)

    Needs a populated .env (live TTS); makes no Claude call (the text is static).
    """
    force = "--force" in argv
    s = ensure_fallback_assets(force=force)
    print("\n----- NEVER-DEAD FALLBACK ASSETS (C4) -----")
    print(f"  evergreen pool  : {s['evergreen']} clip(s) -> {s['playlist']}")
    print(f"  disclosure ident: {s['ident']}")
    print("  music bed       : assets/bed.mp3 (optional — drop one in to use)")
    print("  chain: scheduled -> evergreen -> music bed -> ident -> tone")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))

"""Serve the PUBLIC feeds to a locally-running web app (dev convenience, R7.1).

The site (`/web`) reads the station's feeds cross-origin and polls them, so to look at
the player locally you need two things this script provides:

  1. **CORS.** A plain `python -m http.server` sends no `Access-Control-Allow-Origin`,
     so the browser silently drops every feed read and the page shows its (correct but
     dull) "no feed" fallback.
  2. **Something on air.** On a dev box no scheduler top-up has run, so the real
     `segments/nowplaying.json` says `now: null`. `--demo` synthesises a plausible
     now-playing feed from the REAL grid (whatever show the grid says is on right now,
     plus the next three) with a music slot so the track lore is visible.

    make demo-feeds              # demo now-playing + the real schedule/DJs feeds
    .venv/bin/python scripts/serve_demo_feeds.py --real --port 8099

Then run the app against it:

    cd web && NEXT_PUBLIC_FEEDS_BASE_URL=http://127.0.0.1:8099 npm run dev

This is a DEV TOOL: it never writes into `segments/` (the demo feed is built in a temp
dir), and nothing here runs on the VPS — production serves the real files from nginx
(see docs/ADMIN_MANUAL.md, "The public schedule & DJs feeds").
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import nowplaying  # noqa: E402
from src.config import settings  # noqa: E402
from src.world import programming  # noqa: E402

DEMO_TRACK = {
    "title": "Nine Lamps at Cold Harbor",
    "artist": "Ilsa Rhode",
    "album": "The Long Way Round",
    "era": "27th century",
    "in_world_year": 2618,
    "story_blurb": "Recorded in a dock canteen the night the convoy finally arrived.",
}


def _entry(fmt: str, program, minutes: int, now: datetime, track=None) -> dict:
    """One schedule entry in the shape the scheduler persists."""
    entry = {
        "id": f"{fmt}-{minutes}",
        "format": fmt,
        "program": program.id,
        "program_name": program.name,
        "air_time": (now + timedelta(minutes=minutes)).isoformat(),
        "audio_path": "",
        "actual_duration_sec": 300.0,
        "length_target_sec": 300,
    }
    if track:
        entry["track"] = track
    return entry


def build_demo_dir(now: datetime) -> Path:
    """A temp dir holding a synthesised now-playing feed + the real slow feeds."""
    out = Path(tempfile.mkdtemp(prefix="settlement-demo-feeds-"))

    on_air = programming.program_for(now)
    ahead = [programming.program_for(now + timedelta(minutes=m)) for m in (20, 40, 60)]
    state = {
        "entries": [
            _entry("music", on_air, -3, now, DEMO_TRACK),
            *[
                _entry("talk", p, m, now)
                for p, m in zip(ahead, (20, 40, 60), strict=False)
            ],
        ],
        "last_topup_at": now.isoformat(),
    }
    feed = nowplaying.build_feed(now, state)
    (out / "nowplaying.json").write_text(json.dumps(feed, indent=2), encoding="utf-8")

    # The schedule + DJs feeds are cheap and REAL — copy them if they've been built.
    for path in (settings.schedule_feed_path, settings.djs_feed_path):
        if path.exists():
            shutil.copy(path, out / path.name)
    return out


class _CorsHandler(http.server.SimpleHTTPRequestHandler):
    """Static files, plus the headers the C7 box sends in production."""

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")  # dev only; prod pins it
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real",
        action="store_true",
        help="serve segments/ as-is instead of a synthesised now-playing feed",
    )
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args(argv)

    if args.real:
        directory = settings.nowplaying_feed_path.parent
        note = "REAL feeds (now-playing is empty until a scheduler top-up runs)"
    else:
        directory = build_demo_dir(datetime.now())
        note = (
            "DEMO now-playing (built from the real grid) + the real schedule/DJs feeds"
        )

    print(f"\n  {note}\n  serving {directory}\n")
    print(f"  http://127.0.0.1:{args.port}/nowplaying.json")
    print("\n  Point the site at it:")
    base = f"http://127.0.0.1:{args.port}"
    print(f"    cd web && NEXT_PUBLIC_FEEDS_BASE_URL={base} npm run dev")
    print("\n  Ctrl-C to stop.\n")

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        functools.partial(_CorsHandler, directory=str(directory)),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

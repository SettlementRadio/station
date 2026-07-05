"""Runnable check for the B5 program formats — generate one segment on demand.

    .venv/bin/python -m src.formats <news|talk|music|commercial|promo> [topic...]
    (needs `make seed`)

Makes live Anthropic + TTS calls. Prints the script, the audio path, and the
segment metadata so the human can hear and read the result.
"""

from __future__ import annotations

import sys
from datetime import datetime

from . import FORMATS, make_format_segment


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in FORMATS:
        print(f"usage: python -m src.formats <{'|'.join(FORMATS)}> [topic...]")
        return 2

    name = argv[0]
    topic = " ".join(argv[1:]) or None
    segment = make_format_segment(name, datetime.now().isoformat(), topic=topic)

    print(f"\n----- FORMAT: {name} -----")
    print(f"\n----- SCRIPT -----\n{segment.script or ''}")
    print(f"\n----- AUDIO -----\n{segment.audio_path}")
    print(f"\n----- META -----\n{segment.meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

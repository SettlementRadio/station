"""External-audit probe: run the REAL station pipeline text-only.

Real Anthropic calls (the thing under audit), mocked TTS (no audio, no cost),
world/airplay writes isolated in ONE rolled-back transaction so the operator's
world is untouched. Dumps every placed slot's script to a transcript file.

  python probe.py --start "2026-07-27T06:45" --hours 4 --out day.json
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, "/Users/pavel/station")

from src.config import settings  # noqa: E402
from src.production import mix as mix_mod  # noqa: E402
from src.providers import tts as tts_mod  # noqa: E402
from src.world import store  # noqa: E402

_SEC_PER_WORD = 0.42  # ~145 wpm — realistic spoken pace


class _MockTTS:
    def __init__(self) -> None:
        self.dur: dict[str, float] = {}
        self.calls = 0

    def synthesize(self, text, *, voice, emotion=None, out_path):
        self.calls += 1
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"\x00")
        self.dur[out_path] = max(2.0, len(text.split()) * _SEC_PER_WORD)
        return out_path

    def concat_audio(self, parts, out_path):
        return self._join(parts, out_path)

    def join_clips(self, paths, out_path):
        return self._join(paths, out_path)

    def _join(self, parts, out_path):
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_bytes(b"\x00")
        self.dur[out_path] = sum(self.dur.get(p, 30.0) for p in parts)
        return out_path

    def probe_duration(self, path):
        return self.dur.get(str(path), 30.0)


@contextlib.contextmanager
def isolated(tmp: Path) -> Iterator[_MockTTS]:
    cm = store.connect()
    conn = cm.__enter__()

    @contextlib.contextmanager
    def fake_connect() -> Iterator:
        yield conn

    tts = _MockTTS()
    segdir = tmp / "segments"
    segdir.mkdir(parents=True, exist_ok=True)
    with contextlib.ExitStack() as stack:
        p = stack.enter_context
        p(mock.patch.object(store, "connect", fake_connect))
        p(mock.patch.object(tts_mod, "synthesize", tts.synthesize))
        p(mock.patch.object(tts_mod, "concat_audio", tts.concat_audio))
        p(mock.patch.object(tts_mod, "probe_duration", tts.probe_duration))
        p(mock.patch.object(mix_mod, "join_clips", tts.join_clips))
        p(mock.patch.object(settings, "segments_dir", segdir))
        p(mock.patch.object(settings, "schedule_state_path", segdir / "schedule.json"))
        p(
            mock.patch.object(
                settings, "schedule_playlist_path", segdir / "playlist.txt"
            )
        )
        p(mock.patch.object(settings, "buffer_depth_hours", 0.75))
        p(mock.patch.object(settings, "llm_batch_enabled", False))
        p(mock.patch.object(settings, "production_bedded_programs", []))
        try:
            yield tts
        finally:
            conn.rollback()
            with contextlib.suppress(Exception):
                cm.__exit__(None, None, None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--hours", type=float, default=4.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    start = datetime.fromisoformat(a.start)
    tmp = Path(tempfile.mkdtemp(prefix="sr-probe-"))
    entries: dict[str, dict] = {}

    with isolated(tmp) as tts:
        from src import scheduler

        now = start
        end = start + timedelta(hours=a.hours)
        step = timedelta(minutes=30)
        while now <= end:
            print(f"--- top_up at {now:%H:%M} ---", file=sys.stderr, flush=True)
            for e in scheduler.top_up(now=now):
                key = e.get("id") or f"{e.get('audio_path')}@{e.get('air_time')}"
                entries[key] = e
            now += step

        # Attach the scripts from the sidecar JSONs the scheduler wrote.
        for e in entries.values():
            sid = e.get("id")
            side = tmp / "segments" / f"{sid}.json"
            if side.exists():
                d = json.loads(side.read_text())
                e["script"] = d.get("script")
                e["meta"] = d.get("meta")
        synths = tts.calls

    timeline = sorted(entries.values(), key=lambda e: e.get("air_time") or "")
    Path(a.out).write_text(json.dumps(timeline, indent=2))
    print(
        f"\n{len(timeline)} slots, {synths} synths -> {a.out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

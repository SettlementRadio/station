"""B6 — light nightly buffer: generate ~an hour of varied segments in one run.

The bridge to Phase C (PHASE_B_TASKS.md B6). NOT the real 24/7 scheduler — that,
the buffer-depth dial, the Batch API (50% off Claude), and the real content-safety
gate all land in Phase C with the VPS work. This is the mind proven at volume,
locally and free: one command that fills `segments/` with a varied, coherent,
in-universe block of audio.

How it stays varied without a scheduler: it cycles `settings.buffer_rotation` —
a mix of the three B5 formats — generating one segment per slot until their
`length_target_sec` values sum to roughly `settings.buffer_target_sec`. Because
`talk` is the two-DJ show and `news`/`music` are single-DJ, both DJs appear. Each
slot's `air_time` advances by the previous segment's length, so the block plays
back-to-back and the world's current events progress naturally across the hour.

Each segment is a proper `Segment` written to `segments/<id>.mp3` (by the format
templates) PLUS a `segments/<id>.json` metadata sidecar, and the whole run is
summarized in a `segments/buffer-<timestamp>.json` manifest — the on-disk shape a
Phase C scheduler will read to decide what airs when.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from .config import settings
from .formats import make_format_segment
from .logging_setup import get_logger
from .segment import Segment

log = get_logger(__name__)


def _segment_to_dict(seg: Segment) -> dict:
    """Serialize a Segment to a JSON-ready dict (dataclass fields + meta)."""
    return dataclasses.asdict(seg)


def _write_sidecar(seg: Segment) -> Path:
    """Write `segments/<id>.json` next to the audio so each segment self-describes."""
    path = settings.segments_dir / f"{seg.id}.json"
    path.write_text(json.dumps(_segment_to_dict(seg), indent=2), encoding="utf-8")
    return path


def _write_manifest(
    run_id: str, now: datetime, target_sec: int, segments: list[Segment]
) -> Path:
    """Write the run manifest — the ordered playlist a Phase C scheduler will read."""
    total = sum(s.length_target_sec for s in segments)
    # C2: also report the MEASURED total (segments are stamped post-render). The
    # length-target sum over-counts (see PHASE_B_ORIENTATION §5); the real scheduler
    # in src/scheduler.py times on this measured value, not the target.
    total_actual = sum(s.actual_duration_sec or 0.0 for s in segments)
    path = settings.segments_dir / f"{run_id}.json"
    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "start_now": now.isoformat(),
        "target_sec": target_sec,
        "total_length_target_sec": total,
        "total_actual_duration_sec": round(total_actual, 1),
        "count": len(segments),
        "segments": [_segment_to_dict(s) for s in segments],
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def build_buffer(
    now: datetime | None = None,
    *,
    target_sec: int | None = None,
    rotation: list[str] | None = None,
) -> list[Segment]:
    """Generate a varied buffer of ~`target_sec` of audio into `segments/`.

    Cycles `rotation` (B5 format names), generating one segment per slot until the
    accumulated `length_target_sec` reaches `target_sec` (or `buffer_max_segments`
    is hit). Each slot's `air_time` is advanced by the prior segment's length so the
    block is contiguous and current events progress across it. Writes a JSON sidecar
    per segment and a run manifest; returns the segments in air order.
    """
    now = now or datetime.now()
    target_sec = target_sec if target_sec is not None else settings.buffer_target_sec
    rotation = rotation or settings.buffer_rotation
    if not rotation:
        raise ValueError("buffer_rotation is empty — nothing to generate")

    run_id = f"buffer-{now:%Y%m%dT%H%M%S}"
    settings.segments_dir.mkdir(parents=True, exist_ok=True)
    log.info(
        "buffer_start",
        run_id=run_id,
        target_sec=target_sec,
        rotation=rotation,
        max_segments=settings.buffer_max_segments,
    )

    segments: list[Segment] = []
    air_cursor = now
    total = 0
    i = 0
    while total < target_sec and len(segments) < settings.buffer_max_segments:
        name = rotation[i % len(rotation)]
        log.info(
            "buffer_slot",
            run_id=run_id,
            index=i,
            format=name,
            air_time=air_cursor.isoformat(),
            total_so_far_sec=total,
        )
        # Generate against the advancing cursor so each segment's world context
        # (events near `now`) and its air_time reflect its slot in the hour.
        seg = make_format_segment(name, air_cursor.isoformat())
        _write_sidecar(seg)
        segments.append(seg)
        total += seg.length_target_sec
        air_cursor += timedelta(seconds=seg.length_target_sec)
        i += 1

    manifest_path = _write_manifest(run_id, now, target_sec, segments)
    log.info(
        "buffer_done",
        run_id=run_id,
        count=len(segments),
        total_length_target_sec=total,
        manifest=str(manifest_path),
    )
    return segments


def main(argv: list[str]) -> int:
    """CLI: generate the buffer. Optional arg overrides the target length in seconds.

    .venv/bin/python -m src.buffer [target_sec]   (needs `make seed`; Claude + TTS)
    """
    target_sec = None
    if argv:
        try:
            target_sec = int(argv[0])
        except ValueError:
            print(f"usage: python -m src.buffer [target_sec]; got {argv[0]!r}")
            return 2

    segments = build_buffer(target_sec=target_sec)

    print(f"\n----- BUFFER: {len(segments)} segments -----")
    total = 0
    for s in segments:
        total += s.length_target_sec
        print(
            f"  {s.air_time}  {s.format:6}  ~{s.length_target_sec:>4}s  "
            f"{s.id}  -> {s.audio_path}"
        )
    print(
        f"\n  ~{total}s of audio total (~{total / 60:.1f} min) "
        f"in {settings.segments_dir}/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

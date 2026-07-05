"""The Layer 4 mixing primitive — beds under speech, stings on clips (D7.1).

DECISION (written down per the D7.1 spec): mixing is **baked at render time**,
here, producing one ordinary mp3 per segment. The scheduler/playlist model is
untouched (a segment stays a single file, measured by `stamp_duration` on its
FINAL audio), and every mix is unit-checkable offline. The alternative — a live
ducked bed layer in `config/radio.liq` — is noted as a follow-on if baked beds
ever feel too static; nothing here precludes it.

DECISION (the one-home-for-mixing rule): ffmpeg now has exactly TWO cohesive
homes. Synthesis-side plumbing (transcode `_to_mp3`, `probe_duration`,
same-codec `concat_audio`) stays in `providers/tts.py`; *mixing* — anything that
layers or joins heterogeneous audio — lives ONLY here. Don't scatter ffmpeg
beyond these two modules.

The first-cut bed is a **constant low bed under speech** (the spec's blessed
simple option): the bed is looped to the speech length, dropped
`settings.production_bed_gain_db` below the untouched speech, faded in/out, and
mixed without renormalising (the speech stays at its original level). True
sidechain ducking (bed swells in pauses) is a follow-on tweak inside
`duck_bed_under`'s filter graph if the fixed level isn't lively enough on air.

Inputs are heterogeneous by nature (Suno beds/stings: 44.1 kHz stereo; Kokoro
speech: 24 kHz mono), so everything is normalised to one mix format and
re-encoded — never stream-copied (that's why sting joins live here and not on
`tts.concat_audio`, which requires one shared codec).

GUARANTEE: a mix failure can NEVER silence a segment. Every public function
returns the path to air — the mixed `out_path` on success, the ORIGINAL clean
speech path on any failure (logged at error). ffmpeg is a local, deterministic
subprocess, so unlike the network seams there is no retry — a failed filter
graph fails the same way twice; we log loudly and degrade instead.
"""

from __future__ import annotations

import os
import subprocess

from ..config import settings
from ..logging_setup import get_logger
from ..providers import tts

log = get_logger(__name__)

# The one mix format every input is conformed to before layering/joining —
# intrinsic to the mixer (matches the curated Suno masters; playout resamples
# happily). The output bitrate reuses the pipeline-wide `tts_mp3_bitrate` dial.
_MIX_SAMPLE_RATE = 44_100
_MIX_CHANNEL_LAYOUT = "stereo"
_MIX_FORMAT = (
    f"aformat=sample_rates={_MIX_SAMPLE_RATE}:channel_layouts={_MIX_CHANNEL_LAYOUT}"
)
# Mono input (every Kokoro render) upmixes with a FULL-GAIN pan, not aformat:
# swresample's default mono->stereo conversion applies the -3 dB pan law, which
# would make mixed speech audibly quieter than the same voice airing dry. The
# explicit `pan` copies the mono channel to L+R at unity — measured identical
# (max_volume -7.7 -> -7.6 dB) where aformat lost 3 dB.
_MIX_FORMAT_FROM_MONO = f"aresample={_MIX_SAMPLE_RATE},pan=stereo|c0=c0|c1=c0"


def _probe_channels(path: str) -> int:
    """Channel count of an audio file (ffprobe) — picks the right conform chain."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return int(result.stdout.strip())


def _conform(path: str) -> str:
    """The level-preserving conform-to-mix-format chain for one input file."""
    return _MIX_FORMAT_FROM_MONO if _probe_channels(path) == 1 else _MIX_FORMAT


def _run_ffmpeg(args: list[str], out_path: str) -> None:
    """Run one ffmpeg invocation writing `out_path`; raise on any failure.

    stderr is captured so a filter-graph error lands in OUR structured log (the
    caller catches + degrades) instead of vanishing into the console.
    """
    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({result.returncode}): {result.stderr.strip()}"
        )


def duck_bed_under(speech_path: str, bed_path: str, out_path: str) -> str:
    """Bake a bed under a speech clip at the configured duck level → one mp3.

    The bed loops to the speech length (`-stream_loop -1` + `amix
    duration=first`), sits `production_bed_gain_db` below the speech (which is
    mixed UNtouched — `normalize=0`), and fades in/out over
    `production_bed_fade_sec` so the join never pops. Returns `out_path` on
    success; on ANY failure logs at error and returns `speech_path` — the
    segment airs dry rather than dead.
    """
    try:
        duration = tts.probe_duration(speech_path)
        fade = settings.production_bed_fade_sec
        fade_out_start = max(duration - fade, 0.0)
        bed_chain = (
            f"[1:a]{_conform(bed_path)},volume={settings.production_bed_gain_db}dB,"
            f"afade=t=in:st=0:d={fade},"
            f"afade=t=out:st={fade_out_start}:d={fade}[bed]"
        )
        graph = (
            f"[0:a]{_conform(speech_path)}[speech];{bed_chain};"
            "[speech][bed]amix=inputs=2:duration=first:normalize=0[mix]"
        )
        _run_ffmpeg(
            [
                "-i",
                speech_path,
                "-stream_loop",
                "-1",
                "-i",
                bed_path,
                "-filter_complex",
                graph,
                "-map",
                "[mix]",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                settings.tts_mp3_bitrate,
                out_path,
            ],
            out_path,
        )
    except Exception as exc:
        log.error(
            "mix_bed_failed",
            speech=speech_path,
            bed=bed_path,
            error=str(exc),
        )
        return speech_path
    log.info(
        "mix_bed_done",
        out_path=out_path,
        bed=bed_path,
        gain_db=settings.production_bed_gain_db,
        seconds=round(duration, 2),
    )
    return out_path


def join_clips(paths: list[str], out_path: str) -> str:
    """Join N heterogeneous clips in order into one mp3 — a re-encoding concat.

    The production-side join (D7.4's intro → track → back-announce stitch): each
    input is conformed to the mix format first (level-preserving mono upmix),
    so a Kokoro speech clip and a Suno track concat cleanly — which is exactly
    what `tts.concat_audio` (same-codec stream copy) can NOT do. RAISES on any
    failure: the callers decide the degrade (a sting join falls back to the bare
    clip; a music segment without its track must FAIL the slot — airing intro +
    back-announce around a missing song would be worse than skipping).
    """
    if not paths:
        raise ValueError("join_clips: no clips to join")
    input_args: list[str] = []
    for p in paths:
        input_args += ["-i", p]
    conforms = ";".join(f"[{i}:a]{_conform(p)}[a{i}]" for i, p in enumerate(paths))
    heads = "".join(f"[a{i}]" for i in range(len(paths)))
    graph = f"{conforms};{heads}concat=n={len(paths)}:v=0:a=1[out]"
    _run_ffmpeg(
        [
            *input_args,
            "-filter_complex",
            graph,
            "-map",
            "[out]",
            "-codec:a",
            "libmp3lame",
            "-b:a",
            settings.tts_mp3_bitrate,
            out_path,
        ],
        out_path,
    )
    log.info("mix_join_done", parts=len(paths), out_path=out_path)
    return out_path


def attach_sting(
    clip_path: str, sting_path: str, out_path: str, *, position: str = "before"
) -> str:
    """Join a sting onto a clip (`position` "before" | "after") → one mp3.

    A two-clip `join_clips` with degrade semantics: returns `out_path` on
    success; on failure logs at error and returns `clip_path` — the clip airs
    without its punctuation rather than not at all.
    """
    if position not in ("before", "after"):
        raise ValueError(f"attach_sting: position {position!r} not 'before'|'after'")
    ordered = (
        [sting_path, clip_path] if position == "before" else [clip_path, sting_path]
    )
    try:
        join_clips(ordered, out_path)
    except Exception as exc:
        log.error(
            "mix_sting_failed",
            clip=clip_path,
            sting=sting_path,
            position=position,
            error=str(exc),
        )
        return clip_path
    log.info("mix_sting_done", out_path=out_path, sting=sting_path, position=position)
    return out_path

"""Seam #1b — the ONLY module that imports a TTS vendor SDK.

Every speech-synthesis call goes through `synthesize(...)`. Callers pass a
*logical* voice name (e.g. "vell_night"); this module maps it to the current
vendor's voice id and renders audio. The implementation is selected by the
TTS_PROVIDER env var, so swapping ElevenLabs for self-hosted Kokoro/Orpheus
later means editing this one file + env. See docs/ARCHITECTURE.md "Seam #1".

ffmpeg note (D7.1): this module owns the SYNTHESIS-side ffmpeg only — transcode
(`_to_mp3`), measurement (`probe_duration`), and the same-codec turn join
(`concat_audio`). Production *mixing* (beds under speech, stings, anything
layering heterogeneous audio) lives ONLY in `src/production/mix.py` — two
cohesive homes, nothing scattered.
"""

from __future__ import annotations

import os

from ..config import settings
from ..logging_setup import get_logger
from ..retry import call_with_retry

log = get_logger(__name__)

# Logical voice name -> vendor voice id. This is the seam's own domain data (its
# whole job is to map a logical name to a vendor id), so the registries stay
# here; only tunable *config* (model names, formats, rates) moved to settings.
#   vell_night -> "Adam" (warm, low, unhurried) for Vell, matching his card and
#                 the Kokoro `bm_george` / `say` "Daniel" stand-ins.
#   dj_two     -> "Rachel" (American female) for Wren, the bright first-light
#                 host — the sibling of the Kokoro `af_heart` preset, kept
#                 distinct from Vell so a two-voice talk segment reads as two
#                 people. Rachel leans calm; swap for a brighter prebuilt (e.g.
#                 "Elli" MF3mGyEYCl7XYWbV9V6O) after a listen if Wren feels flat.
# PLACEHOLDERS (D-cast): the expanded cast (90-cast.md) defines 10 logical voices,
# but only two real prebuilts are chosen so far. Until each DJ gets a distinct
# voice (the D9 voice pass), the extra logical names alias onto the two real
# presets — male-leaning cards onto "Adam", bright/female-leaning onto "Rachel" —
# so every card resolves and the cast can be voiced. Repoint these to real ids
# one at a time as voices are picked; the logical names never change.
_ELEVENLABS_VOICE_IDS = {
    "vell_night": "pNInz6obpgDQGcFmaJgB",  # ElevenLabs prebuilt "Adam"
    "dj_two": "21m00Tcm4TlvDq8ikWAM",  # ElevenLabs prebuilt "Rachel"
    # placeholders aliasing onto the two real presets:
    "wren_dawn": "21m00Tcm4TlvDq8ikWAM",
    "joss_bridge": "pNInz6obpgDQGcFmaJgB",
    "kael_sports": "21m00Tcm4TlvDq8ikWAM",
    "mira_culture": "21m00Tcm4TlvDq8ikWAM",
    "thorn_news": "pNInz6obpgDQGcFmaJgB",
    "sera_field": "21m00Tcm4TlvDq8ikWAM",
    "archivist_deep": "pNInz6obpgDQGcFmaJgB",
    "orin_music": "pNInz6obpgDQGcFmaJgB",
    "zhe_observer": "21m00Tcm4TlvDq8ikWAM",
}

# macOS `say` voice names (list them with: say -v '?'). "Daniel" is a warm
# British male stand-in for Vell; "Samantha" a bright American female for Wren —
# both serviceable while testing, and kept distinct so a two-DJ talk segment
# reads as two people. Apple's free downloadable "Enhanced"/"Premium" voices
# (System Settings → Accessibility → Spoken Content → System Voice) sound far
# more natural; drop one in here once installed. This backend is offline, free,
# and unlimited — for testing the loop, not the DJs' final voices.
_SAY_VOICES = {
    "vell_night": "Daniel",
    "dj_two": "Samantha",
    # placeholders aliasing onto the two real presets (see _ELEVENLABS note):
    "wren_dawn": "Samantha",
    "joss_bridge": "Daniel",
    "kael_sports": "Samantha",
    "mira_culture": "Samantha",
    "thorn_news": "Daniel",
    "sera_field": "Samantha",
    "archivist_deep": "Daniel",
    "orin_music": "Daniel",
    "zhe_observer": "Samantha",
}

# Kokoro (self-hosted, open-weight, free/unlimited) voice presets. List the full
# set with the package's `KPipeline.list_voices()` or see the Kokoro-82M model
# card. The first letter encodes language (a=American, b=British English), the
# second gender (m/f) — we derive the pipeline's lang_code from it below.
#   vell_night -> a British male (warm, low), matching Vell's card + the `say`
#                 "Daniel" stand-in.
#   dj_two     -> a distinct American voice RESERVED for the second DJ, who is
#                 defined in B1/B4. Repoint/rename once that card exists; kept
#                 deliberately different from Vell so a two-voice talk segment
#                 reads as two people.
_KOKORO_VOICES = {
    "vell_night": "bm_george",
    "dj_two": "af_heart",
    # placeholders aliasing onto the two real presets (see _ELEVENLABS note):
    "wren_dawn": "af_heart",
    "joss_bridge": "bm_george",
    "kael_sports": "af_heart",
    "mira_culture": "af_heart",
    "thorn_news": "bm_george",
    "sera_field": "af_heart",
    "archivist_deep": "bm_george",
    "orin_music": "bm_george",
    "zhe_observer": "af_heart",
}

# Kokoro render settings (sample rate, speed, repo id) now live in `settings`;
# length is tuned via the writer's word count (B0), not by slowing the voice.

# KPipeline loads model weights on construction (slow, ~seconds), so cache one
# per language code across calls in a process (e.g. a buffer run voicing many
# segments). Keyed by lang_code ("a"/"b").
_kokoro_pipelines: dict[str, object] = {}


def synthesize(
    text: str,
    *,
    voice: str,
    emotion: str | None = None,
    out_path: str,
) -> str:
    """Render `text` to an audio file at `out_path`; return the path.

    Args:
        text: the script to speak.
        voice: a *logical* voice name from the registry (NOT a vendor id).
        emotion: optional emotional hint (reserved; not yet wired to a vendor
            knob — kept in the signature so later providers can use it).
        out_path: where to write the audio file.

    The implementation is chosen by `settings.tts_provider` (default "kokoro").
    """
    provider = settings.tts_provider.strip().lower()
    log.info("tts_synthesize_start", provider=provider, voice=voice, chars=len(text))

    backends = {
        "kokoro": _synthesize_kokoro,
        "elevenlabs": _synthesize_elevenlabs,
        "say": _synthesize_say,
    }
    backend = backends.get(provider)
    if backend is None:
        if provider == "orpheus":
            # --- FUTURE: self-hosted TTS stub ------------------------------
            # Implement `_synthesize_orpheus(...)` rendering to out_path via the
            # same logical voice registry, then add it to `backends` above.
            # Nothing outside this module should need to change.
            raise NotImplementedError(
                f"TTS_PROVIDER={provider!r} is a planned self-hosted backend; "
                "not implemented yet. Use TTS_PROVIDER=kokoro for local voice."
            )
        raise ValueError(
            f"unknown TTS_PROVIDER {provider!r}; expected "
            "'kokoro' (default), 'elevenlabs', 'say' (or future 'orpheus')"
        )

    # Bounded retry: a transient render/transcode failure retries rather than
    # silently producing nothing; an exhausted call fails loudly into the logs.
    result = call_with_retry(
        f"tts.synthesize[{provider}]",
        lambda: backend(text, voice=voice, emotion=emotion, out_path=out_path),
    )
    log.info("tts_synthesize_done", provider=provider, voice=voice, out_path=result)
    return result


def _synthesize_elevenlabs(
    text: str,
    *,
    voice: str,
    emotion: str | None,
    out_path: str,
) -> str:
    """ElevenLabs implementation of `synthesize`."""
    from elevenlabs.client import ElevenLabs

    try:
        voice_id = _ELEVENLABS_VOICE_IDS[voice]
    except KeyError:
        raise ValueError(
            f"unknown logical voice {voice!r}; expected one of "
            f"{sorted(_ELEVENLABS_VOICE_IDS)}"
        ) from None

    client = ElevenLabs(api_key=settings.elevenlabs_api_key or None)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=settings.tts_elevenlabs_model,
        text=text,
        output_format=settings.tts_elevenlabs_output_format,
    )

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    return out_path


def _synthesize_say(
    text: str,
    *,
    voice: str,
    emotion: str | None,
    out_path: str,
) -> str:
    """macOS built-in `say` implementation — offline, free, no quota.

    For testing the loop without spending TTS credits. `say` writes AIFF, so we
    render to a temp file and transcode to `out_path` (mp3) with ffmpeg, leaving
    the rest of the pipeline (which expects mp3) untouched. `emotion` is ignored
    (`say` has no such knob).
    """
    import subprocess
    import tempfile

    try:
        say_voice = _SAY_VOICES[voice]
    except KeyError:
        raise ValueError(
            f"unknown logical voice {voice!r}; expected one of {sorted(_SAY_VOICES)}"
        ) from None

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = tmp.name
    try:
        subprocess.run(["say", "-v", say_voice, "-o", aiff_path, text], check=True)
        _to_mp3(aiff_path, out_path)
    finally:
        if os.path.exists(aiff_path):
            os.remove(aiff_path)
    return out_path


def _kokoro_pipeline(lang_code: str):
    """Return a cached Kokoro `KPipeline` for `lang_code` ('a'/'b'…).

    Construction loads the 82M model (downloaded from HuggingFace on first use,
    then cached locally by `huggingface_hub`), so we build one per language and
    reuse it across calls within a process.
    """
    pipeline = _kokoro_pipelines.get(lang_code)
    if pipeline is None:
        from kokoro import KPipeline

        pipeline = KPipeline(lang_code=lang_code, repo_id=settings.tts_kokoro_repo_id)
        _kokoro_pipelines[lang_code] = pipeline
    return pipeline


def _synthesize_kokoro(
    text: str,
    *,
    voice: str,
    emotion: str | None,
    out_path: str,
) -> str:
    """Kokoro implementation — self-hosted, open-weight, free, unlimited.

    The default Phase B backend: local neural voice with no API quota, so the
    mind can be iterated at volume (B0). Kokoro yields 24 kHz float chunks; we
    concatenate them to a temp WAV and transcode to mp3 via the shared
    `_to_mp3()` helper, leaving the rest of the pipeline (which expects mp3)
    untouched. `emotion` is accepted but ignored — Kokoro has no such knob; the
    signature is kept so other providers can use it.
    """
    import tempfile

    import numpy as np
    import soundfile as sf

    try:
        kokoro_voice = _KOKORO_VOICES[voice]
    except KeyError:
        raise ValueError(
            f"unknown logical voice {voice!r}; expected one of {sorted(_KOKORO_VOICES)}"
        ) from None

    # Voice id encodes language in its first char (a=American, b=British). The
    # pipeline's lang_code must match for correct grapheme-to-phoneme handling.
    lang_code = kokoro_voice[0]
    pipeline = _kokoro_pipeline(lang_code)

    # The pipeline splits long text and yields (graphemes, phonemes, audio) per
    # chunk; stitch the audio back into one clip.
    chunks = [
        audio
        for _gs, _ps, audio in pipeline(
            text, voice=kokoro_voice, speed=settings.tts_kokoro_speed
        )
    ]
    if not chunks:
        raise RuntimeError(f"Kokoro produced no audio for voice {voice!r}")
    audio = np.concatenate(chunks)

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        sf.write(wav_path, audio, settings.tts_kokoro_sample_rate)
        _to_mp3(wav_path, out_path)
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
    return out_path


def _to_mp3(src_path: str, out_path: str) -> str:
    """Transcode any ffmpeg-readable audio file to a 128k mp3 at `out_path`.

    Shared by the non-mp3 backends (e.g. `say`, and future local-neural ones
    like Kokoro that emit WAV) so the pipeline always lands an mp3 in segments/.
    """
    import subprocess

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            src_path,
            "-codec:a",
            "libmp3lame",
            "-b:a",
            settings.tts_mp3_bitrate,
            out_path,
        ],
        check=True,
    )
    return out_path


def probe_duration(path: str) -> float:
    """Measure an audio file's real duration in seconds via ffprobe.

    C2 — honest length accounting. ffprobe ships with ffmpeg, which lives only in
    this seam (alongside `_to_mp3`/`concat_audio`), so the duration probe lives here
    too. The scheduler schedules on this measured value, not the writer's word-count
    target. Raises (subprocess error / unparseable output) if the file can't be read
    — callers decide whether a missing duration is fatal.
    """
    import subprocess

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    seconds = float(result.stdout.strip())
    log.info("tts_probe_duration", path=path, seconds=round(seconds, 2))
    return seconds


def concat_audio(parts: list[str], out_path: str) -> str:
    """Concatenate the per-turn mp3s of a multi-voice segment into one at out_path.

    Used by the B4 conversation orchestrator, which voices each DJ turn separately
    (so each gets its own logical voice) and then stitches the turns back into a
    single talk `Segment`. ffmpeg lives only in this module, so the join lives here
    too, next to `_to_mp3`. The turns are all rendered by the same backend, so they
    share a codec and can be stream-copied (`-c copy`) via the concat demuxer — no
    re-encode, no quality loss.
    """
    import subprocess
    import tempfile

    if not parts:
        raise ValueError("concat_audio: no parts to concatenate")

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    # The concat demuxer reads a list file of `file '<path>'` lines.
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        list_path = f.name
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_path,
                "-c",
                "copy",
                out_path,
            ],
            check=True,
        )
    finally:
        os.remove(list_path)
    log.info("tts_concat_done", parts=len(parts), out_path=out_path)
    return out_path

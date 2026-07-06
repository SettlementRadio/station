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
from . import lexicon

log = get_logger(__name__)

# Logical voice name -> vendor voice id, PER ENGINE — DATA as of D9.2:
# config/voices.yaml (settings.tts_voices_path) is the human-edited registry,
# so adding a DJ never means editing this module (author the card in the bible,
# add one YAML entry, `make seed-canon`). Mapping a logical name to a vendor id
# remains this seam's job — callers still speak only logical names — the
# mapping itself just moved from three hardcoded dicts (whose 9 D-cast entries
# were PLACEHOLDER aliases onto two real presets) to per-engine data with a
# DISTINCT preset per DJ. Cached per (path, mtime) like the lexicon, so a
# long-running scheduler picks up an edit while a buffer run parses once.
#
# FAIL LOUD, never a silent wrong voice: a missing/empty registry file, an
# unknown logical voice, or a voice with no mapping for the active engine all
# raise. `make seed-canon` pre-validates every cast card's voice against
# `known_voices()` (world/seed.py), so a bad mapping is caught at seed time,
# not at a 3 a.m. render.
_voices_cache: tuple[tuple[str, float], dict[str, dict[str, str]]] | None = None


def _voice_registry() -> dict[str, dict[str, str]]:
    """Load (and cache) the voice registry: {logical_voice: {engine: vendor_id}}."""
    global _voices_cache
    path = settings.tts_voices_path
    try:
        key = (str(path), path.stat().st_mtime)
    except OSError as exc:
        raise RuntimeError(
            f"voice registry not found at {path} (settings.tts_voices_path) — "
            "the station cannot voice anything without it"
        ) from exc

    if _voices_cache is not None and _voices_cache[0] == key:
        return _voices_cache[1]

    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    registry = {
        str(logical): {str(eng): str(vid) for eng, vid in (engines or {}).items()}
        for logical, engines in raw.items()
    }
    if not registry:
        raise RuntimeError(f"voice registry at {path} is empty — no voice can render")
    _voices_cache = (key, registry)
    log.debug("tts_voices_loaded", path=str(path), voices=len(registry))
    return registry


def known_voices() -> set[str]:
    """The logical voice names the registry defines (seed-time validation hook)."""
    return set(_voice_registry())


def _vendor_voice(voice: str, provider: str) -> str:
    """Resolve a logical voice to `provider`'s vendor id; fail loud otherwise."""
    registry = _voice_registry()
    try:
        engines = registry[voice]
    except KeyError:
        raise ValueError(
            f"unknown logical voice {voice!r}; expected one of {sorted(registry)} "
            f"(registry: {settings.tts_voices_path})"
        ) from None
    try:
        return engines[provider]
    except KeyError:
        raise ValueError(
            f"logical voice {voice!r} has no {provider!r} mapping in "
            f"{settings.tts_voices_path}"
        ) from None


# --- Emotion (D9.0) -----------------------------------------------------------
# The logical emotion vocabulary — the small named set the writers' room may
# stamp on a turn or segment ("Vell, somber here"). Like the voice registries,
# this is the seam's own domain data: callers speak ONLY these logical names;
# how an engine realises one (or can't) stays behind the seam.
#   * ElevenLabs — mapped to real expressiveness controls on the TTS request
#     (`VoiceSettings`, SDK 2.x): `stability` (lower = more variable/expressive
#     delivery), `style` (higher = more style exaggeration), `speed` (pace).
#     Fields left unset keep the voice's own stored defaults.
#   * Kokoro / `say` — NO emotion knob exists (PHASE_C_ORIENTATION §8): the
#     value is accepted and ignored, exactly as before D9.0. Emotion is
#     therefore only AUDIBLE on the flagship path — and which engine ships is
#     the C6 launch-voice decision (docs/PHASE_C_TASKS.md).
# The numbers are a conservative starting tune (retune by ear on the flagship
# engine, per DJ if needed); the operator-facing dial is the DEFAULT emotion
# (`settings.tts_emotion_default`), not these curves.
_ELEVENLABS_EMOTIONS: dict[str, dict[str, float]] = {
    "warm": {"stability": 0.45, "style": 0.30, "speed": 0.97},
    "bright": {"stability": 0.35, "style": 0.45, "speed": 1.03},
    "wry": {"stability": 0.50, "style": 0.40, "speed": 1.00},
    "somber": {"stability": 0.65, "style": 0.15, "speed": 0.92},
    "urgent": {"stability": 0.25, "style": 0.55, "speed": 1.06},
}

# The engine-neutral vocabulary callers (writers' room, formats) may use.
EMOTIONS: frozenset[str] = frozenset(_ELEVENLABS_EMOTIONS)


def resolve_emotion(emotion: str | None) -> str | None:
    """Normalise + validate a logical emotion; fall back to the settings default.

    Returns a name from `EMOTIONS`, or None for "engine default" (no
    expressiveness override). An unknown name is logged and dropped — a bad tag
    must never fail a render mid-buffer.
    """
    value = (emotion or settings.tts_emotion_default or "").strip().lower()
    if not value:
        return None
    if value not in EMOTIONS:
        log.warning("tts_unknown_emotion", emotion=value, known=sorted(EMOTIONS))
        return None
    return value


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
        emotion: optional logical emotion from `EMOTIONS` (D9.0). Falls back to
            `settings.tts_emotion_default`; shapes the flagship (ElevenLabs)
            render via its expressiveness controls, and is accepted-but-ignored
            on Kokoro/`say` (no such knob — audibility is the C6 decision).
        out_path: where to write the audio file.

    The implementation is chosen by `settings.tts_provider` (default "kokoro").
    D9.1: the pronunciation lexicon (config/pronunciation.yaml, via
    `lexicon.apply_lexicon`) is applied to `text` here, per engine, so the
    world's invented names are spoken right on whichever backend renders.
    """
    provider = settings.tts_provider.strip().lower()
    emotion = resolve_emotion(emotion)
    text = lexicon.apply_lexicon(text, provider)
    log.info(
        "tts_synthesize_start",
        provider=provider,
        voice=voice,
        emotion=emotion,
        chars=len(text),
    )

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
    """ElevenLabs implementation of `synthesize`.

    D9.0: a validated logical `emotion` (see `resolve_emotion`, run by the
    dispatcher) maps here — and ONLY here — to the vendor's expressiveness
    controls (`VoiceSettings`); None sends no override, keeping the voice's own
    stored defaults.
    """
    from elevenlabs.client import ElevenLabs
    from elevenlabs.types import VoiceSettings

    voice_id = _vendor_voice(voice, "elevenlabs")

    voice_settings = VoiceSettings(**_ELEVENLABS_EMOTIONS[emotion]) if emotion else None

    client = ElevenLabs(api_key=settings.elevenlabs_api_key or None)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=settings.tts_elevenlabs_model,
        text=text,
        output_format=settings.tts_elevenlabs_output_format,
        voice_settings=voice_settings,
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

    say_voice = _vendor_voice(voice, "say")

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

    kokoro_voice = _vendor_voice(voice, "kokoro")

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

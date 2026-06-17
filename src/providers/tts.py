"""Seam #1b — the ONLY module that imports a TTS vendor SDK.

Every speech-synthesis call goes through `synthesize(...)`. Callers pass a
*logical* voice name (e.g. "vell_night"); this module maps it to the current
vendor's voice id and renders audio. The implementation is selected by the
TTS_PROVIDER env var, so swapping ElevenLabs for self-hosted Kokoro/Orpheus
later means editing this one file + env. See docs/ARCHITECTURE.md "Seam #1".
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # pull ELEVENLABS_API_KEY / TTS_PROVIDER from .env if present

# Logical voice name -> vendor voice id. Keeps the rest of the codebase free of
# vendor ids. The DJ "Vell" (warm, low, unhurried) maps to ElevenLabs' "Adam".
# Rename / repoint freely; this is the only place a vendor id appears.
_ELEVENLABS_VOICE_IDS = {
    "vell_night": "pNInz6obpgDQGcFmaJgB",  # ElevenLabs prebuilt "Adam"
}

# ElevenLabs render settings. mp3 is convenient for local playout in Phase A.
_ELEVENLABS_MODEL = "eleven_multilingual_v2"
_ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"

# macOS `say` voice names (list them with: say -v '?'). "Daniel" is a warm
# British male — a serviceable stand-in for Vell while testing. Apple's free
# downloadable "Enhanced"/"Premium" voices (System Settings → Accessibility →
# Spoken Content → System Voice) sound far more natural; drop one in here once
# installed. This backend is offline, free, and unlimited — for testing the
# loop, not Vell's final voice.
_SAY_VOICES = {
    "vell_night": "Daniel",
}


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

    The implementation is chosen by TTS_PROVIDER (default "elevenlabs").
    """
    provider = os.getenv("TTS_PROVIDER", "elevenlabs").strip().lower()
    if provider == "elevenlabs":
        return _synthesize_elevenlabs(
            text, voice=voice, emotion=emotion, out_path=out_path
        )
    if provider == "say":
        return _synthesize_say(
            text, voice=voice, emotion=emotion, out_path=out_path
        )
    if provider in ("kokoro", "orpheus"):
        # --- FUTURE: self-hosted TTS stub ----------------------------------
        # Implement a `_synthesize_<provider>(...)` that renders to out_path
        # using the same logical voice registry, then dispatch to it here.
        # Nothing outside this module should need to change.
        raise NotImplementedError(
            f"TTS_PROVIDER={provider!r} is a planned self-hosted backend; "
            "not implemented yet. Use TTS_PROVIDER=elevenlabs for Phase A."
        )
    raise ValueError(
        f"unknown TTS_PROVIDER {provider!r}; expected "
        "'elevenlabs' (or future 'kokoro' / 'orpheus')"
    )


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

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=_ELEVENLABS_MODEL,
        text=text,
        output_format=_ELEVENLABS_OUTPUT_FORMAT,
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
            f"unknown logical voice {voice!r}; expected one of "
            f"{sorted(_SAY_VOICES)}"
        ) from None

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff_path = tmp.name
    try:
        subprocess.run(
            ["say", "-v", say_voice, "-o", aiff_path, text], check=True
        )
        _to_mp3(aiff_path, out_path)
    finally:
        if os.path.exists(aiff_path):
            os.remove(aiff_path)
    return out_path


def _to_mp3(src_path: str, out_path: str) -> str:
    """Transcode any ffmpeg-readable audio file to a 128k mp3 at `out_path`.

    Shared by the non-mp3 backends (e.g. `say`, and future local-neural ones
    like Kokoro that emit WAV) so the pipeline always lands an mp3 in segments/.
    """
    import subprocess

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", src_path,
            "-codec:a", "libmp3lame", "-b:a", "128k",
            out_path,
        ],
        check=True,
    )
    return out_path

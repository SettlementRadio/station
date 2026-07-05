"""Tests for the DB/LLM-free logic in the B5 program formats (src/formats/).

The creative steps need Claude + TTS, so they're exercised by `make format`. Here
we pin the brittle, pure bits a silent bug would corrupt: the music song-slot split
(get it wrong and the marker is spoken, or the back-announce is lost) and the format
registry (every name resolves to a builder + the cast it needs).
"""

from __future__ import annotations

from src import formats
from src.formats import music


def test_split_on_marker_separates_intro_and_back_announce():
    script = "Here's a slow one.\n[SONG]\nAnd that was the piece."
    parts = music.split_on_marker(script, "[SONG]")
    assert parts == ["Here's a slow one.", "And that was the piece."]


def test_split_on_marker_tolerates_bold_and_whitespace():
    script = "Intro line.\n  **[SONG]**  \nBack-announce line."
    parts = music.split_on_marker(script, "[SONG]")
    assert parts == ["Intro line.", "Back-announce line."]


def test_split_on_marker_without_marker_is_one_part():
    # No marker: the whole script is a single spoken part (still renders).
    assert music.split_on_marker("Just one block of talk.", "[SONG]") == [
        "Just one block of talk."
    ]


def test_registry_has_the_three_formats():
    assert set(formats.FORMATS) == {"news", "talk", "music"}
    for spec in formats.FORMATS.values():
        assert callable(spec.build)
        assert list(spec.speaker_ids())  # resolves to at least one cast id


def test_talk_needs_two_speakers():
    # talk wraps the two-DJ conversation, so it must request >= 2 cast ids.
    assert len(formats.FORMATS["talk"].speaker_ids()) >= 2


# --- D7.4: the music builder — stitch order + lore in the prompt ---------------


def _music_ctx():
    from src.world.context import AssembledContext
    from src.world.store import CastMember

    return AssembledContext(
        cached_context="",
        dynamic="",
        speakers=[
            CastMember(
                id="vell",
                name="Vell",
                card_text="night host",
                logical_voice="vell_night",
            )
        ],
    )


def _fixture_track():
    from src.world.store import Track

    return Track(
        id="halden-vre__the-slow-star",
        title="The Slow Star",
        in_world_artist="Halden Vre",
        mood="melancholy",
        audio_path="assets/music/halden-vre__the-slow-star.mp3",
        album="A Window in the Dark",
        era="age-of-relays",
        in_world_year=2611,
        story_blurb="Written on a one-keeper station months from the nearest light.",
        duration_sec=200.0,
    )


def test_music_stitches_intro_bumper_track_back_in_order(
    monkeypatch, tmp_path, audio_factory
):
    from datetime import datetime

    from src.config import settings
    from src.safety import SafetyResult

    track = _fixture_track()
    track_file = audio_factory(seconds=1.0)
    bumper_file = audio_factory(seconds=0.5)
    captured: dict = {}
    joined: dict = {}

    monkeypatch.setattr(settings, "segments_dir", tmp_path)
    monkeypatch.setattr(music.selector, "choose_track", lambda now: track)
    monkeypatch.setattr(music.media, "track_audio_path", lambda t: track_file)
    monkeypatch.setattr(music.media, "sting", lambda name: bumper_file)

    def fake_generate(prompt, *, system, model, cached_context, max_tokens):
        captured["system"] = system
        return "A song about one window.\n[SONG]\nThat was The Slow Star."

    monkeypatch.setattr(music.llm, "generate", fake_generate)
    monkeypatch.setattr(
        music,
        "generate_safe",
        lambda produce, **kw: (produce(), SafetyResult(True, "OK", "disabled")),
    )
    monkeypatch.setattr(
        music.tts,
        "synthesize",
        lambda text, *, voice, out_path: open(out_path, "wb").write(b"\x00"),
    )

    def fake_join(paths, out_path):
        joined["paths"] = list(paths)
        open(out_path, "wb").write(b"\x00")
        return out_path

    monkeypatch.setattr(music.mix, "join_clips", fake_join)

    seg = music.music(datetime(2026, 7, 5, 3, 0), _music_ctx())

    # The stitch order: spoken intro -> C10 bumper -> the track -> back-announce.
    order = joined["paths"]
    assert order[0].endswith("intro.mp3")
    assert order[1] == str(bumper_file)
    assert order[2] == str(track_file)
    assert order[3].endswith("back.mp3")

    # The prompt carries the track's LORE — the DJ tells its story, not a made-up one.
    system = captured["system"]
    for needle in (
        "The Slow Star",
        "Halden Vre",
        "age-of-relays",
        "A Window in the Dark",
        "one-keeper station",
    ):
        assert needle in system

    # The segment carries the track for freshness (id/artist) + now-playing (lore).
    assert seg.meta["track_id"] == track.id
    assert seg.meta["track_artist"] == "Halden Vre"
    assert seg.meta["track"]["title"] == "The Slow Star"
    # Metadata target includes the track's known length (honest-ish; measured wins).
    assert seg.length_target_sec == settings.format_music_length_target_sec + 200


def test_music_without_a_playable_track_falls_back_to_evergreen(monkeypatch):
    from datetime import datetime

    from src.segment import Segment

    sentinel = Segment(id="evergreen-x", format="music", length_target_sec=90)
    monkeypatch.setattr(music.selector, "choose_track", lambda now: None)
    monkeypatch.setattr(
        music.evergreen, "evergreen_segment", lambda now, **kw: sentinel
    )
    seg = music.music(datetime(2026, 7, 5, 3, 0), _music_ctx())
    assert seg is sentinel  # never a silent slot — the evergreen stands in

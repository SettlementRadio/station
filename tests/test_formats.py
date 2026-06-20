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

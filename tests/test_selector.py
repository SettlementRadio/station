"""Tests for D7.4 — the music selection policy (src/production/selector.py).

The selector is the pure "what to play" brain, so these tests are pure too: no
DB, no files. Each weighted input is pinned one at a time (jitter zeroed so the
policy alone decides), plus the determinism contract: same tracks + inputs +
seed → same pick.
"""

from __future__ import annotations

from src.config import settings
from src.production import selector
from src.world.store import Track


def _track(id: str, *, mood: str, artist: str = "A", era: str = "now", tags=()):
    return Track(
        id=id,
        title=id,
        in_world_artist=artist,
        mood=mood,
        audio_path=f"assets/music/{id}.mp3",
        era=era,
        tags=list(tags),
    )


def _pick(tracks, monkeypatch, **inputs) -> str:
    """Run the policy with jitter off so the weights alone decide; return the id."""
    monkeypatch.setattr(settings, "music_select_jitter", 0.0)
    chosen = selector.select_track(tracks, selector.SelectionInputs(**inputs), seed=42)
    return chosen.id


def test_daypart_mood_is_honoured(monkeypatch):
    tracks = [
        _track("bright-one", mood="joyful"),
        _track("night-one", mood="melancholy"),
    ]
    assert _pick(tracks, monkeypatch, daypart="deep night") == "night-one"
    assert _pick(tracks, monkeypatch, daypart="daytime") == "bright-one"


def test_world_tone_tilts_the_pick(monkeypatch):
    tracks = [_track("somber-one", mood="solemn"), _track("upbeat-one", mood="joyful")]
    assert _pick(tracks, monkeypatch, world_tone="somber") == "somber-one"
    assert _pick(tracks, monkeypatch, world_tone="upbeat") == "upbeat-one"


def test_recent_track_is_avoided(monkeypatch):
    tracks = [_track("played", mood="mellow"), _track("fresh", mood="mellow")]
    got = _pick(
        tracks,
        monkeypatch,
        daypart="deep night",
        recent_track_ids=frozenset({"played"}),
    )
    assert got == "fresh"


def test_song_key_strips_only_a_take_suffix():
    assert selector.song_key("asha-ko__carbon-heart_1") == "asha-ko__carbon-heart"
    assert selector.song_key("asha-ko__carbon-heart") == "asha-ko__carbon-heart"
    # A hyphenated number in the title is part of the song, not a take.
    assert selector.song_key("harmony-tract__the-ballad-of-dock-12") == (
        "harmony-tract__the-ballad-of-dock-12"
    )


def test_alternate_take_counts_as_its_main_version(monkeypatch):
    # The main version just aired -> its _1 take is penalised too (recent ids
    # arrive as song_keys, the shape _recent_spins produces).
    tracks = [_track("song_1", mood="mellow"), _track("other", mood="mellow")]
    got = _pick(tracks, monkeypatch, recent_track_ids=frozenset({"song"}))
    assert got == "other"
    # And the reverse: an aired take shields the main version.
    tracks = [_track("song", mood="mellow"), _track("other", mood="mellow")]
    got = _pick(
        tracks,
        monkeypatch,
        recent_track_ids=frozenset({selector.song_key("song_1")}),
    )
    assert got == "other"


def test_recent_artist_is_avoided(monkeypatch):
    tracks = [
        _track("by-vre", mood="mellow", artist="Halden Vre"),
        _track("by-mar", mood="mellow", artist="Ysolde Mar"),
    ]
    got = _pick(tracks, monkeypatch, recent_artists=frozenset({"Halden Vre"}))
    assert got == "by-mar"


def test_era_spread_varies_off_the_last_spin(monkeypatch):
    tracks = [
        _track("same-era", mood="mellow", era="age-of-relays"),
        _track("other-era", mood="mellow", era="first-expansion"),
    ]
    assert _pick(tracks, monkeypatch, last_era="age-of-relays") == "other-era"


def test_featured_artist_from_the_world_wins(monkeypatch):
    tracks = [
        _track("plain", mood="mellow"),
        _track("newsy", mood="mellow", artist="B"),
    ]
    got = _pick(tracks, monkeypatch, featured_artists=frozenset({"B"}))
    assert got == "newsy"


def test_human_pin_tag_wins(monkeypatch):
    tracks = [
        _track("plain", mood="mellow"),
        _track("pinned", mood="mellow", tags=("pinned",)),
    ]
    assert _pick(tracks, monkeypatch) == "pinned"


def test_selection_is_deterministic_given_inputs_and_seed():
    # Jitter ON (the default): the seeded rng must still make the pick repeatable.
    tracks = [_track(f"t{i}", mood="mellow") for i in range(8)]
    inputs = selector.SelectionInputs(daypart="deep night")
    first = selector.select_track(tracks, inputs, seed=1234)
    second = selector.select_track(tracks, inputs, seed=1234)
    assert first.id == second.id


def test_empty_catalogue_returns_none():
    assert selector.select_track([], selector.SelectionInputs(), seed=1) is None


def test_world_tone_classification():
    assert selector.world_tone(["a mourning memorial after the accident"]) == "somber"
    assert selector.world_tone(["the harvest festival celebration begins"]) == "upbeat"
    assert selector.world_tone(["a quiet week across the relays"]) == "neutral"
    assert selector.world_tone([]) == "neutral"

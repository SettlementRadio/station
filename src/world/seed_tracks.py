"""Seed the curated tracks catalogue from the music-lore manifest (D7.0).

    .venv/bin/python -m src.world.seed_tracks      # or: make seed-tracks

The manifest (`config/tracks.yaml`, human-authored from docs/MEDIA_LIBRARY.md) is
the source of truth; this loader conforms to ITS field shape — it never invents
rows or renames fields. The catalogue is curated config/catalog (§2a): this is its
OWN refresh path, separate from `seed-canon`/`reset-world` (which never touch it).
Re-running reproduces exactly what the manifest describes.

Per-row behaviour (the manifest's documented null semantics):
* `duration_sec: null` + the audio file exists → probe the real duration
  (`tts.probe_duration`) and stamp it.
* the `audio_path` file is absent → load the LORE anyway (the track stays
  referenceable world culture) but it simply isn't playable yet — logged, never
  a crash. Playability is always derived live from the file (`media.is_playable`).
* `licence_note: null` → filled from the manifest's top-level `licence_default`
  (the human's clearance call rides every row).
* `artist` (the manifest's field name) → `in_world_artist` (the column);
  `artist_figure_id` stays null until D10 backfills the figure link.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import yaml

from ..config import settings
from ..logging_setup import get_logger
from ..production import media
from ..providers import tts
from . import store

log = get_logger(__name__)


def load_manifest(path: Path) -> list[store.Track]:
    """Parse the music-lore manifest into `Track` rows (no DB, no probing).

    Fails loudly on a missing file or a row missing its required fields — a
    malformed manifest should stop the seed, not half-load a catalogue.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    licence_default = raw.get("licence_default")
    rows = raw.get("tracks") or []
    tracks: list[store.Track] = []
    for row in rows:
        try:
            track = store.Track(
                id=row["id"],
                title=row["title"],
                in_world_artist=row["artist"],
                mood=row["mood"],
                audio_path=row["audio_path"],
                artist_figure_id=row.get("artist_figure_id"),
                album=row.get("album"),
                era=row.get("era"),
                in_world_year=row.get("in_world_year"),
                story_blurb=row.get("story_blurb"),
                duration_sec=row.get("duration_sec"),
                licence_note=row.get("licence_note") or licence_default,
                tags=list(row.get("tags") or []),
            )
        except KeyError as exc:
            raise ValueError(
                f"tracks manifest row {row.get('id', '<no id>')!r} is missing "
                f"required field {exc}"
            ) from None
        tracks.append(track)
    log.info("tracks_manifest_parsed", path=str(path), rows=len(tracks))
    return tracks


def _stamp_durations(tracks: list[store.Track]) -> list[store.Track]:
    """Probe the real duration of each track whose file exists and needs one.

    A probe failure (corrupt/unreadable file) logs and leaves the duration null —
    the row still seeds; it just isn't duration-stamped (and a broken file will
    also fail `is_playable`'s later consumers loudly, not silently here).
    """
    stamped: list[store.Track] = []
    for track in tracks:
        if track.duration_sec is None and media.is_playable(track):
            path = media.track_audio_path(track)
            try:
                seconds = tts.probe_duration(str(path))
            except Exception as exc:
                log.warning(
                    "track_probe_failed", id=track.id, path=str(path), error=str(exc)
                )
            else:
                track = replace(track, duration_sec=round(seconds, 2))
        elif not media.is_playable(track):
            log.info("track_not_playable", id=track.id, audio_path=track.audio_path)
        stamped.append(track)
    return stamped


def seed_tracks() -> dict[str, int]:
    """Refresh the `tracks` table from the manifest; return summary counts."""
    tracks = load_manifest(settings.tracks_manifest_path)
    tracks = _stamp_durations(tracks)

    with store.connect() as conn:
        store.init_schema(conn)
        store.clear_tracks(conn)
        inserted = store.insert_tracks(conn, tracks)

    playable = sum(1 for t in tracks if media.is_playable(t))
    result = {"tracks": inserted, "playable": playable}
    log.info("seed_tracks_done", **result)
    return result


if __name__ == "__main__":
    counts = seed_tracks()
    # Done-when proof: the catalogue reads back, split playable vs lore-only.
    with store.connect() as conn:
        catalogue = store.all_tracks(conn)
    for t in catalogue:
        log.info(
            "track",
            id=t.id,
            artist=t.in_world_artist,
            duration_sec=t.duration_sec,
            playable=media.is_playable(t),
        )
    if counts["tracks"] == 0:
        log.error("seed_tracks_empty", path=str(settings.tracks_manifest_path))
        sys.exit(1)

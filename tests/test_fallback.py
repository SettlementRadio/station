"""Tests for the C4 never-dead fallback prep (src/fallback.py).

The load-bearing promise: prepare the lower playout fallback tiers (the evergreen
pool + the disclosure ident) and write the evergreen playlist Liquidsoap watches —
idempotently, and resiliently enough that one piece failing (e.g. TTS down) still
prepares the rest. The TTS-touching renderers are monkeypatched, so we test the
prep's control flow + the playlist it writes, not the models.
"""

from __future__ import annotations

from pathlib import Path

from src import fallback


def _wire(monkeypatch, tmp_path):
    monkeypatch.setattr(
        fallback.settings,
        "fallback_evergreen_playlist_path",
        tmp_path / "evergreen.txt",
    )


def test_ensure_writes_evergreen_playlist_from_pool(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path)
    clips = []
    for i in range(3):
        p = tmp_path / f"evergreen-{i}-test-vell_night.mp3"
        p.write_bytes(b"\x00")
        clips.append(str(p))
    monkeypatch.setattr(fallback, "render_evergreen_pool", lambda *, force=False: clips)
    monkeypatch.setattr(
        fallback, "render_ident_audio", lambda *, force=False: str(tmp_path / "id.mp3")
    )

    summary = fallback.ensure_fallback_assets()

    assert summary["evergreen"] == 3
    lines = (tmp_path / "evergreen.txt").read_text().splitlines()
    assert lines == [str(Path(c).resolve()) for c in clips]


def test_playlist_lists_only_existing_clips(monkeypatch, tmp_path):
    # A clip the renderer reported but that isn't on disk must not reach the
    # playlist (Liquidsoap would treat a missing entry as a gap).
    _wire(monkeypatch, tmp_path)
    real = tmp_path / "evergreen-0-test-vell_night.mp3"
    real.write_bytes(b"\x00")
    ghost = tmp_path / "evergreen-1-test-vell_night.mp3"  # never written
    monkeypatch.setattr(
        fallback,
        "render_evergreen_pool",
        lambda *, force=False: [str(real), str(ghost)],
    )
    monkeypatch.setattr(fallback, "render_ident_audio", lambda *, force=False: "x.mp3")

    fallback.ensure_fallback_assets()

    lines = (tmp_path / "evergreen.txt").read_text().splitlines()
    assert lines == [str(real.resolve())]


def test_ident_failure_still_prepares_evergreen(monkeypatch, tmp_path):
    # The ident render raising (TTS down) must not stop the evergreen pool/playlist
    # from being prepared — the fallback must be as ready as it can, not all-or-nothing.
    _wire(monkeypatch, tmp_path)
    clip = tmp_path / "evergreen-0-test-vell_night.mp3"
    clip.write_bytes(b"\x00")
    monkeypatch.setattr(
        fallback, "render_evergreen_pool", lambda *, force=False: [str(clip)]
    )

    def _boom(*, force=False):
        raise RuntimeError("simulated TTS failure")

    monkeypatch.setattr(fallback, "render_ident_audio", _boom)

    summary = fallback.ensure_fallback_assets()

    assert summary["evergreen"] == 1
    assert summary["ident"] is None  # ident failed…
    assert (tmp_path / "evergreen.txt").exists()  # …but evergreen was still prepared


def test_evergreen_failure_does_not_raise(monkeypatch, tmp_path):
    # Even if the evergreen render blows up entirely, ensure_fallback_assets must
    # return cleanly (it's called best-effort from a top-up and must never raise).
    _wire(monkeypatch, tmp_path)

    def _boom(*, force=False):
        raise RuntimeError("simulated pool failure")

    monkeypatch.setattr(fallback, "render_evergreen_pool", _boom)
    monkeypatch.setattr(fallback, "render_ident_audio", lambda *, force=False: "id.mp3")

    summary = fallback.ensure_fallback_assets()

    assert summary["evergreen"] == 0
    assert summary["ident"] == "id.mp3"

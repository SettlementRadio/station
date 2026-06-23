#!/usr/bin/env liquidsoap
# Settlement Radio — local playout (Phase C, C2; ARCHITECTURE.md Layers 5–6).
#
# Airs the SCHEDULER's ordered playlist (segments/playlist.txt) to a local Icecast
# mount, with a never-dead FALLBACK so the stream never goes silent: if the playlist
# is empty/absent (or a track ends with nothing queued), a bundled bed
# (assets/bed.mp3, if present) or a quiet sine tone keeps the mount live.
#
# This is the Layer 5 <-> playout seam (C2): `python -m src.scheduler` decides what
# airs when, on MEASURED durations, and rewrites the playlist; Liquidsoap re-reads it
# (reload_mode="watch") and plays through it in order. (Phase A/B aired the newest
# file in segments/; the scheduler now drives the order instead.)
#
# Run from the repo root (the Makefile does this for you):
#   make schedule      # fill the playlist first (live Claude + TTS; needs `make seed`)
#   liquidsoap config/radio.liq
# Then open  http://localhost:8000/settlement.mp3  in a browser.

# --- Logging: quiet, to stdout, so `make serve` shows what's happening. ---
log.level.set(3)
settings.log.stdout.set(true)
settings.log.file.set(false)

# --- Paths (relative to CWD = repo root) and the Icecast password. ---
# The password mirrors ICECAST_SOURCE_PASSWORD in .env and the <source-password>
# in config/icecast.xml; all three default to "hackme". The playlist path mirrors
# settings.schedule_playlist_path (SCHEDULE_PLAYLIST_PATH in .env).
playlist_path = environment.get(default="segments/playlist.txt", "SCHEDULE_PLAYLIST_PATH")
ice_password = environment.get(default="hackme", "ICECAST_SOURCE_PASSWORD")

# --- Source 1: never-dead fallback. A bundled royalty-free bed if the human
# dropped one at assets/bed.mp3, otherwise a quiet sine so the mount stays live
# (Icecast drops a mount with no source; silence-avoidance keeps listeners on). ---
fallback_bed =
  if file.exists("assets/bed.mp3") then
    log("Fallback: assets/bed.mp3")
    single("assets/bed.mp3")
  else
    log("Fallback: quiet sine tone (drop assets/bed.mp3 to replace).")
    sine(amplitude=0.03, 220.)
  end

# --- Source 2: the scheduler's ordered playlist (the Layer 5 <-> playout seam). ---
# `python -m src.scheduler` writes segments/playlist.txt — the upcoming segments in
# air order, one absolute path per line, on MEASURED durations — and rewrites it on
# every top-up (pruning aired entries from the front, appending fresh ones). We read
# it with reload_mode="watch", so each rewrite is picked up live with no restart, and
# mode="normal" so we play through it IN ORDER (the scheduler's decision, not a name/
# mtime guess). When the playlist doesn't exist yet (scheduler never run), we air the
# fallback alone so the mount still comes up; `make schedule` then fills it.
#
# track_sensitive=false so the moment the scheduled source has audio we cut back to
# it instead of waiting for the fallback "track" to end.
radio =
  if file.exists(playlist_path) then
    log("Airing scheduler playlist: #{playlist_path}")
    scheduled = playlist(mode="normal", reload_mode="watch", playlist_path)
    fallback(track_sensitive=false, [scheduled, fallback_bed])
  else
    log("No schedule playlist at #{playlist_path} yet — run `make schedule`. Falling back.")
    fallback_bed
  end

# Keep the stream alive even if a source momentarily yields nothing.
radio = mksafe(radio)

# --- Output: local Icecast, MP3, mount /settlement.mp3 ---
output.icecast(
  %mp3(bitrate=128),
  host="localhost",
  port=8000,
  password=ice_password,
  mount="/settlement.mp3",
  name="Settlement Radio",
  description="AI-generated sci-fi radio from 600 years ahead (Phase A, local).",
  genre="Talk / Sci-Fi",
  radio
)

#!/usr/bin/env liquidsoap
# Settlement Radio — local playout (Phase C, C2/C4; ARCHITECTURE.md Layers 5–6).
#
# Airs the SCHEDULER's ordered playlist (segments/playlist.txt) to a local Icecast
# mount, behind a never-dead FALLBACK CHAIN (C4) so the stream is never silent
# through any single failure:
#
#   scheduled playlist  ->  evergreen pool  ->  music bed  ->  disclosure ident  ->  tone
#
# Each lower tier is always-available audio, so if the generator is down and the
# rolling buffer drains (scheduled playlist empties), playout degrades to the next
# tier instead of dead air: a pre-rendered evergreen segment, then a bundled music
# bed (assets/bed.mp3, if present), then the spoken AI-disclosure ident, and only
# as an absolute last resort a quiet sine. src/fallback.py pre-renders the evergreen
# pool + ident WHILE the system is healthy (so they survive a Claude/Kokoro outage)
# and writes the evergreen playlist this file watches.
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
# in config/icecast.xml; all three default to "hackme". The playlist paths mirror
# settings.schedule_playlist_path (SCHEDULE_PLAYLIST_PATH) and
# settings.fallback_evergreen_playlist_path (FALLBACK_EVERGREEN_PLAYLIST_PATH).
# The ident path defaults to the kokoro/night-host clip; override with
# FALLBACK_IDENT_PATH in .env if you change TTS_PROVIDER or the disclosure voice.
playlist_path = environment.get(default="segments/playlist.txt", "SCHEDULE_PLAYLIST_PATH")
evergreen_path = environment.get(default="segments/evergreen.txt", "FALLBACK_EVERGREEN_PLAYLIST_PATH")
ident_path = environment.get(default="segments/ident-disclosure-kokoro-vell_night.mp3", "FALLBACK_IDENT_PATH")
ice_password = environment.get(default="hackme", "ICECAST_SOURCE_PASSWORD")

# A source that's only available when its file exists; otherwise `source.fail()`
# (never produces), so the fallback chain just moves on to the next tier. This lets
# us build every tier unconditionally and let availability decide what airs.
def file_or_fail(p) =
  if file.exists(p) then single(p) else source.fail() end
end

# --- Tier 1: the scheduler's ordered playlist (the Layer 5 <-> playout seam). ---
# `python -m src.scheduler` writes segments/playlist.txt — the upcoming segments in
# air order, one absolute path per line, on MEASURED durations — and rewrites it on
# every top-up (pruning aired entries from the front, appending fresh ones). We read
# it with reload_mode="watch", so each rewrite is picked up live with no restart, and
# mode="normal" so we play through it IN ORDER (the scheduler's decision, not a name/
# mtime guess). When the playlist is missing OR empty (scheduler never run, or the
# buffer has fully drained), the source is simply unavailable and the chain falls
# through to the never-dead tiers below.
scheduled =
  if file.exists(playlist_path) then
    log("Airing scheduler playlist: #{playlist_path}")
    playlist(mode="normal", reload_mode="watch", playlist_path)
  else
    log("No schedule playlist at #{playlist_path} yet — run `make schedule`.")
    source.fail()
  end

# --- Tier 2: the pre-rendered EVERGREEN POOL (C4). Timeless in-world spoken
# segments src/fallback.py renders while healthy and lists in evergreen.txt.
# randomize so a long fallback spell doesn't loop one clip; watch so a refresh of
# the pool is picked up live. This is the real never-dead workhorse — a clean
# spoken segment, not a tone — for when generation is down. ---
evergreen =
  if file.exists(evergreen_path) then
    log("Evergreen fallback pool: #{evergreen_path}")
    playlist(mode="randomize", reload_mode="watch", evergreen_path)
  else
    log("No evergreen pool at #{evergreen_path} yet — run `make fallback`.")
    source.fail()
  end

# --- Tier 3: a music bed, if the human dropped one at assets/bed.mp3. ---
music_bed = file_or_fail("assets/bed.mp3")

# --- Tier 4: the spoken AI-disclosure ident — the deepest SPOKEN last-resort, so
# even a bare fallback still says what the station is. ---
ident = file_or_fail(ident_path)

# --- Tier 5: a quiet sine — the absolute last resort so the mount is never silent
# (Icecast drops a mount with no source; silence-avoidance keeps listeners on). ---
tone = sine(amplitude=0.03, 220.)

# The never-dead chain (C4): play the highest-priority AVAILABLE tier.
# track_sensitive=false so the moment a higher tier has audio again (e.g. the
# scheduler refills the playlist) we cut back to it mid-fallback-track.
radio = fallback(track_sensitive=false, [scheduled, evergreen, music_bed, ident, tone])

# Belt-and-suspenders: keep the stream alive even if a source momentarily yields
# nothing (the sine tier already guarantees audio; this is the final guard).
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

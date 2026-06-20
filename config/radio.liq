#!/usr/bin/env liquidsoap
# Settlement Radio — local playout (Phase A, T5; ARCHITECTURE.md Layers 5–6).
#
# Loops the NEWEST segment in segments/ to a local Icecast mount, with a
# never-dead FALLBACK so the stream never goes silent: if no segment exists yet
# (or one ends), a bundled bed (assets/bed.mp3, if present) or a quiet sine tone
# keeps the mount live. No scheduler yet — that arrives in a later phase; here
# the "schedule" is simply: always play the latest thing Claude produced.
#
# Run from the repo root (the Makefile in T6 does this for you):
#   liquidsoap config/radio.liq
# Then open  http://localhost:8000/settlement.mp3  in a browser.

# --- Logging: quiet, to stdout, so `make serve` shows what's happening. ---
log.level.set(3)
settings.log.stdout.set(true)
settings.log.file.set(false)

# --- Paths (relative to CWD = repo root) and the Icecast password. ---
# The password mirrors ICECAST_SOURCE_PASSWORD in .env and the <source-password>
# in config/icecast.xml; all three default to "hackme".
segments_dir = "segments"
ice_password = environment.get(default="hackme", "ICECAST_SOURCE_PASSWORD")

# --- Source 1: the newest segment, re-picked every time a track ends. ---
# Pick by MODIFICATION TIME, not by filename order. Segments now use different
# prefixes — produce.py writes vell-YYYYmmddTHHMMSS.mp3 (single DJ) and the
# conversation writes convo-… (two DJs) — which no longer sort by time (a `vell-`
# always sorts after any `convo-`), so a name sort would wrongly prefer an old
# Vell clip over a fresh conversation. `file.mtime` is prefix-agnostic. Re-scanning
# on each request means a segment generated while the stream is up is picked up
# automatically on the next loop, with no restart. (Phase A/B placeholder: the
# real scheduler that plays *through* a buffer arrives in Phase C.)
def newest_segment() =
  files = file.ls(absolute=true, sorted=true, segments_dir)
  audio_files = list.filter(
    fun(f) -> list.mem(file.extension(leading_dot=false, f), [".mp3", "mp3", ".wav", "wav"]),
    files
  )
  if audio_files == [] then
    log("No segment in #{segments_dir} yet — falling back.")
    null
  else
    newest = list.fold(
      fun(best, f) ->
        if best == "" or file.mtime(f) > file.mtime(best) then f else best end,
      "",
      audio_files
    )
    log("Now playing newest segment: #{newest}")
    request.create(newest)
  end
end

segments = request.dynamic(retry_delay=5., newest_segment)

# --- Source 2: never-dead fallback. A bundled royalty-free bed if the human
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

# track_sensitive=false so the moment a real segment is available we cut back to
# it instead of waiting for the fallback "track" to end.
radio = fallback(track_sensitive=false, [segments, fallback_bed])

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

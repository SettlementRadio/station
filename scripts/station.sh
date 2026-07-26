#!/usr/bin/env bash
# station.sh — start (or stop) the WHOLE local station with one command.
#
# `make station` runs everything the station needs on this machine and then gets out
# of the way: after it, the operator PANEL is the only surface you need. The pieces it
# starts are exactly the ones a VPS runs as systemd units + timers (C5) — this script
# is their local stand-in, nothing more:
#
#   top-up loop   `python -m src.scheduler --interval N`   → the C5 scheduler timer
#   playout       Icecast + Liquidsoap (via `make serve`)  → the C5 playout services
#   feeds         scripts/serve_demo_feeds.py --real       → nginx on the box (C7)
#   site          `npm run dev` in web/                    → Vercel in production
#   panel         `python -m src.panel`                    → settlement-panel.service
#
# Logs land in .run/<name>.log, PIDs in .run/<name>.pid, so `make station-stop` can
# put every one of them down again. Deliberately NOT a process supervisor: if one dies
# it stays dead and the panel/dashboard shows it — this is a laptop, not the box.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

RUN_DIR=".run"
PY=".venv/bin/python"
INTERVAL="${INTERVAL:-300}"
STREAM_URL="http://127.0.0.1:8000/settlement.mp3"
PANEL_URL="http://127.0.0.1:8787/"
SITE_URL="http://localhost:3000/"

mkdir -p "$RUN_DIR"

# --- helpers ----------------------------------------------------------------

_alive() { # _alive <name> → 0 if its recorded pid is still running
  local pid_file="$RUN_DIR/$1.pid"
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

_start() { # _start <name> <stray-pattern> <command…>
  local name="$1" pattern="$2"
  shift 2
  if _alive "$name"; then
    printf '    %-12s already running (pid %s)\n' "$name" "$(cat "$RUN_DIR/$name.pid")"
    return 0
  fi
  # Reap a STRAY we don't have a live pid for — e.g. one started by hand in another
  # terminal. Without this the new process loses the port and dies silently, which is
  # exactly what happened the first time this script ran. (A piece we ARE tracking is
  # adopted above, so `make station` twice never interrupts a running top-up.)
  if [ -n "$pattern" ] && pkill -f "$pattern" 2>/dev/null; then
    printf '    %-12s cleared a stray first\n' "$name"
    sleep 1
  fi
  nohup "$@" >"$RUN_DIR/$name.log" 2>&1 &
  local pid=$!
  echo "$pid" >"$RUN_DIR/$name.pid"
  # Don't claim success for a process that is already gone: a bad port, a missing
  # dependency or a config error all show up within a second.
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    printf '    %-12s started  (pid %s, log %s)\n' "$name" "$pid" "$RUN_DIR/$name.log"
  else
    rm -f "$RUN_DIR/$name.pid"
    printf '    %-12s FAILED — see %s\n' "$name" "$RUN_DIR/$name.log"
    tail -2 "$RUN_DIR/$name.log" | sed 's/^/                 /'
  fi
}

_stop_one() { # _stop_one <name>
  local name="$1" pid_file="$RUN_DIR/$name.pid"
  if [ -f "$pid_file" ]; then
    kill "$(cat "$pid_file")" 2>/dev/null && printf '    %-12s stopped\n' "$name"
    rm -f "$pid_file"
  fi
}

# --- start ------------------------------------------------------------------

start() {
  echo "==> Starting the station (everything; the panel is your control surface)"

  if [ ! -x "$PY" ]; then
    echo "    !! $PY not found — run the setup in README.md first." >&2
    exit 1
  fi

  # 1. The rolling top-up: generates segments and keeps the buffer full. It also
  #    rewrites the playlist and all three public feeds on every pass.
  _start topup "src.scheduler --interval" "$PY" -m src.scheduler --interval "$INTERVAL"

  # 2. Playout. `make serve` stops any stale pair first and waits for the mount.
  echo "    playout      handing off to make serve…"
  if make serve >"$RUN_DIR/playout.log" 2>&1; then
    echo "    playout      up on $STREAM_URL"
  else
    echo "    playout      FAILED — see $RUN_DIR/playout.log (the rest is still up)"
  fi

  # 3. The public feeds, served with the CORS header the site needs. (On the box
  #    this is nginx; here it is the same files behind a tiny static server.)
  _start feeds "serve_demo_feeds" "$PY" scripts/serve_demo_feeds.py --real

  # 4. The public site — only if someone has run `npm install`.
  if [ -d web/node_modules ]; then
    _start site "next dev" env -C web NEXT_PUBLIC_STREAM_URL="$STREAM_URL" npm run dev
  else
    echo "    site         skipped (no web/node_modules — run: cd web && npm install)"
  fi

  # 5. The panel, last, so its first dashboard already sees the rest.
  _start panel "src.panel" "$PY" -m src.panel

  cat <<EOF

    ▶  Panel  : $PANEL_URL   ← everything you need is here
    ▶  Site   : $SITE_URL
    ▶  Stream : $STREAM_URL

    The first buffer fill takes a few minutes (Kokoro renders near real time); until
    a segment lands, playout airs the never-dead fallback. Watch it on the panel.

    Stop everything: make station-stop
EOF
}

# --- stop -------------------------------------------------------------------

stop() {
  echo "==> Stopping the station"
  for name in panel site feeds topup; do _stop_one "$name"; done
  make stop
  # `npm run dev` spawns a child next-server that outlives its parent shell.
  pkill -f "next dev" 2>/dev/null && echo "    site         child processes stopped"
  echo "==> Down."
}

# --- status -----------------------------------------------------------------

status() {
  echo "==> Station processes"
  for name in topup feeds site panel; do
    if _alive "$name"; then
      printf '    %-12s running (pid %s)\n' "$name" "$(cat "$RUN_DIR/$name.pid")"
    else
      printf '    %-12s down\n' "$name"
    fi
  done
  make status
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  status) status ;;
  *)
    echo "usage: $0 [start|stop|status]" >&2
    exit 2
    ;;
esac

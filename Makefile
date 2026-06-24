# Settlement Radio — Phase A run commands (T6).
#
#   make generate   Write a fresh ad-hoc segment for the current time (Claude → TTS).
#   make serve      Start Icecast + Liquidsoap; airs the scheduler playlist (C2).
#   make air        schedule (fill the playlist) + serve — the live path (C2).
#   make play       generate (single-DJ) + serve (ad-hoc segment; see note below).
#   make play-convo generate a two-DJ conversation + serve it (B4; see note below).
#   make stop       Stop Icecast + Liquidsoap (no orphans left behind).
#   make status     Show what's running and the mount state.
#   make seed       Load docs/CANON.md into the world-state DB (B1; idempotent).
#   make demo       Show the progressing-event relative-time flip (B2; needs seed).
#   make context    Print the writer's assembled context for now (B3; needs seed).
#   make conversation  Generate a two-DJ talk segment (B4; needs seed; Claude+TTS).
#   make format FMT=…  Generate one B5 format segment (news|talk|music; needs seed).
#   make buffer        Generate ~an hour of varied segments into segments/ (B6; needs seed).
#   make schedule      Top up the rolling buffer to depth + write the playout playlist (C2).
#
# `generate`/`play`/`schedule` make live Anthropic + TTS calls (needs a populated
# .env). Since C2, `serve` airs the SCHEDULER's playlist (segments/playlist.txt),
# not the newest file — so `make air` (schedule + serve) is the live path. The
# `play`/`play-convo` helpers still write a single ad-hoc segment for inspection,
# but the stream airs whatever the scheduler queued (or the never-dead fallback).

SHELL := /bin/bash
.NOTPARALLEL:

PY         := .venv/bin/python
RUN_DIR    := .run
ICE_PID    := $(RUN_DIR)/icecast.pid
LIQ_PID    := $(RUN_DIR)/liquidsoap.pid
ICE_LOG    := $(RUN_DIR)/icecast.log
LIQ_LOG    := $(RUN_DIR)/liquidsoap.log
# Use the IPv4 literal, not `localhost`: browsers resolve `localhost` to IPv6
# ::1 first, but Icecast binds IPv4 127.0.0.1 — so `localhost` shows "empty page".
PLAYER_URL := http://127.0.0.1:8000/
STREAM_URL := http://127.0.0.1:8000/settlement.mp3

.PHONY: help generate serve air play play-convo stop status seed demo context conversation format buffer schedule ident prune fallback health

# B5 format default: `make format` builds a talk segment; override with FMT=news
# or FMT=music. Pass a TOPIC=... to steer canon retrieval.
FMT   ?= talk
TOPIC ?=

# B6 buffer: target audio length in seconds. Default is the configured ~hour;
# lower it for a quick check, e.g. `make buffer SECONDS=600`.
SECONDS ?=

# C2 scheduler: optional loop interval in seconds. Empty = one top-up then exit
# (the cron/systemd shape for C5); e.g. `make schedule INTERVAL=300` to keep the
# rolling buffer topped up locally every 5 minutes.
INTERVAL ?=

help:
	@echo "Settlement Radio (Phase A):"
	@echo "  make play      generate a single-DJ segment + serve it, print the URL"
	@echo "  make play-convo generate a two-DJ conversation + serve it"
	@echo "  make generate  write a fresh segment for the current time"
	@echo "  make serve     start Icecast + Liquidsoap (loops newest segment)"
	@echo "  make stop      stop Icecast + Liquidsoap"
	@echo "  make status    show what's running"
	@echo "  make seed      load docs/CANON.md into the world-state DB (B1)"
	@echo "  make demo      show the progressing-event relative-time flip (B2)"
	@echo "  make context   print the writer's assembled context for now (B3)"
	@echo "  make conversation  generate a two-DJ talk segment (B4)"
	@echo "  make format FMT=…  generate one B5 format segment (news|talk|music)"
	@echo "  make buffer    generate ~an hour of varied segments into segments/ (B6)"
	@echo "  make ident     render the spoken AI-disclosure ident (C3)"
	@echo "  make prune     GC aired segment audio past the retention window (C2.5)"
	@echo "  make fallback  pre-render the never-dead fallback assets (C4)"
	@echo "  make health    run the health checks + alert on any issue (C4)"
	@echo "  make schedule  top up the rolling buffer to depth + write the playlist (C2)"
	@echo "  make air       schedule + serve — the live scheduler-driven stream (C2)"

# Seed the world-state DB from docs/CANON.md (the human-editable source). Reads
# DATABASE_URL via src/config.py; idempotent (re-running reproduces the state).
seed:
	@echo "==> Seeding the world-state DB from docs/CANON.md…"
	$(PY) -m src.world.seed

# B2 proof: render the Lumen Festival at two `now` values and show the relative
# phrase flip ("in five days" -> "yesterday"). Needs `make seed` first.
demo:
	@echo "==> Progressing-event demo (B2)…"
	$(PY) -m src.world.events

# B3 check: print the stable cached core + the dynamic (events/canon) slice the
# writer will send for the current time. Needs `make seed` first.
context:
	@echo "==> Assembled writer context (B3)…"
	$(PY) -m src.world.context

# B4: generate a two-DJ conversation segment (showrunner → orchestrator →
# continuity → two-voice render). Makes live Anthropic calls; needs `make seed`.
conversation:
	@echo "==> Generating a two-DJ conversation segment (B4)…"
	$(PY) -m src.writers.conversation

# B5: generate one program-format segment from a proven skeleton. Live Anthropic
# + TTS; needs `make seed`. e.g. `make format FMT=news` or `make format FMT=music`.
format:
	@echo "==> Generating a '$(FMT)' format segment (B5)…"
	$(PY) -m src.formats $(FMT) $(TOPIC)

# B6: generate a small varied buffer (~an hour of audio) in one run — a mix of the
# three B5 formats and both DJs, each a proper Segment with a JSON sidecar, plus a
# run manifest. Live Anthropic + Kokoro TTS; needs `make seed`. Override the target
# length with SECONDS=… for a quick check, e.g. `make buffer SECONDS=600`.
buffer:
	@echo "==> Generating a light nightly buffer (B6)…"
	$(PY) -m src.buffer $(SECONDS)

# C2: top up the rolling buffer to `buffer_depth_hours` of MEASURED audio and write
# the ordered playlist Liquidsoap airs (segments/playlist.txt). One-shot by default
# (the cron/systemd shape for C5); pass INTERVAL=… to loop locally. Live Anthropic +
# TTS; needs `make seed`. `make serve` then airs whatever the scheduler queued.
schedule:
	@echo "==> Topping up the rolling buffer + writing the playout playlist (C2)…"
	$(PY) -m src.scheduler $(if $(INTERVAL),--interval $(INTERVAL),)

# C3: render (or reuse) the spoken AI-disclosure ident and print its path +
# measured length. The scheduler weaves this clip into the playlist every
# `disclosure_every_n` content segments. Live TTS (no Claude call — text is
# static); pass FORCE=1 to re-render after editing the ident copy.
ident:
	@echo "==> Rendering the AI-disclosure ident (C3)…"
	$(PY) -m src.disclosure $(if $(FORCE),--force,)

# C2.5: garbage-collect aired, unreferenced segment audio so a 24/7 run can't fill
# the disk. Runs automatically at the end of every `make schedule`; this target is
# the standalone GC (no Claude/TTS) for verifying retention against what's on disk.
prune:
	@echo "==> Pruning aired segment audio past the retention window (C2.5)…"
	$(PY) -m src.scheduler --prune

# C4: pre-render the never-dead playout fallback assets — the evergreen pool +
# the AI-disclosure ident — and write the evergreen playlist Liquidsoap watches.
# Runs automatically at the top of every `make schedule`; this is the standalone
# prepare + verify. Live TTS (no Claude — the text is static); FORCE=1 re-renders.
fallback:
	@echo "==> Preparing never-dead fallback assets (C4)…"
	$(PY) -m src.fallback $(if $(FORCE),--force,)

# C4: run the health checks (buffer depth / last scheduler run / stream liveness)
# and alert on any issue (log + optional webhook/uptime ping). Exits non-zero when
# unhealthy so a cron/systemd timer can act on it. No Claude/TTS — pure reads.
health:
	@echo "==> Running health checks (C4)…"
	$(PY) -m src.health

generate:
	@echo "==> Generating a fresh segment for the current time…"
	$(PY) -m src.produce

# `serve` always stops first, so a stale Icecast can never hold port 8000.
serve: stop
	@mkdir -p $(RUN_DIR)
	@echo "==> Starting Icecast…"
	@nohup icecast -c config/icecast.xml > $(ICE_LOG) 2>&1 & echo $$! > $(ICE_PID)
	@printf "    waiting for Icecast on :8000 "
	@for i in $$(seq 1 40); do \
		if curl -sf -o /dev/null $(PLAYER_URL); then echo "ok"; break; fi; \
		printf "."; sleep 0.25; \
		if [ $$i -eq 40 ]; then echo " FAILED (see $(ICE_LOG))"; exit 1; fi; \
	done
	@echo "==> Starting Liquidsoap…"
	@set -a; [ -f .env ] && . ./.env || true; set +a; \
		nohup opam exec -- liquidsoap config/radio.liq > $(LIQ_LOG) 2>&1 & \
		echo $$! > $(LIQ_PID)
	@echo ""
	@echo "    ▶  Player : $(PLAYER_URL)"
	@echo "    ▶  Stream : $(STREAM_URL)"
	@echo "       Logs   : $(ICE_LOG) , $(LIQ_LOG)"
	@echo "       Stop   : make stop"

# The live path (C2): fill the scheduler playlist, then serve it. Re-run `make
# schedule` (or `make schedule INTERVAL=…`) to keep the rolling buffer topped up;
# Liquidsoap re-reads the playlist with no restart.
air: schedule serve

play: generate serve

# Two-DJ counterpart of `play`: generate a conversation, then serve. Playout picks
# the newest segment by modification time, so the fresh convo airs even with older
# vell-*/convo-* files in segments/.
play-convo: conversation serve

stop:
	@-[ -f $(LIQ_PID) ] && kill `cat $(LIQ_PID)` 2>/dev/null || true
	@-[ -f $(ICE_PID) ] && kill `cat $(ICE_PID)` 2>/dev/null || true
	@-pkill -f "liquidsoap config/radio.liq" 2>/dev/null || true
	@-pkill -f "icecast -c config/icecast.xml" 2>/dev/null || true
	@rm -f $(LIQ_PID) $(ICE_PID)
	@echo "==> Stopped Icecast + Liquidsoap."

status:
	@echo "Icecast    : $$(pgrep -f 'icecast -c config/icecast.xml' >/dev/null && echo running || echo stopped)"
	@echo "Liquidsoap : $$(pgrep -f 'liquidsoap config/radio.liq' >/dev/null && echo running || echo stopped)"
	@printf "Mount      : "; curl -s -o /dev/null --max-time 2 -w "%{http_code} %{content_type} (000 = down)\n" $(STREAM_URL) 2>/dev/null; echo

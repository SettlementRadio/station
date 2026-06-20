# Settlement Radio — Phase A run commands (T6).
#
#   make generate   Write a fresh segment for the current time (Claude → TTS).
#   make serve      Start Icecast + Liquidsoap (clean start; backgrounded).
#   make play       generate (single-DJ) + serve, then print the local stream URL.
#   make play-convo generate a two-DJ conversation + serve it (B4).
#   make stop       Stop Icecast + Liquidsoap (no orphans left behind).
#   make status     Show what's running and the mount state.
#   make seed       Load docs/CANON.md into the world-state DB (B1; idempotent).
#   make demo       Show the progressing-event relative-time flip (B2; needs seed).
#   make context    Print the writer's assembled context for now (B3; needs seed).
#   make conversation  Generate a two-DJ talk segment (B4; needs seed; Claude+TTS).
#   make format FMT=…  Generate one B5 format segment (news|talk|music; needs seed).
#   make buffer        Generate ~an hour of varied segments into segments/ (B6; needs seed).
#
# `generate`/`play` make a live Anthropic + ElevenLabs call (needs a populated
# .env). `serve` just loops whatever segment already exists.

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

.PHONY: help generate serve play play-convo stop status seed demo context conversation format buffer

# B5 format default: `make format` builds a talk segment; override with FMT=news
# or FMT=music. Pass a TOPIC=... to steer canon retrieval.
FMT   ?= talk
TOPIC ?=

# B6 buffer: target audio length in seconds. Default is the configured ~hour;
# lower it for a quick check, e.g. `make buffer SECONDS=600`.
SECONDS ?=

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

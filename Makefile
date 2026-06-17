# Settlement Radio — Phase A run commands (T6).
#
#   make generate   Write a fresh segment for the current time (Claude → TTS).
#   make serve      Start Icecast + Liquidsoap (clean start; backgrounded).
#   make play       generate + serve, then print the local stream URL.
#   make stop       Stop Icecast + Liquidsoap (no orphans left behind).
#   make status     Show what's running and the mount state.
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

.PHONY: help generate serve play stop status

help:
	@echo "Settlement Radio (Phase A):"
	@echo "  make play      generate a fresh segment + serve it, print the URL"
	@echo "  make generate  write a fresh segment for the current time"
	@echo "  make serve     start Icecast + Liquidsoap (loops newest segment)"
	@echo "  make stop      stop Icecast + Liquidsoap"
	@echo "  make status    show what's running"

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

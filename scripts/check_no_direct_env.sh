#!/usr/bin/env bash
# Guardrail (B0.5): all configuration must flow through the typed settings module
# src/config.py — code must never read the environment directly (CLAUDE.md
# "config over hardcoding"). This fails a commit if os.getenv / os.environ /
# dotenv access appears anywhere in src/ outside config.py.
#
# pre-commit passes the matching files as args (filtered by .pre-commit-config.yaml
# to src/ excluding config.py). Run manually with:
#   scripts/check_no_direct_env.sh src/**/*.py
set -euo pipefail

# Nothing to check (pre-commit shouldn't invoke us with no files, but be safe).
[ "$#" -eq 0 ] && exit 0

pattern='os\.getenv|os\.environ|load_dotenv|from dotenv|import dotenv'
hits="$(grep -nE "$pattern" "$@" || true)"

if [ -n "$hits" ]; then
  echo "ERROR: direct environment access outside src/config.py."
  echo "Add the value to src/config.py (Settings) and read it via settings.X."
  echo "$hits"
  exit 1
fi

"""`python -m src.panel` → serve the operator panel on loopback (make panel)."""

from __future__ import annotations

from .app import run

if __name__ == "__main__":
    raise SystemExit(run())

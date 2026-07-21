"""E1 — the private operator PANEL (the write-control surface).

A single-operator FastAPI app that upgrades the read-only console (D6.3) into a
real operator surface. It is PRIVATE by network position (CLAUDE.md hard rule):
it binds LOOPBACK ONLY and is reached on the VPS through an SSH tunnel — never a
public DNS name, reverse proxy, or Vercel. See docs/PHASE_E_PANEL_TASKS.md.

    make panel          # then open http://127.0.0.1:8787/
"""

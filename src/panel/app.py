"""E1.0 — the panel app: a FastAPI surface bound to loopback, read side first.

This module builds the app and owns the ONE security invariant every later E1
task inherits (principle #2): the panel is private by NETWORK POSITION. It binds
`settings.panel_host`, which must be a loopback address; `run()` REFUSES to start
on a non-loopback bind unless `settings.panel_allow_nonlocal` is explicitly set
(the escape hatch logs a loud warning). Access on the VPS is an SSH tunnel, never
a public DNS name / reverse proxy / Vercel.

E1.0 serves only the read-only dashboard (the console's web form). Writes — the
actions page, editors, dials — arrive in E1.1+ on this same app + templates.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..logging_setup import get_logger
from . import views

log = get_logger(__name__)

_HERE = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=str(_HERE / "templates"))

# Loopback hosts the panel is allowed to bind without the escape hatch. `0.0.0.0`
# and any real interface are deliberately absent — that is the whole point.
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def is_loopback(host: str) -> bool:
    """True when `host` is a loopback bind (127.x / ::1 / localhost)."""
    host = host.strip()
    return host in _LOOPBACK_HOSTS or host.startswith("127.")


def create_app() -> FastAPI:
    """Build the FastAPI app: static mount + the E1.0 dashboard route."""
    app = FastAPI(
        title="Settlement Radio — Operator Panel", docs_url=None, redoc_url=None
    )
    app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:  # noqa: ANN001
        """The read-only dashboard — the console/health/feed at a glance."""
        return _TEMPLATES.TemplateResponse(
            request, "dashboard.html", {"d": views.dashboard()}
        )

    return app


# The module-level app uvicorn imports as `src.panel.app:app`.
app = create_app()


def run() -> int:
    """Serve the panel, enforcing the loopback invariant (E1 principle #2)."""
    import uvicorn

    host, port = settings.panel_host, settings.panel_port
    if not is_loopback(host):
        if not settings.panel_allow_nonlocal:
            log.error(
                "panel_refuse_nonlocal_bind",
                host=host,
                hint="set PANEL_ALLOW_NONLOCAL=true to override (NOT recommended)",
            )
            print(
                f"REFUSING to start: panel_host={host!r} is not loopback.\n"
                "The operator panel is private (VPS-only, via SSH tunnel) and must "
                "bind 127.0.0.1.\nTo override (you almost certainly should not), set "
                "PANEL_ALLOW_NONLOCAL=true.",
                file=sys.stderr,
            )
            return 2
        log.warning("panel_nonlocal_bind_allowed", host=host)  # loud, per principle #2

    log.info("panel_start", url=f"http://{host}:{port}/")
    print(f"Operator panel (private): http://{host}:{port}/  — Ctrl-C stops")
    uvicorn.run(app, host=host, port=port, log_level=settings.log_level)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

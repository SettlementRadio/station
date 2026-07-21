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

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..logging_setup import get_logger
from . import actions, views

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

    # --- E1.1: the actions page + the destructive reset-world gate ------------

    def _redirect(url: str) -> RedirectResponse:
        """POST-then-redirect (303) so a refresh never re-submits the action."""
        return RedirectResponse(url, status_code=303)

    @app.get("/actions", response_class=HTMLResponse)
    def actions_page(
        request: Request,
        msg: str | None = None,  # noqa: ANN001
        started: str | None = None,
    ) -> HTMLResponse:
        """The action buttons, the mutation-lock banner, and recent run output."""
        runs = actions.recent_runs()
        return _TEMPLATES.TemplateResponse(
            request,
            "actions.html",
            {
                "groups": _grouped_actions(),
                "runs": runs,
                "running": any(r.status == "running" for r in runs),
                "mutation": actions.current_mutation(),
                "refresh_sec": settings.panel_refresh_sec,
                "msg": msg,
                "started": started,
            },
        )

    @app.post("/actions/run")
    def actions_run(action_id: str = Form(...)) -> RedirectResponse:
        """Launch a non-destructive action; destructive ones use the gated page."""
        action = actions.ACTIONS.get(action_id)
        if action is None:
            return _redirect("/actions?msg=unknown+action")
        if action.destructive:  # never runnable from the generic button
            return _redirect("/actions/reset-world")
        try:
            run = actions.start_action(action_id)
        except actions.Busy as busy:
            return _redirect(f"/actions?msg=busy:+{busy.holder.label}+is+running")
        return _redirect(f"/actions?started={run.id}")

    @app.get("/actions/reset-world", response_class=HTMLResponse)
    def reset_world_page(request: Request, msg: str | None = None) -> HTMLResponse:  # noqa: ANN001
        """The red, friction-first confirmation page (E1 principle #4)."""
        return _TEMPLATES.TemplateResponse(
            request,
            "reset_world.html",
            {
                "action": actions.ACTIONS["reset-world"],
                "phrase": actions.ACTIONS["reset-world"].confirm_phrase,
                "mutation": actions.current_mutation(),
                "msg": msg,
            },
        )

    @app.post("/actions/reset-world")
    def reset_world_run(phrase: str = Form("")) -> RedirectResponse:
        """Run the destructive wipe ONLY when the typed phrase matches exactly."""
        try:
            run = actions.start_action("reset-world", phrase=phrase)
        except PermissionError:
            return _redirect("/actions/reset-world?msg=phrase+did+not+match")
        except actions.Busy as busy:
            return _redirect(f"/actions/reset-world?msg=busy:+{busy.holder.label}")
        return _redirect(f"/actions?started={run.id}")

    return app


def _grouped_actions() -> dict[str, list]:
    """The registry grouped for the page (seed / world / air / ops), danger apart."""
    groups: dict[str, list] = {}
    for action in actions.ACTIONS.values():
        if action.destructive:
            continue  # the danger zone links to its own gated page
        groups.setdefault(action.group, []).append(action)
    return groups


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

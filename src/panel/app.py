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
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..logging_setup import get_logger
from . import (
    actions,
    budgets,
    cast_edit,
    catalog_edit,
    dials,
    grid_edit,
    schedule_view,
    views,
    world_view,
)

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

    # --- E1.2: the grid editor (forms over grid.yaml, diff-before-write) ------

    @app.get("/grid", response_class=HTMLResponse)
    def grid_page(request: Request, saved: str | None = None) -> HTMLResponse:  # noqa: ANN001
        """The program list + the read-only weekly slot map."""
        programs = [
            (pid, grid_edit.program_display(pid)) for pid in grid_edit.program_ids()
        ]
        return _TEMPLATES.TemplateResponse(
            request,
            "grid.html",
            {"programs": programs, "slot_map": grid_edit.slot_map(), "saved": saved},
        )

    @app.get("/grid/program/{pid}", response_class=HTMLResponse)
    def grid_program_page(request: Request, pid: str) -> HTMLResponse:  # noqa: ANN001
        """The per-program edit form."""
        try:
            form = grid_edit.program_form(pid)
        except KeyError:
            return _redirect("/grid?saved=")  # unknown program → back to the list
        return _render_program_form(request, form, validation=None)

    @app.post("/grid/program/{pid}", response_class=HTMLResponse)
    def grid_program_edit(  # noqa: ANN001, PLR0913 — one arg per editable field
        request: Request,
        pid: str,
        name: str = Form(""),
        hosts: str = Form(""),
        framing: str = Form("solo"),
        daypart: str = Form(""),
        clock: str = Form(""),
        break_every: str = Form(""),
        guest_chance: str = Form(""),
        brief: str = Form(""),
        energy: str = Form(""),
        talk_length_sec: str = Form(""),
        domains: str = Form(""),
    ) -> HTMLResponse:
        """Build the candidate, validate it, and show the diff (never write here)."""
        form = grid_edit.ProgramForm(
            id=pid,
            name=name,
            hosts=hosts,
            framing=framing,
            daypart=daypart,
            clock=clock,
            break_every=break_every,
            guest_chance=guest_chance,
            brief=brief,
            energy=energy,
            talk_length_sec=talk_length_sec,
            domains=domains,
        )
        try:
            candidate = grid_edit.apply_program_edit(pid, form)
        except KeyError:
            return _redirect("/grid?saved=")
        validation = grid_edit.validate_text(candidate, focus=pid)
        if not validation.ok:
            return _render_program_form(request, form, validation=validation)

        diff = grid_edit.unified_diff(grid_edit.current_text(), candidate)
        if not diff.strip():  # no change → nothing to confirm
            return _render_program_form(
                request, form, validation=validation, no_change=True
            )
        return _TEMPLATES.TemplateResponse(
            request,
            "grid_diff.html",
            {
                "pid": pid,
                "form": form,
                "diff": diff,
                "candidate": candidate,
                "warnings": validation.warnings,
            },
        )

    @app.post("/grid/program/{pid}/confirm")
    def grid_program_confirm(pid: str, candidate: str = Form(...)) -> RedirectResponse:
        """Write the confirmed candidate (atomic + .bak); re-validates as defence."""
        try:
            grid_edit.write_grid(candidate, focus=pid)
        except ValueError as exc:
            log.warning("grid_confirm_rejected", program=pid, error=str(exc))
            return _redirect(f"/grid/program/{pid}")
        return _redirect(f"/grid?saved={pid}")

    def _render_program_form(request, form, *, validation, no_change=False):  # noqa: ANN001
        """Shared render of the program edit form with optional validation state."""
        return _TEMPLATES.TemplateResponse(
            request,
            "grid_program.html",
            {
                "form": form,
                "framings": ["solo", "handover", "ensemble", "legacy"],
                "energies": ["", "calm", "steady", "bright"],
                "errors": validation.errors if validation else [],
                "warnings": validation.warnings if validation else [],
                "no_change": no_change,
            },
        )

    # --- E1.3: the catalog editors (tracks / sponsors / …) -------------------

    @app.get("/catalog", response_class=HTMLResponse)
    def catalog_index(request: Request) -> HTMLResponse:  # noqa: ANN001
        """A small index of the editable config catalogs."""
        return _TEMPLATES.TemplateResponse(
            request, "catalog_index.html", {"catalogs": catalog_edit.CATALOGS.values()}
        )

    @app.get("/catalog/{slug}", response_class=HTMLResponse)
    def catalog_list(request: Request, slug: str, saved: str | None = None):  # noqa: ANN001
        cat = catalog_edit.catalog(slug)
        if cat is None:
            return _redirect("/catalog")
        return _TEMPLATES.TemplateResponse(
            request,
            "catalog_list.html",
            {"cat": cat, "rows": catalog_edit.list_rows(cat), "saved": saved},
        )

    @app.get("/catalog/{slug}/new", response_class=HTMLResponse)
    def catalog_new(request: Request, slug: str) -> HTMLResponse:  # noqa: ANN001
        cat = catalog_edit.catalog(slug)
        if cat is None:
            return _redirect("/catalog")
        return _render_catalog_form(
            request, cat, catalog_edit.blank_form(cat), adding=True, key=""
        )

    @app.get("/catalog/{slug}/edit/{key}", response_class=HTMLResponse)
    def catalog_edit_form(request: Request, slug: str, key: str):  # noqa: ANN001
        cat = catalog_edit.catalog(slug)
        if cat is None:
            return _redirect("/catalog")
        form = catalog_edit.row_form(cat, key)
        if form is None:
            return _redirect(f"/catalog/{slug}")
        return _render_catalog_form(request, cat, form, adding=False, key=key)

    @app.post("/catalog/{slug}/save", response_class=HTMLResponse)
    async def catalog_save(request: Request, slug: str):  # noqa: ANN001
        cat = catalog_edit.catalog(slug)
        if cat is None:
            return _redirect("/catalog")
        data = await request.form()
        adding = data.get("_adding") == "1"
        key = (data.get("_key") or data.get(cat.key_field) or "").strip()
        values = {f.name: (data.get(f.name) or "") for f in cat.fields}
        values["_flags"] = {t: data.get(f"flag_{t}") == "on" for t in cat.feature_tags}
        form_state = {**values, "_flags": values["_flags"]}
        try:
            candidate = catalog_edit.apply_row(cat, key, values, adding=adding)
        except (KeyError, ValueError) as exc:
            return _render_catalog_form(
                request, cat, form_state, adding=adding, key=key, errors=[str(exc)]
            )
        validation = cat.validate(candidate)
        if not validation.ok:
            return _render_catalog_form(
                request,
                cat,
                form_state,
                adding=adding,
                key=key,
                errors=validation.errors,
                warnings=validation.warnings,
            )
        diff = catalog_edit.unified_diff(catalog_edit.current_text(cat), candidate)
        if not diff.strip():
            return _render_catalog_form(
                request, cat, form_state, adding=adding, key=key, no_change=True
            )
        return _TEMPLATES.TemplateResponse(
            request,
            "catalog_diff.html",
            {
                "cat": cat,
                "key": key,
                "diff": diff,
                "candidate": candidate,
                "warnings": validation.warnings,
                "action": "save",
            },
        )

    @app.post("/catalog/{slug}/delete", response_class=HTMLResponse)
    async def catalog_delete(request: Request, slug: str):  # noqa: ANN001
        cat = catalog_edit.catalog(slug)
        if cat is None:
            return _redirect("/catalog")
        data = await request.form()
        key = (data.get("_key") or "").strip()
        try:
            candidate = catalog_edit.delete_row(cat, key)
        except KeyError:
            return _redirect(f"/catalog/{slug}")
        diff = catalog_edit.unified_diff(catalog_edit.current_text(cat), candidate)
        return _TEMPLATES.TemplateResponse(
            request,
            "catalog_diff.html",
            {
                "cat": cat,
                "key": key,
                "diff": diff,
                "candidate": candidate,
                "warnings": [],
                "action": "delete",
            },
        )

    @app.get("/catalog/pronunciation/test")
    def pronunciation_test(text: str = ""):  # noqa: ANN201
        """Render a name/respelling through the TTS seam and serve the throwaway clip.

        Closes the mispronunciation loop in one screen: the lexicon is applied inside
        `tts.synthesize`, so this hears exactly what the engine will say (after a save,
        since the lexicon live-reloads). First call may load the local model.
        """
        phrase = (text or "").strip()[:120]
        if not phrase:
            return PlainTextResponse("no text", status_code=400)
        from ..providers import tts

        out = settings.segments_dir / "panel-tts-test.mp3"
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            tts.synthesize(phrase, voice=settings.disclosure_voice, out_path=str(out))
        except Exception as exc:  # noqa: BLE001 — a TTS failure is a 500 with the reason
            log.warning("panel_tts_test_failed", error=str(exc))
            return PlainTextResponse(f"TTS failed: {exc}", status_code=500)
        return FileResponse(
            out, media_type="audio/mpeg", headers={"Cache-Control": "no-store"}
        )

    @app.post("/catalog/{slug}/write")
    async def catalog_write(request: Request, slug: str) -> RedirectResponse:  # noqa: ANN001
        cat = catalog_edit.catalog(slug)
        if cat is None:
            return _redirect("/catalog")
        data = await request.form()
        candidate = data.get("candidate") or ""
        key = data.get("key") or ""
        try:
            catalog_edit.write(cat, candidate)
        except ValueError as exc:
            log.warning("catalog_write_rejected", catalog=slug, error=str(exc))
            return _redirect(f"/catalog/{slug}")
        return _redirect(f"/catalog/{slug}?saved={key}")

    def _render_catalog_form(
        request,
        cat,
        form,
        *,
        adding,
        key,  # noqa: ANN001
        errors=None,
        warnings=None,
        no_change=False,
    ):
        """Shared render of a catalog add/edit form."""
        return _TEMPLATES.TemplateResponse(
            request,
            "catalog_form.html",
            {
                "cat": cat,
                "form": form,
                "adding": adding,
                "key": key,
                "errors": errors or [],
                "warnings": warnings or [],
                "no_change": no_change,
            },
        )

    # --- E1.4: the cast manager (DJs without editing markdown) ---------------

    cast_bullets = [
        ("role", "Role"),
        ("background", "Background"),
        ("personality", "Personality"),
        ("humour", "Humour"),
        ("voice_tts", "Voice (for TTS)"),
        ("verbal_tics", "Verbal tics"),
        ("never", "Never"),
    ]

    def _known_voices() -> list[str]:
        try:
            return sorted(cast_edit.tts.known_voices())
        except Exception:  # noqa: BLE001 — registry unreadable → an empty picker
            return []

    @app.get("/cast", response_class=HTMLResponse)
    def cast_list(request: Request, saved: str | None = None) -> HTMLResponse:  # noqa: ANN001
        return _TEMPLATES.TemplateResponse(
            request, "cast.html", {"cards": cast_edit.list_cards(), "saved": saved}
        )

    @app.get("/cast/new", response_class=HTMLResponse)
    def cast_new(request: Request) -> HTMLResponse:  # noqa: ANN001
        return _render_cast_form(request, {}, adding=True, cid="")

    @app.get("/cast/edit/{cid}", response_class=HTMLResponse)
    def cast_edit_form(request: Request, cid: str):  # noqa: ANN001
        form = cast_edit.card_form(cid)
        if form is None:
            return _redirect("/cast")
        return _render_cast_form(request, form, adding=False, cid=cid)

    @app.post("/cast/save", response_class=HTMLResponse)
    async def cast_save(request: Request):  # noqa: ANN001
        data = await request.form()
        adding = data.get("_adding") == "1"
        cid = (data.get("_cid") or "").strip()
        values = {k: (data.get(k) or "") for k, _ in cast_bullets}
        values.update(
            name=data.get("name") or "",
            logical_voice=data.get("logical_voice") or "",
            based=data.get("based") or "station",
            tags=data.get("tags") or "",
            sample_lines=data.get("sample_lines") or "",
        )
        try:
            candidate = (
                cast_edit.add_card(values)
                if adding
                else cast_edit.apply_card_edit(cid, values)
            )
        except (KeyError, ValueError) as exc:
            return _render_cast_form(
                request, values, adding=adding, cid=cid, errors=[str(exc)]
            )

        # A new voice not yet in the registry → optionally create its voices.yaml
        # entry in the SAME flow (E1.3's editor, embedded).
        voices_candidate = None
        voice = values["logical_voice"].strip()
        if voice and voice not in _known_voices():
            engines = {
                e: (data.get(f"voice_{e}") or "").strip()
                for e in ("kokoro", "elevenlabs", "say")
            }
            if any(engines.values()):
                vcat = catalog_edit.catalog("voices")
                try:
                    voices_candidate = catalog_edit.apply_row(
                        vcat, voice, {**engines, "_flags": {}}, adding=True
                    )
                except ValueError as exc:
                    return _render_cast_form(
                        request, values, adding=adding, cid=cid, errors=[str(exc)]
                    )
                vv = vcat.validate(voices_candidate)
                if not vv.ok:
                    return _render_cast_form(
                        request, values, adding=adding, cid=cid, errors=vv.errors
                    )

        validation = cast_edit.validate(candidate)
        # If we're also creating the voice entry, the registry check (which reads the
        # LIVE file) would still flag it — suppress that one, the entry is queued.
        if voices_candidate is not None:
            validation.errors = [
                e for e in validation.errors if "has no entry" not in e
            ]
        if not validation.ok:
            return _render_cast_form(
                request, values, adding=adding, cid=cid, errors=validation.errors
            )
        diff = cast_edit.unified_diff(cast_edit.current_text(), candidate)
        if not diff.strip() and voices_candidate is None:
            return _render_cast_form(
                request, values, adding=adding, cid=cid, no_change=True
            )
        vdiff = ""
        if voices_candidate is not None:
            vcat = catalog_edit.catalog("voices")
            vdiff = catalog_edit.unified_diff(
                catalog_edit.current_text(vcat), voices_candidate
            )
        return _TEMPLATES.TemplateResponse(
            request,
            "cast_diff.html",
            {
                "cid": cid or cast_edit._slug(values["name"]),
                "diff": diff,
                "candidate": candidate,
                "voices_candidate": voices_candidate or "",
                "voices_diff": vdiff,
                "warnings": validation.warnings,
                "action": "save",
            },
        )

    @app.post("/cast/delete", response_class=HTMLResponse)
    async def cast_delete(request: Request):  # noqa: ANN001
        data = await request.form()
        cid = (data.get("_cid") or "").strip()
        try:
            candidate = cast_edit.remove_card(cid)
        except KeyError:
            return _redirect("/cast")
        uses = cast_edit.grid_uses(cid)
        warnings = (
            [
                f"the grid still schedules this host on: {', '.join(uses)} — "
                "reassign those programs (Grid) before seeding"
            ]
            if uses
            else []
        )
        diff = cast_edit.unified_diff(cast_edit.current_text(), candidate)
        return _TEMPLATES.TemplateResponse(
            request,
            "cast_diff.html",
            {
                "cid": cid,
                "diff": diff,
                "candidate": candidate,
                "voices_candidate": "",
                "voices_diff": "",
                "warnings": warnings,
                "action": "delete",
            },
        )

    @app.post("/cast/write")
    async def cast_write(request: Request) -> RedirectResponse:  # noqa: ANN001
        data = await request.form()
        cid = data.get("cid") or ""
        voices_candidate = data.get("voices_candidate") or ""
        try:
            if voices_candidate.strip():  # write the new voice entry first
                catalog_edit.write(catalog_edit.catalog("voices"), voices_candidate)
            cast_edit.write(data.get("candidate") or "")
        except ValueError as exc:
            log.warning("cast_write_rejected", cid=cid, error=str(exc))
            return _redirect("/cast")
        return _redirect(f"/cast?saved={cid}")

    def _render_cast_form(
        request,
        form,
        *,
        adding,
        cid,
        errors=None,  # noqa: ANN001
        warnings=None,
        no_change=False,
    ):
        return _TEMPLATES.TemplateResponse(
            request,
            "cast_form.html",
            {
                "form": form,
                "adding": adding,
                "cid": cid,
                "bullets": cast_bullets,
                "voices": _known_voices(),
                "based_values": ["station", "field"],
                "errors": errors or [],
                "warnings": warnings or [],
                "no_change": no_change,
            },
        )

    # --- E1.5: the dials page (the tagged .env groups) -----------------------

    @app.get("/dials", response_class=HTMLResponse)
    def dials_page(
        request: Request,
        saved: str | None = None,  # noqa: ANN001
        msg: str | None = None,
    ) -> HTMLResponse:
        groups = [(g, dials.group_rows(g)) for g in dials.DIAL_GROUPS]
        return _TEMPLATES.TemplateResponse(
            request, "dials.html", {"groups": groups, "saved": saved, "msg": msg}
        )

    @app.post("/dials/{slug}/save", response_class=HTMLResponse)
    async def dials_save(request: Request, slug: str):  # noqa: ANN001
        group = dials.group_by_slug(slug)
        if group is None:
            return _redirect("/dials")
        data = await request.form()
        submitted = {name: (data.get(name) or "") for name in group.fields}
        staged = dials.stage_group_edit(group, submitted)
        if staged.errors:
            return _redirect(f"/dials?msg=rejected:+{staged.errors[0]}")
        if not staged.changes:
            return _redirect(f"/dials?msg=no+changes+in+{group.title}")
        candidate = dials.apply_changes(staged.changes)
        diff = dials.unified_diff(dials.current_text(), candidate)
        return _TEMPLATES.TemplateResponse(
            request,
            "dials_diff.html",
            {
                "group": group,
                "diff": diff,
                "candidate": candidate,
                "changes": staged.changes,
            },
        )

    @app.post("/dials/write")
    async def dials_write(request: Request) -> RedirectResponse:  # noqa: ANN001
        data = await request.form()
        slug = data.get("slug") or ""
        try:
            dials.write(data.get("candidate") or "")
        except Exception as exc:  # noqa: BLE001 — a write failure surfaces, not crashes
            log.warning("dials_write_failed", error=str(exc))
            return _redirect(f"/dials?msg=write+failed:+{exc}")
        return _redirect(f"/dials?saved={slug}")

    # --- R5.0 (=E1.7): the schedule screen (queue / history / retry) ----------

    schedule_run_ids = {"schedule", "playout-start", "playout-stop", "playout-restart"}

    @app.get("/schedule", response_class=HTMLResponse)
    def schedule_page(
        request: Request,
        page: int = 0,  # noqa: ANN001
        msg: str | None = None,
        started: str | None = None,
    ) -> HTMLResponse:
        """On-air + upcoming queue (with retry) + paginated aired history + playout."""
        now = datetime.now()
        state = schedule_view._load_state()
        runs = [r for r in actions.recent_runs() if r.action_id in schedule_run_ids]
        return _TEMPLATES.TemplateResponse(
            request,
            "schedule.html",
            {
                "q": schedule_view.queue_view(now, state),
                "history": schedule_view.aired_history(now, page=page),
                "playout": list(actions.PLAYOUT_ACTIONS.values()),
                "mutation": actions.current_mutation(),
                "runs": runs,
                "running": any(r.status == "running" for r in runs),
                "refresh_sec": settings.panel_refresh_sec,
                "msg": msg,
                "started": started,
            },
        )

    @app.post("/schedule/segment/{seg_id}/skip")
    def schedule_skip(seg_id: str) -> RedirectResponse:
        """Drop an upcoming segment from the queue (it will not air)."""
        if actions.current_mutation() is not None:
            return _redirect("/schedule?msg=busy:+an+action+is+running")
        removed = schedule_view.drop_upcoming(seg_id)
        if removed is None:
            return _redirect("/schedule?msg=nothing+to+skip+(not+upcoming)")
        return _redirect(f"/schedule?msg=skipped+{seg_id}")

    @app.post("/schedule/segment/{seg_id}/regenerate")
    def schedule_regenerate(seg_id: str) -> RedirectResponse:
        """Drop an upcoming segment, then re-run top-up so a fresh one re-enters."""
        if actions.current_mutation() is not None:
            return _redirect("/schedule?msg=busy:+an+action+is+running")
        removed = schedule_view.drop_upcoming(seg_id)
        if removed is None:
            return _redirect("/schedule?msg=nothing+to+regenerate+(not+upcoming)")
        try:
            run = actions.start_action("schedule")  # the existing top-up path
        except actions.Busy as busy:
            return _redirect(f"/schedule?msg=dropped,+but+busy:+{busy.holder.label}")
        return _redirect(f"/schedule?started={run.id}")

    @app.post("/schedule/playout")
    def schedule_playout(action_id: str = Form(...)) -> RedirectResponse:
        """Start / stop / restart playout (wraps the configured service commands)."""
        if action_id not in actions.PLAYOUT_ACTIONS:
            return _redirect("/schedule?msg=unknown+playout+action")
        try:
            run = actions.start_action(action_id)
        except actions.Busy as busy:
            return _redirect(f"/schedule?msg=busy:+{busy.holder.label}+is+running")
        return _redirect(f"/schedule?started={run.id}")

    @app.get("/schedule/audio/{seg_id}")
    def schedule_audio(seg_id: str):  # noqa: ANN201
        """Serve an aired segment's render for the operator to listen back."""
        path = schedule_view.audio_path_for(seg_id)
        if path is None:
            return PlainTextResponse("no audio", status_code=404)
        return FileResponse(
            path, media_type="audio/mpeg", headers={"Cache-Control": "no-store"}
        )

    # --- R5.1 (=E1.8): the Budgets screen (cost visibility) ------------------

    @app.get("/budgets", response_class=HTMLResponse)
    def budgets_page(request: Request) -> HTMLResponse:  # noqa: ANN001
        """Spend by job, by day/week, over the usage telemetry — read-only."""
        return _TEMPLATES.TemplateResponse(
            request,
            "budgets.html",
            {"b": budgets.view(), "refresh_sec": settings.panel_refresh_sec},
        )

    # --- R5.2 (=E1.9): the World screen (post-tick digest + arcs + timeline) --

    @app.get("/world", response_class=HTMLResponse)
    def world_page(
        request: Request,
        msg: str | None = None,  # noqa: ANN001
        started: str | None = None,
    ) -> HTMLResponse:
        """Latest digest, arcs in flight, today's beat timeline + tick run buttons."""
        return _TEMPLATES.TemplateResponse(
            request,
            "world.html",
            {
                "w": world_view.view(),
                "mutation": actions.current_mutation(),
                "refresh_sec": settings.panel_refresh_sec,
                "msg": msg,
                "started": started,
            },
        )

    @app.post("/world/run")
    def world_run(action_id: str = Form(...)) -> RedirectResponse:
        """Run the world tick / micro-tick from the World screen (E1.1 machinery)."""
        if action_id not in {"world-tick", "micro-tick"}:
            return _redirect("/world?msg=unknown+action")
        try:
            run = actions.start_action(action_id)
        except actions.Busy as busy:
            return _redirect(f"/world?msg=busy:+{busy.holder.label}+is+running")
        return _redirect(f"/world?started={run.id}")

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

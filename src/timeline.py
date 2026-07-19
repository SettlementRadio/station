"""The operator TIMELINE — a local web view of now / next / the grid ahead.

A testing and operating aid alongside the terminal console (D6.3): one
auto-refreshing HTML page showing what is ON AIR right now (with a progress
bar), the generated segments queued next (air time · format · program · flow
position · duration), and the GRID's program blocks for the hours ahead — so a
listening test can be read against what the weekly grid *intends* even before
those slots are generated.

PRIVATE, like the console (CLAUDE.md hard rule: public read-only, admin
private): the server binds 127.0.0.1 ONLY and must never be exposed — the
public surface is the C8 web player + the now-playing feed, not this. Strictly
READ-ONLY: it renders `schedule.json` + the grid; it mutates nothing, so it is
always safe to leave open while the scheduler runs.

    make timeline          # then open http://127.0.0.1:8010/
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

from .config import settings
from .logging_setup import get_logger
from .scheduler import _duration_of, _load_state, onair_hosts, split_schedule
from .world import programming

log = get_logger(__name__)

_REFRESH_SEC = 5  # the page reloads itself; the server just re-renders state
_GRID_AHEAD_HOURS = 6  # how far ahead the grid-blocks panel looks
_UPCOMING_LIMIT = 30  # queued rows shown (the buffer rarely holds more)

_CSS = """
body{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#101418;
     color:#d7dde3;margin:0;padding:24px;font-size:14px}
h1{font-size:16px;margin:0 0 4px}h2{font-size:13px;color:#8fa1b3;margin:22px 0 8px;
   text-transform:uppercase;letter-spacing:.08em}
.sub{color:#8fa1b3}
table{border-collapse:collapse;width:100%}
td,th{padding:4px 10px 4px 0;text-align:left;white-space:nowrap}
th{color:#8fa1b3;font-weight:normal;border-bottom:1px solid #2a333d}
tr.boundary td{border-top:1px solid #2a333d}
.onair{background:#18212b;border:1px solid #2a333d;border-radius:6px;
       padding:14px 16px;margin-top:10px}
.bar{height:6px;background:#2a333d;border-radius:3px;margin-top:10px}
.fill{height:6px;background:#5fb0ff;border-radius:3px}
.fmt{color:#5fb0ff}.prog{color:#ffd479}.pos{color:#8fa1b3}
.now{color:#7ee08a}.idle{color:#e0967e}
"""


def _fmt_dur(sec: float) -> str:
    """`247.3` → `4:07` — compact m:ss for row durations."""
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def _esc(v: object) -> str:
    """HTML-escape any value for safe embedding (segment text is model output)."""
    return html.escape(str(v if v is not None else ""))


def _hosts_for(entry: dict, when: datetime) -> str:
    """The display hosts for an entry, via the same routing the console/feed use."""
    try:
        program = programming.program_for(when)
        return ", ".join(onair_hosts(program, entry.get("format") or ""))
    except Exception:  # noqa: BLE001 — a grid hiccup must not break the page
        return ""


def _grid_blocks(now: datetime) -> list[tuple[datetime, datetime, object]]:
    """The grid's program blocks over the look-ahead window, boundary-accurate.

    Walks `program_for` minute by minute (the grid load is mtime-cached, so this
    is a cheap in-memory scan) and coalesces runs of the same program id into
    `(start, end, Program)` blocks — what the WEEK intends, independent of what
    has been generated yet.
    """
    blocks: list[tuple[datetime, datetime, object]] = []
    t = now.replace(second=0, microsecond=0)
    end = t + timedelta(hours=_GRID_AHEAD_HOURS)
    current = programming.program_for(t)
    start = t
    while t < end:
        t += timedelta(minutes=1)
        nxt = programming.program_for(t)
        if nxt.id != current.id:
            blocks.append((start, t, current))
            current, start = nxt, t
    blocks.append((start, end, current))
    return blocks


def _onair_panel(current: dict | None, now: datetime) -> str:
    """The ON AIR box: what's playing per the schedule clock, with progress."""
    if current is None:
        return (
            '<div class="onair"><span class="idle">nothing scheduled at this '
            "minute</span> — playout is on the never-dead fallback (evergreen) "
            "until the generator catches up.</div>"
        )
    start = datetime.fromisoformat(current["air_time"])
    dur = _duration_of(current)
    elapsed = max(0.0, min((now - start).total_seconds(), dur))
    pct = 100.0 * elapsed / dur if dur else 0.0
    track = current.get("track") or {}
    track_line = (
        f'<div class="sub">♪ {_esc(track.get("title"))} — '
        f"{_esc(track.get('artist'))}</div>"
        if track.get("title")
        else ""
    )
    return (
        '<div class="onair">'
        f'<span class="fmt">{_esc(current.get("format"))}</span> · '
        f'<span class="prog">{_esc(current.get("program_name") or "—")}</span> · '
        f"{_esc(_hosts_for(current, start))} "
        f'<span class="pos">{_esc(current.get("flow_position") or "")}</span>'
        f'<div class="sub">{_esc(current.get("id"))} · started {start:%H:%M:%S} · '
        f"{_fmt_dur(elapsed)} / {_fmt_dur(dur)}</div>"
        f"{track_line}"
        f'<div class="bar"><div class="fill" style="width:{pct:.1f}%"></div></div>'
        "</div>"
    )


def _upcoming_rows(upcoming: list[dict]) -> str:
    """The queued-next table rows; a program change starts a visually marked row."""
    rows: list[str] = []
    prev_prog: object = object()
    for e in upcoming[:_UPCOMING_LIMIT]:
        start = datetime.fromisoformat(e["air_time"])
        prog = e.get("program")
        cls = ' class="boundary"' if prog != prev_prog else ""
        prev_prog = prog
        track = (e.get("track") or {}).get("title")
        extra = f" ♪ {_esc(track)}" if track else ""
        rows.append(
            f"<tr{cls}><td>{start:%H:%M:%S}</td>"
            f'<td class="fmt">{_esc(e.get("format"))}</td>'
            f'<td class="prog">{_esc(e.get("program_name") or "—")}</td>'
            f'<td class="pos">{_esc(e.get("flow_position") or "")}</td>'
            f"<td>{_fmt_dur(_duration_of(e))}</td>"
            f'<td class="sub">{_esc(e.get("id"))}{extra}</td></tr>'
        )
    return "".join(rows)


def _clock_label(program) -> str:
    """A program's clock as compact text: `talk · news@:00 · music x3`."""
    parts = []
    for step in program.clock:
        label = step.format
        if step.pin_minute is not None:
            label += f"@:{step.pin_minute:02d}"
        if step.count > 1:
            label += f" x{step.count}"
        parts.append(label)
    return " · ".join(parts) or "rotation"


def _grid_rows(now: datetime) -> str:
    """The grid-ahead table rows: the programs the week intends, hours out."""
    rows: list[str] = []
    for start, end, program in _grid_blocks(now):
        rows.append(
            f"<tr><td>{start:%H:%M}–{end:%H:%M}</td>"
            f'<td class="prog">{_esc(program.name)}</td>'
            f"<td>{_esc(', '.join(program.hosts))}</td>"
            f'<td class="sub">{_esc(_clock_label(program))}</td>'
            "</tr>"
        )
    return "".join(rows)


def render(now: datetime | None = None, state: dict | None = None) -> str:
    """The whole page as one HTML string (pure over its inputs — unit-testable)."""
    now = now or datetime.now()
    state = state if state is not None else _load_state()
    current, upcoming = split_schedule(now, state)
    runway = ""
    if upcoming:
        last_end = datetime.fromisoformat(upcoming[-1]["air_time"]) + timedelta(
            seconds=_duration_of(upcoming[-1])
        )
        runway = f" · buffer runway {_fmt_dur((last_end - now).total_seconds())}"
    status = (
        '<span class="now">● generating + airing</span>'
        if current or upcoming
        else '<span class="idle">● no schedule yet — run `make schedule`</span>'
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="{_REFRESH_SEC}">
<title>Settlement Radio — timeline</title><style>{_CSS}</style></head><body>
<h1>Settlement Radio — operator timeline</h1>
<div class="sub">{now:%A %H:%M:%S} · {status}{runway} · private (127.0.0.1) ·
refreshes every {_REFRESH_SEC}s</div>
<h2>On air</h2>{_onair_panel(current, now)}
<h2>Queued next (generated)</h2>
<table><tr><th>air</th><th>format</th><th>program</th><th>pos</th><th>dur</th>
<th>segment</th></tr>{_upcoming_rows(upcoming)}</table>
<h2>The grid ahead (next {_GRID_AHEAD_HOURS}h — what the week intends)</h2>
<table><tr><th>block</th><th>program</th><th>hosts</th><th>clock</th></tr>
{_grid_rows(now)}</table>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    """GET / → the rendered page. Anything else → 404. No writes, ever."""

    def do_GET(self) -> None:  # noqa: N802 — http.server's required name
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        try:
            body = render().encode("utf-8")
        except Exception as exc:  # noqa: BLE001 — render errors show, not crash
            body = f"<pre>timeline render error: {_esc(exc)}</pre>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        """Quiet the per-request stderr lines (the page polls every few seconds)."""


def main() -> int:
    """Serve the timeline on loopback until Ctrl-C. Read-only; exit 0."""
    addr = ("127.0.0.1", settings.timeline_port)  # LOOPBACK ONLY — never expose
    server = HTTPServer(addr, _Handler)
    log.info("timeline_start", url=f"http://{addr[0]}:{addr[1]}/")
    print(f"Operator timeline (private): http://{addr[0]}:{addr[1]}/  — Ctrl-C stops")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

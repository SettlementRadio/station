"""Commercials & sponsorship demo (PHASE_D_COMMERCIALS_TASKS D8.3).

Makes the D8 payoff audible and visible in three parts:

  1. THE SPOTS — generate ONE commercial and ONE promo for right now (the D8.0
     builder: fresh copy, gated, voiced) and print the scripts + meta, so you
     hear that a spot is written per airing, never pulled from a reel.
  2. THE BREAK, PLACED — token-free: read the shipped grid's per-program
     `break_every` (the D8.1 principle: the GRID owns the ad load) and walk a
     simulated daypart to show exactly where the sparse break lands and its
     d18 sting bracket (with each clip's on-disk status).
  3. THE "POWERED BY" READ — insert a demo sponsor row, show the run window
     working (in-window listed, before/after not), the BINDING wording guard
     correcting a "Sponsored by" attempt, and render the read; then remove the
     row (the real table stays empty until CM — donations live).

Run:  .venv/bin/python -m src.commercials_demo    (or: make commercials-demo)

Parts 1 and 3 make LIVE Anthropic + TTS calls (one spot each + the safety pass)
and need `make seed` + a reachable DB; part 2 is pure reads. Part 3 cleans up
after itself — the sponsors table is left exactly as found.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .config import settings
from .formats import make_format_segment
from .formats import sponsor as sponsor_mod
from .production import media
from .world import programming, store

_RULE = "─" * 72


def _header(title: str) -> None:
    print(f"\n{_RULE}\n{title}\n{_RULE}")


# --- 1. The spots: fresh copy every airing ------------------------------------


def demo_spots(now: datetime) -> None:
    _header("1. THE SPOTS — a commercial and a promo, written fresh for this airing")
    for mode in ("commercial", "promo"):
        seg = make_format_segment(mode, now.isoformat())
        print(f"\n--- {mode.upper()} ({seg.id}) ---")
        print(seg.script or "(evergreen fallback aired instead — see logs)")
        print(f"\naudio: {seg.audio_path}")
        interesting = {
            k: seg.meta[k]
            for k in ("mode", "promoted", "production_level_effective")
            if k in seg.meta
        }
        print(f"meta:  {interesting}")


# --- 2. The break, placed by the grid (token-free) ----------------------------


def demo_break_placement(now: datetime) -> None:
    _header("2. THE BREAK — the grid owns the ad load; stings make it sound like one")

    print("\nPer-program cadence (grid.yaml `break_every`; 0 = the show takes none):")
    seen: set[str] = set()
    for hour in range(24):
        prog = programming.program_for(now.replace(hour=hour, minute=30))
        if prog.id in seen:
            continue
        seen.add(prog.id)
        load = f"a break every {prog.break_every} content segments" or ""
        print(
            f"  {prog.name:18s} ({prog.daypart or 'fallback':11s})  "
            f"{load if prog.break_every else 'no breaks'}"
        )

    day = programming.program_for(now.replace(hour=12, minute=30))
    print(
        f"\nA simulated stretch of {day.name} "
        f"(break_every={day.break_every}, {settings.commercial_break_max_segments} "
        "spot(s) per break):"
    )
    for name in ("break_in", "break_out"):
        clip = media.sting(name)
        status = f"on disk ({clip.name})" if clip else "NOT on disk → unbracketed"
        print(f"  d18 {name:9s} sting: {status}")
    print()
    since = 0
    for slot in range(1, 9):
        print(f"  content #{slot}  (talk/news/music per the program clock)")
        since += 1
        if day.break_every and since >= day.break_every:
            since = 0
            print("    ├─ sting: break_in")
            print("    ├─ SPOT — generated fresh (commercial, or the Nth promo)")
            print("    └─ sting: break_out   → back to programming")


# --- 3. The sponsor read: run window + binding wording ------------------------

_DEMO_ID = "demo-sponsor-d8"


def demo_sponsor_read(now: datetime) -> None:
    _header('3. THE "POWERED BY" READ — run-windowed, wording guaranteed')

    demo_row = store.Sponsor(
        id=_DEMO_ID,
        name="a friend of the signal",
        powered_by_text="Proudly Sponsored By the relay guild.",  # deliberate drift
        run_start=now - timedelta(days=1),
        run_end=now + timedelta(days=1),
    )
    try:
        with store.connect() as conn:
            store.init_schema(conn)
            conn.execute("DELETE FROM sponsors WHERE id = %s", (_DEMO_ID,))
            store.insert_sponsors(conn, [demo_row])
            checks = [
                ("in window (now)", now),
                ("before the window", now - timedelta(days=30)),
                ("after the window", now + timedelta(days=30)),
            ]
            for label, when in checks:
                ids = [s.id for s in store.active_sponsors(conn, when)]
                hit = "READS" if _DEMO_ID in ids else "silent"
                print(f"  {label:20s} → {hit}")
            active = store.active_sponsors(conn, now)
    except Exception as exc:  # noqa: BLE001 — demo degrades without a DB
        print(f"  (no DB reachable — skipping the sponsor part: {exc})")
        return

    try:
        chosen = sponsor_mod.pick_sponsor([s for s in active if s.id == _DEMO_ID], 0)
        print("\nThe blurb was hand-entered with 'Sponsored By' — the guard corrects:")
        print(f"  spoken: {sponsor_mod.powered_by_script(chosen)!r}")
        seg = sponsor_mod.sponsor_read_segment(now, chosen)
        if seg is not None:
            print(f"  audio:  {seg.audio_path}")
    finally:
        # Leave the table exactly as found — empty until CM.
        with store.connect() as conn:
            conn.execute("DELETE FROM sponsors WHERE id = %s", (_DEMO_ID,))
        print("\n(demo sponsor row removed — the table stays empty until CM)")


def main() -> int:
    now = datetime.now()
    demo_spots(now)
    demo_break_placement(now)
    demo_sponsor_read(now)
    print(f"\n{_RULE}\ndone — texture, not interruption.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

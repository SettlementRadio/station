"""Layer 3 (minimal) — Claude writes Vell's night-shift segment from the canon.

This is the Phase A "writers' room": a single function that turns the canon plus
the current clock into one in-character spoken script. There is no multi-agent
showrunner yet (see docs/ARCHITECTURE.md, Layer 3) — just `write_segment_script`.

Two things this module is careful about:

* **The +600yr clock.** The in-world time is `real time + 600 years`. That mapping
  now lives in `world/clock.py` (the single source, B2); this module just calls
  `clock.render_wall_clock` and hands the result to Claude in the small, per-call
  system prompt so the time check is real (CANON.md "The time concept").
* **The cost lever.** The canon is large and stable; it is passed to
  `llm.generate` as `cached_context` (a prompt-cache breakpoint), so repeat runs
  pay ~0.1x on it. The variable instructions + clock go in `system`. (CLAUDE.md
  "Cost levers".)
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from .config import settings
from .logging_setup import get_logger
from .providers import llm
from .world import clock

log = get_logger(__name__)

# The spoken word-count guidance (`settings.writer_words_low` / `writer_words_high`)
# and the script token cap live in the typed settings module — config over
# hardcoding (CLAUDE.md). The word-count guidance was tuned in B0 to land within
# ~10% of the length target at Kokoro's pace; retune those settings if the TTS
# pace changes. The +600yr clock itself lives in `world/clock.py` (B2).


def _inworld_clock(now_iso: str) -> str:
    """Render `now_iso` as a spoken time-check sentence for Claude.

    The in-world wall clock (`real time + 600 years`, keeping the real weekday)
    comes from `world/clock.py` — the single source of that mapping (B2). Here we
    just wrap it with the part-of-day mood and the time-check instruction.
    """
    now = datetime.fromisoformat(now_iso)
    part_of_day = _part_of_day(now.hour)
    # e.g. "Tuesday, 16 June 2626, 02:14 (the deep, quiet hours of the night)"
    return (
        f"{clock.render_wall_clock(now)} "
        f"({part_of_day}). Give a natural, accurate time check for this exact "
        f"time ({now:%H:%M})."
    )


def _part_of_day(hour: int) -> str:
    """A human phrase for the hour, to steer the time check's mood."""
    if hour < 5:
        return "the deep, quiet hours of the night"
    if hour < 8:
        return "the last of the night, edging toward dawn"
    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    if hour < 21:
        return "evening"
    return "late night"


def _build_system_prompt(now_iso: str) -> str:
    """The small, per-call instructions: who is talking, the clock, the spec.

    Stays compact on purpose — the bulky, stable canon rides in `cached_context`
    so only this part pays full price on a cache hit.
    """
    clock = _inworld_clock(now_iso)
    return (
        "You are the writer for Settlement Radio, scripting the night-shift "
        "host Vell. Write the SPOKEN SCRIPT ONLY — exactly the words Vell says "
        "aloud, with no stage directions, headings, speaker labels, or notes.\n\n"
        f"Right now, settlement time, it is: {clock}\n\n"
        "Write one ~5-minute night-shift talk segment, "
        f"{settings.writer_words_low}-{settings.writer_words_high} words, "
        "fully in character per the world bible and Vell's character card:\n"
        "  - Open with a soft greeting to the one listener out there and a real, "
        "accurate time check ('settlement time') for the time given above.\n"
        "  - Move into a short, warm musing tied to ONE canon fact.\n"
        "  - Lead into a piece of music — described in-world, not named or "
        "played (this is talk only).\n"
        "  - Close with a small, hopeful line.\n"
        "Stay entirely inside the fiction: never mention being an AI, never "
        "reference real-world brands, franchises, or living people. Warm, low, "
        "unhurried, intelligent, a little wry — never cynical, never dystopian."
    )


def safety_check(text: str) -> str:
    """Placeholder content-safety gate (no-op in Phase A).

    Nothing is public in Phase A, so this just returns the text unchanged. It
    exists so the script step already has the seam where a real gate slots in
    before any public broadcast (CLAUDE.md "Content safety").
    """
    return text


def write_segment_script(
    canon_text: str,
    now_iso: str,
    *,
    on_token: Callable[[str], None] | None = None,
) -> str:
    """Ask Claude to write Vell's ~5-minute night-shift segment.

    Args:
        canon_text: the full contents of docs/CANON.md (the world bible).
        now_iso: the current real time as an ISO 8601 string; the in-world
            clock (real + 600 years) is derived from it for the time check.
        on_token: optional progress callback, forwarded to `llm.generate`, so a
            caller can show that the ~25s generation is alive (not frozen).

    Returns:
        The spoken script, run through the (placeholder) safety gate.
    """
    log.info("write_segment_script_start", now=now_iso, canon_chars=len(canon_text))
    system = _build_system_prompt(now_iso)
    script = llm.generate(
        "Write tonight's segment now.",
        system=system,
        model=settings.llm_default_tier,  # CLAUDE.md: the default writing brain
        cached_context=canon_text,  # cost lever: canon as a cache breakpoint
        max_tokens=settings.writer_max_tokens,
        on_token=on_token,
    )
    script = safety_check(script.strip())
    log.info("write_segment_script_done", words=len(script.split()))
    return script


if __name__ == "__main__":
    # Runnable check: print a fresh segment for the current time.
    #   .venv/bin/python -m src.writer
    from datetime import datetime as _dt

    script = write_segment_script(
        settings.canon_path.read_text(), _dt.now().isoformat()
    )
    print(script)  # the generated script is this CLI's deliverable (stdout)

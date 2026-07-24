"""R5.2 (=E1.9) — the tick digest: "what happened last night, and how today unfolds".

After each nightly tick / intra-day micro-tick, this turns the tick's own
`TickResult` / `MicroTickResult` into a short, human-readable note the operator can
read in 30 seconds on the panel's World screen — plus the structured facts behind it.

Two rules:
- **Best-effort, never fatal.** The digest is written AFTER the tick has committed,
  in its own transaction; any failure (LLM down, DB hiccup, disabled) is logged and
  skipped — it must never fail or roll back the tick itself.
- **From the tick's result, cheaply.** Facts come from the ids the tick already
  returned (new + advanced stories) plus a couple of small reads; the prose is one
  hard-capped haiku call. Stored as a capped list in the `tick_digests` state row.
"""

from __future__ import annotations

import json
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..providers import llm
from . import events, store

log = get_logger(__name__)

DIGEST_KEY = "tick_digests"


# --- Facts (pure-ish: reads the store, no LLM) -------------------------------


def _next_planned_beat(conn, story_id: str, now: datetime) -> dict | None:  # noqa: ANN001
    """The soonest not-yet-landed planned beat of a story (the plan ahead), or None."""
    for beat in store.story_beats(conn, story_id):
        if beat.planned and not events.has_landed(beat, now):
            return {
                "title": beat.title,
                "when": beat.in_world_datetime.strftime("%Y-%m-%d %H:%M"),
                "phrase": events.relative_phrase(beat, now),
            }
    return None


def build_facts(conn, result, *, kind: str, now: datetime) -> dict:  # noqa: ANN001
    """Structured facts for one tick/micro-tick run — the digest's raw material."""
    facts: dict = {"kind": kind, "when": now.isoformat(timespec="seconds")}

    if kind == "micro-tick":
        facts["micro_tick"] = getattr(result, "micro_tick", None)
        facts["acted"] = bool(getattr(result, "acted", False))
        facts["reason"] = getattr(result, "reason", "")
        sid = getattr(result, "story_id", None)
        if sid:
            story = store.get_story(conn, sid)
            facts["story"] = {"id": sid, "title": story.title if story else sid}
        return facts

    # nightly tick
    facts["tick"] = getattr(result, "tick", None)
    for k in ("proposed", "accepted", "dropped", "duplicates", "advanced", "resolved"):
        facts[k] = getattr(result, k, 0)
    facts["pending"] = getattr(result, "pending", 0)  # R5.3 majors awaiting approval

    new_stories = []
    figures = quotes = 0
    for sid in getattr(result, "story_ids", []):
        story = store.get_story(conn, sid)
        if story is None:
            continue
        figures += len(store.figures_for_story(conn, sid))
        quotes += len(store.quotes_for_story(conn, sid))
        new_stories.append(
            {
                "id": sid,
                "title": story.title,
                "tags": list(story.tags),
                "status": story.status,
            }
        )
    facts["new_stories"] = new_stories
    facts["new_figures"] = figures
    facts["new_quotes"] = quotes

    advanced = []
    for sid in getattr(result, "advanced_ids", []):
        story = store.get_story(conn, sid)
        if story is None:
            continue
        advanced.append(
            {
                "id": sid,
                "title": story.title,
                "stage": story.arc_stage,
                "next_planned": _next_planned_beat(conn, sid, now),
            }
        )
    facts["advanced"] = advanced
    return facts


# --- The prose (one haiku call) ----------------------------------------------


def _facts_to_prompt(facts: dict) -> str:
    """A compact text rendering of the facts for the digest model."""
    lines: list[str] = []
    if facts["kind"] == "micro-tick":
        if facts.get("acted"):
            st = facts.get("story", {})
            lines.append(f"Intra-day micro-tick advanced: {st.get('title', '?')}.")
        else:
            lines.append(f"Micro-tick was a quiet run ({facts.get('reason')}).")
        return "\n".join(lines)

    lines.append(
        f"Nightly tick #{facts.get('tick')}: proposed {facts.get('proposed')}, "
        f"accepted {facts.get('accepted')}, dropped {facts.get('dropped')} "
        f"(duplicates {facts.get('duplicates')}); advanced {facts.get('advanced')} "
        f"stories ({facts.get('resolved')} resolved); "
        f"{facts.get('new_figures')} new people, {facts.get('new_quotes')} quotes."
    )
    for s in facts.get("new_stories", []):
        tags = f" [{', '.join(s['tags'])}]" if s["tags"] else ""
        flag = (
            " (MAJOR — awaiting operator approval)"
            if s.get("status") == "pending"
            else ""
        )
        lines.append(f"NEW: {s['title']}{tags}{flag}")
    for a in facts.get("advanced", []):
        nxt = a.get("next_planned")
        tail = f" — next planned: {nxt['title']} ({nxt['phrase']})" if nxt else ""
        lines.append(f"ADVANCED [{a['stage']}]: {a['title']}{tail}")
    return "\n".join(lines)


def generate_text(facts: dict) -> str:
    """Write the 2–4 sentence operator digest from the facts (haiku-tier)."""
    system = (
        "You are the overnight desk editor for a fictional radio station's world "
        "simulation, briefing the human operator. Given the raw run facts below, write "
        "a SHORT digest (2–4 plain sentences) of what changed in the world and how "
        "today should unfold — lead with the most notable new or advanced story, name "
        "the stories, and mention any planned beats still to come today. Plain, "
        "concrete, factual; no preamble, no bullet points, no in-character flourish."
    )
    return llm.generate(
        f"Run facts:\n{_facts_to_prompt(facts)}\n\nWrite the digest.",
        system=system,
        model=settings.world_digest_tier,
        max_tokens=settings.world_digest_max_tokens,
    ).strip()


# --- Store (a capped list in the `tick_digests` state row) -------------------


def _store_entry(conn, entry: dict) -> None:  # noqa: ANN001
    """Prepend `entry` to the digest list and cap it at `world_digest_keep`."""
    raw = store.get_state(conn, DIGEST_KEY)
    digests = json.loads(raw) if raw else []
    if not isinstance(digests, list):
        digests = []
    digests.insert(0, entry)
    del digests[settings.world_digest_keep :]
    store.set_state(conn, DIGEST_KEY, json.dumps(digests))


def generate_and_store(result, *, kind: str, now: datetime | None = None) -> str | None:  # noqa: ANN001
    """Build facts → write the digest → store it. Best-effort; returns the text or None.

    Skips silently when `world_digest_enabled` is off, or when a micro-tick was a quiet
    run (nothing happened — no digest worth reading). Never raises: a failure here must
    not fail the tick job that called it.
    """
    if not settings.world_digest_enabled:
        return None
    now = now or datetime.now()
    try:
        if kind == "micro-tick" and not getattr(result, "acted", False):
            return None  # a quiet micro-tick writes nothing worth a digest
        with store.connect() as conn:
            facts = build_facts(conn, result, kind=kind, now=now)
            text = generate_text(facts)
            entry = {
                "when": facts["when"],
                "kind": kind,
                "tick": facts.get("tick") or facts.get("micro_tick"),
                "text": text,
                "facts": facts,
            }
            _store_entry(conn, entry)
        log.info("tick_digest_written", kind=kind, chars=len(text))
        return text
    except Exception as exc:  # noqa: BLE001 — the digest must never fail the tick
        log.warning("tick_digest_failed", kind=kind, error=str(exc))
        return None


# --- Read side (for the panel) -----------------------------------------------


def recent(conn, limit: int | None = None) -> list[dict]:  # noqa: ANN001
    """The recent digests, newest first (from the `tick_digests` state row)."""
    raw = store.get_state(conn, DIGEST_KEY)
    if not raw:
        return []
    try:
        digests = json.loads(raw)
    except ValueError:
        return []
    if not isinstance(digests, list):
        return []
    return digests[:limit] if limit else digests

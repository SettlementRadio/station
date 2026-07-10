"""CO0 — repeatable prompt-cache cost probe (docs/CACHE_OPTIMIZATION_TASKS.md).

Measures how the stable prefix (world bible + character cards) actually caches
across the station's distinct speaker sets, on the real seeded stack. It runs one
representative **mixed cycle** — talk + news + music + commercial — **twice
back-to-back** and rolls up the three token fields the cache economics turn on
(`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`).

Two passes is the point: pass 2 is where a *shared* bible would read from cache.
Today (pre-CO2) each distinct speaker set caches its own private copy of the
bible, so pass 1 shows one `cache_creation` per speaker set — the waste the CO
pack removes. Run the probe unchanged after CO2 for the AFTER table (CO4).

What it deliberately does NOT do: TTS, audio stitching, the safety gate, or the
scheduler — the cache key is the system prefix up to the `cache_control`
breakpoint (`cached_context`), so a tiny user prompt against the real assembled
context measures exactly the caching the full pipeline gets, at a fraction of
the output cost.

Run (needs `make seed-canon` + a populated .env):

    .venv/bin/python -m src.costprobe      (or: make costprobe)

Makes real Anthropic calls (~8 small ones; the spend is dominated by the cache
writes of the ~50k-token bible on pass 1).
"""

from __future__ import annotations

from datetime import datetime

from .config import settings
from .formats import FORMATS
from .logging_setup import get_logger
from .providers import llm
from .world import context

log = get_logger(__name__)

# The mixed cycle: the four on-air formats, covering every distinct speaker set
# (talk = vell+wren, news = thorn, music = vell, commercial = vell). Order and
# membership are intrinsic to what this probe measures, so they live here, not in
# settings (config.py convention).
_PROBE_FORMATS: tuple[str, ...] = ("talk", "news", "music", "commercial")

# A minimal user turn: it sits AFTER the cache breakpoint, so its content has no
# effect on what caches — keep the output spend near zero.
_PROBE_PROMPT = "This is a cost probe. Reply with the single word: OK."
_PROBE_MAX_TOKENS = 16

_USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def run_probe(now: datetime | None = None) -> list[dict]:
    """Run the two-pass mixed cycle; return one usage row per call.

    Each row: {pass, format, tier, input_tokens, cache_creation_input_tokens,
    cache_read_input_tokens}. The context for each format is assembled ONCE and
    reused across both passes — the probe measures the cache topology, and a
    byte-identical prefix per format is exactly what consecutive production
    top-ups send (bible + cards are stable; the dynamic slice rides after the
    breakpoint).
    """
    now = now or datetime.now()
    tier = settings.llm_default_tier

    contexts = {
        name: context.assemble(now, speakers=list(FORMATS[name].speaker_ids()))
        for name in _PROBE_FORMATS
    }

    rows: list[dict] = []
    current: dict = {}

    def _listener(event: dict) -> None:
        current.update({k: event.get(k, 0) for k in _USAGE_KEYS})

    llm.add_usage_listener(_listener)
    try:
        for pass_no in (1, 2):
            for name in _PROBE_FORMATS:
                ctx = contexts[name]
                current.clear()
                # Send the stable core exactly as production does post-CO2: the
                # shared bible as its own block + the per-speaker-set cards. This is
                # what makes pass 1 show the bible cache_created ONCE across formats
                # (shared) instead of once per speaker set.
                llm.generate(
                    _PROBE_PROMPT,
                    model=tier,
                    bible=ctx.bible,
                    cards=ctx.cards_block,
                    max_tokens=_PROBE_MAX_TOKENS,
                )
                row = {"pass": pass_no, "format": name, "tier": tier, **current}
                rows.append(row)
                log.info("costprobe_call", **row)
    finally:
        llm.remove_usage_listener(_listener)
    return rows


def render_table(rows: list[dict]) -> str:
    """Render the per-call rows plus per-pass totals as a markdown table."""
    header = "| pass | format | tier | input | cache_creation | cache_read |"
    rule = "|---|---|---|---:|---:|---:|"
    lines = [header, rule]
    for r in rows:
        lines.append(
            f"| {r['pass']} | {r['format']} | {r['tier']} "
            f"| {r.get('input_tokens', 0)} "
            f"| {r.get('cache_creation_input_tokens', 0)} "
            f"| {r.get('cache_read_input_tokens', 0)} |"
        )
    for pass_no in sorted({r["pass"] for r in rows}):
        subset = [r for r in rows if r["pass"] == pass_no]
        totals = {k: sum(r.get(k, 0) for r in subset) for k in _USAGE_KEYS}
        lines.append(
            f"| {pass_no} | **total** | — "
            f"| {totals['input_tokens']} "
            f"| {totals['cache_creation_input_tokens']} "
            f"| {totals['cache_read_input_tokens']} |"
        )
    return "\n".join(lines)


# --- CO4: A/B quality proof (the split doesn't change what the model sees) ----
# The structural proof is CO1's equivalence test: bible + cards is byte-identical
# to the single cached_context, so the model input is unchanged by construction.
# This A/B is the empirical corroboration — generate a real segment BOTH ways
# (two-block post-split vs single-block pre-split) on a fixed clock, and diff. The
# request text is identical, so any script difference is model sampling noise, not
# the cache split. Both paths live in the seam today, so no pre-split checkout is
# needed — the single-`cached_context` arm IS the pre-split behaviour.

import difflib  # noqa: E402 — grouped with the CO4 A/B code it serves

# A fixed clock for the A/B, so the run is repeatable (the "fixed seed" is the
# seeded world + this pinned `now`). A night-shift time suits the station's voice.
_AB_CLOCK = datetime(2026, 7, 9, 2, 14)

_AB_INSTRUCTION = (
    "You are writing for Settlement Radio. Using the world bible and character "
    "card(s) in the cached context, and the current world slice below, write a "
    "short (~120 word) in-character spoken passage for this moment. Spoken words "
    "only — no stage directions, headings, or labels.\n\nWhat's true right now:\n"
)


def run_ab(now: datetime | None = None) -> list[dict]:
    """Generate one segment per speaker set BOTH ways; return the pair + a diff.

    For each format's speaker set, assemble the real context on the fixed clock,
    then generate the same passage via the two-block path (`bible`/`cards`,
    post-split) and the single-block path (`cached_context`, pre-split). The two
    requests carry byte-identical model input (asserted here), so the diff isolates
    pure sampling noise.
    """
    now = now or _AB_CLOCK
    tier = settings.llm_default_tier
    rows: list[dict] = []
    for name in _PROBE_FORMATS:
        ctx = context.assemble(now, speakers=list(FORMATS[name].speaker_ids()))
        # The load-bearing structural fact, re-asserted at runtime: the two cache
        # topologies feed the model the SAME bytes.
        assert ctx.bible + ctx.cards_block == ctx.cached_context, name
        system = f"{_AB_INSTRUCTION}{ctx.dynamic}"
        user = "Write the passage now."

        post = llm.generate(
            user, system=system, model=tier, bible=ctx.bible, cards=ctx.cards_block
        )
        pre = llm.generate(
            user, system=system, model=tier, cached_context=ctx.cached_context
        )
        ratio = difflib.SequenceMatcher(None, pre, post).ratio()
        rows.append(
            {
                "format": name,
                "identical_input": True,
                "ratio": ratio,
                "pre": pre,
                "post": post,
            }
        )
        log.info("costprobe_ab", format=name, similarity=round(ratio, 3))
    return rows


def render_ab(rows: list[dict]) -> str:
    """Render the A/B: per-format input-equivalence + script-similarity + samples."""
    lines = [
        "| format | model input identical | script similarity |",
        "|---|---|---:|",
    ]
    for r in rows:
        mark = "yes" if r["identical_input"] else "NO"
        lines.append(f"| {r['format']} | {mark} | {r['ratio']:.2f} |")
    lines.append("")
    for r in rows:
        lines.append(f"### {r['format']}\n")
        lines.append(f"**pre-split (single block):** {r['pre']}\n")
        lines.append(f"**post-split (bible + cards):** {r['post']}\n")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    # `python -m src.costprobe`      -> the cost probe (token split).
    # `python -m src.costprobe ab`   -> the CO4 A/B quality proof (script diff).
    if len(sys.argv) > 1 and sys.argv[1] == "ab":
        print(render_ab(run_ab()))
    else:
        print(render_table(run_probe()))

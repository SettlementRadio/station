"""Register + repetition metrics over probe transcripts."""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

TURN = re.compile(r"^([A-Z][A-Za-z' \-]{1,24})(?: \[[a-z]+\])?:\s*(.*)$")
CONTR = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.I)
# real-speech markers: fillers, false starts, repair, hedges
DISFLU = re.compile(
    r"\b(erm|um|uh|sorry\W|hang on|what\?|say again|wait,|no, I mean|"
    r"I mean\b|you know\b|sort of\b|kind of\b|like,|anyway\b|whatever\b)",
    re.I,
)


def scripts_from_json(p: Path) -> list[tuple[str, str]]:
    out = []
    for e in json.loads(p.read_text()):
        s = e.get("script")
        if s:
            out.append(
                (
                    f"{e.get('air_time', '')[11:16]} {e.get('format')}/"
                    f"{(e.get('meta') or {}).get('program', '')}",
                    s,
                )
            )
    return out


def scripts_from_txt(p: Path) -> list[tuple[str, str]]:
    out, cur, buf = [], None, []
    for line in p.read_text().splitlines():
        if line.startswith("=" * 20):
            if cur:
                out.append((cur, "\n".join(buf)))
            cur, buf = None, []
        elif (
            cur is None
            and line
            and not line.startswith(("-", "BEAT:", "events_in_ctx"))
        ):
            cur = line.strip()
        elif cur and not line.startswith(("BEAT:", "-" * 20, "events_in_ctx")):
            buf.append(line)
    if cur:
        out.append((cur, "\n".join(buf)))
    return out


def analyse(items: list[tuple[str, str]]) -> None:
    print(f"segments analysed: {len(items)}\n")
    all_turn_words, all_lines = [], 0
    disflu_hits, contr_total, word_total = 0, 0, 0
    proper = Counter()
    for label, script in items:
        turns = []
        for line in script.splitlines():
            m = TURN.match(line.strip())
            if m and len(m.group(1).split()) <= 3:
                turns.append(m.group(2))
        if not turns:
            continue
        w = [len(t.split()) for t in turns]
        all_turn_words += w
        all_lines += len(turns)
        text = " ".join(turns)
        word_total += len(text.split())
        contr_total += len(CONTR.findall(text))
        disflu_hits += len(DISFLU.findall(text))
        for n in re.findall(r"\b[A-Z][a-z]{3,}(?:[ -][A-Z][a-z]{2,})?\b", text):
            proper[n] += 1
        print(
            f"  {label[:70]:70s} turns={len(turns):3d} "
            f"median_turn={statistics.median(w):5.1f}w words={len(text.split()):4d}"
        )
    print()
    print(f"TOTAL turns: {all_lines}")
    print(
        f"median turn length: {statistics.median(all_turn_words):.1f} words "
        f"(mean {statistics.mean(all_turn_words):.1f})"
    )
    n = len(all_turn_words)
    short = sum(1 for x in all_turn_words if x <= 3)
    long_ = sum(1 for x in all_turn_words if x >= 40)
    print(f"turns <= 3 words: {100 * short / n:.0f}%")
    print(f"turns >= 40 words: {100 * long_ / n:.0f}%")
    print(f"contractions per 100 words: {100 * contr_total / word_total:.1f}")
    print(f"hedge/filler markers per 1000 words: {1000 * disflu_hits / word_total:.1f}")
    print()
    print("MOST-NAMED PROPER NOUNS across the run (the topic footprint):")
    for n, c in proper.most_common(25):
        print(f"  {c:4d}  {n}")


if __name__ == "__main__":
    p = Path(sys.argv[1])
    analyse(scripts_from_json(p) if p.suffix == ".json" else scripts_from_txt(p))

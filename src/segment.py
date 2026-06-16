"""Seam #2 — the Segment, the unit that everything else produces and plays.

A Segment is one piece of programming: its audio plus the metadata that says
how long it should run, when it should air, and how far ahead it may be made.
The whole pipeline is `make_segment(spec) -> Segment` (see docs/ARCHITECTURE.md
"Seam #2"). The two DIALS — `length_target_sec` and `lead_time_sec` — are
inputs, never hardcoded, so the same code path serves a 3-hour overnight block
and a 60-second near-live drop. Only the numbers (and the model/TTS tier) change.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Segment:
    id: str
    format: str               # "talk" | "news" | "music" | "ident" ...
    length_target_sec: int    # the DIAL: 3600 for an hour, 60 for near-live. NEVER hardcode.
    air_time: str | None = None   # ISO time this should air; None = "whenever"
    lead_time_sec: int = 0        # how long before air it may be generated. The other DIAL.
    script: str | None = None
    audio_path: str | None = None
    disclosure: bool = True       # AI-generation disclosure attached
    meta: dict = field(default_factory=dict)

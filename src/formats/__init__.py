"""Program format templates (PHASE_B_TASKS.md B5) — reusable show backbones.

Three templates, each a function `(now, context) -> Segment` that fills a proven
skeleton so generation isn't a blank page:

  * `news`  — sting → N in-world headlines → sign-off            (single DJ)
  * `talk`  — open → banter → music lead-in → close              (two DJs; wraps B4)
  * `music` — DJ intro → [song slot marker] → back-announce      (single DJ)

This module is the registry + dispatcher. Each format declares which cast it
needs; `make_format_segment` assembles exactly that slice of the world (via
`context.assemble` — the same cached-core + dynamic-now seam every writer uses)
and hands it to the template. The templates themselves live in sibling modules and
never touch the DB directly.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..config import settings
from ..logging_setup import get_logger
from ..providers import tts
from ..segment import Segment
from ..world import context
from ..world.context import AssembledContext

# Import the builders under aliases so the submodules (`formats.news`, etc.) keep
# their names — `make_format_segment` is the public entry point, not the builders.
from .music import music as build_music
from .news import news as build_news
from .talk import talk as build_talk

log = get_logger(__name__)


@dataclass(frozen=True)
class FormatSpec:
    """One format: its builder and the cast ids it needs assembled into context."""

    build: Callable[[datetime, AssembledContext], Segment]
    speaker_ids: Callable[[], Sequence[str]]


# The registry. Speaker ids are read from `settings` lazily (a callable) so an
# operator who retunes them in `.env` doesn't need a code change — and `talk`
# tracks the same `convo_speaker_ids` the B4 conversation uses.
FORMATS: dict[str, FormatSpec] = {
    "news": FormatSpec(build_news, lambda: [settings.format_news_speaker_id]),
    "talk": FormatSpec(build_talk, lambda: settings.convo_speaker_ids),
    "music": FormatSpec(build_music, lambda: [settings.format_music_speaker_id]),
}


def stamp_duration(seg: Segment) -> Segment:
    """Record the rendered audio's MEASURED duration on the Segment (C2).

    The single post-render chokepoint: every format (and its evergreen fallback)
    returns through `make_format_segment`, so stamping here gives the scheduler
    honest airtime accounting without touching each builder. A probe failure is
    logged and leaves `actual_duration_sec=None` (unknown) rather than aborting a
    segment that rendered fine — the scheduler falls back to the length target.
    """
    if not seg.audio_path:
        return seg
    try:
        seg.actual_duration_sec = tts.probe_duration(seg.audio_path)
    except Exception as exc:  # ffprobe missing/unreadable — don't kill the segment
        log.warning("format_duration_probe_failed", seg_id=seg.id, error=str(exc))
    return seg


def make_format_segment(
    name: str,
    now_iso: str,
    *,
    topic: str | None = None,
) -> Segment:
    """Build a `Segment` for the named format at `now_iso`.

    Assembles the world context with the format's cast (so a single-DJ news desk
    gets one card, a two-DJ talk gets both), then runs the template. `topic`
    steers canon retrieval (see `context.assemble`). The returned Segment carries
    its measured `actual_duration_sec` (C2) so the scheduler times the playlist on
    real audio length.
    """
    if name not in FORMATS:
        raise ValueError(f"unknown format {name!r}; expected one of {sorted(FORMATS)}")
    spec = FORMATS[name]
    now = datetime.fromisoformat(now_iso)
    log.info("format_dispatch", name=name, topic=topic)
    ctx = context.assemble(now, topic=topic, speakers=spec.speaker_ids())
    return stamp_duration(spec.build(now, ctx))


__all__ = ["FORMATS", "FormatSpec", "make_format_segment", "stamp_duration"]

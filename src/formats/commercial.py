"""The `commercial` / `promo` format — short in-world spots (D8.0).

ONE builder, two registry entries sharing it (the mode is bound per entry in
`formats.FORMATS`): `commercial` writes a spot for a fictional +600y product,
service, or small business; `promo` is a station self-promo (the station itself,
or the current named show from the D6 grid — truthful facts only). Sharing the
builder keeps the gate + render plumbing in one place.

Load-bearing D8 principle: spots are GENERATED, never a prerecorded reel — a
break is never the same spot twice. Every airing writes fresh copy (the small-
catalogue problem a rotating jingle has is exactly what infinite in-character
copy avoids). The only prerecorded ad audio is the sparse L4 brand sting below.

The producer pattern is `music.py`/`news.py`'s C0 discipline, copied verbatim:
`generate_safe(lambda: llm.generate(..., cached_context=...))` → on a persistent
safety flag, `evergreen.evergreen_segment(...)` (a flagged spot NEVER airs) →
else a single-voice render. The prompt enforces the CLAUDE.md IP boundary (a
fictional product only — never a real brand, franchise, trademark, or person)
and the gate backs it up.

Production spectrum (D8.0): `settings.format_commercial_production_level` picks
how "produced" the spot sounds — L1 voiced read (default), L2 read over a ducked
bed (D7.1's primitive), L3 multi-voice/testimonial (needs D9's guest voice + a
D10 figure; degrades to L1 until D9 exists), L4 a curated brand-sting bookend
(degrades to L1 while no clip is on disk). Richer levels reuse the other
sub-packs' seams — no new audio plumbing lives here.
"""

from __future__ import annotations

from datetime import datetime

from .. import evergreen
from ..config import settings
from ..flow import ShowFlow
from ..logging_setup import get_logger
from ..production import media, mix
from ..providers import llm
from ..safety import generate_safe
from ..segment import Segment
from ..world import clock, programming
from ..world.context import AssembledContext
from . import common

log = get_logger(__name__)

MODE_COMMERCIAL = "commercial"
MODE_PROMO = "promo"


def _promo_subject(now: datetime) -> str | None:
    """What a promo promotes: the current NAMED show, or None (the station itself).

    Picked in code, not by the model, so `meta["promoted"]` is truthful and
    auditable. The reserved default program isn't a named show — promoting it
    would invent one — so it (and a grid failure) falls back to the station.
    """
    if not settings.programming_enabled:
        return None
    try:
        program = programming.program_for(now)
    except Exception as exc:  # noqa: BLE001 — a grid problem must not kill the spot
        log.warning("format_commercial_grid_unavailable", error=str(exc))
        return None
    if program.id == settings.programming_default_program:
        return None
    return program.name


def _spot_brief(mode: str, subject: str | None) -> str:
    """The mode-specific instruction block of the system prompt."""
    if mode == MODE_COMMERCIAL:
        return (
            "The spot: a short in-world COMMERCIAL. Invent ONE fictional product, "
            "service, or small business that could plausibly exist in the settled "
            "worlds — a dockside noodle counter, a thermal-liner outfitter, a "
            "relay-time chandler — and pitch it the way a small local business "
            "sounds on late-night radio. Invent it FRESH for this airing; give it "
            "a name, one concrete reason to care, and a light closing tag line."
        )
    if subject:
        return (
            f'The spot: a short STATION PROMO for the station\'s own show "{subject}". '
            "Say what it is and why to stay tuned, warmly and in-character. Keep "
            "any time reference loose and in-world ('through the deep night', "
            "never a real-world date or clock time). Only claim things true of "
            "the station; invent no shows, hosts, or events."
        )
    return (
        "The spot: a short STATION PROMO for Settlement Radio itself — the "
        "station, its signal, its company through the hours. Warm, truthful, "
        "in-character. Only claim things true of the station; invent no shows, "
        "hosts, or events."
    )


def _build_system(
    ctx: AssembledContext, now: datetime, dj: str, mode: str, subject: str | None
) -> str:
    world = f"\nWhat's true right now:\n{ctx.dynamic}\n" if ctx.dynamic else ""
    return (
        "You are the writer for Settlement Radio, scripting the host "
        f"{dj} reading a short spot between segments. Write the SPOKEN SCRIPT "
        "ONLY — no stage directions, headings, speaker labels, or notes.\n\n"
        f"Settlement time right now: {clock.render_wall_clock(now)}.\n"
        f"{world}\n"
        f"{_spot_brief(mode, subject)}\n\n"
        "Hard rules: stay entirely inside the fiction — NEVER name a real brand, "
        "company, franchise, trademark, or person, living or dead; no real-world "
        "places, products, or currencies; never mention being an AI. Tone: "
        "texture, not a hard sell — charming, brief, a little wry; no shouting, "
        "no urgency tricks. "
        f"Aim for {settings.format_commercial_words_low}-"
        f"{settings.format_commercial_words_high} words."
    )


def _apply_production(audio_path: str, seg_id: str, level: int) -> tuple[str, int]:
    """Apply the requested production level to the rendered read; return
    `(final_audio_path, effective_level)`.

    Reuses the other sub-packs' machinery — D7.1's `duck_bed_under` for L2, a
    curated `media.sting("brand")` bookend for L4 — and DEGRADES to the plain L1
    read (logged, and visible in the meta via the effective level) when a level's
    dependency isn't built or its clip isn't on disk. L3 (multi-voice scene /
    figure testimonial) is the D9 guest voice × a D10 figure — wired here as the
    degrade until D9 lands. Mixed renders follow the D7.3 `<id>-bedded.mp3`
    naming so the C2.5 prune ages them out like any render.
    """
    if level <= 1:
        return audio_path, 1

    if level == 2:
        bed = media.bed_for_format("commercial")
        if bed is None:
            log.warning(
                "format_commercial_level_degraded",
                seg_id=seg_id,
                requested=2,
                reason="no commercial bed on disk",
            )
            return audio_path, 1
        out = str(settings.segments_dir / f"{seg_id}-bedded.mp3")
        mixed = mix.duck_bed_under(audio_path, str(bed), out)
        return (mixed, 2) if mixed == out else (audio_path, 1)

    if level == 3:
        log.warning(
            "format_commercial_level_degraded",
            seg_id=seg_id,
            requested=3,
            reason="L3 needs the D9 guest voice (+ a D10 figure); not built yet",
        )
        return audio_path, 1

    # level >= 4 — the sparse brand-sting bookend (the only prerecorded ad audio).
    brand = media.sting("brand")
    if brand is None:
        log.warning(
            "format_commercial_level_degraded",
            seg_id=seg_id,
            requested=level,
            reason="no brand sting on disk",
        )
        return audio_path, 1
    out = str(settings.segments_dir / f"{seg_id}-stung.mp3")
    stung = mix.attach_sting(audio_path, str(brand), out, position="after")
    return (stung, 4) if stung == out else (audio_path, 1)


def spot(now: datetime, ctx: AssembledContext, *, mode: str) -> Segment:
    """Generate one `commercial`/`promo` Segment — fresh copy, gated, voiced.

    C0: the draft runs through `generate_safe`; a persistent safety flag drops
    the slot to an evergreen segment — a flagged spot is NEVER aired.
    """
    if mode not in (MODE_COMMERCIAL, MODE_PROMO):
        raise ValueError(f"unknown spot mode {mode!r}")
    dj_card = common.require_speaker(ctx, mode)
    seg_id = common.make_seg_id(mode, now)
    level = settings.format_commercial_production_level
    subject = _promo_subject(now) if mode == MODE_PROMO else None
    log.info(
        "format_commercial_start",
        seg_id=seg_id,
        mode=mode,
        dj=dj_card.id,
        level=level,
        promoted=subject,
    )

    system = _build_system(ctx, now, dj_card.name, mode, subject)
    script, safety = generate_safe(
        lambda: llm.generate(
            "Write the spot now.",
            system=system,
            model=settings.llm_default_tier,
            bible=ctx.bible,
            cards=ctx.cards_block,
            max_tokens=settings.format_commercial_max_tokens,
        )
    )
    if not safety.ok:
        # C0: never air a flagged draft — fall back to a safe evergreen slot.
        log.error(
            "format_commercial_safety_fallback",
            seg_id=seg_id,
            mode=mode,
            reason=safety.reason,
        )
        return evergreen.evergreen_segment(
            now,
            fmt=mode,
            seg_id=seg_id,
            length_target_sec=settings.format_commercial_length_target_sec,
            reason=f"safety: {safety.reason}",
        )

    audio_path = common.render_single_voice([script], dj_card.logical_voice, seg_id)
    audio_path, effective = _apply_production(audio_path, seg_id, level)
    log.info(
        "format_commercial_done",
        seg_id=seg_id,
        mode=mode,
        level=effective,
        words=len(script.split()),
    )
    meta: dict = {
        "format_template": "commercial",
        "mode": mode,
        "speaker": dj_card.id,
        "production_level": level,
        "production_level_effective": effective,
    }
    if mode == MODE_PROMO:
        meta["promoted"] = subject or "the station"
    return Segment(
        id=seg_id,
        format=mode,
        length_target_sec=settings.format_commercial_length_target_sec,
        air_time=now.isoformat(),
        script=script,
        audio_path=audio_path,
        disclosure=True,
        meta=meta,
    )


def commercial(
    now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None
) -> Segment:
    """The `commercial` registry entry — a fictional in-world product spot.

    `flow` (D12.0) is accepted for the uniform format seam but unused: a spot is a
    break, not part of the talk thread.
    """
    return spot(now, ctx, mode=MODE_COMMERCIAL)


def promo(
    now: datetime, ctx: AssembledContext, flow: ShowFlow | None = None
) -> Segment:
    """The `promo` registry entry — a station self-promo (`flow` unused; see above)."""
    return spot(now, ctx, mode=MODE_PROMO)

"""Q0.1 — the API probe: the pure maths, and the harness on a mocked brain.

The probe's *purpose* is to spend tokens (a probe that mocks the LLM measures nothing),
so what gets tested here is everything around that: the text maths that turns scripts
into numbers, the isolation contract (the world is unchanged afterwards), and the
plumbing — exercised with `llm.generate` mocked, which is not a measurement but is a
real check that a $5 run won't die at segment 12.

The pinned inputs are asserted deliberately: if `_SLOTS` or the continuity start drifts,
Q8's comparison against the committed baseline stops meaning anything.
"""

from __future__ import annotations

import pytest
from src.audit import metrics, probe, textstats

# --- the pinned inputs (§1a / seed README §2) -------------------------------


def test_the_fixed_slot_list_is_the_audits_own():
    """Four contrasting shows on one Monday. Changing these invalidates Q8."""
    assert [iso for iso, _ in probe._SLOTS] == [
        "2026-07-27T07:12",
        "2026-07-27T10:12",
        "2026-07-27T16:12",
        "2026-07-27T22:12",
    ]
    assert [pid for _, pid in probe._SLOTS] == [
        "morning_currents",
        "the_exchange",
        "the_circuit",
        "long_night",
    ]


def test_the_pinned_slots_still_resolve_to_those_programmes():
    """A grid edit that moves these shows must be noticed, not silently measured."""
    from datetime import datetime

    from src.world import programming

    for iso, expected in probe._SLOTS:
        assert programming.program_for(datetime.fromisoformat(iso)).id == expected
    assert (
        programming.program_for(probe._CONTINUITY_START).id == probe._CONTINUITY_PROGRAM
    )


# --- the text maths ---------------------------------------------------------


def test_verbatim_overlap_finds_a_replayed_close():
    """§1e's finding: a slot that re-reads the previous slot's last exchange."""
    close = (
        "Sera: By the time this airs they'll have eaten. I hope it tasted the way you "
        "said it would.\nMira: Good. That's the right answer."
    )
    slot1 = f"Sera: Anyway.\n{close}"
    slot2 = f"{close}\nSera: It is, isn't it."
    assert textstats.longest_common_substring_len(slot2, slot1) >= 100
    # A pair that shares only ordinary phrasing scores low.
    a = "Vell: The ice came in early this year and the ferries stopped."
    b = "Wren: The council met about the tariff and adjourned without a vote."
    assert textstats.longest_common_substring_len(a, b) < 20


def test_repeated_ngram_rate_is_a_share_of_the_current_segment():
    prev = "the cook still reaches for the small measure every single morning"
    cur = f"{prev} and nobody has told her to stop yet at all"
    rate = textstats.repeated_ngram_rate(cur, prev, n=8)
    assert rate is not None and 0 < rate < 100
    assert textstats.repeated_ngram_rate("short text", prev, n=8) is None


def test_script_register_measures_turn_shape_and_plainness():
    script = (
        "Vell: Right.\n"
        "Wren [warm]: I mean, we'll see. " + "word " * 45 + "\n"
        "Vell: The ferry's late.\n"
    )
    reg = textstats.script_register([script])
    assert reg["turns"] == 3
    assert reg["pct_turns_under_4w"] > 0  # "Right."
    assert reg["pct_turns_over_40w"] > 0  # the monologue
    assert reg["contractions_per_100w"] > 0
    assert reg["hedges_per_1000w"] > 0


def test_banned_abstractions_are_caught_case_insensitively():
    from src.writers.conversation import BANNED_ABSTRACTIONS

    phrase = BANNED_ABSTRACTIONS[0]
    hits = textstats.banned_abstraction_hits(
        [f"Vell: We were talking about {phrase.title()} again."], BANNED_ABSTRACTIONS
    )
    assert hits == [phrase]
    assert (
        textstats.banned_abstraction_hits(
            ["Vell: The ferry is late."], BANNED_ABSTRACTIONS
        )
        == []
    )


def test_entities_ignore_sentence_openers_and_the_cast():
    """The seed's regex scored "That" and "Because"; the world's own names are it."""
    counts = textstats.entity_counts(
        "Because Cold Harbor filed. That surprised Vell. Cold Harbor's thaw held.",
        vocabulary=["Cold Harbor"],
        exclude=["Vell"],
    )
    assert counts == {"Cold Harbor": 2}


# --- the metric shapes ------------------------------------------------------


def _segment(slot: str, run: int, script: str, *, energy: str = "bright") -> dict:
    return {
        "run": run,
        "slot": slot,
        "program": "p",
        "energy": energy,
        "beat": "a beat about Cold Harbor",
        "script": script,
    }


def test_cross_run_beat_identity_catches_two_runs_picking_the_same_story(monkeypatch):
    monkeypatch.setattr(
        metrics, "world_vocabulary", lambda: (["Cold Harbor", "Meridian"], [])
    )
    same = "Vell: Cold Harbor again.\nWren: Cold Harbor, yes."
    other = "Vell: Meridian filed.\nWren: Meridian, yes."
    agreeing = [_segment("A", 1, same), _segment("A", 2, same)]
    disagreeing = [_segment("B", 1, same), _segment("B", 2, other)]

    assert probe.topic_metrics(agreeing, 2)["cross_run_beat_identity_pct"] == 100.0
    assert probe.topic_metrics(disagreeing, 2)["cross_run_beat_identity_pct"] == 0.0
    mixed = probe.topic_metrics(agreeing + disagreeing, 2)
    assert mixed["cross_run_beat_identity_pct"] == 50.0
    assert mixed["top_entity"] == "Cold Harbor"


def test_top_entity_mentions_is_per_run_not_per_probe(monkeypatch):
    """Or the ≤12 gate measures the probe's size, not the station's concentration.

    §1a counted one pass of the four slots ("named 23 times"), so two runs of the same
    world must report the same number — with the raw total kept beside it.
    """
    monkeypatch.setattr(metrics, "world_vocabulary", lambda: (["Cold Harbor"], []))
    # 3 mentions per segment: two in the script, one in the beat (both are scored).
    script = "Vell: Cold Harbor again.\nWren: Cold Harbor, yes."
    one = probe.topic_metrics([_segment("A", 1, script)], 1)
    two = probe.topic_metrics([_segment("A", 1, script), _segment("A", 2, script)], 2)
    assert one["top_entity_mentions"] == two["top_entity_mentions"] == 3.0
    assert one["top_entity_mentions_total"] == 3
    assert two["top_entity_mentions_total"] == 6  # the raw total does double


def test_register_metrics_only_polices_the_ban_on_daytime_shows(monkeypatch):
    from src.writers.conversation import BANNED_ABSTRACTIONS

    phrase = BANNED_ABSTRACTIONS[0]
    night = _segment("N", 1, f"Vell: {phrase}, again.", energy="calm")
    day = _segment("D", 1, f"Wren: {phrase}, again.", energy="steady")

    assert probe.register_metrics([night])["banned_abstractions_daytime"] == 0
    assert probe.register_metrics([day])["banned_abstractions_daytime"] == 1


def test_continuity_metrics_reports_overlap_and_distinct_subjects(monkeypatch):
    monkeypatch.setattr(
        metrics, "world_vocabulary", lambda: (["Cold Harbor", "Meridian"], [])
    )
    shared = "Mira: Good. That is the right answer, and it always has been, every time."
    segments = [
        {"program": "p", "beat": "Cold Harbor", "script": f"Sera: One.\n{shared}"},
        {"program": "p", "beat": "Cold Harbor", "script": f"{shared}\nSera: Two."},
        {"program": "p", "beat": "Meridian", "script": "Sera: Meridian filed a note."},
    ]
    out = probe.continuity_metrics(segments)
    assert out["max_verbatim_overlap_chars"] >= len(shared) - 2
    assert out["distinct_beats_in_run"] == 2
    assert out["slots"] == 3


def test_declared_probe_groups_match_the_pack():
    assert set(metrics.PROBE_GROUP_KEYS) == {"topic", "register", "continuity"}
    # The Q2 gate reads these off the probe, so a free-only run must show them null.
    for key in ("cached_tokens", "uncached_tokens", "seconds_per_call"):
        assert key in metrics.GROUP_KEYS["context"]


# --- the plan + the dry run -------------------------------------------------


def test_plan_counts_every_segment_it_is_about_to_generate():
    p = probe.plan(runs=2)
    assert p["segments"] == len(probe._SLOTS) * 2 + probe._CONTINUITY_SLOTS
    assert probe.plan(runs=1, continuity=False)["segments"] == len(probe._SLOTS)
    assert "PROBE PLAN" in probe.render_plan(p)


def test_dry_run_spends_nothing(monkeypatch):
    from src.providers import llm as llm_mod

    def boom(*a, **kw):
        raise AssertionError("a dry run must not call Claude")

    monkeypatch.setattr(llm_mod, "generate", boom)
    out = probe.collect_probe(runs=2, dry_run=True)
    assert out["probe"]["dry_run"] is True
    assert "topic" not in out


# --- the harness end to end, on a mocked brain ------------------------------


def test_probe_runs_end_to_end_and_leaves_the_world_untouched(monkeypatch):
    """Plumbing only — a mocked generator measures nothing, but proves it all wires up.

    Also the isolation contract: story/quote/journal counts must be identical after,
    which is what makes it safe to run this against the operator's live world.
    """
    from src.acceptance import _MockGen
    from src.providers import llm as llm_mod
    from src.world import store

    try:
        with store.connect() as conn:
            before = store.counts(conn)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"needs a reachable Postgres: {exc}")

    with store.connect() as conn:
        gen = _MockGen([c.name for c in store.all_cast(conn)])
    monkeypatch.setattr(llm_mod, "generate", gen)

    out = probe.collect_probe(runs=2)

    assert out["probe"]["segments_generated"] == len(probe._SLOTS) * 2 + 5
    assert gen.calls > 0
    for group in ("topic", "register", "continuity"):
        assert set(out[group]) >= set(metrics.PROBE_GROUP_KEYS[group])
    assert out["topic"]["segments"] == len(probe._SLOTS) * 2
    assert out["continuity"]["slots"] == 5

    with store.connect() as conn:
        assert store.counts(conn) == before

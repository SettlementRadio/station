"""Tests for freshness feature extraction at the chokepoint (src/freshness.py) — D5.1.

The pure extraction logic — no DB needed: turning a placed `Segment` into the salient
features the airplay memory stores, and skipping the static, meant-to-repeat segments.
Surgical, on the bits a silent bug would corrupt:

* a talk segment's beat becomes a topic handle; a news segment's covered stories do;
* the opening fingerprint normalizes so NEAR-identical openings collapse and different
  ones diverge (the whole point of a fingerprint — D5.2 shows it as "don't open like");
* a leading speaker label ("Vell:") is stripped from the opening;
* idents / evergreen / gate-failed fallbacks are EXEMPT (not recorded);
* a segment without a pinned air_time is skipped (can't anchor it on the timeline).

The store round-trip + the prune sweep are exercised against a real DB in
test_airplay.py (D5.0); the chokepoint persistence is best-effort glue.
"""

from __future__ import annotations

from datetime import datetime

from src import freshness
from src.segment import Segment


def _talk(script: str, *, beat: str = "the relay drift over the north arc") -> Segment:
    return Segment(
        id="d51-talk",
        format="talk",
        length_target_sec=300,
        air_time="2626-06-24T21:00:00",
        script=script,
        meta={"beat": beat, "part_of_day": "night"},
    )


def test_talk_topic_comes_from_the_beat_handle():
    seg = _talk("**Vell:** Tonight we open on the quiet.")
    rec = freshness.extract_features(seg)
    assert rec is not None
    assert rec.format == "talk"
    assert rec.topic == "the relay drift over the north arc"
    assert rec.aired_at.year == 2626


def test_talk_multiline_beat_handle_is_first_line_only():
    seg = _talk("**Vell:** Hello.", beat="The harvest failure\nand its consequences")
    rec = freshness.extract_features(seg)
    assert rec.topic == "the harvest failure"  # first line, lowercased


def test_opening_fingerprint_strips_label_and_normalizes():
    seg = _talk("**Vell:** Tonight, we open on the quiet hum of the relay.")
    rec = freshness.extract_features(seg)
    # label dropped; lowercased; punctuation gone; first 8 words
    assert rec.opening == "tonight we open on the quiet hum of"


def test_near_identical_openings_share_a_fingerprint():
    a = freshness.extract_features(_talk("**Vell:** Tonight, we open on the quiet!"))
    b = freshness.extract_features(_talk("Wren: tonight we open on the quiet…"))
    assert a.opening == b.opening  # same words, different punctuation/label


def test_different_openings_diverge():
    a = freshness.extract_features(_talk("**Vell:** Tonight we open on the quiet."))
    b = freshness.extract_features(_talk("**Vell:** Good evening from the relay deck."))
    assert a.opening != b.opening


def test_key_phrases_are_distinctive_nonstopwords():
    seg = _talk(
        "**Vell:** The relay drift worsened again as the relay crews scrambled, "
        "drift after drift across the northern relay."
    )
    rec = freshness.extract_features(seg)
    assert "relay" in rec.features
    assert "drift" in rec.features
    # stopwords / short tokens excluded
    assert "the" not in rec.features
    assert "as" not in rec.features


def test_news_topic_is_the_covered_story_ids():
    seg = Segment(
        id="d51-news",
        format="news",
        length_target_sec=300,
        air_time="2626-06-24T18:00:00",
        script="Good evening. The northern relay remains adrift tonight.",
        meta={"stories": ["s-relay", "s-harvest"], "tags": {"s-relay": "breaking/new"}},
    )
    rec = freshness.extract_features(seg)
    assert rec is not None
    assert rec.topic == "s-relay, s-harvest"
    assert rec.format == "news"


def test_ident_is_exempt():
    seg = Segment(
        id="ident-x",
        format="ident",
        length_target_sec=20,
        air_time="2626-06-24T21:00:00",
        script="This is Settlement Radio. Everything you hear is AI-generated.",
        meta={"ident": "disclosure"},
    )
    assert freshness.extract_features(seg) is None


def test_evergreen_is_exempt():
    seg = Segment(
        id="evergreen-x",
        format="evergreen",
        length_target_sec=120,
        air_time="2626-06-24T21:00:00",
        script="A timeless reflection on the settlement.",
        meta={"fallback": True},
    )
    assert freshness.extract_features(seg) is None


def test_gate_failed_fallback_marker_is_exempt_even_with_content_format():
    # A talk slot whose gates failed falls back to evergreen but could carry a content
    # format in some paths — the fallback marker still exempts it.
    seg = _talk("**Vell:** placeholder")
    seg.meta["fallback"] = True
    assert freshness.extract_features(seg) is None


def test_missing_air_time_is_skipped():
    seg = _talk("**Vell:** Tonight we open.")
    seg.air_time = None
    assert freshness.extract_features(seg) is None


# --- D5.2: reading the memory back into prompt blocks ------------------------

NOW = datetime(2026, 6, 30, 21, 0)


def _rec(topic=None, opening=None, fmt="talk"):
    return freshness.store.AirplayRecord(
        seg_id="x", format=fmt, aired_at=NOW, topic=topic, opening=opening
    )


def test_recent_topics_block_lists_distinct_topics(monkeypatch):
    monkeypatch.setattr(
        freshness,
        "_read_recent",
        lambda now, fmt=None: [
            _rec(topic="the relay drift"),
            _rec(topic="The Relay Drift"),  # dupe (case) — collapsed
            _rec(topic="the harvest failure"),
            _rec(topic=None),  # no topic — skipped
        ],
    )
    block = freshness.recent_topics_block(NOW)
    assert "the relay drift" in block
    assert "the harvest failure" in block
    assert block.count("- ") == 2  # de-duped, None dropped


def test_angle_rows_never_crowd_topics_out_of_the_avoid_list(monkeypatch):
    # The 2026-07-18 Voss-atlas triple: continue slots record their per-thread
    # "angle: …" handle, and with enough of them in the recency window the actual
    # TOPIC rows fell off the bounded avoid-list — so a topic aired twice in one
    # evening was re-picked a third time. Angle rows must not consume list slots.
    monkeypatch.setattr(freshness.settings, "freshness_recent_limit", 3)
    monkeypatch.setattr(
        freshness,
        "_read_recent",
        lambda now, fmt=None: [
            # newest first: a thread's angles pile up on top…
            _rec(topic="angle: the letter that arrives late"),
            _rec(topic="Angle: the abstention as a form of speech"),
            _rec(topic="angle: the question as a form of courage"),
            _rec(topic="topic: the sable reach convention deadlock"),
            # …and the topic aired earlier tonight must STILL make the list.
            _rec(topic="topic: the voss atlas — the reproduction argument"),
        ],
    )
    block = freshness.recent_topics_block(NOW)
    assert "the voss atlas" in block  # survives despite 3 fresher angle rows
    assert "the sable reach convention" in block
    assert "angle:" not in block  # deepenings of a listed topic, never listed


def test_recent_topics_block_excludes_the_active_thread(monkeypatch):
    # D12.3 — while continuing a thread, its topic must NOT be in the avoid-list, but
    # the OTHER day-scale topics still are (freshness keeps biting on looping).
    monkeypatch.setattr(
        freshness,
        "_read_recent",
        lambda now, fmt=None: [
            _rec(topic="the relay drift"),
            _rec(topic="the harvest failure"),
        ],
    )
    # exclude passed as the raw multi-line beat; normalized to the stored handle.
    block = freshness.recent_topics_block(
        NOW, exclude="The Relay Drift\nangle: who fixes it\nVell opens"
    )
    assert "the relay drift" not in block  # the active thread is exempt
    assert "the harvest failure" in block  # day-scale looping still steered off


def test_recent_topics_exclude_none_keeps_everything(monkeypatch):
    monkeypatch.setattr(
        freshness, "_read_recent", lambda now, fmt=None: [_rec(topic="the drift")]
    )
    assert "the drift" in freshness.recent_topics_block(NOW, exclude=None)


def test_recent_openings_block_is_format_scoped(monkeypatch):
    captured = {}

    def fake_read(now, fmt=None):
        captured["fmt"] = fmt
        return [_rec(opening="tonight we open on the quiet", fmt="news")]

    monkeypatch.setattr(freshness, "_read_recent", fake_read)
    block = freshness.recent_openings_block(NOW, "news")
    assert captured["fmt"] == "news"  # scoped to the format asked for
    assert "tonight we open on the quiet" in block


def test_prefer_vs_avoid_mode_wording(monkeypatch):
    monkeypatch.setattr(
        freshness, "_read_recent", lambda now, fmt=None: [_rec(topic="the drift")]
    )
    monkeypatch.setattr(freshness.settings, "freshness_mode", "prefer")
    assert "prefer" in freshness.recent_topics_block(NOW).lower()
    monkeypatch.setattr(freshness.settings, "freshness_mode", "avoid")
    assert "do not" in freshness.recent_topics_block(NOW).lower()


def test_limit_caps_items_shown(monkeypatch):
    monkeypatch.setattr(
        freshness,
        "_read_recent",
        lambda now, fmt=None: [_rec(topic=f"topic {i}") for i in range(20)],
    )
    monkeypatch.setattr(freshness.settings, "freshness_recent_limit", 3)
    assert freshness.recent_topics_block(NOW).count("- ") == 3


def test_blocks_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(freshness.settings, "freshness_enabled", False)
    # _read_recent must not even be consulted when disabled.
    monkeypatch.setattr(
        freshness,
        "_read_recent",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not read")),
    )
    assert freshness.recent_topics_block(NOW) == ""
    assert freshness.recent_openings_block(NOW, "talk") == ""


def test_blocks_empty_on_cold_start(monkeypatch):
    monkeypatch.setattr(freshness, "_read_recent", lambda now, fmt=None: [])
    assert freshness.recent_topics_block(NOW) == ""
    assert freshness.recent_openings_block(NOW, "talk") == ""

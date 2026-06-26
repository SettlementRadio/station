# PHASE_D_FIGURES_QUOTES_TASKS.md — D10: Figures & Quotes (the world speaks)

> Sub-pack **D10** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` (especially the **IP
> boundary** — invented in-world people only, never real persons/figures — and the safety gate) and the
> Phase D standing principles (OVERVIEW §2). Written against the **as-built + D3-as-designed** code: the
> D3 story log (`stories` + dated beats-as-`events`, the arc stages, the tick `world_tick.run_tick`),
> the store SQL seam, the gates (`safety.safety_check`, `conversation.continuity_check`),
> `events.relative_phrase` (temporal framing), and `embeddings.retrieve` (D2, for recall).
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D10 brief); `docs/PHASE_D_WORLD_ENGINE_TASKS.md` (D3 —
> the story log this attaches to + the tick that generates it); `docs/PHASE_D_NEWS_DESK_TASKS.md` (D4 —
> the desk that will *attribute* quotes); `src/world/store.py` (the `"cast"` table is the shape to learn
> from — figures are similar rows but a different role); `docs/PHASE_D_VOICE_ROSTER_TASKS.md` (D9 — the
> guest/non-host voice that *plays* a quote as a soundbite).
>
> **Depends on:** **D3** (the story log figures + quotes attach to). **D2** recommended (recall the
> relevant figures/quotes by meaning). **Voicing a quote as a soundbite** depends on **D9**'s
> guest/non-host voice slot — D10 delivers the *data + textual attribution* on its own; the *audio*
> soundbite is the D10×D9 bridge (D10.3).

**What D10 delivers.** Today an event is just a `title` + `body`, and the only *people* the system knows
are the DJs (the `cast`). So the station can't say "the harbour-master reacted angrily" or quote anyone —
the people in the world don't exist as data. D10 models **in-world figures** (the people a story is
about — officials, artists, witnesses, a moon-president's son) and their **attributable statements**
(what they said), attached to the story log, so:
- the **news desk (D4)** can attribute and quote them ("X, the relay-keeper, said: '…'"),
- the **writers' room** can have DJs reference and react to a figure's opinion, and
- (with **D9**) a quote can be **voiced as a soundbite** in that figure's own distinct voice — real radio.

This is the single biggest lever for *rich content*: it's what turns "a fact happened" into "people in a
living world saying things about it."

**Hard rule (load-bearing).** Figures are **invented in-world people only** — never a real person, public
figure, or trademarked character (CLAUDE.md IP boundary). Every generated figure + quote passes the
safety gate and the continuity gate (consistent with canon + the story). The genre's *spirit*, never its
IP.

**Definition of done for D10:** stories carry invented figures with attributable, dated quotes; the news
desk attributes/quotes them with correct temporal framing; DJs can reference what a figure said; (with
D9) a quote can air as a distinctly-voiced soundbite; all figure/quote content is gated and canon-safe;
`ruff` + `pytest` green; README/DEVLOG updated.

---

## D10.0 — Schema: figures + quotes in the story log
**Goal:** a place to record the *people* in a story and *what they said*, linked to stories/beats.
**Do:**
- Add to `store.py` (the only SQL):
  - a **`figures` table** — `figures(id, name, role/title, bio/card_text, voice_id nullable, tags,
    source)` — the invented people of the world. Learn from the `"cast"` shape, but figures are *world
    subjects*, not presenters; `voice_id` is **optional** (set only when a figure is to be *voiced* as a
    soundbite/guest — D9). `source` distinguishes **bible-authored** figures (canon people the human
    wrote) from **tick-generated** ones (so the D1.2 seed-vs-generated split applies — a canon refresh
    must not wipe tick-generated figures).
  - a **`quotes`/`statements` table** — `quotes(id, story_id, beat_id nullable, figure_id, text,
    in_world_datetime, stance/emotion nullable, tags)` — an attributable statement, dated like a beat so
    the clock frames it (said *yesterday* / *today*).
- Add row dataclasses + reads/writes: `insert_figures`/`insert_quotes`, `figures_for_story(story_id)`,
  `quotes_for_story(story_id)`/`quotes_near(now)`, `get_figure(id)`. Fold into `counts` and the **scoped**
  `clear_world` (OVERVIEW §2: tick-generated figures/quotes survive a canon refresh; a full reset clears
  them).
- If D2 is live, embed quotes/figures on write into the **D2 polymorphic `embeddings` table**
  (`store.insert_embeddings(conn, "figure"/"quote", rows)`, carrying the `source` split) so they're
  recall-able by meaning — **reuse the one table, don't add a `*_embeddings` table** (OVERVIEW §2a / D2).
- **Per the §2a matrix:** `figures`/`quotes` follow the same seed-vs-generated `source` split as `events`
  — `source=bible` rows are re-seeded by `seed-canon`; `source=tick` rows **survive `seed-canon`** and are
  **backed up** (irreplaceable), cleared only by `reset-world`. New columns land via idempotent
  migration, not truncate-reseed (OVERVIEW §2).
- **Figures include musicians/artists.** A singer or band is just a `figure` with a music `role` — which
  is what makes a song's artist a real person in the world (referenceable, quotable, guest-able), not a
  text label. **D7's `tracks.artist_figure_id` links a song to its artist figure here.** So a back-announce
  can tie a track to what its artist is up to now (a release/award from D3, the artist's own words via a
  quote); the artist's major works can be authored in the D1 culture cornerstone. Keep it general — figures
  are figures; "musician" is a role/tag, not a separate table.
**Done when:** figures + quotes can be inserted, linked to a story/beat, and read back with their dates;
the seed-vs-generated `source` split is honoured; a canon refresh leaves tick figures/quotes intact.
Unit-tested.

## D10.1 — The tick generates figures + quotes (gated, canon-safe)
**Goal:** when the world moves, it produces the people and the things they said — not bare facts.
**Do:**
- Extend the D3 tick (`world_tick.run_tick`): when it creates or advances a story, also generate the
  **involved figures** (reusing an existing figure when the story continues — don't spawn a new person
  for the same role each beat) and one or more **attributable quotes** that fit the beat (a reaction, an
  announcement, a denial). Anchor quote datetimes to the beat so the clock frames them.
- **Gate every figure + quote** like all generated content: `safety.safety_check` + a continuity check
  against canon and the story's prior beats/quotes (a figure must not contradict who they were last
  beat; a quote must fit the story). Regenerate once, then drop — never write a flagged/contradictory
  figure or quote.
- **Enforce the IP rule in the prompt + gate:** invented people only, inside the fiction, no real
  persons/brands. Keep figures grounded in the bible (a figure's role/place should fit canon — use D2
  recall to anchor them).
- Bound the volume (dials: figures/quotes per story, reuse-vs-new figure preference) — a story needs a
  *few* named voices, not a crowd. Reuse the Batch + caching cost levers (this rides the same nightly run
  as D3).
**Done when:** a tick produces stories whose beats carry invented, canon-consistent figures + dated
quotes; a contradictory/IP-violating figure or quote is regenerated or dropped (nothing bad is written);
recurring stories reuse the same figures across beats.

## D10.2 — News + DJs use figures & quotes (textual attribution)
**Goal:** the station *says* who said what — attribution in the news, reference in the talk.
**Do:**
- **News desk (D4):** include the relevant figures + quotes in the per-story brief, so the anchor
  attributes and quotes them — "X, the harbour-master, said yesterday: '…'" — with correct temporal
  framing (`events.relative_phrase` on the quote's datetime). Keep it reportage; keep the `generate_safe`
  + evergreen fallback. (D4's coverage memory should note *which* quotes/figures were used, so a repeated
  story can bring a *fresh* quote rather than re-reading the same one — ties to D5.)
- **Writers' room (talk):** surface a story's figures/quotes in the assembled context so DJs can
  *reference and react to* an opinion ("Did you hear what the relay-keeper said?") — naturally, not
  reciting (the anti-recitation rule still holds for talk).
- Recall the relevant figures/quotes by meaning via **D2** where a topic is in play; degrade to
  story-linked structured reads when D2 is off.
**Done when:** a news bulletin attributes a dated quote to an invented figure with correct framing; a
talk segment references a figure's opinion in character; both stay gated and canon-safe.

## D10.3 — Soundbites: voice a quote (the D9 bridge) — optional/forward
**Goal:** a quote can air in the figure's *own* voice, like a clip on real radio.
**Do:**
- When a figure has a `voice_id` (D10.0) and **D9's guest/non-host voice slot** exists, render a quote as
  a short **soundbite** in that voice and place it inside the news/talk segment (a distinct voice for the
  figure, bracketed by the anchor/DJ — "here's what they said:" → soundbite → back to studio). Reuse the
  per-turn voicing the conversation engine already does (each turn → its own voice) + D7's stitching.
- Keep it sparse and in-character (texture); the soundbite still carries the world's disclosure posture
  (it's AI-voiced fiction).
- **This task is the D10×D9 bridge** — if D9's guest-voice isn't built, D10 stops at textual attribution
  (D10.2) and this lands when D9 does. Don't block D10.0–D10.2 on it.
**Done when:** with D9's guest-voice available, a quote airs as a distinctly-voiced soundbite inside a
bulletin/segment; without it, attribution stays textual and nothing breaks.

## D10.4 — Tests + verification + docs
**Goal:** the figures/quotes logic is covered, and the result is demonstrable.
**Do:**
- Tests (surgical; mock `llm.generate`): figures/quotes insert + link + read back with dates; the tick
  reuses a figure across a story's beats rather than duplicating; a contradictory/IP-flagged figure or
  quote is dropped (plant a bad draft → assert nothing written); the news brief attributes a quote with
  the right `relative_phrase`; tick figures/quotes survive a canon refresh and are cleared by a full
  reset. Use a fixture story log.
- Add a demo: run a tick, then generate a news bulletin that attributes a quote and a talk segment that
  references an opinion; (if D9) play a soundbite.
- Update `README.md` (figures & quotes — the world's people speak; the IP rule), `.env.example`
  (`FIGURES_*`/quote dials), and the DEVLOG (Phase D — D10).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the demo shows an attributed
quote in the news and a referenced opinion in the talk (and, with D9, a voiced soundbite).

---

## Explicitly NOT in D10 (→ other sub-packs)
- **Generating/advancing the stories themselves** → **D3** (D10 attaches people + quotes to D3's
  stories).
- **Voicing infrastructure — the guest/non-host voice slot, emotion, pronunciation** → **D9** (D10.3 only
  *uses* D9's guest voice; it doesn't build it). A figure brought into the room as an *invited guest* =
  a D10 figure + a D9 voice slot.
- **News recurrence/evolution + on-air anti-repetition** → **D4 / D5** (D10 supplies the quotes; D4
  decides which recur, D5 keeps the wording fresh).
- **The pgvector/embeddings machinery** → **D2** (D10 *uses* recall + embeds quotes via D2's helper).

# JINGLE_PROMPTS_3.md — batch 3: the GRID_V2 new programs + chart/quiz utility (Suno production brief)

> Companion to `docs/JINGLE_PROMPTS.md` (§0 brand sound, §1 Suno mechanics — read those first, they
> still apply verbatim) and `docs/JINGLE_PROMPTS_2.md` (the per-program theme convention). The R2
> grid rebuild (`docs/PHASE_R_TASKS.md`) added 8 new named programs; the **R3.0 placement audit**
> (`make jingle-audit`) confirmed 7 of them are still opening on a **format fallback**
> (`c9_talk.mp3`) rather than their own signature — this pack closes that gap, plus two small
> utility sting sets the new shows need (a chart countdown for The Count, a scoring ding for The
> Relay Round quiz).
>
> **Same filename contract as batch 2:** program themes save as `assets/themes/<program_id>.mp3`
> and wire themselves by convention — no code edit, no restart needed, `media.theme_for_program`
> picks them up the moment the file lands. The two utility sting sets are **registered names**
> (`src/production/media.py` `STINGS`), already wired this session — drop the files in and
> `media.sting(...)` resolves them.

---

## 1. Program themes (7 new — the R3.0 fallback list)

Same rules as batch 2: **instrumental** (Instrumental ON), carries the shared 3–5-note glass-bell
motif, self-contained Style string, generate 2–4 takes, keep the best, **trim to ~8–12 s, fade the
tail clean**. Energy tier picked from each program's grid `energy` (`docs/programming/grid.yaml`)
per `JINGLE_PROMPTS.md` §0's three tiers — the lead instrument changes per entry so same-tier
shows stay distinguishable.

| Save as | Program (energy · tier) | Suno Style |
|---|---|---|
| `assets/themes/the_ledger.mp3` | The Ledger — markets brief, Joss (steady · day, brisk) | `instrumental, no vocals, 8-second markets-brief theme opener, warm retro-futuristic, crisp analog synth pulse, precise ticker-tape mallet ticks, restrained brass stab, dry and exact, brisk no-nonsense energy, composed urgency, glass bell motif, tape warmth, 102 BPM` |
| `assets/themes/the_ward.mp3` | The Ward — health & medicine, Wren+Mira (steady · day) | `instrumental, no vocals, 10-second medical-magazine theme opener, warm retro-futuristic, gentle felt piano, soft mallet bells, warm sustained strings, caring and steady, calm competence, quietly reassuring, glass bell motif, tape warmth, 88 BPM` |
| `assets/themes/the_table.mp3` | The Table — food daily, Mira+Sera (steady · day) | `instrumental, no vocals, 10-second kitchen-table theme opener, warm retro-futuristic, playful pizzicato-style mallets, soft brushed groove, warm electric piano, homely and inviting, market-stall bustle, a little playful, glass bell motif, tape warmth, 96 BPM` |
| `assets/themes/the_count.mp3` | The Count — the daily chart show, Orin (bright · bright) | `instrumental, no vocals, 10-second chart-show theme opener, warm retro-futuristic, driving four-on-floor pulse, bright synth stabs, rising mallet run, danceable and proud, countdown excitement, glass bell motif hook, tape warmth, 122 BPM` |
| `assets/themes/the_serial.mp3` | The Serial — nightly 15-min episode, the Archivist (calm · night) | `instrumental, no vocals, 12-second serial-drama theme opener, warm retro-futuristic, intimate felt piano, slow mellotron strings, soft page-turn-like mallet accent, a hint of cliffhanger tension, storytelling and hushed, the night settling in to listen, sparse glass bell motif, vinyl warmth, 66 BPM` |
| `assets/themes/the_fit.mp3` | The Fit — style & dress, Mira+Orin (bright · bright) | `instrumental, no vocals, 8-second style-and-fashion theme opener, warm retro-futuristic, playful pizzicato mallets, bright synth pulse, strutting groove, stylish and a little cheeky, runway energy kept warm not cold, glass bell motif, tape warmth, 116 BPM` |
| `assets/themes/the_relay_round.mp3` | The Relay Round — the quiz, Kael v Wren (bright · bright) | `instrumental, no vocals, 8-second game-show theme opener, warm retro-futuristic, bouncy mallet riff, bright synth stabs, playful competitive energy, quick and cheeky, a friendly contest, glass bell motif hook, tape warmth, 126 BPM` |

**Reused, not regenerated:** `conditions` → `assets/themes/d14_conditions.mp3` (Conditions Between
Worlds, batch 1) — the file already exists and is wired this session
(`media.PROGRAM_THEMES["conditions"]`); **don't** make a new clip for it. (The R3.0 audit had it
falling back to the news theme only because the reuse override was missing from the registry, not
because the clip was missing.)

---

## 2. Utility — chart countdown ramp + quiz sting

Two small sets, registered ahead of the machinery that will call them (same "speculative/
extensible" posture as batch 1's C12 games theme): The Count's actual chart mechanics are **R6.1**'s
job and The Relay Round has no dedicated `quiz` format yet, so dropping these files in wires the
*name* — a future pack decides exactly when in the show they fire. Continuing the D-series numbering
(`docs/JINGLE_PROMPTS.md` last used D19).

#### D20. Chart Countdown Ramp (×3) 🎛️ — for The Count
- **Type:** Position-reveal stings, a 3-tier ramp (mirrors the A4 sweeper's calm/mid/bright
  pattern, but for chart-position energy rather than daypart energy).
- **Use:** between chart positions as Orin counts down — matter-of-fact for the outer positions,
  building through the middle, a small fanfare on the #1 reveal. `media.sting("chart_countdown_*")`.
- **Style (three separate takes):**
  - approaching (positions 10–6): `instrumental, no vocals, very short 2-second countdown tick sting, crisp mallet tick with soft synth pulse, matter-of-fact forward motion, clean tail, 108 BPM`
  - climbing (positions 5–2): `instrumental, no vocals, very short 3-second countdown sting, rising synth arpeggio run, quickening mallet pulse, building excitement, bright and eager, clean tail, 118 BPM`
  - number one (the reveal): `instrumental, no vocals, short 4-second countdown climax sting, bright triumphant synth stab, rising sweep into a ringing bell motif hit, proud and celebratory, punchy clean resolve, 126 BPM`
- **Instrumental:** ON.
- **Length:** 2–4 s each.
- **Expected outcome:** three takes that visibly climb in energy while staying one family (same
  bell motif resolving the climax) — the countdown should audibly tighten as the numbers get lower.

#### D21. Relay Round Point Sting 🎛️ — for the quiz
- **Type:** Scoring ding.
- **Use:** marks a point won in The Relay Round (Kael v Wren, score kept out loud). `media.sting
  ("quiz_point")`.
- **Style:**
  `instrumental, no vocals, very short 1-second scoring ding, single bright glass bell chime with a soft synth sparkle, playful and quick, clean tail, no lingering resonance`
- **Instrumental:** ON.
- **Length:** 1 s (tight — it lands under a beat of dialogue, not over it).
- **Expected outcome:** a tiny, unmistakable "point!" chime — quotes the family bell motif so it
  reads as Settlement Radio's game, not a generic quiz-show buzzer.

---

## 3. A4 sweeper energy-range recheck (audited, no new asset needed)

R3.0 asked this pack to re-check the three A4 sweepers (`stings/a4_sweeper_{calm,mid,bright}.mp3`)
still cover the grid's energy range now that R2 added these 8 programs. They do: every program in
`docs/programming/grid.yaml`, old and new, carries `energy: calm|steady|bright`
(`ENERGY_SWEEPERS` in `src/production/media.py` maps steady → the mid sweeper), and the 7 new
programs above sit at calm (`the_serial`) or bright (`the_count`, `the_fit`, `the_relay_round`) or
steady (`the_ledger`, `the_ward`, `the_table`) — no fourth tier was introduced. **No new sweeper
needed.**

---

## 4. Storage — where every file goes

All under `assets/` (gitignored; curated, GC-safe — see `JINGLE_PROMPTS.md` §4 for the full-set
rules, repeated here for just this batch):

| Asset | Save the file as |
|---|---|
| The Ledger Theme | `assets/themes/the_ledger.mp3` |
| The Ward Theme | `assets/themes/the_ward.mp3` |
| The Table Theme | `assets/themes/the_table.mp3` |
| The Count Theme | `assets/themes/the_count.mp3` |
| The Serial Theme | `assets/themes/the_serial.mp3` |
| The Fit Theme | `assets/themes/the_fit.mp3` |
| The Relay Round Theme | `assets/themes/the_relay_round.mp3` |
| D20 Chart Countdown — approaching | `assets/stings/d20a_chart_approaching.mp3` |
| D20 Chart Countdown — climbing | `assets/stings/d20b_chart_climbing.mp3` |
| D20 Chart Countdown — number one | `assets/stings/d20c_chart_number_one.mp3` |
| D21 Relay Round Point Sting | `assets/stings/d21_quiz_point.mp3` |

(`conditions` needs no file — see §1's reuse note.)

## 5. Production checklist

- [ ] Carry the A1 motif/palette from `JINGLE_PROMPTS.md` §0 — these 7 themes must still read as
      the same station as batch 1/2, not a new sub-brand.
- [ ] Generate **2–4 takes** per asset; keep the best.
- [ ] **Crop to length**; clean fade so it ducks under speech.
- [ ] The **D20 ramp** should audibly climb tier-to-tier when played back-to-back (approaching →
      climbing → number one) — if two takes are hard to tell apart, re-roll with a different lead
      instrument/BPM, same as the A4 tier-check rule.
- [ ] Export master (WAV) + place under `assets/` with the **exact names in §4**.
- [ ] Re-run `make jingle-audit` after dropping files — the mapping table should show `bespoke`
      (not `fallback`) for all 7 programs, and `conditions` should already read `override`.

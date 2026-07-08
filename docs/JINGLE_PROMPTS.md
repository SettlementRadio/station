# JINGLE_PROMPTS.md — Settlement Radio sonic identity (Suno production brief)

> A copy-paste production pack for generating the station's jingle / ident / sting / theme set in
> **Suno (Pro)**. This is a **content brief**, not code. **Every deliverable file's exact name +
> folder is the table in §4** — generate (§2), then trim, rename per §4, and drop it there. The audio it produces lands in Layer 4
> (Production — sound design) and is aired as non-spoken `Segment`s of `format` `ident` / `sting` /
> `jingle` (see `docs/ARCHITECTURE.md` Seam #2; the producer doesn't *write* these — the scheduler
> just plays the pre-rendered asset). Generated audio lives in `assets/` (gitignored).
>
> **Scope:** this pack is **jingles only** — the static sonic-identity set. **Songs** (the music
> catalogue: `assets/music/` + a `tracks` table) and **commercials** (a generated `commercial`/
> `promo` format) are separate media with their own stores — see `docs/ARCHITECTURE.md` Layers 1/4/5.
>
> **Phase note:** real Layer-4 mixing (beds + stings + ducking) is a **Phase D** workstream
> (`docs/ROADMAP.md`). It's fine to build the asset library now — it's static, human-curated, and
> de-risks the phase. **One asset is useful immediately:** the spoken **AI-disclosure ident** (C3)
> can sit over the disclosure bed below.

---

## 0. The brand sound (read first — this is what makes them a *family*)

The single most important rule of a radio sonic-identity package: **every piece must sound like it
came from the same station.** A listener should recognise Settlement Radio in two seconds, whether
it's the news sting or the night theme. So we fix a shared palette and a recurring motif, and every
prompt below inherits it.

**The Settlement Radio palette** (derived from the canon — warm, optimistic, wondrous, a little wry;
golden-age + new-wave sci-fi *spirit*, never IP; **not** dystopian, **not** camp):

- **Era / lane:** warm analog retro-futurism — late-70s/80s sci-fi soundtrack feel, brought forward.
- **Core instruments:** warm analog synth pads, Mellotron-style strings, soft mallet/glass bells,
  gentle choir "ahh" pads, a slow felt-piano or electric-piano, distant warm brass, sub-bass swells.
- **Texture:** tape warmth, soft vinyl/air hiss, a sense of deep space and great distance — *cozy
  vastness*, like a lit window seen across the dark.
- **Tempo / energy:** mostly slow–mid, unhurried, hopeful. Even the "urgent" pieces stay composed,
  never panicked.
- **The mnemonic (motif):** a simple **3–5 note rising signature** that resolves warmly — the
  "Settlement Radio" logo melody. **Build asset #1 first, then carry that melody into the others** so
  the package is unmistakably one station.

**How to keep the family coherent in Suno:** generate the **Signature Ident (#1)** first; when you
love it, save it as a **Persona** (Suno Pro) and keep its exact Style string. **Use the Persona only
for Group A** (the core identity trio) — for everything else, carry the *palette tags + the motif*,
not the Persona. A Persona locks the full sonic identity; applied to all 20+ pieces it makes the
package blur into one long jingle (if your takes all sound the same, this — plus same-BPM prompts —
is why).

**Variety inside the family — three energy tiers (the anti-sameness rule).** The **motif is the
family glue, not the palette.** Assign each asset a tier and push the tiers apart:

- **Night tier (56–75 BPM):** felt piano, low pads, distant choir — A3, B4, C11, D14, D15a.
- **Day tier (85–105 BPM):** arpeggios, mallets, restrained brass, motion — A1, A2, B5, B5a, B5b,
  B6, C7, C9, D13, D16, D17.
- **Bright tier (110–132 BPM):** pulses, claps, sweeps, energy — C8, C10, C12, A4, D18.

Within a tier, **change the lead-instrument tag per asset** (bells → e-piano → brass → arpeggio) and
let only the 3–5-note motif recur. Two assets in different tiers should be obviously different music
that still ends on the same signature. When re-rolling a take that sounds "like the last one," change
the lead instrument and BPM first, not the adjectives.

---

## 1. Suno mechanics — best practices for 2026 (the dials these prompts assume)

Grounded in current (2026) Suno Pro guidance — sources at the bottom.

- **Field limits (v5 Custom Mode):** **Styles** box ≈ **1,000 chars** (practical sweet spot: 8–15
  comma tags — past ~15 Suno starts ignoring the tail); **Lyrics** box ≈ 5,000 chars; **Title** ≈ 100.
  Every Style string below is ~200–350 chars — nowhere near the cap, by design.
- **What maps where in the UI:** the **Style** string → the **Styles** box; the **Lyrics** block → the
  **Lyrics** box; 🎛️ pieces → **More Options → Lyrics → Instrumental**; set **Vocal Gender** when an
  entry names a voice. Use the newest model (v5.x), Advanced/Custom mode.
- **Plan note:** commercial broadcast rights require a **Pro/Premier** plan — free-tier output is not
  cleared for air. Generate the keepers on Pro.
- **Use Custom Mode, always.** Simple Mode strips the separate **Style**, **Lyrics**, and **Title**
  fields you need for production work. Every entry below gives you a **Style** string and either a
  **Lyrics** block (sung jingles) or an **Instrumental** instruction.
- **Style field = weighted, comma-separated tags. ~8–15 of them, order = priority.** Lead with the
  load-bearing tags: *genre → mood → lead instrument → vocal-or-instrumental → production → tempo
  (BPM)*. Clean and specific beats long and impressive; past ~15 tags Suno starts ignoring the tail
  and contradicting itself.
- **Instrumental pieces:** toggle **Instrumental ON** *and* keep "instrumental, no vocals" in the
  Style string (belt-and-suspenders). Most assets here are instrumental.
- **Sung pieces:** put **structure tags in the Lyrics field**, not the Style field — Suno respects
  `[Intro] [Hook] [Chorus] [Break] [Outro]` etc. Keep the **hook to 2–4 short lines**; a jingle
  lives or dies on one memorable line. Inline vocal cues go in parens on their own line, e.g.
  `(warm, close-mic, almost whispered)`.
- **Exclude Styles is your friend.** Use it to keep the package clean — push out anything that would
  break the cozy-sci-fi tone. Default exclude set for this station:
  `aggressive EDM, trap, drill, dubstep, heavy metal, distorted, harsh, lo-fi tape hiss-heavy, comedic, chiptune novelty`.
- **Length:** Suno generates a full song; you want **3–20 seconds**. Generate, then **Crop / Trim**
  to the sounder, or use a short-length setting if your plan exposes one. Always **fade-clean** the
  tail so it ducks under speech without a stray bar.
- **Generate 2–4 takes per asset, keep the best, re-roll the rest.** Cheap on Pro; consistency is
  worth the re-rolls. Save winners; note the seed/Persona so re-makes match.
- **IP boundary (hard rule, mirrors CLAUDE.md):** **never** name a real artist, franchise, or
  composer in a prompt ("in the style of Vangelis/Blade Runner" is out — Suno blocks it and it
  violates the tribute boundary). Describe the *sound* with instruments and adjectives instead. All
  prompts below already do this.

---

## 2. The jingle set

Twenty-two entries in four groups: **core identity**, **dayparts & handover**, **program themes**, and
**utility & special** (B5a/D15a were added once the D6 grid + C4 fallback landed; A4/B5b/D17/D18 once
D3's living world, the full grid, and the D8 dependency were real — **the §4 table is the
authoritative file list**, ~27 files including the ×3/×2 sets and loop variants). Each entry:
**Type** · **Use in the app** · **Style** (paste into Suno's Style field) · **Lyrics/Instrumental** ·
**Length** · **Expected outcome**. Three entries also ship a **long loopable bed variant** for D7.3
ducking. **After generating each asset, save it under the exact filename in the §4 table** (per-asset
paths, e.g. `assets/idents/a1_signature.mp3`) — that table is the complete deliverables list.

> **The only load-bearing fields are the Style string and the §4 filename.** Every Style below is
> self-contained — it carries the vocal/instrumental spec, the loop intent, and the target length, so
> you can work Style-box-only. (Suno treats the seconds-count as a bias, not a command — generate,
> then trim per §4.) **The single exception is A1**: it *sings the station name*, which only the
> Lyrics box can supply — paste its two lyric lines for that one asset.
>
> Notation: 🎵 = sung (A1 only — uses the Lyrics field) · 🎛️ = instrumental (Instrumental ON; any
> wordless voice — humming, choir "ahh" — is described inside the Style).

---

### Group A — Core station identity

#### DONE_A1. Signature Ident — the sung logo  🎵  ★ build this one first
- **Type:** Station ident / brand mnemonic (the "logo melody").
- **Use:** top-and-tail of the day, between programs, the thing a clip-cutter drops on a Short. The
  source of the 3–5 note motif every other asset reuses.
- **Style:**
  `short sung station ident, 8 seconds, warm retro-futuristic, analog synth pads, mellotron strings, glass bell mnemonic, gentle close-mic female and male unison vocal, hopeful, wondrous, cozy, sparse arrangement, tape warmth, 75 BPM`
- **Lyrics (⚠️ the ONE asset where the Lyrics box matters — paste this):**
  ```
  [Hook]
  (warm, intimate, two voices in soft unison)
  Settlement Radio —
  the light between the worlds.
  [Outro]
  (a single rising glass-bell motif, resolving warmly)
  ```
- **Length:** 5–8 s.
- **Expected outcome:** an instantly recognisable, warm sung tagline ending on the rising motif.
  This melody becomes the station's signature; everything else quotes it.

#### DONE_A2. Top-of-Hour Sounder  🎛️
- **Type:** Instrumental ident (hourly station ID bed).
- **Use:** fires at the top of each hour under the DJ's hour/time check; the "we are Settlement
  Radio, it's the top of the hour" moment. Pairs with the time-check sounder (D13).
- **Style:**
  `instrumental, no vocals, short 5-second radio sounder, warm retro-futuristic, rising analog synth swell, mellotron strings, soft brass fanfare restrained, glass bell motif, hopeful and clean, deep space ambience, tape warmth, 80 BPM`
- **Instrumental:** ON.
- **Length:** 4–6 s.
- **Expected outcome:** a short, dignified swell that quotes the A1 motif and resolves on a clean
  bell — sits *under* a spoken station ID without competing with the voice.

#### DONE_A3. AI-Disclosure Bed  🎛️  ← usable now (C3)
- **Type:** Underscore bed for the spoken AI-generation disclosure.
- **Use:** the spoken disclosure ident (Phase C, C3 — "Settlement Radio is generated by AI") rides
  on top of this. Must be calm, neutral, trustworthy — it's a *promise to the listener*, not a show.
- **Style:**
  `instrumental, no vocals, 15-second seamless loopable ambient underscore, soft sustained analog pad, gentle felt piano, low warm drone, neutral and honest, unhurried, spacious, very low energy, no melody hooks, 60 BPM`
- **Instrumental:** ON.
- **Length:** 12–15 s (long enough to talk over; loops cleanly).
- **Expected outcome:** a quiet, melody-light pad a voice sits cleanly over; reads as sincere and
  transparent, never salesy. Leave headroom — it will be ducked hard under speech.

#### DONE_A4. Transition Sweeper Set (×3)  🎛️  *(added for the D7 build — dynamism between segments)*
- **Type:** Short sweepers — the "moving parts" of the station sound.
- **Use:** quick segment-to-segment transitions (song → talk, talk → song) so not every join is a
  full theme. Three takes at three energies, matched to the expanded music catalogue (ballads → rock
  → dance): calm / mid / bright. The scheduler can pick by daypart.
- **Style (generate three separate takes, changing the CAPITALISED bits):**
  - calm: `instrumental, no vocals, very short 3-second radio sweeper, SOFT RISING PAD SWEEP, single glass bell motif, gentle and spacious, clean tail, 72 BPM`
  - mid: `instrumental, no vocals, very short 3-second radio sweeper, WARM SYNTH ARPEGGIO RUSH, mallet accent into bell motif, forward motion, clean tail, 100 BPM`
  - bright: `instrumental, no vocals, very short 3-second radio sweeper, BRIGHT WHOOSH AND PULSE, quick rising sparkle into bell motif, energetic and joyful, punchy clean tail, 124 BPM`
- **Instrumental:** ON.
- **Length:** 2–4 s each.
- **Expected outcome:** three station-branded "whooshes" that all land on the A1 bell motif but at
  clearly different energies — the bright one must feel at home next to a Lane Runners or Auroral
  Standard track (see `MEDIA_LIBRARY.md`), the calm one next to a void ballad.

---

### Group B — Dayparts & handover

#### DONE_B4. Night Shift Theme — "The Long Quiet" (Vell)  🎛️
- **Type:** Daypart theme / opener for the night block.
- **Use:** opens Vell's night shift; the cozy, late-hours signature. Maps to the night daypart in
  the Phase D programming model.
- **Style:**
  `instrumental, no vocals, 12-second night-radio theme opener, warm ambient, slow felt piano, deep analog pad, distant choir, soft sub-bass swell, intimate and reassuring, starlit, unhurried, vinyl warmth, melancholic but kind, 64 BPM`
- **Instrumental:** ON.
- **Length:** 10–15 s (front) — optionally render a 30–45 s version as a bed.
- **Expected outcome:** "it's late, you're not alone" in sound. Low, warm, intimate — Vell's voice
  drops straight into it. Carries a slowed hint of the A1 motif.

#### DONE_B5. First-Light Theme (Wren)  🎛️
- **Type:** Daypart theme / opener for the waking block.
- **Use:** opens Wren's first-light shift; bright, curious, the day waking across the worlds.
- **Style:**
  `instrumental, no vocals, 12-second sunrise radio theme opener, bright and hopeful, warm analog synth arpeggio, mallet bells, soft strings rising, gentle uplifting brass, curious and awake, optimistic, clean and airy, 96 BPM`
- **Instrumental:** ON.
- **Length:** 10–15 s.
- **Expected outcome:** a clear lift in energy from the night theme — same palette, brighter key and
  a rising arpeggio. Signals "the worlds are waking." Quotes the A1 motif, brightened.

#### DONE_B5a. Daywatch Theme  🎛️  *(added for the as-built D6 grid)*
- **Type:** Daypart theme / opener for the waking-day block.
- **Use:** opens **Daywatch** (`daywatch`, 07:00–20:00 in `docs/programming/grid.yaml`) — the longest
  program of the day. Steady, companionable, "the worlds at work" — between B5's sunrise lift and B4's
  night hush.
- **Style:**
  `instrumental, no vocals, 10-second daytime radio theme opener, warm and steady, mid-tempo analog synth pulse, soft mallet bells, easy strings, gentle purposeful groove, companionable and open, optimistic workday feel, tape warmth, 92 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** a dependable, unhurried daytime signature — less sparkle than B5, more forward
  motion; quotes the A1 motif mid-register. The sound of the long, ordinary, good part of the day.

#### DONE_B5b. Nightfall Theme  🎛️  *(added for the as-built D6 grid)*
- **Type:** Daypart theme / opener for the dusk block.
- **Use:** opens **Nightfall** (`nightfall`, 20:00–22:00 in `docs/programming/grid.yaml`) — the dusk
  handover program (Wren hands Vell the light). The day folding up its work; not yet the deep night.
- **Style:**
  `instrumental, no vocals, 10-second dusk radio theme opener, warm, settling synth pads, slow mallet bells, low strings entering, day winding down feeling, calm but not yet sleepy, amber and gentle, tape warmth, 84 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** the audible turn of the day — brighter than B4 (deep night), softer than B5a
  (daywatch); the A1 motif slowing down. Pairs with B6 for the on-air handover moment.

#### DONE_B6. Shift Handover Sounder (Vell → Wren / Wren → Vell)  🎛️
- **Type:** Transition sounder.
- **Use:** the moment one host hands the broadcast to the other (canon: they pass the light at the
  edges of the day). A short musical bridge between night and first-light dayparts.
- **Style:**
  `instrumental, no vocals, short 6-second transition sounder, two intertwining synth motifs handing off, soft crossfade pad, single warm bell resolve, passing-the-light feeling, tender, cinematic, 80 BPM`
- **Instrumental:** ON.
- **Length:** 5–8 s.
- **Expected outcome:** the night motif (B4) morphs into the dawn motif (B5) — audibly "passing the
  light." Used both directions (it can be reversed for the dawn→night handover).

---

### Group C — Program / format themes

#### C7. DONE_News Desk Theme — "The News of the Era"  🎛️
- **Type:** Program theme for the news format.
- **Use:** opens the news desk. Maps to the `news` format (`src/formats/news.py`). Authoritative but
  warm — this station reports the news of the late 27th century without fearmongering.
- **Style:**
  `instrumental, no vocals, 10-second news bulletin theme opener, confident analog synth pulse, steady arpeggio, clean brass stabs restrained, glass bell accents, authoritative but warm, trustworthy, forward-moving, resolves to a clean pad, 100 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** "headlines are starting" — purposeful, credible, a steady pulse, never harsh
  or anxious. Resolves into a clean pad the newsreader speaks over.

#### DONE_C8. News Sting  🎛️
- **Type:** Short stab / punctuation.
- **Use:** the **sting** the `news` template fires *before* the headlines, and between major items.
  This is the short, sharp sibling of C7.
- **Style:**
  `instrumental, no vocals, very short 2-second news sting, sharp clean synth stab, single rising glass bell, tight brass hit restrained, urgent but composed, crisp, no tail, 110 BPM`
- **Instrumental:** ON.
- **Length:** 2–3 s.
- **Expected outcome:** a crisp 2-second punctuation that says "next item." Tight transient, quick
  clean tail — designed to fire *over* the end of a sentence.

#### DONE_C9. Talk / Feature Theme  🎛️
- **Type:** Program theme for the talk format.
- **Use:** opens the two-DJ conversation / feature segments. Maps to the `talk` format
  (`src/formats/talk.py`) — which, post-D3/D4, includes **current-affairs discussion of the living
  story log** (council disputes, frontier politics, the day's developments), not just banter. One
  theme covers both: the station debates warmly, so the sound doesn't change when the topic gets
  serious (for the big set-piece events, D17 takes over).
- **Style:**
  `instrumental, no vocals, 10-second talk-show theme opener, loops cleanly as a bed, warm and conversational, relaxed electric piano, soft brushed groove, mellow analog bass, gentle vibraphone, friendly and curious, a little wry, intimate, 88 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s (plus an optional 30 s loopable bed for under-talk ducking).
- **Expected outcome:** "pull up a chair." Loose, friendly, unhurried — sets up banter rather than
  announcing. Loops cleanly as a low bed under conversation.

#### DONE_C10. Music Show Bumper — "Into the Music"  🎛️
- **Type:** Bumper into the music format's song slot.
- **Use:** the DJ's hand-off into a track. Maps to the `music` format (`src/formats/music.py`); sits
  right before the `[SONG]` slot the Phase D scheduler fills.
- **Style:**
  `instrumental, no vocals, short 5-second music bumper, warm rising synth sweep, shimmer pad, soft four-on-floor pulse entering, anticipatory, elegant, lifts into a track, clean downbeat resolve, 100 BPM`
- **Instrumental:** ON.
- **Length:** 4–6 s.
- **Expected outcome:** a short lift that lands on a clean downbeat — engineered so a song can start
  the instant it resolves. "And now, the music."

#### DONE_C11. Letters Between Worlds Theme  🎛️
- **Type:** Program theme for the listener-letters / dedications segment.
- **Use:** the canon's "letters between worlds" (CANON fact #7) — messages that travel weeks across
  the relays, read on air. The future home of listener dedications/requests (Phase E inbound). Tender
  and nostalgic.
- **Style:**
  `10-second nostalgic radio theme, soft wordless female humming melody, no lyrics no words, gentle felt piano, mellotron strings, distant radio static warmth, longing and tender, intimate, humming fades into warm static, slow, 70 BPM`
- **Instrumental:** ON *(the wordless humming is carried by the Style — no Lyrics needed)*.
- **Length:** 8–12 s.
- **Expected outcome:** a wistful, humming signature that says "someone, far away, wrote to you." The
  warmth of distance — nostalgic without being sad. (Hummed, not worded, so it never dates.)

#### DONE_C12. Inter-Settlement Games Theme  🎛️  *(speculative / extensible)*
- **Type:** Program theme for a sport / games segment.
- **Use:** *sports* for a between-worlds civilization — the "games between the settlements." Not yet
  in the canon or the format registry; included as a ready-to-go theme for when a sports daypart is
  added (keep tasteful — wonder, not jock-bombast).
- **Style:**
  `instrumental, no vocals, 10-second sports-broadcast theme opener, bright synth brass fanfare, driving mallet rhythm, soaring strings, triumphant but elegant, energetic and proud, celebratory, cinematic, 120 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** energetic, proud, celebratory — the lift of a games broadcast, kept classy
  and wondrous rather than aggressive. Flag it as a Phase-D-or-later addition.

---

### Group D — Utility & special

#### DONE_D13. Settlement-Time Check Sounder  🎛️
- **Type:** Utility sounder (the station "clock").
- **Use:** under the DJ's time check — "coming up on two in the morning, settlement time."
  Time-awareness is core to the station, so the clock deserves its own tiny signature.
- **Style:**
  `instrumental, no vocals, short 4-second time-check sounder, soft ticking mallet pulse, single clear glass chime, warm pad underneath, calm and precise, reassuring, spacious, 72 BPM`
- **Instrumental:** ON.
- **Length:** 3–5 s.
- **Expected outcome:** a soft, precise chime-and-pulse that reads as "the time is —" without being a
  literal clock tick. Sits under one spoken sentence.

#### DONE_D14. Conditions Between Worlds — relay/space weather  🎛️
- **Type:** Program theme for a "weather"-equivalent segment.
- **Use:** real radio has weather; a between-worlds relay has **the conditions across the dark** —
  relay strength, the quiet of the void, the crossing between settlements. Spacious and atmospheric.
- **Style:**
  `instrumental, no vocals, 10-second atmospheric theme dropping to a low bed, slow shimmering pad, soft radio-signal sweeps, distant wind-like synth, deep calm drone, gentle bell, vast and serene, contemplative, 66 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** wide, weather-map-of-the-void atmosphere — signal sweeps and deep calm, the
  sense of distance between worlds. Drops to a low bed under the report.

#### DONE_D15. All-Settlements Advisory — emergency sounder  🎛️
- **Type:** Alert / advisory sounder (the EAS equivalent, in-character).
- **Use:** a rare, attention-getting advisory ("an all-settlements advisory"). **Tone discipline:**
  the station is *not* dystopian — this is composed and authoritative, a steady hand, **never**
  panic, sirens, or horror. Attention without alarm.
- **Style:**
  `instrumental, no vocals, short 5-second alert sounder, calm and authoritative, steady low two-tone synth pulse, clear sustained bell tone, composed and serious, attention-getting but never panicked, dignified, sparse, 90 BPM`
- **Instrumental:** ON.
- **Length:** 4–6 s.
- **Expected outcome:** an unmistakable "listen now" signal that stays calm and in control — the
  trustworthy voice of a station that holds steady. Distinct from every warm theme above, by design.

#### DONE_D15a. Never-Dead Fallback Bed — `assets/bed.mp3`  🎛️  ← usable now (C4)
- **Type:** Long ambient bed — the playout **Tier 3 fallback**.
- **Use:** `config/radio.liq` already looks for **`assets/bed.mp3`** and plays it *in the clear* when
  the schedule runs dry (the C4 never-dead chain: schedule → this bed → disclosure ident → silence-
  breaker). It must stand alone for minutes without a voice — pleasant, unobtrusive, unmistakably
  Settlement Radio. **This is the one file whose path/name is fixed by playout — exactly
  `assets/bed.mp3`, not in a subfolder.**
- **Style:**
  `instrumental, no vocals, long 3-minute ambient space-radio bed, seamless loop, warm slow analog pads, gentle evolving drone, soft glass bell motif recurring sparsely, distant choir, calm and patient, cozy vastness, tape warmth, 60 BPM`
- **Instrumental:** ON.
- **Length:** generate long (2–4 min), trim to a **60–120 s seamless loop** (match head/tail so it
  cycles without a seam).
- **Expected outcome:** a station-branded ambient hold — a listener tuning in mid-fallback should hear
  "Settlement Radio, between moments," not dead air or an alarm. Sparse quotes of the A1 motif.

#### DONE_D16. Lumen Festival Seasonal Theme  🎛️
- **Type:** Special-event theme (annual; canon Event).
- **Use:** the Lumen Festival (CANON Event; in-world 2626-06-24) — every world kindles its lamps at
  the same shared hour. A once-a-year celebratory theme; the station carries the night through as the
  lights come up.
- **Style:**
  `15-second celebratory festival theme, soft wordless massed choir ahh rising warmly, no lyrics no words, glowing analog synths, twinkling bells layering in, gentle uplifting strings, communal and luminous, hopeful, building slowly never bombastic, resolving into a glowing bell motif, 84 BPM`
- **Instrumental:** ON *(the wordless choir is carried by the Style — no Lyrics needed)*.
- **Length:** 12–20 s (a longer hero piece is fine here — it's seasonal).
- **Expected outcome:** the warmest, most communal piece in the set — many worlds lighting their
  lamps at once. Resolves into the A1 motif so even the festival feels like *home*.

#### D17. Special Coverage Theme — event-agnostic  🎛️  *(added for the D3 living world)*
- **Type:** Program theme / bed for any big world event.
- **Use:** the D3 world engine now **generates** events (launches, council votes, rediscovered
  worlds, regional festivals) and the D4 news desk covers them across days. D16 serves exactly one
  hardcoded event (Lumen); this is the **generic** "the station is carrying something bigger than
  the hourly bulletin" theme — usable for *any* story the tick produces, this year and every year.
  Deliberately not tied to any event's mood: dignified anticipation, works for a launch or a vote.
- **Style:**
  `instrumental, no vocals, 12-second event coverage theme resolving to a low loopable pad, purposeful analog synth pulse, slow-building strings, restrained noble brass, glass bell motif, sense of occasion, dignified anticipation, neither happy nor sad, tape warmth, 96 BPM`
- **Instrumental:** ON.
- **Length:** 10–15 s, resolving to a low loopable pad (it will be ducked under coverage).
- **Expected outcome:** "something is happening across the worlds, and we're carrying it" — occasion
  without editorial mood, so the same theme fits a celebration or a tense vote. The workhorse the
  Lumen theme is the once-a-year exception to.

#### D18. Ad-Break Stings — in & out (×2)  🎛️  *(added for D8 commercials)*
- **Type:** Break punctuation pair.
- **Use:** **D8** builds the commercial/promo format and its break cadence **on D7's stings** — these
  are those stings. Two takes: **break-in** (hands from the show to the spot) and **break-out**
  (returns to the show). D8's philosophy is *texture, not interruption* (MARKETING.md "Powered by") —
  friendly and brief, never a hard commercial klaxon.
- **Style (two separate takes):**
  - in: `instrumental, no vocals, very short 2-second friendly break sting, warm descending synth figure, soft bell motif landing, welcoming pause feeling, clean tail, 100 BPM`
  - out: `instrumental, no vocals, very short 2-second friendly return sting, warm rising synth figure, bell motif lifting back in, we're back feeling, bright clean resolve, 104 BPM`
- **Instrumental:** ON.
- **Length:** 2–3 s each.
- **Expected outcome:** a matched pair — the "in" settles down and opens a door, the "out" walks back
  through it; together they bracket a spot so a break feels like part of the show, not a cut away
  from it.

#### D19. Sponsor Brand Bug — `d8_brand.mp3`  🎛️  *(D8 commercials, production level 4)*
- **Type:** Micro brand sting (the sponsor bookend).
- **Use:** the sparse ~2 s bug that bookends a sponsor read at `format_commercial_production_level: 4`
  (`STINGS["brand"]` in `src/production/media.py`) — the ONLY prerecorded ad audio; until it exists the
  spot degrades to a plain voiced read. D8's philosophy is *texture, not interruption* ("Powered by") —
  a warm sonic signature, never a hard commercial klaxon.
- **Style:**
  `instrumental, no vocals, very short 2-second brand bug sting, warm retro-futuristic, single soft glass bell motif resolving, gentle analog pad swell, friendly and unobtrusive, "powered by" warmth, clean quick tail, tape warmth, 96 BPM`
- **Instrumental:** ON.
- **Length:** 2–3 s (tight — no lingering tail; it bookends a spot).
- **Expected outcome:** a tiny warm "Settlement Radio" signature that lands on the A1 bell motif — says
  *whose* station carried the message, in under two seconds.

---

## 3. Mapping to the app (so these slot in without a rewrite)

> **Per-program themes moved to `docs/JINGLE_PROMPTS_2.md`.** The grid grew to ~28 named programs; each
> now has its own opening theme, resolved by **convention** (`assets/themes/<program_id>.mp3`) — see
> `docs/PHASE_D_JINGLES_TASKS.md`. The table below is the batch-1 identity/format/utility set; the
> old daypart-only mapping (`daywatch` etc.) is superseded by the per-program convention.

Program ids below are the as-built D6 grid (`docs/programming/grid.yaml`): `long_night` (22–05),
`first_light` (05–07), `daywatch` (07–20), `nightfall` (20–22); news is pinned `news@:00` in every
clock — that pin is where the C8 sting fires (D7.2).

| Asset | `Segment.format` | Where it's used |
|---|---|---|
| A1 Signature Ident | `ident` | between programs; clip cutter |
| A2 Top-of-Hour | `ident` | hourly station ID, under DJ |
| A3 Disclosure Bed | `ident` | under spoken disclosure (C3) |
| A4 Sweepers (×3) | `sting` | segment-to-segment transitions, picked by daypart energy |
| B4 Night Theme | `ident`/bed | `long_night` program open (+ loop bed variant for D7.3 ducking) |
| B5 First-Light Theme | `ident`/bed | `first_light` program open |
| B5a Daywatch Theme | `ident`/bed | `daywatch` program open |
| B5b Nightfall Theme | `ident`/bed | `nightfall` program open |
| B6 Handover | `sting` | `first_light` / `nightfall` boundary (Vell↔Wren, both directions) |
| C7 News Theme | `ident`/bed | `news` format open |
| C8 News Sting | `sting` | before the pinned `news@:00` / between items |
| C9 Talk Theme | `ident`/bed | `talk` format open (+ loop bed variant for D7.3 ducking) |
| C10 Music Bumper | `sting` | `music` format, before the `[SONG]` slot |
| C11 Letters Theme | `ident`/bed | listener-letters segment (Phase E inbound) |
| C12 Games Theme | `ident`/bed | future sports daypart (extensible) |
| D13 Time-Check | `sting` | under DJ time checks |
| D14 Conditions | `ident`/bed | "weather"-equivalent segment |
| D15 Advisory | `sting` | rare all-settlements advisory |
| D15a Fallback Bed | (playout) | `config/radio.liq` Tier 3 — plays when the schedule runs dry (C4) |
| D16 Lumen Festival | `ident`/bed | annual event window (the one *fixed* canon event) |
| D17 Special Coverage | `ident`/bed | any D3-generated big event the station carries (event-agnostic) |
| D18 Break Stings (×2) | `sting` | D8 ad-break in/out brackets |

These are pre-rendered audio assets the scheduler plays directly — `script=None`, `audio_path` set —
exactly the `ident`/`sting`/`jingle` Segments described in `docs/ARCHITECTURE.md` Seam #2. No model
below the seam changes.

## 4. Storage — where every file goes (the exact names; D7.0 reads these)

**After you generate (every asset):**
1. Download the keeper take (WAV master + MP3).
2. **Trim/crop to the entry's length; fade the tail clean** (stings: tight, no tail; beds: seamless loop).
3. **Rename the MP3 to the exact name below** and drop it in the listed folder. These names are the
   contract with the D7 code (the ident/theme/sting→placement mapping resolves by these paths — nothing
   is discovered by scanning). Keep WAV masters in a backed-up `masters/` folder outside `assets/`.

All under `assets/` (gitignored; curated media — backed up, never GC'd; C2.5 `prune` only scans
`segments/`, so everything here is automatically safe):

| Asset | Save the file as |
|---|---|
| A1 Signature Ident | `assets/idents/a1_signature.mp3` |
| A2 Top-of-Hour | `assets/idents/a2_top_of_hour.mp3` |
| A3 Disclosure Bed | `assets/idents/a3_disclosure_bed.mp3` |
| A4 Sweeper — calm | `assets/stings/a4_sweeper_calm.mp3` |
| A4 Sweeper — mid | `assets/stings/a4_sweeper_mid.mp3` |
| A4 Sweeper — bright | `assets/stings/a4_sweeper_bright.mp3` |
| B4 Night Theme (opener) | `assets/themes/b4_night.mp3` |
| B4 Night Theme — **loop bed variant** (30–45 s, for ducking) | `assets/themes/b4_night_bed.mp3` |
| B5 First-Light Theme | `assets/themes/b5_first_light.mp3` |
| B5a Daywatch Theme | `assets/themes/b5a_daywatch.mp3` |
| B5b Nightfall Theme | `assets/themes/b5b_nightfall.mp3` |
| B6 Handover Sounder | `assets/stings/b6_handover.mp3` |
| C7 News Theme | `assets/themes/c7_news.mp3` |
| C8 News Sting | `assets/stings/c8_news_sting.mp3` |
| C9 Talk Theme (opener) | `assets/themes/c9_talk.mp3` |
| C9 Talk Theme — **loop bed variant** (~30 s, for ducking) | `assets/themes/c9_talk_bed.mp3` |
| C10 Music Bumper | `assets/stings/c10_music_bumper.mp3` |
| C11 Letters Theme | `assets/themes/c11_letters.mp3` |
| C12 Games Theme | `assets/themes/c12_games.mp3` |
| D13 Time-Check Sounder | `assets/stings/d13_time_check.mp3` |
| D14 Conditions Theme | `assets/themes/d14_conditions.mp3` |
| D15 Advisory Sounder | `assets/stings/d15_advisory.mp3` |
| **D15a Fallback Bed** | **`assets/bed.mp3`** ← fixed by `config/radio.liq`; root of `assets/`, no subfolder |
| D16 Lumen Festival Theme | `assets/themes/d16_lumen.mp3` |
| D17 Special Coverage Theme | `assets/themes/d17_special_coverage.mp3` |
| D18 Break Sting — in | `assets/stings/d18_break_in.mp3` |
| D18 Break Sting — out | `assets/stings/d18_break_out.mp3` |
| D19 Sponsor Brand Bug | `assets/stings/d8_brand.mp3` |

(The loop-bed variants are separate trims of the same generation — cut a longer take of B4/C9, keep the
front 8–12 s as the opener and a clean 30–45 s cycle as the `_bed`.) Songs live separately in
`assets/music/` — see `docs/MEDIA_LIBRARY.md`.

Export from Suno at the highest quality your plan allows (WAV if available), keep the WAV master, and
let the pipeline's `_to_mp3()` path / playout handle the broadcast encode. Trim/fade tails clean.

## 5. Production checklist

- [ ] **A1 first.** Lock the signature; save it as a Suno **Persona** (or keep the exact Style
      string) and reuse it so the whole set is one family.
- [ ] Generate **2–4 takes** per asset; keep the best, log the seed/Persona.
- [ ] Verify each against the brand: warm, hopeful, **not** dystopian, **not** camp; no real IP.
- [ ] **Crop to length**; clean fade so it ducks under speech.
- [ ] Cut the **loop-bed variants** (B4/C9) and verify they cycle without an audible seam.
- [ ] **Tier check (anti-sameness):** play A4-bright next to B4 — if they could be mistaken for each
      other, the tiers have collapsed; re-roll with a different lead instrument + BPM (§0).
- [ ] The **D18 pair** works as brackets: in → 3 s of silence → out should feel like leaving and
      returning.
- [ ] Render **`assets/bed.mp3`** (D15a) and confirm it loops cleanly — this is the C4 on-air fallback.
- [ ] Export master (WAV) + place under `assets/` with the **exact names in §4**.
- [ ] Spot-check three transitions by ear: A2→speech, C8 over a sentence end, B4→Vell voice.

---

### Sources (Suno 2026 practice)
- [Jack Righteous — Best Suno AI Prompts 2026](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/best-prompts-for-suno-ai-2026-guide-to-better-results)
- [HookGenius — AI Jingle Generator with Suno (2026)](https://hookgenius.app/learn/ai-jingle-generator-guide/)
- [HookGenius — Suno AI Prompt Guide 2026 (formula + examples)](https://hookgenius.app/learn/suno-prompt-guide-2026/)
- [Blake Crosley — Suno v5.5 Reference: Meta Tags & Style-of-Music](https://blakecrosley.com/guides/suno)
- [Soundverse — Effective Prompts for Instrumental Music on Suno](https://www.soundverse.ai/blog/article/how-to-write-effective-prompts-for-instrumental-music-on-sunoai-1313)
</content>
</invoke>

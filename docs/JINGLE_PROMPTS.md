# JINGLE_PROMPTS.md — Settlement Radio sonic identity (Suno production brief)

> A copy-paste production pack for generating the station's jingle / ident / sting / theme set in
> **Suno (Pro)**. This is a **content brief**, not code. The audio it produces lands in Layer 4
> (Production — sound design) and is aired as non-spoken `Segment`s of `format` `ident` / `sting` /
> `jingle` (see `docs/ARCHITECTURE.md` Seam #2; the producer doesn't *write* these — the scheduler
> just plays the pre-rendered asset). Generated audio lives in `assets/` (gitignored).
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
love it, save it as a **Persona** (Suno Pro) and/or keep its exact Style string. For every later
asset, reuse that Persona (or paste the same palette tags) and change only the job-specific tags.
That's what turns 16 separate generations into one recognisable station.

---

## 1. Suno mechanics — best practices for 2026 (the dials these prompts assume)

Grounded in current (2026) Suno Pro guidance — sources at the bottom.

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

Sixteen assets in four groups: **core identity**, **dayparts & handover**, **program themes**, and
**utility & special**. Each entry: **Type** · **Use in the app** · **Style** (paste into Suno's
Style field) · **Lyrics/Instrumental** · **Length** · **Expected outcome**.

> Notation: 🎵 = sung (uses the Lyrics field) · 🎛️ = instrumental (Instrumental ON).

---

### Group A — Core station identity

#### A1. Signature Ident — the sung logo  🎵  ★ build this one first
- **Type:** Station ident / brand mnemonic (the "logo melody").
- **Use:** top-and-tail of the day, between programs, the thing a clip-cutter drops on a Short. The
  source of the 3–5 note motif every other asset reuses.
- **Style:**
  `warm retro-futuristic station ident, analog synth pads, mellotron strings, soft choir ahh, glass bell mnemonic, gentle close-mic female + male unison, hopeful, wondrous, cozy, cinematic, tape warmth, 75 BPM, instrumental sparse`
- **Lyrics:**
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

#### A2. Top-of-Hour Sounder  🎛️
- **Type:** Instrumental ident (hourly station ID bed).
- **Use:** fires at the top of each hour under the DJ's hour/time check; the "we are Settlement
  Radio, it's the top of the hour" moment. Pairs with the time-check sounder (D13).
- **Style:**
  `instrumental, no vocals, warm retro-futuristic radio sounder, rising analog synth swell, mellotron strings, soft brass fanfare restrained, glass bell motif, hopeful and clean, deep space ambience, tape warmth, 80 BPM`
- **Instrumental:** ON.
- **Length:** 4–6 s.
- **Expected outcome:** a short, dignified swell that quotes the A1 motif and resolves on a clean
  bell — sits *under* a spoken station ID without competing with the voice.

#### A3. AI-Disclosure Bed  🎛️  ← usable now (C3)
- **Type:** Underscore bed for the spoken AI-generation disclosure.
- **Use:** the spoken disclosure ident (Phase C, C3 — "Settlement Radio is generated by AI") rides
  on top of this. Must be calm, neutral, trustworthy — it's a *promise to the listener*, not a show.
- **Style:**
  `instrumental, no vocals, calm ambient underscore, soft sustained analog pad, gentle felt piano, low warm drone, neutral and honest, unhurried, spacious, very low energy, no melody hooks, 60 BPM`
- **Instrumental:** ON.
- **Length:** 12–15 s (long enough to talk over; loops cleanly).
- **Expected outcome:** a quiet, melody-light pad a voice sits cleanly over; reads as sincere and
  transparent, never salesy. Leave headroom — it will be ducked hard under speech.

---

### Group B — Dayparts & handover

#### B4. Night Shift Theme — "The Long Quiet" (Vell)  🎛️
- **Type:** Daypart theme / opener for the night block.
- **Use:** opens Vell's night shift; the cozy, late-hours signature. Maps to the night daypart in
  the Phase D programming model.
- **Style:**
  `instrumental, no vocals, warm ambient night-radio theme, slow felt piano, deep analog pad, distant choir, soft sub-bass swell, intimate and reassuring, starlit, unhurried, vinyl warmth, melancholic but kind, 64 BPM`
- **Instrumental:** ON.
- **Length:** 10–15 s (front) — optionally render a 30–45 s version as a bed.
- **Expected outcome:** "it's late, you're not alone" in sound. Low, warm, intimate — Vell's voice
  drops straight into it. Carries a slowed hint of the A1 motif.

#### B5. First-Light Theme (Wren)  🎛️
- **Type:** Daypart theme / opener for the waking block.
- **Use:** opens Wren's first-light shift; bright, curious, the day waking across the worlds.
- **Style:**
  `instrumental, no vocals, bright hopeful sunrise theme, warm analog synth arpeggio, mallet bells, soft strings rising, gentle uplifting brass, curious and awake, optimistic, clean and airy, mid tempo, 96 BPM`
- **Instrumental:** ON.
- **Length:** 10–15 s.
- **Expected outcome:** a clear lift in energy from the night theme — same palette, brighter key and
  a rising arpeggio. Signals "the worlds are waking." Quotes the A1 motif, brightened.

#### B6. Shift Handover Sounder (Vell → Wren / Wren → Vell)  🎛️
- **Type:** Transition sounder.
- **Use:** the moment one host hands the broadcast to the other (canon: they pass the light at the
  edges of the day). A short musical bridge between night and first-light dayparts.
- **Style:**
  `instrumental, no vocals, gentle transition sounder, two intertwining synth motifs handing off, soft crossfade pad, single warm bell resolve, passing-the-light feeling, tender, cinematic, 80 BPM`
- **Instrumental:** ON.
- **Length:** 5–8 s.
- **Expected outcome:** the night motif (B4) morphs into the dawn motif (B5) — audibly "passing the
  light." Used both directions (it can be reversed for the dawn→night handover).

---

### Group C — Program / format themes

#### C7. News Desk Theme — "The News of the Era"  🎛️
- **Type:** Program theme for the news format.
- **Use:** opens the news desk. Maps to the `news` format (`src/formats/news.py`). Authoritative but
  warm — this station reports the news of the late 27th century without fearmongering.
- **Style:**
  `instrumental, no vocals, futuristic news bulletin theme, confident analog synth pulse, steady mid-tempo arpeggio, clean brass stabs restrained, glass bell accents, authoritative but warm, trustworthy, forward-moving, cinematic, 100 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** "headlines are starting" — purposeful, credible, a steady pulse, never harsh
  or anxious. Resolves into a clean pad the newsreader speaks over.

#### C8. News Sting  🎛️
- **Type:** Short stab / punctuation.
- **Use:** the **sting** the `news` template fires *before* the headlines, and between major items.
  This is the short, sharp sibling of C7.
- **Style:**
  `instrumental, no vocals, short news sting, sharp clean synth stab, single rising glass bell, tight brass hit restrained, urgent but composed, crisp, no tail, 110 BPM`
- **Instrumental:** ON.
- **Length:** 2–3 s.
- **Expected outcome:** a crisp 2-second punctuation that says "next item." Tight transient, quick
  clean tail — designed to fire *over* the end of a sentence.

#### C9. Talk / Feature Theme  🎛️
- **Type:** Program theme for the talk format.
- **Use:** opens the two-DJ conversation / feature segments. Maps to the `talk` format
  (`src/formats/talk.py`). Conversational, warm, a little wry — room to breathe.
- **Style:**
  `instrumental, no vocals, warm conversational talk-show theme, relaxed electric piano, soft brushed groove, mellow analog bass, gentle vibraphone, friendly and curious, a little wry, intimate, easy mid tempo, 88 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s (plus an optional 30 s loopable bed for under-talk ducking).
- **Expected outcome:** "pull up a chair." Loose, friendly, unhurried — sets up banter rather than
  announcing. Loops cleanly as a low bed under conversation.

#### C10. Music Show Bumper — "Into the Music"  🎛️
- **Type:** Bumper into the music format's song slot.
- **Use:** the DJ's hand-off into a track. Maps to the `music` format (`src/formats/music.py`); sits
  right before the `[SONG]` slot the Phase D scheduler fills.
- **Style:**
  `instrumental, no vocals, smooth music-into bumper, warm rising synth sweep, shimmer pad, soft four-on-floor pulse entering, anticipatory, elegant, lifts into a track, clean downbeat resolve, 100 BPM`
- **Instrumental:** ON.
- **Length:** 4–6 s.
- **Expected outcome:** a short lift that lands on a clean downbeat — engineered so a song can start
  the instant it resolves. "And now, the music."

#### C11. Letters Between Worlds Theme  🎵
- **Type:** Program theme for the listener-letters / dedications segment.
- **Use:** the canon's "letters between worlds" (CANON fact #7) — messages that travel weeks across
  the relays, read on air. The future home of listener dedications/requests (Phase E inbound). Tender
  and nostalgic.
- **Style:**
  `warm nostalgic theme, soft female humming, gentle felt piano, mellotron strings, distant radio static warmth, longing and tender, intimate, letters across great distance, slow, 70 BPM`
- **Lyrics:**
  ```
  [Hook]
  (soft, wordless humming over piano — no lyrics, just a tender melody)
  [Outro]
  (humming fades into warm static)
  ```
- **Length:** 8–12 s.
- **Expected outcome:** a wistful, humming signature that says "someone, far away, wrote to you." The
  warmth of distance — nostalgic without being sad. (Hummed, not worded, so it never dates.)

#### C12. Inter-Settlement Games Theme  🎛️  *(speculative / extensible)*
- **Type:** Program theme for a sport / games segment.
- **Use:** *sports* for a between-worlds civilization — the "games between the settlements." Not yet
  in the canon or the format registry; included as a ready-to-go theme for when a sports daypart is
  added (keep tasteful — wonder, not jock-bombast).
- **Style:**
  `instrumental, no vocals, uplifting sports-broadcast theme, bright synth brass fanfare, driving mallet rhythm, soaring strings, triumphant but elegant, energetic and proud, celebratory, cinematic, 120 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** energetic, proud, celebratory — the lift of a games broadcast, kept classy
  and wondrous rather than aggressive. Flag it as a Phase-D-or-later addition.

---

### Group D — Utility & special

#### D13. Settlement-Time Check Sounder  🎛️
- **Type:** Utility sounder (the station "clock").
- **Use:** under the DJ's time check — "coming up on two in the morning, settlement time."
  Time-awareness is core to the station, so the clock deserves its own tiny signature.
- **Style:**
  `instrumental, no vocals, gentle time-check sounder, soft ticking mallet pulse, single clear glass chime, warm pad underneath, calm and precise, reassuring, spacious, 72 BPM`
- **Instrumental:** ON.
- **Length:** 3–5 s.
- **Expected outcome:** a soft, precise chime-and-pulse that reads as "the time is —" without being a
  literal clock tick. Sits under one spoken sentence.

#### D14. Conditions Between Worlds — relay/space weather  🎛️
- **Type:** Program theme for a "weather"-equivalent segment.
- **Use:** real radio has weather; a between-worlds relay has **the conditions across the dark** —
  relay strength, the quiet of the void, the crossing between settlements. Spacious and atmospheric.
- **Style:**
  `instrumental, no vocals, atmospheric space-weather theme, slow shimmering pad, soft radio-signal sweeps, distant wind-like synth, deep calm drone, gentle bell, vast and serene, contemplative, 66 BPM`
- **Instrumental:** ON.
- **Length:** 8–12 s.
- **Expected outcome:** wide, weather-map-of-the-void atmosphere — signal sweeps and deep calm, the
  sense of distance between worlds. Drops to a low bed under the report.

#### D15. All-Settlements Advisory — emergency sounder  🎛️
- **Type:** Alert / advisory sounder (the EAS equivalent, in-character).
- **Use:** a rare, attention-getting advisory ("an all-settlements advisory"). **Tone discipline:**
  the station is *not* dystopian — this is composed and authoritative, a steady hand, **never**
  panic, sirens, or horror. Attention without alarm.
- **Style:**
  `instrumental, no vocals, calm authoritative alert signal, steady low two-tone synth pulse, clear sustained bell tone, composed and serious, attention-getting but never panicked, dignified, sparse, 90 BPM`
- **Instrumental:** ON.
- **Length:** 4–6 s.
- **Expected outcome:** an unmistakable "listen now" signal that stays calm and in control — the
  trustworthy voice of a station that holds steady. Distinct from every warm theme above, by design.

#### D16. Lumen Festival Seasonal Theme  🎵
- **Type:** Special-event theme (annual; canon Event).
- **Use:** the Lumen Festival (CANON Event; in-world 2626-06-24) — every world kindles its lamps at
  the same shared hour. A once-a-year celebratory theme; the station carries the night through as the
  lights come up.
- **Style:**
  `warm celebratory festival theme, soft massed choir, glowing analog synths, twinkling bells, gentle uplifting strings, communal and luminous, hopeful, awe and togetherness, cinematic, building slowly, 84 BPM`
- **Lyrics:**
  ```
  [Hook]
  (a soft, wordless massed choir "ahh", warm and rising — lights coming up across the dark)
  [Build]
  (bells layer in, the choir swells gently, never bombastic)
  [Outro]
  (resolves into the Settlement Radio motif, glowing)
  ```
- **Length:** 12–20 s (a longer hero piece is fine here — it's seasonal).
- **Expected outcome:** the warmest, most communal piece in the set — many worlds lighting their
  lamps at once. Resolves into the A1 motif so even the festival feels like *home*.

---

## 3. Mapping to the app (so these slot in without a rewrite)

| Asset | `Segment.format` | Where it's used |
|---|---|---|
| A1 Signature Ident | `ident` | between programs; clip cutter |
| A2 Top-of-Hour | `ident` | hourly station ID, under DJ |
| A3 Disclosure Bed | `ident` | under spoken disclosure (C3) |
| B4 Night Theme | `ident`/bed | night daypart open (Phase D programming) |
| B5 First-Light Theme | `ident`/bed | first-light daypart open |
| B6 Handover | `sting` | daypart transition (Vell↔Wren) |
| C7 News Theme | `ident`/bed | `news` format open |
| C8 News Sting | `sting` | inside `news` (before headlines / between items) |
| C9 Talk Theme | `ident`/bed | `talk` format open |
| C10 Music Bumper | `sting` | `music` format, before the `[SONG]` slot |
| C11 Letters Theme | `ident`/bed | listener-letters segment (Phase E inbound) |
| C12 Games Theme | `ident`/bed | future sports daypart (extensible) |
| D13 Time-Check | `sting` | under DJ time checks |
| D14 Conditions | `ident`/bed | "weather"-equivalent segment |
| D15 Advisory | `sting` | rare all-settlements advisory |
| D16 Lumen Festival | `ident`/bed | annual event window |

These are pre-rendered audio assets the scheduler plays directly — `script=None`, `audio_path` set —
exactly the `ident`/`sting`/`jingle` Segments described in `docs/ARCHITECTURE.md` Seam #2. No model
below the seam changes.

## 4. File / naming convention (suggested)

Drop finals in `assets/` (gitignored). Suggested names so the scheduler can glob them predictably:

```
assets/idents/a1_signature.mp3
assets/idents/a2_top_of_hour.mp3
assets/idents/a3_disclosure_bed.mp3
assets/themes/b4_night.mp3   b5_first_light.mp3
assets/stings/b6_handover.mp3  c8_news_sting.mp3  c10_music_bumper.mp3  d13_time_check.mp3  d15_advisory.mp3
assets/themes/c7_news.mp3  c9_talk.mp3  c11_letters.mp3  c12_games.mp3  d14_conditions.mp3  d16_lumen.mp3
```

Export from Suno at the highest quality your plan allows (WAV if available), keep the WAV master, and
let the pipeline's `_to_mp3()` path / playout handle the broadcast encode. Trim/fade tails clean.

## 5. Production checklist

- [ ] **A1 first.** Lock the signature; save it as a Suno **Persona** (or keep the exact Style
      string) and reuse it so the whole set is one family.
- [ ] Generate **2–4 takes** per asset; keep the best, log the seed/Persona.
- [ ] Verify each against the brand: warm, hopeful, **not** dystopian, **not** camp; no real IP.
- [ ] **Crop to length**; clean fade so it ducks under speech.
- [ ] Export master (WAV) + place under `assets/` with the names above.
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

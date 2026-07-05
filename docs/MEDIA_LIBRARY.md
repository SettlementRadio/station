# MEDIA_LIBRARY.md — Settlement Radio media production brief (Suno)

> A copy-paste **production pack** for generating the station's first real media library in **Suno
> (Pro / v5+)**: the **jingle set** (already spec'd — see cross-ref) and the **first ~27 songs** as
> *cultural artifacts* of the +600y world. This is a **content brief + a data spec**, not code. It
> tells you (the human) exactly what to generate, the exact prompt to paste for each, how to make a
> handful of generations sound like **one station with a real music culture**, and how every file
> maps into the D7 `tracks` catalogue so a cleared track — with its lore — *just plays*.
>
> **Companion docs:** `docs/JINGLE_PROMPTS.md` (the sonic-identity set — jingles/idents/
> stings/beds; still the source of truth for those). `docs/PHASE_D_PRODUCTION_TASKS.md` (D7 — the code
> that places jingles and fills the `[SONG]` slot). `docs/canon/70-music.md` + `65-arts.md` (the music
> *culture* these artists inhabit). `docs/canon/90-cast.md` (the DJs who introduce them).
>
> **Hard rules carried in (CLAUDE.md):** tribute, **never** derivative — **no real artist, band,
> franchise, or composer named in any prompt** (Suno blocks it and it breaks the IP boundary); the
> in-world year is `real year + 600` (present ≈ **2626**) — the lore below uses in-world years/eras,
> never a real one; every artist/song here is **original to this world**.

---

## 0. What you're producing (the checklist)

Two media kinds, two homes, both curated (live under `assets/`, gitignored, backed up — never GC'd):

| Kind | Count | Home | Prompt source | Maps to |
|---|---|---|---|---|
| **Jingles / idents / stings / beds** | see JINGLE_PROMPTS §4 (~27 files) | `assets/{idents,themes,stings}/` + `assets/bed.mp3` | `docs/JINGLE_PROMPTS.md` | placed by the grid (D7.2/D7.3) |
| **Songs** (cultural artifacts) | **27** | `assets/music/` | **this doc, §5** | `tracks` table (D7.0), `[SONG]` slot (D7.4) |

This doc's job is the **27 songs** (and the *media library spec* that catalogues them). The jingles are
already fully spec'd next door — **generate those from `JINGLE_PROMPTS.md`**; §1 below applies to both.

**Do them in this order** (each stage de-risks the next):
1. **Jingle A1 first** (the sung logo) → save as a Persona; it seeds the whole sonic family.
2. The rest of the **jingle set** (the JINGLE_PROMPTS **§4 table** is the authoritative file list —
   incl. `assets/bed.mp3`, the sweepers, and the loop-bed variants).
3. The **27 songs** here — **one artist at a time**: generate the artist's first track, love it, **save it
   as a Persona**, then generate that artist's remaining tracks *from the Persona* so the band sounds like
   one act. (§2 explains why this is the whole trick.)

---

## 1. Suno mechanics — getting the most out of each generation (v5, 2026)

Verified against current Suno guidance (sources at the foot). These are the dials every prompt below assumes.

**The field limits (v5 Custom Mode) — the "max length" you asked about:**

| Field | Hard cap | Practical sweet spot |
|---|---|---|
| **Style of Music** | ~**1,000 chars** | **8–15 comma tags** (~200–400 chars). *Past ~15 tags Suno starts ignoring the tail and contradicting itself.* |
| **Lyrics** | ~**5,000 chars** (~80–100 lines) | **≤ ~3,000 chars** — beyond that Suno rushes the song |
| **Title** | ~**100 chars** | short |

None of the prompts below come close to the caps — **shorter and specific beats long and impressive.**
Lead the Style string with the load-bearing tags: **genre → mood → lead instrument → vocal/instrumental
→ production → tempo (BPM)**. Order = priority.

**Getting the most out of each generation:**

- **Custom Mode, always** (Simple Mode hides the Style/Lyrics/Title fields). Every entry gives you a
  paste-ready **Style** string and a **Lyrics** block (sung) or an **Instrumental: ON** instruction.
- **One idea per field.** Don't stuff 6 genres + 10 instruments into Style — competing instructions
  *reduce* consistency. 1–2 genres, one mood/energy line, 2–4 priority instruments.
- **Personas are the album-maker** (see §2). A Persona is a saved *vocal + sonic identity* pulled from a
  song you already like. Reusing it is how the three songs by one artist actually sound like *the same
  artist*. This is the single most important lever for a believable roster.
- **Structure tags go in the Lyrics field**, not Style: `[Intro] [Verse] [Chorus] [Bridge]
  [Instrumental] [Outro]`. Inline delivery cues in parens on their own line, e.g.
  `(close-mic, almost whispered, tape warmth)`.
- **Instrumental pieces:** toggle **Instrumental ON** *and* keep `instrumental, no vocals` in the Style
  string (belt-and-suspenders).
- **Generate 2–4 takes, keep the best, re-roll the rest.** Cheap on Pro. **Log the seed/Persona** of the
  winner so re-makes match.
- **Full song, then Trim.** v5 renders up to ~8 min; for the catalogue you want **standard 3–4 min
  songs.** The full lyric structures below (2–3 verses, repeated chorus, bridge) naturally land there.
  Generate the full take, then **Crop/Trim** only if it overruns (~4:30+) and **fade the tail clean**
  so the back-announce lands without a stray bar. (Songs, unlike jingles, are *not* ducked under speech —
  they play in the clear in the `[SONG]` slot.)
- **Extend / Cover** only if a take is *almost* right — extend to grow a too-short idea, cover to
  re-voice a melody you like through a Persona. Prefer a clean re-roll for small misses.
- **Exclude Styles** to hold the station tone. Default exclude set (both jingles and songs):
  `aggressive EDM, trap, drill, dubstep, heavy metal, distorted, harsh, comedic, chiptune novelty, autotune-heavy modern pop`.
- **Export the highest quality your plan allows** (WAV if offered); keep the WAV master, let the
  pipeline's `_to_mp3()` do the broadcast encode.
- **IP boundary (hard rule):** never "in the style of \<real artist/film\>" — describe the *sound* with
  instruments + adjectives. Every prompt below already does.

**The brand-sound thread (both kinds share it).** Everything Settlement Radio airs should feel like it
comes from one warm, hopeful, wondrous world — *cozy vastness*, golden-age + new-wave sci-fi **spirit**,
never dystopian, never camp. The songs are more varied than the jingles (they're a whole *culture*), but
they still live in the palette from `JINGLE_PROMPTS.md §0`: **warm analog tape, real space and distance,
human and unhurried.** Keep `warm analog` / `tape warmth` / `spacious` in most Style strings as the
family thread.

---

## 2. The load-bearing idea — songs are *cultural artifacts*, and artists are *Personas*

The D7 spec is emphatic: a song in this world **is not a labelled file — it's a cultural artifact** with
an artist, an era, and a story. The DJ never "plays a piece of music"; they say *"here's a classic from
the Reconnection, by the Ninefold Pipes of Forge, off* Foundry Evensong*."* So the media library is
**two linked things**:

1. **The audio** (`assets/music/…`), generated here in Suno.
2. **The lore** (the `tracks` row + the artist behind it) — title, **artist**, album, in-world era, a
   one-line **story**, mood, tags. This is what the DJ intro/back-announce and now-playing draw on (D7.4).

**Why the artist matters twice.** In the D7.0 schema, a track carries `in_world_artist` (plain text —
what ships now) **and** a nullable `artist_figure_id` (a link to a **D10 figure** — the musician as a real
in-world *person*, quotable and guest-able, backfilled when D10 lands). So building a **coherent roster of
named artists now** pays off twice: it makes the catalogue feel like a real music scene today, and it
becomes the D10 figure list tomorrow (a one-off backfill connects each `in_world_artist` string to its
figure row). **That's the "how the songs connect with names and bands" answer:** we design a small,
canon-true **roster** (§4) first, then every song is *by* one of them.

**Persona = artist.** In Suno, we make each roster artist **one Persona**. Generate the artist's first
song, save it as a Persona named for the artist, and cut their other songs from it. Result: their tracks
share a voice and sonic signature — a believable *act*, not 20 unrelated generations. **The roster is the
bridge between the Suno mechanic (Personas) and the app data model (`in_world_artist` → `artist_figure_id`).**

**Playable vs referenceable (keep this line clean).** Only tracks *with a file* are **playable**. The
world's wider music culture — a hundred artists/albums/scenes the DJs merely *talk about* — is lore/events
(D1 canon, D10 figures, D3 releases), **no audio needed.** So this pack clears **27 playable tracks by
~14 artists**; the DJs can reference a far larger culture around them. Don't try to record the whole world
— record a **representative core** that spans the genres, eras, and worlds (§4), and let talk fill the rest.

**Licence.** Suno **Pro/Premier** plans grant commercial-use rights to what you generate — so the
`licence_note` for these is *"Suno Pro, commercial rights, self-owned — cleared for broadcast."* **Confirm
your plan's current terms before air** (this is the human's clearance call, per D7); free-tier output is
*not* cleared. Record the note per track in the manifest (§6).

---

## 3. The media-library spec (how a generated song becomes a catalogued track)

Each song below ships as **one WAV/MP3 file + one manifest entry**. D7.0 seeds the `tracks` table from a
**music-lore manifest** (`config/tracks.yaml` — human-owned, diffable, survives a canon refresh; `make
seed-tracks` imports it). The manifest field ↔ `tracks` column mapping:

| Manifest field | `tracks` column | Source |
|---|---|---|
| `title` | `title` | §5 |
| `artist` | `in_world_artist` | §4 roster |
| `artist_figure_id` | `artist_figure_id` (nullable) | **null now**; backfilled at D10 |
| `album` | `album` | §5 (nullable) |
| `era` / `in_world_year` | `in_world_year`/`era` | §5 (in-world; present ≈ 2626) |
| `story_blurb` | `story_blurb` | §5 — the one line the DJ tells |
| `mood` | `mood` | §5 — **used by the D7.4 selector** (daypart/world-mood match) |
| `tags` | `tags` | §5 — genre/world/era/movement/instrument — **selector era-spread + freshness** |
| `duration_sec` | `duration_sec` | stamped from the final file |
| `licence_note` | `licence_note` | §2 (Suno Pro) |
| `audio_path` | `audio_path` | §3 naming |

**File naming** (so the D7 seeder/scheduler globs predictably — `assets/music/` is GC-safe):
```
assets/music/<artist-slug>__<title-slug>.mp3
  e.g.  assets/music/halden-vre__the-slow-star.mp3
        assets/music/ninefold-pipes-of-forge__foundry-evensong.mp3
```
Keep the WAV master alongside (or in a `masters/` sibling you back up); ship the mp3 the pipeline reads.

**Mood + tag vocabularies** (keep them consistent so the selector's rules bite):
- **mood** (one primary, matched to daypart/world mood): `melancholy · mellow · contemplative · serene ·
  wistful · tender · warm · hopeful · bright · joyful · celebratory · driving · solemn · nostalgic`.
- **tags** (several; the selector spreads eras & avoids repeats over these): a **genre** tag
  (`void-ballad · core-harmony · frontier-reel · exodus-hymn · drift-song · earth-roots · lane-rock ·
  pulse-dance · void-lounge · relay-pop`), a **world**
  (`concordance · meridian · forge · freeholds · outer-station · betweener · earth`), an **era**
  (`first-expansion · the-silence · reconnection · age-of-relays`), and optional **movement/instrument**
  (`purist · synthesist · localist · outer-revival · resonance-pipe · synth-harpsichord · salvage-perc`).

---

## 4. The roster — the "bands" (each = one Suno Persona)

Fourteen acts, chosen to **span the canon's genres, movements, worlds, and eras** so the catalogue has
real variety (and the D7.4 selector has range to work with) — **including the up-tempo end**: real radio
needs rock, dance, pop, and lounge, not only ballads and hymns. Canon licenses this explicitly — the
Divergence produced "a thousand local scenes flowering in isolation" (`70-music.md`), so the named canon
genres are examples, not an exhaustive list; R11–R14 below are four more such scenes, each grounded in a
SPIRIT strain (Heinlein's competent frontier folk → hauler rock; the Synthesists → dance; retro-futurist
warmth → relay-pop; core abundance → late-night lounge). The tone guardrail still holds: driving but
**warm** — the §1 exclude set (no metal/harsh/aggressive EDM) applies to every one of them. Several are seeded directly from existing canon
anecdotes (the DJs already reference them — noted **↳ canon**). For each: build the Persona from the
first-listed song, reuse it for the rest.

| # | Artist (`in_world_artist`) | Genre / lane | World · Era | Voice signature (the Persona) | Songs |
|---|---|---|---|---|---|
| R1 | **Halden Vre** | Void Ballads | outer-station · present | lone weathered baritone over a life-support drone; vast, spare, close-mic | 3 |
| R2 | **Ysolde Mar** | Drift Songs | betweener · present | a navigator's warm alto, sung to stay awake on long crossings; looping, patient ↳ *Orin: "The Long Way Round"* | 2 |
| R3 | **The Ninefold Pipes of Forge** | resonance-pipe / Purist-industrial (instrumental) | forge · Reconnection | deep organ-like alloy tubes, no vocals; cathedral-of-industry ↳ *Orin: Forge resonators from industrial waste* | 2 |
| R4 | **Concordance Exchange Consort** | Core Harmonies | concordance · present | layered synth-harpsichord + strings, refined and abundant | 2 |
| R5 | **Brace & the Tin Reelers** | Frontier Reels | freeholds · present | joyful group vocal, salvaged percussion (oxygen-tank drums, wire chimes), foot-stomping | 3 |
| R6 | **Sixteen Hands** | Drift / collective | betweener · present | a collective who never met, layered by relay — many distant voices stitched across the dark ↳ *canon fact 9* | 2 |
| R7 | **The Shellwrights** | Localist / far-worlds | outer-station · present | strange bright resonance from instruments built of native-fauna shells; airy, alien-warm ↳ *Mira's "shells of native fauna"* | 2 |
| R8 | **The First-Ships Choir** | Exodus Hymns | earth→core · First Expansion (classic) | solemn massed choir, hymn-like, four centuries old and still sung | 2 |
| R9 | **The Outer Revival** | Void-revival (Outer Revival movement) | core rediscovering outer-station · present | core musicians reviving a Silence-era outer style — polished melancholy ↳ *canon fact 11* | 2 |
| R10 | **(archival — "First Generation")** | Earth-roots (found recording) | earth · pre-diaspora origin | a crackly, tender solo acoustic voice from the original ship's records ↳ *Greaves/Archivist deep stacks* | 1 |
| R11 | **The Lane Runners** | lane-rock (hauler rock) | betweener · present | warm driving analog rock — engine-room drums, jangly guitars, a road-worn male lead; anthems of the freight lanes | 2 |
| R12 | **Auroral Standard** | pulse-dance (Synthesist) | meridian · present | warm four-on-the-floor synth-dance, analog arpeggios, euphoric female lead — storm-season dance music ↳ *Meridian's storm coast (Vell's homeworld)* | 2 |
| R13 | **The Nightliners** | void-lounge | concordance · present | late-night lounge — brushed drums, upright bass, electric piano, a smoky warm female voice; the deep-hours standard | 1 |
| R14 | **Vela & the Beacons** | relay-pop (retro) | core · present | bright retro harmony-pop — handclaps, doo-wop-flavoured group vocals, hooky and tender; relay-romance songs | 1 |

= **27 slots — ship all 27** (the §5 list matches; S21 stays the optional archival extra if you must cut one).

**Album / series lore you can reuse:** Mira's **"Deep Listening"** series (Core Harmonies + Shellwrights
features); the frontier compilation **"Salvage & Song"** (Tin Reelers); the archival series **"The Deep
Stacks"** (First-Ships Choir, First Generation). These give albums for the `album` field and hooks for DJ
intros.

---

## 5. The 27 songs — paste-ready

For each: a **metadata block** (→ the manifest / `tracks` row — this is the *lore* the DJ tells) and the
**Suno prompt** (Style string + Lyrics/Instrumental). 🎵 = sung (Lyrics field) · 🎛️ = instrumental
(Instrumental ON). Build each artist's Persona from their **first** song.

> **HOW TO READ EACH ENTRY — only two lines go into Suno.** Suno has exactly two paste boxes:
> - **`Style:`** → paste into Suno's **Styles** box.
> - **`Lyrics:`** → paste into Suno's **Lyrics** box (for a 🎛️ entry, skip it and set *More Options →
>   Lyrics → Instrumental*). Also type the **Title**, and set **Vocal Gender** if the entry names a
>   male/female voice.
>
> **Everything else in the block — `artist`, `album`, `era/year`, `mood`, `tags`, `story_blurb` — is NOT
> a Suno field.** It's the song's catalogue lore; it goes into `config/tracks.yaml` (§6), which the
> *station app* uses later (DJ intros, now-playing, song selection). Don't enter it in Suno.

> **AFTER YOU GENERATE — name it + store it (do this every time).**
> 1. Download the take from Suno (WAV master + MP3).
> 2. **Rename the MP3 to the exact "Save as" name** in the table below and drop it in **`assets/music/`**.
> 3. Later, its `config/tracks.yaml` row's `audio_path` must equal that same path — **that string is the
>    only thing linking the file to its lore; the code finds nothing by scanning the folder.**
>
> | # | Song | **Save the file as** |
> |---|---|---|
> | S1 | The Slow Star | `assets/music/halden-vre__the-slow-star.mp3` |
> | S2 | Nobody Answers the Dark | `assets/music/halden-vre__nobody-answers-the-dark.mp3` |
> | S3 | Keeper's Lament | `assets/music/halden-vre__keepers-lament.mp3` |
> | S4 | The Long Way Round | `assets/music/ysolde-mar__the-long-way-round.mp3` |
> | S5 | Cargo-Hold Lullaby | `assets/music/ysolde-mar__cargo-hold-lullaby.mp3` |
> | S6 | Foundry Evensong | `assets/music/ninefold-pipes-of-forge__foundry-evensong.mp3` |
> | S7 | Signalfire | `assets/music/ninefold-pipes-of-forge__signalfire.mp3` |
> | S8 | Gardens Under Glass | `assets/music/concordance-exchange-consort__gardens-under-glass.mp3` |
> | S9 | The Long Table | `assets/music/concordance-exchange-consort__the-long-table.mp3` |
> | S10 | Salvage Yard Saturday | `assets/music/brace-and-the-tin-reelers__salvage-yard-saturday.mp3` |
> | S11 | Wire and Bone | `assets/music/brace-and-the-tin-reelers__wire-and-bone.mp3` |
> | S12 | The Oxygen Drum | `assets/music/brace-and-the-tin-reelers__the-oxygen-drum.mp3` |
> | S13 | Letters We Sent Ahead | `assets/music/sixteen-hands__letters-we-sent-ahead.mp3` |
> | S14 | Sixteen Skies | `assets/music/sixteen-hands__sixteen-skies.mp3` |
> | S15 | Tideshell Resonance | `assets/music/shellwrights__tideshell-resonance.mp3` |
> | S16 | Fauna Song | `assets/music/shellwrights__fauna-song.mp3` |
> | S17 | Departure Hymn | `assets/music/first-ships-choir__departure-hymn.mp3` |
> | S18 | The Blue Cradle | `assets/music/first-ships-choir__the-blue-cradle.mp3` |
> | S19 | Nobody Told the Frontier It Was Over | `assets/music/outer-revival__nobody-told-the-frontier-it-was-over.mp3` |
> | S20 | Rediscovery | `assets/music/outer-revival__rediscovery.mp3` |
> | S21 | Earthlight (First-Generation Recording) | `assets/music/first-generation__earthlight.mp3` |
> | S22 | Burn Day | `assets/music/lane-runners__burn-day.mp3` |
> | S23 | The Thousand-Hour Road | `assets/music/lane-runners__the-thousand-hour-road.mp3` |
> | S24 | Stormglass | `assets/music/auroral-standard__stormglass.mp3` |
> | S25 | Aurora Season | `assets/music/auroral-standard__aurora-season.mp3` |
> | S26 | Two O'Clock, Settlement Time | `assets/music/nightliners__two-oclock-settlement-time.mp3` |
> | S27 | Meet Me on the Thread | `assets/music/vela-and-the-beacons__meet-me-on-the-thread.mp3` |
>
> (Keep the WAV masters too — e.g. a `masters/` folder you back up — but the pipeline plays the MP3s.)

> Present in-world year ≈ **2626**. Years below are **in-world**; they exist to spread eras for the
> selector and to give the DJ a "from the …" line — treat them as authored lore, not code.

---

### R1 · Halden Vre — Void Ballads (outer-station, present) — Persona: build from S1

#### S1. "The Slow Star"  🎵  ★ Persona seed for R1
- **artist:** Halden Vre · **album:** *A Window in the Dark* · **era/year:** Age of the Relays, 2611
- **mood:** melancholy · **tags:** `void-ballad, outer-station, age-of-relays, solo, melancholy`
- **story_blurb:** "Written on a one-keeper station months from the nearest light — a man singing to the
  single star that never sets in his window."
- **Style:** `warm void ballad, sparse and slow, lone weathered baritone, close-mic intimate, sustained analog drone like life-support hum, distant felt piano, deep space ambience, tape warmth, melancholic but tender, 58 BPM`
- **Lyrics:**
  ```
  [Intro]
  (close-mic, almost whispered, a low drone underneath)
  [Verse 1]
  There's a star that never leaves my window,
  it doesn't rise, it doesn't fall.
  Months from the nearest lit-up doorway —
  it's company enough, that's all.
  [Verse 2]
  I walk the ring at seven, station time,
  check the seals, the air, the light.
  The kettle and the old transmitter
  are the loudest things tonight.
  [Chorus]
  Slow star, slow star, hold the line for me,
  I'll keep the lamp lit if you keep the dark company.
  Slow star, slow star, patient in the pane,
  come the next wake-cycle, we'll do it all again.
  [Verse 3]
  The relay brings me voices weekly,
  songs and news from kinder skies.
  I answer, though they will not hear me
  till the winter satellites rise.
  [Chorus]
  [Bridge]
  (quieter, half-spoken)
  They asked me once why I stay out here,
  where the dark leans hard on the glass.
  I said, someone has to hold this corner —
  and wave the long ships as they pass.
  [Instrumental]
  (felt piano over the drone, spare)
  [Chorus]
  (warmer, resolved)
  [Outro]
  (voice thins into the drone, unresolved, warm)
  ```
- **Length:** ~3:30 (standard song).

#### S2. "Nobody Answers the Dark"  🎵  *(from R1 Persona)*
- **artist:** Halden Vre · **album:** *A Window in the Dark* · **era/year:** Age of the Relays, 2613
- **mood:** contemplative · **tags:** `void-ballad, outer-station, age-of-relays, solo, solitude`
- **story_blurb:** "A keeper's half-question to the emptiness beyond the last settlement — sent out on a
  relay that won't reach anyone for half a year."
- **Style:** `warm void ballad, spare, lone weathered baritone, close-mic, low sustained synth drone, single sparse guitar, vast and lonely, unhurried, tape warmth, reverent, 60 BPM`
- **Lyrics:**
  ```
  [Intro]
  (low drone, breath, a single sparse guitar)
  [Verse 1]
  I send my voice into the nothing,
  half a year till it lands somewhere.
  A keeper's log, a joke, a question,
  for anyone still out there.
  [Verse 2]
  Past my window ends the mapped dark,
  past the mapped dark, no one knows.
  They say it's empty, say it's silent —
  but silence too is something that grows.
  [Chorus]
  Nobody answers the dark, nobody answers —
  but I keep talking, so it knows I'm there.
  Nobody answers the dark, nobody has to —
  an unanswered voice is still a prayer.
  [Verse 3]
  Some nights I catch a ghost of static
  and I let myself pretend
  it's someone at the far end, listening —
  some other keeper, some other friend.
  [Chorus]
  [Bridge]
  (half-spoken, very close)
  And if an answer ever comes here,
  long after I've gone quiet and grey,
  tell them the dark was never empty —
  a voice was here. It did not go away.
  [Chorus]
  (softer, fading)
  [Outro]
  (fades to drone and breath)
  ```
- **Length:** ~3:30 (standard song).

#### S3. "Keeper's Lament"  🎛️  *(from R1 Persona — instrumental)*
- **artist:** Halden Vre · **album:** *A Window in the Dark* · **era/year:** Age of the Relays, 2612
- **mood:** wistful · **tags:** `void-ballad, outer-station, age-of-relays, instrumental, wistful`
- **story_blurb:** "The wordless version keepers hum on the long shifts — no lyrics ever settled on it,
  so everyone finishes it their own way."
- **Style:** `instrumental, no vocals, slow void-ballad instrumental, felt piano lead, low analog drone, distant bowed strings, soft wordless breath-pad, deep space, spare and aching, tape warmth, 56 BPM`
- **Instrumental:** ON. **Length:** ~3:00 (standard song; let the theme develop through 2–3 variations).

---

### R2 · Ysolde Mar — Drift Songs (betweener, present) — Persona: build from S4

#### S4. "The Long Way Round"  🎵  ★ Persona seed for R2 — ↳ **canon** (Orin references this song)
- **artist:** Ysolde Mar · **album:** *Cargo-Hold Songs* · **era/year:** Age of the Relays, 2619
- **mood:** mellow · **tags:** `drift-song, betweener, age-of-relays, solo, mellow`
- **story_blurb:** "A navigator's song, learned in a cargo hold from a woman who plays to stay awake on
  the crossings — it loops the way a long journey does." *(As introduced by Orin on air.)*
- **Style:** `warm drift song, slow looping groove, navigator's alto voice, brushed hand-percussion, mellow analog bass, soft rhodes, gentle repeating motif, patient and hypnotic, long-journey feel, tape warmth, 72 BPM`
- **Lyrics:**
  ```
  [Intro]
  (warm, a little tired, close and human; the loop begins)
  [Verse 1]
  Nine weeks of dark and the same three stars,
  I sing to keep my eyes from the floor.
  Coffee's cold and the console's humming
  a chord I've heard ten thousand times before.
  [Chorus]
  We go the long way round, the long way round,
  no straight line home when there's no straight line at all.
  We go the long way round, the long way round,
  and every turn I take, I take it singing — that's all.
  [Verse 2]
  Wake me at the buoy, wake me at the turn,
  I've got a song for every hour there is to burn.
  The freight don't care and the dark don't listen,
  but a song is for the singer first, I've learned.
  [Chorus]
  [Bridge]
  (slower, almost to herself)
  My mother flew this lane before me,
  her mother drew the charts by hand.
  They sang the same three stars I'm singing —
  the road remembers, the road understands.
  [Verse 3]
  Landfall's just a week past nowhere,
  I'll sleep when the lights come into view.
  Till then it's me and the hum and the turning,
  and this old song to see me through.
  [Chorus]
  [Chorus]
  (looser, road-worn, fading)
  [Outro]
  (the motif loops, fades on the road)
  ```
- **Length:** ~3:45 (standard song; a drift song can breathe).

#### DONE_S5. "Cargo-Hold Lullaby"  🎵  *(from R2 Persona)*
- **artist:** Ysolde Mar · **album:** *Cargo-Hold Songs* · **era/year:** Age of the Relays, 2620
- **mood:** tender · **tags:** `drift-song, betweener, age-of-relays, solo, tender`
- **story_blurb:** "What she sings to the freight and to herself in the last watch before landfall —
  half a lullaby, half a promise to arrive."
- **Style:** `warm drift lullaby, very slow, soft alto humming into gentle verse, muted rhodes, low warm bass, distant ship-hum ambience, tender and drowsy, tape warmth, spacious, 64 BPM`
- **Lyrics:**
  ```
  [Intro]
  (soft humming over the ship-hum, drowsy)
  [Verse 1]
  Hush now, freight and bone and me,
  landfall's close as close can be.
  The last watch always runs the longest,
  so I'll sing us down easy, one, two, three.
  [Chorus]
  Sleep the dark, we'll wake in light,
  I'll steer us gentle through the night.
  Sleep the dark, the lane runs true,
  the morning's already waiting for you.
  [Verse 2]
  Hush now, engines, ease your turning,
  you've carried us farther than maps can say.
  There's a bed and a meal and a blue-lit harbour
  a little less than a sleep away.
  [Chorus]
  [Bridge]
  (barely above a whisper)
  And if I drift, the boards will wake me —
  a ship looks after those who sing.
  Old spacers say the hull remembers
  every lullaby you bring.
  [Chorus]
  (slower, dissolving)
  [Outro]
  (humming into ship-hum, fades)
  ```
- **Length:** ~3:15 (standard song).

---

### R3 · The Ninefold Pipes of Forge — resonance-pipe instrumental (forge, Reconnection) — Persona: S6

#### DONE_S6. "Foundry Evensong"  🎛️  ★ Persona seed for R3 — ↳ **canon** (Forge resonance pipes)
- **artist:** The Ninefold Pipes of Forge · **album:** *Resonance* · **era/year:** the Reconnection, c. 2470 (a classic)
- **mood:** solemn · **tags:** `resonance-pipe, forge, reconnection, instrumental, purist, solemn`
- **story_blurb:** "Played on Forge's resonance pipes — long alloy tubes first built as signalling
  devices in the foundries, later bowed and struck into an organ of industry. This is the piece the
  night shift plays out over the cooling floors."
- **Style:** `instrumental, no vocals, deep resonance-pipe organ music, long bowed alloy tubes, cathedral-of-industry, low sustained metallic overtones, slow processional, warm reverb, awe and gravity, hopeful resolve, tape warmth, 60 BPM`
- **Instrumental:** ON. **Length:** ~3:15 (standard song; let the theme develop through 2–3 variations).

#### DONE_S7. "Signalfire"  🎛️  *(from R3 Persona)*
- **artist:** The Ninefold Pipes of Forge · **album:** *Resonance* · **era/year:** the Reconnection, c. 2475
- **mood:** hopeful · **tags:** `resonance-pipe, forge, reconnection, instrumental, hopeful`
- **story_blurb:** "The pipes were signalling gear before they were instruments; this piece remembers
  that — a call across the foundry-dark that answers itself, warmer each time."
- **Style:** `instrumental, no vocals, resonance-pipe call-and-answer, struck and bowed alloy tubes, rising metallic motif, deep sub-bass swell, industrial-sacred, building warmth, spacious reverb, hopeful, 66 BPM`
- **Instrumental:** ON. **Length:** ~3:10 (standard song; let the theme develop through 2–3 variations).

---

### R4 · Concordance Exchange Consort — Core Harmonies (concordance, present) — Persona: S8

#### S8. "Gardens Under Glass"  🎛️  ★ Persona seed for R4
- **artist:** Concordance Exchange Consort · **album:** *Deep Listening, Vol. II* · **era/year:** Age of the Relays, 2607
- **mood:** serene · **tags:** `core-harmony, concordance, age-of-relays, synth-harpsichord, instrumental, serene`
- **story_blurb:** "Core Harmonies from Concordance, the oldest world — layered synth-harpsichord written
  for the roofed gardens of the Exchange Houses, where nothing has wanted for anything in centuries."
- **Style:** `instrumental, no vocals, lush core-harmony chamber piece, layered synth-harpsichord, warm strings, soft woodwinds, refined and abundant, interweaving counterpoint, graceful, golden and unhurried, tape warmth, 84 BPM`
- **Instrumental:** ON. **Length:** ~3:30 (standard song; let the theme develop through 2–3 variations).

#### DONE_S9. "The Long Table"  🎵  *(from R4 Persona — restrained vocal)*
- **artist:** Concordance Exchange Consort · **album:** *Deep Listening, Vol. II* · **era/year:** Age of the Relays, 2609
- **mood:** warm · **tags:** `core-harmony, concordance, age-of-relays, synth-harpsichord, warm`
- **story_blurb:** "A gentle piece for the Settlement Council's long table — the sound of many worlds
  sitting down together, for once, in the same room."
- **Style:** `warm core-harmony art-song, soft mixed choir gentle, layered synth-harpsichord, warm strings, dignified and communal, hopeful, refined, spacious, tape warmth, 80 BPM`
- **Lyrics:**
  ```
  [Intro]
  (synth-harpsichord alone, graceful)
  [Verse 1]
  (soft mixed choir, restrained, almost spoken-sung)
  Set the long table, world by world,
  a place for every distant light.
  Some sailed a season, some a lifetime,
  and all of them arrive tonight.
  [Chorus]
  We came the whole dark just to sit,
  and share the bread of the same night.
  We came the whole dark just to sit —
  and for once, the whole dark holds us right.
  [Verse 2]
  The frontier chair and the core-world chair
  are cut from the same old ship-hull board.
  Whatever we argue when the lamps burn low,
  we all reached for the same door.
  [Chorus]
  [Bridge]
  (a single voice rises over the choir)
  Pass the salt of the outer stations,
  pass the wine of the garden worlds;
  what the distance couldn't sever,
  a table gently holds.
  [Instrumental]
  (synth-harpsichord counterpoint, strings answering)
  [Chorus]
  (fuller, warm and open)
  [Outro]
  (choir resolves warm and open)
  ```
- **Length:** ~3:30 (standard song).

---

### R5 · Brace & the Tin Reelers — Frontier Reels (freeholds, present) — Persona: S10

#### DONE_S10. "Salvage Yard Saturday"  🎵  ★ Persona seed for R5
- **artist:** Brace & the Tin Reelers · **album:** *Salvage & Song* · **era/year:** Age of the Relays, 2622
- **mood:** joyful · **tags:** `frontier-reel, freeholds, age-of-relays, salvage-perc, joyful`
- **story_blurb:** "A Freeholds reel banged out on oxygen-tank drums and wire chimes — the Saturday
  sound of people who work hard all week and celebrate harder, on instruments made from what broke."
- **Style:** `joyful frontier reel, fast and danceable, group vocal shout-along, oxygen-tank drums, wire chimes, salvaged metal percussion, driving handclaps, foot-stomping, raw and warm, communal, tape warmth, 128 BPM`
- **Lyrics:**
  ```
  [Intro]
  (a whoop, then the drums kick — tin and wire)
  [Verse 1]
  We built the drums from what the dark threw back,
  oxygen tanks and a busted rack!
  Marn plays the pipes off a coolant line,
  and the kid keeps time on a crate of wine!
  [Chorus]
  Salvage yard Saturday, everybody's here,
  we made a whole band out of a wasted year!
  Salvage yard Saturday, bang the tank and shout —
  what the dark threw back, we're gonna dance it out!
  (hey! hey!)
  [Verse 2]
  Six days hauling and the seventh we ring,
  every busted thing's got a note to sing.
  The foreman's stomping and the doc's in a spin,
  and nobody remembers what a chair was for when the reel kicks in!
  [Chorus]
  [Bridge]
  (percussion breakdown, wire chimes, stomps and claps)
  (shouted over the top:)
  One for the week that broke us!
  Two for the hands that mend!
  Three for the yard that woke us —
  and four, we go again!
  [Verse 3]
  When the last light dims and the little ones yawn,
  we'll hang the drums till the week is gone.
  But the yard remembers and the wire stays strung,
  'cause a Freeholds Saturday is never done!
  [Chorus]
  [Chorus]
  (everybody, twice as loud)
  [Outro]
  (final shout, everything hits, cut clean)
  ```
- **Length:** ~3:15 (standard song).

#### DONE_S11. "Wire and Bone"  🎵  *(from R5 Persona)*
- **artist:** Brace & the Tin Reelers · **album:** *Salvage & Song* · **era/year:** Age of the Relays, 2621
- **mood:** driving · **tags:** `frontier-reel, freeholds, age-of-relays, salvage-perc, driving`
- **story_blurb:** "The reel they play at a Freeholds send-off — half work-song, half dare, all made of
  wire and bone and whatever rings when you hit it."
- **Style:** `driving frontier reel, mid-fast, gritty group vocal, wire-string plucking, bone-and-metal percussion, stomping rhythm, defiant and joyful, salvaged sound, raw warmth, 118 BPM`
- **Lyrics:**
  ```
  [Intro]
  (a stomp count-in, wire strings picking up)
  [Verse 1]
  Wire and bone and a good strong back,
  that's all it takes to answer back.
  The dark says no and we say maybe,
  the dark says quit and we play it double-back.
  [Chorus]
  Play it on the wire, play it on the bone,
  a frontier heart is never on its own!
  Play it on the wire, play it loud and long,
  whoever's leaving, they leave with a song!
  [Verse 2]
  Tessa's shipping out on the morning run,
  a year in the black till her contract's done.
  So we play her the reel that her father played,
  so she carries the yard in the noise we made.
  [Chorus]
  [Bridge]
  (drops to stomps and a single wire string)
  The dark is long and the pay is thin,
  and half of what we build, the void takes back again —
  but you can't take a song, you can't dent a reel,
  what we play tonight is ours for real!
  [Verse 3]
  So raise the tin cups, bang the rack,
  sing her out and sing her back.
  A send-off's just a promise turned up loud:
  come home to the yard, come home to the crowd!
  [Chorus]
  [Chorus]
  (all voices, stomping hard)
  [Outro]
  (stomp-and-clap, one last shout, cut clean)
  ```
- **Length:** ~3:15 (standard song).

#### DONE_S12. "The Oxygen Drum"  🎛️  *(from R5 Persona — instrumental)*
- **artist:** Brace & the Tin Reelers · **album:** *Salvage & Song* · **era/year:** Age of the Relays, 2623
- **mood:** bright · **tags:** `frontier-reel, freeholds, age-of-relays, salvage-perc, instrumental, bright`
- **story_blurb:** "Just the rhythm section, cut loose — the sound of a Freeholds workshop finding a
  groove in its own scrap."
- **Style:** `instrumental, no vocals, frontier-reel percussion jam, oxygen-tank drums, wire chimes, salvaged metal, bright plucked wire melody, driving danceable groove, communal energy, raw warmth, 124 BPM`
- **Instrumental:** ON. **Length:** ~3:00 (standard song; let the theme develop through 2–3 variations).

---

### R6 · Sixteen Hands — Drift / relay-collective (betweener, present) — Persona: S13

#### DONE_S13. "Letters We Sent Ahead"  🎵  ★ Persona seed for R6 — ↳ **canon fact 9** (composed by relay, members never met)
- **artist:** Sixteen Hands · **album:** *Across the Dark* · **era/year:** Age of the Relays, 2618
- **mood:** wistful · **tags:** `drift-song, betweener, age-of-relays, synthesist, wistful`
- **story_blurb:** "A collective whose members have never met — each part recorded on a different world
  and stitched together across the relays. You can hear the distance between the voices; that's the point."
- **Style:** `layered drift song, many distant voices stitched together, staggered vocal harmonies with subtle lag, warm analog pads, soft arpeggio, gentle percussion, spacious and aching, sense of great distance, tape warmth, 76 BPM`
- **Lyrics:**
  ```
  [Intro]
  (one voice, then another answers from far away, slightly delayed)
  [Verse 1]
  I recorded my half and I sent it ahead,
  months till you'll hear what I've already said.
  By the time my verse arrives at your sky,
  I'll be older, and so will the reply.
  [Verse 2]
  (a second voice, more distant)
  I got your verse on a winter relay,
  you sang it last spring, it arrived today.
  I'm answering now, though the answer will roam
  a hundred small stations before it gets home.
  [Chorus]
  We're a song that was never once in one room,
  a harmony crossing the dark to you.
  Sixteen hands and no two met —
  and the chord still lands, and it's landing yet.
  [Verse 3]
  (a third voice, brighter, farther)
  My part I sang in a hydroponics bay,
  the tomatoes were listening, that's what I'll say.
  Whoever stitches these letters through —
  leave in the hum, it's my greenhouse for you.
  [Chorus]
  [Bridge]
  (all the voices at once, each slightly out of time)
  Late is not lost, far is not gone,
  a verse in the dark keeps travelling on.
  Late is not lost, slow is not silent —
  we are singing together. It just takes long.
  [Chorus]
  (fuller, the distances resolving)
  [Outro]
  (voices layer from every distance, resolve together)
  ```
- **Length:** ~3:45 (standard song).

#### S14. "Sixteen Skies"  🎛️  *(from R6 Persona — instrumental)*
- **artist:** Sixteen Hands · **album:** *Across the Dark* · **era/year:** Age of the Relays, 2620
- **mood:** contemplative · **tags:** `drift-song, betweener, age-of-relays, synthesist, instrumental, contemplative`
- **story_blurb:** "Sixteen players, sixteen skies, one piece — the instrumental the collective built to
  prove a song could hold together across worlds that will never share an hour."
- **Style:** `instrumental, no vocals, layered drift instrumental, interweaving analog arpeggios from many hands, warm pads, distant bells, staggered entries like signals arriving, spacious and luminous, contemplative, tape warmth, 78 BPM`
- **Instrumental:** ON. **Length:** ~3:20 (standard song; let the theme develop through 2–3 variations).

---

### R7 · The Shellwrights — Localist / far-worlds (outer, present) — Persona: S15

#### S15. "Tideshell Resonance"  🎛️  ★ Persona seed for R7 — ↳ **canon** (Mira: instruments from shells of native fauna)
- **artist:** The Shellwrights · **album:** *Deep Listening, Vol. IV* · **era/year:** Age of the Relays, 2616
- **mood:** serene · **tags:** `localist, outer-station, age-of-relays, instrumental, serene`
- **story_blurb:** "A far-worlds collective who build their instruments from the shells of native fauna —
  listen for the resonance no manufactured instrument makes. A signature of the Localist tradition:
  music grown from its own world."
- **Style:** `instrumental, no vocals, otherworldly localist piece, bright shell-resonance percussion, glassy organic overtones, hollow bowed tones, soft airy pad, gentle water-like textures, serene and strange, alien-warm, spacious, tape warmth, 70 BPM`
- **Instrumental:** ON. **Length:** ~3:15 (standard song; let the theme develop through 2–3 variations).

#### S16. "Fauna Song"  🎵  *(from R7 Persona)*
- **artist:** The Shellwrights · **album:** *Deep Listening, Vol. IV* · **era/year:** Age of the Relays, 2617
- **mood:** tender · **tags:** `localist, outer-station, age-of-relays, tender`
- **story_blurb:** "A lullaby the far-worlds sing to the creatures whose shells become their instruments —
  gratitude and apology in the same breath."
- **Style:** `tender localist art-song, soft breathy vocal, shell-resonance percussion, glassy organic overtones, hollow flute-like tones, gentle and reverent, strange warmth, spacious, tape warmth, 68 BPM`
- **Lyrics:**
  ```
  [Intro]
  (shell-resonance rings once, then breath)
  [Verse 1]
  (soft, reverent, close)
  We took your shell to make a sound,
  we sing it back to you.
  You grew it slow in the tide-dark shallows,
  we only passed it through.
  [Chorus]
  Little life of the far, far worlds,
  your voice outlasts you now.
  Little life of the far, far worlds,
  we keep it sounding, this is how.
  [Verse 2]
  Nothing here is only borrowed,
  nothing taken without a song.
  The luthier bows to the empty water
  before she carries a shell along.
  [Chorus]
  [Bridge]
  (the shells alone, then the voice returns, barely)
  Gratitude and apology
  are the same note on this shore.
  We strike it soft, we strike it slowly,
  and the shell rings on for evermore.
  [Verse 3]
  When our own voices join the tide-dark,
  as every voice out here must do,
  may something small take up our echo
  and sing us onward too.
  [Chorus]
  (dissolving into resonance)
  [Outro]
  (shell-resonance rings out, fades)
  ```
- **Length:** ~3:20 (standard song).

---

### R8 · The First-Ships Choir — Exodus Hymns (First Expansion — classic) — Persona: S17

#### S17. "Departure Hymn"  🎵  ★ Persona seed for R8
- **artist:** The First-Ships Choir · **album:** *The Deep Stacks* · **era/year:** First Expansion, c. 2190 (four centuries old)
- **mood:** solemn · **tags:** `exodus-hymn, earth, first-expansion, purist, solemn`
- **story_blurb:** "An Exodus Hymn from the first ships — solemn, hopeful, carrying the weight of leaving
  and the dream of arrival. Four hundred years old and still sung when a settlement sends someone out."
- **Style:** `solemn exodus hymn, massed choir, hymn-like and hopeful, slow processional, warm pipe-organ pad, restrained strings, ancient and sacred, dignified departure, great tenderness, tape warmth, 62 BPM`
- **Lyrics:**
  ```
  [Intro]
  (organ pad alone, then the choir gathers)
  [Verse 1]
  (massed choir, solemn and warm)
  We leave the cradle, blue and small,
  and set our faces to the dark.
  What we could carry, we have gathered;
  what we could not, we learn to let go.
  [Chorus]
  Carry us, carry us, far and long,
  and let some distant morning find us home.
  Carry us, carry us, all together,
  no ship of ours goes out alone.
  [Verse 2]
  Our children's children will make the landfall,
  their eyes will open under other suns.
  Let them be kind, and let them remember
  the water, the gardens, the ancient songs.
  [Chorus]
  [Bridge]
  (a lone voice over a held chord)
  And if the crossing proves too long,
  and if the dark unthreads our names,
  still we were those who dared the leaving —
  sing that of us, and we are not ashamed.
  [Verse 3]
  So dim the harbour lights behind us,
  and light the long lamps of the hull.
  The night is great, but so is the morning
  we will not see, and love in full.
  [Chorus]
  (full choir, rising)
  [Outro]
  (choir swells, resolves, holds)
  ```
- **Length:** ~3:40 (standard song / hymn).

#### S18. "The Blue Cradle"  🎵  *(from R8 Persona)*
- **artist:** The First-Ships Choir · **album:** *The Deep Stacks* · **era/year:** First Expansion, c. 2205 (classic)
- **mood:** nostalgic · **tags:** `exodus-hymn, earth, first-expansion, nostalgic`
- **story_blurb:** "The hymn every settled child learns about Earth — half record, half founding myth:
  the blue planet, the place humanity first learned to look up and wonder."
- **Style:** `nostalgic exodus hymn, gentle choir with a lead voice, hymn-like, warm organ pad, soft strings, longing and grateful, ancient and tender, sense of a distant home, tape warmth, 64 BPM`
- **Lyrics:**
  ```
  [Intro]
  (soft organ, a lead voice begins alone)
  [Verse 1]
  There was a blue and turning cradle,
  where first we learned to look and wonder.
  Its seas taught patience, its storms taught shelter,
  its nights taught naming the lights up yonder.
  [Chorus]
  We won't go back, but we won't forget you,
  little blue light, our first, our under.
  We carry your water in every harbour,
  little blue light, our first, our wonder.
  [Verse 2]
  (the choir joins, gently)
  The teachers show it in the schoolroom,
  a picture older than the walls:
  that's where the first ships took their leaving —
  and half of the story is true at all.
  [Chorus]
  [Bridge]
  (lead voice, tender)
  Half record and half founding legend,
  and both halves ours, and both halves dear.
  A world doesn't need to be remembered rightly
  to be the reason we are here.
  [Verse 3]
  So when a child asks where we came from,
  point through the roof, past lamp and beam,
  and say: a blue and turning cradle —
  half of it real, and all of it home.
  [Chorus]
  (full choir, warm)
  [Outro]
  (lead voice fades into the choir)
  ```
- **Length:** ~3:30 (standard song / hymn).

---

### R9 · The Outer Revival — Void-revival / Outer Revival movement (core, present) — Persona: S19

#### S19. "Nobody Told the Frontier It Was Over"  🎵  ★ Persona seed for R9 — ↳ **canon fact 11** (Outer Revival)
- **artist:** The Outer Revival · **album:** *Rediscovery* · **era/year:** Age of the Relays, 2624
- **mood:** melancholy · **tags:** `outer-revival, core, age-of-relays, void-ballad, melancholy`
- **story_blurb:** "Core musicians 'discovering' a Void-Ballad style that never stopped evolving on the
  outer stations — polished and beautiful, and a little haunted by the fact that it was never lost, just
  never heard. The Outer Revival in one song."
- **Style:** `polished void-ballad revival, melancholy, refined lead vocal, lush analog pads, felt piano, subtle strings, spacious and cinematic, beautiful and a little haunted, core-studio sheen over frontier soul, tape warmth, 66 BPM`
- **Lyrics:**
  ```
  [Intro]
  (felt piano, a distant pad, unhurried)
  [Verse 1]
  They said they found it, brought it home,
  a sound the far dark kept alive alone.
  Pressed it clean and lit it bright,
  and called it new on opening night.
  [Chorus]
  Nobody told the frontier it was over,
  it was singing all along.
  Nobody told the frontier it was over —
  you can't rediscover an unbroken song.
  [Verse 2]
  Out past the lanes where the ships run thin,
  a keeper hums it to her kin.
  Three hundred years of the same low tune,
  passed hand to hand like a heat in the room.
  [Chorus]
  [Bridge]
  (quieter, almost confessing)
  And we, the polished, the garden-born,
  we mean it kindly, we mean it warm —
  but the credit reads like a borrowed coat:
  it fits, and it isn't ours by note.
  [Verse 3]
  So here's the version with the lights turned low,
  and here's the name of the worlds that made it so.
  If this is revival, let it be true:
  the song never died — we finally came to.
  [Chorus]
  (strings rising underneath)
  [Chorus]
  (softer, letting it go)
  [Outro]
  (strings swell, resolve bittersweet)
  ```
- **Length:** ~3:45 (standard song).

#### S20. "Rediscovery"  🎛️  *(from R9 Persona — instrumental)*
- **artist:** The Outer Revival · **album:** *Rediscovery* · **era/year:** Age of the Relays, 2625
- **mood:** contemplative · **tags:** `outer-revival, core, age-of-relays, instrumental, contemplative`
- **story_blurb:** "The instrumental title piece — the moment the core hears an old outer-station melody
  as if for the first time, and treats a rediscovery as a discovery."
- **Style:** `instrumental, no vocals, cinematic void-ballad revival, felt piano lead, lush warm pads, swelling strings, spacious and reflective, beautiful melancholy, refined, tape warmth, 64 BPM`
- **Instrumental:** ON. **Length:** ~3:15 (standard song; let the theme develop through 2–3 variations).

---

### R10 · "First Generation" — archival Earth-roots (origin — a "found" recording)

#### S21. "Earthlight (First-Generation Recording)"  🎵  *(optional 21st track — drop one above for a round 20)* — ↳ **canon** (Greaves/Archivist deep stacks)
- **artist:** attributed *"First Generation"* (unknown original ship) · **album:** *The Deep Stacks* · **era/year:** pre-diaspora / origin (the oldest thing in the archive)
- **mood:** nostalgic · **tags:** `earth-roots, earth, origin, solo, nostalgic`
- **story_blurb:** "From the deep stacks — Greaves says it's first-generation, off the original ship. A
  single voice and a worn acoustic instrument, older than every world now listening."
- **Style:** `intimate earth-roots folk, single warm voice, worn acoustic guitar, very old recording warmth, soft vinyl crackle and room tone, plain and human, timeless and tender, close-mic, 72 BPM`
- **Lyrics:**
  ```
  [Intro]
  (room tone, a chair creak, the guitar tunes for a moment — an old recording)
  [Verse 1]
  (plain, unadorned)
  I sang this when the world was one,
  before we scattered to the sun.
  I sang it on the front porch step,
  while the ships were built and the promise kept.
  [Chorus]
  Hold the light, hold the light,
  wherever you wake up tonight.
  Hold the light, hold it long,
  and hand it on with a song.
  [Verse 2]
  My daughter's name is on a list,
  a berth, a bunk, a fist-sized case.
  She asked me, will the stars have mornings?
  I said, love, you'll make the place.
  [Chorus]
  [Bridge]
  (half-spoken, smiling audibly)
  They tell me this machine will keep me,
  long past the porch, long past the tree.
  So if you're hearing this out yonder —
  good morning, stranger. You carry me.
  [Verse 3]
  I won't be there when the engines quiet,
  I won't see the other shore.
  But a song's a seed you plant in leaving,
  and it grows what porches are for.
  [Chorus]
  (softer, farther away)
  [Outro]
  (fades into room tone and crackle)
  ```
- **Length:** ~3:20 (standard song). *Add a touch of `vinyl crackle` so it reads as archival — but keep
  the exclude set on (no harsh hiss).*

---

### R11 · The Lane Runners — lane-rock (betweener, present) — Persona: build from S22

#### S22. "Burn Day"  🎵  ★ Persona seed for R11
- **artist:** The Lane Runners · **album:** *Turnover* · **era/year:** Age of the Relays, 2623
- **mood:** driving · **tags:** `lane-rock, betweener, age-of-relays, driving, joyful`
- **story_blurb:** "Hauler rock off the freight lanes — 'burn day' is the day a ship fires the main
  engines for turnover, halfway home. The whole crew's holiday; the Lane Runners made it everyone's."
- **Style:** `warm driving analog rock anthem, energetic drumkit like engine rhythm, jangly bright electric guitars, road-worn male lead vocal, gang backing vocals on the chorus, hopeful and triumphant, big singalong hook, tape warmth, 132 BPM`
- **Lyrics:**
  ```
  [Intro]
  (a four-count on the toms — the engines spinning up)
  [Verse 1]
  Six hundred hours with the throttle cold,
  drifting the lane like a stone that's rolled.
  Chalk on the wall, one mark a day —
  but the chief just grinned and looked my way.
  [Pre-Chorus]
  Strap in, sing out, the captain's on the horn —
  [Chorus]
  It's burn day! Light the long flame!
  Halfway done and homeward again!
  Burn day! Feel the floor shove!
  Every klick behind us is a klick I love!
  [Verse 2]
  Cook broke out the good preserves,
  the kid did cartwheels down the curves.
  Gravity's back like an old friend's hand,
  pressing us home to the harbour stand.
  [Pre-Chorus]
  [Chorus]
  [Bridge]
  (half-time, guitars ringing out)
  They ask why we ride the thousand-hour dark —
  for this. For the shove. For the singing spark.
  For the day the whole hull hums one song,
  and home stops being far and starts being long-gone-not-for-long.
  [Guitar Solo]
  [Chorus]
  (everybody, double length)
  [Outro]
  (drums and a last held chord — the burn settles into cruise)
  ```
- **Length:** ~3:30 (standard song).

#### S23. "The Thousand-Hour Road"  🎵  *(from R11 Persona)*
- **artist:** The Lane Runners · **album:** *Turnover* · **era/year:** Age of the Relays, 2624
- **mood:** warm · **tags:** `lane-rock, betweener, age-of-relays, warm, driving`
- **story_blurb:** "The mid-tempo one — the pride and patience of the people who keep the freight
  moving. Every hauler bar on every dock claims this song was written about their lane."
- **Style:** `warm mid-tempo analog rock, steady driving beat, chiming electric guitars, road-worn male lead, warm harmonies, proud and steady, open-road feeling across deep space, tape warmth, 108 BPM`
- **Lyrics:**
  ```
  [Intro]
  (a lone chiming guitar, then the beat rolls in)
  [Verse 1]
  My father hauled the near-core ring,
  his mother ran the frontier swing.
  The lanes are just a family trade —
  long dark, fair pay, and the friends you've made.
  [Chorus]
  On the thousand-hour road, you learn to hold steady,
  thousand-hour road, you sleep when you're ready,
  and the worlds go 'round, and the freight gets through —
  somebody's gotta carry it, might as well be you.
  [Verse 2]
  I've hauled the seed-grain, hauled the steel,
  hauled a wedding dress and a ferris wheel,
  hauled the mail through a flare-storm shroud —
  every crate a promise, and I keep 'em proud.
  [Chorus]
  [Bridge]
  (quieter, the beat drops to the floor tom)
  It ain't the leaving that makes you a Runner,
  it ain't the engines, it ain't the pay —
  it's knowing a town you'll never live in
  eats tonight 'cause you didn't stay.
  [Chorus]
  (bigger, harmonies stacked)
  [Outro]
  (the guitars chime out down the lane)
  ```
- **Length:** ~3:40 (standard song).

---

### R12 · Auroral Standard — pulse-dance / Synthesist (meridian, present) — Persona: build from S24

#### S24. "Stormglass"  🎵  ★ Persona seed for R12
- **artist:** Auroral Standard · **album:** *Storm Season* · **era/year:** Age of the Relays, 2625
- **mood:** joyful · **tags:** `pulse-dance, meridian, age-of-relays, synthesist, joyful`
- **story_blurb:** "Dance music from Meridian's storm coast, where the season locks everyone indoors —
  so they dance. A 'stormglass' is the window wall you dance in front of while the weather does its
  worst. Pure Synthesist: music that could exist no other way."
- **Style:** `warm euphoric synth-dance, four-on-the-floor, bright analog arpeggios, shimmering pads, clear female lead vocal, joyful and communal, rain-on-glass texture, uplifting build and release, tape warmth, 122 BPM`
- **Lyrics:**
  ```
  [Intro]
  (rain texture, an arpeggio blinking on like house lights)
  [Verse 1]
  Sky's gone sideways, doors sealed tight,
  storm's got the coast for a month of night.
  Mama waxed the floor at four,
  said: we don't hide from weather, we dance indoors.
  [Pre-Chorus]
  Turn the big lamps up, let the windows shake —
  [Chorus]
  Dance at the stormglass, lightning on the bay!
  Let it rattle, let it roar, we're warm and we stay!
  Dance at the stormglass, all the coast alight —
  every house a little star the storm can't put out tonight!
  [Verse 2]
  Grandpa says it's been this way
  since the first domes heard the first waves play:
  you can't out-shout a Meridian squall,
  but a hundred dancing houses barely hear it at all.
  [Pre-Chorus]
  [Chorus]
  [Bridge]
  (the beat thins to a heartbeat pulse, voice close)
  And when the season turns, and the doors swing wide,
  we'll blink at the sun like it's the strange one outside —
  but tonight the storm can sing lead if it likes,
  we've got the harmony.
  [Build]
  (arpeggios stack, rise)
  [Chorus]
  (full, euphoric)
  [Outro]
  (the arpeggio blinks out; rain fades)
  ```
- **Length:** ~3:30 (standard song).

#### S25. "Aurora Season"  🎛️  *(from R12 Persona — instrumental)*
- **artist:** Auroral Standard · **album:** *Storm Season* · **era/year:** Age of the Relays, 2626
- **mood:** bright · **tags:** `pulse-dance, meridian, age-of-relays, synthesist, instrumental, bright`
- **story_blurb:** "The instrumental — the week after the storms, when Meridian's sky pays the coast
  back with auroras. The track every skate-rink on three worlds wore out last season."
- **Style:** `instrumental, no vocals, warm uplifting synth-dance instrumental, four-on-the-floor, cascading analog arpeggios, glittering bells, wide shimmering pads, aurora-like sweeps, joyful momentum, clean build and release, tape warmth, 120 BPM`
- **Instrumental:** ON. **Length:** ~3:15 (standard song; let the theme develop through 2–3 variations).

---

### R13 · The Nightliners — void-lounge (concordance, present) — Persona: build from S26

#### S26. "Two O'Clock, Settlement Time"  🎵  ★ Persona seed for R13
- **artist:** The Nightliners · **album:** *The Late Window* · **era/year:** Age of the Relays, 2615
- **mood:** mellow · **tags:** `void-lounge, concordance, age-of-relays, mellow, nostalgic`
- **story_blurb:** "The deep-hours standard from Concordance's late clubs — named for the hour the
  night really begins. Every settlement bar band covers it; Vell has been known to hum it on air."
- **Style:** `late-night lounge jazz, smoky warm female vocal, brushed drums, upright bass, mellow electric piano, soft vibraphone, intimate small-club feel, tender and wry, unhurried swing, tape warmth, 78 BPM`
- **Lyrics:**
  ```
  [Intro]
  (brushes and bass, a small room, glasses somewhere)
  [Verse 1]
  The last ferry's gone from the garden quay,
  the waiters are stacking the chairs away.
  But the sign's still lit and the band's still kind,
  and nobody's watching the clock but time.
  [Chorus]
  It's two o'clock, settlement time,
  the hour the honest and the hopeless rhyme.
  The worlds are turning, but they turn so slow —
  stay for one more, love. Where would you go?
  [Verse 2]
  The relay hums with the late dispatch,
  some captain's love note, some world's new catch.
  And every lonely light across the dark
  is somebody's kitchen, somebody's heart.
  [Chorus]
  [Bridge]
  (piano solo, then the voice returns, half-smiling)
  They say the night's the same on every world —
  same brave lamps, same tired pearls.
  So here's to the night shift, wherever you are:
  same song, same hour, different star.
  [Chorus]
  (slower, the room leaning in)
  [Outro]
  (the band winds down; the brushes keep going a little longer, then stop)
  ```
- **Length:** ~3:40 (standard song).

---

### R14 · Vela & the Beacons — relay-pop (core, present) — Persona: build from S27

#### S27. "Meet Me on the Thread"  🎵  ★ Persona seed for R14
- **artist:** Vela & the Beacons · **album:** *Signals* · **era/year:** Age of the Relays, 2625
- **mood:** bright · **tags:** `relay-pop, core, age-of-relays, bright, tender`
- **story_blurb:** "The relay-romance hit — two sweethearts on worlds eleven weeks apart who keep
  their date on 'the thread' (the relay network), same hour every week. Half the settled worlds can
  sing the chorus; the other half pretends it can't."
- **Style:** `bright retro harmony pop, doo-wop flavoured group vocals, warm female lead, handclaps, upright bass, chiming guitar, sweet and hooky, tender and playful, sunny retro-futurist warmth, tape warmth, 116 BPM`
- **Lyrics:**
  ```
  [Intro]
  (handclaps and a doo-wop "ooh-ooh" under the lead)
  [Verse 1]
  Eleven weeks by the fastest freight,
  too far to visit, too fond to wait.
  So we made a plan when you shipped away:
  same hour, same channel, every seventh day.
  [Chorus]
  Meet me on the thread tonight (ooh-ooh),
  where the relays hold the light (ooh-ooh),
  I'll be talking to the dark, but the dark talks back —
  your voice comes shining down the track!
  Meet me on the thread!
  [Verse 2]
  Your words arrive from a week ago,
  I love them slow-motion, I love them slow.
  The lag's just the distance doing its part —
  it gives every sentence time to reach my heart.
  [Chorus]
  [Bridge]
  (the Beacons hum, the lead goes soft)
  Someday a ship will close the gap,
  I'll meet you at the dock with the storm-coast map.
  But until the day I hold your hand,
  the thread is the nearest thing to land.
  [Chorus]
  (key change, everybody, handclaps doubled)
  [Outro]
  (the "ooh-ooh" carries off down the relay, fades)
  ```
- **Length:** ~3:20 (standard song).

---

## 6. The music-lore manifest (paste-ready seed source)

Drop this at `config/tracks.yaml` (D7.0's importer reads it → `insert_tracks`; `make seed-tracks`). Fill
`duration_sec` after you trim each file; leave `artist_figure_id` null until D10. Two rows shown — extend
to all 20:

```yaml
# config/tracks.yaml — curated music-lore manifest (human-owned; survives canon refresh; make seed-tracks)
licence_default: "Suno Pro — commercial rights, self-owned; cleared for broadcast (confirm plan terms)."
tracks:
  - id: halden-vre__the-slow-star
    title: "The Slow Star"
    artist: "Halden Vre"
    artist_figure_id: null            # backfilled at D10
    album: "A Window in the Dark"
    era: "age-of-relays"
    in_world_year: 2611
    mood: "melancholy"
    tags: [void-ballad, outer-station, age-of-relays, solo, melancholy]
    story_blurb: "Written on a one-keeper station months from the nearest light — a man singing to the single star that never sets in his window."
    duration_sec: null                # stamp after trim
    audio_path: "assets/music/halden-vre__the-slow-star.mp3"
    licence_note: null                # inherits licence_default

  - id: ysolde-mar__the-long-way-round
    title: "The Long Way Round"
    artist: "Ysolde Mar"
    artist_figure_id: null
    album: "Cargo-Hold Songs"
    era: "age-of-relays"
    in_world_year: 2619
    mood: "mellow"
    tags: [drift-song, betweener, age-of-relays, solo, mellow]
    story_blurb: "A navigator's song, learned in a cargo hold from a woman who plays to stay awake on the crossings — it loops the way a long journey does."
    duration_sec: null
    audio_path: "assets/music/ysolde-mar__the-long-way-round.mp3"
    licence_note: null
```

*(D7.0 decides the exact loader/format — YAML or per-track sidecar. This is the recommended shape; keep
the field names aligned to §3 so the mapping is trivial.)*

---

## 7. Production workflow & checklist

**Per artist (the album method):**
1. Generate the artist's **★ Persona-seed** song (2–4 takes). Pick the best; **Create → Make Persona**,
   name it for the artist (e.g. `Halden Vre`).
2. Generate that artist's remaining songs **from the Persona** — change only Style tempo/mood/instrument
   nuance and the Lyrics. This is what makes them sound like one act.
3. **Trim** each to its radio length; **fade the tail clean**; export WAV master.
4. Name the file `assets/music/<artist-slug>__<title-slug>.mp3`; keep the WAV master.
5. Add the manifest row (§6); stamp `duration_sec` from the final file.

**Per-track sign-off:**
- [ ] On-brand: warm, human, wondrous — **not** dystopian, **not** camp; no real IP named anywhere.
- [ ] Fits its **mood** tag (you'll trust this tag to place the song by daypart/world-mood in D7.4).
- [ ] Era/genre/world **tags** correct (the selector spreads on these — get them honest).
- [ ] Standard song length (3–4 min); clean fade; plays cleanly in the clear (songs aren't ducked).
- [ ] Licence confirmed (Suno Pro plan) and noted.

**Coverage check (so the catalogue has range for the selector):**
- [ ] Every **genre**: void-ballad, drift-song, core-harmony, frontier-reel, exodus-hymn, resonance-pipe,
      localist, outer-revival, earth-roots, **lane-rock, pulse-dance, void-lounge, relay-pop** — ✅ all
      present in §5.
- [ ] **Energy spread**: the catalogue must not all sit at 56–84 BPM — ballads → reels → rock → dance
      (S10–S12, S22–S25, S27 carry the up-tempo end; a mellow-only library makes every daypart sound
      like the night shift).
- [ ] Every **mood band** from mellow/melancholy → joyful/celebratory — for daypart matching (overnight
      mellow, morning bright, festival celebratory).
- [ ] **Era spread**: First Expansion classics, Reconnection, present — ✅ (no all-present catalogue).
- [ ] A few **instrumentals** (S3, S6, S7, S8, S12, S14, S15, S20) — good for under-talk and variety.

**Whole-package sign-off:**
- [ ] The full `JINGLE_PROMPTS.md` §4 file set + 27 songs in `assets/`.
- [ ] `config/tracks.yaml` complete, one row per song, durations stamped.
- [ ] Spot-check three DJ hand-offs by ear: a Music-Bumper (C10) → a mellow S1/S4; the News Sting (C8)
      before headlines; a Frontier Reel (S10) coming out of a bright morning theme (B5).

---

### Sources (Suno 2026 practice)
- [HookGenius — Suno Character Limits 2026 (Prompt, Lyrics & Title caps)](https://hookgenius.app/learn/suno-character-limits/)
- [HookGenius — Suno Custom Mode 2026: Style-of-Music field & limits](https://hookgenius.app/learn/suno-custom-mode-guide/)
- [Suno Help — How long will my song be?](https://help.suno.com/en/articles/2409473)
- [SongSmith — Suno Personas Guide: a consistent voice across songs](https://songsmith.studio/blog/suno-personas-guide)
- [Jack Righteous — Suno Personas: keep the same voice across songs](https://jackrighteous.com/en-us/blogs/guides-using-suno-ai-music-creation/suno-personas-keep-the-same-voice-across-songs)
- [Blake Crosley — Suno v5.5 reference: meta tags & style-of-music](https://blakecrosley.com/guides/suno)
- (Carried from `docs/JINGLE_PROMPTS.md` §1 sources — the jingle-side Suno practice.)

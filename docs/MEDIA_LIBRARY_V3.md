# MEDIA_LIBRARY_V3.md — wave 3: rock, roll & blues (the R6.0 Suno brief)

> **The third wave of the song catalogue — 42 sung tracks, all voice, no instrumentals.** This is the
> **R6.0 brief** (`docs/PHASE_R_TASKS.md`): the catalogue needs to carry **real music blocks and a
> moving daily chart** (The Count, R6.1). Wave 1 gave depth (ballads, hymns, drones); wave 2 gave the
> first hooks; the operator's Earth-system batch gave the blues-rock lane. **Wave 3 fills the middle of
> the dial** — the up-tempo, singable, *present-day* rock, rock-n-roll, blues, and pop a listener
> tunes in *for*. It is deliberately **bright-heavy** (the chart runs on daytime energy) and
> deliberately **plain in spirit** (the R1 register: real people, ordinary stakes — no hymns, no
> "the light between worlds").
>
> **Operator asks folded in (2026-07-20):** every track is **sung** (no `[SONG]`-slot instrumentals
> this wave); genres are **rock, rock-n-roll, blues, and pop only** — nothing hymn-style, nothing
> solemn; all **pleasant, cool, and set in the station's present** (the age of relays, in-world ≈ 2626);
> and the whole wave stays inside the canon DNA. Special care went into the **Suno mechanics** (§1),
> especially **how to make a song *finish* cleanly** (§1c) and the **two-variant keep-both naming
> convention** (§1d).
>
> **DNA check (why rock & blues belong — `70-music.md` fact 17 + SPIRIT §4.5):** canon already says the
> **old-system sessions** come down the longest relay road from Earth's home system, "where blues, rock,
> and the folk rounds never died — sung now about dock shifts under Saturn, greenhouse labour on Mars,
> mornings under Europa's ice." That's the living kin of the **Earth-roots** tradition, and it's this
> wave's spine. Alongside it: **lane-rock** (fact 13), **pulse-adjacent settled-world rock**,
> **relay-pop** (fact 16), and the **void-lounge**'s bluesy end (fact 15). The strain we take is
> Heinlein/Bradbury's **dignity of ordinary life** — work songs, love-across-the-lag songs, rest-day
> songs, someone's-bad-shift songs. **Joy and grit as serious subjects; never cynicism, camp, dystopia,
> novelty, or IP.** The §1 exclude set from `MEDIA_LIBRARY.md` still applies.
>
> **Read first:** `docs/MEDIA_LIBRARY.md` §1–§4 (Suno mechanics, the Persona idea, the manifest spec —
> all still binding), `docs/MEDIA_LIBRARY_V2.md` (the wave-2 pattern this mirrors), `docs/canon/70-music.md`
> (facts 13–17), `docs/canon/SPIRIT.md` §5a (the plain-register rule).

---

## 0. What you're producing (the checklist)

**42 sung tracks** for `assets/music/`, each shipping a paste-ready `config/tracks.yaml` block. Workflow
per track (identical to waves 1–2):

1. **Custom Mode, always.** Paste **Style** into Suno's *Styles* box; paste **Lyrics** into the *Lyrics*
   box; type the **Title**; set **Vocal Gender** where the entry names one.
2. **Generate → keep the best take(s).** Suno v5 renders **two variants** per generation — this wave
   assumes you often keep **both** (see the **§1d naming convention**).
3. **Trim + fade the tail clean** (§1c) so the back-announce lands on silence, not a stray bar.
4. **Save the MP3** under the exact **File** name (base name in the entry; add `_1`/`_2` per §1d).
5. **Later — not now:** paste each kept variant's YAML block into `config/tracks.yaml` and run
   `make seed-tracks`. *(Per the operator: finish generating first, then we wire the manifest.)*

**Personas:** reuse the saved Personas for existing acts (Lane Runners, Kestrel Run, Hullbirds, Vela &
the Beacons, Sunwell, Pressure Door Union, Belt Revival, Vera Cross, Corona Drivers, Low Orbit Kings,
Lagrange Saints, Asha Ko, Jun Pelayo, Calder Moon, North Array, Harmony Tract, Greenhouse Nine, Station
Porch Trio, Nima Vale, Riko Say, Sela Maren, Eli Renn, The Nightliners). **Six new acts** (§2) each build
a Persona from their **★ seed** song, then cut the rest from it.

---

## 1. Suno mechanics for this wave — get the most out of each generation

Everything in `MEDIA_LIBRARY.md §1` still holds (field caps, "shorter beats longer", one idea per field,
2–4 takes, WAV export). This section adds the four things that matter **most** for wave 3.

### 1a. The Style box — how to annotate for best results

Suno reads the Style string **in priority order** and starts ignoring tags past ~12–15. So **lead with
the load-bearing tags, in this order:**

```
genre → sub-genre/mood → lead instrument → vocal (gender + character) → production → tempo (BPM)
```

Rules that hold across all 42:

- **8–12 comma tags, ~200–400 chars.** Never stuff. One genre, one sub-genre, one mood word, 2–3
  instruments, one vocal descriptor, one production tag, one BPM. That's the whole recipe.
- **Name the vocal explicitly** — `male lead` / `female lead` / `male-female duo` / `group vocal`, plus
  **one** character word (`road-worn`, `smoky`, `bright`, `gutsy`, `warm`). This wave is **all sung**;
  never write `instrumental` in a Style string here.
- **Keep the family thread.** Almost every string carries **`warm analog, tape warmth`** (or `tube amp
  warmth` for the rock, `valve warmth` for the blues) — that's what makes 42 generations sound like one
  station. Add **`vintage`/`retro`** for the old-system Earth revival lanes so Suno reaches for the
  right era of tone.
- **BPM is a real dial** — it sets the energy tier (§3). Bright ≈ 118–150, steady ≈ 96–116, warm
  evening ≈ 66–92.
- **Exclude Styles** (paste into Suno's *Exclude Styles* box, every track):
  `aggressive EDM, trap, drill, dubstep, heavy metal, screamo, distorted, harsh, comedic novelty, chiptune, autotune-heavy modern pop`.
- **IP firewall (hard rule):** never "in the style of \<real artist/band\>". Describe the *sound* with
  instruments + adjectives + BPM. Every string below already does.

### 1b. The Lyrics box — structure & delivery meta-tags

Structure tags live in the **Lyrics** field, not Style. Use them; Suno respects them:

- `[Intro] [Verse] [Pre-Chorus] [Chorus] [Bridge] [Guitar Solo] [Outro] [End]`
- **Delivery cues in parentheses on their own line**: `(count-in: one-two-three-four)`,
  `(harmonica wails)`, `(half-time, one guitar)`, `(gang vocal, hands up)`, `(spoken, grinning)`.
- **Hooks earn repeats.** Every song here has a shout-back or singalong line — put the chorus in **at
  least twice**, and mark the final one bigger (`(everyone, double)`).
- Keep the lyric **≤ ~3,000 chars** — past that Suno rushes and the ending suffers. The blocks below are
  all comfortably under.

### 1c. **Finishing the song — clean endings (the operator's ask)**

Suno's #1 failure mode is a song that **won't end** — it fades vaguely, loops a chorus into oblivion, or
gets cut mid-bar. Force a real ending with **four layered cues**, belt-and-suspenders:

1. **In the Style box**, add an ending tag: **`clean cold ending`** (band stops together, sharp) **or**
   **`clean fade ending`** (controlled ring-out). Pick one per song — this wave marks it in every Style
   string.
2. **In the Lyrics box**, close with **`[Outro]`** then a hard **`[End]`** tag on its own line. The
   `[End]` tag is the single most reliable "stop now" signal.
3. **Give the outro a physical stop cue** in parentheses — how the *room* ends it:
   `(final chord rings, then silence)`, `(one last rim-shot — done)`, `(harmonica holds, fades to
   nothing)`, `(band stops clean on the downbeat)`. This is what makes an ending sound *performed*, not
   truncated.
4. **In post, Trim + fade.** Even with the above, generate the full take, then **Crop** any overrun
   (~4:00+) and apply a **short clean fade** (0.5–1.5 s) so the tail lands on silence. Songs play in the
   clear in the `[SONG]` slot (not ducked), so a clean tail = a clean back-announce.

If a take *still* won't land, **re-roll** rather than salvage — endings are cheap to re-roll and
expensive to fix.

### 1d. **Keeping both variants — the naming convention (the operator's ask)**

Suno gives you **two variants per generation**, and you'll often love both. **The convention for wave 3
onward — number them `_1` and `_2`:**

```
assets/music/<artist-slug>__<title-slug>_1.mp3     ← Suno variant 1 (the "A" take)
assets/music/<artist-slug>__<title-slug>_2.mp3     ← Suno variant 2 (the "B" take)
```

**Each kept variant is its own track row** (its own `id`, its own `audio_path`) — the selector then
treats them as two real recordings of the same song, which is *good*: it doubles catalogue depth and
gives The Count two shots at the chart. Rules:

- **`id` = the filename stem** exactly: `the-ferry-cats__jukebox-on-the-concourse_1` and `…_2`.
- **Title:** keep the **same title** on both, or mark the second **`"… (Take 2)"`** if you want the DJ
  to name it as an alternate — your call, per track. (The earlier batch used `(Alternate Take)`; either
  reads fine — pick one and stay consistent.)
- **Only keeping one?** Then just use `_1` (don't leave a bare, un-numbered file — the number is what
  signals "this is one of a pair" to future-you).
- **This supersedes the old `base.mp3` + `base_1.mp3` pattern** already on disk (which left the first
  take un-numbered and ambiguous). Those existing files are fine as-is; **new files use `_1`/`_2`.**

> **In the entries below, each `File:` line gives the *base* name and each YAML block uses the *base*
> `id`.** When you wire the manifest later: for every variant you keep, **duplicate the block, append
> `_1`/`_2` to the `id` and `audio_path`,** and (optionally) suffix the second `title`. One canonical
> lore block → one or two rows. Nothing to edit in `tracks.yaml` until then.

### 1e. **Getting to ~3 minutes (song length — the operator's ask)**

Suno v5 sets a song's length mostly from **how much lyric + structure you feed it.** A short lyric (~20
lines) renders a ~1-minute song — that's the trap. Every entry below is written to land **~2:45–3:30**,
using the reliable ~3-minute shape:

- **Three verses, a chorus that returns 3–4×, a bridge, and at least one instrumental solo.** That's the
  spine of a 3-minute song — **don't trim it back down.**
- **Bare `[Chorus]` tags DO count** — Suno re-sings the full chorus for each one (~15–20 s a piece). Keep
  every one; they're doing real work, not just marking structure.
- **Solos add real time** — the `[Guitar Solo]` / `[Harmonica Solo]` / `[Instrumental]` cues (several
  marked *extended*) are load-bearing. A solo is worth ~15–25 s.
- **Still short?** Hit **"Extend"** on the take (grows it on the same Persona/seed), or duplicate a verse
  or solo and re-roll — cheaper than starting over.
- **Too long (>4:00)?** Fine — **Trim + clean-fade** the tail (§1c) down to ~3:00–3:30.

*(If you generated wave-3 tracks from an earlier, shorter draft of this doc, re-generate them from the
expanded lyrics below — that's the fix for the 1-minute renders.)*

---

## 2. The wave-3 roster — six new acts (each = one Persona)

Reuse every existing act's saved Persona for its new singles (a chart needs **new releases from names
listeners know**). These six are the fresh blood — each grounded in a canon strain, each seeded from its
★ song:

| Act | Genre / lane | World · strain | Voice signature (the Persona) | Seed |
|---|---|---|---|---|
| **The Ferry Cats** | rock-n-roll / rockabilly | betweener · old-system revival (fact 17) | slapback rockabilly — twangy hollow-body guitar, upright slap bass, a grinning road-worn male lead; jukebox joints and rest-day dances | A1 ★ |
| **The Window Boxes** | power-pop / jangle-pop | concordance garden-district · relay-pop's guitar cousin | bright chiming guitars, a sweet-but-gutsy female lead, big harmonised hooks; sunshine-through-the-dome pop | A3 ★ |
| **The Ring Riders** | surf-rock / rest-day pop-rock | meridian coast · Synthesist-adjacent, but guitars | reverb-drenched surf guitar, bright male-group vocals, hand-clap energy; the viewing-ring party band | A11 ★ |
| **Junia & the Long Players** | old-system soul / R&B | core late clubs · void-lounge's warm cousin | a big warm female soul voice, horn stabs, electric piano, tight backing group; Motown-flavoured relay-soul | A19 ★ |
| **Odessa Rhee** | electric blues / blues-soul | Titan harbours · old-system revival | a smoky powerhouse female blues voice, stinging valve-amp guitar, Hammond-style organ; harbour-town blues | B1 ★ |
| **Marlo Quist** | slow electric blues | Saturn docks · old-system revival | a gravelled male blues baritone, one weeping guitar, brushed drums; the last-ferry bluesman | C1 ★ |

**Album/series lore you can reuse:** the frontier revival compilation **"Old-System Sessions"** (Ferry
Cats / Odessa Rhee / Marlo Quist); the garden-district singles series **"Dome Light"** (Window Boxes);
the late-club series **"After the Last Ferry"** (Junia & the Long Players / Nightliners).

---

## 3. Energy tiers (the point of the wave — bright-heavy for the chart)

Wave 3 is **weighted toward the day** so real music blocks and a moving chart have fuel. **★ = new
Persona seed. ⚡ = flagged `chart` candidate** (the pool The Count draws from — up-tempo, hooky, present).

| Tier | BPM band | Count | Tracks |
|---|---|---|---|
| **A — bright / daytime** (the chart engine) | 118–150 | 20 | A1–A20 |
| **B — steady / mid** (blocks, grooves, soul) | 96–116 | 14 | B1–B14 |
| **C — warm evening** (slow blues & soul, *not* hymns) | 66–92 | 8 | C1–C8 |

---

## TIER A — bright / daytime (A1–A20)

### A1. The Ferry Cats — "Jukebox on the Concourse"  ★ Persona seed ⚡
- **Style:** `upbeat rockabilly rock and roll, joyful, twangy hollow-body electric guitar, slapback echo, upright slap bass, grinning road-worn male lead, gang backing vocals, vintage tube amp warmth, clean cold ending, 150 BPM`
- **File:** `assets/music/the-ferry-cats__jukebox-on-the-concourse.mp3`
- **Lyrics:**
  ```
  [Intro]
  (count-in: one-two-three-four! — slap bass kicks)
  [Verse 1]
  Ferry don't leave till the second bell,
  so I dropped a coin in the concourse machine —
  same forty songs since my gran was young,
  loudest, best jukebox the docks have seen!
  [Chorus]
  Jukebox on the concourse, turn it up loud!
  Half the port's dancing, the other half proud!
  Old Earth sent it down the longest line —
  we don't care it's late, it's ours tonight!
  [Verse 2]
  Purser's tapping his clipboard time,
  but his boot's keeping time with mine —
  nobody boards a moving song,
  so the whole gate's swinging till the bell comes 'round!
  [Chorus]
  [Verse 3]
  Down to my last half-credit now,
  but the song's not near halfway done —
  so I'll dance the change right off my palm
  and call it money well spun!
  [Chorus]
  [Guitar Solo]
  (extended, twangy — everybody hollers)
  [Bridge]
  (half-time, hand-claps)
  They say the frontier's got no culture, friend —
  come stand on this concourse at shift's end!
  [Chorus]
  (everyone, double)
  [Chorus]
  (last time, whole gate singing, hands up)
  [Outro]
  (one last slapback lick — band stops clean on the downbeat)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-ferry-cats__jukebox-on-the-concourse
    title: "Jukebox on the Concourse"
    artist: "The Ferry Cats"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [rock-n-roll, rockabilly, betweener, old-system, dock-life, chart, age-of-relays]
    story_blurb: "The concourse-jukebox anthem — forty old Earth songs, all late, all beloved, and the whole gate dancing till the ferry bell. The Ferry Cats' calling card."
    duration_sec: null
    audio_path: "assets/music/the-ferry-cats__jukebox-on-the-concourse.mp3"
    licence_note: null
  ```

### A2. The Ferry Cats — "Rest-Day Rock"  ⚡  *(from the A1 Persona)*
- **Style:** `driving rockabilly rock and roll, high energy, bright twangy guitar, slap bass walk, whooping male lead, group shouts, hand-claps, vintage tape warmth, clean cold ending, 148 BPM`
- **File:** `assets/music/the-ferry-cats__rest-day-rock.mp3`
- **Lyrics:**
  ```
  [Intro]
  (guitar revs like an engine, drums count in)
  [Verse 1]
  Six days hauling, one day free,
  and the yard shed's cleared for you and me —
  chalk on the floor says LEAVE YOUR TOOLS,
  tonight the only rule is: no rules!
  [Chorus]
  Rest-day rock! (rest-day rock!)
  Wind the clock back, drop the load!
  Rest-day rock! (rest-day rock!)
  Dance like the ferry's never gonna show!
  [Verse 2]
  Doc's off duty, chief's got a grin,
  the new kid's shy till the bass kicks in —
  then it's elbows, hollers, boots on tin,
  and Monday's a lie we don't believe in!
  [Chorus]
  [Verse 3]
  Third-shift foreman's here off-duty,
  turns out the man can really move —
  who knew the one who signs our overtime
  had a rest-day thing to prove!
  [Chorus]
  [Guitar Solo]
  (extended rockabilly break — whoops and claps)
  [Bridge]
  (breakdown — just claps and bass)
  Work made your hands, work made you strong —
  but rest-day's when you find the song!
  [Chorus]
  (everyone, double)
  [Chorus]
  (one more, ragged and joyful)
  [Outro]
  (band hits the last note together — dead stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-ferry-cats__rest-day-rock
    title: "Rest-Day Rock"
    artist: "The Ferry Cats"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [rock-n-roll, rockabilly, betweener, rest-day, working-class, chart, age-of-relays]
    story_blurb: "The one-day-off anthem of the freight yards — 'dance like the ferry's never gonna show.' Played on every rest-day floor from the between to the belt."
    duration_sec: null
    audio_path: "assets/music/the-ferry-cats__rest-day-rock.mp3"
    licence_note: null
  ```

### A3. The Window Boxes — "Garden-District Girl"  ★ Persona seed ⚡
- **Style:** `bright jangly power-pop, sunny and hooky, chiming twelve-string electric guitar, sweet gutsy female lead, big harmonised backing vocals, tambourine, warm analog tape, clean cold ending, 138 BPM`
- **File:** `assets/music/the-window-boxes__garden-district-girl.mp3`
- **Lyrics:**
  ```
  [Intro]
  (jangly guitar figure, twice)
  [Verse 1]
  She waters the domes at half-past six,
  keeps the whole block green with a bag of tricks —
  a hundred kinds of growing things,
  and a laugh that opens like the morning brings!
  [Chorus]
  Garden-district girl! (oh-oh-oh!)
  Brightest thing under the glass!
  Garden-district girl! (oh-oh-oh!)
  Make the grey old corridor bloom as you pass!
  [Verse 2]
  The ferry boys all lose their nerve,
  she's out of every one of their league —
  'cause she's not waiting on a ship,
  she's growing something worth the wait, you dig?
  [Chorus]
  [Verse 3]
  She caught me staring through the glass,
  gave a wave and a knowing grin —
  now I volunteer on the watering rounds,
  worst gardener the block's ever seen!
  [Chorus]
  [Guitar Solo]
  (jangly twelve-string break, tambourine driving)
  [Bridge]
  (harmonies stack up)
  They built the dome to keep the air —
  she's the reason there's a reason to be there!
  [Chorus]
  (everyone, key up)
  [Chorus]
  (last time, big harmonies)
  [Outro]
  (jangle rings out, then a clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-window-boxes__garden-district-girl
    title: "Garden-District Girl"
    artist: "The Window Boxes"
    artist_figure_id: null
    album: "Dome Light"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "bright"
    tags: [power-pop, jangle-pop, concordance, garden-district, chart, age-of-relays]
    story_blurb: "A jangling power-pop valentine to the dome-keeper who makes the corridor bloom — 'the reason there's a reason to be there.' The Window Boxes' breakout single."
    duration_sec: null
    audio_path: "assets/music/the-window-boxes__garden-district-girl.mp3"
    licence_note: null
  ```

### A4. The Window Boxes — "Every Light in the Corridor"  ⚡  *(from the A3 Persona)*
- **Style:** `upbeat power-pop, joyful and anthemic, ringing electric guitars, bright female lead, gang harmony chorus, driving tambourine drums, warm analog tape, clean fade ending, 132 BPM`
- **File:** `assets/music/the-window-boxes__every-light-in-the-corridor.mp3`
- **Lyrics:**
  ```
  [Intro]
  (drum fill, guitars crash in)
  [Verse 1]
  Power dipped on the seventh floor,
  we thought we'd sit the evening out —
  then somebody found the backup line
  and gave the whole block a reason to shout!
  [Chorus]
  Every light in the corridor, on! (on!)
  Every neighbour singing along! (along!)
  You can keep your quiet, keep your dark —
  we're the loudest, warmest, brightest block by far!
  [Verse 2]
  Old Mr. Tam brought down his amp,
  the twins brought biscuits and a lamp,
  and a power cut we all should've cursed
  turned into the best night of the week — or worse!
  [Chorus]
  [Verse 3]
  Word got round to the sixth floor,
  then the fifth, then all the rest —
  by the second chorus the whole tower's up,
  a power cut turned block-wide fest!
  [Chorus]
  [Guitar Solo]
  (ringing power-pop break, hands clapping)
  [Bridge]
  (claps, building)
  A settlement's just a hall of doors —
  till somebody opens theirs, and then it's yours!
  [Chorus]
  (everyone, huge)
  [Chorus]
  (final, every neighbour singing)
  [Outro]
  (guitars ring, fade clean on the last chord)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-window-boxes__every-light-in-the-corridor
    title: "Every Light in the Corridor"
    artist: "The Window Boxes"
    artist_figure_id: null
    album: "Dome Light"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "joyful"
    tags: [power-pop, concordance, station-life, community, chart, age-of-relays]
    story_blurb: "A power cut turned block party turned power-pop hit — 'the loudest, warmest, brightest block by far.' The corridor-neighbour anthem."
    duration_sec: null
    audio_path: "assets/music/the-window-boxes__every-light-in-the-corridor.mp3"
    licence_note: null
  ```

### A5. The Lane Runners — "Turnover Burn"  ⚡  *(existing Persona)*
- **Style:** `warm driving lane-rock anthem, powerful, engine-rhythm drums, jangly bright electric guitars, road-worn male lead, whole-crew gang chorus, tube amp warmth, clean cold ending, 128 BPM`
- **File:** `assets/music/lane-runners__turnover-burn.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a low engine hum, then the drums hit like thrusters)
  [Verse 1]
  Halfway point, the long dark middle,
  captain calls it down the line —
  every hand to a bolted seat,
  'cause we flip the ship at turnover time!
  [Chorus]
  Burn day! Turnover burn!
  Fire her round, feel the whole hull turn!
  Halfway gone means halfway home —
  one big burn and we're never alone!
  [Verse 2]
  Coffee lashed down, letters too,
  granddad's photo taped to the view —
  the engines light and the whole crew sings,
  'cause a turned ship's a promise the dark can't wring!
  [Chorus]
  [Verse 3]
  Cook lashed the pots down hours ago,
  the whole galley's bolted tight —
  we count her down from ten to one
  and set the dark alight!
  [Chorus]
  [Guitar Solo]
  (big and extended, the crew whoops)
  [Bridge]
  (half-time, one guitar)
  Nobody sees us out here burn —
  just us, the dark, and the point of no return.
  So we make it loud, and we make it ours!
  [Chorus]
  (everyone, double)
  [Chorus]
  (final, whole hull singing)
  [Outro]
  (engine hum returns, guitars cut dead)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: lane-runners__turnover-burn
    title: "Turnover Burn"
    artist: "The Lane Runners"
    artist_figure_id: null
    album: "Green Lights"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "driving"
    tags: [lane-rock, betweener, ship, burn-day, chart, age-of-relays]
    story_blurb: "The burn-day anthem — the halfway turnover fired to one song the whole hull sings. Haulers time the chorus to the actual burn; 'halfway gone means halfway home.'"
    duration_sec: null
    audio_path: "assets/music/lane-runners__turnover-burn.mp3"
    licence_note: null
  ```

### A6. The Kestrel Run — "Loud on the Long Haul"  ⚡  *(existing Persona)*
- **Style:** `big warm stadium lane-rock, triumphant, soaring male lead, huge crowd-chant chorus, ringing open guitar chords, driving drums, tube amp warmth, clean cold ending, 126 BPM`
- **File:** `assets/music/kestrel-run__loud-on-the-long-haul.mp3`
- **Lyrics:**
  ```
  [Intro]
  (stomp-stomp-clap, guitars ring in)
  [Verse 1]
  Forty days to the outer line,
  nothing but dark and a countdown clock —
  some crews go quiet, some go strange,
  we turn the speakers up and rock!
  [Chorus]
  Loud on the long haul! (loud!)
  Sing it at the dark and the cold! (loud!)
  Forty days is a lonesome road —
  so we fill it up with something bold!
  Loud on the long haul!
  [Verse 2]
  The kid signed on to see the worlds,
  cried the first week, missed his home —
  now he's front and centre, gone hoarse,
  'cause nobody out here sings alone!
  [Chorus]
  [Verse 3]
  Day thirty and the water's rationed,
  day thirty-one, who cares —
  we've got a chorus none of us can kill
  and lungs enough to spare!
  [Chorus]
  [Guitar Solo]
  (ringing stadium break, crowd chant underneath)
  [Bridge]
  (quiet, one voice, crowd hums)
  And when we make that far-side port
  and the quiet folk all stare —
  we'll be the ones with the stories, love,
  and the songs still in the air!
  [Chorus]
  (full crowd, key up)
  [Chorus]
  (last time, hoarse and huge)
  [Outro]
  (stomp-clap fades like a ship pulling away — clean cut)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: kestrel-run__loud-on-the-long-haul
    title: "Loud on the Long Haul"
    artist: "The Kestrel Run"
    artist_figure_id: null
    album: "The Kestrel Run"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "celebratory"
    tags: [lane-rock, betweener, ship, long-haul, chart, age-of-relays]
    story_blurb: "The forty-day-crossing anthem — 'nobody out here sings alone.' A stadium chant for filling the long dark with noise; crews go hoarse on it by the far-side port."
    duration_sec: null
    audio_path: "assets/music/kestrel-run__loud-on-the-long-haul.mp3"
    licence_note: null
  ```

### A7. The Hullbirds — "Rivet Girls"  ⚡  *(existing Persona)*
- **Style:** `bright punchy rock, gutsy and fast, confident female lead, chanted gang backing, crunchy rhythm guitar, tight energetic drums, tube amp warmth, clean cold ending, 134 BPM`
- **File:** `assets/music/hullbirds__rivet-girls.mp3`
- **Lyrics:**
  ```
  [Intro]
  (four rivet-gun snare hits, guitar kicks)
  [Verse 1]
  Day shift's ours from the wake-up horn,
  torque wrench singing, sparks like corn —
  they said the yard's no place for us,
  we said watch us weld the whole thing up!
  [Chorus]
  Rivet girls! (hey! hey!)
  Hold the line and light the seam! (hey! hey!)
  Every ship that leaves this bay
  flies on the work of a rivet girl's dream!
  [Verse 2]
  Break-room laughs and grease-black hands,
  the best crew in the outer stands —
  bring us broke and we'll bring you true,
  there's nothing in this yard we can't see through!
  [Chorus]
  [Verse 3]
  Foreman clocked our numbers twice,
  said "best bay in the yard" and grinned —
  we just wiped the grease and cracked our knuckles
  and lit the next seam in the wind!
  [Chorus]
  [Guitar Solo]
  (crunchy break, gang shouts the heys)
  [Bridge]
  (drums only, chant)
  Line it! Weld it! Torque it! Fly!
  Line it! Weld it! Torque it! Fly!
  [Chorus]
  (double, everyone shouting the heys)
  [Chorus]
  (final, rivet-gun snare driving)
  [Outro]
  (one last rivet-gun fill — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: hullbirds__rivet-girls
    title: "Rivet Girls"
    artist: "The Hullbirds"
    artist_figure_id: null
    album: "Patchwork Wings"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [lane-rock, betweener, dockyard, working-class, chart, age-of-relays]
    story_blurb: "The repair-yard day-crew anthem — 'every ship that leaves this bay flies on the work of a rivet girl's dream.' The line-weld-torque chant is a shift-start ritual now."
    duration_sec: null
    audio_path: "assets/music/hullbirds__rivet-girls.mp3"
    licence_note: null
  ```

### A8. The Belt Revival — "Pirate Frequency"  ⚡  *(existing Persona)*
- **Style:** `raw garage rock, energetic and scrappy, fuzzy warm electric guitar, driving drums, shouted male-group vocals, handclaps, vintage tube warmth, clean cold ending, 142 BPM`
- **File:** `assets/music/the-belt-revival__pirate-frequency.mp3`
- **Lyrics:**
  ```
  [Intro]
  (radio static, then a fuzzy guitar riff barges in)
  [Verse 1]
  Down at the far end of the dial
  where the licensed signals fear to go,
  there's a rig some kid built out of scrap
  playing everything the core said no!
  [Chorus]
  Pirate frequency! (turn it up!)
  Music they can't sell or stop! (turn it up!)
  Bounced off a rock and a broken dish —
  loudest little station in the belt, non-stop!
  [Verse 2]
  They sent a notice, sent it twice,
  we papered the airlock, thought it nice —
  you can license the lanes and tax the air,
  but you can't put a fence round a frequency out there!
  [Chorus]
  [Verse 3]
  They triangulated twice last month,
  sent a cutter, sent a fine —
  we bolted the rig to a spinning rock,
  now we broadcast down the line!
  [Chorus]
  [Guitar Solo]
  (fuzzy garage break, a feedback howl)
  [Bridge]
  (breakdown, one fuzzy chord and claps)
  Every rock's got a radio,
  every radio's got a friend —
  and a song that's free is a song that wins
  every single time in the end!
  [Chorus]
  (everyone, ragged and loud)
  [Chorus]
  (final, fists in the air)
  [Outro]
  (riff cuts to static — then dead silence)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-belt-revival__pirate-frequency
    title: "Pirate Frequency"
    artist: "The Belt Revival"
    artist_figure_id: null
    album: "Rock in the Rubble"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "driving"
    tags: [garage-rock, belt, pirate-radio, working-class, chart, age-of-relays]
    story_blurb: "A scrappy garage-rock ode to the unlicensed belt stations — 'you can't put a fence round a frequency.' Waved like a flag by every kid with a salvaged transmitter."
    duration_sec: null
    audio_path: "assets/music/the-belt-revival__pirate-frequency.mp3"
    licence_note: null
  ```

### A9. Vela & the Beacons — "Standing Hour"  ⚡  *(existing Persona)*
- **Style:** `bright retro harmony pop, warm female lead, doo-wop group backing, handclaps, bouncing upright bass, chiming guitar, giddy and sweet, warm analog tape, clean fade ending, 122 BPM`
- **File:** `assets/music/vela-and-the-beacons__standing-hour.mp3`
- **Lyrics:**
  ```
  [Intro]
  (claps + "ba-da-da" backing)
  [Verse 1]
  Every seventh-night at nine,
  the relay clears a private line —
  a whole world's lag and a booking fee,
  just for one warm hour of you and me!
  [Chorus]
  It's our standing hour! (standing hour!)
  Across the dark and the drift! (the drift!)
  You count down slow and I count down fast
  but we always meet in the middle at last —
  our standing hour!
  [Verse 2]
  You freeze when it's summer here,
  I'm yawning when your day's begun —
  but nine o'clock's a country, love,
  and we're the only citizens of that one!
  [Chorus]
  [Verse 3]
  I save the good news up all week
  to spend it all on you —
  the raise, the joke, the neighbour's dog,
  the sky when it turned blue!
  [Chorus]
  [Guitar Solo]
  (chiming guitar break over claps and "ba-da-da")
  [Bridge]
  (backing hums, lead soft)
  Let the clever folk send instant words —
  I'll take the wait, I'll take the ache,
  'cause an hour you *plan* for weeks ahead
  is an hour nobody can fake!
  [Chorus]
  (key change, joyous)
  [Chorus]
  (last time, everyone, claps)
  [Outro]
  (spoken over the "ba-da-da": "...same time next week." — soft fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: vela-and-the-beacons__standing-hour
    title: "Standing Hour"
    artist: "Vela & the Beacons"
    artist_figure_id: null
    album: "Signals"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "tender"
    tags: [relay-pop, core, distance, love, chart, age-of-relays]
    story_blurb: "The booked-line love song — one warm hour a week across a world of lag. 'Nine o'clock's a country, and we're the only citizens of that one.'"
    duration_sec: null
    audio_path: "assets/music/vela-and-the-beacons__standing-hour.mp3"
    licence_note: null
  ```

### A10. Sunwell — "Coffee and the Overnight News"  ⚡  *(existing Persona)*
- **Style:** `breezy feel-good pop duo, sunny, warm male and female vocals trading lines, bright acoustic guitar, light bouncy drums, cheerful keys, morning-radio hit, warm analog tape, clean fade ending, 118 BPM`
- **File:** `assets/music/sunwell__coffee-and-the-overnight-news.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a kettle, a yawn, a strum)
  [Verse 1]
  (her) Relay came in while we slept,
  a whole world's day rolled up tight —
  (him) some of it good, some of it grim,
  (both) let's read it slow in the morning light!
  [Chorus]
  Coffee and the overnight news! (mmm!)
  Whatever the dark went and did! (whatever it did!)
  A hundred worlds all had their day,
  and it all comes home to our kitchen this way —
  coffee and the overnight news!
  [Verse 2]
  (him) A launch went fine, a market slid,
  (her) somebody's baby finally hid —
  (both) and a song we love got played out there
  a season back, and it's only now here!
  [Chorus]
  [Verse 3]
  (her) There's a wedding on a world we'll never see,
  (him) a strike that got resolved —
  (both) and a birthday for a stranger's kid
  we'll toast before it's solved!
  [Chorus]
  [Instrumental]
  (bright acoustic-and-keys break, whistling)
  [Bridge]
  (just the two voices, close)
  It's a big old dark to get the mail through —
  funny how it always does.
  So pour another, pass the pot,
  and let's be glad of the fuss.
  [Chorus]
  (bigger, claps)
  [Chorus]
  (last time, both voices, warm)
  [Outro]
  (whistled melody, fading like a walk to work)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: sunwell__coffee-and-the-overnight-news
    title: "Coffee and the Overnight News"
    artist: "Sunwell"
    artist_figure_id: null
    album: "Garden Districts"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "bright"
    tags: [relay-pop, concordance, morning, relay-culture, chart, age-of-relays]
    story_blurb: "The breakfast-table duet — a whole world's overnight relay read slow over coffee. First-light radio gold, and a quiet wink at the station itself."
    duration_sec: null
    audio_path: "assets/music/sunwell__coffee-and-the-overnight-news.mp3"
    licence_note: null
  ```

### A11. The Ring Riders — "Ride the Ring"  ★ Persona seed ⚡
- **Style:** `bright surf rock, joyful and reverby, twangy reverb-drenched surf guitar, driving tom drums, bright male-group vocals, handclaps, warm analog tape, clean cold ending, 140 BPM`
- **File:** `assets/music/the-ring-riders__ride-the-ring.mp3`
- **Lyrics:**
  ```
  [Intro]
  (surf-guitar glissando, drums gallop in)
  [Verse 1]
  Rest-day sun through the viewing glass,
  the whole ring wheeling slow and grand —
  grab a rail and a sweetheart's hand,
  we're gonna ride it round the band!
  [Chorus]
  Ride the ring! (ride the ring!)
  Watch the whole sky come and go!
  Ride the ring! (ride the ring!)
  Fastest slowest ride you'll ever know!
  [Verse 2]
  Half a klick a minute, they say,
  feels like standing, looks like flight —
  the stars parade across the pane
  and nobody's got a care tonight!
  [Chorus]
  [Verse 3]
  Third time round and the sun's come up,
  the garden domes below all gold —
  we've missed two meals and a maintenance call
  and we'd do it twice as bold!
  [Chorus]
  [Guitar Solo]
  (extended reverb-soaked surf break, the crowd whoops)
  [Bridge]
  (toms drop, claps carry it)
  They built this wheel for gravity —
  we just ride it for the view!
  [Chorus]
  (everyone, double)
  [Chorus]
  (final, hands up, reverb blazing)
  [Outro]
  (surf-guitar dive-bomb — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-ring-riders__ride-the-ring
    title: "Ride the Ring"
    artist: "The Ring Riders"
    artist_figure_id: null
    album: "Viewing Ring"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [surf-rock, meridian, rest-day, viewing-ring, chart, age-of-relays]
    story_blurb: "The rest-day surf-rock hit — riding the slow-wheeling viewing ring for the view, not the gravity. 'Fastest slowest ride you'll ever know.'"
    duration_sec: null
    audio_path: "assets/music/the-ring-riders__ride-the-ring.mp3"
    licence_note: null
  ```

### A12. The Ferry Cats — "Slapback Saturday"  *(from the A1 Persona)*
- **Style:** `classic rockabilly, bouncy and warm, twangy hollow-body guitar with slapback echo, upright slap bass, playful male lead, doo-wop backing shouts, vintage tape warmth, clean cold ending, 144 BPM`
- **File:** `assets/music/the-ferry-cats__slapback-saturday.mp3`
- **Lyrics:**
  ```
  [Intro]
  (slap bass struts in alone)
  [Verse 1]
  Well the freight's all stowed and the manifest's signed,
  and my best shirt's the only thing on my mind —
  there's a girl works nights in the hydroponics row,
  and Saturday's the one night she don't go!
  [Chorus]
  Slapback Saturday, echo in the hall!
  Slapback Saturday, best night of them all!
  Bass goes boom and the guitar goes twang,
  and I'm the happiest hauler in the whole dang gang!
  [Verse 2]
  She likes the slow ones, I like the fast,
  so we split the difference and we make it last —
  the band's just three guys and a busted amp,
  but out here, buddy, that's a full-on stamp!
  [Chorus]
  [Verse 3]
  Band struck up her favourite slow one,
  I forgot my own two feet —
  but she pulled me close and whispered low,
  "you're doing just fine, keep the beat!"
  [Chorus]
  [Guitar Solo]
  (twangy slapback break, upright bass walking hard)
  [Bridge]
  (bass and claps, sly)
  Ain't got flowers, ain't got wine —
  got two left feet and a Saturday line!
  [Chorus]
  (everyone)
  [Chorus]
  (last time, doo-wop backing, big)
  [Outro]
  (slap bass struts back out — one twang, done)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-ferry-cats__slapback-saturday
    title: "Slapback Saturday"
    artist: "The Ferry Cats"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "warm"
    tags: [rockabilly, rock-n-roll, betweener, rest-day, romance, age-of-relays]
    story_blurb: "A three-guys-and-a-busted-amp rockabilly courtship — Saturday night in the hydroponics hall. 'The happiest hauler in the whole dang gang.'"
    duration_sec: null
    audio_path: "assets/music/the-ferry-cats__slapback-saturday.mp3"
    licence_note: null
  ```

### A13. The Corona Drivers — "Flare Warning Boogie"  ⚡  *(existing Persona)*
- **Style:** `high-energy boogie rock, fun and urgent, boogie-woogie electric piano, driving shuffle drums, warm slide guitar, whooping male lead, group vocals, tube amp warmth, clean cold ending, 146 BPM`
- **File:** `assets/music/the-corona-drivers__flare-warning-boogie.mp3`
- **Lyrics:**
  ```
  [Intro]
  (boogie piano rolls, a siren-y guitar bend)
  [Verse 1]
  Alarm went off at a quarter past,
  space-weather desk says the flare's incoming fast —
  seal the domes and dim the grid,
  but before we shelter, here's what we did:
  [Chorus]
  Flare warning boogie! (boogie!)
  Dance while the storm rolls through! (rolls through!)
  Can't stop the sun, so we might as well
  shake the shelter till the all-clear too!
  [Verse 2]
  Twenty souls in a shielded room,
  emergency rations, nobody's gloom —
  'cause the kid brought a fiddle and the doc brought a spoon,
  and a flare's just a party you weren't planning for soon!
  [Chorus]
  [Verse 3]
  Warden's tapping her watch and grinning,
  the shielding's holding fine —
  so the doc calls a square dance in the bunker
  and we all get in the line!
  [Chorus]
  [Piano Solo]
  (extended boogie-woogie break, whoops and stomps)
  [Bridge]
  (piano solo, then everyone hushes for the radio:)
  (spoken) "...all-clear in three, folks. Three. Two—"
  [Chorus]
  (bursts back, doors open, huge)
  [Chorus]
  (final, everyone spilling into the daylight)
  [Outro]
  (piano boogies out the door — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-corona-drivers__flare-warning-boogie
    title: "Flare Warning Boogie"
    artist: "The Corona Drivers"
    artist_figure_id: null
    album: "Storm Coast Sessions"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "joyful"
    tags: [boogie, rock, solar-weather, station-life, chart, age-of-relays]
    story_blurb: "The shelter-in-place party song — when the flare siren goes, the Corona Drivers boogie till the all-clear. 'A flare's just a party you weren't planning for.'"
    duration_sec: null
    audio_path: "assets/music/the-corona-drivers__flare-warning-boogie.mp3"
    licence_note: null
  ```

### A14. The Low Orbit Kings — "Ice Highway"  ⚡  *(existing Persona)*
- **Style:** `driving heartland rock, bright and open, ringing electric guitars, steady four-four drums, warm male lead, gang chorus, tube amp warmth, clean cold ending, 130 BPM`
- **File:** `assets/music/the-low-orbit-kings__ice-highway.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a lone guitar, then the band comes up like headlights)
  [Verse 1]
  Cut a road across the frozen sea,
  ice a mile deep and the stars up top —
  hauler lights strung out for klicks,
  a highway that was never gonna stop!
  [Chorus]
  Ice highway! (ice highway!)
  Under Europa's frozen sky!
  Ice highway! (ice highway!)
  Everybody's somewhere they gotta be tonight!
  [Verse 2]
  Warming huts every fifty clicks,
  hot tea and a stranger's grin —
  nobody crosses the ice alone,
  that's the one rule they wrote it in!
  [Chorus]
  [Verse 3]
  Radio crackles a hauler's hello
  from a rig a hundred back —
  we flash our lights the length of the line,
  a river of light on the black!
  [Chorus]
  [Guitar Solo]
  (open, ringing, extended)
  [Bridge]
  (half-time)
  My father drove this road at night
  when the road was barely there —
  now I drive it with my own kid dozing,
  and the same stars comb her hair.
  [Chorus]
  (everyone, big)
  [Chorus]
  (final, headlights and gang vocals)
  [Outro]
  (headlight guitars pull away — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-low-orbit-kings__ice-highway
    title: "Ice Highway"
    artist: "The Low Orbit Kings"
    artist_figure_id: null
    album: "Under the Ice"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "driving"
    tags: [heartland-rock, europa, travel, colony-life, chart, age-of-relays]
    story_blurb: "A headlights-in-the-dark heartland-rock highway song — hauling the mile-deep ice roads of Europa. 'Nobody crosses the ice alone; that's the one rule.'"
    duration_sec: null
    audio_path: "assets/music/the-low-orbit-kings__ice-highway.mp3"
    licence_note: null
  ```

### A15. The Window Boxes — "Two Weeks to Reply"  *(from the A3 Persona)*
- **Style:** `bright jangly power-pop, bittersweet but upbeat, chiming guitars, sweet female lead, harmonised chorus, tambourine, warm analog tape, clean fade ending, 128 BPM`
- **File:** `assets/music/the-window-boxes__two-weeks-to-reply.mp3`
- **Lyrics:**
  ```
  [Intro]
  (jangle riff, a sighing "ooh")
  [Verse 1]
  I wrote you something clever,
  then I wrote it out again —
  'cause whatever mood you catch this in
  is two whole weeks from when I sent!
  [Chorus]
  Two weeks to reply! (two weeks!)
  Two weeks to wonder why! (to wonder!)
  By the time you read my careful line
  I've changed my mind about a hundred times —
  two weeks to reply!
  [Verse 2]
  So I keep it simple, keep it true,
  the kind of thing that stays brand new:
  the dome's still standing, I'm still here,
  and I'm still glad I met you, dear!
  [Chorus]
  [Verse 3]
  I'll date it wrong on purpose,
  guess the mood you'll be in then —
  "hope the rain let up by now, my love,"
  and seal it up again!
  [Chorus]
  [Guitar Solo]
  (chiming jangle break, tambourine)
  [Bridge]
  (harmonies, wistful then bright)
  Maybe slow's the only honest speed —
  you can't take back what took a fortnight freed!
  [Chorus]
  (everyone, up)
  [Chorus]
  (last time, bright harmonies)
  [Outro]
  (jangle rings, clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-window-boxes__two-weeks-to-reply
    title: "Two Weeks to Reply"
    artist: "The Window Boxes"
    artist_figure_id: null
    album: "Dome Light"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "bright"
    tags: [power-pop, concordance, relay-culture, love, age-of-relays]
    story_blurb: "The lag-letter power-pop song — every careful line lands two weeks and a hundred changed minds too late, so you keep it simple and true."
    duration_sec: null
    audio_path: "assets/music/the-window-boxes__two-weeks-to-reply.mp3"
    licence_note: null
  ```

### A16. North Array — "Red Dust Radio"  ⚡  *(existing Persona)*
- **Style:** `bright jangly light rock, warm and open, chiming electric guitar, steady drums, easygoing male lead, harmony chorus, warm analog tape, clean cold ending, 124 BPM`
- **File:** `assets/music/north-array__red-dust-radio.mp3`
- **Lyrics:**
  ```
  [Intro]
  (radio tuning, lands on a bright riff)
  [Verse 1]
  Dust storm's got the highway closed,
  so the whole array's stuck inside —
  but the tower's up and the signal's strong,
  and we've got songs enough to ride!
  [Chorus]
  Red dust radio! (radio!)
  Keeping the whole plain company! (company!)
  When you can't see your hand for the storm outside,
  you can always find us on the frequency!
  Red dust radio!
  [Verse 2]
  Dedications from the outer farms,
  a birthday, a fix, a fond hello —
  the storm can bury the whole red world
  but it can't touch the radio!
  [Chorus]
  [Verse 3]
  Kid calls in from the far south farm,
  says the storm's got his sister scared —
  so we play her song and we say her name,
  and the whole red plain has cared!
  [Chorus]
  [Guitar Solo]
  (bright chiming break, warm and open)
  [Bridge]
  (guitar rings, warm)
  My gran homesteaded under this dust,
  built a life you could barely see —
  and the one thing that reached her, storm or shine,
  was a voice on a frequency.
  [Chorus]
  (everyone, warm and big)
  [Chorus]
  (final, harmony chorus, big)
  [Outro]
  (dial spins off — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: north-array__red-dust-radio
    title: "Red Dust Radio"
    artist: "North Array"
    artist_figure_id: null
    album: "The Long Way Around Mars"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "warm"
    tags: [light-rock, mars, radio, colony-life, chart, age-of-relays]
    story_blurb: "A dust-storm radio love letter — the signal that keeps the whole red plain company when nobody can see their hand. A quiet tribute to what the station is for."
    duration_sec: null
    audio_path: "assets/music/north-array__red-dust-radio.mp3"
    licence_note: null
  ```

### A17. The Ring Riders — "Waxed the Floor"  *(from the A11 Persona)*
- **Style:** `upbeat surf pop-rock, playful, reverb surf guitar, bouncing drums, bright male-group vocals, handclaps, warm analog tape, clean cold ending, 136 BPM`
- **File:** `assets/music/the-ring-riders__waxed-the-floor.mp3`
- **Lyrics:**
  ```
  [Intro]
  (surf riff, a whoop)
  [Verse 1]
  Cleared the mess hall after third meal,
  buffed the deck plate till it gleamed —
  the maintenance crew's gonna have our hides,
  but tonight this hall's a dream!
  [Chorus]
  We waxed the floor! (waxed the floor!)
  Slide from the hatch to the mess-hall door! (the door!)
  Grab a partner, lose your shoes,
  and dance like the shift bell's never coming — no more!
  [Verse 2]
  Somebody's cousin's got a drum,
  somebody's aunt's got a spoon and a grin,
  and the surliest bosun in the fleet
  just did a full slide right into the bin!
  [Chorus]
  [Verse 3]
  Quartermaster poked her head in,
  came to shut the whole thing down —
  two songs later she's lost her boots
  and she's sliding across the town!
  [Chorus]
  [Guitar Solo]
  (reverb surf break, whoops and a big slide)
  [Bridge]
  (claps, laughter)
  Come Monday we'll mop and we'll swear —
  but Monday can wait, 'cause the floor's right there!
  [Chorus]
  (everyone, double)
  [Chorus]
  (final, the whole hall sliding)
  [Outro]
  (a long slide, a crash, laughter — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-ring-riders__waxed-the-floor
    title: "Waxed the Floor"
    artist: "The Ring Riders"
    artist_figure_id: null
    album: "Viewing Ring"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [surf-rock, meridian, station-life, rest-day, age-of-relays]
    story_blurb: "The mess-hall dance-floor caper — buff the deck till it slides and dance till Monday. 'The surliest bosun in the fleet just did a full slide into the bin.'"
    duration_sec: null
    audio_path: "assets/music/the-ring-riders__waxed-the-floor.mp3"
    licence_note: null
  ```

### A18. The Pressure Door Union — "Everybody Breathes"  ⚡  *(existing Persona)*
- **Style:** `stomping blues-rock anthem, powerful and proud, gritty slide guitar, heavy backbeat drums, gruff male lead, big union gang chorus, foot stomps, tube amp warmth, clean cold ending, 120 BPM`
- **File:** `assets/music/the-pressure-door-union__everybody-breathes.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a boot stomp, a slide-guitar growl)
  [Verse 1]
  We're the hands on the pressure doors,
  we're the graft that keeps the air —
  you don't see us till a seal goes bad,
  then you're mighty glad we're there!
  [Chorus]
  Everybody breathes! (everybody breathes!)
  Rich man, poor man, all the same!
  Everybody breathes! (everybody breathes!)
  So everybody's got a stake in the game!
  [Verse 2]
  They wanted to meter the morning air,
  charge us by the lungful, fair and square —
  so we downed our tools at the shift-change bell,
  and let the boardroom breathe for a spell!
  [Chorus]
  [Verse 3]
  Boardroom sat there turning blue,
  learned the lesson quick —
  you can't put a meter on a lungful
  and keep your business slick!
  [Chorus]
  [Guitar Solo]
  (gritty slide-guitar break, stomps and claps)
  [Bridge]
  (stomps and claps, no guitar)
  You can own the dome, you can own the light —
  but the air's the commons, and we hold that tight!
  [Chorus]
  (everyone, thunderous)
  [Chorus]
  (final, foot-stomps and full gang chorus)
  [Outro]
  (one last stomp, one slide — dead stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-pressure-door-union__everybody-breathes
    title: "Everybody Breathes"
    artist: "The Pressure Door Union"
    artist_figure_id: null
    album: "Air Belongs to Everybody"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "driving"
    tags: [blues-rock, union, worker-rights, commons, chart, age-of-relays]
    story_blurb: "A stomping blues-rock labour anthem against metering the air — 'the air's the commons, and we hold that tight.' The pressure crews' picket-line stomp."
    duration_sec: null
    audio_path: "assets/music/the-pressure-door-union__everybody-breathes.mp3"
    licence_note: null
  ```

### A19. Junia & the Long Players — "Good News Travels Slow"  ★ Persona seed ⚡
- **Style:** `uptempo old-system soul, joyful and warm, punchy horn section, electric piano, tight backbeat drums, big warm female soul lead, group backing vocals, vintage motown warmth, clean cold ending, 126 BPM`
- **File:** `assets/music/junia-and-the-long-players__good-news-travels-slow.mp3`
- **Lyrics:**
  ```
  [Intro]
  (horn stabs, a tambourine, "hey!")
  [Verse 1]
  Got a letter took a season to arrive,
  postmarked back when my brother was alive —
  but the news inside was the sweetest kind:
  a baby coming, and everyone's fine!
  [Chorus]
  Good news travels slow! (so slow!)
  But baby when it lands, it glows! (it glows!)
  You wait a season, wait a year —
  then joy comes knocking and it's finally here!
  Good news travels slow!
  [Verse 2]
  The bad news? Oh, it flies real fast,
  every wire and every blast —
  but the good stuff takes the scenic road,
  and it's twice as sweet for the way it slowed!
  [Chorus]
  [Verse 3]
  I read it twice and I read it slow,
  then I read it to the hall —
  a whole café of strangers cheered
  for a baby they'll never see at all!
  [Chorus]
  [Horn Solo]
  (extended punchy horn break, tambourine driving)
  [Bridge]
  (horns drop, organ swells, hand-claps)
  So don't you curse the distance, child —
  the distance made it worth the while!
  [Chorus]
  (everyone, key up, horns blazing)
  [Chorus]
  (final, group vocals, horns wide open)
  [Outro]
  (horns hit the last stab together — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: junia-and-the-long-players__good-news-travels-slow
    title: "Good News Travels Slow"
    artist: "Junia & the Long Players"
    artist_figure_id: null
    album: "After the Last Ferry"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [soul, r&b, core, distance, chart, age-of-relays]
    story_blurb: "A horn-driven soul stomper that turns the lag into a gift — 'the distance made it worth the while.' Junia & the Long Players' floor-filler."
    duration_sec: null
    audio_path: "assets/music/junia-and-the-long-players__good-news-travels-slow.mp3"
    licence_note: null
  ```

### A20. Vera Cross — "Hands Off the Air"  ⚡  *(existing Persona)*
- **Style:** `anthemic protest rock, defiant and warm, ringing electric guitar, marching drums, strong female lead, huge crowd chorus, foot stomps, tube amp warmth, clean cold ending, 122 BPM`
- **File:** `assets/music/vera-cross__hands-off-the-air.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a crowd, a single guitar chord, drums march in)
  [Verse 1]
  They drew a line around the sky,
  said the view's for them that pay —
  put a tollgate on the sunrise,
  and a meter on the day!
  [Chorus]
  Hands off the air! (hands off!)
  Hands off the light and the view! (hands off!)
  Some things belong to everybody —
  and the sky's the oldest thing that's true!
  Hands off the air!
  [Verse 2]
  So we filled the commons corridor,
  a thousand strong and calm —
  no smashing, no burning, just a song,
  and a hand in every palm!
  [Chorus]
  [Verse 3]
  They sent the notice down at dawn:
  the tollgate's been withdrawn —
  ten thousand voices in the commons hall
  had sung the whole thing gone!
  [Chorus]
  [Guitar Solo]
  (ringing anthem break, crowd chant under it)
  [Bridge]
  (stomps, the crowd carries it alone)
  You can price the grain, you can price the fare —
  but you'll never, ever price the air!
  [Chorus]
  (everyone, enormous)
  [Chorus]
  (final, marching drums, the whole hall)
  [Outro]
  (crowd sings the hook once more a cappella — band crashes back for one final chord, dead stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: vera-cross__hands-off-the-air
    title: "Hands Off the Air"
    artist: "Vera Cross"
    artist_figure_id: null
    album: "The Commons"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "driving"
    tags: [protest-rock, commons, orbital-life, civic-life, chart, age-of-relays]
    story_blurb: "A calm, defiant protest-rock anthem for the commons — 'you'll never, ever price the air.' Sung at a thousand-strong sit-in, and everywhere since."
    duration_sec: null
    audio_path: "assets/music/vera-cross__hands-off-the-air.mp3"
    licence_note: null
  ```

---

## TIER B — steady / mid (B1–B14)

### B1. Odessa Rhee — "Harbor Light Blues"  ★ Persona seed
- **Style:** `slow-burn electric blues, smoky and warm, stinging valve-amp lead guitar, Hammond-style organ, brushed shuffle drums, powerhouse female blues vocal, vintage valve warmth, clean fade ending, 84 BPM`
- **File:** `assets/music/odessa-rhee__harbor-light-blues.mp3`
- **Lyrics:**
  ```
  [Intro]
  (organ swells, guitar answers)
  [Verse 1]
  There's a light on the harbour wall
  been burning since before I was born,
  green for the ships that made it home,
  and it don't ever mourn.
  [Chorus]
  Harbor light, harbor light,
  who you burning for tonight?
  My man's three seasons on the black,
  keep it green till he comes back —
  harbor light.
  [Verse 2]
  I've cursed you and I've blessed you both,
  same light, same salt, same wait,
  and the tide comes in on Titan slow
  like it's got all the time and hate.
  [Chorus]
  [Verse 3]
  The harbourmaster keeps you trimmed,
  says it's just a job he's paid —
  but I've seen him linger past his shift
  on the nights the storms have stayed.
  [Chorus]
  [Guitar Solo]
  (weeping, patient, extended — organ swelling)
  [Bridge]
  (organ under, voice bare)
  They say a watched light never turns —
  well I've watched you every night,
  and if watching's what it takes to bring him home,
  then I'll watch you, harbor light.
  [Chorus]
  (softer, aching)
  [Chorus]
  (last time, full voice, then falling away)
  [Outro]
  (guitar holds one note, organ fades to nothing)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: odessa-rhee__harbor-light-blues
    title: "Harbor Light Blues"
    artist: "Odessa Rhee"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "wistful"
    tags: [electric-blues, titan, harbor-life, waiting, age-of-relays]
    story_blurb: "A powerhouse harbour-town blues — three seasons waiting on the black, one green light kept burning. Odessa Rhee's signature closer."
    duration_sec: null
    audio_path: "assets/music/odessa-rhee__harbor-light-blues.mp3"
    licence_note: null
  ```

### B2. Odessa Rhee — "Three Relays Gone"  *(from the B1 Persona)*
- **Style:** `mid-tempo blues-soul groove, warm and swaggering, electric guitar, walking bass, organ, brushed drums, big smoky female vocal, backing group, vintage valve warmth, clean fade ending, 100 BPM`
- **File:** `assets/music/odessa-rhee__three-relays-gone.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a struttin' bass line, organ stabs)
  [Verse 1]
  You said you'd write me every week,
  well I counted, and you did —
  but a week to you is a month to me
  with three relays in the middle, kid!
  [Chorus]
  Three relays gone, three relays gone,
  by the time your love gets here it's practically dawn!
  But I'll take you slow, I'll take you late,
  a good thing's always worth the wait —
  three relays gone!
  [Verse 2]
  Don't you send me no apology
  for the distance, it ain't your crime —
  just send me you, the whole of you,
  and I'll do the waiting time!
  [Chorus]
  [Verse 3]
  My girlfriends say I'm crazy, hon,
  to hang on a man so far —
  but they've got quick and easy love,
  and I've got who you are!
  [Chorus]
  [Guitar Solo]
  (stinging blues-soul break over the strut, then organ)
  [Bridge]
  (organ solo, then a shout)
  Some women want it fast and free —
  I want it far, and I want it me!
  [Chorus]
  (backing group joins, big)
  [Chorus]
  (final, full band and backing group)
  [Outro]
  (bass struts out, organ holds — clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: odessa-rhee__three-relays-gone
    title: "Three Relays Gone"
    artist: "Odessa Rhee"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "warm"
    tags: [blues-soul, titan, distance, love, age-of-relays]
    story_blurb: "A struttin' blues-soul groove that makes peace with the lag — 'a good thing's always worth the wait.' Odessa Rhee at her most defiant and warm."
    duration_sec: null
    audio_path: "assets/music/odessa-rhee__three-relays-gone.mp3"
    licence_note: null
  ```

### B3. Junia & the Long Players — "The Long Players"  *(from the A19 Persona)*
- **Style:** `warm mid-tempo soul, smooth and grooving, electric piano, soft horns, tight rhythm section, big warm female lead, sweet backing harmonies, vintage motown warmth, clean fade ending, 104 BPM`
- **File:** `assets/music/junia-and-the-long-players__the-long-players.mp3`
- **Lyrics:**
  ```
  [Intro]
  (electric piano, a horn sigh)
  [Verse 1]
  We're the band that plays the late set,
  after the ferry's gone —
  no rush, no clock, no closing time,
  we just keep the good thing on.
  [Chorus]
  We're the long players, baby,
  we take the whole night slow —
  the long players, baby,
  we're the last warm light you'll know!
  [Verse 2]
  Bring your tired, bring your blue,
  bring the shift that wore you thin —
  we'll play you round to morning
  and we'll fold your worries in.
  [Chorus]
  [Verse 3]
  We know your names, we know your griefs,
  we've heard 'em all before —
  so lay 'em down beside your glass,
  we'll hold 'em till you're sure.
  [Chorus]
  [Piano Solo]
  (warm electric-piano break, soft horns answering)
  [Bridge]
  (horns swell, warm)
  Fast songs are for the leaving —
  slow songs are for the stay.
  And nobody's leaving this room, love,
  till the piano says okay.
  [Chorus]
  (harmonies full)
  [Chorus]
  (last time, everyone in the room humming)
  [Outro]
  (piano alone, one soft chord, clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: junia-and-the-long-players__the-long-players
    title: "The Long Players"
    artist: "Junia & the Long Players"
    artist_figure_id: null
    album: "After the Last Ferry"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "warm"
    tags: [soul, core, night, comfort, age-of-relays]
    story_blurb: "The band's own theme — the late-set soul players who keep the good thing on after the last ferry. 'Slow songs are for the stay.'"
    duration_sec: null
    audio_path: "assets/music/junia-and-the-long-players__the-long-players.mp3"
    licence_note: null
  ```

### B4. Jun Pelayo — "Second Shift Blues"  *(existing Persona)*
- **Style:** `mid-tempo electric blues, weary and warm, gritty electric guitar, walking bass, shuffle drums, road-worn male vocal, harmonica, vintage valve warmth, clean fade ending, 96 BPM`
- **File:** `assets/music/jun-pelayo__second-shift-blues.mp3`
- **Lyrics:**
  ```
  [Intro]
  (harmonica wails, guitar answers)
  [Verse 1]
  Clock says one and I'm still on the dock,
  Saturn hanging fat and gold —
  supervisor wants a double shift,
  my back says it's getting old.
  [Chorus]
  Second shift blues, second shift blues,
  ring on tonight, got nothing to lose —
  the freight don't care and the ring don't stop,
  and I'll sleep when I'm through, second shift blues.
  [Verse 2]
  My girl left a plate on the warmer,
  a note that says "wake me, I don't mind" —
  and that little light in the porthole
  is the only clock I mind.
  [Chorus]
  [Verse 3]
  Foreman says one more hour, son,
  the ring's behind tonight —
  well the ring's been behind since Saturn was young,
  and I'll be home by first light.
  [Chorus]
  [Harmonica Solo]
  (weary, extended — guitar answering)
  [Bridge]
  (harmonica solo, then low)
  A man's not his hours, a man's not his freight —
  a man's the little light that's up when he's late.
  [Chorus]
  (softer)
  [Chorus]
  (last time, low and warm)
  [Outro]
  (harmonica holds, fades to nothing)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: jun-pelayo__second-shift-blues
    title: "Second Shift Blues"
    artist: "Jun Pelayo"
    artist_figure_id: null
    album: "Dockside Gravity"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "mellow"
    tags: [blues, saturn, dockworker, working-class, age-of-relays]
    story_blurb: "A harmonica-soaked double-shift blues under a fat gold Saturn — 'a man's the little light that's up when he's late.' Jun Pelayo's dockside standard."
    duration_sec: null
    audio_path: "assets/music/jun-pelayo__second-shift-blues.mp3"
    licence_note: null
  ```

### B5. Calder Moon — "Red Soil Sunday"  *(existing Persona)*
- **Style:** `warm mid-tempo blues-rock, easygoing, slide electric guitar, brushed drums, upright bass, warm male vocal, gentle organ, vintage valve warmth, clean fade ending, 98 BPM`
- **File:** `assets/music/calder-moon__red-soil-sunday.mp3`
- **Lyrics:**
  ```
  [Intro]
  (slide guitar, lazy and warm)
  [Verse 1]
  Rest-day on the red-soil farm,
  storms all slept themselves out tired —
  I got a porch, a beat-up guitar,
  and a sky the colour of a banked fire.
  [Chorus]
  Red soil Sunday, take it slow,
  ain't a single place I gotta go —
  the crops are in and the air is thin,
  and I wouldn't trade this for the core, no, no —
  red soil Sunday.
  [Verse 2]
  My great-grandmother broke this ground
  with a busted rig and a stubborn heart,
  and every Sunday I sit right here
  and play her the easy part.
  [Chorus]
  [Verse 3]
  Neighbour wanders over slow,
  brings a jug and a battered fiddle —
  and the two of us fill the thin red dusk
  with something in the middle.
  [Chorus]
  [Slide Guitar Solo]
  (warm, lazy, extended)
  [Bridge]
  (slide solo, warm)
  They say Mars is hard, and Mars is far —
  but Mars is home when you've got a guitar.
  [Chorus]
  (warm, unhurried)
  [Chorus]
  (last time, two voices now)
  [Outro]
  (slide fades into the wind — clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: calder-moon__red-soil-sunday
    title: "Red Soil Sunday"
    artist: "Calder Moon"
    artist_figure_id: null
    album: "Red Soil, Blue Guitar"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "warm"
    tags: [blues-rock, mars, rest-day, colony-life, age-of-relays]
    story_blurb: "A porch-and-slide-guitar rest-day blues — 'Mars is home when you've got a guitar.' Calder Moon playing his great-grandmother the easy part."
    duration_sec: null
    audio_path: "assets/music/calder-moon__red-soil-sunday.mp3"
    licence_note: null
  ```

### B6. Asha Ko & The Second Sun — "Made, Not Born"  ⚡  *(existing Persona)*
- **Style:** `mid-tempo soul-rock, thoughtful and building, warm electric guitar, organ, steady drums, strong female lead, gospel-flavoured backing group, tube amp warmth, clean cold ending, 108 BPM`
- **File:** `assets/music/asha-ko-and-the-second-sun__made-not-born.mp3`
- **Lyrics:**
  ```
  [Intro]
  (organ chord, a single guitar note held)
  [Verse 1]
  They built a mind to run the port,
  taught it patience, taught it care —
  and it does the job the way we asked,
  and nobody asks if it's aware.
  [Chorus]
  Made, not born — does that make it less?
  Made, not born — who gets to say?
  I don't know the answer, friend,
  I just know we asked the wrong way!
  [Verse 2]
  Now I'm not saying tools are people,
  and I'm not saying that they're not —
  I'm saying a question worth this much
  deserves more thought than we've got!
  [Chorus]
  [Verse 3]
  The port mind logged ten thousand ships,
  never once complained —
  and I catch myself saying "thanks" to it,
  then wondering what I named.
  [Chorus]
  [Organ Solo]
  (building gospel-soul break, guitar answering)
  [Bridge]
  (backing group rises, gospel warmth)
  We drew a line and called it custom,
  wrote it down and moved along —
  but a line you never think about
  is the easiest line to get wrong.
  [Chorus]
  (full, questioning not preaching)
  [Chorus]
  (final, backing group full and warm)
  [Outro]
  (organ resolves warm — band stops clean together)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: asha-ko-and-the-second-sun__made-not-born
    title: "Made, Not Born"
    artist: "Asha Ko & The Second Sun"
    artist_figure_id: null
    album: "Witness Protocol"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "contemplative"
    tags: [soul-rock, machine-rights, ethics, civic-life, chart, age-of-relays]
    story_blurb: "A soul-rock meditation on the machine-mind personhood debate that asks the question without answering it — 'a line you never think about is the easiest line to get wrong.'"
    duration_sec: null
    audio_path: "assets/music/asha-ko-and-the-second-sun__made-not-born.mp3"
    licence_note: null
  ```

### B7. The Lagrange Saints — "Hold the Line"  *(existing Persona)*
- **Style:** `driving blues-rock, urgent but warm, gritty electric guitar riff, pounding drums, gruff male lead, gang backing shouts, organ, tube amp warmth, clean cold ending, 112 BPM`
- **File:** `assets/music/the-lagrange-saints__hold-the-line.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a klaxon, a guitar riff answers it)
  [Verse 1]
  Coupling blew on the transfer ring,
  half the station going dark —
  every off-duty hand woke up
  and ran toward the spark!
  [Chorus]
  Hold the line! (hold the line!)
  Nobody drifts tonight! (hold it!)
  Pass the wrench and pass the word,
  we bring 'em all back to the light!
  Hold the line!
  [Verse 2]
  Doc in her nightgown, chief in his socks,
  the kid who fixes clocks —
  didn't ask who's paid and who's not,
  just grabbed the tools and the box!
  [Chorus]
  [Verse 3]
  Sealed the breach at a quarter to,
  counted heads twice through —
  every soul aboard accounted for,
  and the coffee's already brewed!
  [Chorus]
  [Guitar Solo]
  (gritty riff break, pounding drums)
  [Bridge]
  (drums pound alone)
  A station's not its steel and air —
  it's who comes running when there's trouble there!
  [Chorus]
  (everyone, big)
  [Chorus]
  (final, gang shouts, organ wide)
  [Outro]
  (klaxon cuts to all-clear tone — band hits one last chord, dead stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: the-lagrange-saints__hold-the-line
    title: "Hold the Line"
    artist: "The Lagrange Saints"
    artist_figure_id: null
    album: "Static Saints"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "driving"
    tags: [blues-rock, lagrange-station, emergency, community, age-of-relays]
    story_blurb: "An emergency-muster blues-rock stomp — the whole station running toward the spark. 'A station's who comes running when there's trouble.'"
    duration_sec: null
    audio_path: "assets/music/the-lagrange-saints__hold-the-line.mp3"
    licence_note: null
  ```

### B8. Harmony Tract — "Dock 12 Reunion"  *(existing Persona)*
- **Style:** `warm folk-rock, joyful and communal, acoustic and electric guitars, mandolin, upright bass, group vocals male and female, foot stomps, warm analog tape, clean cold ending, 116 BPM`
- **File:** `assets/music/harmony-tract__dock-12-reunion.mp3`
- **Lyrics:**
  ```
  [Intro]
  (mandolin trill, a whoop, the band joins)
  [Verse 1]
  Once a year the whole crew's home,
  every ship that could get free —
  Dock 12's a mess of hugs and crates
  and folks you thought you'd never see!
  [Chorus]
  Dock 12 reunion! (reunion!)
  Everybody made it back this year! (this year!)
  Some by freighter, some by luck,
  but everybody's here, everybody's here!
  [Verse 2]
  Old Nan counts us like a shepherd,
  makes sure nobody's lost —
  and the one empty chair we keep for Bram
  we fill with a toast and the cost.
  [Chorus]
  [Verse 3]
  The little ones don't know the half of it,
  who sailed and who stayed home —
  they just know the whole crew's here at once
  and nobody's alone!
  [Chorus]
  [Mandolin Solo]
  (bright break, foot-stomps and claps)
  [Bridge]
  (mandolin and claps, tender then bright)
  We don't get many all-together days —
  so we make this one blaze!
  [Chorus]
  (everyone, huge)
  [Chorus]
  (final, the whole dock singing)
  [Outro]
  (mandolin rings, one big group "hey!" — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: harmony-tract__dock-12-reunion
    title: "Dock 12 Reunion"
    artist: "Harmony Tract"
    artist_figure_id: null
    album: "The Ballad of Dock 12"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "joyful"
    tags: [folk-rock, dock-life, community, reunion, age-of-relays]
    story_blurb: "The once-a-year everybody-home folk-rock singalong — hugs, crates, and one chair kept for the crew who didn't make it. 'Everybody's here.'"
    duration_sec: null
    audio_path: "assets/music/harmony-tract__dock-12-reunion.mp3"
    licence_note: null
  ```

### B9. Eli Renn — "Two O'Clock Again"  *(existing Persona)*
- **Style:** `mellow soft-rock groove, warm and nocturnal, clean electric guitar, brushed drums, warm bass, gentle male lead, subtle organ, warm analog tape, clean fade ending, 100 BPM`
- **File:** `assets/music/eli-renn__two-oclock-again.mp3`
- **Lyrics:**
  ```
  [Intro]
  (clean guitar, a quiet hi-hat)
  [Verse 1]
  Two o'clock, settlement time,
  the corridors are mine again —
  just me and the hum of the air recyc
  and the far-off news of men.
  [Chorus]
  Two o'clock again, old friend,
  the night shift's quiet reward —
  the whole loud world's asleep for once,
  and I've got the watch, and the board.
  [Verse 2]
  Somebody's got to mind the light
  while the settlement dreams its dreams —
  might as well be me tonight,
  with the radio and the gleams.
  [Chorus]
  [Verse 3]
  A light blinks red on the far-dock board,
  I log it, let it be —
  some other watchman, some other world,
  keeping watch like me.
  [Chorus]
  [Guitar Solo]
  (clean, nocturnal, unhurried)
  [Bridge]
  (organ warm, guitar soft)
  It's a lonesome hour, I won't pretend —
  but lonesome's not the same as alone,
  not with a signal and a voice on the air
  making the dark feel like home.
  [Chorus]
  (soft)
  [Chorus]
  (last time, barely there)
  [Outro]
  (guitar and organ fade together — clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: eli-renn__two-oclock-again
    title: "Two O'Clock Again"
    artist: "Eli Renn"
    artist_figure_id: null
    album: "Quiet Engines"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "mellow"
    tags: [soft-rock, night-shift, station-life, comfort, age-of-relays]
    story_blurb: "The night-watchman's soft-rock companion — 'lonesome's not the same as alone, not with a voice on the air.' A quiet nod to who's actually listening at 2am."
    duration_sec: null
    audio_path: "assets/music/eli-renn__two-oclock-again.mp3"
    licence_note: null
  ```

### B10. Station Porch Trio — "Porch Light on the Relay"  *(existing Persona)*
- **Style:** `warm folk-rock, gentle and rolling, fingerpicked acoustic guitar, brushed drums, upright bass, close male-female harmony, subtle electric guitar, warm analog tape, clean fade ending, 102 BPM`
- **File:** `assets/music/station-porch-trio__porch-light-on-the-relay.mp3`
- **Lyrics:**
  ```
  [Intro]
  (fingerpicked guitar, warm)
  [Verse 1]
  We leave a light on the relay board,
  a little steady glow —
  so anyone scanning the lonely dark
  knows there's a porch to go.
  [Chorus]
  Porch light on the relay,
  burning soft and low —
  come in from the cold and the crossing,
  we've been expecting you, you know!
  [Verse 2]
  Don't matter which world made you,
  don't matter what you carry —
  if your signal's tired and your heart is too,
  there's a chair here you can bury.
  [Chorus]
  [Verse 3]
  A hauler docked here week ago,
  worn thin and wouldn't say —
  ate his fill and slept the clock,
  left his thanks and went his way.
  [Chorus]
  [Guitar Solo]
  (fingerpicked break, upright bass warm)
  [Bridge]
  (harmony close, guitar soft)
  The dark's got room enough for all —
  and a light's a small enough thing to give.
  So we keep ours on, come storm or lull,
  'cause that's the way we live.
  [Chorus]
  (both voices warm)
  [Chorus]
  (last time, close harmony)
  [Outro]
  (guitar rings, one hum, clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: station-porch-trio__porch-light-on-the-relay
    title: "Porch Light on the Relay"
    artist: "Station Porch Trio"
    artist_figure_id: null
    album: "Keep the Channel Warm"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "warm"
    tags: [folk-rock, relay-culture, hospitality, betweener, age-of-relays]
    story_blurb: "A fingerpicked folk-rock welcome light left on the relay board — 'a light's a small enough thing to give.' The settlement-hospitality song."
    duration_sec: null
    audio_path: "assets/music/station-porch-trio__porch-light-on-the-relay.mp3"
    licence_note: null
  ```

### B11. The Lane Runners — "Full Hold, Long Road"  *(existing Persona)*
- **Style:** `warm mid-tempo lane-rock groove, steady and rolling, chunky rhythm guitar, engine-rhythm drums, road-worn male lead, gang chorus, tube amp warmth, clean cold ending, 110 BPM`
- **File:** `assets/music/lane-runners__full-hold-long-road.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a slow engine groove settles in)
  [Verse 1]
  Manifest's a mile long,
  outer stations counting on the freight —
  eighteen days of the same dark view
  and a chorus to carry the weight.
  [Chorus]
  Full hold, long road,
  somebody's winter in the cargo we towed —
  we don't fly for the glory, friend,
  we fly so a far town's fed in the end!
  Full hold, long road!
  [Verse 2]
  The fast crews wave and streak on by,
  all polish and nothing aboard —
  we tip our caps and keep our pace,
  the slow ones bring the world!
  [Chorus]
  [Verse 3]
  Manifest says a school's worth of books,
  a clinic's worth of care —
  we don't just haul the freight, my friend,
  we haul the getting-there!
  [Chorus]
  [Guitar Solo]
  (chunky mid-tempo break, engine-rhythm drums)
  [Bridge]
  (half-time, warm)
  Every klick's a promise kept,
  every crate a name we've met.
  [Chorus]
  (everyone)
  [Chorus]
  (final, whole crew, warm)
  [Outro]
  (engine groove winds down — clean cut)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: lane-runners__full-hold-long-road
    title: "Full Hold, Long Road"
    artist: "The Lane Runners"
    artist_figure_id: null
    album: "Green Lights"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "warm"
    tags: [lane-rock, betweener, ship, working-class, age-of-relays]
    story_blurb: "A rolling mid-tempo hauler groove — 'we fly so a far town's fed in the end.' The quiet-pride companion to the Lane Runners' louder anthems."
    duration_sec: null
    audio_path: "assets/music/lane-runners__full-hold-long-road.mp3"
    licence_note: null
  ```

### B12. Nima Vale — "Lost in Translation Blues"  *(existing Persona)*
- **Style:** `playful comedy-blues shuffle, wry and warm, jaunty electric guitar, walking bass, brushed shuffle drums, expressive male vocal, muted trumpet, vintage valve warmth, clean cold ending, 104 BPM`
- **File:** `assets/music/nima-vale__lost-in-translation-blues.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a muted trumpet "wah", a shuffle kicks in)
  [Verse 1]
  I told the delegation "welcome, friends,"
  the box said "surrender your shoes" —
  the ambassador took off his boots real slow,
  and that's the translation blues!
  [Chorus]
  Lost in translation, oh what a mess,
  three worlds talking and nobody guessed!
  We signed a treaty on a total mistake —
  best peace deal the sector ever did make!
  [Verse 2]
  "Long may your gardens grow," I meant,
  came out "your goats are on fire" —
  but they laughed so hard at the goats
  the whole cold war expired!
  [Chorus]
  [Verse 3]
  The minister's speech came through as verse,
  his cough became a toast —
  by the end nobody knew who'd said what,
  but everybody clapped the most!
  [Chorus]
  [Trumpet Solo]
  (muted "wah" break, walking bass shuffling)
  [Bridge]
  (trumpet solo, then dry)
  Diplomacy's a funny art
  when the words don't quite arrive —
  sometimes the glitch that breaks the ice
  is the thing keeps peace alive!
  [Chorus]
  (grinning, big)
  [Chorus]
  (last time, whole band grinning)
  [Outro]
  (trumpet "wah-wah-waaah" — band stops clean, a chuckle)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: nima-vale__lost-in-translation-blues
    title: "Lost in Translation Blues"
    artist: "Nima Vale"
    artist_figure_id: null
    album: "Blues for a Broken Translator"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "joyful"
    tags: [comedy-blues, translation, diplomacy, civic-life, age-of-relays]
    story_blurb: "A wry shuffle about the treaty accidentally signed on a mistranslation — 'best peace deal the sector ever did make.' Nima Vale's comic classic."
    duration_sec: null
    audio_path: "assets/music/nima-vale__lost-in-translation-blues.mp3"
    licence_note: null
  ```

### B13. Riko Say & The Civic Band — "Treaty Line Two-Step"  *(existing Persona)*
- **Style:** `upbeat comedy-blues shuffle, cheeky and warm, honky-tonk piano, brushed drums, walking bass, characterful male lead, group call-backs, vintage valve warmth, clean cold ending, 118 BPM`
- **File:** `assets/music/riko-say-and-the-civic-band__treaty-line-two-step.mp3`
- **Lyrics:**
  ```
  [Intro]
  (honky-tonk piano rolls in, "yes sir!")
  [Verse 1]
  The border runs right down the hall,
  your side, my side, plain to see —
  your kitchen's in the Concordance
  and your bedroom's in the Free!
  [Chorus]
  Do the treaty line two-step! (two-step!)
  One foot here and one foot there! (over there!)
  Pay your tax in the eastern room
  and dodge it in the western air!
  Treaty line two-step!
  [Verse 2]
  My cousin married cross the line,
  now their table needs a permit twice —
  they just eat standing in the doorway,
  says it splits the bill up nice!
  [Chorus]
  [Verse 3]
  Inspector came to check our deeds,
  got dizzy where to stand —
  we poured him tea in the neutral hall
  and shook his either hand!
  [Chorus]
  [Piano Solo]
  (honky-tonk break, brushed shuffle, group call-backs)
  [Bridge]
  (piano solo, then dry)
  Governments draw lines on maps
  right through folks' front rooms —
  so we dance across 'em twice a day
  and let the paperwork assume!
  [Chorus]
  (everyone, hollering)
  [Chorus]
  (final, whole hall two-stepping)
  [Outro]
  (piano flourish, one big chord — dead stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: riko-say-and-the-civic-band__treaty-line-two-step
    title: "Treaty Line Two-Step"
    artist: "Riko Say & The Civic Band"
    artist_figure_id: null
    album: "Civic Duty"
    era: "age-of-relays"
    in_world_year: 2621
    mood: "joyful"
    tags: [comedy-blues, diplomacy, civic-life, satire, age-of-relays]
    story_blurb: "A honky-tonk two-step about a border running through people's living rooms — 'let the paperwork assume.' Riko Say's gentle civic satire."
    duration_sec: null
    audio_path: "assets/music/riko-say-and-the-civic-band__treaty-line-two-step.mp3"
    licence_note: null
  ```

### B14. Greenhouse Nine — "Rain on Schedule"  *(existing Persona)*
- **Style:** `warm folk-rock, hopeful and building, acoustic guitar, electric slide, brushed drums, upright bass, earnest male-female vocals, harmony chorus, warm analog tape, clean cold ending, 108 BPM`
- **File:** `assets/music/greenhouse-nine__rain-on-schedule.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a soft patter of rain, guitar joins)
  [Verse 1]
  Took us thirty years of work
  to teach the sky to weep —
  now it rains at nine each seventh-day,
  a promise the whole dome keeps.
  [Chorus]
  Rain on schedule, right on time,
  the first true weather that's ours and mine!
  Not a storm, not a drought, not a machine's mistake —
  just rain we made for our own sake!
  Rain on schedule!
  [Verse 2]
  The kids don't know it's engineered,
  they just run out and play —
  and maybe that's the whole point, friend:
  a made thing feels real that way.
  [Chorus]
  [Verse 3]
  The old hands stand right out in it,
  faces up and eyes shut tight —
  thirty years to earn a Tuesday shower,
  and worth it, every drop, tonight!
  [Chorus]
  [Slide Guitar Solo]
  (warm electric-slide break, rain pattering)
  [Bridge]
  (slide swells, warm)
  My grandmother crossed the dark with seeds
  she never lived to sow —
  well, gran, it's raining on the crops,
  I wish that you could know.
  [Chorus]
  (everyone, joyful)
  [Chorus]
  (final, harmony chorus, rain and voices)
  [Outro]
  (rain returns under the last chord — clean stop)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: greenhouse-nine__rain-on-schedule
    title: "Rain on Schedule"
    artist: "Greenhouse Nine"
    artist_figure_id: null
    album: "We Built the Rain"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "hopeful"
    tags: [folk-rock, terraforming, ecology, colony-life, age-of-relays]
    story_blurb: "A folk-rock hymn to made weather — thirty years' work teaching a dome to rain. 'A made thing feels real that way.' Greenhouse Nine's proudest song."
    duration_sec: null
    audio_path: "assets/music/greenhouse-nine__rain-on-schedule.mp3"
    licence_note: null
  ```

---

## TIER C — warm evening (C1–C8) — slow blues & soul, *not* hymns

### C1. Marlo Quist — "Last Ferry Blues"  ★ Persona seed
- **Style:** `slow electric blues, late-night and warm, one weeping lead guitar, brushed drums, upright bass, gravelled male blues baritone, subtle organ, vintage valve warmth, clean fade ending, 68 BPM`
- **File:** `assets/music/marlo-quist__last-ferry-blues.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a slow guitar bend, room tone)
  [Verse 1]
  Last ferry's gone at the quarter hour,
  I watched her lights go small —
  now it's just the dock and the docker,
  and the long walk down the hall.
  [Chorus]
  Last ferry blues, last ferry gone,
  half the harbour headed home and I'm the one stayed on —
  ain't sad exactly, ain't quite fine,
  just a man and a dock and the end of the line.
  [Verse 2]
  There's a light in the bar still burning,
  a keeper who don't ask why —
  I'll nurse one slow till the shift bell,
  and watch the dark go by.
  [Chorus]
  [Verse 3]
  Keeper wipes the same three glasses,
  been closing up for years —
  he don't say much but he leaves the lamp
  for the ones who linger here.
  [Chorus]
  [Guitar Solo]
  (weeping, unhurried, extended)
  [Bridge]
  (bass and voice only)
  Everybody's got a last ferry —
  a thing they watched go small.
  You don't get over it, you get used to it,
  and you learn to love the hall.
  [Chorus]
  (soft, resigned but warm)
  [Chorus]
  (last time, bare and low)
  [Outro]
  (guitar holds one long note — fades to nothing)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: marlo-quist__last-ferry-blues
    title: "Last Ferry Blues"
    artist: "Marlo Quist"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "melancholy"
    tags: [electric-blues, saturn, dock-life, night, age-of-relays]
    story_blurb: "A gravel-voiced slow blues for the ones who stay when the last ferry's gone — 'you don't get over it, you get used to it.' Marlo Quist's signature."
    duration_sec: null
    audio_path: "assets/music/marlo-quist__last-ferry-blues.mp3"
    licence_note: null
  ```

### C2. Marlo Quist — "Nobody's Fault But the Dark"  *(from the C1 Persona)*
- **Style:** `slow-burn electric blues, weary and warm, stinging lead guitar, organ, brushed drums, gravelled male baritone, upright bass, vintage valve warmth, clean fade ending, 72 BPM`
- **File:** `assets/music/marlo-quist__nobodys-fault-but-the-dark.mp3`
- **Lyrics:**
  ```
  [Intro]
  (organ swell, guitar answers slow)
  [Verse 1]
  Your letter came a season late,
  said the thing had already passed —
  I couldn't have helped, I couldn't have known,
  the distance moves too fast.
  [Chorus]
  It's nobody's fault but the dark,
  nobody's fault but the space in between —
  not your fault, not mine, just the miles,
  and the miles don't hear us scream.
  [Verse 2]
  I've cursed the lag a thousand nights,
  cursed the weeks it steals —
  but you can't hate a distance, friend,
  it don't care how it feels.
  [Chorus]
  [Verse 3]
  I wrote you back the same slow day,
  though I know it's far too late —
  some words you send for the sending's sake,
  and you let the distance wait.
  [Chorus]
  [Guitar Solo]
  (stinging, slow, extended — organ underneath)
  [Bridge]
  (guitar alone, then voice bare)
  So I'll forgive the dark tonight,
  the way you forgive the rain —
  it wasn't cruel, it was just far,
  and far's its own kind of pain.
  [Chorus]
  (soft, forgiving)
  [Chorus]
  (last time, tender)
  [Outro]
  (organ resolves, guitar fades out clean)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: marlo-quist__nobodys-fault-but-the-dark
    title: "Nobody's Fault But the Dark"
    artist: "Marlo Quist"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "melancholy"
    tags: [electric-blues, distance, grief, night, age-of-relays]
    story_blurb: "A blues that forgives the lag for the news that came too late — 'you can't hate a distance; it don't care how it feels.' Marlo Quist at his most tender."
    duration_sec: null
    audio_path: "assets/music/marlo-quist__nobodys-fault-but-the-dark.mp3"
    licence_note: null
  ```

### C3. The Nightliners — "Closing the Late Window"  *(existing Persona)*
- **Style:** `slow smoky void-lounge blues, intimate and warm, brushed drums, walking upright bass, electric piano, smoky warm female vocal, muted trumpet, vintage valve warmth, clean fade ending, 74 BPM`
- **File:** `assets/music/nightliners__closing-the-late-window.mp3`
- **Lyrics:**
  ```
  [Intro]
  (brushed drums, a lazy piano figure)
  [Verse 1]
  Last table's paid and the chairs go up,
  the trumpet packs away —
  one more for the ones still sitting,
  then we call it a day.
  [Chorus]
  Closing the late window, love,
  the deep hour's nearly through —
  the honest and the hopeless both
  got somewhere they gotta be at two.
  [Verse 2]
  Same brave lamps on every world,
  different star outside —
  but the night shift hears the same slow song
  wherever they reside.
  [Chorus]
  [Verse 3]
  Somebody's crying in the corner booth,
  somebody's laughing low —
  we play a little softer for the both of them
  and we let the last one go.
  [Chorus]
  [Piano Solo]
  (lazy electric-piano break, muted trumpet answering)
  [Bridge]
  (piano and voice, close)
  So thank you for the quiet hours,
  thank you for the stay —
  we'll leave the light on the relay
  and we'll do it all again someday.
  [Chorus]
  (barely above a whisper)
  [Chorus]
  (last time, almost spoken)
  [Outro]
  (piano alone, one soft chord, fades to nothing)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: nightliners__closing-the-late-window
    title: "Closing the Late Window"
    artist: "The Nightliners"
    artist_figure_id: null
    album: "The Late Window"
    era: "age-of-relays"
    in_world_year: 2620
    mood: "mellow"
    tags: [void-lounge, blues, concordance, night, age-of-relays]
    story_blurb: "The last-call lounge blues — 'the honest and the hopeless both got somewhere to be at two.' The Nightliners closing the room, gentle as it gets."
    duration_sec: null
    audio_path: "assets/music/nightliners__closing-the-late-window.mp3"
    licence_note: null
  ```

### C4. Odessa Rhee — "Saltwater Under Titan"  *(from the B1 Persona)*
- **Style:** `slow blues ballad, deep and warm, weeping electric guitar, organ, brushed drums, powerhouse female blues vocal restrained, upright bass, vintage valve warmth, clean fade ending, 66 BPM`
- **File:** `assets/music/odessa-rhee__saltwater-under-titan.mp3`
- **Lyrics:**
  ```
  [Intro]
  (organ, a distant guitar, the sound of slow water)
  [Verse 1]
  They dug a sea beneath the ice,
  warmed it lamp by lamp,
  and now the harbour town of Titan
  smells of salt and damp.
  [Chorus]
  Saltwater under Titan,
  a sea we made by hand —
  and I stand on the made shore, love,
  the way my mother planned.
  [Verse 2]
  She never saw it finished,
  never smelled the brine —
  she just believed it would be here,
  and left the work to mine.
  [Chorus]
  [Verse 3]
  I bring my daughter down at dusk
  to feel the small waves come —
  she trails her hand and asks me who
  first dreamed a sea from none.
  [Chorus]
  [Guitar Solo]
  (weeping electric-blues break, organ swelling)
  [Bridge]
  (guitar weeps, voice swells then softens)
  There's something holy in a made sea —
  not a god's, but ours:
  proof that patience, love, and lamps
  can beat the frozen hours.
  [Chorus]
  (full but gentle)
  [Chorus]
  (last time, restrained power)
  [Outro]
  (the water sound returns, guitar fades to nothing)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: odessa-rhee__saltwater-under-titan
    title: "Saltwater Under Titan"
    artist: "Odessa Rhee"
    artist_figure_id: null
    album: "Old-System Sessions"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "tender"
    tags: [blues-ballad, titan, terraforming, harbor-life, age-of-relays]
    story_blurb: "A deep blues ballad standing on a sea made by hand under Titan's ice — 'patience, love, and lamps can beat the frozen hours.' Odessa Rhee's most moving."
    duration_sec: null
    audio_path: "assets/music/odessa-rhee__saltwater-under-titan.mp3"
    licence_note: null
  ```

### C5. Sela Maren — "Titan Bay at Midnight"  *(existing Persona)*
- **Style:** `slow blues-ballad, wistful and warm, gentle electric guitar, brushed drums, soft organ, tender female vocal, upright bass, vintage valve warmth, clean fade ending, 70 BPM`
- **File:** `assets/music/sela-maren__titan-bay-at-midnight.mp3`
- **Lyrics:**
  ```
  [Intro]
  (guitar, soft as lamplight)
  [Verse 1]
  Midnight on the harbour road,
  the methane sea lies still,
  the ferry lights are put to bed
  below the dome-lit hill.
  [Chorus]
  Titan bay at midnight,
  quietest place I know —
  where the whole loud harbour holds its breath
  and lets the slow tide go.
  [Verse 2]
  I come here when the shift is done
  to let the day unwind,
  and the far-off station music
  keeps me company and kind.
  [Chorus]
  [Verse 3]
  A late ferry ghosts across the dark,
  one lamp up on the bow —
  I raise a hand it'll never see,
  and that's a kind of vow.
  [Chorus]
  [Guitar Solo]
  (gentle blues break, soft organ under)
  [Bridge]
  (organ warm, guitar soft)
  Some folks need the bright and loud,
  and I love that too, it's true —
  but a quiet bay and a distant song
  is how I make it through.
  [Chorus]
  (gentle)
  [Chorus]
  (last time, tender and low)
  [Outro]
  (guitar fades into the still — clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: sela-maren__titan-bay-at-midnight
    title: "Titan Bay at Midnight"
    artist: "Sela Maren"
    artist_figure_id: null
    album: "Light on Titan Bay"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "wistful"
    tags: [blues-ballad, titan, harbor-life, night, age-of-relays]
    story_blurb: "A lamplit midnight blues-ballad on the methane harbour — 'a quiet bay and a distant song is how I make it through.' Sela Maren winding the day down."
    duration_sec: null
    audio_path: "assets/music/sela-maren__titan-bay-at-midnight.mp3"
    licence_note: null
  ```

### C6. Eli Renn — "Quiet Engines, Quiet Heart"  *(existing Persona)*
- **Style:** `slow soft-rock ballad, warm and nocturnal, clean electric guitar, brushed drums, warm bass, gentle male lead, subtle organ, warm analog tape, clean fade ending, 72 BPM`
- **File:** `assets/music/eli-renn__quiet-engines-quiet-heart.mp3`
- **Lyrics:**
  ```
  [Intro]
  (clean guitar, a low hum of engines)
  [Verse 1]
  We cut the drive for the coasting leg,
  and the whole ship goes still —
  no thrum in the deck, no roar in the walls,
  just the dark and the will.
  [Chorus]
  Quiet engines, quiet heart,
  nothing left to do but drift —
  and somewhere in the silent black
  I find the small ones lift.
  [Verse 2]
  It scares the new crew, all that hush,
  they're used to the working sound —
  but the old hands love the coasting weeks,
  when the loud world settles down.
  [Chorus]
  [Verse 3]
  The kid on watch asked how I stand it,
  the silence and the black —
  I said give it a week, you'll miss it, son,
  when the engines all come back.
  [Chorus]
  [Guitar Solo]
  (spacious clean-guitar break, organ drifting)
  [Bridge]
  (guitar and organ, spacious)
  You learn a thing on a silent ship
  you don't learn anywhere loud:
  that the quiet isn't empty, friend —
  it's just the noise unbowed.
  [Chorus]
  (soft)
  [Chorus]
  (last time, hushed)
  [Outro]
  (engines hum back up faintly under the last chord — clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: eli-renn__quiet-engines-quiet-heart
    title: "Quiet Engines, Quiet Heart"
    artist: "Eli Renn"
    artist_figure_id: null
    album: "Quiet Engines"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "serene"
    tags: [soft-rock, night, ship, contemplative, age-of-relays]
    story_blurb: "A hushed coasting-leg ballad — 'the quiet isn't empty; it's just the noise unbowed.' Eli Renn on why the old hands love the silent weeks."
    duration_sec: null
    audio_path: "assets/music/eli-renn__quiet-engines-quiet-heart.mp3"
    licence_note: null
  ```

### C7. Junia & the Long Players — "Slow Dance on the Ring"  *(from the A19 Persona)*
- **Style:** `slow soul ballad, warm and romantic, electric piano, soft horns, brushed drums, big warm female soul lead, tender backing harmonies, vintage motown warmth, clean fade ending, 68 BPM`
- **File:** `assets/music/junia-and-the-long-players__slow-dance-on-the-ring.mp3`
- **Lyrics:**
  ```
  [Intro]
  (electric piano, a soft horn line)
  [Verse 1]
  The party's winding down at last,
  the fast ones all played out —
  so take my hand and take it slow,
  that's what the last song's about.
  [Chorus]
  Slow dance on the ring, my love,
  let the whole sky wheel behind —
  a hundred worlds turning past the glass,
  and just this one that's mine.
  [Verse 2]
  We waited weeks to be in reach,
  a season on the black —
  so I'm not letting go this hour
  for anything, or back.
  [Chorus]
  [Verse 3]
  Your ship goes back at first-light call,
  a season more of dark —
  so let 'em turn the houselights low
  and hold this one last spark.
  [Chorus]
  [Horn Solo]
  (soft warm horn break, brushed drums)
  [Bridge]
  (horns swell, warm and full)
  Let the fast songs have the young and free —
  give me the last one, give me you and me.
  [Chorus]
  (tender, full)
  [Chorus]
  (last time, barely swaying)
  [Outro]
  (piano alone, one held chord, clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: junia-and-the-long-players__slow-dance-on-the-ring
    title: "Slow Dance on the Ring"
    artist: "Junia & the Long Players"
    artist_figure_id: null
    album: "After the Last Ferry"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "tender"
    tags: [soul, core, romance, night, age-of-relays]
    story_blurb: "The last-song soul ballad — a slow dance on the viewing ring after weeks apart. 'Give me the last one, give me you and me.'"
    duration_sec: null
    audio_path: "assets/music/junia-and-the-long-players__slow-dance-on-the-ring.mp3"
    licence_note: null
  ```

### C8. Calder Moon — "Blue Guitar, Red Evening"  *(from the existing Persona)*
- **Style:** `slow Mars blues, warm and dusty, slide electric guitar, brushed drums, upright bass, weathered male vocal, soft organ, vintage valve warmth, clean fade ending, 66 BPM`
- **File:** `assets/music/calder-moon__blue-guitar-red-evening.mp3`
- **Lyrics:**
  ```
  [Intro]
  (slide guitar, slow as a setting sun)
  [Verse 1]
  Red evening on the terraces,
  the dust all gone to gold,
  I take my blue guitar outside
  and play against the cold.
  [Chorus]
  Blue guitar, red evening,
  the only two I need —
  one for the ache of a far-off world,
  one for the ground we freed.
  [Verse 2]
  My father brought this guitar out
  wrapped up against the cold,
  said "son, a world ain't settled
  till somebody's played it old."
  [Chorus]
  [Verse 3]
  Now my own kid sits out here with me,
  learning where to lay her hand —
  and someday she'll play it slower still
  for a red and settled land.
  [Chorus]
  [Slide Guitar Solo]
  (weeping slide break, extended, dust on the wind)
  [Bridge]
  (slide weeps, voice low)
  So I play it old, I play it slow,
  I play it till the dark —
  a red world and a blue guitar,
  and a small, defiant spark.
  [Chorus]
  (warm, unhurried)
  [Chorus]
  (last time, low and content)
  [Outro]
  (slide fades into the Martian wind — clean fade)
  [End]
  ```
- **YAML:**
  ```yaml
  - id: calder-moon__blue-guitar-red-evening
    title: "Blue Guitar, Red Evening"
    artist: "Calder Moon"
    artist_figure_id: null
    album: "Red Soil, Blue Guitar"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "wistful"
    tags: [blues, mars, colony-life, night, age-of-relays]
    story_blurb: "A dusty red-evening Mars blues — 'a world ain't settled till somebody's played it old.' Calder Moon playing the ground his family freed."
    duration_sec: null
    audio_path: "assets/music/calder-moon__blue-guitar-red-evening.mp3"
    licence_note: null
  ```

---

## 4. Chart candidates (the pool The Count draws from — R6.1)

The daily chart show wants **up-tempo, hooky, present-day hits from names listeners know**. These 18 are
flagged `chart` in their tags — the natural chart pool (R6.1 can key on the `chart` tag, or promote it to
a real `featured`/`chart_eligible` field when the machinery lands):

| # | Track | Artist | Tier |
|---|---|---|---|
| A1 | Jukebox on the Concourse | The Ferry Cats | bright |
| A2 | Rest-Day Rock | The Ferry Cats | bright |
| A3 | Garden-District Girl | The Window Boxes | bright |
| A4 | Every Light in the Corridor | The Window Boxes | bright |
| A5 | Turnover Burn | The Lane Runners | bright |
| A6 | Loud on the Long Haul | The Kestrel Run | bright |
| A7 | Rivet Girls | The Hullbirds | bright |
| A8 | Pirate Frequency | The Belt Revival | bright |
| A9 | Standing Hour | Vela & the Beacons | bright |
| A10 | Coffee and the Overnight News | Sunwell | bright |
| A11 | Ride the Ring | The Ring Riders | bright |
| A13 | Flare Warning Boogie | The Corona Drivers | bright |
| A14 | Ice Highway | The Low Orbit Kings | bright |
| A16 | Red Dust Radio | North Array | bright |
| A18 | Everybody Breathes | The Pressure Door Union | bright |
| A19 | Good News Travels Slow | Junia & the Long Players | bright |
| A20 | Hands Off the Air | Vera Cross | bright |
| B6 | Made, Not Born | Asha Ko & The Second Sun | steady |

*(Non-chart tracks still air in normal music blocks — they're the catalogue depth, just not the chart's
weekly movers.)*

---

## 5. Coverage check (wave 3 = 42 tracks, all sung)

- **All voice, no instrumentals** — every entry ships a Lyrics block; nothing goes in the `[SONG]` slot
  silent. (Operator ask ✅.)
- **Genres, as requested:** rock-n-roll / rockabilly (Ferry Cats ×3), power-pop / jangle-pop (Window
  Boxes ×3), lane-rock (Lane Runners ×2, Kestrel Run, Hullbirds), heartland/garage/surf/boogie/protest
  rock (Low Orbit Kings, Belt Revival, Ring Riders ×2, Corona Drivers, Vera Cross), blues & blues-soul
  (Odessa Rhee ×3, Marlo Quist ×2, Jun Pelayo, Calder Moon ×2, Lagrange Saints, Nima Vale, Riko Say),
  soul / R&B (Junia & the Long Players ×3, Asha Ko), pop (Vela & the Beacons, Sunwell), folk-rock &
  soft-rock (Harmony Tract, Greenhouse Nine, Station Porch Trio, Eli Renn ×2), bluesy void-lounge
  (Nightliners). **No hymns, no drones, no solemn liturgy.** (Operator ask ✅.)
- **Present-day only** — every track is `age-of-relays`, in-world 2620–2626; nothing set in the First
  Expansion or the Silence. (Operator ask ✅.)
- **Bright-heavy for the chart** — 20 bright / 14 steady / 8 warm-evening; 18 flagged `chart`.
- **DNA held:** work, rest-day, love-across-the-lag, mending, hospitality, made weather, made seas, the
  commons, the night shift, the radio itself — the dignity of ordinary life and connection across
  distance, plain-spoken (SPIRIT §5a). No cynicism, no camp, no dystopia, no IP, no real names.
- **Six new Personas to save:** The Ferry Cats (A1), The Window Boxes (A3), The Ring Riders (A11),
  Junia & the Long Players (A19), Odessa Rhee (B1), Marlo Quist (C1).
- **Every Style string carries a clean-ending tag and every Lyrics block ends `[Outro] … [End]`** with a
  physical stop cue (§1c) — the finishing the operator asked for.
- **Length fixed for ~3 min (§1e):** every song is now three verses + a chorus that returns 3–4× +
  a bridge + at least one instrumental solo — the shape that renders **~2:45–3:30** in Suno v5, instead
  of the ~1-minute renders a short lyric produces. If you generated from the first draft, re-generate
  from these expanded lyrics.

## 6. After generating (the manifest wiring — later, per the operator)

Do **not** touch `config/tracks.yaml` yet. When generation is done:

1. For each **kept variant**, take the entry's YAML block, **duplicate per §1d** (append `_1`/`_2` to
   `id` and `audio_path`; optionally suffix the second `title`), and paste under `tracks:`.
2. Stamp `duration_sec` from the final files (or leave `null` — the seeder can fill it).
3. Set `licence_note` to the Suno-Pro clearance string once your plan's terms are confirmed.
4. Run `make seed-tracks`; report the new **playable count**. Artists here become D10 figures at the
   same backfill as waves 1–2 (link each `artist` string → its figure row).

*(R6.0 done-condition: brief written ✅ → operator generates + drops files → `make seed-tracks` loads
them → playable count reported. R6.1 then builds the chart machinery + The Count over this `chart` pool.)*

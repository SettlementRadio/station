# MEDIA_LIBRARY_V2.md — wave 2: the songs people remember (Suno brief)

> **The second wave of the song catalogue — 15 sung songs, deliberately up-tempo and hooky.** Wave 1
> (`docs/MEDIA_LIBRARY.md`, 27 songs) gave the catalogue its depth: ballads, hymns, drones — beautiful,
> but heavy. Real radio needs the other half: **rock anthems, pop hooks, singalongs** — the songs a
> listener hums after one play. This wave fixes the mood balance.
>
> **DNA check (why these still belong — SPIRIT.md):** hooks are not camp. The golden-age strain this
> wave leans on is *the dignity of ordinary life* (Bradbury/Heinlein): work songs, love songs, wake-up
> songs — joy as a serious subject. Every song here is warm, communal, and hopeful; none are cynical,
> dystopian, or novelty. Genres stay inside the canon's scenes (`70-music.md` facts 4–6, 13–16 +
> Earth-roots traditions). The §1 exclude set from `MEDIA_LIBRARY.md` still applies:
> `aggressive EDM, trap, drill, dubstep, heavy metal, distorted, harsh, comedic, chiptune novelty, autotune-heavy modern pop`.
>
> **How to use (same workflow as wave 1):** per song — paste **Style** into Suno's Styles box, paste
> **Lyrics** into the Lyrics box (all 15 are sung), set Vocal Gender per the style, generate, trim to
> a clean 3–4 min, save the MP3 under the exact **File** name, and **paste the YAML block into
> `config/tracks.yaml`** (append under `tracks:`), then run `make seed-tracks` (once D7.0 is built).
>
> **Personas:** existing acts (Lane Runners, Vela & the Beacons, Auroral Standard, Tin Reelers,
> Nightliners) — reuse their saved wave-1 Personas. New acts (**The Kestrel Run, The Hullbirds,
> Sunwell, Hearth & Hull**) — build the Persona from their first song here (★), then cut the second
> from it.

---

## The wave-2 roster additions (4 new acts → 18 total)

| Act | Genre / lane | World | Voice signature (the Persona) | Songs |
|---|---|---|---|---|
| **The Kestrel Run** | lane-rock (anthemic) | betweener | big warm stadium-rock, male lead + crowd vocals; named for a famous shipping lane | 2 |
| **The Hullbirds** | lane-rock (punchy, dockyard) | betweener | bright punchy rock, female lead, chanted backing; repair-dock underdog warmth | 2 |
| **Sunwell** | relay-pop (sunny duo) | concordance | male+female duo pop, breezy harmonies, garden-district morning sound | 2 |
| **Hearth & Hull** | earth-roots (singalong folk) | betweener | acoustic duo, guitar + hand percussion, everyone-joins choruses; the settlement songbook | 2 |

Wave-2 songs by existing acts: Lane Runners ×2, Vela & the Beacons ×2, Auroral Standard ×1,
Brace & the Tin Reelers ×1, The Nightliners ×1.

---

## The 15 songs

### The Lane Runners (existing Persona) — lane-rock

#### V2-1. "Green Lights All the Way"
- **Style:** `warm driving analog rock anthem, energetic drumkit, jangly bright electric guitars, road-worn male lead vocal, gang chorus, optimistic and unstoppable, big memorable hook, tape warmth, 128 BPM`
- **File:** `assets/music/lane-runners__green-lights-all-the-way.mp3`
- **Lyrics:**
  ```
  [Intro]
  (guitar riff, drums count in)
  [Verse 1]
  Cleared the dock at seven sharp,
  the board lit up like a festival —
  every buoy from here to home
  is showing green, unbelievable!
  [Chorus]
  Green lights all the way, green lights all the way,
  somebody up there likes us, we're gonna make the bay!
  Green lights all the way — sing it if you're bound:
  nothing between us and home but the black, and the black don't slow us down!
  [Verse 2]
  The chief don't smile on principle,
  but I caught her humming in the hold.
  Even the freight seems lighter now,
  even the coffee don't taste old.
  [Chorus]
  [Bridge]
  (half-time, one guitar)
  Now I know the dark's got moods,
  and I know a run can turn —
  but tonight the lanes are kind,
  and a kind night's a thing you earn.
  [Guitar Solo]
  [Chorus]
  (everyone, double)
  [Outro]
  (riff rides out, one last "green lights!")
  ```
- **YAML (paste into `config/tracks.yaml` under `tracks:`):**
  ```yaml
  - id: lane-runners__green-lights-all-the-way
    title: "Green Lights All the Way"
    artist: "The Lane Runners"
    artist_figure_id: null
    album: "Green Lights"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "joyful"
    tags: [lane-rock, betweener, age-of-relays, driving, joyful]
    story_blurb: "The luckiest run ever sung — every buoy green from dock to bay. Haulers play it leaving port for luck; harbourmasters swear it works."
    duration_sec: null
    audio_path: "assets/music/lane-runners__green-lights-all-the-way.mp3"
    licence_note: null
  ```

#### V2-2. "Heavy and Happy"
- **Style:** `warm mid-tempo rock groove, chunky rhythm guitar, steady rolling drums, road-worn male lead, playful backing shouts, content and grinning, singalong chorus, tape warmth, 112 BPM`
- **File:** `assets/music/lane-runners__heavy-and-happy.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a laugh, then the groove)
  [Verse 1]
  Loaded to the waterline, every locker full,
  grain for the outer stations, wire and wool.
  Some ships fly empty, light and fast and free —
  not this one, darling, and that's fine by me.
  [Chorus]
  We're heavy and happy, low in the lane,
  every ton a promise, every klick a gain!
  Heavy and happy — that's the hauler's law:
  the fuller the hold, the better the song! (hey!)
  [Verse 2]
  The purists fly their sleek machines,
  all chrome and nothing in the back.
  We wave as they go streaking by —
  they're racing nowhere, we're bringing the whole town back.
  [Chorus]
  [Bridge]
  (drums drop out, claps keep time)
  'Cause an empty ship is an empty tale,
  and a hold full up is a town that won't fail —
  so load her deep and sing her slow,
  we carry the worlds where the worlds wanna go!
  [Chorus]
  (big, everyone)
  [Outro]
  (groove winds down, another laugh)
  ```
- **YAML:**
  ```yaml
  - id: lane-runners__heavy-and-happy
    title: "Heavy and Happy"
    artist: "The Lane Runners"
    artist_figure_id: null
    album: "Green Lights"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "warm"
    tags: [lane-rock, betweener, age-of-relays, warm, joyful]
    story_blurb: "The hauler's grin set to a groove — a full hold as a point of pride. The unofficial anthem of every loading dock on the frontier run."
    duration_sec: null
    audio_path: "assets/music/lane-runners__heavy-and-happy.mp3"
    licence_note: null
  ```

---

### The Kestrel Run (NEW — build Persona from V2-3 ★) — anthemic lane-rock

#### V2-3. "Run the Kestrel"  ★ Persona seed
- **Style:** `big warm stadium rock anthem, soaring male lead vocal, crowd chant backing, driving drums, ringing open guitar chords, triumphant and communal, huge memorable chorus, tape warmth, 124 BPM`
- **File:** `assets/music/kestrel-run__run-the-kestrel.mp3`
- **Lyrics:**
  ```
  [Intro]
  (crowd stomp-stomp-clap, guitars ring in)
  [Verse 1]
  There's a lane they cut when my gran was young,
  fastest thread through the middle dark —
  they named it for a diving bird
  no one out here has ever heard.
  [Chorus]
  Run the Kestrel! (run the Kestrel!)
  Fast and true! (fast and true!)
  Every light on that old lane
  is somebody coming through!
  Run the Kestrel, run it proud,
  sing it soft or sing it loud —
  the shortest road through the longest dark
  runs straight through me and you!
  [Verse 2]
  Pilots tip their caps to her,
  the buoys blink her name in code.
  Half the worlds got built from crates
  that rode that dear old road.
  [Chorus]
  [Bridge]
  (quiet, one voice, crowd humming)
  And when they chart a faster thread,
  and the Kestrel's traffic thins —
  we'll still sing her every port we make,
  'cause that's where us begins.
  [Chorus]
  (full crowd, key up)
  [Outro]
  (stomp-stomp-clap fades like a departing ship)
  ```
- **YAML:**
  ```yaml
  - id: kestrel-run__run-the-kestrel
    title: "Run the Kestrel"
    artist: "The Kestrel Run"
    artist_figure_id: null
    album: "The Kestrel Run"
    era: "age-of-relays"
    in_world_year: 2621
    mood: "celebratory"
    tags: [lane-rock, betweener, age-of-relays, driving, celebratory]
    story_blurb: "A stadium-sized anthem for the famous shipping lane the band is named after — the shortest road through the longest dark. Crowds do the stomp-stomp-clap unprompted."
    duration_sec: null
    audio_path: "assets/music/kestrel-run__run-the-kestrel.mp3"
    licence_note: null
  ```

#### V2-4. "Same Stars Tonight"  *(from the V2-3 Persona)*
- **Style:** `warm mid-tempo rock anthem, heartfelt male lead, big gentle singalong chorus, ringing guitars, steady drums, lighters-up feeling, tender and huge at once, tape warmth, 100 BPM`
- **File:** `assets/music/kestrel-run__same-stars-tonight.mp3`
- **Lyrics:**
  ```
  [Intro]
  (single guitar, warm)
  [Verse 1]
  You're three relays out and a season gone,
  and I'm still keeping your side of the dawn.
  Different harbour, different sky —
  but listen, love, before you cry:
  [Chorus]
  We're under the same stars tonight,
  same old fires, same old light.
  Wherever the work takes you from me,
  look up — that's where I'll be.
  Same stars tonight.
  [Verse 2]
  Your mother asks me how you are,
  I read your letters at the bar,
  and the whole crew raises one for you —
  the distance don't get a vote in what's true.
  [Chorus]
  [Bridge]
  (drums build, crowd joins)
  They can map the dark a thousand ways,
  chart every lane and light —
  but nobody's drawn the line yet
  that cuts through "same stars tonight."
  [Chorus]
  (everyone, arms up)
  [Chorus]
  (softer, almost goodnight)
  [Outro]
  (the guitar alone again)
  ```
- **YAML:**
  ```yaml
  - id: kestrel-run__same-stars-tonight
    title: "Same Stars Tonight"
    artist: "The Kestrel Run"
    artist_figure_id: null
    album: "The Kestrel Run"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "hopeful"
    tags: [lane-rock, betweener, age-of-relays, hopeful, tender]
    story_blurb: "The lighters-up anthem of the settled worlds — for everyone with someone three relays away. The chorus is sung at every send-off and every homecoming."
    duration_sec: null
    audio_path: "assets/music/kestrel-run__same-stars-tonight.mp3"
    licence_note: null
  ```

---

### The Hullbirds (NEW — build Persona from V2-5 ★) — punchy dockyard rock

#### V2-5. "Dockyard Heart"  ★ Persona seed
- **Style:** `bright punchy rock, confident female lead vocal, chanted gang backing, tight energetic drums, crunchy warm rhythm guitar, upbeat and gutsy, catchy shout-along hook, tape warmth, 126 BPM`
- **File:** `assets/music/hullbirds__dockyard-heart.mp3`
- **Lyrics:**
  ```
  [Intro]
  (four hits on the rim, guitar kicks)
  [Verse 1]
  Born in the clang of the repair bays,
  raised on the smell of sealant and tea,
  my lullabies were docking claxons —
  the yard made you, the yard made me!
  [Chorus]
  I got a dockyard heart! (hey! hey!)
  Beat like a rivet gun! (hey! hey!)
  You can shine up all your garden worlds —
  I'll take the yard, the noise, the grease, the fun!
  Dockyard heart!
  [Verse 2]
  Ships come in all broke and weary,
  we send 'em out like they're brand new.
  Fixing things is a kind of loving —
  somebody oughta write that true. (we just did!)
  [Chorus]
  [Bridge]
  (drums only, chant)
  Weld it! Seal it! Test it! Fly!
  Weld it! Seal it! Test it! Fly!
  (guitar back in, big)
  [Chorus]
  (double, everyone shouting the heys)
  [Outro]
  (one last rivet-gun drum fill, clean stop)
  ```
- **YAML:**
  ```yaml
  - id: hullbirds__dockyard-heart
    title: "Dockyard Heart"
    artist: "The Hullbirds"
    artist_figure_id: null
    album: "Patchwork Wings"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "joyful"
    tags: [lane-rock, betweener, age-of-relays, driving, joyful]
    story_blurb: "The repair-dock anthem — 'fixing things is a kind of loving.' The Hullbirds grew up in the yards and it shows; the weld-it-seal-it chant is a playground game now."
    duration_sec: null
    audio_path: "assets/music/hullbirds__dockyard-heart.mp3"
    licence_note: null
  ```

#### DONE_V2-6. "Patchwork Wings"  *(from the V2-5 Persona)*
- **Style:** `warm upbeat rock, spirited female lead, harmonised chorus, driving but friendly drums, bright guitar riff, underdog pride, uplifting and catchy, tape warmth, 118 BPM`
- **File:** `assets/music/hullbirds__patchwork-wings.mp3`
- **Lyrics:**
  ```
  [Intro]
  (bright riff, twice)
  [Verse 1]
  She's got plates from seven salvage yards,
  a hatch that used to be a door,
  a name that's painted over three old names —
  and she flies better than before!
  [Chorus]
  Patchwork wings still fly! (still fly!)
  Second-hand can touch the sky! (the sky!)
  Don't you tell me what a thing was for —
  tell me what it's gonna be!
  Patchwork wings, that's me!
  [Verse 2]
  They laughed at her at the core-side docks,
  all gleam and matching parts.
  But gleam don't cross the deep dark twice —
  that takes patches, and it takes heart.
  [Chorus]
  [Bridge]
  (half-time, tender for eight bars)
  Everything out here is mended —
  the ships, the domes, the people too.
  Mended's not a mark of shame, love:
  mended means you made it through.
  [Chorus]
  (big finish)
  [Outro]
  (riff once more, clean stop)
  ```
- **YAML:**
  ```yaml
  - id: hullbirds__patchwork-wings
    title: "Patchwork Wings"
    artist: "The Hullbirds"
    artist_figure_id: null
    album: "Patchwork Wings"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "hopeful"
    tags: [lane-rock, betweener, age-of-relays, hopeful, joyful]
    story_blurb: "The underdog song — a ship of salvaged plates that flies better than new. 'Mended means you made it through' gets quoted far beyond the music."
    duration_sec: null
    audio_path: "assets/music/hullbirds__patchwork-wings.mp3"
    licence_note: null
  ```

---

### Vela & the Beacons (existing Persona) — relay-pop

#### V2-7. "Counting Down the Sky"
- **Style:** `bright retro harmony pop, warm female lead, doo-wop group backing, handclaps, bouncing upright bass, chiming guitar, giddy and sweet, irresistible hook, tape warmth, 120 BPM`
- **File:** `assets/music/vela-and-the-beacons__counting-down-the-sky.mp3`
- **Lyrics:**
  ```
  [Intro]
  (claps + "ba-da-da" backing)
  [Verse 1]
  Circled every day in red,
  a calendar above my bed —
  your ship left port a year ago,
  and now there's only ten to go!
  [Chorus]
  I'm counting down the sky! (ten!)
  Every night one less goodbye! (nine!)
  When that old freighter crests the bay,
  I'll throw the calendar away!
  Counting down, counting down the sky!
  [Verse 2]
  Eight — I wash the harbour coat.
  Seven — practise my hello.
  Six — I can't remember five,
  'cause four is all I know! (three! two!)
  [Chorus]
  [Bridge]
  (backing hums, lead soft)
  They say don't count the days, they're slow —
  but honey, that's the charm:
  every number I cross out
  is you, closer in my arms. (one...)
  [Chorus]
  (key change, joyous)
  [Outro]
  (spoken over the "ba-da-da": "...zero." — a harbour bell rings)
  ```
- **YAML:**
  ```yaml
  - id: vela-and-the-beacons__counting-down-the-sky
    title: "Counting Down the Sky"
    artist: "Vela & the Beacons"
    artist_figure_id: null
    album: "Signals"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "joyful"
    tags: [relay-pop, core, age-of-relays, bright, joyful]
    story_blurb: "The arrival-day countdown song — ten nights till the freighter crests the bay. Harbour crowds shout the numbers back; the final bell is real on some worlds."
    duration_sec: null
    audio_path: "assets/music/vela-and-the-beacons__counting-down-the-sky.mp3"
    licence_note: null
  ```

#### V2-8. "P.S. I'm Still Yours"
- **Style:** `sweet retro pop, tender female lead, soft doo-wop harmonies, gentle swing beat, warm upright bass, playful and loving, hooky and light, tape warmth, 108 BPM`
- **File:** `assets/music/vela-and-the-beacons__ps-im-still-yours.mp3`
- **Lyrics:**
  ```
  [Intro]
  (soft "ooh" backing, a typewriter-ish tick of percussion)
  [Verse 1]
  Wrote you all the boring news:
  the dome leak's fixed, I lost my shoes,
  your brother's beard looks worse than mine —
  and then I signed the last line:
  [Chorus]
  P.S. I'm still yours! (still yours!)
  Same as every letter before! (before!)
  Twelve weeks out on a one-way beam,
  short and simple, plain as it seems —
  P.S. I'm still yours!
  [Verse 2]
  You once wrote back, "you always say it,
  it's word for word, you never change" —
  well sweetheart, some things bear repeating
  across that much exchange!
  [Chorus]
  [Bridge]
  (harmonies swell)
  Let the clever songs be clever,
  let the poets earn their pay —
  the finest thing I ever wrote
  is four small words a world away.
  [Chorus]
  (warm, everyone)
  [Outro]
  ("ooh" fades; spoken, smiling: "P.S. — still.")
  ```
- **YAML:**
  ```yaml
  - id: vela-and-the-beacons__ps-im-still-yours
    title: "P.S. I'm Still Yours"
    artist: "Vela & the Beacons"
    artist_figure_id: null
    album: "Signals"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "tender"
    tags: [relay-pop, core, age-of-relays, tender, bright]
    story_blurb: "Four words signed at the end of every relay letter, made into a hook. The postscript half the settled worlds now writes on purpose."
    duration_sec: null
    audio_path: "assets/music/vela-and-the-beacons__ps-im-still-yours.mp3"
    licence_note: null
  ```

---

### Sunwell (NEW duo — build Persona from V2-9 ★) — sunny relay-pop

#### V2-9. "Good Morning, Universe"  ★ Persona seed
- **Style:** `breezy feel-good pop duo, warm male and female vocals trading lines, sunny acoustic guitar, light bouncy drums, bright keys, cheerful harmonies, morning-radio hit, catchy and kind, tape warmth, 114 BPM`
- **File:** `assets/music/sunwell__good-morning-universe.mp3`
- **Lyrics:**
  ```
  [Intro]
  (a stretch and a strum)
  [Verse 1]
  (her) Kettle's on and the shutters up,
  the garden domes are gold —
  (him) Somewhere it's the dead of night,
  (both) but morning's ours to hold!
  [Chorus]
  Good morning, universe! (good morning!)
  How'd you sleep, old friend? (how'd you sleep?)
  A hundred worlds are waking up
  and starting up again!
  Whatever yesterday forgot,
  today can still be learned —
  good morning, universe!
  The lights are coming on wherever you turn!
  [Verse 2]
  (him) The relay's warm with overnight news,
  (her) some of it's even good —
  (both) and the ferry's full of sleepy folks
  all doing what they should!
  [Chorus]
  [Bridge]
  (just the two voices, close)
  It's a big old dark, we've heard, we've heard —
  but look what's in it: us.
  And every single morning
  the sun shows up without a fuss.
  [Chorus]
  (bigger, claps)
  [Outro]
  (whistled melody, fading like a walk to work)
  ```
- **YAML:**
  ```yaml
  - id: sunwell__good-morning-universe
    title: "Good Morning, Universe"
    artist: "Sunwell"
    artist_figure_id: null
    album: "Garden Districts"
    era: "age-of-relays"
    in_world_year: 2623
    mood: "bright"
    tags: [relay-pop, concordance, age-of-relays, bright, joyful]
    story_blurb: "The wake-up song of the garden districts — a duo trading lines over breakfast. First-light radio gold; the whistled outro is everyone's walk-to-work tune."
    duration_sec: null
    audio_path: "assets/music/sunwell__good-morning-universe.mp3"
    licence_note: null
  ```

#### V2-10. "Picnic on the Ring"  *(from the V2-9 Persona)*
- **Style:** `playful summer pop duo, male and female harmonies, skipping upbeat rhythm, bright guitar and keys, lighthearted and warm, holiday feeling, singable chorus, tape warmth, 120 BPM`
- **File:** `assets/music/sunwell__picnic-on-the-ring.mp3`
- **Lyrics:**
  ```
  [Intro]
  (bright count-in: "one, two — you bring the basket!")
  [Verse 1]
  (her) Rest-day comes but once a week
  and the viewing ring is free —
  (him) pack the bread and the good preserves,
  (both) save the window seat for me!
  [Chorus]
  Picnic on the ring! (on the ring!)
  Watch the whole sky wheel and swing! (wheel and swing!)
  Half the stars are somebody's home —
  wave at 'em while you eat!
  Picnic on the ring, my love,
  best seat that there'll ever be!
  [Verse 2]
  (him) Old man Tam brings his squeezebox up,
  (her) the kids race the corridor —
  (both) and for one slow turn of the station
  nobody's thinking of the chore-list anymore!
  [Chorus]
  [Bridge]
  (slower, dreamy)
  They built this ring for engineering,
  all torque and spin and steel —
  funny how the finest thing it makes
  is one free afternoon that's real.
  [Chorus]
  (everyone, joyful)
  [Outro]
  (the squeezebox takes the melody, laughter, fade)
  ```
- **YAML:**
  ```yaml
  - id: sunwell__picnic-on-the-ring
    title: "Picnic on the Ring"
    artist: "Sunwell"
    artist_figure_id: null
    album: "Garden Districts"
    era: "age-of-relays"
    in_world_year: 2624
    mood: "joyful"
    tags: [relay-pop, concordance, age-of-relays, joyful, bright]
    story_blurb: "Rest-day on the viewing ring — bread, preserves, and the whole sky wheeling past the window. The station-kid summer song."
    duration_sec: null
    audio_path: "assets/music/sunwell__picnic-on-the-ring.mp3"
    licence_note: null
  ```

---

### Auroral Standard (existing Persona) — pulse-dance

#### V2-11. "Turn Up the Lights"
- **Style:** `warm euphoric synth-dance, four-on-the-floor, joyful female lead, big communal chorus, bright analog arpeggios, hands-up build and release, celebratory and kind, tape warmth, 124 BPM`
- **File:** `assets/music/auroral-standard__turn-up-the-lights.mp3`
- **Lyrics:**
  ```
  [Intro]
  (arpeggio blinks on, a crowd noise swells)
  [Verse 1]
  Long week, long dark, long list of things
  that almost got me down —
  but it's seventh-night on the storm coast, baby,
  and the power's back in town!
  [Pre-Chorus]
  One switch, two switch, every room aglow —
  [Chorus]
  Turn up the lights! (turn 'em up!)
  Every window, every hall! (every hall!)
  Let the whole dark coast look up tonight
  and see we're not small at all!
  Turn up the lights, turn up the lights —
  we are the brightest thing in sight!
  [Verse 2]
  My gran says joy's a generator:
  you crank it, it comes on.
  So grab my hand, the floor's been waxed,
  and the storm can keep the dawn!
  [Pre-Chorus]
  [Chorus]
  [Bridge]
  (beat drops to a heartbeat, voice close)
  And somewhere out a ship looks down
  and sees our little glow —
  that's us, that's home, that's everyone —
  now let the whole void know!
  [Build]
  [Chorus]
  (full, hands up)
  [Outro]
  (the arpeggio slows, one light left on)
  ```
- **YAML:**
  ```yaml
  - id: auroral-standard__turn-up-the-lights
    title: "Turn Up the Lights"
    artist: "Auroral Standard"
    artist_figure_id: null
    album: "Storm Season"
    era: "age-of-relays"
    in_world_year: 2626
    mood: "celebratory"
    tags: [pulse-dance, meridian, age-of-relays, synthesist, celebratory]
    story_blurb: "Seventh-night on the storm coast, power restored, every window lit — 'we are the brightest thing in sight.' The dance-floor closer on three worlds."
    duration_sec: null
    audio_path: "assets/music/auroral-standard__turn-up-the-lights.mp3"
    licence_note: null
  ```

---

### Brace & the Tin Reelers (existing Persona) — frontier-reel

#### V2-12. "Everybody Brings a Drum"
- **Style:** `joyful frontier reel, fast and danceable, rowdy warm group vocals, oxygen-tank drums, wire chimes, stomps and claps, call-and-response chorus, infectious party energy, tape warmth, 130 BPM`
- **File:** `assets/music/brace-and-the-tin-reelers__everybody-brings-a-drum.mp3`
- **Lyrics:**
  ```
  [Intro]
  (one drum, then two, then ten)
  [Verse 1]
  There's no ticket to the yard tonight,
  no list and no velvet rope —
  the only rule since the first dome rose
  is written on the door in soap:
  [Chorus]
  Everybody brings a drum! (brings a drum!)
  Pot or pan or barrel, come! (barrel, come!)
  If it rings when you bang it, it's an instrument —
  everybody brings a drum!
  [Verse 2]
  The doc brought a tray, the chief brought a tank,
  the kid brought a box of bolts —
  and the mayor, bless her serious heart,
  brought a gong and TWO revolts! (of rhythm!)
  [Chorus]
  [Bridge]
  (breakdown — every "instrument" solos two bars, crowd names them:)
  (the tray!) (the tank!) (the bolts!) (the gong!)
  (all together now —)
  [Verse 3]
  When the reel winds down and the little ones sleep
  in a pile of coats by the wall,
  we'll bang it out soft, one round for the dark —
   'cause the dark never learned to dance at all!
  [Chorus]
  [Chorus]
  (twice as loud, everything at once)
  [Outro]
  (one drum again, one laugh, done)
  ```
- **YAML:**
  ```yaml
  - id: brace-and-the-tin-reelers__everybody-brings-a-drum
    title: "Everybody Brings a Drum"
    artist: "Brace & the Tin Reelers"
    artist_figure_id: null
    album: "Salvage & Song"
    era: "age-of-relays"
    in_world_year: 2625
    mood: "celebratory"
    tags: [frontier-reel, freeholds, age-of-relays, salvage-perc, celebratory]
    story_blurb: "The open-door party reel — if it rings when you bang it, it's an instrument. The one song where the audience IS the band."
    duration_sec: null
    audio_path: "assets/music/brace-and-the-tin-reelers__everybody-brings-a-drum.mp3"
    licence_note: null
  ```

---

### The Nightliners (existing Persona) — void-lounge, uptempo

#### V2-13. "One More for the Relay"
- **Style:** `upbeat swinging lounge jazz, smoky warm female vocal, playful and quick, brushed uptempo drums, walking upright bass, bright electric piano, finger snaps, charming singalong hook, tape warmth, 132 BPM swing`
- **File:** `assets/music/nightliners__one-more-for-the-relay.mp3`
- **Lyrics:**
  ```
  [Intro]
  (snaps, walking bass — the room perks up)
  [Verse 1]
  The band was packing up their things,
  the barman called the hour —
  then the relay bell rang three sweet times:
  a ship made port at Flower!
  [Chorus]
  One more for the relay! (one more!)
  One more for the news that's good! (so good!)
  When the thread brings home a happy word,
  you drink to it, knock wood!
  Play it once for the ones who made it —
  one more for the relay!
  [Verse 2]
  A wedding out on Cold Harbor,
  a launch that didn't slip,
  a lost world found, a debt paid down,
  a granddaughter's first ship!
  [Chorus]
  [Bridge]
  (piano solo, then she leans in:)
  Now some folks say we'll toast to anything —
  and darling, guilty, true!
  But the dark's so big and the good's so small,
  you cheer what makes it through!
  [Chorus]
  (the whole room)
  [Outro]
  (bass walks out the door, one last snap)
  ```
- **YAML:**
  ```yaml
  - id: nightliners__one-more-for-the-relay
    title: "One More for the Relay"
    artist: "The Nightliners"
    artist_figure_id: null
    album: "The Late Window"
    era: "age-of-relays"
    in_world_year: 2617
    mood: "joyful"
    tags: [void-lounge, concordance, age-of-relays, joyful, warm]
    story_blurb: "The late-club toast song — when the relay bell brings good news, the band plays one more. Every bar has its own verse of local good news."
    duration_sec: null
    audio_path: "assets/music/nightliners__one-more-for-the-relay.mp3"
    licence_note: null
  ```

---

### Hearth & Hull (NEW duo — build Persona from V2-14 ★) — earth-roots singalong

#### V2-14. "The Lamplighter's Song"  ★ Persona seed
- **Style:** `warm acoustic folk singalong, male and female duo vocals, strummed guitar, hand percussion, easy campfire melody, generous joined chorus, timeless and kind, everyone can sing it, tape warmth, 104 BPM`
- **File:** `assets/music/hearth-and-hull__the-lamplighters-song.mp3`
- **Lyrics:**
  ```
  [Intro]
  (guitar strum, a knee-slap beat)
  [Verse 1]
  When the shift bell rings and the light goes low
  and the corridors hum goodnight,
  there's a someone walks the whole dome round
  making sure each lamp burns bright.
  [Chorus]
  Oh, light one for the traveller!
  And light one for the home!
  And light one for the far, far worlds
  so nobody walks alone!
  (one more time —)
  So nobody walks alone!
  [Verse 2]
  My father sang it on the ships,
  his mother sang it first,
  and they say it goes back all the way
  to the world where we were nursed.
  [Chorus]
  [Verse 3]
  So if you're out where the lanes run thin
  and the dark leans on your door,
  sing the lamplighter's easy song
  and it's daylight evermore!
  [Chorus]
  (everyone, rounds of it)
  [Outro]
  (voices drop away one by one till just the guitar — and one hum)
  ```
- **YAML:**
  ```yaml
  - id: hearth-and-hull__the-lamplighters-song
    title: "The Lamplighter's Song"
    artist: "Hearth & Hull"
    artist_figure_id: null
    album: "The Settlement Songbook"
    era: "age-of-relays"
    in_world_year: 2620
    mood: "warm"
    tags: [earth-roots, betweener, age-of-relays, warm, hopeful]
    story_blurb: "The song every settlement child knows — a lamplighter's round said to go back to the first ships. Hearth & Hull's recording is just the version everyone learned it from."
    duration_sec: null
    audio_path: "assets/music/hearth-and-hull__the-lamplighters-song.mp3"
    licence_note: null
  ```

#### V2-15. "Pass It On"  *(from the V2-14 Persona)*
- **Style:** `uplifting acoustic folk-pop, duo harmonies, bright strumming, claps on the backbeat, building joined choruses, generous and warm, feels like a crowd by the end, tape warmth, 112 BPM`
- **File:** `assets/music/hearth-and-hull__pass-it-on.mp3`
- **Lyrics:**
  ```
  [Intro]
  (strum + claps)
  [Verse 1]
  Got a coat I never wear enough,
  got a soup that stretches two,
  got an hour on my rest-day free —
  now what's an hour do?
  [Chorus]
  Pass it on! (pass it on!)
  What you've got is what you give!
  Pass it on! (pass it on!)
  That's the way the far worlds live!
  A little more than what you found —
  leave it better, pass it down,
  pass it on!
  [Verse 2]
  The dock-hand taught the kid to weld,
  the kid taught gran to call,
  and gran taught half the corridor
  the song that started it all!
  [Chorus]
  [Bridge]
  (claps only)
  Nobody made it out here alone —
  not one, not once, not ever.
  A settlement's just a pile of parts
  till the passing holds it together!
  [Chorus]
  [Chorus]
  (rounds, big and happy)
  [Outro]
  (claps carry on after the guitar stops — then laughter)
  ```
- **YAML:**
  ```yaml
  - id: hearth-and-hull__pass-it-on
    title: "Pass It On"
    artist: "Hearth & Hull"
    artist_figure_id: null
    album: "The Settlement Songbook"
    era: "age-of-relays"
    in_world_year: 2622
    mood: "hopeful"
    tags: [earth-roots, betweener, age-of-relays, hopeful, joyful]
    story_blurb: "The passing-it-down song — coats, soup, skills, and the song itself. Ends every Hearth & Hull show with the crowd carrying the claps out the door."
    duration_sec: null
    audio_path: "assets/music/hearth-and-hull__pass-it-on.mp3"
    licence_note: null
  ```

---

## Coverage check (wave 1 + wave 2 = 42 songs)

- **Mood rebalance (the point of this wave):** wave 2 adds joyful ×5, celebratory ×3, hopeful ×3,
  bright ×1, warm ×2, tender ×1 — zero melancholy/solemn. Combined catalogue is now roughly half
  up-tempo/bright, half reflective — a real daypart range.
- **Memorability:** every song has a shout-back or singalong hook (counted numbers, call-and-response,
  a four-word postscript, a stomp-clap pattern) — the "hum it after one play" test.
- **DNA held:** work, love, mornings, mending, hospitality, light-against-dark — the dignity of
  ordinary life, communal joy, connection across distance. No cynicism, no camp, no IP, no real names.
- **New Personas to save:** The Kestrel Run (V2-3), The Hullbirds (V2-5), Sunwell (V2-9),
  Hearth & Hull (V2-14).
- **After generating:** file per the `File:` line → paste the YAML block into `config/tracks.yaml`
  under `tracks:` → `make seed-tracks` (once D7.0 exists). Artists here become D10 figures at the
  same backfill as wave 1.

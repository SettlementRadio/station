# PHASE_D_PRODUCTION_TASKS.md — D7: Production Layer (sound design + songs)

> Sub-pack **D7** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the music format `formats/music.py`
> (`split_on_marker(script, marker)` → intro / `[SONG]` / back-announce, rendered via
> `common.render_single_voice(parts, voice, seg_id)` so the marker is never spoken and the **track sits
> in the gap** — today empty), `settings.format_music_song_marker="[SONG]"`, the ffmpeg seam in
> `providers/tts.py` (`concat_audio`, `_to_mp3`, `probe_duration` — ffmpeg lives only here today), the
> playout fallback chain in `config/radio.liq` (which already references an optional `assets/bed.mp3`
> tier), and the scheduler's playlist-entry placement (the disclosure ident is woven in as just another
> ordered entry — the pattern stings/jingles reuse).
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D7 brief); `docs/JINGLE_PROMPTS.md` (**the sonic-identity
> brief + Suno prompts + §3 "Mapping to the app" + §4 naming convention — already written; follow it**);
> `src/formats/music.py` + `src/formats/common.py` (`render_single_voice`); `src/providers/tts.py`
> (`concat_audio`); `config/radio.liq` (the bed tier); `docs/PHASE_C_ORIENTATION.md` §6.1 (music dropped
> from rotation) + §6.2/§9 (the C2.5 `prune` name-exemption rule for shared/reused media).
>
> **Depends on:** **D6** (dayparts/programs decide *when* idents/stings/beds fire). Uses JINGLE_PROMPTS.
> The **song catalogue + clearance is the human's separate call** — D7 builds only the plumbing so a
> *cleared* track just plays. (D8 commercials build their ad-break cadence + break stings on D7.)

**What D7 delivers (ROADMAP, verbatim intent).** Three media kinds, three homes:
- **Jingles / idents / stings / beds** — a static curated file-set in `assets/{idents,themes,stings}/`,
  **mixed with ducking** (a bed under speech, a sting before news): Layer 4 mixing, finally real (the
  brief + Suno prompts already live in `docs/JINGLE_PROMPTS.md`).
- **Songs** — tracks in `assets/music/`, catalogued by a **`tracks` table** as **cultural artifacts**
  (title, **artist** — linked to a D10 figure — album, in-world year/era, story, mood, licence note), which
  the scheduler drops into the `music` format's `[SONG]` slot with a DJ intro/back-announce that **tells
  the song's story** ("a classic from the 24th century, by …") + now-playing. The broader *music culture*
  (artists as people, releases as events) lives in D10/D3/canon — see those cross-refs; **only tracks with
  a file are playable**. *(Tech only — the catalog + lore + clearance is the human's call; the plumbing
  makes a cleared track, with its story, just play.)*

**The shift from today.** Layer 4 doesn't exist yet — the only non-speech audio is the C4 fallback bed,
and the `music` format's `[SONG]` slot is an unspoken marker with nothing behind it (so `music` is
dropped from rotation). D7 makes the station *sound produced*: curated idents/stings/jingles placed by
the programming grid, beds ducked under speech, and real tracks filling the song slot — then `music`
returns to air.

**Definition of done for D7:** curated media is registered and protected from the disk GC; station
idents/jingles air at program boundaries and a sting precedes the news; a bed is audibly ducked under
speech where the grid calls for it; a cleared track plays in the `music` slot with a DJ intro/back-
announce that *names it* and now-playing that *shows it*; `music` is back in the rotation/program mix
with no silent gaps; `ruff` + `pytest` green; README/DEVLOG updated.

---

## D7.0 — Media stores + the `tracks` table (curated, GC-safe)
**Goal:** a home and a catalogue for curated audio that the rest of D7 draws on, safe from the retention
GC.
**Do:**
- Create the curated file-sets under `assets/` per JINGLE_PROMPTS §4: `assets/idents/`, `assets/themes/`
  (program themes/jingles), `assets/stings/`, `assets/music/` (tracks), plus the existing `assets/bed.mp3`
  convention. `assets/` is gitignored (curated, non-regenerable media — backed up to object storage by
  C5, not regenerated). **`prune` (C2.5) only ever scans `segments_dir`, so anything under `assets/` is
  automatically safe** — keep all curated media there. If any *cached render* of a production clip must
  live in `segments/`, give it a GC-exempt name prefix (the disclosure-ident / evergreen-pool pattern).
- Add a **`tracks` table** in `store.py` (the only SQL) — but model a track as a **cultural artifact,
  not a labelled file.** A song in this world has an artist, an era, and a story; the DJ doesn't "play a
  piece of music," they say *"here's a classic from the 24th century, by …"*. So:
  `tracks(id, title, artist_figure_id nullable, in_world_artist, album nullable, in_world_year/era
  nullable, story_blurb nullable, mood, duration_sec, licence_note, audio_path, tags)`. The
  `artist_figure_id` **links the artist to a D10 figure** (so the musician is a real in-world person —
  referenceable, quotable, guest-able; `in_world_artist` is the plain-text fallback when no figure row
  exists yet). `album` / `era` / `story_blurb` are the lore the DJ intro/back-announce + now-playing draw
  on (D7.4). Add row dataclass + writes (`insert_tracks`) and reads (`all_tracks`, `tracks_by_mood`/
  `tracks_by_tags`, `tracks_by_artist`, `get_track`). Fold into `counts` + the **scoped** `clear_world`.
- **The catalogue is curated lore you own (a mini-bible), not generated.** A human adds a cleared track by
  dropping the file in `assets/music/` **and writing its lore** — recommend a **music-lore manifest** (or
  per-track sidecar) the seeder reads into `tracks` (the canon-folder pattern: human-authored source →
  seeded rows), so it's reproducible, diffable, and **survives a canon refresh** (it's curated, `source`
  = bible-authored, never tick-generated — OVERVIEW §2). Provide the registration path (seed from the
  manifest / a `make tracks` import). Ship a couple of **royalty-free/placeholder** tracks for testing —
  flag clearly that the real catalogue + lore + **licence clearance is the human's call**.
- **Playable songs vs music *culture* — the load-bearing boundary.** Only tracks with an actual
  `audio_path` are **playable**. But the world's *music culture* — artists, albums, scenes, eras the
  station merely *talks about* — is **lore + events, no audio needed** (see the D3/D10 cross-refs). So the
  station can reference a hundred artists/albums while playing the dozen you've cleared: a DJ may discuss a
  whole album and play the one single that has a file. Keep this split clean — `tracks` is the *playable*
  catalogue; the broader culture lives as canon (D1 culture cornerstone), figures (D10 musicians), and
  events (D3 releases). A track with no file is not playable; an artist with no track is still
  referenceable.
- Map idents/themes/stings to programs/events per JINGLE_PROMPTS §3 (which sting before news, which theme
  per program/daypart) — as config or a small lookup, so D7.2 can resolve "the right clip for here."
**Done when:** the `assets/` layout exists; the `tracks` table + reads/writes work; a track can be
registered with metadata; the ident/theme/sting→placement mapping is defined; nothing curated is ever in
GC's path.

## D7.1 — The Layer 4 mixing primitive (ducking / sting / levels)
**Goal:** one place that can lay a bed under speech and place a sting, at controlled levels — the real
Layer 4.
**Do:**
- Decide **where mixing lives** and **render-time vs playout-time** (write the choice down):
  - **Render-time baking** (recommended first cut): a `src/production/mix.py` (or extend the ffmpeg-owning
    seam) that shells ffmpeg to (a) **duck** a bed under a speech clip (`amix` + sidechain/volume
    automation, or a simple bed at a low fixed level under speech) and (b) **prepend/append a sting** to a
    clip — producing one mp3. This keeps the scheduler/playlist model intact (segments stay single mp3s)
    and is unit-checkable. **Recommended.**
  - **Playout-time ducking** (alternative/complement): a ducked bed layer in `config/radio.liq` under the
    speech source. More "live radio," but changes playout — note it as a follow-on if the baked approach
    isn't enough.
- Keep ffmpeg cohesive: it currently lives only in `tts.py` (concat/transcode/probe). Either add the
  *mixing* calls there or to a dedicated `production` module — pick one home for mixing ffmpeg and
  document it (don't scatter ffmpeg across many modules). Expose level/duck dials via `settings`
  (`production_bed_gain_db`, `production_duck_db`, etc.).
- Bound/guard like the other ffmpeg helpers (retry/log; a mix failure must degrade to the un-mixed
  speech, never produce silence).
**Done when:** the primitive can bake a bed under a speech clip at a configured duck level and
prepend/append a sting, returning one mp3; levels are dials; a mix failure falls back to clean speech.

## D7.2 — Idents / jingles / stings into the schedule (placed by the grid)
**Goal:** the station's discrete sonic identity airs at the right moments, driven by D6's programming.
**Do:**
- Place **station idents / program themes / stings** as ordered playlist entries — exactly the pattern
  the C3 disclosure ident already uses (`disclosure_ident_segment` → a `Segment` woven into the
  scheduler's order). Add the analogous producers: a `theme`/`ident`/`sting` segment from a curated
  `assets/` clip (static, gate-free, duration-stamped via `stamp_duration`), reused (not re-rendered).
- Drive placement from **D6's programming grid**: a program **theme/ident at program boundaries** (top of
  show), a **sting before the news** (resolve via the D7.0 mapping + `program_for`/the daypart). Cadence
  dials in `settings` (`production_ident_every_n` / boundary-triggered, `production_sting_before_news`,
  etc.). Keep the disclosure ident (C3) airing as-is — these are additive.
- These curated clips live under `assets/` (GC-safe). They flow through the normal scheduler placement so
  playout needs no change.
**Done when:** program themes/idents air at program boundaries and a sting precedes the news, placed by
the grid; cadence is config; the clips are reused curated `assets/` audio; the disclosure ident still
airs.

## D7.3 — Beds under speech (ducking) wired in
**Goal:** speech sits over a bed where the grid wants it, audibly ducked.
**Do:**
- Use the D7.1 primitive to lay a bed under speech for the segments/programs that call for it (per the
  D7.0 mapping + the program's framing hint) — e.g. a soft bed under the night talk show, none under the
  news. Apply at render (bake the bed under the speech segment) or via the playout bed layer, per the
  D7.1 decision.
- Make it selective and tunable (which programs get a bed, which bed, the duck level) — over-bedding is
  worse than none. Default conservative.
- Keep duration accounting honest: a bed-mixed segment is still measured (`stamp_duration`) on its final
  audio.
**Done when:** designated programs air with a bed audibly ducked under the speech; news (and other
bed-less programs) stay dry; the bed selection + level are dials; durations stay accurate.

## D7.4 — Songs: fill the `[SONG]` slot + re-add `music` to air
**Goal:** a real, cleared track plays in the music slot, introduced and back-announced by name — and
`music` returns to the rotation without silent gaps.
**Do:**
- **Select a track — a real selection *policy* (rule-based, no LLM), not a random pick.** When a `music`
  slot comes up, choose from the eligible (playable, in-licence) catalogue by a documented policy over the
  track tags — the "what to play" brain. Inputs, weighted (dials in `settings`):
  - **Daypart / program mood** — the active program (D6) carries a mood; match it (mellow overnight,
    brighter morning).
  - **World mood** — let the current world (D3) tilt the choice: a somber recent event pulls a somber
    track; an upbeat festival, an upbeat one. (Read from the live story log; cheap rule, not an LLM call.)
  - **Freshness** — don't repeat a song or artist that aired recently (reuse **D5**'s airplay memory if
    built; otherwise a simple recent-track list).
  - **Era / variety spread** — mix eras so it isn't all "24th-century classics" or all current.
  - **Featured / promoted** — if the world just "dropped a new album" or an artist is in the news (D3),
    favour that artist's playable tracks; honour an explicit human **feature/pin** flag on a track.
  Make the policy a small, testable selector (deterministic given the same inputs + a seed, so it's
  unit-checkable) with the weights as dials. **This is "the brain that decides what to play" — the
  scheduler/selector, not the LLM** (the LLM only writes the intro/back-announce around the chosen track).
- Pass the chosen track's **cultural lore** (title, artist, album, in-world year/era, story_blurb — D7.0)
  into the intro/back-announce prompt so the DJ **tells its story**, not just its name: *"Here's a classic
  from the 24th century, by …, off the album …"* — an artist, an era, a reason it suits the hour. (A
  track's `artist_figure_id` means the DJ can also draw on what that artist has been up to in the world —
  a recent release/award from D3, or the artist's own words via D10 — so a back-announce can tie the song
  to *now*, like real radio.) Fall back to the plain `in_world_artist` + name when the lore is thin.
- Fill the slot: instead of leaving the `[SONG]` gap empty, stitch the rendered intro → **the track
  audio** (`assets/music/...`) → the back-announce into one segment (`concat_audio([intro, track,
  backannounce])`), reusing the existing split-on-marker structure (the marker is still never spoken; the
  track now occupies the gap). Mind sample-rate/codec compatibility for the concat (transcode the track to
  the pipeline's mp3 if needed, via `_to_mp3`).
- Surface **now-playing**: feed the playing track into D6's now-playing/program-info feed (title + artist
  + album/era) so the player can show what's on, with its lore.
- **Re-add `music` to air:** add `"music"` back into the rotation — into **D6's program format mix** (the
  grid decides which programs play music) and/or `settings.buffer_rotation`. Confirm no silent gap can
  occur (PHASE_C_ORIENTATION §6.1: music was dropped precisely because the slot was empty — it is no
  longer).
**Done when:** the selector picks a track by the documented policy (mood/world/freshness/era/featured,
weighted by dials); a cleared track plays in the music slot, intro/back-announce tell its story,
now-playing shows it, and `music` airs in the grid/rotation with audio in the slot every time (no silent
gaps).
**Note — gates.** The intro/back-announce is generated text → keep the `generate_safe` + evergreen
fallback (as `music.py` does today). The track audio itself is curated/cleared (not generated), so it
doesn't pass the text gates — but the licence_note must be honoured (human's clearance call).

## D7.5 — Tests + verification + docs
**Goal:** the production logic is covered, and the sound is demonstrable.
**Do:**
- Tests (surgical): the mixing primitive produces an output of the expected duration and falls back to
  clean speech on a mix failure (mock/guard ffmpeg); the **track-selection policy** honours each weighted
  input — matches daypart/world mood, avoids recent repeats (D5), spreads eras, and favours a
  featured/promoted artist — and is **deterministic given the same inputs + seed**; the music builder
  stitches intro→track→back-announce in order and the intro prompt contains the track's lore
  (title/artist/era); idents/stings are placed as entries by the grid (mock the scheduler loop); curated
  `assets/` paths are never in the prune candidate set. Use small fixture audio + fixture `tracks` rows;
  don't depend on real curated media.
- Add a demo: render a `music` segment with a placeholder track (hear intro→track→back-announce) and a
  talk segment with a ducked bed; show now-playing reflecting the track.
- Update `README.md` (the `assets/` media layout; registering a track; the ident/sting/bed dials;
  `music` back on air), `.env.example` (`PRODUCTION_*`), and the DEVLOG (Phase D — D7). Cross-check
  JINGLE_PROMPTS §3/§4 stayed the source of truth for naming/placement.
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the demo audibly shows
idents/stings, a ducked bed under speech, and a real track in the music slot with a named intro.

---

## Explicitly NOT in D7 (→ other sub-packs)
- **Commercials / promos + ad-break cadence + sponsor reads** → **D8** (D7 provides the stings/beds and
  the placement pattern those breaks reuse; D8 adds the break content + cadence + `sponsors` table).
- **Choosing/clearing the actual song catalogue + writing its lore** → the **human's separate call** (D7
  ships the plumbing + placeholder tracks only; a cleared track with a `licence_note` + lore just plays).
- **The *artist* as an in-world person** (referenceable, quotable, guest-able) → **D10** (a musician is a
  `figure`; `tracks.artist_figure_id` links to it). D7 holds the *track + its lore*; D10 makes the artist
  *a person in the world*.
- **Music-culture *happenings*** — a new album, an award, a tour the station references/promotes →
  **D3** (authored or tick-generated *events*; the news covers them, DJs trail them). Hard line: **only
  curated tracks with a file are playable**; generated music culture is *lore/talk/events*, never a
  playable song. D7 plays the files; D3/D10/D1-culture supply the world around them.
- **Generating jingles/themes from scratch** → out of scope; JINGLE_PROMPTS is the human/Suno production
  brief — D7 *places + mixes* the curated outputs, it doesn't synthesize them.
- **emotion in the DJ voice / the wider roster** → **D9**.
- **Deciding which programs get music/beds at which hour** → **D6** (the grid); D7 honours the grid's
  decisions.

# PHASE_D_VOICE_ROSTER_TASKS.md — D9: Voice & Emotion + DJ Roster

> Sub-pack **D9** of Phase D (see `docs/PHASE_D_OVERVIEW.md`). Work in order, one task at a time:
> implement → show + how to verify → stop for review. Respect `CLAUDE.md` and the Phase D standing
> principles (OVERVIEW §2). Written against the **as-built code**: the TTS seam `providers/tts.py`
> (`synthesize(text, *, voice, emotion=None, out_path)` — **`emotion` is accepted but ignored on every
> backend today**; the logical-voice registries `_ELEVENLABS_VOICE_IDS` / `_KOKORO_VOICES` /
> `_SAY_VOICES` map a logical voice → a vendor id — **as of the 90-cast.md audit (2026-06-28) the roster
> is 10 DJs and all 10 logical voices are mapped on all three backends, but 9 are PLACEHOLDERS aliasing
> onto the two real presets; see the D9.2 note**), the conversation `Turn(speaker, voice, text)` +
> `_render_turns` (each turn voiced separately),
> the cast model in `store.py` (`"cast"` table: id, name, card_text, logical_voice, tags;
> `insert_cast`/`all_cast`/`get_cast_member`), `settings.convo_speaker_ids=["vell","wren"]`, and the
> story log (D3).
>
> **Injection point already marked.** `writers/conversation.py` `orchestrate` reserves where DJ memory
> goes: each host's history from the event log (D3) joined to their character card. The route-A
> naturalness pass (2026-06-29) leans on each card's voice/tics, so richer per-host memory composes
> directly with it — and the persona/"way of speaking" itself is authored in `docs/canon/90-cast.md`,
> the right home for any roster edits.
>
> **Read first:** `docs/PHASE_D_OVERVIEW.md` §3 (D9 brief); `docs/ROADMAP.md` (Phase D "voice & emotion +
> the DJ roster" bullet); `src/providers/tts.py` (the inert `emotion` param + the voice registries —
> **the only TTS importer; all of D9's voice work stays behind this seam**); `src/world/store.py`
> (`"cast"` — already supports more rows); `docs/PHASE_C_ORIENTATION.md` §8/§9 (**emotion presumes the
> flagship path — ElevenLabs carries emotion, Kokoro cannot**; the C6 launch-voice DECISION); D3's
> story-log reads (for DJ memory).
>
> **Depends on:** **D3** (the event/story log DJ memory draws on). **Presumes the C6 flagship-voice
> decision** (server track) for *audible* emotion — Kokoro has no emotion knob, so emotion is wired
> end-to-end but only audible on the flagship engine. The pronunciation lexicon + roster work apply on
> **either** engine and are buildable after **D1** (bible-authored cast) + **D6** (programming
> assignment).

**What D9 delivers (ROADMAP, verbatim intent).** Wire the `emotion` param to the chosen engine —
**ElevenLabs carries real emotion; Kokoro cannot, so emotion presumes the flagship path** — and add a
**pronunciation lexicon** so the world's invented names are spoken right. Grow the cast: add / edit /
remove DJs (a `cast` row + voice — already supported), each with their own persona, way of speaking, and
**history/memory drawn from the event log**, so a DJ remembers what the world (and they) lived through.

**Scope boundary vs Phase E.** D9 makes the roster *support* N DJs — a DJ authored in the bible (D1
`docs/canon/` cast file) with a voice mapping and persona card gets fully wired (writers' room, voice
registry, programmable via D6, memory from the log). **Adding/editing/removing a DJ is done by authoring
the bible + re-seed** — the current model. The **runtime write/management surface** (CRUD DJs and edit
the grid *without* re-seeding) is **Phase E** (as D6 noted). Don't build a management UI here.

**Definition of done for D9:** `emotion` flows end-to-end (writers → `tts.synthesize` → the flagship
engine's expressiveness controls) and is a no-op on Kokoro without breaking anything; a pronunciation
lexicon makes invented names spoken right and consistently on both engines; a third DJ authored in the
bible with a voice mapping airs in character on the programmed grid; on-air DJs reference past stories as
lived memory drawn from the event log; `ruff` + `pytest` green; README/DEVLOG updated.

---

## D9.0 — Wire `emotion` end-to-end to the flagship engine
**Goal:** the long-inert `emotion` param actually shapes the voice on the flagship path, behind the seam.
**Do:**
- Map a **logical emotion** (a small named vocabulary — e.g. `warm`, `wry`, `somber`, `bright`,
  `urgent`; a named module constant, like the voice registries) to the chosen engine's **expressiveness
  controls** inside `providers/tts.py`'s `_synthesize_elevenlabs` (the only place the ElevenLabs SDK
  lives). Keep the exact vendor controls behind the seam (don't leak them); expose the mapping as
  registry data + a `settings` default. **Do not fabricate the vendor API** — implement against the
  ElevenLabs SDK actually in use; if the control surface is unclear, leave a clearly-marked TODO and the
  seam in place rather than guessing.
- **Kokoro stays a no-op** (it has no emotion knob — PHASE_C_ORIENTATION §8): on Kokoro/`say`, `emotion`
  is accepted and ignored exactly as today, so nothing breaks when the default engine is local. Emotion
  becomes *audible* only on the flagship path — which is the **C6 launch-voice decision**; note that
  dependency in code + README.
- **Source the emotion value:** let the writers' room set it. Add an optional `emotion` to `Turn` (and a
  per-segment default from the program/format mood, D6/D7) so the orchestrator can annotate a turn
  ("Vell, somber here") and `_render_turns` passes it into `synthesize`. Decide how the orchestrator
  emits it (a light per-turn tag it already could produce, parsed alongside the speaker label) — keep it
  optional with a sensible default so un-annotated turns still render.
**Done when:** an emotion set on a turn/segment reaches `synthesize` and shapes the ElevenLabs render;
the same path is a clean no-op on Kokoro; the emotion vocabulary + mapping are data, not literals; the
C6 dependency for audibility is documented.

> **BUILT (2026-07-06).** Vocabulary `warm|wry|somber|bright|urgent` → `_ELEVENLABS_EMOTIONS` in
> `tts.py`, mapping each to the SDK's `VoiceSettings` (`stability`/`style`/`speed`); orchestrator emits
> a sparse `Name [emotion]:` tag; un-tagged turns take a daypart mood default
> (`_PART_OF_DAY_EMOTION` in `writers/conversation.py`), then `settings.tts_emotion_default`.
> **Open follow-up → C6:** the per-emotion `stability`/`style`/`speed` numbers (and the daypart
> defaults) are a conservative starting tune chosen WITHOUT a funded flagship listen — they must be
> retuned by ear during the C6 voice pass (see the C6 task), and possibly per DJ once D9.2 assigns
> distinct voices (a curve that suits "Adam" may not suit a brighter preset).

## D9.1 — Pronunciation lexicon for invented names
**Goal:** the world's invented names (settlements, the festival, in-world artists, DJ names) are spoken
right and consistently, on either engine.
**Do:**
- Add a **pronunciation lexicon** — data mapping a spelled name → a pronunciation hint (phonetic
  respelling and/or phonemes). Keep it editable (a file under `docs/`/`assets/` or a small store table;
  pick one, document it) so the human can fix a mispronunciation without code.
- Apply it **before synthesis, behind the TTS seam**, per engine: for Kokoro (espeak-ng/phoneme-based)
  and for the flagship (its pronunciation-dictionary / SSML-phoneme mechanism, if available) — abstract
  "apply the lexicon to this text for this engine" so callers don't know the mechanism. Where an engine
  can't take phonemes, fall back to a phonetic respelling substitution.
- Source the names from the bible (D1 canon) + the story log (D3 invented stories/artists) so the lexicon
  can be grown as the world grows; ship it seeded with the current canon's names (Vell, Wren, the Lumen
  Festival, settlement names).
**Done when:** a known invented name renders with the intended pronunciation on the active engine; an
unknown name falls back to the engine default unharmed; the lexicon is human-editable and applied behind
the seam.

## D9.2 — Grow the roster (N DJs, bible-authored, fully wired)
**Goal:** a DJ defined in the bible with a voice gets fully wired — beyond the two hardcoded hosts.

> **Heads-up — state as of the `90-cast.md` audit (2026-06-28).** The roster was already grown to **10
> bible-authored DJs** (Vell, Wren + 8 new: Joss, Kael, Mira, Thorn, Sera, The Archivist, Orin, Zhe) in
> `docs/canon/90-cast.md`, so this task's "add ≥1 new example DJ" is satisfied by real content. **But the
> 9 new logical voices are PLACEHOLDERS** in `tts.py`: they alias onto the two real presets
> (Adam/Rachel · Daniel/Samantha · `bm_george`/`af_heart`), so several DJs currently share a voice.
> This task therefore still owes: **(a)** give each new voice a **distinct** real preset (the D9.0/C6
> voice work), and **(b)** when making the registry **data-driven**, migrate these ~11 entries and
> **drop the aliasing** (search `tts.py` for "PLACEHOLDERS (D-cast)"). Also note
> `settings.convo_speaker_ids=["vell","wren"]` + the two-host framing are **still hardcoded**, so the 8
> new DJs are **seeded but not yet on air** until this task (cast-from-table) + **D6** (grid) wire them in.
**Do:**
- Generalise the roster beyond `settings.convo_speaker_ids=["vell","wren"]` and the hardcoded two-host
  framing: the **set of DJs comes from the `"cast"` table** (seeded from the D1 `docs/canon/` cast
  file), each with a persona card (`card_text`), a `logical_voice`, and tags. The writers' room +
  D6's programming pick hosts from this set (D6 already generalised `framing`/program hosts to N hosts;
  D9 makes the *cast itself* extensible and ensures a new DJ flows through end-to-end).
- Make the **voice registry data-driven** so adding a DJ doesn't require editing `tts.py`: a new logical
  voice → vendor id mapping should come from config/store (per engine), not a hardcoded dict — or, at
  minimum, a documented one-line registry add per engine. Keep the registries behind the seam.
- **Edit / remove** a DJ = edit the bible cast file + re-seed (the `clear_world` flow already reproduces
  the cast from source). Confirm removing a DJ leaves no dangling references (programming grid, voice
  registry) — fail loud on an unknown cast id (as the current `context.assemble` does).
- Add at least one **new example DJ** (persona card in the bible + voice mapping) and air it via D6's
  grid to prove the path; keep persona/voice distinct so multi-DJ segments still read as different people.
- **Defer the runtime management surface to Phase E** — D9 is bible-authored + re-seed, not a CRUD UI.
**Done when:** the cast is read from the table (not a 2-element constant); a newly-authored DJ with a
voice mapping airs in character on the grid; removing a DJ re-seeds cleanly with no dangling refs; the
voice registry grows without surgery on `tts.py` internals.

> **BUILT (2026-07-06).** The registry is DATA: `config/voices.yaml` (logical voice → vendor preset,
> per engine; loader in `tts.py`, cached by mtime) — the three hardcoded dicts and the 9 placeholder
> aliases are GONE; every DJ has a distinct preset per engine (`dj_two` stays as Wren's documented
> legacy alias). Kokoro picks are verified rendering locally; the 8 new ElevenLabs ids are
> premade-roster picks NOT yet heard (operator key lacks `voices_read`) — **confirm/repick at the C6
> listen**. `make seed-canon` now fails loud when a cast card names an unmapped voice (seed.py).
> The Bridge (grid weekends 07–12, joss + mira) is the first program airing the new cast; hosts
> flow grid→scheduler→formats (D6.2), and `context.assemble` still fails loud on an unknown cast id.
> `settings.convo_speaker_ids` remains ONLY as the legacy default-program fallback.

## D9.3 — Guest / non-host voices (figures, invited guests, soundbites)
**Goal:** voices beyond the rostered DJs — an in-world figure or an invited guest can speak in a
segment, the way real radio plays a clip or runs an interview.
**Do:**
- Generalise the room beyond "the rostered hosts": a segment may include a **temporary, non-host
  speaker** — a **D10 figure** voiced as a short **soundbite** ("here's what they said:" → the figure's
  line → back to studio), or an **invited guest** appearing for one segment (a brief interview). The
  conversation engine's turn model already voices each turn in its own voice (`Turn(speaker, voice,
  text)` + `_render_turns`), so the plumbing supports N voices — what's missing is letting the
  showrunner/room **introduce a non-host speaker and assign it a voice**, with a host bracketing and
  staying in control.
- A guest/figure voice = a logical voice from the **D9.2 data-driven registry**, attached to the figure
  (**D10**'s `figures.voice_id`) or to a one-off guest persona for the segment. Keep distinct voices so a
  guest reads as a different person from the hosts.
- Keep it **sparse and in-character** (texture, not a parade of voices); the guest/soundbite still
  carries the world's AI-disclosure posture (AI-voiced fiction).
- **This is the D9×D10 bridge:** D10 supplies the *figure + quote*; D9 gives it a *voice + a turn slot*.
  If D10 isn't built, a generic "invited guest" persona still works (a one-off voice for a segment);
  D10's figures/quotes are what make the guest world-grounded.
**Done when:** a segment can include a distinctly-voiced non-host speaker (a figure soundbite or an
invited guest), introduced and closed by a host, with the voice drawn from the registry; it degrades to
host-only when no guest/figure is present.

> **BUILT (2026-07-06).** `src/writers/guest.py` decides the guest: sparse air-time-seeded draw
> (`convo_guest_chance`, default ~1 in 5 talk slots; `convo_guest_enabled` off = pre-D9.3), figure
> soundbite when the context carries D10.2 quotes (newest pair; `figures.voice_id` honoured when it
> names a registry voice, else a stable-hash pick from the `guest_*` pool in voices.yaml — same
> figure, same voice), else a one-off invited persona labelled `Guest:`. The orchestrator weaves it
> (bracketed, short, inside the fiction); `parse_turns` takes the extra label; a **structural gate**
> in `compose_segment` re-rolls any draft where the guest opens or closes. Emotion tags (D9.0) and
> the lexicon (D9.1) apply to guest turns like any other.

## D9.4 — DJ memory from the event/story log
**Goal:** a DJ on air references what they (and the world) lived through — in character.
**Do:**
- Assemble a **per-DJ memory** from D3's story log: past/resolved (and notable ongoing) stories the DJ
  can reference as lived history. Feed it into the writers' room for that DJ (a "what {DJ} remembers"
  block in the dynamic context — small + variable, so it sits in the per-call part, not the cached
  bible, preserving the cache lever).
- Decide the memory's flavour: at minimum the significant past beats near now (reuse the D3 reads +
  `events.relative_phrase` framing); optionally **persona/coverage-weighted** (a DJ remembers what fits
  their persona, or what they themselves covered — drawing on D4's coverage / D5's airplay memory if
  built). Keep it bounded (a memory window dial) so it doesn't bloat the prompt or contradict freshness.
- Ensure memory references stay **consistent and in-character** (a DJ shouldn't misremember a resolved
  story) — lean on the existing continuity gate; a memory that contradicts canon/the log should be
  caught like any continuity flag.
- Distinguish from neighbours: this is a DJ *remembering on purpose* (D9), vs D4's news *coverage
  recurrence* and D5's *anti-repetition* — cross-reference so they don't merge.
**Done when:** an on-air DJ references a past story from the log as lived memory with correct past-tense
framing; the memory is bounded + in the dynamic context; it stays consistent (no misremembering) under
the continuity gate.

> **BUILT (2026-07-06).** `store.remembered_stories` (past beats in a look-back window; resolved-first)
> → `writers/memory.py` renders a per-host "What {DJ} remembers" block: persona-weighted by card-tag
> overlap, bounded by `convo_memory_window_days` + `convo_memory_per_host`, each story clipped to a
> one-sentence handle, clock-framed via `events.phrase_for_datetime` + arc-labelled
> (resolved / still unfolding). Injected in the orchestrator's PER-CALL system (cache lever holds) and
> shown to the continuity editor so misremembering flags (the gate re-rolls). Degrades to "" on
> off/empty-log/DB failure. The tag vocabularies were ALIGNED the same day: every cast card in
> `90-cast.md` now carries a few tick-DOMAIN tags (the file's intro documents the double duty), a
> `sports` domain was added to `world_tick.DOMAINS` so Kael's beat exists in the generated world,
> and the candidate window was widened — verified live: Vell recalls peoples/history stories, Wren
> relay/nations, Thorn finance/war, Mira culture/literature.

## D9.5 — Tests + verification + docs
**Goal:** voice/roster/memory logic is covered, and the result is demonstrable.
**Do:**
- Tests (surgical; mock the vendor calls — don't hit a paid TTS API): the emotion vocabulary maps to the
  engine controls and is a no-op on Kokoro; an un-annotated turn renders with the default; the lexicon
  transforms a known name and passes an unknown one through; the cast is read from the table and an
  unknown cast id fails loud; per-DJ memory assembles bounded past beats with correct framing. Use
  fixtures (a fixture cast row, a fixture story log).
- Add a demo: render a short two-DJ exchange on the **flagship** engine with per-turn emotion (audible
  difference) and the lexicon applied; air the new example DJ via the grid; show a DJ referencing a past
  story as memory. (Flagship audibility needs a funded key — note it; the Kokoro path still runs as a
  no-op for the non-emotion checks.) If the funded key is available before C6, use this demo to start
  the **emotion-curve retune by ear** (the D9.0 `_ELEVENLABS_EMOTIONS` `stability`/`style`/`speed`
  numbers are an unheard starting tune — C6 owns the final tune, but note findings here).
- Update `README.md` (emotion needs the flagship engine / C6; the lexicon + how to edit it; authoring a
  new DJ in the bible + voice mapping; DJ memory), `.env.example` (`VOICE_*`/`ROSTER_*`/lexicon path),
  and the DEVLOG (Phase D — D9).
- **Append this pack's admin how-tos to `docs/ADMIN_MANUAL.md`** — terse (what it does + the exact
  command/file/steps) — for the D11 capstone to consolidate.
**Done when:** `ruff` + `pytest` green; README/`.env.example`/DEVLOG updated; the demo shows emotion on
the flagship path, correct pronunciation of an invented name, a new DJ on air, and a DJ recalling a past
story.

---

## Explicitly NOT in D9 (→ other sub-packs / phases)
- **The runtime DJ-management / control surface** (CRUD DJs + edit the grid without re-seeding) → **Phase
  E** (D9 is bible-authored + re-seed).
- **The launch-voice decision (Kokoro at scale vs flagship)** → **C6** (server track) — D9 *wires*
  emotion; C6 decides which engine ships, which is what makes emotion audible.
- **Generating the world/stories the DJ remembers** → **D3** (D9 only *recalls* the log).
- **The in-world figures + quotes a guest/soundbite voices** → **D10** (Figures & Quotes). D9.3 supplies
  the *voice + turn slot*; D10 supplies the *person + what they said*. A guest segment = D10 figure ×
  D9 voice.
- **News-desk story recurrence / output anti-repetition** → **D4 / D5** (DJ memory is in-character
  recall, distinct from those).
- **Assigning DJs to programs/dayparts (the grid)** → **D6** (D9 makes the cast extensible; D6 schedules
  it).

# GRID_V2.md — the 24-hour speech-station week (R2.0 design)

> **Status: DRAFT — awaiting operator sign-off.** Nothing in `grid.yaml` moves until this doc is
> approved (R2.0 "done when"). R2.2 implements exactly what is signed off here; R2.1 builds the
> canon/domain support listed in §8; R3.1 specs the themes listed in §7. Open questions for the
> review are collected in §10 — everything else is a concrete proposal.
>
> **What this fixes** (the 2026-07-19 audit, topics 1+6): the current day runs eight 1–2-hour
> blocks — long, slow, one register at a time. Real speech radio runs a **fixed spine of short
> fixtures**: flagships that never sit on one item, ≤30-minute named programs everywhere else,
> predictable fixture times, energy from *variation* inside the hour. This design rebuilds the
> daytime on that model while leaving the night — which already works — alone.

---

## 1. Design rules (locked by the operator, 2026-07-19 + the R2.0 spec)

1. **Flagships stay long, get fast.** `morning_currents` 07:00–09:00 and `evening_currents`
   18:00–20:00 remain 2-hour branded shows, restructured into 3–5-minute items around
   `news@:00`/`news@:30` pins (the BBC-*Today* model: 2–3 hours, never one item for long).
2. **Everything else in the daytime is a named program ≤30 minutes.** The current 1–2h verticals
   become 30-minute editions; the freed space takes **new fixtures** (§5.3).
3. **The night is exempt and unchanged** (20:15–07:00; the R2.0 energy rule: "night unchanged —
   the night is already good"). The one night-adjacent change is the 15-minute evening serial at
   20:00 (§10 Q1).
4. **Fixture discipline.** Dailies air at the same time every day (the R4 recurrence hooks depend
   on it). Hourly `news@:00` pins stay everywhere; short bulletins hourly, long bulletins inside
   the flagships plus the 30-minute Settlement Desk at midday (bulletin length becomes
   per-program in R4.2).
5. **Energy curve:** bright 07–09 → steady with bright spikes (11:00 music, midday desk) →
   chart + sport late afternoon → bright drive → calm night. `energy` on every program drives
   both delivery pace and the R1.2 register rules.
6. **Host rotation:** pairs rotate so nobody carries anything close to 6h/day (rota in §6).
7. **Length is a parameter.** Flagship items ~3–5 min, 30-min specialists ~6–8 min — via the
   R2.2 `talk_length_sec` per-program dial, never hardcoded (the Segment seam rule).

---

## 2. The day at a glance (identical all seven days)

The whole week is ONE daily spine; the only per-day variation is the five rotating vertical
windows (W1–W5) and the 15:30 weekly belt (W6) — see §3. Two 15-minute update points (Conditions
+ The Ledger) air twice daily, the real-radio weather-and-markets rhythm.

| Time | Program | What it is | Energy |
|---|---|---|---|
| 00:00–02:00 | The Deep Hours | night — unchanged | calm |
| 02:00–05:00 | The Deep Field | night — unchanged | calm |
| 05:00–07:00 | First Light | dawn handover — unchanged | steady |
| 07:00–09:00 | **Morning Currents** | FLAGSHIP — fast breakfast clock | bright |
| 09:00–09:30 | Common Ground | daily life magazine | bright |
| 09:30–10:00 | **W1** — governance & law window | rotating vertical | steady |
| 10:00–10:30 | **W2** — money & worlds window | rotating vertical | steady |
| 10:30–11:00 | The Table *(new)* | food, daily | steady |
| 11:00–11:30 | The New Signal | music — the day's arrivals | bright |
| 11:30–11:45 | Conditions *(new)* | the lanes & the sky, AM | calm |
| 11:45–12:00 | The Ledger *(new)* | markets brief, AM | steady |
| 12:00–12:30 | The Settlement Desk | the long midday bulletin + field | steady |
| 12:30–13:00 | The Commons | the midday argument — now daily | steady |
| 13:00–13:30 | The Gallery | arts, daily | steady |
| 13:30–14:00 | **W3** — making & mending window | rotating vertical | steady |
| 14:00–14:30 | **W4** — story & record window | rotating vertical | steady |
| 14:30–15:00 | **W5** — watch & thread window | rotating vertical | steady |
| 15:00–15:15 | Conditions — PM edition | the afternoon update | calm |
| 15:15–15:30 | The Ledger — the close | the markets close | steady |
| 15:30–16:00 | **W6** — the weekly belt | one weekly strand per day | varies |
| 16:00–16:30 | The Circuit | sport, daily | bright |
| 16:30–17:00 | The Count *(new)* | the daily chart show (R6) | bright |
| 17:00–17:30 | The Far Signal | today's dispatches — now daily | steady |
| 17:30–18:00 | The Mailbag | listener letters | steady |
| 18:00–20:00 | **Evening Currents** | FLAGSHIP — drive, day-so-far wrap | bright |
| 20:00–20:15 | The Serial *(new)* | the evening episode (R4 arcs) | calm |
| 20:15–22:00 | Nightfall | dusk handover — start moves 20:00→20:15 | calm |
| 22:00–00:00 | The Long Night | night — unchanged | calm |

Distinct programs on a typical day: **23** (2 flagships + ~16 short daytime fixtures + 5 night)
— the "~20 short fixtures" target of the R2 pack.

---

## 3. The rotating windows + the weekly belt

Each vertical owns **one canonical time** (predictability = the fixture rule); the weekday
pattern picks its days. Five windows × 7 days = 35 vertical editions/week, split 4+3 inside
each window pair. Sunday keeps the classic Sunday-show posture (politics + the week's watch).

| Window | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| **W1 09:30** | The Assembly | The Compact | The Assembly | The Compact | The Assembly | The Compact | The Assembly |
| **W2 10:00** | The Exchange | The Exchange | The Far Towns | The Exchange | The Exchange | The Far Towns | The Far Towns |
| **W3 13:30** | The Workshop | The Ward | The Workshop | The Ward | The Workshop | The Workshop | The Ward |
| **W4 14:00** | The Long View | The Reading Room | The Long View | The Reading Room | The Long View | The Reading Room | The Reading Room |
| **W5 14:30** | The Standing Watch | The Thread | The Standing Watch | The Thread | The Standing Watch | The Thread | The Standing Watch |
| **W6 15:30** | The Fit | The Bridge | The Relay Round | The Fit | The Relay Round | Deep Listening | The Gathering |

Editions per week: Assembly 4 · Compact 3 · Exchange 4 · Far Towns 3 · Workshop 4 · Ward 3 ·
Long View 3 · Reading Room 4 · Standing Watch 4 · Thread 3 · Fit 2 · Relay Round 2 ·
Bridge / Deep Listening / Gathering 1 each. **The Bridge, Deep Listening and The Gathering come
back off the bench** as weeklies (they were benched 2026-07-18, definitions kept — exactly for
this).

---

## 4. Tiling + pin coverage (the proof)

**168 hours:** the §2 spine tiles 00:00–24:00 with no gaps or overlaps; it runs all seven days;
the only per-day cells are W1–W6 and every cell of the §3 table is filled → the whole week is
tiled. (`default` still backstops any future editing hole.)

**Hourly news pins** — every top-of-hour crossing lands inside a program whose clock carries
`news@:00`, except 20:00 (deliberate — see §10 Q7):

| :00 | Program covering it | | :00 | Program covering it |
|---|---|---|---|---|
| 00,01 | Deep Hours | | 12 | Settlement Desk (long) |
| 02–04 | Deep Field | | 13 | The Gallery |
| 05,06 | First Light | | 14 | W4 window |
| 07,08 | Morning Currents (flagship mix) | | 15 | Conditions PM (`[news@:00, talk]`) |
| 09 | Common Ground | | 16 | The Circuit |
| 10 | W2 window | | 17 | The Far Signal |
| 11 | The New Signal | | 18,19 | Evening Currents (18:00 = day-so-far wrap) |
| 21 | Nightfall | | 22,23 | The Long Night |

Programs that start at :30/:45 never cross a top-of-hour and carry no pin — the hourly cadence
is kept by the :00-sitting shows. `news@:30` pins live only in the flagships and Morning/Evening
Currents' half-hours. **R2.2 must add the regression test:** a 15/30-minute program crossing its
pin fires it correctly (the sub-hour-program pin test named in the pack).

---

## 5. The program register

Format for each entry: hosts (lead first) · framing · clock · `break_every` / `guest_chance` ·
energy · brief. Existing programs whose **brief is unchanged from `grid.yaml` (R1.1)** say so
rather than repeating it — the diff is what the review needs. All hosts are existing cast ids
(`docs/canon/90-cast.md`); field hosts (sera/orin/zhe) auto-frame as relay dispatches wherever
they appear (the card rule, unchanged).

### 5.1 The flagships (restructured clocks, same brands)

**morning_currents — Morning Currents** · thorn + wren · ensemble
- clock: `[news@:00, talk, talk, news@:30, talk, talk]` · items **3–5 min** (`talk_length_sec`)
- break_every 6 · guest 0.3 · **bright** · brief: unchanged (R1.1 — already written for the fast
  item cadence: "move every few minutes").

**evening_currents — Evening Currents** · **kael + joss** (change — §10 Q2) · ensemble
- clock: `[news@:00, talk, talk, news@:30, talk, talk]` · items 3–5 min. The 18:00 bulletin is
  the **"day so far" wrap** (R4.2's distinct drive flavour).
- break_every 6 · guest 0.3 · **bright** · brief: unchanged in content; Thorn still reads every
  bulletin (the news desk always cuts in — anchor duty is separate from the co-host chairs).

### 5.2 News & updates (daily fixtures)

**settlement_desk — The Settlement Desk** · thorn + sera · 12:00–12:30 (was a full hour)
- clock: `[news@:00, talk, talk]` — the long midday bulletin + one field record.
- break_every 6 · guest 0.5 · steady · brief: unchanged.

**conditions — Conditions** *(NEW — the D14 slot, finally scheduled)* · zhe · solo ·
11:30–11:45 + 15:00–15:15
- clock: `[talk]` (AM) / `[news@:00, talk]` (PM) · no breaks/guests · **calm** (deliberate — the
  one daytime slot where the wide register belongs; §10 Q5).
- brief: *Relay strength, particle weather over the lanes, crossing windows opening and closing,
  the queue at the transfer points — the between-worlds weather report, from the far-edge watch.
  Someone is planning a crossing on this: give the numbers, the windows, the delays, plainly.
  A little vastness is allowed — it IS vast out there. Never bury the practical in the poetry;
  the window times come first.*
- Theme: **reuses `assets/themes/d14_conditions.mp3`** (exists, never yet aired).

**the_ledger — The Ledger** *(NEW)* · joss · solo · 11:45–12:00 + 15:15–15:30 ("the close")
- clock: `[talk]` · no breaks/guests · steady.
- brief: *The markets in ten minutes: today's prices, freight rates, a contract signed or
  defaulted, what the Exchange Houses are quoting on the morning relays. Name the cargo, the
  port, the number, the direction it moved — and who that squeezes. Never explain what a market
  is, and never pad: say the numbers and get out.*

### 5.3 The daily magazines & fixtures

**common_ground** · wren + mira · 09:00–09:30 (was an hour) · clock `[news@:00, talk, talk, talk]`
· break 5 · guest 0.6 · bright · brief unchanged.

**the_table — The Table** *(NEW)* · mira + sera · 10:30–11:00 · clock `[talk, talk, talk]`
- break 4 · guest 0.6 · steady.
- brief: *What's actually for dinner across the worlds: a harvest in or short, a galley trick
  that survives ration week, what a market stall is charging for real eggs, a festival dish and
  the argument over whose recipe is right — with Sera recording from the kitchens and stalls.
  Food is budget, homesickness and pride before it is culture. Never rhapsodise about cuisine —
  it's dinner, and somebody had to queue for it.*

**the_commons** · joss + mira · **now daily** 12:30–13:00 · clock `[talk, talk]` · break 5 ·
guest 0.5 · steady · brief: unchanged in spirit — one wording change for R2.2: the question is
pulled from **the day's** stories (this morning's bulletins), not "the week", so the midday
argument chases what the newsroom just aired.

**the_gallery** · mira + orin · 13:00–13:30 (was an hour) · clock `[news@:00, talk, music, talk]`
· break 5 · guest 0.8 · steady · brief unchanged.

**the_circuit** · kael + sera · 16:00–16:30 (was an hour) · clock `[news@:00, talk, talk, talk]`
· break 5 · guest 0.6 · bright · brief unchanged.

**the_count — The Count** *(NEW — the R6 chart show)* · orin · solo · 16:30–17:00
- clock: `[music, music, music]` now; R6.1 replaces with the `chart` countdown step.
- break 4 · no guests · **bright**.
- brief: *The day's chart, counted down and taken personally: who climbed, who fell, the new
  entry in off the relays, the holdout that will not leave the top five. Chart movement is sport
  — call it like sport, with the countdown stings and the day's chart story. Never play it cool:
  if a track jumped six places, that is drama, treat it as drama.*
- Needs the R3.1 **chart-countdown sting set** + its own theme.

**the_far_signal** · sera + zhe · **now daily** 17:00–17:30 · clock `[news@:00, talk, talk]` ·
guest 0.7 · steady · brief unchanged — "today's post from the worlds", the pre-drive dispatch
round.

**the_new_signal** · orin · **moves 17:00 → 11:00–11:30** · clock `[news@:00, music, music, music]`
· bright · brief unchanged (the mid-morning music spike).

**the_mailbag** · vell + wren · 17:30–18:00 (unchanged slot) · clock `[talk, talk]` · guest 0.4 ·
steady · brief unchanged.

**the_serial — The Serial** *(NEW)* · the-archivist · solo · 20:00–20:15 nightly
- clock: `[talk]` · no breaks/guests · **calm**.
- brief: *Fifteen minutes of the continuing story: one episode a night, one thread of the
  worlds' long arcs, told by the Archivist before the night begins — a real serial, with a
  cliff at the end and yesterday honoured at the start. One breath of recap, no more; trust the
  listener to have been here. Never wrap the story up neatly — the point of a serial is that
  tomorrow exists.*
- Source: until R4 lands, the writers' room carries it from the brief + story log; R4.0's
  long-arc machinery becomes its proper feed (§10 Q6). Needs an R3.1 theme.

### 5.4 The rotating verticals (all become 30-minute editions)

All ten keep their **R1.1 briefs unchanged** and their hosts, shrink to 30 minutes, and air at
one canonical time (§3). Clocks: `[news@:00, talk, talk, talk]` for the :00-start windows
(W2/W4), `[talk, talk, talk]` for the :30-start windows (W1/W3/W5). `break_every` drops to 4
(one sparse break per edition); `guest_chance` unchanged per program.

| Program | Window | Days | Hosts (unchanged) |
|---|---|---|---|
| the_assembly | W1 09:30 | Mon Wed Fri Sun | thorn + joss |
| the_compact | W1 09:30 | Tue Thu Sat | joss + sera |
| the_exchange | W2 10:00 | Mon Tue Thu Fri | wren + joss |
| the_far_towns | W2 10:00 | Wed Sat Sun | sera + mira |
| the_workshop | W3 13:30 | Mon Wed Fri Sat | wren + joss |
| **the_ward** *(NEW)* | W3 13:30 | Tue Thu Sun | **wren + mira** |
| the_long_view | W4 14:00 | Mon Wed Fri | joss + the-archivist |
| the_reading_room | W4 14:00 | Tue Thu Sat Sun | mira + the-archivist |
| the_standing_watch | W5 14:30 | Mon Wed Fri Sun | thorn + zhe |
| the_thread | W5 14:30 | Tue Thu Sat | sera + joss |

**the_ward — The Ward** *(NEW — health & medicine)* · wren + mira · interview posture, guest 0.7
- brief: *Medicine at relay distance: a clinic short of a drug that is three crossings away, the
  physician-correspondence network arguing a diagnosis across the lag, an outbreak scare walked
  back, a treatment that works and what it costs. Start from the patient or the medic, and get
  the practical answer on air — with a physician guest pressed for specifics. Never speculate a
  diagnosis on air, never mystify medicine, and never turn someone's illness into a metaphor.*
- Canon: **needs `docs/canon/54-health.md` + the `health` tick domain (R2.1)** — without it the
  show starves (the D9.4 sports lesson).

### 5.5 The weekly belt (W6, 15:30)

**the_fit — The Fit** *(NEW — style & dress)* · mira + orin · Mon + Thu · clock
`[talk, talk, talk]` · break 4 · guest 0.6 · **bright**
- brief: *What people actually wear and make across the worlds: dock-crew workwear that became a
  fashion, festival dress and who gets to wear it, a fabric shortage rippling down the lanes, a
  tailor's feud, what the well-dressed of Meridian are being laughed at for this season — with
  Orin's field notes from the concourses. Clothes are how people manage weather, work and pride.
  Never sneer at anyone's clothes, and never do trend-speak — name the garment, the maker, the
  price.*
- Canon: **needs a style section (extend `50-daily-life.md` or a small `56-style.md`) + a
  `style` domain (R2.1)**.

**the_relay_round — The Relay Round** *(NEW — the quiz)* · kael + wren · Wed + Fri · clock
`[talk, talk]` · guest 0 · **bright**
- brief: *The station's game: rounds of questions sent in by listener settlements — their
  history, their lanes, their scores, their kitchens — with the hosts competing and the score
  kept out loud. It is a real contest: gloat, groan, dispute a ruling, honour the settlement
  that stumped everyone. Never let a question become a discussion — answer, score, next; the
  game has pace or it has nothing.*
- Needs the R3.1 **quiz sting** + theme. (Inclusion itself is §10 Q3.)

**Returning weeklies** (off the bench, definitions already in `grid.yaml`, briefs unchanged):
- **the_bridge** · joss + mira · Tue — culture & history magazine. Clock trims to
  `[talk, music, talk]` (no :00 crossing at 15:30).
- **deep_listening** · mira · Sat — the curated half-hour. Clock `[music, music, music]`.
- **the_gathering** · the-archivist + vell · Sun — faith, custom, the open questions. Clock
  `[talk, talk]`.

### 5.6 The night (unchanged)

`nightfall` (start moves 20:00 → **20:15**, otherwise untouched), `long_night`, `deep_hours`,
`deep_field`, `first_light` — hosts, clocks, briefs, energy all as today. The night was
explicitly judged good; R2 does not touch it.

---

## 6. The host rota (worst-day loads)

Nobody exceeds ~4.5 on-air hours on any day (rule: well under 6). Field hosts' totals are
dispatch-framed, not live hours. Thorn's flagship load *drops* (hands the drive chair to
Kael+Joss, keeps every bulletin).

| Host | Daily fixtures | Rotating appearances | Worst day ≈ |
|---|---|---|---|
| thorn | Morning Currents 2h · Desk ·  bulletins all day | Assembly, Standing Watch | **3.5h** (Mon/Wed/Fri) |
| wren | Morning Currents 2h · Common Ground · Mailbag | Exchange, Workshop, Ward, Relay Round | **4.0h** (Mon/Fri) |
| joss | Evening Currents 2h · Ledger ×2 · Commons | Assembly, Compact, Exchange, Workshop, Long View, Thread | **4.5h** (Mon) |
| kael | Evening Currents 2h · Circuit | Relay Round | **3.0h** |
| mira | Common Ground · Table · Commons · Gallery | Far Towns, Ward, Reading Room, Fit, Deep Listening | **3.0h** |
| vell | Mailbag · night (Nightfall, Long Night) | Gathering (Sun) | night spine, unchanged |
| the-archivist | The Serial · night (Deep Hours…) | Long View, Reading Room, Gathering | ~3h + night, unchanged |
| sera *(field)* | Desk · Table · Far Signal | Compact, Far Towns, Thread, Circuit | dispatches |
| orin *(field)* | New Signal · Count · Gallery | Fit | dispatches |
| zhe *(field)* | Conditions ×2 · Far Signal · night (Deep Field) | Standing Watch | dispatches |

Joss is the heaviest and is flagged for the review (§10 Q2) — the drive chair is the lever if
4.5h reads as too much.

---

## 7. Theme / jingle status (→ the R3.1 batch-3 list)

**Existing bespoke themes cover every current program** (`assets/themes/<program_id>.mp3` —
verified present for all §5.1–5.6 continuing shows, including the returning bench trio). The
R3.0 audit must re-verify placement end-to-end after R2.2.

| New program | Theme status |
|---|---|
| conditions | **REUSE** `assets/themes/d14_conditions.mp3` — exists, no new clip |
| the_table | needs R3.1 theme |
| the_ward | needs R3.1 theme |
| the_fit | needs R3.1 theme |
| the_count | needs R3.1 theme **+ the chart-countdown sting set** |
| the_ledger | needs R3.1 theme (short desk sting-style) |
| the_serial | needs R3.1 theme |
| the_relay_round | needs R3.1 theme **+ a quiz sting** |

Until batch 3 lands, new programs fall back per `placement.program_theme_segment` (format
fallback) — acceptable on air, flagged in the R3.0 mapping table. The three A4 sweepers must be
re-checked against the new energy range (R3.1's existing to-do).

---

## 8. Canon + domain support (→ the R2.1 work list)

| Program | Feeds on | Gap → R2.1 |
|---|---|---|
| the_ward | — | **`docs/canon/54-health.md`** (clinics, the physician network, illness across the lag) + `DOMAINS += health` + cast affinity tags |
| the_fit | 50-daily-life (thin) | **style section** (extend 50 or new `56-style.md`) + `DOMAINS += style` (only if the file lands) |
| the_table | 50-daily-life §Food | extend §Food if generation runs thin (check during R2.1) |
| conditions | 80-cosmos, 78-communication | none — covered |
| the_ledger | 35-economy | none — covered |
| the_count / new_signal | 70-music + `config/tracks.yaml` | R6.0 track batch (parallel, human) |
| the_serial | 65-arts + the R4 story arcs | R4.0 (machinery, not canon) |
| the_relay_round | the whole bible (question fodder) | none — the bible IS the quiz bank |

All other verticals keep their existing cornerstone coverage (strong per the R2 pack audit).

---

## 9. Implementation notes for R2.2 (so the YAML lands exactly as signed off)

1. **`talk_length_sec` per program** (or reuse `length_target` plumbing): flagships ~3–5 min
   items; 30-min shows ~6–8; 15-min shows ~3–5. A parameter, never a constant.
2. **Sub-hour pin regression test**: a 30-min program sitting on :00 fires `news@:00` exactly
   once; a :30-start program fires none.
3. **Slot grammar**: 15-minute ranges (`11:30-11:45`) are legal (`HH:MM` loader) — add a loader
   test at that granularity.
4. Same program in two slots (conditions/ledger AM+PM) is already supported (one program, many
   slots) — the PM edition's clock difference means conditions needs either two program ids
   (`conditions`, `conditions_pm`) or pin-tolerant clock reuse; **prefer one id + the
   `[news@:00, talk]` clock**, since the AM slot simply never crosses a pin.
5. **Nothing is deleted**: replaced hour-long slots just re-tile; every current program survives
   (D12.4 bench discipline still available if the operator cuts anything at review).
6. Update every changed/new brief per §5; keep briefs in `grid.yaml` beside programs
   (git-diffable, E1.2 round-trips them).
7. After the YAML lands: tiling test, `make console` spot-check, the D11 24h simulated top-up,
   R3.0 placement audit re-run.

---

## 10. Open questions for sign-off (answer these; everything else builds as written)

1. **The Serial at 20:00–20:15**, trimming Nightfall to 20:15 — the classic evening-drama slot,
   leading beautifully into the night's register. Alternative if the night must stay
   byte-identical: 13:45–14:00 (the lunchtime-drama slot); the 20:00 slot is recommended.
2. **Evening Currents presented by Kael + Joss** (Thorn keeps breakfast + every bulletin). This
   is the pair-rotation fix — without it Thorn carries 4.5h+ daily. Alternative pairs: wren+joss
   (pushes Wren to ~5h) or mira+joss.
3. **The Relay Round (quiz), 2×/week** — new format risk (a game needs pace the room hasn't done
   before), but the biggest single energy win in the belt. Cuttable without a tiling hole
   (replace with a third Fit / second Bridge edition).
4. **The Table daily** — food every day leans hard on 50-daily-life §Food; if that reads thin in
   practice, drop to 3×/week and give the freed days to the belt. Recommend starting daily.
5. **Conditions voiced by Zhe** (field → auto-framed as a far-edge dispatch, `calm` register
   with licensed vastness) — vs a plain station read by Thorn. Recommend Zhe: it makes the
   weather slot canon-true and gives the D14 theme its intended atmosphere.
6. **The Serial before R4**: schedule from day one (brief-driven continuing story, upgraded to
   the R4 long-arc feed when R4.0 lands) — vs holding the slot empty (Nightfall keeps 20:00)
   until R4. Recommend day one: the fixture habit matters more than the source purity.
7. **No 20:00 bulletin** (The Serial takes the top of the hour; 18:00–20:00 was wall-to-wall
   news, next bulletin 21:00 inside Nightfall). Confirm this is acceptable.
8. **Names**: The Ward · The Fit · The Table · The Count · The Ledger · Conditions · The Serial ·
   The Relay Round — all final-at-review per the pack.

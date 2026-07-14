# 95-events.md — the world timeline

> Cornerstone file: dated, hand-seeded occurrences. The `## Events` section projects
> to `events` rows (each `### ` entry is one event; `In-world datetime` is required).
> These are `source='seed'` events — the nightly world tick (D3) writes its own
> `source='tick'` events here too, and a `seed-canon` refresh leaves those intact.
> See `docs/canon/README.md` for conventions.

## Events — the world timeline

Dated, progressing occurrences the DJs reference on air. The seed loads each `### ` entry below as
an `events` row; B2 computes its live status and relative phrasing ("in five days" → "yesterday")
from its in-world datetime and the world clock. The in-world year is `real year + 600` (so a date
in `2626` is the in-world face of `2026`).

**Roll-forward policy:** a recurring event (annual / seasonal / scheduled) carries the date of its
*next* instance — once an instance passes, bump the year here and re-seed. Rarer cycles (the
decennial Conclave, the eleven-year eclipse) keep a just-passed date while it is still fresh DJ
material, then roll to the next occurrence. The `Status:` field is a cadence label (annual,
seasonal, memorial…) — the *live* upcoming/today/past status is computed from the datetime at
read time, never from this field.

### Lumen Festival

- **In-world datetime:** 2627-06-24T20:00
- **Status:** annual
- **Tags:** festival, lights, music, annual
- **Body:** The settlements' great annual festival of light. Every world kindles its lamps at the same shared hour, so that across the dark between them the whole of settled humanity glows at once — and the station carries the night through, world to world, as the lights come up.

### Founding Remembrance

- **In-world datetime:** 2626-01-01T00:00
- **Status:** annual
- **Tags:** founding, remembrance, history, newyear, ritual, silence, memory
- **Body:** The turn of the year is given over to the first crossings — the generation-ships that carried humanity into the dark, ages ago. For one hour at midnight, the station goes quiet — no music, no talk, only the carrier wave humming in the dark. Listeners gather in their homes, some in groups, most alone, to remember the ones who crossed the void without knowing what waited. At 01:00, the first notes of the new year rise: always the same piece, an Earth-origin composition called "The Long Way Round," played on instruments older than the settlements themselves.

### The Meridian Eclipse

- **In-world datetime:** 2637-03-15T14:30
- **Status:** upcoming
- **Tags:** eclipse, meridian, astronomy, rare, darkness, wonder, alignment
- **Body:** Once every eleven years, Meridian's twin moons align to swallow its sun completely. The world goes dark for seven minutes in the middle of the afternoon. Ships in orbit adjust their schedules to watch from above. The station broadcasts a special programme: field recordings from previous eclipses, messages from listeners who remember being children during the last one, and a live feed from the surface as the shadow crosses. It is considered bad luck to speak during the minutes of darkness.

### Cold Harbor Thaw

- **In-world datetime:** 2627-04-22T06:00
- **Status:** seasonal
- **Tags:** cold, harbor, thaw, spring, ice, water, renewal, hardship, endurance
- **Body:** The ice world Cold Harbor enters its brief warm season, when the frozen sea cracks and the first ships can move between the settlements in months. The station runs a week of programmes from Cold Harbor — music recorded in ice caves, interviews with the people who live through the long night, the sounds of the thaw itself. It is a time of reunions and of mourning those who did not survive the dark months.

### Relay Maintenance Window

- **In-world datetime:** 2627-05-08T02:00
- **Status:** scheduled
- **Tags:** relay, maintenance, silence, interruption, repair, infrastructure, patience
- **Body:** Every settlement year, the relay network undergoes coordinated maintenance, timed and sequenced by the Relay Authority though the hands doing the work are whoever is nearest each node. For six hours, the station cannot broadcast to the farther worlds — only the nearest relays remain in range. The DJs fill the time with archival programmes, pre-recorded features, and long-form music. Listeners in the far settlements know to expect silence and use the hours for sleep or local gathering. It is a reminder of how fragile the thread is.

### The Archivist's Conclave

- **In-world datetime:** 2626-07-12T10:00
- **Status:** decennial
- **Tags:** archivists, conclave, knowledge, preservation, memory, gathering, scholars
- **Body:** Once a decade, the keepers of the settlements' records gather on neutral station-space to compare archives, reconcile divergent histories, and decide what to preserve and what to let fade. The station broadcasts selected sessions — not the technical work, but the stories the archivists tell each other, the memories they argue about, the moments when they disagree about what really happened. It is the closest thing the settlements have to a shared history lesson.

### Ship Naming Day

- **In-world datetime:** 2626-09-03T16:00
- **Status:** annual
- **Tags:** ship, naming, tradition, children, hope, future, continuity
- **Body:** On the old calendar, this was the day the first generation-ships were christened. Now it is when children born that year receive their ship-names — the tradition of naming offspring after vessels, a practice that never died out even as the ships themselves became museums or scrap. The station reads the names aloud, world by world, for hours. Parents listen to hear their child's name in the voice of the dark between.

### The Ashfall Minute

- **In-world datetime:** 2626-11-17T00:00
- **Status:** memorial
- **Tags:** ashfall, memorial, tragedy, silence, loss, remembrance, history
- **Body:** Generations ago, the volcanic world Ashfall suffered an eruption that buried its largest settlement. The station had been broadcasting to them moments before. Every year, at the hour the signal died, the station observes a minute of silence, then plays the last recording received from Ashfall — a weather report, routine, cut off mid-sentence. It is a reminder that the void takes as well as connects.

### New Year's Relay Chorus

- **In-world datetime:** 2626-12-31T23:59
- **Status:** annual
- **Tags:** newyear, chorus, relay, greetings, lag, unity, simultaneity, hope
- **Body:** As the year turns, the station opens its frequencies to listener messages and broadcasts them in the order received, creating a cascade of greetings that arrives at each world minutes or hours late, depending on distance. The result is a chorus of belated well-wishes, people hearing "happy new year" from strangers who spoke it before they did. It is the sound of the settlements breathing together across the dark.

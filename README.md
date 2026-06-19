<p align="center"><img src="assets/brand/wordmark-horizontal.png" alt="Settlement Radio" width="420"></p>

<p align="center"><em>Late-night radio from the far future.</em></p>

Settlement Radio is an always-on, AI-voiced radio station that broadcasts from the settled worlds
of the late 27th century — six hundred years from now. It knows what time it really is, reflects
it in-universe, and keeps you company across the dark with news from the colonies, music for the
small hours, and presenters who carry the same conversation night after night. It's a tribute to
the science-fiction authors who taught a generation to imagine a kinder future.

It's also being built almost entirely by AI agents — and in the open.

## Listen
- 🎧 Live stream: Cooming soon
- 🌍 [settlementradio.com]

## What it is
- A continuous, time-aware broadcast — generated ahead of air, played out 24/7.
- Persistent AI presenters with consistent personalities and a shared, version-controlled world.
- All writing, reasoning, and world-simulation by **Claude**; voice by an external TTS; the whole
  system built with **Claude Code**.

## Built in the open with Claude Code
Settlement Radio is an experiment in handing a creative production to AI agents: Claude Code wrote
the pipeline, the world engine, and the writers'-room that scripts each segment in character. The
build log lives in [`docs/DEVLOG.md`](docs/DEVLOG.md); the design in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## How it works (in brief)
Generation and playout are decoupled in time: a writers'-room of Claude agents drafts segments
ahead of air from a living world-state (canon, cast, an event timeline, and a world clock running
+600 years), those segments are voiced and stored, and a lightweight playout layer streams them
around the clock. Segment length is a parameter, so the same pipeline serves an overnight block or
a near-live drop. Details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## A note on what you're hearing
Settlement Radio is a **work of fiction, generated with AI**. The presenters are not real people;
the news from the future is invented. AI generation is disclosed on the stream and the player.

## License
- **Code:** Apache-2.0 — see [`LICENSE-CODE`](LICENSE-CODE).
- **Creative world** (lore, scripts, canon): Creative Commons Attribution-ShareAlike 4.0 — see
  [`LICENSE-CONTENT`](LICENSE-CONTENT). Build in this universe; share alike; credit Settlement Radio.

## Support & follow
☕ [Ko-fi] · ✦ [GitHub Sponsors] · 🛰️ [X] · ✉️ [newsletter]

<p align="center"><sub>For the authors who imagined us here.</sub></p>
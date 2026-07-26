# Settlement Radio — web

The Settlement Radio public site (Next.js App Router + TypeScript + Tailwind), deployed to
[settlementradio.com](https://settlementradio.com) via Vercel (**Root Directory = `web`**). The
Python station backend lives at the repo root and is never built or deployed by Vercel.

Routes (all three station pages share one shell: masthead, nav, and a footer carrying the letters
box, the follow links and the AI disclosure):

- **`/`** — **the switch** (R7.4). With `NEXT_PUBLIC_COMING_SOON` on (the default) it's the A2
  coming-soon screen; set it to `false` and it becomes the player. See *The front-door flag* below.
- **`/listen`** — the player (R7.1): press play, see what you're hearing. The on-air card (programme,
  tagline, host signal marks, track lore), the transport, and the up-next rail, all driven by the
  station's public feeds. Redirects to `/` once the flag is off, so there's one canonical home.
- **`/schedule`** — Programmes (R7.2): **today** as a rail (time · name · tagline · hosts, with the
  current show lit and scrolled into view) and **the week** as a programme guide — one row per time
  band, one column per day, so the fixed spine and the rotating specialist windows are visible at a
  glance. Pick any show in the week view for its tagline, hosts and next airing.
- **`/voices`** — The DJs (R7.3): one card per host — their signal mark in their own accent tone,
  role line, the operator-authored public bio, the shows they present with next-on-air times, and a
  field-correspondent badge for the three who report across the relay lag. **No portraits, ever**
  (canon: listeners know the presenters only by their voices).

This app is **public and read-only**. The operator/admin surface is NOT here — it's the private,
VPS-only panel in the Python backend (`make panel`).

## The front-door flag (R7.4)

One switch decides whether the world sees the station or the waiting room:

| `NEXT_PUBLIC_COMING_SOON` | `/` | `/listen` | `/schedule`, `/voices` |
|---|---|---|---|
| `true` (default, safe) | coming-soon screen | the player, `noindex` | live, `noindex` |
| `false` | **the player** | 307 → `/` | live, indexable |

- **Default is the safe state.** The flag is only off when it says exactly `false`, so a missing or
  mistyped variable can never accidentally advertise a stream that isn't running.
- **Pre-launch, the station pages still work** — unlinked from the coming-soon screen and marked
  `noindex`, so you can preview and share them by hand without Google announcing the launch for you.
- **The redirect is deliberately temporary (307)**, not permanent: flipping the flag back must not be
  defeated by a cached 308 in everyone's browser.
- It's a build-time value (`NEXT_PUBLIC_`), so **flipping it means a redeploy** — which is the point.
  Flipping the front page should be an act, not an accident.

## Deploying (Vercel)

Root Directory = `web`. Set these in **Project → Settings → Environment Variables**, then redeploy
(all are build-time; changing one without redeploying changes nothing):

| Variable | Production value | Notes |
|---|---|---|
| `NEXT_PUBLIC_COMING_SOON` | `true` until launch, then `false` | the front-door flag above |
| `NEXT_PUBLIC_STREAM_URL` | the C7 stream URL | empty ⇒ the play control is disabled and says so |
| `NEXT_PUBLIC_FEEDS_BASE_URL` | where the C7 box serves the JSON feeds | needs CORS for this domain |
| `NEXT_PUBLIC_PLAUSIBLE_DOMAIN` | `settlementradio.com` | empty ⇒ no analytics script at all |
| `BUTTONDOWN_API_KEY` | the list key | **server-side only**, never `NEXT_PUBLIC_` |
| `NEXT_PUBLIC_FEED_POLL_SEC` / `NEXT_PUBLIC_SLOW_FEED_POLL_SEC` | leave unset | defaults 20s / 300s |
| `NEXT_PUBLIC_SUPPORT_URL` | the Ko-fi link at M1 | hidden while unset |
| `NEXT_PUBLIC_VOICE_SAMPLES` | unset | `true` only once clips exist |

Launch order that never shows a dead player: **C7 stream up → feeds reachable with CORS → set the
stream/feeds/Plausible vars → redeploy and check `/listen` → only then set `COMING_SOON=false` and
redeploy again.**

## Develop

```bash
cd web
npm install   # first time only
cp .env.example .env.local   # then fill in BUTTONDOWN_API_KEY
npm run dev   # http://localhost:3000
```

### Seeing the player with something on air

`npm run dev` alone gives you `/listen` with its no-feed fallback (a static on-air card, the play
control disabled) — correct, but dull. To see it populated, serve the station's feeds **with CORS**
from the repo root in a second terminal and point the app at them:

```bash
# terminal 1 (repo root) — feeds on :8099, with a demo "now" built from the real grid
make demo-feeds            # add REAL=1 to serve segments/ as-is instead

# terminal 2
cd web && NEXT_PUBLIC_FEEDS_BASE_URL=http://127.0.0.1:8099 npm run dev
```

Then open <http://localhost:3000/listen>. The demo now-playing feed exists because a dev box has
run no scheduler top-up, so the real `nowplaying.json` correctly says nothing is on air.

To actually **hear** it, run the real local stream and point the player at it:

```bash
# terminal 1 (repo root) — generates segments and serves Icecast (costs Claude + TTS)
make air
# terminal 2 (repo root)
make demo-feeds REAL=1
# terminal 3
cd web && NEXT_PUBLIC_FEEDS_BASE_URL=http://127.0.0.1:8099 \
  NEXT_PUBLIC_STREAM_URL=http://127.0.0.1:8000/settlement.mp3 npm run dev
```

## Email signup (Buttondown)

The form posts to the `app/api/subscribe` route handler, which adds the email to the
[Buttondown](https://buttondown.com/) list using the server-side `BUTTONDOWN_API_KEY` (never
exposed to the client). The route validates the email, drops bots via a hidden honeypot field, and
maps Buttondown's responses to `subscribed` / `already_subscribed` / error states the form shows.
Set `BUTTONDOWN_API_KEY` in `.env.local` locally and as a Vercel env var for production.

## Brand foundation

- **Colors** (Tailwind theme tokens in `src/app/globals.css`): `night` `#081B45`, `amber`
  `#F2C04D`, `neutral` `#F4F1EB` — use as `bg-night`, `text-amber`, `text-neutral`, etc.
- **Font:** Inter, loaded via `next/font` in `src/app/layout.tsx` (`--font-inter` → `font-sans`).
- **Favicon:** wired via the App Router convention — `src/app/favicon.ico` + `src/app/icon.svg`
  (Next emits the `<link>` tags automatically).
- **Assets** in `public/` (copied from `assets/brand/`): `beacon-mark.svg` (transparent amber
  roundel for the night field), `wordmark-horizontal.svg` (recolored for dark backgrounds),
  `og-image.png` (stacked lockup on night field, for the social card in A2-T4).

### The player's design language (R7.1)

"**A lit window seen across the dark**" — the page is mostly dark, vast and calm, with ONE warm
glowing focus: the on-air card. Three helper classes in `globals.css` carry it, all pure CSS:

- `.lit-window` — the card's warm corner-lit gradient. It stays warm even when you're not
  listening (the station is on air regardless); pressing play turns the lamp *up* (a brighter border
  and a wider glow), it doesn't switch it on.
- `.starfield` — a few faint stars, positioned at the edges of the field so they never read as dust
  in the middle of the text, plus the warm wash the card throws up into the night.
- `.tape-grain` — warm analog, not sterile dashboard: an SVG-noise overlay at 4.5% opacity.
- `animate-signal` (theme keyframes) — the VU pulse in `SignalMeter`, which sits on a baseline rule
  so its idle state reads as "a meter at rest". All motion is disabled under
  `prefers-reduced-motion`.

**DJs are voices, not faces** (canon: listeners know only their voices) — so there are no portraits,
ever. Each host gets an abstract waveform **signal mark** (`lib/hostMark.ts` + `components/HostMark`)
whose accent tone and bar heights are hashed from their name: deterministic (so server and client
agree, and a host's mark never changes), and no new asset to author when the cast grows.

**The transport sits above the on-air card on purpose.** The card changes height as the air changes
(a music slot carries track lore, a talk slot doesn't); below it, the play/stop control would move
under the listener's cursor at every programme change — measured at 161px during R7.1 verification.

**Two clocks, never one** (R7.2). The feeds are re-read on a timer (`POLL_SECONDS` for now-playing,
`SLOW_POLL_SECONDS` for the schedule), but anything that depends on *when it is* — the on-air
highlight, the dimming of finished shows — is recomputed from the LOCAL clock every 30s. So the
page keeps up with the air without asking the station for anything, and the highlight moves with no
reload. Times are always the feeds' naive strings sliced for display; `new Date()` is used only to
compare instants (`lib/schedule.ts`), never to re-zone a printed time.

**The listener's day, not the feed's.** `dayFor()` picks the published day matching the viewer's own
date rather than `days[0]`, so a page left open across midnight — or a feed a few minutes stale —
still shows the right rail with the right show lit.

### Voice samples on /voices (R7.3, off by default)

Set `NEXT_PUBLIC_VOICE_SAMPLES=true` and drop **operator-curated** clips (5–10s) at
`web/public/voices/<host-id>.mp3` — `vell.mp3`, `the-archivist.mp3`, and so on (the id is the one in
`djs-public.json`). Never publish a generated segment here: this is a chosen introduction, not a
sample of the air. Hosts without a clip show no control at all — the card probes the file's metadata
and hides the button when it 404s — so enabling the flag with two clips recorded is safe.

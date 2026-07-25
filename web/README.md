# Settlement Radio — web

The Settlement Radio public site (Next.js App Router + TypeScript + Tailwind), deployed to
[settlementradio.com](https://settlementradio.com) via Vercel (**Root Directory = `web`**). The
Python station backend lives at the repo root and is never built or deployed by Vercel.

Routes:

- **`/`** — the coming-soon screen (A2) with the email signup. Still the front page: the public
  stream (C7) isn't up yet. R7.4 adds the nav and the `COMING_SOON` flag that flips `/` to the player.
- **`/listen`** — the player (R7.1): press play, see what you're hearing. The on-air card (programme,
  tagline, host signal marks, track lore), the transport, and the up-next rail, all driven by the
  station's public feeds.

This app is **public and read-only**. The operator/admin surface is NOT here — it's the private,
VPS-only panel in the Python backend (`make panel`).

## Develop

```bash
cd web
npm install   # first time only
cp .env.example .env.local   # then fill in BUTTONDOWN_API_KEY
npm run dev   # http://localhost:3000
```

### Running the player against real feeds, locally

The player reads the station's JSON feeds cross-origin, so serve them with a CORS header and point
the app at them. From the repo root, with the backend's `segments/` populated (`make public-feeds`):

```bash
# 1. serve the feeds with CORS on :8099
.venv/bin/python - <<'EOF'
import http.server, functools
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()
http.server.ThreadingHTTPServer(("127.0.0.1", 8099),
    functools.partial(H, directory="segments")).serve_forever()
EOF

# 2. point the app at them (any mp3 URL stands in for the stream while C7 is unbuilt)
cd web && NEXT_PUBLIC_FEEDS_BASE_URL=http://127.0.0.1:8099 \
  NEXT_PUBLIC_STREAM_URL=http://127.0.0.1:8099/some-track.mp3 npm run dev
```

Then open <http://localhost:3000/listen>. With no feed URL set the page still works — it shows a
static "Settlement Radio" on-air card and (if a stream URL is set) still plays.

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

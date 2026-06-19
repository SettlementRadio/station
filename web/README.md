# Settlement Radio — web

The Settlement Radio coming-soon site (Next.js App Router + TypeScript + Tailwind), deployed to
[settlementradio.com](https://settlementradio.com) via Vercel (**Root Directory = `web`**). It grows
into the audio player + studio in Phase C. The Python station backend lives at the repo root and is
never built or deployed by Vercel.

## Develop

```bash
cd web
npm install   # first time only
cp .env.example .env.local   # then fill in BUTTONDOWN_API_KEY
npm run dev   # http://localhost:3000
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

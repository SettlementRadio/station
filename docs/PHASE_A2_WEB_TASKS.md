# PHASE_A2_WEB_TASKS.md — Coming-soon site (the web app, v0)

A small, branded coming-soon page deployed to **settlementradio.com**, built as the Next.js app
that later grows into the web player. Simple now; no throwaway. Runs independently of the Python
station, so A2 and Phase B don't block each other. Work one task at a time, show + verify, stop.

## Repo & deploy shape (decided)
- **Monorepo, same repo.** The Python station stays at the root (`src/`, `config/`, etc.). The
  web app lives in a new top-level **`/web`** folder as its own Next.js project.
- **Vercel deploys only `/web`** — in the Vercel project, set **Root Directory = `web`**. The
  Python backend is never built or deployed by Vercel.
- Brand master assets stay in `assets/brand/`; the web copies the few it needs into `web/public/`.

## Brand tokens (use exactly)
- Colors: **Night Field `#081B45`** (bg) · **Signal Amber `#F2C04D`** (mark/accents) ·
  **Warm Neutral `#F4F1EB`** (light text / light sections).
- Logo: beacon **avatar mark** + **horizontal wordmark** (from `assets/brand/`). Favicon: the
  simplified `favicon/` set.
- Type: use the brand system's typeface if `tokens/` names one; otherwise a clean humanist sans
  (e.g., Inter) via `next/font`. Calm and readable, never techno/display.
- Mood: a single quiet night-field screen, warm amber mark, generous space — "a light on in the
  dark," not a busy landing page. Avoid default-template look (no stock gradients/hero clichés).

## Copy (paste, STATION voice)
- H1: **Settlement Radio**
- Tagline: *Late-night radio from the far future.*
- Body: *Broadcasting soon from the settled worlds of the late 27th century — news, music, and
  company across the dark. Leave your signal and we'll tell you when we're on air.*
- Disclosure (small, always present): *A work of fiction, written and voiced with AI — a tribute
  to the science fiction that imagined us here.*
- Follow line: links to X, GitHub, newsletter.

---

## A2-T0 — Scaffold the web app
**Do:** create `/web` as a Next.js (App Router) + TypeScript + Tailwind project. Confirm it runs
locally (`npm run dev` in `/web`). Add a `web/README.md` one-liner.
**Done when:** the default app serves locally from `/web`; root Python project is untouched.

## A2-T1 — Brand foundation
**Do:** copy the needed assets into `web/public/` (favicon set, `wordmark-horizontal`, the beacon
mark, and an OG share image — the stacked lockup on night field). Add the three brand colors as
Tailwind theme tokens; load the brand font via `next/font`; wire the favicon.
**Done when:** Tailwind classes for `night`/`amber`/`neutral` work and the favicon shows in the tab.

## A2-T2 — Build the coming-soon page
**Do:** in `app/page.tsx`, build one centered, responsive screen on the Night-Field background:
beacon mark + wordmark, the tagline, the body copy, the email signup (T3), the disclosure line,
and the follow links. Mobile-first; fast; accessible (real headings, labelled input, good
contrast — amber on night passes, but check small text).
**Done when:** the page looks on-brand and reads well on phone and desktop.

## A2-T3 — Email signup (no database)
**Do:** sign up for **Buttondown** (free) as the list. Build a server route
`app/api/subscribe/route.ts` that POSTs the email to Buttondown's API using a **server-side env
key** (never expose it client-side). Client form calls the route; show clear success / error /
"already subscribed" states; add basic email validation + a honeypot field for spam.
**Done when:** submitting an email adds it to Buttondown and the UI confirms it. (Any hosted form
provider works if you prefer — Buttondown is the default since it's your newsletter surface too.)

## A2-T4 — Metadata & social card
**Do:** set the page `<title>` and meta description (include the fiction/AI note), Open Graph +
Twitter card tags, and the branded OG image so shared links render a proper card.
**Done when:** pasting the URL into a link-preview checker shows the branded card + title.

## A2-T5 — Deploy to Vercel + point the domain
**Do:** connect the repo to a Vercel project with **Root Directory = `web`**; add the Buttondown
key as a Vercel env var; deploy. Then point **settlementradio.com** at Vercel (apex `A` record +
`www` `CNAME` per Vercel's instructions). **Do NOT touch the Microsoft mail records**
(MX / SPF / DKIM / autodiscover) — only add/adjust the web records, so `hello@settlementradio.com`
keeps working.
**Done when:** https://settlementradio.com serves the page over HTTPS and email still delivers.

## A2-T6 (optional) — Analytics
**Do:** enable Vercel Web Analytics (one toggle) to see visits and signup conversions.
**Done when:** the dashboard records a visit.

## A2-T7 — Note the monorepo in CLAUDE.md
**Do:** add a short paragraph to root `CLAUDE.md`: the repo now has `/web` (a Next.js app deployed
to Vercel, Root Directory = `web`) alongside the Python station (the backend, not on Vercel); the
web app grows into the audio player + studio in Phase C.
**Done when:** CLAUDE.md reflects the two-part repo.

---

## Definition of done (Phase A2)
settlementradio.com serves the branded coming-soon page over HTTPS; email signup works end to
end into Buttondown; the link shares with a branded card; it's fast and responsive with the
correct favicon; and `hello@settlementradio.com` email still delivers (mail records untouched).

## Not in A2 (→ Phase C, added to this same app)
The audio player, now-playing, channel pages, the studio/about — all become routes in `/web`
later, pointing at the live stream. Don't build them now.

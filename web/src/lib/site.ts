import type { Metadata } from "next";

// R7.4 — the site's own switches and shared metadata.
//
// Everything here is PUBLIC config (no secrets) and inlined at build time, so a change
// on Vercel needs a redeploy — which is the point: flipping the front page is a
// deliberate act, not a runtime accident.

/**
 * While true, `/` stays the coming-soon screen and the player lives at `/listen`.
 * Set `NEXT_PUBLIC_COMING_SOON=false` and redeploy to make the station the front
 * page: `/` becomes the player and `/listen` redirects to it.
 *
 * Defaults to TRUE — the safe state. A missing/mistyped env var can only ever leave
 * the old page up; it can never accidentally advertise a stream that isn't running.
 */
export const COMING_SOON = process.env.NEXT_PUBLIC_COMING_SOON !== "false";

/** Where "Listen" points: the player's canonical home under the current flag. */
export const LISTEN_HREF = COMING_SOON ? "/listen" : "/";

/** Plausible (MARKETING M1). Empty = no analytics script at all. */
export const PLAUSIBLE_DOMAIN = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN ?? "";

export const SITE_NAME = "Settlement Radio";

export const FOLLOW_LINKS = [
  { label: "X", href: "https://x.com/settlement_ch" },
  { label: "GitHub", href: "https://github.com/settlementradio" },
  { label: "YouTube", href: "https://www.youtube.com/@SettlementRadio" },
];

/** The brand social card, shared by every route. */
export const OG_IMAGE = {
  url: "/og-image.png",
  width: 1000,
  height: 1180,
  alt: "Settlement Radio — late-night radio from the far future",
};

/**
 * Per-page metadata that KEEPS the brand card.
 *
 * Next merges metadata *shallowly*: a page that sets `openGraph` replaces the layout's
 * whole `openGraph` object, image and all. Before R7.4 that silently left /listen,
 * /schedule and /voices with no `og:image` — every shared link a blank card. Building
 * page metadata through this helper is what stops that happening again.
 */
export function pageMetadata({
  title,
  description,
  path,
}: {
  title: string;
  description: string;
  path: string;
}): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    // While the station is still "coming soon", the pages behind that screen are for
    // previewing and sharing by hand — not for a search engine to publish as if the
    // stream were live. `/` stays indexable throughout.
    ...(COMING_SOON && path !== "/"
      ? { robots: { index: false, follow: true } }
      : {}),
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      url: path,
      title,
      description,
      images: [OG_IMAGE],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [OG_IMAGE.url],
    },
  };
}

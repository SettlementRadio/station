// R7.1 — where the public data comes from, and the few pure helpers that read it.
//
// The station publishes three read-only JSON feeds beside the stream (built by the
// Python backend: `src/nowplaying.py` + `src/publicfeeds.py`, served by the C7 box).
// The site fetches them CLIENT-SIDE and polls, so a static page keeps tracking the air
// — see `usePolledFeed`. Shapes live in `./types`.
//
// Everything here must be safe to import from both server and client components.

/** The live audio stream (Icecast/HLS URL). Empty until the C7 box is up. */
export const STREAM_URL = process.env.NEXT_PUBLIC_STREAM_URL ?? "";

/** Base URL the three feeds are served from, e.g. https://stream…/feeds */
export const FEEDS_BASE_URL = process.env.NEXT_PUBLIC_FEEDS_BASE_URL ?? "";

/** How often to re-read the fast feed, in seconds. */
export const POLL_SECONDS = Number(process.env.NEXT_PUBLIC_FEED_POLL_SEC ?? 20);

/**
 * How often to re-read the SLOW feeds (schedule, DJs), in seconds.
 *
 * The grid changes when the operator edits it — days or weeks apart — so re-reading
 * every few minutes is already generous. The "on air now" highlight does NOT depend
 * on this: the page recomputes it from the published times against the local clock.
 */
export const SLOW_POLL_SECONDS = Number(
  process.env.NEXT_PUBLIC_SLOW_FEED_POLL_SEC ?? 300,
);

/** Optional support link (Ko-fi goes live at MARKETING M1); hidden while unset. */
export const SUPPORT_URL = process.env.NEXT_PUBLIC_SUPPORT_URL ?? "";

/**
 * R7.3 stretch: offer a short voice sample per host on /voices.
 *
 * Off by default. Turning it on expects OPERATOR-CURATED clips at
 * `web/public/voices/<host-id>.mp3` — never an auto-published segment. Hosts without
 * a clip simply show no control.
 */
export const VOICE_SAMPLES = process.env.NEXT_PUBLIC_VOICE_SAMPLES === "true";

/** Absolute URL of one feed file, or null when no feed host is configured. */
export function feedUrl(file: string): string | null {
  if (!FEEDS_BASE_URL) return null;
  return `${FEEDS_BASE_URL.replace(/\/$/, "")}/${file}`;
}

export const NOWPLAYING_FEED = "nowplaying.json";
export const SCHEDULE_FEED = "schedule-public.json";
export const DJS_FEED = "djs-public.json";

/**
 * "HH:MM" from one of the feeds' naive ISO timestamps.
 *
 * The feeds carry SETTLEMENT WALL CLOCK with no zone suffix, and settlement time is
 * the listener's local time by construction — so the string is sliced, never parsed
 * and re-zoned (a `new Date()` round-trip would shift the schedule for some viewers).
 */
export function wallClock(iso: string | null | undefined): string {
  if (!iso || iso.length < 16) return "";
  return iso.slice(11, 16);
}

/** The listener's own clock as "HH:MM" — settlement time, by construction. */
export function nowWallClock(at: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(at.getHours())}:${pad(at.getMinutes())}`;
}

/** "Vell and Wren", "Thorn", "Kael, Joss and Wren" — a spoken-sounding host list. */
export function hostList(hosts: string[]): string {
  if (hosts.length === 0) return "";
  if (hosts.length === 1) return hosts[0];
  return `${hosts.slice(0, -1).join(", ")} and ${hosts[hosts.length - 1]}`;
}

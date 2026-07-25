// R7.0 — the shape of the three PUBLIC feeds the station publishes, shared by every
// fetcher on the site (the player, /schedule, /voices).
//
// The backend builders are the source of truth and are allow-lists by construction:
//   src/nowplaying.py    -> nowplaying.json        (fast: what is on air now)
//   src/publicfeeds.py   -> schedule-public.json   (slow: today + the week)
//                        -> djs-public.json        (slow: the public cast slice)
// A backend test asserts each feed's exact key set, so if these types drift from the
// JSON, that test is the thing that fails — keep the two in step.
//
// TIMES ARE SETTLEMENT WALL CLOCK: naive ISO strings with NO zone suffix
// ("2026-07-25T18:00:00"). Settlement time and the listener's local time are equal by
// construction, so render these strings AS GIVEN — never `new Date(s)` into a
// browser-zone conversion, which would silently shift the schedule for some viewers.
// Use the string's own "HH:MM" slice (or parse it as local) to display a time.

/** Feed fields common to all three public feeds. */
export interface FeedEnvelope {
  /** "Settlement Radio". */
  station: string;
  /** The AI-disclosure line — must be visible on every route (hard rule). */
  disclosure: string;
  /** When the station last wrote this feed (settlement wall clock, naive ISO). */
  updated_at: string;
}

// --- nowplaying.json ---------------------------------------------------------

/** The public lore of a spun music track (null on non-music segments). */
export interface NowPlayingTrack {
  title: string;
  artist: string;
  album: string | null;
  era: string | null;
  /** The in-world release year (real year + 600). */
  in_world_year: number | null;
  /** One-line story behind the track, when the catalogue carries one. */
  story_blurb: string | null;
}

/** One segment on air or coming up. `program`/`tagline` are null for an ident. */
export interface NowPlayingEntry {
  /** The show's display name, e.g. "Morning Currents". */
  program: string | null;
  /** The internal format id: "talk" | "news" | "music" | "ident" | … */
  format: string | null;
  /** The listener-facing format label, e.g. "The Settlement News". */
  format_label: string | null;
  /** Display names of the voices on this segment, lead first. */
  hosts: string[];
  /** When this segment airs (settlement wall clock, naive ISO). */
  air_time: string | null;
  /** The show's public one-liner. */
  tagline: string | null;
  /** When the SHOW (not the segment) ends — the "until 09:00" line. */
  program_until: string | null;
  track: NowPlayingTrack | null;
}

export interface NowPlayingFeed extends FeedEnvelope {
  /** Null when nothing is on air (the player then shows its static card). */
  now: NowPlayingEntry | null;
  next: NowPlayingEntry[];
}

// --- schedule-public.json ----------------------------------------------------

/** A programme in the directory — the details each schedule entry points at. */
export interface PublicProgram {
  name: string;
  /** The public one-liner shown under the name ("" if the grid gives none). */
  tagline: string;
  /** Display names of the show's hosts, lead first. */
  hosts: string[];
}

/** One run of the day's tiling: half-open [start, end), by programme id. */
export interface ScheduleEntry {
  /** Key into `ScheduleFeed.programs`. */
  program: string;
  start: string;
  end: string;
}

export interface ScheduleDay {
  /** ISO date, "2026-07-25". */
  date: string;
  /** "mon" … "sun". */
  weekday: string;
  /** Gap-free tiling of this day, in air order. */
  entries: ScheduleEntry[];
}

export interface ScheduleFeed extends FeedEnvelope {
  /** Programme details by id — referenced by every day's entries. */
  programs: Record<string, PublicProgram>;
  /** `days[0]` is today; the rest are the week ahead. */
  days: ScheduleDay[];
}

// --- djs-public.json ---------------------------------------------------------

/** A show a host presents this week. */
export interface DjShow {
  id: string;
  name: string;
}

export interface PublicDj {
  id: string;
  name: string;
  /** The short role line, e.g. "the night shift". */
  role: string;
  /** The operator-authored public bio ("" when a card carries none). */
  bio: string;
  /** "station" (in the studio) or "field" (a correspondent, across the lag). */
  based: "station" | "field";
  shows: DjShow[];
}

export interface DjsFeed extends FeedEnvelope {
  djs: PublicDj[];
}

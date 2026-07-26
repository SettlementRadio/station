// R7.2 — the pure reading of the schedule feed. No React here, so the awkward parts
// (what's on now, when does this show air next, how do seven days line up in one
// table) stay small and inspectable.

import type { ScheduleDay, ScheduleEntry, ScheduleFeed } from "./types";

const DAY_MINUTES = 24 * 60;

export const WEEKDAY_LABELS: Record<string, string> = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri",
  sat: "Sat",
  sun: "Sun",
};

/**
 * A feed timestamp as a real Date, for COMPARISON only.
 *
 * The feeds carry settlement wall clock with no zone suffix, and JS parses such a
 * string as LOCAL time — which is exactly right here, because settlement time is the
 * listener's local time by construction. (Display still slices the string; see
 * `wallClock` in ./feeds. Never emit a re-zoned time.)
 */
export function toLocalDate(iso: string): Date {
  return new Date(iso);
}

/** Minutes from the start of `day` — 0..1440, where a day's last run ends at 1440. */
export function minutesIntoDay(day: ScheduleDay, iso: string): number {
  const midnight = toLocalDate(`${day.date}T00:00:00`).getTime();
  return Math.round((toLocalDate(iso).getTime() - midnight) / 60_000);
}

/** The entry covering `now`, or null when `now` falls outside this day. */
export function entryAt(day: ScheduleDay, now: Date): ScheduleEntry | null {
  const t = now.getTime();
  return (
    day.entries.find(
      (e) => toLocalDate(e.start).getTime() <= t && t < toLocalDate(e.end).getTime(),
    ) ?? null
  );
}

/** The on-air entry, looked up across every published day. */
export function onAirEntry(feed: ScheduleFeed, now: Date): ScheduleEntry | null {
  for (const day of feed.days) {
    const hit = entryAt(day, now);
    if (hit) return hit;
  }
  return null;
}

/** "2026-07-26" for a local Date — the key the feed's `days[].date` uses. */
export function localDateKey(at: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}`;
}

/**
 * The published day the listener is actually IN — not blindly `days[0]`.
 *
 * `days[0]` is "today" as of the moment the station wrote the feed. A page left open
 * across midnight, or a feed a few minutes stale, would otherwise show yesterday's
 * rail with nothing marked on air. Matching on the local date fixes both, and falls
 * back to the first published day when the viewer is outside the window entirely.
 */
export function dayFor(feed: ScheduleFeed, now: Date): ScheduleDay | undefined {
  const key = localDateKey(now);
  return feed.days.find((d) => d.date === key) ?? feed.days[0];
}

/** The next time `programId` starts after `now`, anywhere in the published week. */
export function nextAiring(
  feed: ScheduleFeed,
  programId: string,
  now: Date,
): { day: ScheduleDay; entry: ScheduleEntry } | null {
  const t = now.getTime();
  for (const day of feed.days) {
    for (const entry of day.entries) {
      if (entry.program !== programId) continue;
      if (toLocalDate(entry.start).getTime() > t) return { day, entry };
    }
  }
  return null;
}

/** One row of the week table: a time band, and what each day airs in it. */
export interface WeekRow {
  /** Minutes into the day this band starts / ends (0..1440). */
  startMin: number;
  endMin: number;
  /** "07:00" — the band's start, for the row header. */
  label: string;
  /** Per day (feed order), the entry covering this band — null if the day has none. */
  cells: (ScheduleEntry | null)[];
  /** Per day, true when this band merely CONTINUES the same show from the row above. */
  continues: boolean[];
}

function hhmm(totalMinutes: number): string {
  const m = totalMinutes % DAY_MINUTES;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

/**
 * The week as one table: rows are the time bands where ANY day changes programme.
 *
 * Days share most of their spine but differ in the rotating specialist windows, so
 * slicing every day at the union of all boundaries is what makes those windows line
 * up in a column — the "Tuesday economy hour" rhythm becomes visible at a glance
 * (R7.2). `continues` lets the renderer draw a show that spans several bands as one
 * block instead of repeating its name.
 */
export function buildWeekRows(feed: ScheduleFeed): WeekRow[] {
  const edges = new Set<number>([0, DAY_MINUTES]);
  for (const day of feed.days) {
    for (const entry of day.entries) {
      edges.add(minutesIntoDay(day, entry.start));
      edges.add(minutesIntoDay(day, entry.end));
    }
  }
  const sorted = [...edges].filter((m) => m >= 0 && m <= DAY_MINUTES).sort((a, b) => a - b);

  const rows: WeekRow[] = [];
  for (let i = 0; i < sorted.length - 1; i += 1) {
    const startMin = sorted[i];
    const endMin = sorted[i + 1];
    const cells = feed.days.map(
      (day) =>
        day.entries.find(
          (e) =>
            minutesIntoDay(day, e.start) <= startMin &&
            startMin < minutesIntoDay(day, e.end),
        ) ?? null,
    );
    const previous = rows[rows.length - 1];
    rows.push({
      startMin,
      endMin,
      label: hhmm(startMin),
      cells,
      continues: cells.map(
        (cell, d) => !!cell && !!previous && previous.cells[d]?.program === cell.program,
      ),
    });
  }
  return rows;
}

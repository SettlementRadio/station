"use client";

import { useEffect, useMemo, useState } from "react";

import HostMarkGlyph from "@/components/HostMark";
import TodayRail from "@/components/TodayRail";
import WeekTable from "@/components/WeekTable";
import {
  SCHEDULE_FEED,
  SLOW_POLL_SECONDS,
  feedUrl,
  hostList,
  wallClock,
} from "@/lib/feeds";
import { WEEKDAY_LABELS, dayFor, nextAiring, onAirEntry } from "@/lib/schedule";
import type { ScheduleFeed } from "@/lib/types";
import { usePolledFeed } from "@/lib/usePolledFeed";

// R7.2 — "Programmes": today as a rail, the week as a guide.
//
// Two clocks, deliberately separate: the FEED is re-read rarely (the grid changes when
// the operator edits it), while the "on air now" highlight is recomputed from the
// local clock every 30s — so the page keeps up with the air without asking the station
// for anything, and the highlight moves with no reload.

type View = "today" | "week";

/** "Sunday 26 July" — client-only, so the viewer's own locale is safe to use. */
function longDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export default function ScheduleView() {
  const { data, failed, ready } = usePolledFeed<ScheduleFeed>(
    feedUrl(SCHEDULE_FEED),
    SLOW_POLL_SECONDS,
  );
  const [view, setView] = useState<View>("today");
  const [selected, setSelected] = useState<string | null>(null);
  const [now, setNow] = useState<Date | null>(null); // null until the client ticks

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const timer = setInterval(tick, 30_000);
    return () => clearInterval(timer);
  }, []);

  const onAir = useMemo(
    () => (data && now ? onAirEntry(data, now) : null),
    [data, now],
  );

  if (!data) {
    return (
      <p className="text-sm text-neutral/60">
        {!ready
          ? "Reading the schedule…"
          : failed
            ? "The schedule isn't reachable right now. The station is still on air — press play on the listen page."
            : ""}
      </p>
    );
  }

  // The day the LISTENER is in (see dayFor) — not whichever day the feed was written
  // on, so a page left open across midnight still shows the right rail.
  const today = now ? dayFor(data, now) : data.days[0];
  const todayIndex = today ? data.days.indexOf(today) : 0;
  const detail = selected ? data.programs[selected] : null;
  const upcoming = selected && now ? nextAiring(data, selected, now) : null;

  return (
    <div className="flex w-full flex-col gap-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-sm text-neutral/60">
          All times are{" "}
          <span className="text-neutral/85">settlement time</span>{" "}
          <span className="text-neutral/45">(yours — they&rsquo;re the same)</span>
        </p>
        <div className="flex gap-1 rounded-full bg-neutral/10 p-1">
          {(["today", "week"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setView(option)}
              aria-pressed={view === option}
              className={
                "rounded-full px-4 py-1.5 text-sm transition " +
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber " +
                (view === option
                  ? "bg-amber text-night font-semibold"
                  : "text-neutral/70 hover:text-neutral")
              }
            >
              {option === "today" ? "Today" : "The week"}
            </button>
          ))}
        </div>
      </div>

      {view === "today" ? (
        <section aria-label="Today's programmes" className="flex flex-col gap-4">
          <h2 className="text-xs tracking-[0.2em] text-neutral/50 uppercase">
            {today ? longDate(today.date) : "Today"}
          </h2>
          {today && now && (
            <TodayRail feed={data} day={today} now={now} onAir={onAir} />
          )}
        </section>
      ) : (
        <section aria-label="The week's programmes" className="flex flex-col gap-4">
          <p className="text-sm text-neutral/55">
            Most of the day is the same every day — the fixture rule. The windows that
            change are the specialist hours; pick any show to see what it is.
          </p>
          {now && (
            <WeekTable
              feed={data}
              now={now}
              todayIndex={todayIndex}
              selected={selected}
              onSelect={(id) => setSelected((prev) => (prev === id ? null : id))}
            />
          )}
          {detail && (
            <aside
              aria-live="polite"
              className="lit-window rounded-2xl border border-amber/25 px-5 py-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex flex-col gap-2">
                  <h3 className="text-lg font-semibold text-neutral">
                    {detail.name}
                  </h3>
                  {detail.tagline && (
                    <p className="max-w-prose text-sm text-neutral/70">
                      {detail.tagline}
                    </p>
                  )}
                  {detail.hosts.length > 0 && (
                    <p className="flex flex-wrap items-center gap-2 text-sm text-neutral/55">
                      {detail.hosts.map((host) => (
                        <HostMarkGlyph key={host} name={host} size={16} />
                      ))}
                      <span>with {hostList(detail.hosts)}</span>
                    </p>
                  )}
                  <p className="text-sm text-amber/85">
                    {upcoming
                      ? `Next: ${
                          upcoming.day === today
                            ? "today"
                            : (WEEKDAY_LABELS[upcoming.day.weekday] ??
                              upcoming.day.weekday)
                        } at ${wallClock(upcoming.entry.start)}`
                      : "On air now"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="rounded-full px-2 py-1 text-sm text-neutral/50 transition hover:text-neutral focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber"
                  aria-label={`Close details for ${detail.name}`}
                >
                  ✕
                </button>
              </div>
            </aside>
          )}
        </section>
      )}

      {failed && (
        <p className="text-xs text-neutral/45">
          (Showing the last schedule we received — the station feed is unreachable.)
        </p>
      )}
    </div>
  );
}

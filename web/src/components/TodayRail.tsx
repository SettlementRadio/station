"use client";

import { useEffect, useRef } from "react";

import { hostList, wallClock } from "@/lib/feeds";
import HostMarkGlyph from "@/components/HostMark";
import { toLocalDate } from "@/lib/schedule";
import type { ScheduleDay, ScheduleEntry, ScheduleFeed } from "@/lib/types";

// R7.2 — today, as a relay thread: one node per programme, the current one lit.
//
// Every row carries its full detail inline (time · name · tagline · hosts) rather than
// hiding it behind a disclosure — a listener scanning "what's on at four" shouldn't
// have to click seven things to find out.

export default function TodayRail({
  feed,
  day,
  now,
  onAir,
}: {
  feed: ScheduleFeed;
  day: ScheduleDay;
  now: Date;
  onAir: ScheduleEntry | null;
}) {
  const liveRow = useRef<HTMLLIElement | null>(null);
  const scrolled = useRef(false);

  // Land the listener on "now" — once, on first paint, and never again (re-scrolling
  // on a later poll would yank the page out from under someone who has scrolled off).
  // `nearest` on purpose: it scrolls only when the current show is off-screen, so an
  // early-morning slot doesn't shove the page heading out of view for no reason.
  useEffect(() => {
    if (scrolled.current || !liveRow.current) return;
    scrolled.current = true;
    liveRow.current.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [onAir]);

  return (
    <ol className="relative flex flex-col border-l border-neutral/15">
      {day.entries.map((entry) => {
        const program = feed.programs[entry.program];
        const live = entry === onAir;
        const past = toLocalDate(entry.end).getTime() <= now.getTime();
        return (
          <li
            key={entry.start}
            ref={live ? liveRow : undefined}
            aria-current={live ? "true" : undefined}
            className={
              "relative py-3 pl-5 transition-opacity " +
              (past && !live ? "opacity-45" : "")
            }
          >
            <span
              aria-hidden="true"
              className={
                "absolute top-[1.35rem] -left-[5px] h-[9px] w-[9px] rounded-full ring-4 ring-night " +
                (live ? "bg-amber" : past ? "bg-neutral/30" : "bg-amber/50")
              }
            />
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <time className="w-12 shrink-0 text-sm tabular-nums text-amber/90">
                {wallClock(entry.start)}
              </time>
              <h3
                className={
                  "text-lg " + (live ? "font-semibold text-amber" : "text-neutral/90")
                }
              >
                {program?.name ?? entry.program}
              </h3>
              {live && (
                <span className="rounded-full bg-amber/15 px-2 py-0.5 text-[0.65rem] font-semibold tracking-[0.16em] text-amber uppercase ring-1 ring-amber/40">
                  On air
                </span>
              )}
            </div>
            {(program?.tagline || program?.hosts.length) && (
              <div className="mt-1 flex flex-col gap-1.5 pl-0 sm:pl-15">
                {program?.tagline && (
                  <p className="max-w-prose text-sm text-neutral/65">
                    {program.tagline}
                  </p>
                )}
                {program && program.hosts.length > 0 && (
                  <p className="flex items-center gap-2 text-sm text-neutral/50">
                    {program.hosts.map((host) => (
                      <HostMarkGlyph key={host} name={host} size={16} />
                    ))}
                    <span>with {hostList(program.hosts)}</span>
                  </p>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}

"use client";

import { WEEKDAY_LABELS, buildWeekRows } from "@/lib/schedule";
import type { ScheduleEntry, ScheduleFeed } from "@/lib/types";
import { useMemo } from "react";

// R7.2 — the whole week in one table, so the station's RHYTHM is visible: the fixed
// spine every day, and the rotating specialist windows standing out as the cells that
// differ from their neighbours ("the Tuesday economy hour").
//
// Rows are the time bands where any day changes show; a show spanning several bands is
// drawn once and left blank below (a real programme guide), which is also what makes
// the rotating windows pop.

export default function WeekTable({
  feed,
  now,
  todayIndex,
  selected,
  onSelect,
}: {
  feed: ScheduleFeed;
  now: Date;
  /** Which published day the listener is in — the column the live band belongs to. */
  todayIndex: number;
  selected: string | null;
  onSelect: (programId: string) => void;
}) {
  const rows = useMemo(() => buildWeekRows(feed), [feed]);
  // Minutes into the local day, read straight off the clock. (NOT via toISOString —
  // that converts to UTC and would slide the highlight by the viewer's offset.)
  const nowMinutes = now.getHours() * 60 + now.getMinutes();

  return (
    // Wide content scrolls in its own container — the page never scrolls sideways.
    <div className="-mx-5 overflow-x-auto px-5 sm:mx-0 sm:px-0">
      <table className="w-full min-w-[46rem] border-separate border-spacing-0 text-left">
        <caption className="sr-only">
          The week&rsquo;s programmes, by day and settlement time
        </caption>
        <thead>
          <tr>
            <th
              scope="col"
              className="sticky left-0 z-10 bg-night pr-3 pb-2 text-xs font-normal tracking-[0.16em] text-neutral/40 uppercase"
            >
              Time
            </th>
            {feed.days.map((day, i) => (
              <th
                key={day.date}
                scope="col"
                className={
                  "px-2 pb-2 text-xs font-semibold tracking-[0.12em] uppercase " +
                  (i === todayIndex ? "text-amber" : "text-neutral/55")
                }
              >
                {i === todayIndex
                  ? "Today"
                  : (WEEKDAY_LABELS[day.weekday] ?? day.weekday)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const liveBand = nowMinutes >= row.startMin && nowMinutes < row.endMin;
            return (
              <tr key={row.startMin} className="align-top">
                <th
                  scope="row"
                  className={
                    "sticky left-0 z-10 bg-night py-1 pr-3 text-xs font-normal tabular-nums " +
                    (liveBand ? "text-amber" : "text-neutral/40")
                  }
                >
                  {row.label}
                </th>
                {row.cells.map((cell, dayIndex) => (
                  <WeekCell
                    key={feed.days[dayIndex].date}
                    feed={feed}
                    cell={cell}
                    continues={row.continues[dayIndex]}
                    live={liveBand && dayIndex === todayIndex}
                    selected={!!cell && cell.program === selected}
                    onSelect={onSelect}
                  />
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WeekCell({
  feed,
  cell,
  continues,
  live,
  selected,
  onSelect,
}: {
  feed: ScheduleFeed;
  cell: ScheduleEntry | null;
  continues: boolean;
  live: boolean;
  selected: boolean;
  onSelect: (programId: string) => void;
}) {
  if (!cell) return <td className="px-2 py-1" />;

  const program = feed.programs[cell.program];
  const name = program?.name ?? cell.program;

  return (
    <td className="border-l border-neutral/10 px-1 py-0.5">
      {continues ? (
        // The show runs on from the band above: keep the column unbroken, stay silent.
        <span className="sr-only">{name} continues</span>
      ) : (
        <button
          type="button"
          onClick={() => onSelect(cell.program)}
          aria-pressed={selected}
          className={
            "w-full rounded-lg px-2 py-1.5 text-left text-[0.8rem] leading-snug transition " +
            "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber " +
            (live
              ? "bg-amber/15 text-amber ring-1 ring-amber/40 "
              : "text-neutral/80 hover:bg-neutral/10 ") +
            (selected && !live ? "bg-neutral/10 ring-1 ring-neutral/25" : "")
          }
        >
          {name}
          {live && <span className="sr-only"> — on air now</span>}
        </button>
      )}
    </td>
  );
}

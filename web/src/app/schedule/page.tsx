import type { Metadata } from "next";

import ScheduleView from "@/components/ScheduleView";
import SiteShell from "@/components/SiteShell";
import { pageMetadata } from "@/lib/site";

// R7.2 — "Programmes": the station's whole day and week, the thing that makes a
// listener read this as a real station rather than a generated stream. A server shell;
// everything that depends on the clock or the feed lives in <ScheduleView /> (client).

const title = "Programmes — Settlement Radio";
const description =
  "The whole day and the week ahead: every programme on Settlement Radio, in " +
  "settlement time — news desks, magazines, the chart, and the long night.";

export const metadata: Metadata = pageMetadata({
  title,
  description,
  path: "/schedule",
});

export default function SchedulePage() {
  return (
    <SiteShell
      current="schedule"
      width="wide"
      title="Programmes"
      intro="What’s on, all week. The spine repeats every day; the specialist windows rotate."
    >
      <ScheduleView />
    </SiteShell>
  );
}

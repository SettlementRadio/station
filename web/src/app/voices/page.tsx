import type { Metadata } from "next";

import SiteShell from "@/components/SiteShell";
import VoicesGrid from "@/components/VoicesGrid";
import { pageMetadata } from "@/lib/site";

// R7.3 — "The DJs": who you're listening to.
//
// Canon rule the page is built around (00-station.md, fact 8): listeners know the
// presenters only by their VOICES. So there are no portraits — each host is a signal
// mark in their own accent tone, a role line, and the bio the operator wrote for them.

const title = "The voices — Settlement Radio";
const description =
  "The presenters of Settlement Radio: the night shift, the news desk, the " +
  "correspondents out past the last relay. You know them by their voices.";

export const metadata: Metadata = pageMetadata({
  title,
  description,
  path: "/voices",
});

export default function VoicesPage() {
  return (
    <SiteShell
      current="voices"
      width="wide"
      title="The voices"
      intro="Nobody out here has seen the presenters. You know them the way the settlements do — by the voice that comes through the dark, and what it says."
    >
      <VoicesGrid />
    </SiteShell>
  );
}

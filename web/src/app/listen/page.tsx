import type { Metadata } from "next";
import { redirect } from "next/navigation";

import Player from "@/components/Player";
import SiteShell from "@/components/SiteShell";
import { COMING_SOON, pageMetadata } from "@/lib/site";

// R7.1 — the player: "settlementradio.com IS the station."
//
// R7.4 gave the site one canonical home for it. While `NEXT_PUBLIC_COMING_SOON` is on,
// that home is here (so the station front can be previewed while `/` still says
// "soon"); once it's off, `/` is the player and this route redirects there rather than
// serving a second copy of the same page.

const title = "Listen live — Settlement Radio";
const description =
  "Press play: live radio from the settled worlds of the late 27th century — " +
  "news, music, and company across the dark.";

export const metadata: Metadata = pageMetadata({
  title,
  description,
  path: "/listen",
});

export default function ListenPage() {
  if (!COMING_SOON) redirect("/");

  return (
    <SiteShell current="listen">
      <Player />
    </SiteShell>
  );
}

import type { Metadata } from "next";

import ComingSoon from "@/components/ComingSoon";
import Player from "@/components/Player";
import SiteShell from "@/components/SiteShell";
import { COMING_SOON, pageMetadata } from "@/lib/site";

// R7.4 — the front door, on ONE switch (`NEXT_PUBLIC_COMING_SOON`, default true):
//
//   true  → the A2 coming-soon screen, exactly as it has always been. `/listen` still
//           serves the player, so the station front can be previewed and shared
//           before it's announced.
//   false → `/` IS the station: the player, inside the shared shell. `/listen`
//           redirects here so there's one canonical home, not two copies of it.
//
// Flip it in the Vercel env vars and redeploy; flip it back the same way if the
// stream has to come down. Nothing else in the site changes.

const comingSoonMeta = {
  title: "Settlement Radio — Late-night radio from the far future",
  description:
    "Broadcasting soon from the settled worlds of the late 27th century — news, " +
    "music, and company across the dark. A work of fiction, written and voiced " +
    "with AI, as a tribute to the science fiction that imagined us here.",
};

const listenMeta = {
  title: "Settlement Radio — live from the settled worlds",
  description:
    "Press play: live radio from the settled worlds of the late 27th century — " +
    "news, music, and company across the dark.",
};

export const metadata: Metadata = pageMetadata({
  ...(COMING_SOON ? comingSoonMeta : listenMeta),
  path: "/",
});

export default function Home() {
  if (COMING_SOON) return <ComingSoon />;

  return (
    <SiteShell current="listen">
      <Player />
    </SiteShell>
  );
}

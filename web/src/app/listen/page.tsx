import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import Player from "@/components/Player";
import { DISCLOSURE_TAGLINE } from "@/lib/disclosure";
import { SUPPORT_URL } from "@/lib/feeds";

// R7.1 — the player page: "settlementradio.com IS the station."
//
// It lives at /listen for now and `/` stays the coming-soon screen: the public stream
// (C7) isn't up yet, so replacing the live front page would advertise a transmitter
// that doesn't transmit. R7.4 adds the nav + the COMING_SOON flag that flips `/` here.
//
// A server component: it renders the calm dark shell, the brand, the disclosure and the
// links; everything that moves lives in <Player /> (a client component).

const title = "Listen live — Settlement Radio";
const description =
  "Press play: live radio from the settled worlds of the late 27th century — " +
  "news, music, and company across the dark.";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, url: "/listen" },
  twitter: { title, description },
};

const followLinks = [
  { label: "X", href: "https://x.com/settlement_ch" },
  { label: "GitHub", href: "https://github.com/settlementradio" },
  { label: "YouTube", href: "https://www.youtube.com/@SettlementRadio" },
];

export default function ListenPage() {
  return (
    <main className="starfield relative flex flex-1 flex-col items-center bg-night px-5 py-12 text-neutral sm:px-6 sm:py-16">
      <div className="relative flex w-full max-w-2xl flex-col gap-10">
        <header className="flex flex-col items-start gap-3">
          <h1 className="m-0">
            <Image
              src="/wordmark-horizontal.svg"
              alt="Settlement Radio"
              width={360}
              height={100}
              className="h-auto w-44 sm:w-52"
              priority
            />
          </h1>
          <p className="text-sm text-neutral/60">{DISCLOSURE_TAGLINE}</p>
        </header>

        <Player />

        <footer className="mt-2 flex flex-col gap-4 border-t border-neutral/10 pt-6">
          <nav aria-label="Follow Settlement Radio">
            <ul className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-neutral/70">
              {followLinks.map(({ label, href }) => (
                <li key={label}>
                  <a
                    href={href}
                    className="underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:text-amber focus-visible:underline focus-visible:outline-none"
                  >
                    {label}
                  </a>
                </li>
              ))}
              <li>
                <Link
                  href="/#signup"
                  className="underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:text-amber focus-visible:underline focus-visible:outline-none"
                >
                  Newsletter
                </Link>
              </li>
              {SUPPORT_URL && (
                <li>
                  <a
                    href={SUPPORT_URL}
                    className="text-amber/90 underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:underline focus-visible:outline-none"
                  >
                    Keep the signal lit
                  </a>
                </li>
              )}
            </ul>
          </nav>
        </footer>
      </div>
    </main>
  );
}

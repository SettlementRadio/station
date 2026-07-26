import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import VoicesGrid from "@/components/VoicesGrid";
import { DISCLOSURE_LINE } from "@/lib/disclosure";

// R7.3 — "The DJs": who you're listening to.
//
// Canon rule the page is built around (00-station.md, fact 8): listeners know the
// presenters only by their VOICES. So there are no portraits — each host is a signal
// mark in their own accent tone, a role line, and the bio the operator wrote for them.
// R7.4 replaces the inline links with the shared nav.

const title = "The voices — Settlement Radio";
const description =
  "The presenters of Settlement Radio: the night shift, the news desk, the " +
  "correspondents out past the last relay. You know them by their voices.";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, url: "/voices" },
  twitter: { title, description },
};

export default function VoicesPage() {
  return (
    <main className="starfield relative flex flex-1 flex-col items-center bg-night px-5 py-12 text-neutral sm:px-6 sm:py-16">
      <div className="relative flex w-full max-w-4xl flex-col gap-10">
        <header className="flex flex-col items-start gap-4">
          <Link href="/listen" className="inline-block">
            <Image
              src="/wordmark-horizontal.svg"
              alt="Settlement Radio"
              width={360}
              height={100}
              className="h-auto w-44 sm:w-52"
              priority
            />
          </Link>
          <div className="flex flex-col gap-2">
            <h1 className="text-3xl font-semibold sm:text-4xl">The voices</h1>
            <p className="max-w-prose text-base text-neutral/70">
              Nobody out here has seen the presenters. You know them the way the
              settlements do — by the voice that comes through the dark, and what it
              says.
            </p>
          </div>
          <nav className="flex gap-5 text-sm">
            <Link
              href="/listen"
              className="text-amber/90 underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:underline focus-visible:outline-none"
            >
              ← Listen live
            </Link>
            <Link
              href="/schedule"
              className="text-amber/90 underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:underline focus-visible:outline-none"
            >
              Programmes
            </Link>
          </nav>
        </header>

        <VoicesGrid />

        <footer className="mt-2 border-t border-neutral/10 pt-6">
          <p className="max-w-prose text-xs leading-relaxed text-neutral/60">
            {DISCLOSURE_LINE}
          </p>
        </footer>
      </div>
    </main>
  );
}

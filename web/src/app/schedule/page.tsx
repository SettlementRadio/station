import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";

import ScheduleView from "@/components/ScheduleView";
import { DISCLOSURE_LINE } from "@/lib/disclosure";

// R7.2 — "Programmes": the station's whole day and week, the thing that makes a
// listener read this as a real station rather than a generated stream.
//
// A server component shell; everything that depends on the clock or the feed lives in
// <ScheduleView /> (client). R7.4 replaces the inline back-link with the shared nav.

const title = "Programmes — Settlement Radio";
const description =
  "The whole day and the week ahead: every programme on Settlement Radio, in " +
  "settlement time — news desks, magazines, the chart, and the long night.";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, url: "/schedule" },
  twitter: { title, description },
};

export default function SchedulePage() {
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
            <h1 className="text-3xl font-semibold sm:text-4xl">Programmes</h1>
            <p className="max-w-prose text-base text-neutral/70">
              What&rsquo;s on, all week. The spine repeats every day; the specialist
              windows rotate.
            </p>
          </div>
          <Link
            href="/listen"
            className="text-sm text-amber/90 underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:underline focus-visible:outline-none"
          >
            ← Listen live
          </Link>
        </header>

        <ScheduleView />

        <footer className="mt-2 border-t border-neutral/10 pt-6">
          <p className="max-w-prose text-xs leading-relaxed text-neutral/60">
            {DISCLOSURE_LINE}
          </p>
        </footer>
      </div>
    </main>
  );
}

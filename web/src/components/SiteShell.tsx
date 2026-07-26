import Image from "next/image";
import Link from "next/link";

import SignupForm from "@/components/SignupForm";
import { DISCLOSURE_LINE, DISCLOSURE_TAGLINE } from "@/lib/disclosure";
import { SUPPORT_URL } from "@/lib/feeds";
import { FOLLOW_LINKS, LISTEN_HREF } from "@/lib/site";

// R7.4 — one shell for the three public pages: the same masthead, the same nav, the
// same footer. A server component (no client JS for chrome) — the current page is
// passed in rather than read from a router hook.
//
// The footer carries the AI-disclosure line, which is how "visible on every route"
// (CLAUDE.md hard rule) becomes structural instead of something each page remembers.

export type SitePage = "listen" | "schedule" | "voices";

const NAV: { key: SitePage; label: string; href: string }[] = [
  { key: "listen", label: "Listen", href: LISTEN_HREF },
  { key: "schedule", label: "Programmes", href: "/schedule" },
  { key: "voices", label: "The voices", href: "/voices" },
];

export default function SiteShell({
  current,
  title,
  intro,
  width = "narrow",
  children,
}: {
  current: SitePage;
  /** The page's own heading. Omitted on the player, where the card is the hero. */
  title?: string;
  intro?: string;
  width?: "narrow" | "wide";
  children: React.ReactNode;
}) {
  const maxWidth = width === "wide" ? "max-w-4xl" : "max-w-2xl";

  return (
    <main className="starfield relative flex flex-1 flex-col items-center bg-night px-5 py-10 text-neutral sm:px-6 sm:py-14">
      <div className={`relative flex w-full flex-col gap-9 ${maxWidth}`}>
        <header className="flex flex-col gap-5">
          <div className="flex flex-wrap items-center justify-between gap-x-8 gap-y-4">
            <Link href={LISTEN_HREF} aria-label="Settlement Radio — home">
              <Image
                src="/wordmark-horizontal.svg"
                alt="Settlement Radio"
                width={360}
                height={100}
                className="h-auto w-40 sm:w-48"
                priority
              />
            </Link>
            <nav aria-label="Sections">
              <ul className="flex items-center gap-5 text-sm sm:gap-7">
                {NAV.map((item) => {
                  const active = item.key === current;
                  return (
                    <li key={item.key}>
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        className={
                          "underline-offset-8 transition-colors focus-visible:outline-none focus-visible:underline " +
                          (active
                            ? "font-semibold text-amber underline decoration-amber/60"
                            : "text-neutral/70 hover:text-amber")
                        }
                      >
                        {item.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
          </div>

          {title && (
            <div className="flex flex-col gap-2">
              <h1 className="text-3xl font-semibold sm:text-4xl">{title}</h1>
              {intro && (
                <p className="max-w-prose text-base text-neutral/70">{intro}</p>
              )}
            </div>
          )}
        </header>

        {children}

        <SiteFooter />
      </div>
    </main>
  );
}

function SiteFooter() {
  return (
    <footer className="mt-4 flex flex-col gap-6 border-t border-neutral/10 pt-7">
      {/* The letters box — the station's own framing for the mailing list. */}
      <div className="flex flex-col gap-3">
        <h2 className="text-xs tracking-[0.2em] text-neutral/50 uppercase">
          Send a letter
        </h2>
        <p className="max-w-prose text-sm text-neutral/65">
          Leave a signal and we&rsquo;ll write when something changes out here — new
          programmes, new voices, the day we go live for good.
        </p>
        <SignupForm />
      </div>

      <div className="flex flex-col gap-3">
        <nav aria-label="Follow Settlement Radio">
          <ul className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-neutral/70">
            {FOLLOW_LINKS.map(({ label, href }) => (
              <li key={label}>
                <a
                  href={href}
                  className="underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:text-amber focus-visible:underline focus-visible:outline-none"
                >
                  {label}
                </a>
              </li>
            ))}
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
        {/* The hard rule: the disclosure is on EVERY route, in the station's voice. */}
        <p className="max-w-prose text-xs leading-relaxed text-neutral/60">
          {DISCLOSURE_LINE} {DISCLOSURE_TAGLINE}
        </p>
      </div>
    </footer>
  );
}

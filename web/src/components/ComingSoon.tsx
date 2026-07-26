import Image from "next/image";

import SignupForm from "@/components/SignupForm";
import { DISCLOSURE_LINE, DISCLOSURE_TAGLINE } from "@/lib/disclosure";
import { FOLLOW_LINKS } from "@/lib/site";

// The A2 coming-soon screen, kept intact and moved into a component (R7.4) so `/` can
// switch between it and the station front on one env flag. Deliberately its own quiet
// page with no site nav: while this is up, there is nothing yet to navigate to.

export default function ComingSoon() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center bg-night px-6 py-16 text-center text-neutral">
      <div className="flex w-full max-w-xl flex-col items-center gap-10">
        {/* Brand lockup doubles as the page's real heading via its alt text. */}
        <h1 className="m-0">
          <Image
            src="/wordmark-horizontal.svg"
            alt="Settlement Radio"
            width={360}
            height={100}
            className="h-auto w-60 sm:w-72"
            priority
          />
        </h1>

        <div className="flex flex-col items-center gap-4">
          <p className="text-lg font-medium text-amber sm:text-xl">
            Late-night radio from the far future.
          </p>
          <p className="max-w-md text-sm leading-relaxed text-neutral/80 sm:text-base">
            Broadcasting soon from the settled worlds of the late 27th century.
            News, music, and company across the dark. Leave your signal and
            we&rsquo;ll tell you when we&rsquo;re on air.
          </p>
        </div>

        <SignupForm />

        <p className="max-w-sm text-xs leading-relaxed text-neutral/60">
          {DISCLOSURE_LINE} {DISCLOSURE_TAGLINE}
        </p>

        <nav aria-label="Follow Settlement Radio">
          <ul className="flex items-center gap-6 text-sm text-neutral/70">
            {FOLLOW_LINKS.map(({ label, href }) => (
              <li key={label}>
                <a
                  href={href}
                  className="underline-offset-4 transition-colors hover:text-amber hover:underline focus:text-amber focus:underline focus:outline-none"
                >
                  {label}
                </a>
              </li>
            ))}
            <li>
              <a
                href="#signup"
                className="underline-offset-4 transition-colors hover:text-amber hover:underline focus:text-amber focus:underline focus:outline-none"
              >
                Newsletter
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </main>
  );
}

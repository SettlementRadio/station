import Image from "next/image";

// Coming-soon screen (A2-T2): one quiet night-field screen — beacon + wordmark
// lockup, tagline, body, email signup, disclosure, follow links.
// The signup form is presentational here; A2-T3 wires it to Buttondown.

const followLinks = [
  { label: "X", href: "https://x.com/settlement_ch" },
  { label: "GitHub", href: "https://github.com/settlementradio" },
  { label: "YouTube", href: "https://www.youtube.com/@SettlementRadio" },
  { label: "Newsletter", href: "#signup" },
];

export default function Home() {
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
            Broadcasting soon from the settled worlds of the late 27th
            century — news, music, and company across the dark. Leave your
            signal and we&rsquo;ll tell you when we&rsquo;re on air.
          </p>
        </div>

        <form
          id="signup"
          className="flex w-full max-w-sm flex-col gap-3 sm:flex-row"
        >
          <label htmlFor="email" className="sr-only">
            Email address
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            required
            className="flex-1 rounded-md border border-amber/30 bg-white/5 px-4 py-3 text-base text-neutral placeholder:text-neutral/40 focus:border-amber focus:outline-none focus:ring-2 focus:ring-amber/60"
          />
          <button
            type="submit"
            className="rounded-md bg-amber px-5 py-3 font-semibold text-night transition-colors hover:bg-amber/90 focus:outline-none focus:ring-2 focus:ring-amber/60 focus:ring-offset-2 focus:ring-offset-night"
          >
            Notify me
          </button>
        </form>

        <p className="max-w-sm text-xs leading-relaxed text-neutral/60">
          A work of fiction, written and voiced with AI — a tribute to the
          science fiction that imagined us here.
        </p>

        <nav aria-label="Follow Settlement Radio">
          <ul className="flex items-center gap-6 text-sm text-neutral/70">
            {followLinks.map(({ label, href }) => (
              <li key={label}>
                <a
                  href={href}
                  className="underline-offset-4 transition-colors hover:text-amber hover:underline focus:text-amber focus:underline focus:outline-none"
                >
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </main>
  );
}

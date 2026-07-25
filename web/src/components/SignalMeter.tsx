// R7.1 — the signal/VU pulse: the window is LIT while playing, still and dim when not.
// Pure CSS (no canvas, no deps), and honours `prefers-reduced-motion` via globals.css.
//
// The bars sit on a faint baseline rule so the idle state reads as "a meter at rest"
// rather than as stray specks on the page.

const BARS = [0.55, 0.9, 0.45, 1, 0.7, 0.35, 0.8];

export default function SignalMeter({ active }: { active: boolean }) {
  return (
    <div
      className="flex h-6 items-end gap-[3px] border-b border-neutral/15 pb-[3px]"
      role="presentation"
      aria-hidden="true"
    >
      {BARS.map((peak, i) => (
        <span
          key={i}
          className={
            "w-[3px] origin-bottom rounded-full bg-amber transition-opacity duration-500 " +
            (active ? "animate-signal opacity-90" : "opacity-40")
          }
          style={{
            height: `${Math.round(peak * 100)}%`,
            animationDelay: `${i * 0.11}s`,
            animationDuration: `${0.9 + (i % 3) * 0.22}s`,
            transform: active ? undefined : "scaleY(0.4)",
          }}
        />
      ))}
    </div>
  );
}

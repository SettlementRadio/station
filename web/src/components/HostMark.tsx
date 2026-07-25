import { hostMark } from "@/lib/hostMark";

// R7.1 — the per-host signal mark (see lib/hostMark.ts for why it isn't a face).
// A pure, presentational server component: no state, safe to render anywhere.

export default function HostMarkGlyph({
  name,
  size = 22,
}: {
  name: string;
  size?: number;
}) {
  const { tone, bars } = hostMark(name);
  const gap = 1.2;
  const barWidth = (24 - gap * 4 - 4) / 5; // 24-unit box, 2 units padding each side

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      role="presentation"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect
        x="0.5"
        y="0.5"
        width="23"
        height="23"
        rx="6"
        fill={tone}
        fillOpacity="0.1"
        stroke={tone}
        strokeOpacity="0.45"
      />
      {bars.map((h, i) => {
        const height = 14 * h;
        return (
          <rect
            key={i}
            x={2 + i * (barWidth + gap)}
            y={12 - height / 2}
            width={barWidth}
            height={height}
            rx={barWidth / 2}
            fill={tone}
            fillOpacity="0.85"
          />
        );
      })}
    </svg>
  );
}

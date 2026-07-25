// R7.1 — a host's identity device: an abstract SIGNAL MARK, never a portrait.
//
// Canon (00-station.md fact 8): listeners know the presenters only by their voices.
// So every host gets a small waveform mark in their own accent tone, derived
// deterministically from their display name — same host, same mark, on every page and
// on both server and client (no randomness, so no hydration mismatch), and no new
// asset to author when the cast changes.

/** The warm-analog accent palette — dial glows, not neon. */
const TONES = [
  "#f2c04d", // amber (the station's own)
  "#e8935c", // copper
  "#d9736f", // rose dust
  "#e3c08a", // sand
  "#8fbf9f", // sage
  "#6fb3bf", // relay teal
  "#9b93c9", // dusk violet
  "#bcd3e8", // ice
] as const;

/** A tiny stable string hash (FNV-1a, 32-bit) — deterministic across runtimes. */
function hash(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

export interface HostMark {
  /** The host's accent colour. */
  tone: string;
  /** Five bar heights in 0..1 — their "signature" on the meter. */
  bars: number[];
}

export function hostMark(name: string): HostMark {
  const h = hash(name || "signal");
  const tone = TONES[h % TONES.length];
  // Five bars pulled from successive bits of the same hash, kept clear of 0 and 1 so
  // every mark reads as a waveform rather than a solid block or an empty frame.
  const bars = [0, 1, 2, 3, 4].map((i) => {
    const nibble = (h >>> (i * 5)) & 0x1f; // 0..31
    return 0.28 + (nibble / 31) * 0.72;
  });
  return { tone, bars };
}

// Placeholder — the full coming-soon screen is built in A2-T2.
// This minimal version exercises the brand foundation: night-field
// background, amber mark, warm-neutral text, and the Inter brand font.
import Image from "next/image";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-night px-6 text-center text-neutral">
      <Image
        src="/beacon-mark.svg"
        alt="Settlement Radio beacon mark"
        width={96}
        height={96}
        priority
      />
      <h1 className="text-2xl font-semibold tracking-tight text-amber">
        Settlement Radio
      </h1>
    </main>
  );
}

"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { DISCLOSURE_LINE } from "@/lib/disclosure";
import {
  NOWPLAYING_FEED,
  POLL_SECONDS,
  STREAM_URL,
  feedUrl,
  hostList,
  nowWallClock,
  wallClock,
} from "@/lib/feeds";
import type { NowPlayingEntry, NowPlayingFeed } from "@/lib/types";
import { usePolledFeed } from "@/lib/usePolledFeed";

import HostMarkGlyph from "./HostMark";
import SignalMeter from "./SignalMeter";

// R7.1 — "a lit window seen across the dark": the on-air card, the play control, and
// the up-next rail. One client component because all three read the same polled feed
// and the same playback state.
//
// Two non-negotiables from the pack:
//   * NEVER a broken page. No feed (or a feed that fails) still gives a playable
//     "Settlement Radio — live" card; no stream URL configured says so plainly.
//   * The AI-disclosure line is always rendered here, under the controls.

type Playback = "idle" | "connecting" | "playing" | "error";

const VOLUME_KEY = "sr-volume";
const DEFAULT_VOLUME = 0.8;

export default function Player() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const volumeRef = useRef<HTMLInputElement | null>(null);
  const [playback, setPlayback] = useState<Playback>("idle");
  const [clock, setClock] = useState(""); // set on the client — never during SSR

  const { data, failed } = usePolledFeed<NowPlayingFeed>(
    feedUrl(NOWPLAYING_FEED),
    POLL_SECONDS,
  );

  const now = data?.now ?? null;
  const next = (data?.next ?? []).slice(0, 3);
  const playing = playback === "playing" || playback === "connecting";

  // The listener's clock IS settlement time (the world clock shifts only the year).
  useEffect(() => {
    const tick = () => setClock(nowWallClock());
    tick();
    const timer = setInterval(tick, 15_000);
    return () => clearInterval(timer);
  }, []);

  // Volume is NOT React state: it belongs to the audio element (and to the slider that
  // drives it), so it lives there and the saved value is restored straight onto both.
  // Radio manners — a listener sets the level once.
  useEffect(() => {
    const saved = Number(window.localStorage.getItem(VOLUME_KEY));
    const level = saved > 0 && saved <= 1 ? saved : DEFAULT_VOLUME;
    if (volumeRef.current) volumeRef.current.value = String(level);
    if (audioRef.current) audioRef.current.volume = level;
  }, []);

  const currentVolume = () => {
    const level = Number(volumeRef.current?.value);
    return level > 0 && level <= 1 ? level : DEFAULT_VOLUME;
  };

  const toggle = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || !STREAM_URL) return;

    if (playing) {
      // A live stream must be truly released, not just paused, or the browser keeps
      // pulling audio in the background: drop the source and reload the element.
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      setPlayback("idle");
      return;
    }

    setPlayback("connecting");
    audio.src = STREAM_URL;
    audio.volume = currentVolume();
    try {
      await audio.play();
      setPlayback("playing");
    } catch {
      setPlayback("error");
    }
  }, [playing]);

  return (
    <div className="flex w-full flex-col gap-8">
      {/* The one element that actually carries the station. */}
      <audio
        ref={audioRef}
        preload="none"
        onPlaying={() => setPlayback("playing")}
        onWaiting={() => setPlayback((p) => (p === "idle" ? p : "connecting"))}
        onError={() => setPlayback((p) => (p === "idle" ? p : "error"))}
      />

      {/* The TRANSPORT SITS ABOVE THE CARD ON PURPOSE. The card changes height as the
          air changes (a music slot carries track lore, a talk slot doesn't), and a
          play/stop control that moves when a programme ends is a control you have to
          chase. Above the card, its position depends only on the header — it never
          moves while you're reaching for it. */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
          <button
            type="button"
            onClick={toggle}
            disabled={!STREAM_URL}
            aria-label={playing ? "Stop the live stream" : "Play the live stream"}
            className={
              "group flex h-16 w-16 shrink-0 items-center justify-center rounded-full transition " +
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber " +
              (STREAM_URL
                ? playing
                  ? "bg-amber/15 text-amber ring-2 ring-amber hover:bg-amber/25"
                  : "bg-amber text-night shadow-[0_0_40px_-8px_rgba(242,192,77,0.55)] hover:brightness-110"
                : "cursor-not-allowed bg-neutral/10 text-neutral/40 ring-1 ring-neutral/20")
            }
          >
            {playing ? <StopGlyph /> : <PlayGlyph />}
          </button>

          <div className="flex min-w-0 flex-col gap-2">
            <p className="flex items-center gap-3 text-sm tracking-wide text-neutral/70">
              <span
                className={
                  "inline-flex items-center gap-2 font-semibold " +
                  (playing ? "text-amber" : "text-neutral/60")
                }
              >
                <span
                  className={
                    "h-2 w-2 rounded-full " +
                    (playing ? "bg-amber" : "bg-neutral/40")
                  }
                />
                LIVE
              </span>
              <span aria-hidden="true">·</span>
              <span>
                settlement time{" "}
                <time className="tabular-nums text-neutral">
                  {clock || "--:--"}
                </time>{" "}
                <span className="text-neutral/50">(yours)</span>
              </span>
            </p>
            <div className="flex items-center gap-4">
              <SignalMeter active={playing} />
              <label htmlFor="volume" className="sr-only">
                Volume
              </label>
              <input
                id="volume"
                ref={volumeRef}
                type="range"
                min={0}
                max={1}
                step={0.01}
                defaultValue={DEFAULT_VOLUME}
                onChange={(e) => {
                  const level = Number(e.target.value);
                  if (audioRef.current) audioRef.current.volume = level;
                  window.localStorage.setItem(VOLUME_KEY, String(level));
                }}
                className="h-1 w-32 cursor-pointer appearance-none rounded-full bg-neutral/20 accent-amber focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber"
              />
            </div>
          </div>
        </div>

        {/* Status, spoken plainly — never a dead-end. */}
        <p aria-live="polite" className="min-h-5 text-sm text-neutral/60">
          {!STREAM_URL
            ? "The stream isn't live yet — we're still building the transmitter."
            : playback === "error"
              ? "We couldn't reach the stream. Try again in a moment."
              : playback === "connecting"
                ? "Tuning in…"
                : ""}
        </p>
      </div>

      <OnAirCard entry={now} degraded={failed || !now} lit={playing} />

      <UpNext entries={next} />

      {/* R7.4 replaces this with the shared nav; until then the two pages still meet. */}
      <Link
        href="/schedule"
        className="self-start text-sm text-amber/90 underline-offset-4 transition-colors hover:text-amber hover:underline focus-visible:underline focus-visible:outline-none"
      >
        See the whole day&rsquo;s programmes →
      </Link>

      {/* The AI-disclosure line: visible on every route, in the station's own voice
          rather than buried in a footer (CLAUDE.md hard rule). */}
      <p className="max-w-prose text-xs leading-relaxed text-neutral/60">
        {DISCLOSURE_LINE}
      </p>
    </div>
  );
}

// --- The on-air card: the warm, glowing focus of the page --------------------

function OnAirCard({
  entry,
  degraded,
  lit,
}: {
  entry: NowPlayingEntry | null;
  degraded: boolean;
  lit: boolean;
}) {
  const hosts = entry?.hosts ?? [];
  const track = entry?.track ?? null;
  const until = wallClock(entry?.program_until);

  return (
    <section
      aria-label="On air now"
      aria-live="polite"
      className={
        // The station is on air whether or not you're listening, so the window is
        // always warm — tuning in turns the lamp up rather than switching it on.
        "tape-grain lit-window relative overflow-hidden rounded-3xl border px-6 py-8 " +
        "transition-shadow duration-700 sm:px-9 sm:py-10 " +
        (lit
          ? "border-amber/45 shadow-[0_0_110px_-25px_rgba(242,192,77,0.6)]"
          : "border-amber/20 shadow-[0_0_70px_-35px_rgba(242,192,77,0.35)]")
      }
    >
      <div className="relative flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-xs tracking-[0.18em] text-amber/90 uppercase">
          <span>{degraded ? "On air" : (entry?.format_label ?? "On air")}</span>
          {until && (
            <>
              <span aria-hidden="true" className="text-neutral/30">
                ·
              </span>
              <span className="tracking-[0.12em] text-neutral/60 normal-case">
                until {until}
              </span>
            </>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <h2 className="text-3xl leading-tight font-semibold text-neutral sm:text-4xl">
            {degraded ? "Settlement Radio" : (entry?.program ?? "Settlement Radio")}
          </h2>
          <p className="max-w-prose text-base leading-relaxed text-neutral/75">
            {degraded
              ? "Live from the settled worlds."
              : (entry?.tagline ?? "Live from the settled worlds.")}
          </p>
        </div>

        {hosts.length > 0 && (
          <ul className="flex flex-wrap items-center gap-x-5 gap-y-3">
            {hosts.map((host) => (
              <li key={host} className="flex items-center gap-2">
                <HostMarkGlyph name={host} />
                <span className="text-sm text-neutral/85">{host}</span>
              </li>
            ))}
          </ul>
        )}

        {track && (
          <div className="mt-1 rounded-2xl border border-amber/20 bg-night/50 px-5 py-4">
            <p className="text-xs tracking-[0.18em] text-amber/80 uppercase">
              Now playing
            </p>
            <p className="mt-2 text-lg font-medium text-neutral">
              {track.title}
            </p>
            <p className="text-sm text-neutral/70">
              {[track.artist, track.era, track.in_world_year]
                .filter(Boolean)
                .join(" · ")}
            </p>
            {track.story_blurb && (
              <p className="mt-2 max-w-prose text-sm leading-relaxed text-neutral/60 italic">
                {track.story_blurb}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

// --- Up next: the schedule rail, drawn as a relay thread --------------------

function UpNext({ entries }: { entries: NowPlayingEntry[] }) {
  if (entries.length === 0) return null;

  return (
    <section aria-label="Up next" className="flex flex-col gap-4">
      <h2 className="text-xs tracking-[0.2em] text-neutral/50 uppercase">
        Up next
      </h2>
      <ol className="relative flex flex-col gap-4 border-l border-neutral/15 pl-5">
        {entries.map((entry, i) => (
          <li key={`${entry.air_time}-${i}`} className="relative">
            <span
              aria-hidden="true"
              className="absolute top-2 -left-[23px] h-[7px] w-[7px] rounded-full bg-amber/60 ring-3 ring-night"
            />
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <time className="text-sm tabular-nums text-amber/90">
                {wallClock(entry.air_time)}
              </time>
              <span className="text-base text-neutral/90">
                {entry.program ?? entry.format_label ?? "Settlement Radio"}
              </span>
              {entry.hosts.length > 0 && (
                <span className="text-sm text-neutral/55">
                  with {hostList(entry.hosts)}
                </span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

// --- Glyphs (inline: no icon dependency for two shapes) ---------------------

function PlayGlyph() {
  return (
    <svg width="22" height="24" viewBox="0 0 22 24" aria-hidden="true">
      <path d="M4 2.5 19 12 4 21.5z" fill="currentColor" />
    </svg>
  );
}

function StopGlyph() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <rect x="3" y="3" width="14" height="14" rx="2.5" fill="currentColor" />
    </svg>
  );
}

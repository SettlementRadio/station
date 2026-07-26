"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import HostMarkGlyph from "@/components/HostMark";
import {
  DJS_FEED,
  SCHEDULE_FEED,
  SLOW_POLL_SECONDS,
  VOICE_SAMPLES,
  feedUrl,
  wallClock,
} from "@/lib/feeds";
import { hostMark } from "@/lib/hostMark";
import { WEEKDAY_LABELS, dayFor, nextAiring } from "@/lib/schedule";
import type { DjsFeed, PublicDj, ScheduleFeed } from "@/lib/types";
import { usePolledFeed } from "@/lib/usePolledFeed";

// R7.3 — "The DJs": the cast made real by VOICE, per canon (00-station fact 8 —
// listeners know the presenters only by their voices). No portraits anywhere; each
// host is their signal mark, their accent tone, and what they say.
//
// Two feeds: `djs-public.json` for who they are (name, role, the operator-authored
// public bio, station-vs-field, the shows they present) and `schedule-public.json` so
// each show can say when it's next on. Neither carries a line of the DJ's card — that
// is a prompt, and it never leaves the station.

export default function VoicesGrid() {
  const djs = usePolledFeed<DjsFeed>(feedUrl(DJS_FEED), SLOW_POLL_SECONDS);
  const schedule = usePolledFeed<ScheduleFeed>(
    feedUrl(SCHEDULE_FEED),
    SLOW_POLL_SECONDS,
  );
  const [now, setNow] = useState<Date | null>(null);

  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const timer = setInterval(tick, 60_000);
    return () => clearInterval(timer);
  }, []);

  if (!djs.data) {
    return (
      <p className="text-sm text-neutral/60">
        {!djs.ready
          ? "Reading the roster…"
          : "The roster isn't reachable right now — but the station is still on air."}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <ul className="grid gap-5 sm:grid-cols-2">
        {djs.data.djs.map((dj) => (
          <VoiceCard
            key={dj.id}
            dj={dj}
            schedule={schedule.data}
            now={now}
          />
        ))}
      </ul>
      {djs.failed && (
        <p className="text-xs text-neutral/45">
          (Showing the last roster we received — the station feed is unreachable.)
        </p>
      )}
    </div>
  );
}

function VoiceCard({
  dj,
  schedule,
  now,
}: {
  dj: PublicDj;
  schedule: ScheduleFeed | null;
  now: Date | null;
}) {
  const { tone } = hostMark(dj.name);
  const field = dj.based === "field";

  // "Next on: today at 18:00" for each show, from the schedule feed when we have it.
  const shows = useMemo(() => {
    if (!schedule || !now) return dj.shows.map((s) => ({ ...s, when: null }));
    const today = dayFor(schedule, now);
    return dj.shows
      .map((show) => {
        const next = nextAiring(schedule, show.id, now);
        return {
          ...show,
          when: next
            ? {
                label:
                  next.day === today
                    ? "today"
                    : (WEEKDAY_LABELS[next.day.weekday] ?? next.day.weekday),
                time: wallClock(next.entry.start),
                at: next.entry.start,
              }
            : null,
        };
      })
      .sort((a, b) => (a.when?.at ?? "~").localeCompare(b.when?.at ?? "~"));
  }, [dj.shows, schedule, now]);

  return (
    <li
      className="tape-grain relative flex flex-col gap-4 overflow-hidden rounded-2xl border border-neutral/12 bg-night-lift/60 px-5 py-5"
      style={{ borderTopColor: tone, borderTopWidth: 2 }}
    >
      <div className="flex items-start gap-3">
        <HostMarkGlyph name={dj.name} size={40} />
        <div className="flex min-w-0 flex-col gap-1">
          <h2 className="text-xl font-semibold text-neutral">{dj.name}</h2>
          {dj.role && (
            <p className="text-sm text-neutral/60 first-letter:uppercase">
              {dj.role}
            </p>
          )}
        </div>
      </div>

      {field && (
        <p
          className="flex flex-col gap-1 rounded-xl border px-3 py-2 text-xs leading-relaxed"
          style={{ borderColor: `${tone}55`, color: `${tone}` }}
        >
          <span className="font-semibold tracking-[0.14em] uppercase">
            Field correspondent
          </span>
          <span className="text-neutral/60">
            Reports across the relay — dispatches arrive with the lag, never live from
            the booth.
          </span>
        </p>
      )}

      {dj.bio && (
        <p className="text-sm leading-relaxed text-neutral/75">{dj.bio}</p>
      )}

      {VOICE_SAMPLES && <VoiceSample dj={dj} tone={tone} />}

      {shows.length > 0 && (
        <div className="flex flex-col gap-2 border-t border-neutral/10 pt-3">
          <h3 className="text-xs tracking-[0.18em] text-neutral/40 uppercase">
            On air
          </h3>
          <ul className="flex flex-col gap-1">
            {shows.map((show) => (
              <li
                key={show.id}
                className="flex flex-wrap items-baseline justify-between gap-x-3 text-sm"
              >
                <span className="text-neutral/85">{show.name}</span>
                {show.when && (
                  <span className="text-xs tabular-nums text-amber/80">
                    {show.when.label} {show.when.time}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

/**
 * The optional voice sample (R7.3 stretch, behind `NEXT_PUBLIC_VOICE_SAMPLES`).
 *
 * Plays an OPERATOR-CURATED clip at `/voices/<id>.mp3` in `web/public` — deliberately
 * not an auto-published segment, so nothing reaches the site that a human didn't
 * choose. A missing file simply hides the control again (the `onError` path), so
 * turning the flag on with only some clips present is safe.
 */
function VoiceSample({ dj, tone }: { dj: PublicDj; tone: string }) {
  const [state, setState] = useState<"idle" | "playing" | "missing">("idle");
  // The clip is an external system, so it lives in a ref — the same shape the player's
  // volume uses. (Holding it in state would be a sync setState inside an effect.)
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const el = new Audio(`/voices/${dj.id}.mp3`);
    el.preload = "metadata"; // probe now, so a missing clip hides the button
    const onEnded = () => setState("idle");
    const onError = () => setState("missing"); // no clip for this host — hide again
    el.addEventListener("ended", onEnded);
    el.addEventListener("error", onError);
    audioRef.current = el;
    return () => {
      el.pause();
      el.removeEventListener("ended", onEnded);
      el.removeEventListener("error", onError);
      audioRef.current = null;
    };
  }, [dj.id]);

  if (state === "missing") return null;

  return (
    <button
      type="button"
      onClick={() => {
        const audio = audioRef.current;
        if (!audio) return;
        if (state === "playing") {
          audio.pause();
          audio.currentTime = 0;
          setState("idle");
          return;
        }
        void audio
          .play()
          .then(() => setState("playing"))
          .catch(() => setState("missing"));
      }}
      className="self-start rounded-full border px-3 py-1.5 text-xs transition hover:brightness-125 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber"
      style={{ borderColor: `${tone}66`, color: tone }}
      aria-label={
        state === "playing"
          ? `Stop the voice sample for ${dj.name}`
          : `Hear ${dj.name}'s voice`
      }
    >
      {state === "playing" ? "■ Stop" : `▸ Hear ${dj.name}`}
    </button>
  );
}

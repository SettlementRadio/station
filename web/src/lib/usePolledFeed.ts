"use client";

import { useEffect, useState } from "react";

// R7.1 — the one polling hook every public page uses (the player now; /schedule and
// /voices in R7.2/R7.3). Deliberately small and dependency-free.
//
// Rules it keeps:
//   * NEVER breaks the page — a failed fetch sets `failed`, keeps the last good data,
//     and the caller renders its own static fallback (the player still plays).
//   * Polls only while the tab is visible (a backgrounded tab costs the station
//     bandwidth for nothing), and refetches immediately on becoming visible again.
//   * `cache: "no-store"` — the feed is the live air, not a document.

export interface PolledFeed<T> {
  /** The last successfully fetched payload, or null before the first success. */
  data: T | null;
  /** True when the most recent attempt failed (or no feed URL is configured). */
  failed: boolean;
  /** False until the first attempt settles — lets a caller show a quiet placeholder. */
  ready: boolean;
}

/** With no feed host configured there is nothing to poll — say so without state. */
const NO_FEED: PolledFeed<never> = { data: null, failed: true, ready: true };

export function usePolledFeed<T>(
  url: string | null,
  seconds: number,
): PolledFeed<T> {
  const [state, setState] = useState<PolledFeed<T>>({
    data: null,
    failed: false,
    ready: false,
  });

  useEffect(() => {
    if (!url) return; // nothing to subscribe to; the derived NO_FEED covers it

    let cancelled = false;
    const controllers = new Set<AbortController>();

    async function read() {
      if (typeof document !== "undefined" && document.hidden) return;
      const controller = new AbortController();
      controllers.add(controller);
      try {
        const res = await fetch(url!, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`feed ${res.status}`);
        const json = (await res.json()) as T;
        if (cancelled) return;
        setState({ data: json, failed: false, ready: true });
      } catch (err) {
        if (cancelled || (err as Error)?.name === "AbortError") return;
        // Keep the last good payload — stale beats blank — and flag the failure.
        setState((prev) => ({ ...prev, failed: true, ready: true }));
      } finally {
        controllers.delete(controller);
      }
    }

    function onVisible() {
      if (!document.hidden) void read();
    }

    void read();
    const timer = setInterval(() => void read(), Math.max(5, seconds) * 1000);
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      cancelled = true;
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      controllers.forEach((c) => c.abort());
    };
  }, [url, seconds]);

  return url ? state : (NO_FEED as PolledFeed<T>);
}

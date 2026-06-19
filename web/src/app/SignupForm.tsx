"use client";

import { useState } from "react";

// A2-T3: the email capture form. Posts to /api/subscribe (which holds the
// Buttondown key server-side) and surfaces success / already-subscribed / error.

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Status =
  | "idle"
  | "submitting"
  | "subscribed"
  | "already_subscribed"
  | "error";

const MESSAGES: Record<Exclude<Status, "idle" | "submitting">, string> = {
  subscribed: "You're on the list — we'll tell you when we're on air.",
  already_subscribed: "You're already on the list. Hang tight.",
  error: "Something went wrong. Please try again.",
};

export default function SignupForm() {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");

  const submitting = status === "submitting";
  const done = status === "subscribed" || status === "already_subscribed";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const form = event.currentTarget;
    const data = new FormData(form);
    const email = String(data.get("email") ?? "").trim();
    const company = String(data.get("company") ?? "");

    if (!EMAIL_RE.test(email)) {
      setStatus("error");
      setMessage("Please enter a valid email address.");
      return;
    }

    setStatus("submitting");
    setMessage("");

    try {
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, company }),
      });
      const payload = (await res.json().catch(() => ({}))) as {
        status?: string;
        error?: string;
      };

      if (res.ok && payload.status === "subscribed") {
        setStatus("subscribed");
        setMessage(MESSAGES.subscribed);
        form.reset();
      } else if (res.ok && payload.status === "already_subscribed") {
        setStatus("already_subscribed");
        setMessage(MESSAGES.already_subscribed);
      } else {
        setStatus("error");
        setMessage(payload.error ?? MESSAGES.error);
      }
    } catch {
      setStatus("error");
      setMessage(MESSAGES.error);
    }
  }

  return (
    <div className="flex w-full max-w-sm flex-col items-center gap-3">
      <form
        id="signup"
        onSubmit={handleSubmit}
        noValidate
        className="relative flex w-full flex-col gap-3 sm:flex-row"
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
          disabled={done}
          className="flex-1 rounded-md border border-amber/30 bg-white/5 px-4 py-3 text-base text-neutral placeholder:text-neutral/40 focus:border-amber focus:outline-none focus:ring-2 focus:ring-amber/60 disabled:opacity-60"
        />

        {/* Honeypot — hidden from real users, irresistible to naive bots. */}
        <div aria-hidden="true" className="absolute -left-[9999px] top-0">
          <label htmlFor="company">Company</label>
          <input
            id="company"
            name="company"
            type="text"
            tabIndex={-1}
            autoComplete="off"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || done}
          className="rounded-md bg-amber px-5 py-3 font-semibold text-night transition-colors hover:bg-amber/90 focus:outline-none focus:ring-2 focus:ring-amber/60 focus:ring-offset-2 focus:ring-offset-night disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Sending…" : "Notify me"}
        </button>
      </form>

      <p
        role="status"
        aria-live="polite"
        className={`min-h-[1.25rem] text-sm ${
          status === "error" ? "text-red-300" : "text-amber"
        }`}
      >
        {message}
      </p>
    </div>
  );
}

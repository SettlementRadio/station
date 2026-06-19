import { NextResponse, type NextRequest } from "next/server";

// A2-T3: server route that adds an email to the Buttondown list. The API key is
// read from a server-side env var and never reaches the client.

const BUTTONDOWN_SUBSCRIBERS_URL = "https://api.buttondown.com/v1/subscribers";

// Pragmatic email shape check — Buttondown does the authoritative validation.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type SubscribeBody = { email?: unknown; company?: unknown };

export async function POST(request: NextRequest) {
  let body: SubscribeBody;
  try {
    body = (await request.json()) as SubscribeBody;
  } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400 });
  }

  // Honeypot: real users never see or fill `company`. If it's set, it's a bot —
  // pretend success so we don't teach the bot what tripped the trap.
  if (typeof body.company === "string" && body.company.trim() !== "") {
    return NextResponse.json({ status: "subscribed" }, { status: 200 });
  }

  const email = typeof body.email === "string" ? body.email.trim() : "";
  if (!EMAIL_RE.test(email)) {
    return NextResponse.json(
      { error: "Please enter a valid email address." },
      { status: 400 },
    );
  }

  const apiKey = process.env.BUTTONDOWN_API_KEY;
  if (!apiKey) {
    console.error("BUTTONDOWN_API_KEY is not set");
    return NextResponse.json(
      { error: "Signup is temporarily unavailable." },
      { status: 500 },
    );
  }

  // Forward the client IP so Buttondown can apply its own spam scoring.
  const ipAddress = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();

  let res: Response;
  try {
    res = await fetch(BUTTONDOWN_SUBSCRIBERS_URL, {
      method: "POST",
      headers: {
        Authorization: `Token ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email_address: email,
        ...(ipAddress ? { ip_address: ipAddress } : {}),
      }),
    });
  } catch (err) {
    console.error("Buttondown request failed", err);
    return NextResponse.json(
      { error: "Something went wrong. Please try again." },
      { status: 502 },
    );
  }

  if (res.ok) {
    return NextResponse.json({ status: "subscribed" }, { status: 200 });
  }

  // Buttondown rejects an already-known email with 400 + code email_already_exists.
  const data = (await res.json().catch(() => null)) as
    | { code?: string; detail?: string }
    | null;
  const code = data?.code ?? "";
  const detail = (data?.detail ?? "").toLowerCase();
  if (
    res.status === 400 &&
    (code === "email_already_exists" || detail.includes("already"))
  ) {
    return NextResponse.json({ status: "already_subscribed" }, { status: 200 });
  }

  console.error("Buttondown error", res.status, data);
  return NextResponse.json(
    { error: "Something went wrong. Please try again." },
    { status: 502 },
  );
}

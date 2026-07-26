import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";

import { OG_IMAGE, PLAUSIBLE_DOMAIN } from "@/lib/site";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const title = "Settlement Radio — Late-night radio from the far future";
const description =
  "Broadcasting soon from the settled worlds of the late 27th century — news, " +
  "music, and company across the dark. A work of fiction, written and voiced " +
  "with AI, as a tribute to the science fiction that imagined us here.";

export const metadata: Metadata = {
  metadataBase: new URL("https://settlementradio.com"),
  title,
  description,
  openGraph: {
    type: "website",
    siteName: "Settlement Radio",
    url: "/",
    title,
    description,
    images: [OG_IMAGE],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: [OG_IMAGE.url],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">
        {children}
        {/* MARKETING M1 — privacy-friendly, cookieless analytics, and only when a
            domain is configured (so local and preview builds send nothing). */}
        {PLAUSIBLE_DOMAIN && (
          <Script
            defer
            data-domain={PLAUSIBLE_DOMAIN}
            src="https://plausible.io/js/script.js"
          />
        )}
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Inter } from "next/font/google";
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
    images: [
      {
        url: "/og-image.png",
        width: 1000,
        height: 1180,
        alt: "Settlement Radio — late-night radio from the far future",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: ["/og-image.png"],
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
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}

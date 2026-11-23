import type { Metadata } from "next";
import { Newsreader, Plus_Jakarta_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import ClientProviders from "@/lib/client-providers";

const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CareerForge — Precision CV & Cover Letter Studio",
  description:
    "Analyze job descriptions, uncover implied skills and red flags, and generate ATS-compliant CVs and cover letters in DOCX and PDF.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${newsreader.variable} ${plusJakarta.variable} ${ibmPlexMono.variable}`}
    >
      <body className="bg-[var(--color-bg)] text-[var(--color-text)] antialiased">
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}

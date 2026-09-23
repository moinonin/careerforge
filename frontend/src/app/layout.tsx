import type { Metadata } from "next";
import "./globals.css";
import ClientProviders from "@/lib/client-providers";

export const metadata: Metadata = {
  title: "CareerForge — AI CV Generation",
  description:
    "Generate ATS-compliant CVs and cover letters tailored to every job description. Paste a JD, get a ready-to-send DOCX and PDF.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-[var(--color-bg)] text-[var(--color-text)] antialiased">
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}

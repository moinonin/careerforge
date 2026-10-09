"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/generate", label: "Generation Studio" },
  { href: "/library", label: "Document Library" },
  { href: "/profiles", label: "Profiles" },
  { href: "/settings/llm", label: "LLM Settings" },
];

/**
 * Minimal app shell for the standalone pages (generate, library, settings).
 * Reuses the global `dashboard-*` styles from globals.css for visual
 * consistency with the dashboard page's inline sidebar.
 */
export function AppShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <div className="dashboard-sidebar-header">
          <Link href="/dashboard" className="dashboard-logo">
            <span className="dashboard-logo-mark">CF</span>
            <span className="dashboard-logo-text">CareerForge</span>
          </Link>
        </div>
        <nav className="dashboard-nav">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`dashboard-nav-item ${pathname.startsWith(item.href) ? "active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="dashboard-main">
        <header className="dashboard-header">
          <h1 className="dashboard-title">{title}</h1>
          {subtitle && <p className="dashboard-subtitle">{subtitle}</p>}
        </header>
        {children}
      </main>
    </div>
  );
}

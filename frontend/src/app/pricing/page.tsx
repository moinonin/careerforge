"use client";

import { useTheme } from "next-themes";
import Link from "next/link";
import { useState, useEffect } from "react";

const plans = [
  {
    name: "Free",
    price: "$0",
    description: "2 generations free, then $1.99 per 4 extra.",
    features: [
      "2 CV generations/month",
      "$1.99 per extra 4 generations",
      "DOCX + PDF export",
      "Basic ATS scoring",
      "Community support",
    ],
    highlighted: false,
  },
  {
    name: "Individual",
    price: "$9.99/mo",
    description: "20 generations per month for professionals.",
    features: [
      "20 generations/month",
      "DOCX + PDF export",
      "Full ATS scoring",
      "Priority support",
      "14-day free trial",
    ],
    highlighted: true,
  },
  {
    name: "Team",
    price: "$19.99/mo",
    description: "40 generation sets per month for teams.",
    features: [
      "5 seats included",
      "40 generation sets/month",
      "Shared master profiles",
      "Organization admin panel",
      "Priority support",
    ],
    highlighted: false,
  },
];

export default function PricingPage() {
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = theme === "dark";

  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-[var(--color-text-faint)] text-sm">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[rgba(0,0,0,0.08)] flex items-center justify-center text-xs font-bold">
            CF
          </div>
          <span className="text-sm font-medium tracking-tight">
            CareerForge
          </span>
        </Link>
        <Link
          href="/"
          className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
        >
          ← Back to home
        </Link>
      </nav>

      {/* Hero */}
      <section className="px-6 pt-16 pb-8 max-w-3xl mx-auto text-center">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
          Simple, transparent pricing
        </h1>
        <p className="text-[var(--color-text-secondary)] text-sm leading-relaxed">
          No hidden fees. No per-credit surprise charges. Pick the plan that
          fits your needs, or start free and upgrade anytime.
        </p>
      </section>

      {/* Plans */}
      <section className="px-6 pb-20 max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-xl border p-6 relative ${
                plan.highlighted
                  ? "bg-[var(--color-accent)]/10 border-[var(--color-accent)]/30"
                  : "bg-[var(--color-bg-elevated)] border-[var(--color-border)]"
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-[var(--color-accent)] text-black text-xs font-bold px-3 py-0.5 rounded-full">
                    Most Popular
                  </span>
                </div>
              )}
              <h2 className="text-lg font-bold mb-1">{plan.name}</h2>
              <p className="text-[var(--color-text-muted)] text-xs mb-4">
                {plan.description}
              </p>
              <p className="text-3xl font-bold mb-6">{plan.price}</p>
              <ul className="space-y-2 mb-6">
                {plan.features.map((f) => (
                  <li
                    key={f}
                    className="text-sm text-[var(--color-text-secondary)] flex items-start gap-2"
                  >
                    <span className="text-green-400">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href="/signup"
                className={`block w-full text-center py-3 rounded-xl text-sm font-medium transition-colors ${
                  plan.highlighted
                    ? "bg-[var(--color-accent)] text-black hover:opacity-90"
                    : "bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)]"
                }`}
              >
                {plan.name === "Free" ? "Get Started" : "Start Free Trial"}
              </Link>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
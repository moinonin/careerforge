"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

interface BillingData {
  plan_tier: string;
  status: string;
  credits_remaining: number;
  trial_ends_at: string | null;
  current_period_end: string | null;
}

interface CreditBundle {
  id: string;
  name: string;
  credits: number;
  price_cents: number;
}

export default function BillingPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [billing, setBilling] = useState<BillingData | null>(null);
  const [creditBundles, setCreditBundles] = useState<CreditBundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [checkingOut, setCheckingOut] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
      return;
    }
    if (user) {
      fetchBilling();
      fetchCreditBundles();
    }
  }, [user, authLoading, router]);

  async function fetchBilling() {
    try {
      const res = await fetch("/api/v1/billing/subscription");
      if (res.ok) {
        const data: BillingData = await res.json();
        setBilling(data);
      }
    } catch {
      // ignore
    }
  }

  async function fetchCreditBundles() {
    try {
      const res = await fetch("/api/v1/billing/credit-bundles");
      if (res.ok) {
        const data: CreditBundle[] = await res.json();
        setCreditBundles(data);
      }
    } catch {
      // ignore
    }
  }

  async function handleCheckout(type: string, creditPackageId?: string) {
    setCheckingOut(true);
    try {
      const res = await fetch("/api/v1/billing/checkout-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          credit_package_id: creditPackageId,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        window.location.href = data.checkout_url;
      } else {
        const err = await res.json();
        alert(err.detail || "Checkout failed");
      }
    } catch {
      alert("Checkout failed");
    } finally {
      setCheckingOut(false);
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex items-center justify-center">
        <div className="text-[var(--color-text-faint)] text-sm">Loading billing...</div>
      </div>
    );
  }

  const daysLeft = billing?.current_period_end
    ? Math.ceil(
        (new Date(billing.current_period_end).getTime() - Date.now()) /
          (1000 * 60 * 60 * 24),
      )
    : null;

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[rgba(0,0,0,0.08)] flex items-center justify-center text-xs font-bold">
            CF
          </div>
          <span className="text-sm font-medium tracking-tight">CareerForge</span>
        </Link>
        <Link
          href="/dashboard"
          className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
        >
          ← Dashboard
        </Link>
      </nav>

      <section className="px-6 pt-12 pb-8 max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Billing</h1>
        <p className="text-[var(--color-text-low)] text-sm">Manage your subscription and credits.</p>
      </section>

      {/* Current Plan */}
      <section className="px-6 pb-8 max-w-3xl mx-auto">
        <div className="bg-[rgba(0,0,0,0.04)] rounded-xl p-6 border border-[rgba(0,0,0,0.04)]">
          <h2 className="text-lg font-semibold mb-4">Current Plan</h2>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl font-bold capitalize">
              {billing?.plan_tier || "Trial"}
            </span>
            <span className="text-xs bg-[rgba(0,0,0,0.08)] px-2.5 py-0.5 rounded-full">
              {billing?.status}
            </span>
          </div>
          {billing?.plan_tier === "trial" && billing?.trial_ends_at && (
            <p className="text-sm text-[var(--color-text-low)]">
              Trial ends in{" "}
              {Math.ceil(
                (new Date(billing.trial_ends_at).getTime() - Date.now()) /
                  (1000 * 60 * 60 * 24),
              )}{" "}
              days
            </p>
          )}
          {billing?.plan_tier !== "trial" && billing?.current_period_end && (
            <p className="text-sm text-[var(--color-text-low)]">
              Renews in {daysLeft} days ({billing.current_period_end})
            </p>
          )}
          <div className="mt-4 space-y-2">
            <p className="text-sm text-[var(--color-text-medium)]">
              Credits remaining: <strong>{billing?.credits_remaining ?? 0}</strong>
            </p>
          </div>
        </div>
      </section>

      {/* Credit Bundles */}
      <section className="px-6 pb-8 max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold mb-4">Buy Credits</h2>
        <div className="grid gap-3">
          {creditBundles.map((pkg) => (
            <div
              key={pkg.id}
              className="flex items-center justify-between bg-[rgba(0,0,0,0.04)] rounded-xl p-4 border border-[rgba(0,0,0,0.04)]"
            >
              <div>
                <p className="font-medium">{pkg.name}</p>
                <p className="text-xs text-[var(--color-text-faint)]">{pkg.credits} credits</p>
              </div>
              <button
                onClick={() => handleCheckout("credit_bundle", pkg.id)}
                disabled={checkingOut}
                className="bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-40"
              >
                ${(pkg.price_cents / 100).toFixed(2)}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Subscription Actions */}
      <section className="px-6 pb-8 max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold mb-4">Subscription</h2>
        <div className="flex flex-wrap gap-3">
          {billing?.plan_tier === "trial" && (
            <button
              onClick={() => handleCheckout("subscription_individual")}
              disabled={checkingOut}
              className="bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm px-5 py-2.5 rounded-full transition-colors"
            >
              Upgrade to Individual ($19.99/mo)
            </button>
          )}
          {billing?.plan_tier !== "trial" && (
            <button
              onClick={() => handleCheckout("subscription_team")}
              disabled={checkingOut}
              className="bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm px-5 py-2.5 rounded-full transition-colors"
            >
              Change to Team ($79.99/mo)
            </button>
          )}
          {billing?.plan_tier !== "trial" && (
            <button
              onClick={async () => {
                const res = await fetch("/api/v1/billing/cancel", {
                  method: "POST",
                });
                if (res.ok) {
                  fetchBilling();
                }
              }}
              disabled={checkingOut}
              className="bg-red-500/10 hover:bg-red-500/15 text-red-300 text-sm px-5 py-2.5 rounded-full transition-colors"
            >
              Cancel Subscription
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
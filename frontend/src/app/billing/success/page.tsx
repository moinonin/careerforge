"use client";

export const dynamic = "force-dynamic";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

function BillingSuccessContent() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");

  useEffect(() => {
    if (sessionId) {
      fetch(`/api/v1/billing/webhook`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      }).catch(() => {});
    }
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg
            className="w-8 h-8 text-green-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-bold mb-2">Payment Successful!</h1>
        <p className="text-[var(--color-text-low)] text-sm mb-6">
          Your subscription or credit bundle has been activated. You can
          now access all features.
        </p>
        <Link
          href="/dashboard"
          className="inline-block bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm px-6 py-3 rounded-full transition-colors"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function BillingSuccessPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex items-center justify-center">Loading...</div>}>
      <BillingSuccessContent />
    </Suspense>
  );
}

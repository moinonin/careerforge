"use client";

export const dynamic = "force-dynamic";

import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg
            className="w-8 h-8 text-amber-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        <h1 className="text-2xl font-bold mb-2">Payment Canceled</h1>
        <p className="text-[var(--color-text-low)] text-sm mb-6">
          Your payment was not processed. If you intended to cancel,
          your current plan will remain active until the end of the
          billing period.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/billing"
            className="bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm px-6 py-3 rounded-full transition-colors"
          >
            Try Again
          </Link>
          <Link
            href="/dashboard"
            className="bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm px-6 py-3 rounded-full transition-colors"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
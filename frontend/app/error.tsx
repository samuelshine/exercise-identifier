"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, RotateCw } from "lucide-react";

/**
 * Global error boundary — catches any uncaught client error during render
 * outside the EDP route. Next.js automatically wraps the page in this
 * component if it exists.
 *
 * Logging hook here is the right place to forward to Sentry once it's wired.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("[GlobalError]", error);
    }
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/8 border border-red-500/15">
        <AlertCircle className="h-7 w-7 text-red-400" aria-hidden="true" />
      </div>
      <h1 className="mt-4 text-base font-semibold text-neutral-200">
        Something went wrong
      </h1>
      <p className="mt-1 max-w-xs text-sm text-neutral-500">
        An unexpected error interrupted your session. You can retry, or head back to search.
      </p>

      <div className="mt-6 flex flex-col gap-2 w-full max-w-xs">
        <button
          onClick={reset}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-white shadow-glow-accent transition-colors hover:bg-accent-light active:bg-accent-dim active:scale-[0.98] no-select"
        >
          <RotateCw className="h-4 w-4" aria-hidden="true" />
          Try again
        </button>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-xl bg-surface-200 px-4 py-2.5 text-sm font-medium text-neutral-300 transition-colors hover:bg-surface-300 hover:text-neutral-100 no-select"
        >
          Back to search
        </Link>
      </div>

      {error.digest && (
        <p className="mt-6 font-mono text-[10px] text-neutral-700">
          ref: {error.digest}
        </p>
      )}
    </main>
  );
}

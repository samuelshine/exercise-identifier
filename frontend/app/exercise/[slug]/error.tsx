"use client";

import { useEffect } from "react";
import Link from "next/link";
import { AlertCircle, ArrowLeft, RotateCw } from "lucide-react";

/**
 * Scoped error boundary for the EDP route. The page already handles
 * fetch errors gracefully (PageError), so this catches *render* errors —
 * a bad muscle map prop, a Framer Motion regression, etc.
 */
export default function ExerciseError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") {
      console.error("[ExerciseError]", error);
    }
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/8 border border-red-500/15">
        <AlertCircle className="h-7 w-7 text-red-400" aria-hidden="true" />
      </div>
      <div>
        <p className="text-base font-semibold text-neutral-300">
          Couldn't load this exercise
        </p>
        <p className="mt-1 max-w-xs text-sm text-neutral-600">
          The page hit an unexpected error. You can retry or head back to the search.
        </p>
      </div>

      <div className="flex gap-2">
        <button
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-neutral-950 transition-colors hover:bg-accent/90 active:scale-[0.98] no-select"
        >
          <RotateCw className="h-4 w-4" aria-hidden="true" />
          Retry
        </button>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-surface-200 px-4 py-2.5 text-sm font-medium text-neutral-300 transition-colors hover:bg-surface-300 hover:text-neutral-100 no-select"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </Link>
      </div>

      {error.digest && (
        <p className="mt-2 font-mono text-[10px] text-neutral-700">
          ref: {error.digest}
        </p>
      )}
    </main>
  );
}

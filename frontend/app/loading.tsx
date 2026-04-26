import { Loader2 } from "lucide-react";

/**
 * Route-level fallback shown while a server component or the next route
 * is being fetched. Mirrors the EDP PageSpinner styling so transitions
 * feel consistent across the app.
 */
export default function Loading() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-accent/60" aria-hidden="true" />
      <p className="text-sm text-neutral-500">Loading…</p>
    </main>
  );
}

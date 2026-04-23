import { Skeleton } from "@/components/ui/Skeleton";

/**
 * Loading placeholder that exactly mirrors the shape of ResultCard.
 *
 * Uses the `.skeleton` shimmer animation from globals.css.
 * Rendered 3× while the search pipeline runs (embed → vector → LLM → response).
 */
export function ResultSkeleton() {
  return (
    <div
      className="glass-card flex items-center gap-4 rounded-2xl p-4"
      aria-hidden="true"
      role="presentation"
    >
      {/* Ring placeholder */}
      <div className="flex-shrink-0">
        <Skeleton className="h-12 w-12 rounded-full" />
      </div>

      {/* Content placeholder */}
      <div className="flex-1 space-y-2.5">
        {/* Rank + name row */}
        <div className="flex items-center gap-2">
          <Skeleton className="h-3 w-5" />
          <Skeleton className="h-4 w-40" />
        </div>

        {/* Badge row */}
        <div className="flex gap-1.5">
          <Skeleton className="h-4 w-16 rounded-full" />
          <Skeleton className="h-4 w-24 rounded-full" />
        </div>

        {/* Muscle pills */}
        <div className="flex gap-1">
          <Skeleton className="h-4 w-14 rounded-full" />
          <Skeleton className="h-4 w-16 rounded-full" />
          <Skeleton className="h-4 w-12 rounded-full" />
        </div>

        {/* Reasoning text — two lines */}
        <div className="space-y-1.5">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
      </div>

      {/* Chevron placeholder */}
      <div className="flex-shrink-0">
        <Skeleton className="h-4 w-4" />
      </div>
    </div>
  );
}

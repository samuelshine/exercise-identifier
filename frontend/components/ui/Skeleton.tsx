import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

/**
 * Base skeleton block — applies the shimmer animation defined in globals.css.
 * Compose multiples of these to match the shape of the content being loaded.
 */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "skeleton rounded-lg",
        className
      )}
      aria-hidden="true"
    />
  );
}

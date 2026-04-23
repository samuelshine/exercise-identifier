"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

import { AlternativeMatch, AlternativeRelationship, formatLabel } from "@/lib/types";
import { Skeleton } from "@/components/ui/Skeleton";

interface AlternativesListProps {
  alternatives: AlternativeMatch[];
  isLoading?: boolean;
}

// Relationship display metadata
const RELATIONSHIP_META: Record<
  AlternativeRelationship,
  { label: string; className: string }
> = {
  substitute_for: {
    label: "Substitute",
    className:
      "bg-accent/8 text-accent-light border-accent/15",
  },
  variation_of: {
    label: "Variation",
    className:
      "bg-surface-200 text-neutral-400 border-white/8",
  },
  progression_of: {
    label: "Progression",
    className:
      "bg-amber-500/8 text-amber-400 border-amber-500/15",
  },
  regression_of: {
    label: "Regression",
    className:
      "bg-orange-500/8 text-orange-400 border-orange-500/15",
  },
};

function AlternativeCard({
  alt,
  index,
}: {
  alt: AlternativeMatch;
  index: number;
}) {
  const router = useRouter();
  const meta = RELATIONSHIP_META[alt.relationship_type];

  return (
    <motion.article
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: "easeOut", delay: index * 0.06 }}
      onClick={() => router.push(`/exercise/${alt.exercise.slug}`)}
      className="
        glass-card glass-card-hover group
        flex w-52 flex-shrink-0 cursor-pointer flex-col justify-between
        rounded-2xl p-4 active:scale-[0.98] transition-transform
      "
      role="button"
      tabIndex={0}
      onKeyDown={(e) =>
        (e.key === "Enter" || e.key === " ") &&
        router.push(`/exercise/${alt.exercise.slug}`)
      }
      aria-label={`${alt.exercise.primary_name} — ${meta.label}`}
    >
      {/* Relationship badge */}
      <span
        className={`
          inline-flex w-fit items-center rounded-full border px-2 py-0.5
          text-2xs font-semibold uppercase tracking-wider
          ${meta.className}
        `}
      >
        {meta.label}
      </span>

      {/* Exercise name */}
      <div className="mt-3 flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold leading-snug text-neutral-100 group-hover:text-accent-light transition-colors line-clamp-2">
          {alt.exercise.primary_name}
        </h3>
        <ChevronRight
          className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-neutral-700 transition-all group-hover:translate-x-0.5 group-hover:text-accent"
          aria-hidden="true"
        />
      </div>

      {/* Difficulty + movement pattern */}
      <div className="mt-2.5 flex flex-wrap gap-1">
        <span
          className={`badge-${alt.exercise.difficulty} inline-flex items-center rounded-full px-2 py-0.5 text-2xs font-medium uppercase tracking-wider`}
        >
          {alt.exercise.difficulty}
        </span>
        <span className="inline-flex items-center rounded-full bg-surface-200 px-2 py-0.5 text-2xs text-neutral-500 uppercase tracking-wider">
          {formatLabel(alt.exercise.movement_pattern)}
        </span>
      </div>

      {/* Primary muscles */}
      {alt.exercise.primary_muscles.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {alt.exercise.primary_muscles.slice(0, 2).map((m) => (
            <span key={m} className="muscle-pill muscle-pill-primary">
              {formatLabel(m)}
            </span>
          ))}
          {alt.exercise.primary_muscles.length > 2 && (
            <span className="muscle-pill">
              +{alt.exercise.primary_muscles.length - 2}
            </span>
          )}
        </div>
      )}

      {/* Optional note */}
      {alt.note && (
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-neutral-600">
          {alt.note}
        </p>
      )}
    </motion.article>
  );
}

function AlternativeSkeleton() {
  return (
    <div
      className="glass-card flex w-52 flex-shrink-0 flex-col gap-3 rounded-2xl p-4"
      aria-hidden="true"
      role="presentation"
    >
      <Skeleton className="h-4 w-20 rounded-full" />
      <Skeleton className="h-4 w-36" />
      <div className="flex gap-1.5">
        <Skeleton className="h-4 w-16 rounded-full" />
        <Skeleton className="h-4 w-20 rounded-full" />
      </div>
      <div className="flex gap-1">
        <Skeleton className="h-4 w-14 rounded-full" />
        <Skeleton className="h-4 w-14 rounded-full" />
      </div>
    </div>
  );
}

/**
 * Horizontal swipable list of alternative exercises for the EDP.
 *
 * Layout: edge-to-edge bleed via `-mx-4 px-4` so cards can scroll
 * beneath the page padding without a hard cutoff.
 *
 * Each card: 208px (w-52) fixed width, rounded-2xl glass card with
 * relationship badge, name, difficulty, movement pattern, primary muscles.
 *
 * Shows 3 skeleton cards while alternatives are being fetched.
 */
export function AlternativesList({
  alternatives,
  isLoading = false,
}: AlternativesListProps) {
  if (!isLoading && alternatives.length === 0) return null;

  return (
    <section aria-label="Alternative exercises">
      {/* Section label */}
      <div className="px-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-500">
          Alternatives
        </h2>
      </div>

      {/* Horizontal scroll container — bleeds to screen edges */}
      <div
        className="flex overflow-x-auto no-scrollbar -mx-4 px-4 gap-3 pb-2"
        role="list"
      >
        {isLoading
          ? [0, 1, 2].map((i) => <AlternativeSkeleton key={i} />)
          : alternatives.map((alt, i) => (
              <AlternativeCard key={alt.exercise.id} alt={alt} index={i} />
            ))}

        {/* Trailing spacer so the last card isn't flush against the edge */}
        <div className="w-4 flex-shrink-0" aria-hidden="true" />
      </div>
    </section>
  );
}

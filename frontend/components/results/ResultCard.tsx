"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

import { SearchResultItem } from "@/lib/types";
import { formatLabel, scoreToColor } from "@/lib/types";

interface ResultCardProps {
  result: SearchResultItem;
  index: number; // used for stagger delay
}

// SVG ring constants — radius chosen so the ring sits at a clean size
const RING_RADIUS = 18;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS; // ≈ 113.1

/**
 * A single search result card with:
 * - Animated confidence ring (SVG stroke-dashoffset driven by score)
 * - Exercise name and primary muscles
 * - Reasoning text from the LLM judge
 * - Tap/click → navigate to the Exercise Detail Page
 *
 * Motion: card fades up from 12px below, staggered by index × 80ms.
 */
export function ResultCard({ result, index }: ResultCardProps) {
  const router = useRouter();
  const { exercise, similarity_score: score, reasoning, rank } = result;
  const ringColor = scoreToColor(score);

  // Stroke offset: 0 = full ring, circumference = empty ring
  const ringOffset = RING_CIRCUMFERENCE * (1 - score);
  const scorePercent = Math.round(score * 100);

  function handleSelect() {
    router.push(`/exercise/${exercise.slug}`);
  }

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: 0.35,
        ease: "easeOut",
        delay: index * 0.08,
      }}
      // Glass card + hover effect
      className="glass-card glass-card-hover group relative flex cursor-pointer items-center gap-4 rounded-2xl p-4"
      onClick={handleSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && handleSelect()}
      aria-label={`${exercise.primary_name}, ${scorePercent}% match`}
    >
      {/* ── Confidence ring ────────────────────────────────────────────────── */}
      <div className="flex-shrink-0" aria-hidden="true">
        <svg
          width={48}
          height={48}
          viewBox="0 0 48 48"
          className="rotate-[-90deg]" // start fill from top
        >
          {/* Track */}
          <circle
            cx={24}
            cy={24}
            r={RING_RADIUS}
            fill="none"
            strokeWidth={3.5}
            className="confidence-ring-track"
          />
          {/* Fill */}
          <circle
            cx={24}
            cy={24}
            r={RING_RADIUS}
            fill="none"
            strokeWidth={3.5}
            stroke={ringColor}
            strokeDasharray={RING_CIRCUMFERENCE}
            strokeDashoffset={ringOffset}
            strokeLinecap="round"
            className="confidence-ring-fill"
            style={{
              "--ring-color": ringColor,
              "--ring-circumference": RING_CIRCUMFERENCE,
              "--ring-offset": ringOffset,
            } as React.CSSProperties}
          />
          {/* Score text — rendered at 0deg (counter-rotated) */}
          <text
            x={24}
            y={24}
            dominantBaseline="central"
            textAnchor="middle"
            className="rotate-90 fill-neutral-200 font-mono text-[9px] font-semibold"
            style={{ transform: "rotate(90deg)", transformOrigin: "24px 24px" }}
          >
            {scorePercent}%
          </text>
        </svg>
      </div>

      {/* ── Exercise info ──────────────────────────────────────────────────── */}
      <div className="min-w-0 flex-1">
        {/* Rank + name */}
        <div className="flex items-baseline gap-2">
          <span className="flex-shrink-0 text-2xs font-semibold uppercase tracking-widest text-neutral-600">
            #{rank}
          </span>
          <h3 className="truncate text-base font-semibold text-neutral-100 group-hover:text-accent-light transition-colors">
            {exercise.primary_name}
          </h3>
        </div>

        {/* Difficulty + movement badges */}
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          <span className={`badge-${exercise.difficulty} inline-flex items-center rounded-full px-2 py-0.5 text-2xs font-medium uppercase tracking-wider`}>
            {exercise.difficulty}
          </span>
          <span className="inline-flex items-center rounded-full bg-surface-200 px-2 py-0.5 text-2xs text-neutral-400 uppercase tracking-wider">
            {formatLabel(exercise.movement_pattern)}
          </span>
        </div>

        {/* Primary muscles */}
        {exercise.primary_muscles.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {exercise.primary_muscles.slice(0, 3).map((m) => (
              <span key={m} className="muscle-pill muscle-pill-primary">
                {formatLabel(m)}
              </span>
            ))}
            {exercise.primary_muscles.length > 3 && (
              <span className="muscle-pill">+{exercise.primary_muscles.length - 3}</span>
            )}
          </div>
        )}

        {/* Reasoning — capped at 2 lines */}
        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-neutral-500">
          {reasoning}
        </p>
      </div>

      {/* ── Chevron ────────────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 text-neutral-700 transition-all group-hover:translate-x-0.5 group-hover:text-accent">
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </div>
    </motion.article>
  );
}

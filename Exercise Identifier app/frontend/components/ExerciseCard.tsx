"use client";

import { motion } from "framer-motion";
import { Dumbbell, Zap, ChevronRight } from "lucide-react";
import { SearchResultItem } from "@/lib/types";
import ConfidenceRing from "./ConfidenceRing";

interface ExerciseCardProps {
  result: SearchResultItem;
  index: number;
  onClick: () => void;
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ExerciseCard({
  result,
  index,
  onClick,
}: ExerciseCardProps) {
  const { exercise, similarity_score, matched_description, reasoning } = result;

  return (
    <motion.div
      layoutId={`card-${exercise.id}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: index * 0.1,
        duration: 0.45,
        ease: [0.22, 1, 0.36, 1],
      }}
      onClick={onClick}
      className="glass-card glass-card-hover group cursor-pointer rounded-3xl p-5 sm:p-6 transition-all duration-300 hover:scale-[1.01] active:scale-[0.99]"
    >
      <div className="flex items-start gap-3.5">
        {/* De-emphasized Confidence Ring */}
        <ConfidenceRing score={similarity_score} size={44} strokeWidth={3} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Name + difficulty — elevated title */}
          <div className="flex items-center gap-2.5 mb-1">
            <h3 className="text-xl font-bold text-white truncate">
              {exercise.primary_name}
            </h3>
            <span className="flex-shrink-0 rounded-md bg-white/[0.04] border border-white/[0.06] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-neutral-400">
              {exercise.difficulty}
            </span>
          </div>

          {/* LLM Reasoning */}
          {reasoning && (
            <p className="text-sm text-accent-light/70 leading-relaxed line-clamp-2 mb-2">
              {reasoning}
            </p>
          )}

          {/* Matched description (fallback if no reasoning) */}
          {!reasoning && (
            <p className="text-sm text-neutral-500 leading-relaxed line-clamp-2 mb-2.5">
              &ldquo;{matched_description}&rdquo;
            </p>
          )}

          {/* Muscle pills — fixed contrast */}
          <div className="flex flex-wrap gap-1.5">
            {exercise.primary_muscles.map((m) => (
              <span key={m} className="muscle-pill-primary">
                {formatLabel(m)}
              </span>
            ))}
            {exercise.secondary_muscles.slice(0, 3).map((m) => (
              <span
                key={m}
                className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide uppercase bg-white/10 text-neutral-300 border border-white/[0.08]"
              >
                {formatLabel(m)}
              </span>
            ))}
          </div>
        </div>

        {/* Expand indicator */}
        <div className="flex-shrink-0 self-center">
          <ChevronRight className="h-5 w-5 text-neutral-600 group-hover:text-neutral-400 transition-colors" />
        </div>
      </div>

      {/* Footer meta */}
      <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center gap-4 text-[11px] text-neutral-600">
        <div className="flex items-center gap-1.5">
          <Dumbbell className="h-3.5 w-3.5" />
          <span>{exercise.equipment_required.map(formatLabel).join(", ") || "Bodyweight"}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Zap className="h-3.5 w-3.5" />
          <span>{formatLabel(exercise.movement_pattern)}</span>
        </div>
        <span className="ml-auto">
          {exercise.mechanic === "compound" ? "Compound" : "Isolation"}
        </span>
      </div>
    </motion.div>
  );
}

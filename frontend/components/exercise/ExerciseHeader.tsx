"use client";

import { motion } from "framer-motion";
import { Dumbbell, Zap, RefreshCw } from "lucide-react";

import {
  DifficultyLevel,
  EquipmentType,
  ExerciseAlias,
  MovementPattern,
  formatLabel,
} from "@/lib/types";

interface ExerciseHeaderProps {
  primaryName: string;
  aliases: ExerciseAlias[];
  difficulty: DifficultyLevel;
  mechanic: "compound" | "isolation";
  movementPattern: MovementPattern;
  isUnilateral: boolean;
  equipmentRequired: EquipmentType[];
}

/**
 * EDP header section.
 *
 * Layout (top → bottom):
 *   Difficulty badge + mechanic chip
 *   Exercise primary name (large)
 *   Aliases row (horizontal scroll)
 *   Equipment pills
 *
 * Motion: all elements fade up from 8px on mount, staggered at 60ms intervals.
 */
export function ExerciseHeader({
  primaryName,
  aliases,
  difficulty,
  mechanic,
  movementPattern,
  isUnilateral,
  equipmentRequired,
}: ExerciseHeaderProps) {
  return (
    <motion.header
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.06 } },
      }}
      className="flex flex-col gap-3 px-4 pt-4"
    >
      {/* ── Badge row ─────────────────────────────────────────────────────── */}
      <motion.div
        variants={fadeUp}
        className="flex flex-wrap items-center gap-2"
      >
        {/* Difficulty */}
        <span
          className={`badge-${difficulty} inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider`}
        >
          {difficulty}
        </span>

        {/* Mechanic */}
        <span className="inline-flex items-center gap-1 rounded-full bg-surface-200 px-2.5 py-0.5 text-xs text-neutral-400 uppercase tracking-wider">
          {mechanic === "compound" ? (
            <Zap className="h-3 w-3 text-accent-light" aria-hidden="true" />
          ) : (
            <RefreshCw className="h-3 w-3 text-neutral-500" aria-hidden="true" />
          )}
          {mechanic}
        </span>

        {/* Movement pattern */}
        <span className="inline-flex items-center rounded-full bg-surface-200 px-2.5 py-0.5 text-xs text-neutral-400 uppercase tracking-wider">
          {formatLabel(movementPattern)}
        </span>

        {/* Unilateral indicator */}
        {isUnilateral && (
          <span className="inline-flex items-center rounded-full bg-accent/8 border border-accent/15 px-2.5 py-0.5 text-xs text-accent-light uppercase tracking-wider">
            Unilateral
          </span>
        )}
      </motion.div>

      {/* ── Primary name ──────────────────────────────────────────────────── */}
      <motion.h1
        variants={fadeUp}
        className="text-2xl font-bold leading-tight tracking-tight text-neutral-100"
      >
        {primaryName}
      </motion.h1>

      {/* ── Aliases ───────────────────────────────────────────────────────── */}
      {aliases.length > 0 && (
        <motion.div
          variants={fadeUp}
          className="flex items-center gap-2"
          aria-label="Also known as"
        >
          <span className="flex-shrink-0 text-xs text-neutral-600 uppercase tracking-wider">
            aka
          </span>
          {/* Horizontal scroll for many aliases */}
          <div className="flex overflow-x-auto no-scrollbar gap-1.5 pb-0.5">
            {aliases.map((a) => (
              <span
                key={a.id}
                className="flex-shrink-0 rounded-full bg-surface-100 px-2.5 py-0.5 text-xs text-neutral-400 border border-white/5"
              >
                {a.alias}
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* ── Equipment ─────────────────────────────────────────────────────── */}
      {equipmentRequired.length > 0 && (
        <motion.div variants={fadeUp} className="flex flex-wrap items-center gap-1.5">
          <Dumbbell
            className="h-3.5 w-3.5 flex-shrink-0 text-neutral-600"
            aria-hidden="true"
          />
          {equipmentRequired.map((eq) => (
            <span
              key={eq}
              className="inline-flex items-center rounded-md bg-surface-100 px-2 py-0.5 text-xs text-neutral-400 border border-white/5"
            >
              {formatLabel(eq)}
            </span>
          ))}
        </motion.div>
      )}

      {/* Divider */}
      <motion.hr variants={fadeUp} className="divider-fade mt-1" />
    </motion.header>
  );
}

// Shared motion variant — reused across all child elements
const fadeUp = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease: "easeOut" } },
};

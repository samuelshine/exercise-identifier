"use client";

import { motion } from "framer-motion";
import { Box, ChevronRight } from "lucide-react";

import { MovementDescriptor } from "@/lib/types";

interface FormViewerProps {
  exerciseName: string;
  descriptors: MovementDescriptor[];
}

// Categories surfaced in the cues section, in display order
const CUE_CATEGORIES: MovementDescriptor["category"][] = [
  "setup",
  "execution",
  "cue",
  "common_mistake",
];

const CATEGORY_LABEL: Record<string, string> = {
  setup: "Setup",
  execution: "Execution",
  cue: "Form Cue",
  common_mistake: "Common Mistake",
};

const CATEGORY_COLOR: Record<string, string> = {
  setup: "text-accent-light",
  execution: "text-neutral-300",
  cue: "text-emerald-400",
  common_mistake: "text-amber-400",
};

/**
 * EDP form viewer section.
 *
 * Phase 1: polished placeholder for the 3D avatar (`.model-placeholder`)
 *          with a "Coming in Phase 2" badge.
 * Phase 2: replace the placeholder div with the actual <ModelViewer> component.
 *
 * Below the media area: structured text cues derived from MovementDescriptor
 * records, grouped by category (setup → execution → cue → common_mistake).
 */
export function FormViewer({ exerciseName, descriptors }: FormViewerProps) {
  // Group descriptors by category, preserving insertion order within each group
  const grouped = new Map<string, MovementDescriptor[]>();
  for (const d of descriptors) {
    if (!CUE_CATEGORIES.includes(d.category)) continue;
    if (!grouped.has(d.category)) grouped.set(d.category, []);
    grouped.get(d.category)!.push(d);
  }

  // Pull the summary descriptor if present
  const summary = descriptors.find((d) => d.category === "summary");

  return (
    <section className="px-4" aria-label="Form and technique">
      {/* ── Section label ─────────────────────────────────────────────────── */}
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-500">
        Form & Technique
      </h2>

      {/* ── 3D avatar placeholder ─────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="model-placeholder relative flex h-56 flex-col items-center justify-center rounded-2xl"
        aria-label={`3D form demonstration for ${exerciseName} — coming soon`}
        role="img"
      >
        {/* Icon */}
        <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/8 border border-accent/15">
          <Box className="h-7 w-7 text-accent/60" aria-hidden="true" />
        </div>

        {/* Label */}
        <p className="text-sm font-medium text-neutral-400">{exerciseName}</p>
        <p className="mt-1 text-xs text-neutral-600">3D form demonstration</p>

        {/* Phase badge */}
        <span className="mt-4 inline-flex items-center rounded-full bg-surface-200 px-3 py-1 text-xs text-neutral-500 border border-white/5">
          Coming in Phase 2
        </span>
      </motion.div>

      {/* ── Summary ───────────────────────────────────────────────────────── */}
      {summary && (
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.1 }}
          className="mt-4 text-sm leading-relaxed text-neutral-400"
        >
          {summary.text}
        </motion.p>
      )}

      {/* ── Cue groups ────────────────────────────────────────────────────── */}
      {CUE_CATEGORIES.map((cat, groupIdx) => {
        const items = grouped.get(cat);
        if (!items || items.length === 0) return null;
        const label = CATEGORY_LABEL[cat];
        const color = CATEGORY_COLOR[cat];

        return (
          <motion.div
            key={cat}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 + groupIdx * 0.07 }}
            className="mt-4"
          >
            {/* Category heading */}
            <p className={`mb-2 text-xs font-semibold uppercase tracking-wider ${color}`}>
              {label}
            </p>

            {/* Cue items */}
            <ul className="flex flex-col gap-2">
              {items.map((d) => (
                <li
                  key={d.id}
                  className="flex items-start gap-2.5 rounded-xl bg-surface-100 px-3.5 py-3 border border-white/5"
                >
                  <ChevronRight
                    className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-neutral-600"
                    aria-hidden="true"
                  />
                  <p className="text-sm leading-relaxed text-neutral-300">{d.text}</p>
                </li>
              ))}
            </ul>
          </motion.div>
        );
      })}
    </section>
  );
}

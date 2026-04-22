"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Dumbbell,
  Zap,
  Target,
  Activity,
  Play,
  RotateCcw,
} from "lucide-react";
import { SearchResultItem } from "@/lib/types";
import ConfidenceRing from "./ConfidenceRing";

interface ExerciseModalProps {
  result: SearchResultItem | null;
  onClose: () => void;
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ExerciseModal({ result, onClose }: ExerciseModalProps) {
  return (
    <AnimatePresence>
      {result && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            layoutId={`card-${result.exercise.id}`}
            className="fixed inset-x-4 top-[5vh] bottom-[5vh] z-50 mx-auto max-w-2xl overflow-y-auto rounded-3xl glass-card border-white/[0.08] shadow-2xl"
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
          >
            <div className="p-6 sm:p-8">
              {/* Header */}
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                  <ConfidenceRing score={result.similarity_score} size={72} strokeWidth={4} />
                  <div>
                    <h2 className="text-2xl font-bold text-white">
                      {result.exercise.primary_name}
                    </h2>
                    <div className="mt-1 flex items-center gap-2 text-sm text-neutral-500">
                      <span className="capitalize">{result.exercise.difficulty}</span>
                      <span className="text-neutral-700">·</span>
                      <span>{result.exercise.mechanic === "compound" ? "Compound" : "Isolation"}</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={onClose}
                  className="rounded-xl p-2 text-neutral-500 hover:text-white hover:bg-white/5 transition"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* 3D Model Placeholder */}
              <div className="model-placeholder rounded-2xl h-48 sm:h-56 flex flex-col items-center justify-center mb-6">
                <div className="rounded-full bg-accent/10 p-3 mb-3">
                  <Play className="h-6 w-6 text-accent-light" />
                </div>
                <p className="text-sm text-neutral-500 font-light">
                  3D Movement Preview
                </p>
                <p className="text-xs text-neutral-700 mt-1">Coming soon</p>
              </div>

              {/* Summary */}
              {result.exercise.summary && (
                <div className="mb-6">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
                    Summary
                  </h3>
                  <p className="text-sm text-neutral-300 leading-relaxed">
                    {result.exercise.summary}
                  </p>
                </div>
              )}

              {/* Matched description */}
              <div className="mb-6 rounded-2xl bg-accent/[0.04] border border-accent/10 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-accent-light/60 mb-2">
                  Why this matched
                </h3>
                <p className="text-sm text-neutral-400 leading-relaxed italic">
                  &ldquo;{result.matched_description}&rdquo;
                </p>
              </div>

              {/* Details grid */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                <DetailBlock
                  icon={<Target className="h-4 w-4" />}
                  label="Primary Muscles"
                  values={result.exercise.primary_muscles}
                  highlight
                />
                <DetailBlock
                  icon={<Activity className="h-4 w-4" />}
                  label="Secondary Muscles"
                  values={result.exercise.secondary_muscles}
                />
                <DetailBlock
                  icon={<Dumbbell className="h-4 w-4" />}
                  label="Equipment"
                  values={result.exercise.equipment_required}
                />
                <DetailBlock
                  icon={<Zap className="h-4 w-4" />}
                  label="Movement Pattern"
                  values={[result.exercise.movement_pattern]}
                />
              </div>

              {/* Aliases */}
              {result.exercise.aliases.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2.5">
                    Also known as
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {result.exercise.aliases.map((a) => (
                      <span
                        key={a.id}
                        className="rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1 text-xs text-neutral-400"
                      >
                        {a.alias}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* All beginner descriptions */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2.5 flex items-center gap-1.5">
                  <RotateCcw className="h-3.5 w-3.5" />
                  All Descriptions
                </h3>
                <div className="space-y-2">
                  {result.exercise.movement_descriptors
                    .filter((d) => d.category === "beginner_description")
                    .map((d) => (
                      <div
                        key={d.id}
                        className="rounded-xl bg-white/[0.02] border border-white/[0.04] px-4 py-2.5 text-sm text-neutral-400 leading-relaxed"
                      >
                        &ldquo;{d.text}&rdquo;
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function DetailBlock({
  icon,
  label,
  values,
  highlight = false,
}: {
  icon: React.ReactNode;
  label: string;
  values: string[];
  highlight?: boolean;
}) {
  return (
    <div className="rounded-2xl bg-white/[0.02] border border-white/[0.04] p-3.5">
      <div className="flex items-center gap-1.5 mb-2 text-neutral-600">
        {icon}
        <span className="text-[10px] font-semibold uppercase tracking-wider">
          {label}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span
            key={v}
            className={highlight ? "muscle-pill-primary" : "muscle-pill"}
          >
            {formatLabel(v)}
          </span>
        ))}
      </div>
    </div>
  );
}

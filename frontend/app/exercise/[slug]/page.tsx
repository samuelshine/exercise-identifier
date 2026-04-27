"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, ArrowLeft, Loader2 } from "lucide-react";

import { ExerciseHeader } from "@/components/exercise/ExerciseHeader";
import { MuscleMap } from "@/components/exercise/MuscleMap";
import { FormViewer } from "@/components/exercise/FormViewer";
import { AlternativesList } from "@/components/exercise/AlternativesList";

import { getExercise, getAlternatives, ApiError } from "@/lib/api";
import { AlternativeMatch, Exercise } from "@/lib/types";

// ─── Segmented control ────────────────────────────────────────────────────────

type Tab = "form" | "anatomy";

const TABS: { id: Tab; label: string }[] = [
  { id: "form",    label: "Form"    },
  { id: "anatomy", label: "Anatomy" },
];

function SegmentedControl({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Exercise detail view"
      className="relative flex rounded-xl bg-surface-100 p-1"
    >
      {TABS.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`
              relative z-10 flex-1 rounded-lg py-2 text-sm font-semibold
              transition-colors duration-200 no-select
              ${isActive ? "text-neutral-100" : "text-neutral-500 hover:text-neutral-300"}
            `}
          >
            {/* Sliding indicator — sits behind the label text */}
            {isActive && (
              <motion.span
                layoutId="tab-pill"
                className="absolute inset-0 rounded-lg bg-surface-300"
                transition={{ type: "spring", stiffness: 420, damping: 36 }}
                aria-hidden="true"
              />
            )}
            <span className="relative">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}

// ─── Page-level loading spinner ───────────────────────────────────────────────

function PageSpinner() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
      <Loader2 className="h-8 w-8 animate-spin text-accent/60" aria-hidden="true" />
      <p className="text-sm text-neutral-500">Loading exercise…</p>
    </div>
  );
}

// ─── Page-level error ─────────────────────────────────────────────────────────

function PageError({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/8 border border-red-500/15">
        <AlertCircle className="h-7 w-7 text-red-400" aria-hidden="true" />
      </div>
      <div>
        <p className="text-base font-semibold text-neutral-300">Exercise not found</p>
        <p className="mt-1 text-sm text-neutral-600">{message}</p>
      </div>
      <button
        onClick={onBack}
        className="mt-2 inline-flex items-center gap-2 rounded-xl bg-surface-200 px-4 py-2.5 text-sm font-medium text-neutral-300 transition-colors hover:bg-surface-300 hover:text-neutral-100"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to search
      </button>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

/**
 * Exercise Detail Page (EDP) — `/exercise/[slug]`
 *
 * Layout (mobile-first, single column):
 *   ┌─────────────────────────────────────────┐
 *   │  Back button                            │
 *   │  ExerciseHeader                         │
 *   │  SegmentedControl  [Form | Anatomy]     │
 *   │  AnimatePresence → FormViewer           │
 *   │                  → MuscleMap            │
 *   │  AlternativesList (horizontal scroll)   │
 *   │  (pb-safe: iOS home-bar clearance)      │
 *   └─────────────────────────────────────────┘
 *
 * Data fetching:
 *   - Exercise:    GET /exercises/slug/{slug}
 *   - Alternatives: GET /exercises/{id}/alternatives  (parallel, after exercise resolves)
 *
 * Both requests are initiated client-side on mount. Alternatives load
 * independently — the page is usable before they arrive.
 */
export default function ExercisePage() {
  const params   = useParams<{ slug: string }>();
  const router   = useRouter();
  const slug     = params?.slug ?? "";

  const [exercise,     setExercise]     = useState<Exercise | null>(null);
  const [alternatives, setAlternatives] = useState<AlternativeMatch[]>([]);
  const [altLoading,   setAltLoading]   = useState(true);
  const [pageState,    setPageState]    = useState<"loading" | "ready" | "error">("loading");
  const [errorMsg,     setErrorMsg]     = useState("");
  const [activeTab,    setActiveTab]    = useState<Tab>("form");

  // Guard against double-fetch in React strict mode
  const fetchedSlug = useRef<string>("");

  useEffect(() => {
    if (!slug || fetchedSlug.current === slug) return;
    fetchedSlug.current = slug;

    let cancelled = false;

    async function load() {
      setPageState("loading");
      setExercise(null);
      setAlternatives([]);
      setAltLoading(true);

      // ── Stage 1: load exercise ─────────────────────────────────────────
      let ex: Exercise;
      try {
        ex = await getExercise(slug);
      } catch (err) {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? err.detail
            : "Failed to load exercise. Try again.";
        setErrorMsg(msg);
        setPageState("error");
        return;
      }

      if (cancelled) return;
      setExercise(ex);
      setPageState("ready");

      // ── Stage 2: load alternatives in parallel ─────────────────────────
      try {
        const res = await getAlternatives(ex.id);
        if (!cancelled) setAlternatives(res.alternatives);
      } catch {
        // Alternatives failing is non-fatal — page still works
      } finally {
        if (!cancelled) setAltLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [slug]);

  // ── Back navigation ────────────────────────────────────────────────────────
  // Deep links land here with no history, so router.back() would no-op —
  // fall back to the home page in that case.
  function goBack() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
    } else {
      router.push("/");
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <main className="flex min-h-screen flex-col pb-safe">
      {/* ── Back button ─────────────────────────────────────────────────────── */}
      <div className="flex items-center px-4 pt-safe pt-3">
        <button
          onClick={goBack}
          className="touch-target inline-flex items-center gap-1.5 rounded-xl py-2 pr-3 text-sm font-medium text-neutral-500 transition-colors hover:text-neutral-200 active:text-neutral-300 no-select"
          aria-label="Back to search results"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </button>
      </div>

      {/* ── Main content ─────────────────────────────────────────────────────── */}
      {pageState === "loading" && <PageSpinner />}

      {pageState === "error" && (
        <PageError message={errorMsg} onBack={goBack} />
      )}

      {pageState === "ready" && exercise && (
        <div className="flex flex-col gap-5 pb-8">
          {/* ── Header ──────────────────────────────────────────────────────── */}
          <ExerciseHeader
            primaryName={exercise.primary_name}
            aliases={exercise.aliases}
            difficulty={exercise.difficulty}
            mechanic={exercise.mechanic}
            movementPattern={exercise.movement_pattern}
            isUnilateral={exercise.is_unilateral}
            equipmentRequired={exercise.equipment_required}
          />

          {/* ── Segmented control ────────────────────────────────────────────── */}
          <div className="px-4">
            <SegmentedControl active={activeTab} onChange={setActiveTab} />
          </div>

          {/* ── Tab content ──────────────────────────────────────────────────── */}
          <div
            role="tabpanel"
            aria-label={activeTab === "form" ? "Form and technique" : "Muscle anatomy"}
          >
            <AnimatePresence mode="wait">
              {activeTab === "form" ? (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2, ease: "easeInOut" }}
                >
                  <FormViewer
                    exerciseName={exercise.primary_name}
                    descriptors={exercise.movement_descriptors}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="anatomy"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2, ease: "easeInOut" }}
                >
                  <MuscleMap
                    primaryMuscles={exercise.primary_muscles}
                    secondaryMuscles={exercise.secondary_muscles}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ── Divider ──────────────────────────────────────────────────────── */}
          <hr className="divider-fade mx-4" />

          {/* ── Alternatives ─────────────────────────────────────────────────── */}
          <AlternativesList
            alternatives={alternatives}
            isLoading={altLoading}
          />
        </div>
      )}
    </main>
  );
}

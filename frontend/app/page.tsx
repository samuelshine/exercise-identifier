"use client";

import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Dumbbell } from "lucide-react";

import { SearchBar } from "@/components/search/SearchBar";
import { ResultCard } from "@/components/results/ResultCard";
import { ResultSkeleton } from "@/components/results/ResultSkeleton";
import { useSearch } from "@/hooks/useSearch";

/**
 * Home page — the primary search interface.
 *
 * Layout (mobile-first, single column):
 *   ┌─────────────────────────────────────────────┐
 *   │  Hero / brand mark  (hidden once results show) │
 *   │  SearchBar                                    │
 *   │  Results or skeleton or error                 │
 *   │  (pb-safe: iOS home-bar clearance)            │
 *   └─────────────────────────────────────────────┘
 *
 * The hero section slides up and shrinks as the user gets results,
 * keeping the search bar near the top of the visible area.
 */
export default function Home() {
  const { query, results, state, error, search } = useSearch(5);

  const hasResults  = state === "success" && results.length > 0;
  const isLoading   = state === "loading";
  const hasError    = state === "error";
  const noResults   = state === "success" && results.length === 0;
  const hasSearched = state !== "idle";

  return (
    <main className="flex min-h-screen flex-col px-4 pb-safe pt-safe">
      {/* ── Hero — visible only before first search ───────────────────────── */}
      <AnimatePresence>
        {!hasSearched && (
          <motion.header
            key="hero"
            initial={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="flex flex-col items-center justify-center py-16 text-center overflow-hidden"
          >
            {/* Brand mark */}
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-3xl bg-accent/10 ring-1 ring-accent/20">
              <Dumbbell className="h-8 w-8 text-accent" aria-hidden="true" />
            </div>

            <h1 className="text-3xl font-bold tracking-tight text-neutral-100">
              <span className="text-gradient-accent">Identify</span>
            </h1>
            <p className="mt-2 max-w-xs text-sm leading-relaxed text-neutral-500">
              Describe any exercise you see in the gym. We'll tell you exactly what it is.
            </p>

            {/* Example prompts — tappable to pre-fill */}
            <div className="mt-8 flex flex-col gap-2 w-full max-w-sm">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => search(prompt)}
                  className="rounded-xl bg-surface-100 px-4 py-2.5 text-left text-sm text-neutral-400 transition-colors hover:bg-surface-200 hover:text-neutral-300 active:scale-[0.98] no-select"
                >
                  <span className="text-neutral-600 mr-2" aria-hidden="true">→</span>
                  {prompt}
                </button>
              ))}
            </div>
          </motion.header>
        )}
      </AnimatePresence>

      {/* ── Search bar — always visible, floats to top after search ──────── */}
      <div className={`w-full ${hasSearched ? "pt-8" : ""}`}>
        <SearchBar onSearch={search} isLoading={isLoading} />
      </div>

      {/* ── Results area ─────────────────────────────────────────────────── */}
      <section
        className="mt-4 flex flex-col gap-3 pb-8"
        aria-label="Search results"
        aria-live="polite"
        aria-busy={isLoading}
      >
        {/* Loading skeletons */}
        {isLoading && (
          <>
            {[0, 1, 2].map((i) => (
              <ResultSkeleton key={i} />
            ))}
          </>
        )}

        {/* Error state */}
        {hasError && error && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3 rounded-2xl bg-red-500/8 border border-red-500/15 p-4"
            role="alert"
          >
            <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-400" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-red-400">Search failed</p>
              <p className="mt-0.5 text-xs text-neutral-500">{error}</p>
            </div>
          </motion.div>
        )}

        {/* No results */}
        {noResults && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl bg-surface-100 p-6 text-center"
          >
            <p className="text-sm font-medium text-neutral-400">No matches found</p>
            <p className="mt-1 text-xs text-neutral-600">
              Try describing the movement differently — body position, equipment used, or which muscles you felt working.
            </p>
          </motion.div>
        )}

        {/* Results — stagger handled inside ResultCard via motion props */}
        {hasResults && (
          <>
            {/* Results header */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="px-1 text-xs text-neutral-600"
            >
              {results.length} match{results.length !== 1 ? "es" : ""} for{" "}
              <span className="text-neutral-400">&ldquo;{query}&rdquo;</span>
            </motion.p>

            {results.map((result, i) => (
              <ResultCard key={result.exercise.id} result={result} index={i} />
            ))}
          </>
        )}
      </section>
    </main>
  );
}

// ─── Example prompts ──────────────────────────────────────────────────────────
// Surface common search patterns to help new users understand the input style.
// These are also effective test cases for the semantic search quality.

const EXAMPLE_PROMPTS = [
  "lying on a bench pushing two dumbbells up toward the ceiling",
  "sitting and pulling a wide bar down to my chest",
  "standing and pulling a bar up toward my chin with a narrow grip",
  "bending over and rowing a barbell to my stomach",
] as const;

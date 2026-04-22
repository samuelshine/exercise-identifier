"use client";

import { useState, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import SearchHero from "@/components/SearchHero";
import ExerciseCard from "@/components/ExerciseCard";
import ExerciseModal from "@/components/ExerciseModal";
import Toast from "@/components/Toast";
import { searchExercises, ApiError } from "@/lib/api";
import { SearchResultItem } from "@/lib/types";

export default function Home() {
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResultItem | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (query: string) => {
    setIsLoading(true);
    setError(null);
    setResults([]);
    setHasSearched(true);

    try {
      const data = await searchExercises(query, 5);
      setResults(data.results);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  return (
    <main className="relative min-h-screen flex flex-col">
      {/* Ambient background glow */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 h-[600px] w-[800px] rounded-full bg-accent/[0.03] blur-[120px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 flex flex-col">
        {/* Hero section — pushes down when results appear */}
        <motion.div
          animate={{
            paddingTop: hasSearched ? "3rem" : "25vh",
          }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="w-full"
        >
          <SearchHero onSearch={handleSearch} isLoading={isLoading} />
        </motion.div>

        {/* Results */}
        <AnimatePresence mode="wait">
          {results.length > 0 && (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 0.1 }}
              className="w-full max-w-2xl mx-auto px-4 mt-10 pb-16"
            >
              {/* Results header */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between mb-5"
              >
                <p className="text-sm text-neutral-600">
                  <span className="text-neutral-400 font-medium">
                    {results.length}
                  </span>{" "}
                  {results.length === 1 ? "match" : "matches"} found
                </p>
                <div className="h-px flex-1 ml-4 bg-gradient-to-r from-white/[0.06] to-transparent" />
              </motion.div>

              {/* Cards */}
              <div className="space-y-3">
                {results.map((result, i) => (
                  <ExerciseCard
                    key={result.exercise.id}
                    result={result}
                    index={i}
                    onClick={() => setSelectedResult(result)}
                  />
                ))}
              </div>
            </motion.div>
          )}

          {/* Empty state */}
          {hasSearched && !isLoading && results.length === 0 && !error && (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="w-full max-w-md mx-auto px-4 mt-12 text-center"
            >
              <div className="rounded-2xl glass-card p-8">
                <p className="text-neutral-400 text-sm">
                  No matching exercises found. Try describing the movement
                  differently.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Detail Modal */}
      <ExerciseModal
        result={selectedResult}
        onClose={() => setSelectedResult(null)}
      />

      {/* Error Toast */}
      <Toast
        message={error || ""}
        visible={!!error}
        onDismiss={() => setError(null)}
      />
    </main>
  );
}

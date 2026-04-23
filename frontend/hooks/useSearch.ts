"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError, searchExercises } from "@/lib/api";
import { SearchResultItem } from "@/lib/types";

export type SearchState = "idle" | "loading" | "success" | "error";

export interface UseSearchReturn {
  query: string;
  results: SearchResultItem[];
  state: SearchState;
  error: string | null;
  search: (q: string) => Promise<void>;
  clear: () => void;
}

/**
 * Manages the full search lifecycle — query, loading, results, and error states.
 *
 * Includes a request-cancellation guard: if a new search fires before the
 * previous one resolves (e.g. user submits twice rapidly), the stale result
 * is silently discarded and only the latest response updates state.
 */
export function useSearch(topK: number = 5): UseSearchReturn {
  const [query, setQuery]     = useState<string>("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [state, setState]     = useState<SearchState>("idle");
  const [error, setError]     = useState<string | null>(null);

  // Tracks the in-flight request so we can detect and discard stale responses
  const reqIdRef = useRef<number>(0);

  const search = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed || trimmed.length < 3) return;

      // Assign a unique ID to this request
      const thisReqId = ++reqIdRef.current;

      setQuery(trimmed);
      setState("loading");
      setError(null);
      setResults([]);

      try {
        const data = await searchExercises(trimmed, topK);

        // Guard: only update state if this is still the latest request
        if (thisReqId !== reqIdRef.current) return;

        setResults(data.results);
        setState("success");
      } catch (err) {
        if (thisReqId !== reqIdRef.current) return;

        const message =
          err instanceof ApiError
            ? err.detail
            : "An unexpected error occurred. Please try again.";

        setError(message);
        setState("error");
      }
    },
    [topK]
  );

  const clear = useCallback(() => {
    reqIdRef.current++; // invalidate any in-flight request
    setQuery("");
    setResults([]);
    setState("idle");
    setError(null);
  }, []);

  return { query, results, state, error, search, clear };
}

"use client";

import { useEffect, useRef, useState } from "react";
import { Search, X, Loader2 } from "lucide-react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
  initialValue?: string;
}

/**
 * Primary search input.
 *
 * Design decisions:
 * - Auto-focuses on mount — the PWA's entire purpose is to search, so the
 *   keyboard should be ready immediately on open.
 * - Submit on Enter or button click — no debounce (search is explicit, not
 *   reactive). This keeps the UX predictable and avoids mid-word API calls.
 * - 48px minimum touch target on the submit/clear buttons (touch-target class).
 * - `search-input-wrap` from globals.css provides the glow-on-focus effect.
 * - Disabled during loading — prevents duplicate in-flight requests.
 */
export function SearchBar({ onSearch, isLoading = false, initialValue = "" }: SearchBarProps) {
  const [value, setValue] = useState(initialValue);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus on mount — gym context: open app → type immediately
  useEffect(() => {
    // Slight delay prevents the keyboard from flashing during PWA splash
    const t = setTimeout(() => inputRef.current?.focus(), 100);
    return () => clearTimeout(t);
  }, []);

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = value.trim();
    if (trimmed.length >= 3 && !isLoading) {
      onSearch(trimmed);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit();
  }

  function handleClear() {
    setValue("");
    inputRef.current?.focus();
  }

  const canSubmit = value.trim().length >= 3 && !isLoading;
  const showClear = value.length > 0 && !isLoading;

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full"
      role="search"
      aria-label="Exercise search"
    >
      <div className="search-input-wrap flex items-center gap-3 rounded-2xl px-4 py-3.5">
        {/* Search icon — shows spinner while loading */}
        <div className="flex-shrink-0 text-neutral-500">
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin text-accent" aria-hidden="true" />
          ) : (
            <Search className="h-5 w-5" aria-hidden="true" />
          )}
        </div>

        {/* Input */}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you saw… e.g. pulling a bar down while sitting"
          disabled={isLoading}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
          className={`
            flex-1 bg-transparent text-base text-neutral-100
            placeholder:text-neutral-600
            outline-none
            disabled:opacity-50
          `}
          aria-label="Describe the exercise"
          aria-busy={isLoading}
        />

        {/* Clear button — shown when there's text and not loading */}
        {showClear && (
          <button
            type="button"
            onClick={handleClear}
            className="touch-target flex-shrink-0 rounded-full p-1 text-neutral-500 transition-colors hover:text-neutral-300 no-select"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={!canSubmit}
          className={`
            touch-target flex-shrink-0 rounded-xl px-3.5 py-2
            text-sm font-semibold transition-all duration-150 no-select
            ${canSubmit
              ? "bg-accent text-white shadow-glow-accent hover:bg-accent-light active:bg-accent-dim"
              : "bg-surface-200 text-neutral-600 cursor-not-allowed"
            }
          `}
          aria-label="Search"
        >
          Identify
        </button>
      </div>

      {/* Min-length hint — only shown when user has started typing but not enough */}
      {value.length > 0 && value.trim().length < 3 && (
        <p className="mt-2 px-4 text-xs text-neutral-600" role="status">
          Keep typing — need at least 3 characters
        </p>
      )}
    </form>
  );
}

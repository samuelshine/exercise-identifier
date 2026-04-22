"use client";

import { motion } from "framer-motion";
import { Search, Loader2 } from "lucide-react";
import { useState, useRef } from "react";

interface SearchHeroProps {
  onSearch: (query: string) => void;
  isLoading: boolean;
}

const SUGGESTIONS = [
  "lying on my back pushing a bar up",
  "sitting down and pulling a bar to my chest",
  "standing and curling weights with my arms",
  "bending over and rowing a weight to my hip",
];

export default function SearchHero({ onSearch, isLoading }: SearchHeroProps) {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 3 && !isLoading) {
      onSearch(query.trim());
    }
  };

  const handleSuggestion = (suggestion: string) => {
    setQuery(suggestion);
    onSearch(suggestion);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="w-full max-w-2xl mx-auto px-4"
    >
      {/* Title */}
      <div className="text-center mb-10">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.5 }}
        >
          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight bg-gradient-to-b from-white to-neutral-400 bg-clip-text text-transparent">
            Identify
          </h1>
          <p className="mt-2 text-lg text-neutral-500 font-light">
            Describe any exercise. We&apos;ll find it.
          </p>
        </motion.div>
      </div>

      {/* Search Input */}
      <form onSubmit={handleSubmit}>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5 }}
          className={`search-glow relative rounded-2xl border transition-all duration-300 ${
            isFocused
              ? "border-accent/40 bg-surface-200"
              : "border-white/[0.06] bg-surface-100"
          }`}
        >
          <div className="flex items-center px-5 py-4">
            {isLoading ? (
              <Loader2 className="h-5 w-5 text-accent-light animate-spin flex-shrink-0" />
            ) : (
              <Search className="h-5 w-5 text-neutral-500 flex-shrink-0" />
            )}
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Describe the movement you saw..."
              disabled={isLoading}
              className="ml-3 flex-1 bg-transparent text-base text-neutral-100 placeholder:text-neutral-600 outline-none disabled:opacity-50"
            />
            {query.length > 0 && !isLoading && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                type="submit"
                className="ml-3 rounded-xl bg-accent/10 px-4 py-2 text-sm font-medium text-accent-light hover:bg-accent/20 transition-colors"
              >
                Search
              </motion.button>
            )}
          </div>
        </motion.div>
      </form>

      {/* Loading State */}
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-6 text-center"
        >
          <div className="inline-flex items-center gap-2.5 rounded-full bg-accent/5 border border-accent/10 px-4 py-2">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-accent-light"
                  animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    delay: i * 0.2,
                  }}
                />
              ))}
            </div>
            <span className="text-sm text-accent-light/70 font-light">
              Analyzing biomechanics...
            </span>
          </div>
        </motion.div>
      )}

      {/* Suggestions */}
      {!isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 flex flex-wrap justify-center gap-2"
        >
          {SUGGESTIONS.map((s, i) => (
            <motion.button
              key={s}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.08 }}
              onClick={() => handleSuggestion(s)}
              className="rounded-full border border-white/[0.06] bg-white/[0.02] px-3.5 py-1.5 text-xs text-neutral-500 hover:text-neutral-300 hover:border-white/10 hover:bg-white/[0.04] transition-all duration-200"
            >
              &ldquo;{s}&rdquo;
            </motion.button>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}

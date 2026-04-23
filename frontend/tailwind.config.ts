import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Dark mode is always active via the `dark` class on <html>
  // We apply it at build time — no user toggle for V1
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // ─── Background surfaces (dark-first) ─────────────────────────────
        // Usage: bg-surface (page), bg-surface-100 (cards), bg-surface-200 (hover)
        surface: {
          DEFAULT: "#09090b", // zinc-950 — base page background
          50:      "#0d0d0f",
          100:     "#18181b", // zinc-900 — cards, modals
          200:     "#27272a", // zinc-800 — hover states, input backgrounds
          300:     "#3f3f46", // zinc-700 — subtle dividers, borders
          400:     "#52525b", // zinc-600 — disabled states
        },

        // ─── Accent (indigo) ───────────────────────────────────────────────
        // Primary interactive color: focus rings, active states, CTAs
        // Note: PRD specified blue (#3B82F6) but indigo (#6366f1) was chosen
        // in the initial scaffold for better contrast on dark surfaces.
        // Decision documented in As-Built log.
        accent: {
          DEFAULT: "#6366f1", // indigo-500
          light:   "#818cf8", // indigo-400 — gradients, hover
          dim:     "#4f46e5", // indigo-600 — pressed states
          glow:    "rgba(99, 102, 241, 0.15)", // ambient glow behind cards
          ring:    "rgba(99, 102, 241, 0.30)", // focus ring color
          muted:   "rgba(99, 102, 241, 0.08)", // faint tint backgrounds
        },

        // ─── Confidence / match quality ────────────────────────────────────
        // Used on result cards to visually represent similarity scores
        match: {
          high:   "#34d399", // emerald-400 — score ≥ 0.85
          mid:    "#fbbf24", // amber-400   — score 0.60–0.84
          low:    "#f87171", // red-400     — score < 0.60
        },

        // ─── Muscle anatomy highlights ─────────────────────────────────────
        // Used in the MuscleMap component for anatomical overlays
        muscle: {
          primary:   "#ef4444", // red-500   — primary targeted muscles
          secondary: "#f97316", // orange-500 — secondary/synergist muscles
          inactive:  "rgba(255,255,255,0.04)", // untargeted muscle fill
        },

        // ─── Status / system feedback ──────────────────────────────────────
        status: {
          success: "#22c55e", // green-500
          warning: "#eab308", // yellow-500
          error:   "#ef4444", // red-500
          info:    "#3b82f6", // blue-500
        },
      },

      // ─── Typography ────────────────────────────────────────────────────
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Menlo", "monospace"],
      },
      fontSize: {
        // Gym UI: large primary text, very small metadata labels
        "2xs": ["0.625rem", { lineHeight: "1rem" }],      // 10px — micro labels
        xs:    ["0.75rem",  { lineHeight: "1.125rem" }],   // 12px — tags, badges
        sm:    ["0.875rem", { lineHeight: "1.375rem" }],   // 14px — body small
        base:  ["1rem",     { lineHeight: "1.5rem" }],     // 16px — body
        lg:    ["1.125rem", { lineHeight: "1.75rem" }],    // 18px
        xl:    ["1.25rem",  { lineHeight: "1.75rem" }],    // 20px — card titles
        "2xl": ["1.5rem",   { lineHeight: "2rem" }],       // 24px — section heads
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],    // 30px — exercise name
        "4xl": ["2.25rem",  { lineHeight: "2.75rem" }],    // 36px — hero
      },

      // ─── Spacing & border radius ────────────────────────────────────────
      borderRadius: {
        "2xl": "1rem",    // 16px — standard card
        "3xl": "1.25rem", // 20px — modal, large cards
        "4xl": "1.5rem",  // 24px — search input
        "5xl": "2rem",    // 32px — pill buttons
      },

      // ─── Backdrop blur ──────────────────────────────────────────────────
      backdropBlur: {
        xs: "2px",   // subtle — status overlays
        sm: "8px",   // light glass
        md: "12px",  // standard glassmorphism
        lg: "20px",  // heavy glass — modals
      },

      // ─── Animations & keyframes ─────────────────────────────────────────
      animation: {
        // Skeleton loader — pulsing shimmer
        shimmer: "shimmer 2s linear infinite",
        // Card entrance — stagger applied via style={{ animationDelay }}
        "fade-up": "fade-up 0.4s ease-out both",
        // Accent glow on focused inputs / active cards
        "glow-pulse": "glow-pulse 2.5s ease-in-out infinite",
        // Confidence ring fill (SVG strokeDashoffset driven by CSS var)
        "ring-fill": "ring-fill 1s cubic-bezier(0.4, 0, 0.2, 1) both",
        // Recording indicator — pulsing red dot
        "record-pulse": "record-pulse 1.2s ease-in-out infinite",
      },
      keyframes: {
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition:  "200% 0" },
        },
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(99, 102, 241, 0.08)" },
          "50%":      { boxShadow: "0 0 40px rgba(99, 102, 241, 0.22)" },
        },
        "ring-fill": {
          "0%":   { strokeDashoffset: "var(--ring-circumference)" },
          "100%": { strokeDashoffset: "var(--ring-offset)" },
        },
        "record-pulse": {
          "0%, 100%": { opacity: "1",   transform: "scale(1)" },
          "50%":      { opacity: "0.5", transform: "scale(0.85)" },
        },
      },

      // ─── Box shadows ────────────────────────────────────────────────────
      boxShadow: {
        // Card elevation levels
        "card-sm": "0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)",
        "card-md": "0 4px 16px rgba(0,0,0,0.5), 0 2px 6px rgba(0,0,0,0.4)",
        "card-lg": "0 12px 40px rgba(0,0,0,0.6), 0 4px 12px rgba(0,0,0,0.5)",
        // Accent glow (input focus, active result)
        "glow-accent": "0 0 0 1px rgba(99,102,241,0.35), 0 0 30px rgba(99,102,241,0.12), 0 0 60px rgba(99,102,241,0.06)",
        // Inset for pressed states
        "inset-sm": "inset 0 1px 2px rgba(0,0,0,0.3)",
      },

      // ─── Z-index scale ──────────────────────────────────────────────────
      zIndex: {
        "base":    "0",
        "raised":  "10",
        "overlay": "20",
        "modal":   "30",
        "toast":   "40",
        "max":     "50",
      },
    },
  },
  plugins: [],
};

export default config;

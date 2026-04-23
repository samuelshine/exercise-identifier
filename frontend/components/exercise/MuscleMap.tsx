"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { MuscleGroup, formatLabel } from "@/lib/types";

interface MuscleMapProps {
  primaryMuscles: MuscleGroup[];
  secondaryMuscles: MuscleGroup[];
}

type View = "front" | "back";

// ─── Muscle zone geometry ─────────────────────────────────────────────────────
// Each zone maps to one or more SVG ellipse/rect descriptors.
// viewBox: "0 0 120 290" — front and back silhouettes sit side by side
// but are rendered in separate SVGs per tab view.
// Coordinates tuned to match a simple anatomical body outline at this scale.

interface Zone {
  muscles: MuscleGroup[];
  view: View;
  // SVG shape — either ellipse or rect
  shape: "ellipse" | "rect";
  // Ellipse params
  cx?: number; cy?: number; rx?: number; ry?: number;
  // Rect params
  x?: number; y?: number; width?: number; height?: number; rx_r?: number;
}

const MUSCLE_ZONES: Zone[] = [
  // ── FRONT VIEW ──────────────────────────────────────────────────────────────
  // Chest (pectorals)
  { muscles: ["chest"], view: "front", shape: "ellipse", cx: 60, cy: 100, rx: 28, ry: 15 },
  // Front delts
  { muscles: ["front_delt"], view: "front", shape: "ellipse", cx: 31, cy: 93, rx: 9, ry: 10 },
  { muscles: ["front_delt"], view: "front", shape: "ellipse", cx: 89, cy: 93, rx: 9, ry: 10 },
  // Side delts
  { muscles: ["side_delt"], view: "front", shape: "ellipse", cx: 26, cy: 90, rx: 7, ry: 8 },
  { muscles: ["side_delt"], view: "front", shape: "ellipse", cx: 94, cy: 90, rx: 7, ry: 8 },
  // Biceps
  { muscles: ["biceps"], view: "front", shape: "ellipse", cx: 24, cy: 118, rx: 7, ry: 14 },
  { muscles: ["biceps"], view: "front", shape: "ellipse", cx: 96, cy: 118, rx: 7, ry: 14 },
  // Forearms
  { muscles: ["forearms"], view: "front", shape: "ellipse", cx: 22, cy: 148, rx: 6, ry: 14 },
  { muscles: ["forearms"], view: "front", shape: "ellipse", cx: 98, cy: 148, rx: 6, ry: 14 },
  // Abs / Core
  { muscles: ["abs", "core"], view: "front", shape: "rect", x: 50, y: 118, width: 20, height: 30, rx_r: 4 },
  // Obliques
  { muscles: ["obliques"], view: "front", shape: "ellipse", cx: 40, cy: 133, rx: 10, ry: 14 },
  { muscles: ["obliques"], view: "front", shape: "ellipse", cx: 80, cy: 133, rx: 10, ry: 14 },
  // Quads
  { muscles: ["quads"], view: "front", shape: "ellipse", cx: 46, cy: 195, rx: 14, ry: 28 },
  { muscles: ["quads"], view: "front", shape: "ellipse", cx: 74, cy: 195, rx: 14, ry: 28 },
  // Adductors
  { muscles: ["adductors"], view: "front", shape: "ellipse", cx: 55, cy: 195, rx: 8, ry: 22 },
  { muscles: ["adductors"], view: "front", shape: "ellipse", cx: 65, cy: 195, rx: 8, ry: 22 },
  // Hip flexors
  { muscles: ["hip_flexors"], view: "front", shape: "ellipse", cx: 48, cy: 163, rx: 10, ry: 8 },
  { muscles: ["hip_flexors"], view: "front", shape: "ellipse", cx: 72, cy: 163, rx: 10, ry: 8 },
  // Calves (front visible)
  { muscles: ["calves"], view: "front", shape: "ellipse", cx: 45, cy: 252, rx: 10, ry: 18 },
  { muscles: ["calves"], view: "front", shape: "ellipse", cx: 75, cy: 252, rx: 10, ry: 18 },

  // ── BACK VIEW ───────────────────────────────────────────────────────────────
  // Traps
  { muscles: ["traps"], view: "back", shape: "ellipse", cx: 60, cy: 88, rx: 22, ry: 10 },
  // Rear delts
  { muscles: ["rear_delt"], view: "back", shape: "ellipse", cx: 32, cy: 93, rx: 9, ry: 9 },
  { muscles: ["rear_delt"], view: "back", shape: "ellipse", cx: 88, cy: 93, rx: 9, ry: 9 },
  // Upper back (rhomboids / mid traps)
  { muscles: ["upper_back"], view: "back", shape: "rect", x: 42, y: 98, width: 36, height: 20, rx_r: 4 },
  // Lats
  { muscles: ["lats"], view: "back", shape: "ellipse", cx: 36, cy: 122, rx: 14, ry: 22 },
  { muscles: ["lats"], view: "back", shape: "ellipse", cx: 84, cy: 122, rx: 14, ry: 22 },
  // Triceps
  { muscles: ["triceps"], view: "back", shape: "ellipse", cx: 24, cy: 118, rx: 7, ry: 14 },
  { muscles: ["triceps"], view: "back", shape: "ellipse", cx: 96, cy: 118, rx: 7, ry: 14 },
  // Forearms (back)
  { muscles: ["forearms"], view: "back", shape: "ellipse", cx: 22, cy: 148, rx: 6, ry: 14 },
  { muscles: ["forearms"], view: "back", shape: "ellipse", cx: 98, cy: 148, rx: 6, ry: 14 },
  // Lower back (erectors)
  { muscles: ["lower_back"], view: "back", shape: "ellipse", cx: 60, cy: 148, rx: 14, ry: 14 },
  // Glutes
  { muscles: ["glutes"], view: "back", shape: "ellipse", cx: 48, cy: 175, rx: 16, ry: 14 },
  { muscles: ["glutes"], view: "back", shape: "ellipse", cx: 72, cy: 175, rx: 16, ry: 14 },
  // Hamstrings
  { muscles: ["hamstrings"], view: "back", shape: "ellipse", cx: 46, cy: 210, rx: 13, ry: 22 },
  { muscles: ["hamstrings"], view: "back", shape: "ellipse", cx: 74, cy: 210, rx: 13, ry: 22 },
  // Abductors
  { muscles: ["abductors"], view: "back", shape: "ellipse", cx: 36, cy: 190, rx: 9, ry: 16 },
  { muscles: ["abductors"], view: "back", shape: "ellipse", cx: 84, cy: 190, rx: 9, ry: 16 },
  // Calves (back)
  { muscles: ["calves"], view: "back", shape: "ellipse", cx: 45, cy: 252, rx: 10, ry: 18 },
  { muscles: ["calves"], view: "back", shape: "ellipse", cx: 75, cy: 252, rx: 10, ry: 18 },
];

// Body silhouette paths — simplified outline for each view
// These are decorative shapes that frame the muscle zones
const FRONT_SILHOUETTE = `
  M60,28 C70,28 76,32 78,38 C82,36 88,36 90,40 C94,44 92,52 88,56
  C94,60 100,68 100,78 C100,88 96,94 88,98
  C96,102 104,112 104,128 C104,148 96,162 94,170
  C100,174 104,182 104,198 C104,220 96,238 90,256
  C88,262 84,270 82,276 C80,280 76,282 72,282
  C68,282 66,278 64,274 L60,266 L56,274
  C54,278 52,282 48,282 C44,282 40,280 38,276
  C36,270 32,262 30,256 C24,238 16,220 16,198
  C16,182 20,174 26,170 C24,162 16,148 16,128
  C16,112 24,102 32,98 C24,94 20,88 20,78
  C20,68 26,60 32,56 C28,52 26,44 30,40
  C32,36 38,36 42,38 C44,32 50,28 60,28 Z
`;

const BACK_SILHOUETTE = `
  M60,28 C70,28 76,32 78,38 C82,36 88,36 90,40 C94,44 92,52 88,56
  C94,60 100,68 100,78 C100,88 96,94 88,98
  C96,102 104,112 104,128 C104,148 96,162 94,170
  C100,174 104,182 104,198 C104,220 96,238 90,256
  C88,262 84,270 82,276 C80,280 76,282 72,282
  C68,282 66,278 64,274 L60,266 L56,274
  C54,278 52,282 48,282 C44,282 40,280 38,276
  C36,270 32,262 30,256 C24,238 16,220 16,198
  C16,182 20,174 26,170 C24,162 16,148 16,128
  C16,112 24,102 32,98 C24,94 20,88 20,78
  C20,68 26,60 32,56 C28,52 26,44 30,40
  C32,36 38,36 42,38 C44,32 50,28 60,28 Z
`;

function getZoneColor(
  zoneMuscles: MuscleGroup[],
  primary: Set<MuscleGroup>,
  secondary: Set<MuscleGroup>
): { fill: string; opacity: number; glow: boolean } {
  const isPrimary = zoneMuscles.some((m) => primary.has(m));
  const isSecondary = zoneMuscles.some((m) => secondary.has(m));

  if (isPrimary)   return { fill: "#ef4444", opacity: 0.75, glow: true };
  if (isSecondary) return { fill: "#f97316", opacity: 0.55, glow: true };
  return { fill: "rgba(255,255,255,0.04)", opacity: 1, glow: false };
}

function MuscleZone({
  zone,
  primary,
  secondary,
}: {
  zone: Zone;
  primary: Set<MuscleGroup>;
  secondary: Set<MuscleGroup>;
}) {
  const { fill, opacity, glow } = getZoneColor(zone.muscles, primary, secondary);
  const filterId = glow ? "muscle-glow" : undefined;

  const sharedProps = {
    fill,
    fillOpacity: opacity,
    filter: filterId ? `url(#${filterId})` : undefined,
    className: "transition-all duration-700",
  };

  if (zone.shape === "ellipse") {
    return (
      <ellipse
        cx={zone.cx} cy={zone.cy} rx={zone.rx} ry={zone.ry}
        {...sharedProps}
      />
    );
  }
  return (
    <rect
      x={zone.x} y={zone.y} width={zone.width} height={zone.height}
      rx={zone.rx_r}
      {...sharedProps}
    />
  );
}

/**
 * SVG anatomical muscle map — front/back tab toggle.
 *
 * Primary muscles: red (#ef4444) with glow filter
 * Secondary muscles: orange (#f97316) with glow filter
 * Inactive zones: near-invisible white fill
 *
 * The body silhouette is a simplified SVG path at viewBox="0 0 120 290".
 * Muscle zones are SVG ellipses/rects overlaid on the silhouette.
 * A `feGaussianBlur` filter creates the glow effect on active zones.
 */
export function MuscleMap({ primaryMuscles, secondaryMuscles }: MuscleMapProps) {
  const [view, setView] = useState<View>("front");

  const primary = new Set(primaryMuscles);
  const secondary = new Set(secondaryMuscles);
  const zones = MUSCLE_ZONES.filter((z) => z.view === view);
  const silhouette = view === "front" ? FRONT_SILHOUETTE : BACK_SILHOUETTE;

  return (
    <section className="px-4" aria-label="Muscle anatomy map">
      {/* Section label */}
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-500">
        Muscles Worked
      </h2>

      {/* Front / Back toggle */}
      <div className="mb-4 flex w-fit rounded-xl bg-surface-100 p-1" role="tablist">
        {(["front", "back"] as const).map((v) => (
          <button
            key={v}
            role="tab"
            aria-selected={view === v}
            onClick={() => setView(v)}
            className={`
              rounded-lg px-5 py-1.5 text-xs font-semibold uppercase tracking-wider
              transition-all duration-200 no-select
              ${view === v
                ? "bg-surface-300 text-neutral-200 shadow-card-sm"
                : "text-neutral-600 hover:text-neutral-400"
              }
            `}
          >
            {v}
          </button>
        ))}
      </div>

      {/* SVG anatomical map */}
      <div className="flex gap-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex-shrink-0"
          >
            <svg
              viewBox="0 0 120 290"
              width={140}
              height={340}
              aria-hidden="true"
              overflow="visible"
            >
              {/* Glow filter */}
              <defs>
                <filter id="muscle-glow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Body silhouette */}
              <path
                d={silhouette}
                fill="rgba(255,255,255,0.03)"
                stroke="rgba(255,255,255,0.07)"
                strokeWidth={1}
              />

              {/* Muscle zones */}
              {zones.map((zone, i) => (
                <MuscleZone
                  key={i}
                  zone={zone}
                  primary={primary}
                  secondary={secondary}
                />
              ))}
            </svg>
          </motion.div>
        </AnimatePresence>

        {/* Legend */}
        <div className="flex flex-col justify-center gap-4">
          {primaryMuscles.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-neutral-600">
                Primary
              </p>
              <div className="flex flex-wrap gap-1">
                {primaryMuscles.map((m) => (
                  <span key={m} className="muscle-pill muscle-pill-primary">
                    {formatLabel(m)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {secondaryMuscles.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-neutral-600">
                Secondary
              </p>
              <div className="flex flex-wrap gap-1">
                {secondaryMuscles.map((m) => (
                  <span key={m} className="muscle-pill muscle-pill-secondary">
                    {formatLabel(m)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}


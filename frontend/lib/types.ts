// ─── Enums (mirror backend) ───────────────────────────────────────────────────

export type DifficultyLevel = "beginner" | "intermediate" | "advanced" | "elite";
export type MuscleGroup =
  | "chest" | "front_delt" | "side_delt" | "rear_delt" | "triceps"
  | "lats" | "upper_back" | "traps" | "biceps" | "forearms"
  | "core" | "abs" | "obliques" | "lower_back"
  | "quads" | "hamstrings" | "glutes" | "adductors" | "abductors"
  | "calves" | "hip_flexors";
export type EquipmentType =
  | "barbell" | "dumbbell" | "kettlebell" | "ez_curl_bar" | "trap_bar"
  | "cable" | "machine" | "smith_machine" | "bench" | "incline_bench"
  | "decline_bench" | "squat_rack" | "pull_up_bar" | "dip_bars"
  | "preacher_bench" | "resistance_band" | "medicine_ball"
  | "weight_plate" | "landmine" | "bodyweight";
export type MovementPattern =
  | "horizontal_push" | "horizontal_pull" | "vertical_push" | "vertical_pull"
  | "squat" | "hinge" | "lunge" | "carry" | "rotation" | "anti_rotation" | "isolation";
export type AlternativeRelationship =
  | "progression_of" | "regression_of" | "substitute_for" | "variation_of";

// ─── Exercise sub-types ───────────────────────────────────────────────────────

export interface ExerciseAlias {
  id: string;
  alias: string;
}

export interface MovementDescriptor {
  id: string;
  category: "summary" | "setup" | "execution" | "cue" | "common_mistake" | "variation_note" | "beginner_description";
  text: string;
  vector_id: string | null;
  embedding_model: string | null;
  needs_reindex: boolean;
}

export interface ExerciseAlternativeRead {
  id: string;
  relationship_type: AlternativeRelationship;
  related_id: string;
  note: string | null;
}

// ─── Core exercise types ──────────────────────────────────────────────────────

export interface ExerciseSummary {
  id: string;
  primary_name: string;
  slug: string;
  difficulty: DifficultyLevel;
  movement_pattern: MovementPattern;
  primary_muscles: MuscleGroup[];
  equipment_required: EquipmentType[];
}

export interface Exercise {
  id: string;
  primary_name: string;
  slug: string;
  difficulty: DifficultyLevel;
  mechanic: "compound" | "isolation";
  force_type: string;
  movement_pattern: MovementPattern;
  summary: string | null;
  is_unilateral: boolean;
  created_at: string;
  updated_at: string;
  primary_muscles: MuscleGroup[];
  secondary_muscles: MuscleGroup[];
  equipment_required: EquipmentType[];
  aliases: ExerciseAlias[];
  movement_descriptors: MovementDescriptor[];
  alternatives_from: ExerciseAlternativeRead[];
}

// ─── Search types ─────────────────────────────────────────────────────────────

export interface SearchRequest {
  query: string;
  top_k?: number;
}

export interface SearchResultItem {
  rank: number;
  similarity_score: number;
  matched_description: string;
  reasoning: string;
  exercise: Exercise;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
  pose_confidence: number | null;
  classified_patterns: string[] | null;
}

// ─── Paginated list ───────────────────────────────────────────────────────────

export interface PaginatedExerciseList {
  total: number;
  page: number;
  per_page: number;
  pages: number;
  results: ExerciseSummary[];
}

// ─── Alternatives ─────────────────────────────────────────────────────────────

export interface AlternativeMatch {
  relationship_type: AlternativeRelationship;
  note: string | null;
  exercise: ExerciseSummary;
}

export interface AlternativesResponse {
  exercise_id: string;
  available_equipment: EquipmentType[];
  alternatives: AlternativeMatch[];
}

// ─── Utilities ────────────────────────────────────────────────────────────────

/** Convert a snake_case enum value to a human-readable label. */
export function formatLabel(snake: string): string {
  return snake
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Map a similarity score (0–1) to the Tailwind match color token. */
export function scoreToColor(score: number): string {
  if (score >= 0.85) return "#34d399"; // match.high — emerald
  if (score >= 0.60) return "#fbbf24"; // match.mid — amber
  return "#f87171";                     // match.low — red
}

export interface ExerciseAlias {
  id: string;
  alias: string;
}

export interface MovementDescriptor {
  id: string;
  category: string;
  text: string;
  vector_id: string | null;
  embedding_model: string | null;
  needs_reindex: boolean;
}

export interface Exercise {
  id: string;
  primary_name: string;
  slug: string;
  difficulty: string;
  mechanic: string;
  force_type: string;
  movement_pattern: string;
  summary: string | null;
  is_unilateral: boolean;
  created_at: string;
  updated_at: string;
  primary_muscles: string[];
  secondary_muscles: string[];
  equipment_required: string[];
  aliases: ExerciseAlias[];
  movement_descriptors: MovementDescriptor[];
  alternatives_from: unknown[];
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
}

export function formatLabel(snake: string): string {
  return snake
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

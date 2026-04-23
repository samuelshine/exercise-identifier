import { AlternativesResponse, Exercise, SearchResponse } from "./types";

// API base URL — override via NEXT_PUBLIC_API_URL for staging/production.
// Falls back to localhost for local development.
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

// ─── Error type ───────────────────────────────────────────────────────────────

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(detail: string, status: number) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  let res: Response;

  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...init.headers },
      ...init,
    });
  } catch {
    throw new ApiError(
      "Network error — check your connection or that the backend is running.",
      0
    );
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // body wasn't JSON — keep the default message
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<T>;
}

// ─── Exercise endpoints ───────────────────────────────────────────────────────

export async function getExercise(slug: string): Promise<Exercise> {
  return apiFetch<Exercise>(`/exercises/slug/${encodeURIComponent(slug)}`);
}

export async function getAlternatives(
  exerciseId: string,
  equipment: string[] = []
): Promise<AlternativesResponse> {
  const params =
    equipment.length > 0
      ? "?" + equipment.map((e) => `equipment=${encodeURIComponent(e)}`).join("&")
      : "";
  return apiFetch<AlternativesResponse>(
    `/exercises/${encodeURIComponent(exerciseId)}/alternatives${params}`
  );
}

// ─── Search endpoints ─────────────────────────────────────────────────────────

export async function searchExercises(
  query: string,
  topK: number = 5
): Promise<SearchResponse> {
  return apiFetch<SearchResponse>("/search/text", {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK }),
  });
}

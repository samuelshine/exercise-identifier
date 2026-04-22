import { SearchResponse } from "./types";

const API_BASE = "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Search exercises via natural language description.
 * Hits POST /search/text on the FastAPI backend.
 */
export async function searchExercises(
  query: string,
  topK: number = 3
): Promise<SearchResponse> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE}/search/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
    });
  } catch {
    throw new ApiError(
      "Unable to reach the backend. Make sure the FastAPI server is running on port 8000.",
      0
    );
  }

  if (!response.ok) {
    const text = await response.text().catch(() => "Unknown error");
    throw new ApiError(
      `Search failed (${response.status}): ${text}`,
      response.status
    );
  }

  return response.json();
}

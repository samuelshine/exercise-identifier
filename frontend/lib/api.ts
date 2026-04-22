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

export async function searchExercises(
  query: string,
  topK: number = 3
): Promise<SearchResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/search/text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK }),
    });
  } catch {
    throw new ApiError("Network error — is the backend running?", 0);
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(body || `HTTP ${res.status}`, res.status);
  }

  return res.json();
}

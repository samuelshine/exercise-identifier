"""
Exercise Identifier - Backend entrypoint.

This module wires up the FastAPI application with:
- CORS middleware for the Next.js frontend.
- A health-check endpoint.
- The ``POST /search/text`` two-stage RAG endpoint:
    Stage 1: ChromaDB vector search → top-7 candidates.
    Stage 2: Gemma4 LLM re-ranking → top-3 semantically verified results.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from contextlib import asynccontextmanager

import chromadb
import ollama
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Exercise, MovementDescriptor, DescriptorCategory
from app.schemas import ExerciseRead

logger = logging.getLogger("uvicorn.error")

# ---------- Configuration ----------------------------------------------------

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_JUDGE_MODEL = "gemma4:e4b"
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION = "exercise_descriptions"

# Stage 1: retrieve this many candidates from ChromaDB
CANDIDATE_POOL_SIZE = 7
# Stage 2: return this many after LLM re-ranking (can be overridden by top_k)
DEFAULT_RETURN_COUNT = 3


# ---------- Shared state (initialised at startup) ----------------------------

chroma_collection: chromadb.Collection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the ChromaDB collection once at startup, reuse for all requests."""
    global chroma_collection
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    chroma_collection = client.get_collection(name=CHROMA_COLLECTION)
    logger.info(
        "ChromaDB collection '%s' loaded — %d vectors.",
        CHROMA_COLLECTION,
        chroma_collection.count(),
    )
    yield


# ---------- App setup --------------------------------------------------------

app = FastAPI(
    title="Exercise Identifier API",
    version="0.3.0",
    description=(
        "Two-stage RAG backend: ChromaDB vector retrieval + Gemma4 LLM "
        "semantic re-ranking for identifying gym exercises from natural language."
    ),
    lifespan=lifespan,
)

# CORS is permissive in dev so the Next.js frontend (http://localhost:3000)
# can call the API from the browser. Tighten this before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Request / Response schemas ---------------------------------------


class SearchRequest(BaseModel):
    """POST body for the text search endpoint."""

    query: str = Field(
        min_length=3,
        max_length=500,
        description="Natural-language description of the exercise you're looking for.",
        examples=["sitting down pulling the bar to my chest"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of results to return after re-ranking (1–10).",
    )


class SearchResultItem(BaseModel):
    """A single search hit — LLM confidence score + full exercise data."""

    rank: int
    similarity_score: float = Field(
        description="LLM re-ranked confidence score (0–1). Higher is better."
    )
    matched_description: str = Field(
        description="The beginner_description text that initially matched the query."
    )
    reasoning: str = Field(
        default="",
        description="LLM's 1-sentence explanation of the confidence score.",
    )
    exercise: ExerciseRead


class SearchResponse(BaseModel):
    """Response from the ``POST /search/text`` endpoint."""

    query: str
    results: list[SearchResultItem]


# ---------- Scaffolding routes -----------------------------------------------


@app.get("/")
async def root() -> dict[str, str]:
    """Sanity-check endpoint so the frontend (and humans) can confirm uptime."""
    return {"message": "Exercise Identifier API v0.3.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Lightweight liveness probe — useful for container orchestrators later."""
    return {"status": "ok"}


# ---------- LLM Re-ranking (Stage 2) ----------------------------------------


def _build_judge_prompt(user_query: str, candidates: list[dict]) -> str:
    """Build the system + user prompt for the LLM judge.

    Each candidate dict has:
      - exercise_id, exercise_name, force_type, beginner_descriptions (list[str])
    """
    candidate_block = ""
    for i, c in enumerate(candidates, 1):
        descs = "\n".join(f"    - {d}" for d in c["beginner_descriptions"])
        candidate_block += (
            f"\n  {i}. exercise_id: {c['exercise_id']}\n"
            f"     name: {c['exercise_name']}\n"
            f"     force_type: {c['force_type']}\n"
            f"     descriptions:\n{descs}\n"
        )

    return f"""You are an expert biomechanist and exercise scientist. A user described a gym exercise in their own words. Your job is to evaluate how well each candidate exercise matches the user's description based on the PHYSICAL MECHANICS of the movement — not just surface-level word similarity.

CRITICAL RULES:
- Pay close attention to body position (standing vs sitting vs lying), direction of force (pushing vs pulling), and equipment used.
- Distinguish between spatial concepts: "floor" means the ground (bodyweight exercises), "platform" means a machine surface. "Pushing off the floor" is NOT the same as "pushing a platform with your legs."
- If the user says "pushing" and the exercise is a "pull" movement, it should score very low.
- Score each candidate between 0.00 (no match) and 1.00 (perfect match).

USER'S DESCRIPTION: "{user_query}"

CANDIDATE EXERCISES:
{candidate_block}

Respond with ONLY a raw JSON array (no markdown, no backticks, no explanation outside the JSON). Each element must be:
{{"exercise_id": "<uuid>", "confidence_score": <float 0.00-1.00>, "reasoning": "<1 sentence>"}}

Return the array now:"""


async def _llm_rerank(
    user_query: str,
    candidates: list[dict],
) -> list[dict] | None:
    """Call gemma4:e4b to re-rank candidates. Returns parsed list or None on failure."""
    prompt = _build_judge_prompt(user_query, candidates)

    try:
        client = ollama.Client(host=OLLAMA_HOST)
        # Run the synchronous Ollama call in a thread to avoid blocking the event loop
        response = await asyncio.to_thread(
            client.generate,
            model=OLLAMA_JUDGE_MODEL,
            prompt=prompt,
            options={"temperature": 0.1, "num_predict": 2048},
        )
        raw_text = response["response"].strip()
    except Exception as e:
        logger.warning("LLM re-ranking call failed: %s: %s", type(e).__name__, e)
        return None

    # Parse JSON — the model may wrap it in markdown code fences
    json_text = raw_text
    # Strip ```json ... ``` wrapper if present
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", json_text, re.DOTALL)
    if fence_match:
        json_text = fence_match.group(1).strip()

    try:
        parsed = json.loads(json_text)
        if not isinstance(parsed, list):
            logger.warning("LLM returned non-list JSON: %s", type(parsed).__name__)
            return None
        return parsed
    except json.JSONDecodeError as e:
        logger.warning("LLM JSON parse failed: %s — raw: %.300s", e, raw_text)
        return None


# ---------- RAG search endpoint ----------------------------------------------


@app.post("/search/text", response_model=SearchResponse)
async def search_text(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Identify exercises from a natural-language description.

    Two-Stage Retrieval Pipeline
    ----------------------------
    1. **Embed** the user's query with Ollama (``nomic-embed-text``).
    2. **Stage 1 — Vector retrieval**: Query ChromaDB for the top-7 nearest
       ``beginner_description`` embeddings (expanded candidate pool).
    3. **Fetch** full exercise records from PostgreSQL for these 7 candidates.
    4. **Stage 2 — LLM re-ranking**: Send the user query + 7 candidates to
       ``gemma4:e4b`` acting as an expert biomechanist judge. The LLM evaluates
       physical mechanics (body position, force direction, equipment) and returns
       a confidence score + reasoning for each candidate.
    5. **Return** the top-K re-ranked results with LLM confidence scores.

    If the LLM re-ranking fails (network, parsing), falls back gracefully to
    the original vector similarity ranking.
    """
    if chroma_collection is None:
        raise HTTPException(
            status_code=503,
            detail="ChromaDB collection not loaded. Run embed_database.py first.",
        )

    # ── Stage 1: Embed + Vector Search ──────────────────────────────────

    # 1a. Embed the user query locally via Ollama
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        embed_response = client.embed(model=OLLAMA_EMBED_MODEL, input=body.query)
        query_embedding = embed_response["embeddings"][0]
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama embedding failed: {type(e).__name__}: {e}",
        )

    # 1b. Query ChromaDB for expanded candidate pool (top-7 unique exercises)
    # Request more than 7 to account for deduplication across descriptions
    chroma_results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=CANDIDATE_POOL_SIZE * 3,  # over-fetch to ensure 7 unique exercises
        include=["distances", "documents", "metadatas"],
    )

    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return SearchResponse(query=body.query, results=[])

    # 1c. Deduplicate to unique exercises, keep best vector match per exercise
    hit_data: list[dict] = []
    seen_exercise_ids: set[str] = set()

    for idx, meta in enumerate(chroma_results["metadatas"][0]):
        exercise_id = meta["exercise_id"]
        if exercise_id in seen_exercise_ids:
            continue
        seen_exercise_ids.add(exercise_id)

        distance = chroma_results["distances"][0][idx]
        similarity = max(0.0, 1.0 - distance)

        hit_data.append({
            "exercise_id": exercise_id,
            "vector_similarity": round(similarity, 4),
            "matched_description": chroma_results["documents"][0][idx],
        })

        if len(hit_data) >= CANDIDATE_POOL_SIZE:
            break

    # 1d. Fetch full exercise records from Postgres
    exercise_uuids = [uuid.UUID(h["exercise_id"]) for h in hit_data]
    stmt = select(Exercise).where(Exercise.id.in_(exercise_uuids))
    result = await session.execute(stmt)
    exercises_by_id = {str(ex.id): ex for ex in result.scalars().all()}

    # ── Stage 2: LLM Re-ranking ────────────────────────────────────────

    # 2a. Build candidate dossiers for the LLM judge
    candidates_for_llm: list[dict] = []
    for hit in hit_data:
        exercise = exercises_by_id.get(hit["exercise_id"])
        if exercise is None:
            continue
        # Gather all beginner_descriptions for this exercise
        beginner_descs = [
            md.text
            for md in exercise.movement_descriptors
            if md.category == DescriptorCategory.BEGINNER_DESCRIPTION
        ]
        candidates_for_llm.append({
            "exercise_id": hit["exercise_id"],
            "exercise_name": exercise.primary_name,
            "force_type": exercise.force_type.value if exercise.force_type else "unknown",
            "beginner_descriptions": beginner_descs,
        })

    # 2b. Call the LLM judge
    llm_rankings = await _llm_rerank(body.query, candidates_for_llm)

    # 2c. Merge LLM scores or fall back to vector similarity
    use_llm = False
    llm_scores: dict[str, dict] = {}

    if llm_rankings is not None:
        for entry in llm_rankings:
            eid = entry.get("exercise_id", "")
            score = entry.get("confidence_score")
            reasoning = entry.get("reasoning", "")
            if isinstance(score, (int, float)) and eid:
                llm_scores[eid] = {
                    "score": max(0.0, min(1.0, float(score))),
                    "reasoning": str(reasoning),
                }
        # Only use LLM if we got scores for at least half the candidates
        if len(llm_scores) >= len(candidates_for_llm) // 2:
            use_llm = True
            logger.info(
                "LLM re-ranking succeeded: %d/%d candidates scored.",
                len(llm_scores),
                len(candidates_for_llm),
            )
        else:
            logger.warning(
                "LLM returned too few scores (%d/%d) — falling back to vector sort.",
                len(llm_scores),
                len(candidates_for_llm),
            )

    if not use_llm:
        logger.info("Using vector similarity fallback.")

    # ── Stage 3: Build final response ──────────────────────────────────

    # Build scored list
    scored_hits: list[dict] = []
    for hit in hit_data:
        exercise = exercises_by_id.get(hit["exercise_id"])
        if exercise is None:
            continue

        if use_llm and hit["exercise_id"] in llm_scores:
            llm_entry = llm_scores[hit["exercise_id"]]
            final_score = llm_entry["score"]
            reasoning = llm_entry["reasoning"]
        else:
            final_score = hit["vector_similarity"]
            reasoning = ""

        scored_hits.append({
            "exercise_id": hit["exercise_id"],
            "score": final_score,
            "reasoning": reasoning,
            "matched_description": hit["matched_description"],
        })

    # Sort by score descending
    scored_hits.sort(key=lambda h: h["score"], reverse=True)

    # Return top_k results
    results: list[SearchResultItem] = []
    for rank, hit in enumerate(scored_hits[: body.top_k], start=1):
        exercise = exercises_by_id[hit["exercise_id"]]
        results.append(
            SearchResultItem(
                rank=rank,
                similarity_score=round(hit["score"], 4),
                matched_description=hit["matched_description"],
                reasoning=hit["reasoning"],
                exercise=ExerciseRead.model_validate(exercise),
            )
        )

    return SearchResponse(query=body.query, results=results)

"""
Exercise Identifier - Backend entrypoint.

This module wires up the FastAPI application with:
- CORS middleware for the Next.js frontend.
- A health-check endpoint.
- The ``POST /search/text`` RAG endpoint that identifies exercises from
  natural-language descriptions using the dual-database architecture
  (ChromaDB for vector similarity → PostgreSQL for full exercise details).
"""

from __future__ import annotations

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
from app.models import Exercise
from app.schemas import ExerciseRead


# ---------- Configuration ----------------------------------------------------

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION = "exercise_descriptions"


# ---------- Shared state (initialised at startup) ----------------------------

chroma_collection: chromadb.Collection | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the ChromaDB collection once at startup, reuse for all requests."""
    global chroma_collection
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    chroma_collection = client.get_collection(name=CHROMA_COLLECTION)
    print(
        f"ChromaDB collection '{CHROMA_COLLECTION}' loaded — "
        f"{chroma_collection.count()} vectors."
    )
    yield


# ---------- App setup --------------------------------------------------------

app = FastAPI(
    title="Exercise Identifier API",
    version="0.2.0",
    description=(
        "RAG-powered backend for identifying gym strength-training exercises "
        "from natural-language descriptions."
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
        description="Number of results to return (1–10).",
    )


class SearchResultItem(BaseModel):
    """A single search hit — similarity score + full exercise data."""

    rank: int
    similarity_score: float = Field(
        description="Cosine similarity (0–1). Higher is more similar."
    )
    matched_description: str = Field(
        description="The beginner_description text that matched the query."
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
    return {"message": "Exercise Identifier API v0.2.0"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Lightweight liveness probe — useful for container orchestrators later."""
    return {"status": "ok"}


# ---------- RAG search endpoint ----------------------------------------------


@app.post("/search/text", response_model=SearchResponse)
async def search_text(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Identify exercises from a natural-language description.

    Pipeline
    --------
    1. **Embed** the user's query with Ollama (``nomic-embed-text``).
    2. **Vector search** in ChromaDB for the top-K most similar
       ``beginner_description`` embeddings.
    3. **Join back** to PostgreSQL using the ``exercise_id`` stored in
       ChromaDB metadata to fetch full, structured exercise records.
    4. **Return** ranked results with similarity scores.
    """
    if chroma_collection is None:
        raise HTTPException(
            status_code=503,
            detail="ChromaDB collection not loaded. Run embed_database.py first.",
        )

    # 1. Embed the user query locally via Ollama
    try:
        client = ollama.Client(host=OLLAMA_HOST)
        embed_response = client.embed(model=OLLAMA_EMBED_MODEL, input=body.query)
        query_embedding = embed_response["embeddings"][0]
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama embedding failed: {type(e).__name__}: {e}",
        )

    # 2. Query ChromaDB for nearest neighbours
    chroma_results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=body.top_k,
        include=["distances", "documents", "metadatas"],
    )

    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return SearchResponse(query=body.query, results=[])

    # 3. Collect unique exercise IDs and fetch from Postgres
    #    (ChromaDB may return multiple descriptions from the same exercise)
    hit_data: list[dict] = []
    seen_exercise_ids: set[str] = set()

    for idx, meta in enumerate(chroma_results["metadatas"][0]):
        exercise_id = meta["exercise_id"]
        if exercise_id in seen_exercise_ids:
            continue
        seen_exercise_ids.add(exercise_id)

        # ChromaDB returns L2 distances by default, but we configured cosine.
        # Cosine distance in ChromaDB = 1 - cosine_similarity.
        distance = chroma_results["distances"][0][idx]
        similarity = max(0.0, 1.0 - distance)

        hit_data.append({
            "exercise_id": exercise_id,
            "similarity": round(similarity, 4),
            "matched_description": chroma_results["documents"][0][idx],
        })

    # Fetch exercises from Postgres in one query
    exercise_uuids = [uuid.UUID(h["exercise_id"]) for h in hit_data]
    stmt = select(Exercise).where(Exercise.id.in_(exercise_uuids))
    result = await session.execute(stmt)
    exercises_by_id = {str(ex.id): ex for ex in result.scalars().all()}

    # 4. Build ranked response
    results: list[SearchResultItem] = []
    for rank, hit in enumerate(hit_data, start=1):
        exercise = exercises_by_id.get(hit["exercise_id"])
        if exercise is None:
            continue  # orphaned vector — skip gracefully

        results.append(
            SearchResultItem(
                rank=rank,
                similarity_score=hit["similarity"],
                matched_description=hit["matched_description"],
                exercise=ExerciseRead.model_validate(exercise),
            )
        )

    return SearchResponse(query=body.query, results=results)

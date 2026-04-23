"""
Vector embedding and retrieval service.

Responsibilities:
  1. get_chroma_collection()  → singleton ChromaDB collection, lazy-initialized
  2. embed_query(text)        → 768-dim float vector via Ollama nomic-embed-text
  3. search_similar(vector)   → kNN candidates, deduplicated by exercise_id

ChromaDB collection schema (per document/vector):
  id       : str  — MovementDescriptor UUID
  document : str  — the descriptor text that was embedded
  metadata : {
    exercise_id : str (UUID)   — FK to exercises table
    category    : str          — DescriptorCategory value
  }
  embedding: list[float]       — 768-dim nomic-embed-text vector
"""

import asyncio
import logging
from typing import TypedDict

import chromadb
from chromadb.config import Settings as ChromaSettings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ─── Types ────────────────────────────────────────────────────────────────────

class Candidate(TypedDict):
    """A deduplicated, scored exercise candidate from the vector search stage."""
    exercise_id: str            # UUID string — used to load from PostgreSQL
    matched_description: str    # The descriptor text that matched the query
    similarity: float           # 0.0–1.0 (1.0 = identical)


# ─── ChromaDB singleton ───────────────────────────────────────────────────────
# Initialized on first call; reused for all subsequent requests.
# Thread-safe: Python's GIL protects the lazy initialization check.

_chroma_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def get_chroma_collection() -> chromadb.Collection:
    """
    Return the ChromaDB collection, initializing the client if needed.

    Uses a PersistentClient so vectors survive server restarts.
    The collection is created if it doesn't exist yet — safe to call
    before embed_database.py has been run (the collection will just be empty).
    """
    global _chroma_client, _collection
    if _collection is None:
        settings = get_settings()
        _chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _chroma_client.get_or_create_collection(
            name=settings.chroma_collection,
            # Cosine similarity is the right metric for normalized text embeddings.
            # ChromaDB stores distance = 1 - cosine_similarity, so distance ∈ [0, 2].
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB collection '%s' initialized — %d vectors",
            settings.chroma_collection,
            _collection.count(),
        )
    return _collection


# ─── Embedding ────────────────────────────────────────────────────────────────

_ollama_client = None

@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    reraise=True,
)
async def embed_query(text: str) -> list[float]:
    """
    Embed a text query using Ollama's nomic-embed-text model.

    Returns a 768-dimensional float vector.
    Retries once on transient errors (Ollama briefly unavailable).
    Raises on persistent failure — caller should 503.
    """
    global _ollama_client
    settings = get_settings()

    if _ollama_client is None:
        from ollama import AsyncClient
        _ollama_client = AsyncClient(host=settings.ollama_host)

    try:
        response = await asyncio.wait_for(
            _ollama_client.embeddings(
                model=settings.ollama_embed_model,
                prompt=text,
            ),
            timeout=settings.ollama_embed_timeout,
        )
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"Embedding timed out after {settings.ollama_embed_timeout}s — "
            f"is Ollama running at {settings.ollama_host}?"
        )

    embedding: list[float] = response["embedding"]
    logger.debug("Embedded query (%d chars) → %d-dim vector", len(text), len(embedding))
    return embedding


# ─── Vector retrieval ─────────────────────────────────────────────────────────

async def search_similar(
    vector: list[float],
    top_k: int = 20,
) -> list[Candidate]:
    """
    Query ChromaDB for the nearest descriptor vectors.

    Deduplication logic:
      - Multiple MovementDescriptors per exercise may all match the query
        (e.g., both the "summary" and "execution" descriptors for Bench Press).
      - We group by exercise_id and keep only the highest-similarity descriptor
        per exercise. This prevents one exercise from flooding the candidate list.
      - Returns at most top_k unique exercises, sorted by similarity descending.

    Similarity conversion:
      ChromaDB cosine space returns distance = 1 − cosine_similarity.
      For nomic-embed-text (normalized vectors), cosine_similarity ∈ [-1, 1],
      so distance ∈ [0, 2]. We convert: similarity = 1 − distance.
      In practice for related text, distance < 1.0, so similarity > 0.
    """
    collection = get_chroma_collection()
    total_vectors = collection.count()

    if total_vectors == 0:
        logger.warning(
            "ChromaDB collection is empty — run `python -m scripts.embed_database` first"
        )
        return []

    # Fetch 3× top_k to have enough candidates after deduplication
    n_results = min(top_k * 3, total_vectors)

    results = collection.query(
        query_embeddings=[vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs: list[str]       = results["documents"][0]
    metas: list[dict]     = results["metadatas"][0]
    distances: list[float] = results["distances"][0]

    # Deduplicate: exercise_id → best Candidate
    seen: dict[str, Candidate] = {}
    for doc, meta, dist in zip(docs, metas, distances):
        exercise_id: str = meta["exercise_id"]
        # Clamp to [0, 1] to guard against floating-point edge cases
        similarity = float(max(0.0, min(1.0, 1.0 - dist)))

        if exercise_id not in seen or similarity > seen[exercise_id]["similarity"]:
            seen[exercise_id] = Candidate(
                exercise_id=exercise_id,
                matched_description=doc,
                similarity=round(similarity, 4),
            )

    candidates = sorted(seen.values(), key=lambda c: c["similarity"], reverse=True)
    logger.info(
        "Vector search: %d raw hits → %d unique exercises (top_k=%d)",
        len(docs), len(candidates), top_k,
    )
    return candidates[:top_k]

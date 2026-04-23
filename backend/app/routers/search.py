"""
Search router — text and video (Phase 2) endpoints.

Text search pipeline (POST /search/text):
  1. Embed user query → 768-dim vector (Ollama nomic-embed-text)
  2. kNN retrieval    → top-20 descriptor candidates (ChromaDB cosine)
  3. Deduplication    → at most 10 unique exercises (best score per exercise)
  4. Hydration        → load full Exercise rows from PostgreSQL
  5. LLM re-ranking   → score + reason via Ollama judge (gemma4:e4b)
  6. Slice → top_k    → return SearchResponse

Video search pipeline (POST /search/video) — Phase 2 stub.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.exercise import Exercise
from app.schemas.exercise import ExerciseRead, SearchRequest, SearchResponse
from app.services.embedding import Candidate, embed_query, search_similar
from app.services.reranker import HydratedCandidate, rerank_candidates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _load_exercises_by_ids(
    session: AsyncSession,
    exercise_ids: list[str],
) -> dict[str, ExerciseRead]:
    """
    Batch-load Exercise rows from PostgreSQL by UUID.

    Uses a single SELECT … WHERE id IN (…) query.
    The lazy="selectin" strategy on all relationships ensures aliases,
    muscle groups, equipment, descriptors, and alternatives are all
    loaded within this one await — no N+1 queries.

    Returns a dict keyed by UUID string for O(1) lookup during merge.
    """
    if not exercise_ids:
        return {}

    uuids = []
    for eid in exercise_ids:
        try:
            uuids.append(uuid.UUID(eid))
        except ValueError:
            logger.warning("Invalid UUID in vector metadata: %s — skipping", eid)

    if not uuids:
        return {}

    stmt = select(Exercise).where(Exercise.id.in_(uuids))
    result = await session.execute(stmt)
    exercises = result.scalars().all()

    # Pydantic v2: model_validate reads @property fields correctly when
    # from_attributes=True is set (all relations already loaded via selectin)
    return {str(ex.id): ExerciseRead.model_validate(ex) for ex in exercises}


# ─── POST /search/text ────────────────────────────────────────────────────────

@router.post(
    "/text",
    response_model=SearchResponse,
    summary="Semantic exercise search by text description",
    description=(
        "Accepts a natural-language description of an exercise and returns "
        "the top-k matching exercises, ranked by an LLM biomechanics judge. "
        "Falls back to vector-similarity ordering if the LLM is unavailable."
    ),
)
async def search_by_text(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    logger.info("Text search: query=%r top_k=%d", body.query, body.top_k)

    # ── Stage 1: Embed ──────────────────────────────────────────────────────
    try:
        query_vector = await embed_query(body.query)
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Embedding service unavailable: {exc}. "
                "Ensure Ollama is running and nomic-embed-text is pulled."
            ),
        )

    # ── Stage 2: Vector retrieval + deduplication ───────────────────────────
    # Retrieve more than top_k so we have headroom after deduplication.
    # Cap retrieval at 20; the reranker will reduce to top_k.
    candidates: list[Candidate] = await search_similar(query_vector, top_k=20)

    if not candidates:
        logger.info("No vector results — returning empty SearchResponse")
        return SearchResponse(query=body.query, results=[])

    # ── Stage 3: PostgreSQL hydration ───────────────────────────────────────
    # Load full Exercise objects (with all relations) for the top-10 candidates.
    # We cap at 10 to keep the LLM prompt size predictable.
    top_candidates = candidates[:10]
    exercise_map = await _load_exercises_by_ids(
        session,
        [c["exercise_id"] for c in top_candidates],
    )

    if not exercise_map:
        logger.warning("Vector candidates found but no matching PostgreSQL rows — DB may be out of sync")
        return SearchResponse(query=body.query, results=[])

    # Merge: attach hydrated exercise to each candidate
    hydrated: list[HydratedCandidate] = []
    for c in top_candidates:
        ex = exercise_map.get(c["exercise_id"])
        if ex is None:
            # Vector index references an exercise that no longer exists in DB
            logger.warning("Stale vector — exercise_id %s not in DB", c["exercise_id"])
            continue
        hydrated.append(
            HydratedCandidate(
                exercise_id=c["exercise_id"],
                matched_description=c["matched_description"],
                similarity=c["similarity"],
                exercise=ex,
            )
        )

    if not hydrated:
        return SearchResponse(query=body.query, results=[])

    # ── Stage 4: LLM re-ranking ─────────────────────────────────────────────
    # The reranker handles its own timeout and always returns a valid list
    # (vector fallback if the LLM is unavailable). Will never raise here.
    results = await rerank_candidates(body.query, hydrated, body.top_k)

    logger.info(
        "Search complete: query=%r → %d results (top score: %.3f)",
        body.query,
        len(results),
        results[0].similarity_score if results else 0.0,
    )
    return SearchResponse(query=body.query, results=results)


# ─── POST /search/video/upload-url ────────────────────────────────────────────

@router.post(
    "/video/upload-url",
    summary="[Phase 2] Generate a pre-signed S3 URL for ephemeral video upload",
    description=(
        "Returns a pre-signed S3 PUT URL. The client uploads the video directly "
        "to S3 — the video never passes through the application server. "
        "The S3 bucket has a 5-minute lifecycle policy that guarantees deletion."
    ),
)
async def get_video_upload_url():
    # TODO: Phase 2 — see services/video.py
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Video search is scheduled for Phase 2.",
    )


# ─── POST /search/video ───────────────────────────────────────────────────────

@router.post(
    "/video",
    response_model=SearchResponse,
    summary="[Phase 2] Exercise identification via pose estimation",
    description=(
        "Accepts an S3 key for a previously uploaded video. Downloads the video "
        "ephemerally, runs MediaPipe pose estimation, classifies the movement "
        "pattern, and pipes it through the text search pipeline. "
        "The video is deleted from S3 immediately after processing."
    ),
)
async def search_by_video(
    session: AsyncSession = Depends(get_session),
):
    # TODO: Phase 2 — see services/video.py
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Video search is scheduled for Phase 2.",
    )

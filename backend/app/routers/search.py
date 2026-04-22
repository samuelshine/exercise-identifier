from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.exercise import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/text", response_model=SearchResponse)
async def search_by_text(
    body: SearchRequest,
    session: AsyncSession = Depends(get_session),
):
    """Two-stage RAG search: vector retrieval → LLM re-ranking."""
    # TODO: implement — see services/embedding.py and services/reranker.py
    raise NotImplementedError


@router.post("/video", response_model=SearchResponse)
async def search_by_video(
    session: AsyncSession = Depends(get_session),
):
    """Video-based exercise identification via pose estimation."""
    # TODO: Phase 2 — see services/video.py
    raise NotImplementedError

"""
Exercise Identifier API — FastAPI entrypoint.

Boot order:
  1. Configure logging (JSON in prod, human-readable in dev)
  2. Build the FastAPI app + middleware stack
  3. Run lifespan startup: validate ChromaDB, Ollama; create tables in dev
  4. Begin accepting requests

In production, schema management is handled by Alembic — the dev-only
create_all branch in lifespan is gated behind settings.environment.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.limiter import limiter
from app.core.logging_config import configure_logging
from app.core.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.routers import exercises, search
from app.services.embedding import get_chroma_collection

settings = get_settings()
configure_logging(json_logs=settings.is_production, level="DEBUG" if settings.debug else "INFO")
logger = logging.getLogger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting Exercise Identifier API v%s (env=%s)",
        settings.api_version,
        settings.environment,
    )

    try:
        collection = get_chroma_collection()
        logger.info("ChromaDB ready — %d vectors indexed", collection.count())
    except Exception as exc:
        logger.warning("ChromaDB init failed: %s — search will return empty results", exc)

    try:
        import ollama  # noqa: F401
        logger.info("Ollama package ready (host: %s)", settings.ollama_host)
    except ImportError as exc:
        logger.error("Ollama package not installed: %s", exc)

    # Schema bootstrap is dev-only. Production migrates via Alembic so that
    # column changes ship as reviewable, reversible migrations.
    if not settings.is_production:
        from app.core.database import Base, engine
        import app.models.exercise  # noqa: F401

        async with engine.begin() as conn:
            logger.info("Dev mode: ensuring tables exist via metadata.create_all")
            await conn.run_sync(Base.metadata.create_all)

    logger.info("API ready — accepting connections")
    yield
    logger.info("Shutting down Exercise Identifier API")


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Exercise Identifier API",
    description="Semantic exercise search via text description and video pose estimation.",
    version=settings.api_version,
    lifespan=lifespan,
    # /docs is publicly reachable in dev only. In prod the OpenAPI surface
    # is hidden — schemas leak internal field names that aren't part of the
    # external contract.
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# Wire the rate limiter — slowapi reads app.state.limiter at request time.
app.state.limiter = limiter

# ─── Middleware ───────────────────────────────────────────────────────────────
# Order matters: middlewares run outermost-first on the way in, innermost-first
# on the way out. We register from inside out, so the actual execution order
# (request → response) is:
#   RequestID → SecurityHeaders → SlowAPI → CORS → route
# RequestID must be outermost so every log line — including rate-limit
# rejections and CORS preflights — carries an ID.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)

register_exception_handlers(app, settings)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(search.router)
app.include_router(exercises.router)


# ─── Root & Health ────────────────────────────────────────────────────────────

@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Exercise Identifier API",
        "version": settings.api_version,
        "docs": "/docs" if not settings.is_production else None,
    }


@app.get("/health", tags=["meta"])
async def health():
    """
    Dependency health check. Used by ECS health checks and monitoring.
    Returns 200 even if some dependencies are degraded — callers should
    inspect the per-dependency status fields.
    """
    deps: dict[str, str] = {}

    try:
        col = get_chroma_collection()
        deps["vector_db"] = f"ok ({col.count()} vectors)"
    except Exception as exc:
        deps["vector_db"] = f"error: {exc}"

    try:
        from ollama import AsyncClient
        client = AsyncClient(host=settings.ollama_host)
        models = await client.list()
        pulled = [m.model for m in models.models]
        embed_ok = settings.ollama_embed_model in pulled
        judge_ok = settings.ollama_judge_model in pulled
        deps["ollama"] = "ok"
        deps["embed_model"] = settings.ollama_embed_model if embed_ok else f"NOT PULLED: {settings.ollama_embed_model}"
        deps["judge_model"] = settings.ollama_judge_model if judge_ok else f"NOT PULLED: {settings.ollama_judge_model}"
    except Exception as exc:
        deps["ollama"] = f"unreachable: {exc}"

    overall = "ok" if all("error" not in v and "unreachable" not in v for v in deps.values()) else "degraded"
    return {"status": overall, **deps}


@app.get("/meta/enums", tags=["meta"])
async def enum_values():
    """
    Returns all valid enum values for frontend dropdowns and filter UI.
    Avoids hardcoding enum lists in the frontend.
    """
    from app.models.enums import (
        AlternativeRelationship, DescriptorCategory, DifficultyLevel,
        EquipmentType, ForceType, MechanicType, MovementPattern, MuscleGroup,
    )
    return {
        "difficulty_levels":         [e.value for e in DifficultyLevel],
        "muscle_groups":             [e.value for e in MuscleGroup],
        "equipment_types":           [e.value for e in EquipmentType],
        "movement_patterns":         [e.value for e in MovementPattern],
        "mechanic_types":            [e.value for e in MechanicType],
        "force_types":               [e.value for e in ForceType],
        "descriptor_categories":     [e.value for e in DescriptorCategory],
        "alternative_relationships": [e.value for e in AlternativeRelationship],
    }

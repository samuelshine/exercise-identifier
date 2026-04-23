import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import exercises, search
from app.services.embedding import get_chroma_collection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

settings = get_settings()


# ─── Lifespan ─────────────────────────────────────────────────────────────────
# Runs at process start and stop. Validates that all required services are
# reachable before the server begins accepting requests.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    logger.info("Starting Exercise Identifier API v%s", settings.api_version)

    # 1. Initialize ChromaDB collection — validates persistence path and creates
    #    the collection if it doesn't exist yet.
    try:
        collection = get_chroma_collection()
        logger.info("ChromaDB ready — %d vectors indexed", collection.count())
    except Exception as exc:
        # Non-fatal: server still starts but search will return empty results
        # until the embed pipeline has been run (scripts/embed_database.py)
        logger.warning("ChromaDB init failed: %s — search will return empty results", exc)

    # 2. Test Ollama connectivity — just a lightweight import; actual ping
    #    happens on first real embed/judge call.
    try:
        import ollama  # noqa: F401 — confirms the package is installed and importable
        logger.info("Ollama package ready (host: %s)", settings.ollama_host)
    except ImportError as exc:
        logger.error("Ollama package not installed: %s", exc)

    # 3. Create database tables via SQLAlchemy
    from app.core.database import engine, Base
    import app.models.exercise  # noqa: F401 — ensure models are registered
    
    async with engine.begin() as conn:
        logger.info("Creating database tables (if they don't exist)...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified.")

    logger.info("API ready — accepting connections")
    yield

    # ── Shutdown ──
    logger.info("Shutting down Exercise Identifier API")


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Exercise Identifier API",
    description="Semantic exercise search via text description and video pose estimation.",
    version=settings.api_version,
    lifespan=lifespan,
    # Disable default /docs in production; enable for development
    docs_url="/docs" if settings.debug else "/docs",
    redoc_url="/redoc" if settings.debug else None,
)

# ─── Middleware ────────────────────────────────────────────────────────────────
# CORS origins are loaded from settings — override via CORS_ORIGINS env var
# in production to add the Vercel deployment URL.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(search.router)
app.include_router(exercises.router)


# ─── Root & Health ────────────────────────────────────────────────────────────

@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Exercise Identifier API",
        "version": settings.api_version,
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
async def health():
    """
    Dependency health check. Used by ECS health checks and monitoring.
    Returns 200 even if some dependencies are degraded — callers should
    inspect the per-dependency status fields.
    """
    status: dict[str, str] = {}

    # ChromaDB
    try:
        col = get_chroma_collection()
        status["vector_db"] = f"ok ({col.count()} vectors)"
    except Exception as exc:
        status["vector_db"] = f"error: {exc}"

    # Ollama — lightweight check via the list endpoint
    try:
        from ollama import AsyncClient
        client = AsyncClient(host=settings.ollama_host)
        models = await client.list()
        pulled = [m.model for m in models.models]
        embed_ok = settings.ollama_embed_model in pulled
        judge_ok = settings.ollama_judge_model in pulled
        status["ollama"] = "ok"
        status["embed_model"] = settings.ollama_embed_model if embed_ok else f"NOT PULLED: {settings.ollama_embed_model}"
        status["judge_model"] = settings.ollama_judge_model if judge_ok else f"NOT PULLED: {settings.ollama_judge_model}"
    except Exception as exc:
        status["ollama"] = f"unreachable: {exc}"

    overall = "ok" if all("error" not in v and "unreachable" not in v for v in status.values()) else "degraded"

    return {"status": overall, **status}


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

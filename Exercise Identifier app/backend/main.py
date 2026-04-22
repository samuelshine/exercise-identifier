"""
Exercise Identifier - Backend entrypoint.

This module spins up a minimal FastAPI app to validate the infrastructure is
wired up correctly. The routes defined here are intentionally scaffolding-only;
gym/exercise business logic belongs in dedicated modules under a future
`app/` package (e.g. `app/routers/`, `app/services/ai/`) so that the AI layer
remains decoupled from core logic, per project guidelines.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Exercise Identifier API",
    version="0.1.0",
    description="MVP backend for identifying gym strength-training exercises.",
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


@app.get("/")
async def root() -> dict[str, str]:
    """Sanity-check endpoint so the frontend (and humans) can confirm uptime."""
    return {"message": "Hello World"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Lightweight liveness probe — useful for container orchestrators later."""
    return {"status": "ok"}

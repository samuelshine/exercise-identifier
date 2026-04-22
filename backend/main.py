from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import search, exercises


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load ChromaDB collection, verify Ollama connectivity
    yield
    # Shutdown: cleanup


app = FastAPI(
    title="Exercise Identifier API",
    version="0.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(exercises.router)


@app.get("/")
async def root():
    return {"message": "Exercise Identifier API v0.4.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}

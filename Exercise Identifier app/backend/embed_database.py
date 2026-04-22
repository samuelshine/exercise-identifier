"""
embed_database.py
=================
One-shot script that reads all ``beginner_description`` MovementDescriptor
rows from PostgreSQL and upserts them into a local ChromaDB collection.

Design
------
* **Embeddings are generated locally** via the Ollama ``nomic-embed-text``
  model — no cloud API calls, no cost, fully offline.
* **ChromaDB runs in persistent mode** with data stored in ``./chroma_db/``.
  The collection name is ``exercise_descriptions``.
* **Metadata links back to Postgres**: each ChromaDB document stores the
  ``exercise_id`` (UUID) so the search endpoint can join back to the
  relational DB for full exercise details.
* **Idempotent**: uses deterministic IDs derived from the Postgres
  ``MovementDescriptor.id`` UUID.  Re-running overwrites with fresh
  embeddings rather than duplicating.

Prerequisites
-------------
    ollama serve                     # in another terminal
    ollama pull nomic-embed-text     # one-time download
    # Postgres up with the 50-exercise dataset already ingested

Usage
-----
    cd backend
    source venv/bin/activate
    python embed_database.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid

import chromadb
import ollama
from sqlalchemy import select
from tqdm import tqdm

from app.core.database import async_session_factory
from app.models import DescriptorCategory, Exercise, MovementDescriptor


# ---------- Configuration ----------------------------------------------------

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION = "exercise_descriptions"


# ---------- Embedding helper -------------------------------------------------


def get_embedding(text: str) -> list[float]:
    """Generate an embedding vector for a single text string using Ollama."""
    client = ollama.Client(host=OLLAMA_HOST)
    response = client.embed(model=OLLAMA_EMBED_MODEL, input=text)
    return response["embeddings"][0]


# ---------- Main pipeline ----------------------------------------------------


async def load_descriptors() -> list[dict]:
    """Read all BEGINNER_DESCRIPTION rows from Postgres with their exercise name."""
    async with async_session_factory() as session:
        stmt = (
            select(
                MovementDescriptor.id,
                MovementDescriptor.exercise_id,
                MovementDescriptor.text,
                Exercise.primary_name,
            )
            .join(Exercise, MovementDescriptor.exercise_id == Exercise.id)
            .where(MovementDescriptor.category == DescriptorCategory.BEGINNER_DESCRIPTION)
            .order_by(Exercise.primary_name)
        )
        result = await session.execute(stmt)
        return [
            {
                "descriptor_id": str(row.id),
                "exercise_id": str(row.exercise_id),
                "text": row.text,
                "exercise_name": row.primary_name,
            }
            for row in result.all()
        ]


def build_collection(descriptors: list[dict]) -> None:
    """Embed all descriptors and upsert them into ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Get or create the collection (no default embedding function —
    # we supply our own embeddings from Ollama).
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    ids: list[str] = []
    documents: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict] = []

    progress = tqdm(descriptors, desc="Embedding", unit="desc", file=sys.stdout)
    for desc in progress:
        progress.set_postfix_str(desc["exercise_name"][:25])

        embedding = get_embedding(desc["text"])

        ids.append(desc["descriptor_id"])
        documents.append(desc["text"])
        embeddings.append(embedding)
        metadatas.append({
            "exercise_id": desc["exercise_id"],
            "exercise_name": desc["exercise_name"],
        })

    # Upsert in one batch — ChromaDB handles this efficiently for ~200 docs.
    print(f"\nUpserting {len(ids)} vectors into ChromaDB collection '{CHROMA_COLLECTION}'...")
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
    print(f"  Collection now has {collection.count()} documents.")


async def main() -> int:
    print(f"Embed model: {OLLAMA_EMBED_MODEL}   Host: {OLLAMA_HOST}")
    print(f"ChromaDB:    {CHROMA_PERSIST_DIR} / {CHROMA_COLLECTION}\n")

    # 1. Load from Postgres
    print("Loading beginner_descriptions from PostgreSQL...")
    descriptors = await load_descriptors()
    print(f"  Found {len(descriptors)} descriptions across exercises.\n")

    if not descriptors:
        print("No descriptors found — nothing to embed. Run generate_exercise_dataset.py first.")
        return 1

    # 2. Embed + upsert into ChromaDB
    build_collection(descriptors)

    print("\n✓ Embedding pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

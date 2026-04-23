"""
PostgreSQL → ChromaDB embedding pipeline.

Reads all MovementDescriptor rows with needs_reindex=True from PostgreSQL,
generates 768-dim embeddings via Ollama nomic-embed-text, and upserts them
into ChromaDB. Updates vector_id, embedding_model, and needs_reindex on each row.

Usage:
    cd backend
    python -m scripts.embed_database              # embed only stale rows
    python -m scripts.embed_database --all        # force re-embed everything
    python -m scripts.embed_database --dry-run    # preview without writing

Prerequisites:
    1. PostgreSQL running with the exercise schema and seed data loaded
    2. Ollama running with nomic-embed-text pulled:
           ollama pull nomic-embed-text
    3. Dependencies installed:
           pip install -r requirements.txt
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Allow running as `python -m scripts.embed_database` from the backend/ dir
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tqdm import tqdm

from app.core.config import get_settings
from app.core.database import async_session_factory, engine
from app.models.exercise import MovementDescriptor
from app.services.embedding import embed_query, get_chroma_collection

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ─── Core pipeline ────────────────────────────────────────────────────────────

async def run_pipeline(force_all: bool = False, dry_run: bool = False) -> None:
    settings = get_settings()

    async with async_session_factory() as session:
        from sqlalchemy import select

        stmt = select(MovementDescriptor)
        if not force_all:
            stmt = stmt.where(MovementDescriptor.needs_reindex.is_(True))
        stmt = stmt.order_by(MovementDescriptor.exercise_id, MovementDescriptor.category)

        result = await session.execute(stmt)
        descriptors: list[MovementDescriptor] = result.scalars().all()

    if not descriptors:
        logger.info("No descriptors require embedding. Database is fully indexed.")
        return

    logger.info(
        "Found %d descriptor(s) to embed (force_all=%s, dry_run=%s)",
        len(descriptors), force_all, dry_run,
    )

    if dry_run:
        for d in descriptors[:10]:
            logger.info("  [dry-run] Would embed: %s / %s — %r", d.exercise_id, d.category, d.text[:60])
        if len(descriptors) > 10:
            logger.info("  ... and %d more", len(descriptors) - 10)
        return

    # ── Embedding loop ──────────────────────────────────────────────────────
    collection = get_chroma_collection()

    success_count = 0
    error_count = 0

    # Process in batches: upsert to ChromaDB in groups of 50,
    # then commit DB updates in the same batch — reduces round trips
    BATCH_SIZE = 50

    async with async_session_factory() as session:
        batch_ids:         list[str] = []
        batch_embeddings:  list[list[float]] = []
        batch_documents:   list[str] = []
        batch_metadatas:   list[dict] = []
        batch_descriptors: list[MovementDescriptor] = []

        with tqdm(total=len(descriptors), desc="Embedding", unit="desc") as pbar:
            for descriptor in descriptors:
                try:
                    embedding = await embed_query(descriptor.text)
                except Exception as exc:
                    logger.error(
                        "Failed to embed descriptor %s: %s — skipping", descriptor.id, exc
                    )
                    error_count += 1
                    pbar.update(1)
                    continue

                vector_id = str(descriptor.id)  # use the descriptor UUID as the vector ID

                batch_ids.append(vector_id)
                batch_embeddings.append(embedding)
                batch_documents.append(descriptor.text)
                batch_metadatas.append({
                    "exercise_id": str(descriptor.exercise_id),
                    "category":    descriptor.category.value,
                    "descriptor_id": str(descriptor.id),
                })
                batch_descriptors.append(descriptor)

                if len(batch_ids) >= BATCH_SIZE:
                    await _flush_batch(
                        session, collection,
                        batch_ids, batch_embeddings, batch_documents,
                        batch_metadatas, batch_descriptors,
                        settings.ollama_embed_model,
                    )
                    success_count += len(batch_ids)
                    batch_ids, batch_embeddings, batch_documents = [], [], []
                    batch_metadatas, batch_descriptors = [], []

                pbar.update(1)

            # Flush any remaining items
            if batch_ids:
                await _flush_batch(
                    session, collection,
                    batch_ids, batch_embeddings, batch_documents,
                    batch_metadatas, batch_descriptors,
                    settings.ollama_embed_model,
                )
                success_count += len(batch_ids)

    logger.info(
        "Pipeline complete: %d embedded, %d errors. ChromaDB now has %d total vectors.",
        success_count, error_count, collection.count(),
    )


async def _flush_batch(
    session,
    collection,
    ids:         list[str],
    embeddings:  list[list[float]],
    documents:   list[str],
    metadatas:   list[dict],
    descriptors: list[MovementDescriptor],
    model_name:  str,
) -> None:
    """
    Upsert a batch into ChromaDB, then update the PostgreSQL rows.
    Both operations must succeed — ChromaDB first (idempotent upsert),
    then PostgreSQL commit.
    """
    # ChromaDB upsert is idempotent: safe to re-run on the same IDs
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    # Mark descriptors as indexed in PostgreSQL
    for descriptor, vector_id in zip(descriptors, ids):
        descriptor.vector_id      = vector_id
        descriptor.embedding_model = model_name
        descriptor.needs_reindex  = False
        session.add(descriptor)

    await session.commit()


# ─── Entry point ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        dest="force_all",
        action="store_true",
        help="Re-embed all descriptors, not just those with needs_reindex=True",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which descriptors would be embedded without writing anything",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_pipeline(force_all=args.force_all, dry_run=args.dry_run))

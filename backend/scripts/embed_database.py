"""Postgres → ChromaDB embedding pipeline.

Usage:
    cd backend
    python -m scripts.embed_database

Reads all BEGINNER_DESCRIPTION MovementDescriptor rows from PostgreSQL,
generates embeddings via nomic-embed-text, and upserts into ChromaDB.
Requires: Ollama running with nomic-embed-text model pulled.
"""

# TODO: port from old embed_database.py

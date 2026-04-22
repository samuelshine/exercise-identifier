"""Vector embedding and ChromaDB retrieval logic."""

# TODO: extract from old main.py
# - embed_query(text) → vector via Ollama nomic-embed-text
# - search_similar(vector, top_k) → ChromaDB cosine kNN
# - deduplicate by exercise_id, keep best match per exercise

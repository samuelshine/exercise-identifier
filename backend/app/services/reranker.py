"""LLM re-ranking service using Ollama."""

# TODO: extract from old main.py
# - rerank_candidates(query, candidates) → scored results via gemma4:e4b
# - biomechanist system prompt evaluating body position, force direction, equipment
# - fallback to vector similarity if LLM fails

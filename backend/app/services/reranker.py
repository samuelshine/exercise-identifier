"""
LLM re-ranking service.

Takes the top-N candidates from the vector search stage and asks an Ollama
judge model to score each one against the original query using biomechanical
reasoning. Falls back to vector-similarity ordering if the LLM call fails,
times out, or returns malformed JSON.

Judge model: gemma4:e4b (local Ollama)
  - Low temperature (0.1) for consistent, deterministic scoring
  - JSON output mode to eliminate post-processing ambiguity
  - Hard timeout enforced via asyncio.wait_for — never blocks the request indefinitely
"""

import asyncio
import json
import logging
from typing import TypedDict

from app.core.config import get_settings
from app.schemas.exercise import ExerciseRead, SearchResultItem
from app.services.embedding import Candidate

logger = logging.getLogger(__name__)


# ─── Internal type ────────────────────────────────────────────────────────────

class HydratedCandidate(TypedDict):
    """A vector Candidate enriched with its full Exercise ORM data."""
    exercise_id: str
    matched_description: str
    similarity: float
    exercise: ExerciseRead


# ─── Prompt builder ───────────────────────────────────────────────────────────

def _build_prompt(query: str, candidates: list[HydratedCandidate]) -> str:
    """
    Construct the biomechanics evaluation prompt.

    Deliberately terse candidate summaries to stay within the judge model's
    effective context window. We pass:
      - Primary name and aliases (what the exercise is called)
      - Movement pattern + force type (biomechanical classification)
      - Equipment required (matches explicit equipment mentions in the query)
      - Primary muscles targeted (implies body part and movement direction)
      - The two most relevant descriptor texts already matched by vector search
    """
    lines = []
    for c in candidates:
        ex = c["exercise"]
        aliases = ", ".join(a.alias for a in ex.aliases[:3]) if ex.aliases else "none"
        muscles = ", ".join(ex.primary_muscles[:4]) if ex.primary_muscles else "unknown"
        equipment = ", ".join(ex.equipment_required[:4]) if ex.equipment_required else "bodyweight"
        # Top 2 descriptor texts give the judge the richest matching signal
        desc_texts = [d.text for d in ex.movement_descriptors[:2]]
        desc = " | ".join(desc_texts) if desc_texts else ex.summary or ""

        lines.append(
            f'ID: {ex.id}\n'
            f'Name: {ex.primary_name} (aka: {aliases})\n'
            f'Pattern: {ex.movement_pattern.value}, Force: {ex.force_type.value}, '
            f'Mechanic: {ex.mechanic.value}\n'
            f'Equipment: {equipment}\n'
            f'Primary muscles: {muscles}\n'
            f'Description: {desc}'
        )

    candidates_block = "\n\n".join(f"[{i + 1}]\n{l}" for i, l in enumerate(lines))

    return f"""You are an expert biomechanics coach and certified personal trainer.

A gym user described an exercise they observed. Your job: score each candidate exercise on how precisely it matches their description.

USER DESCRIPTION:
"{query}"

CANDIDATE EXERCISES:
{candidates_block}

SCORING RUBRIC:
- Body position match: Does the candidate match the described position (lying, standing, seated, hunched, etc.)?
- Force direction match: Is the pushing/pulling/hinging direction consistent with the description?
- Equipment match: If equipment is mentioned or implied, does it match?
- Muscle/body-part match: If a body part is mentioned, does this exercise target it?

RETURN: A JSON object with a "rankings" array. Do not include any text outside the JSON.
Each ranking item MUST have:
  "exercise_id": string (the UUID exactly as shown above)
  "score": float between 0.0 and 1.0 (1.0 = perfect match, 0.0 = completely wrong)
  "reasoning": string of exactly one sentence explaining the score

Example format:
{{"rankings": [{{"exercise_id": "...", "score": 0.93, "reasoning": "Matches supine dumbbell pressing with chest as primary target."}}]}}"""


# ─── Main re-ranker ───────────────────────────────────────────────────────────

async def rerank_candidates(
    query: str,
    candidates: list[HydratedCandidate],
    top_k: int,
) -> list[SearchResultItem]:
    """
    Score candidates via the Ollama judge model and return top_k ranked results.

    Fallback behaviour:
      - asyncio.TimeoutError  → LLM too slow; fall back to vector order
      - json.JSONDecodeError  → Malformed LLM output; fall back to vector order
      - Any other exception   → Log warning; fall back to vector order

    The fallback always produces a valid SearchResponse — the frontend never
    sees a 500 error due to a flaky LLM. The reasoning field distinguishes
    LLM-ranked from fallback-ranked results so the UI can show a subtle indicator.
    """
    if not candidates:
        return []

    settings = get_settings()

    try:
        from ollama import AsyncClient

        prompt = _build_prompt(query, candidates)
        client = AsyncClient(host=settings.ollama_host)

        raw_response = await asyncio.wait_for(
            client.generate(
                model=settings.ollama_judge_model,
                prompt=prompt,
                format="json",
                options={
                    "temperature": 0.1,  # near-deterministic scoring
                    "num_predict": 512,  # cap output tokens — we only need short JSON
                },
            ),
            timeout=settings.ollama_judge_timeout,
        )

        parsed = json.loads(raw_response["response"])
        rankings: list[dict] = parsed.get("rankings", [])

        if not rankings:
            raise ValueError("LLM returned empty rankings array")

        # Build a map: exercise_id → (score, reasoning)
        score_map: dict[str, tuple[float, str]] = {}
        for item in rankings:
            ex_id = str(item.get("exercise_id", ""))
            score = float(item.get("score", 0.0))
            reasoning = str(item.get("reasoning", "No reasoning provided."))
            score_map[ex_id] = (max(0.0, min(1.0, score)), reasoning)

        logger.info(
            "LLM re-ranking complete: %d candidates scored (judge: %s)",
            len(score_map),
            settings.ollama_judge_model,
        )

        # Sort candidates by LLM score; fall back to similarity for unscored ones
        def sort_key(c: HydratedCandidate) -> float:
            return score_map.get(str(c["exercise"].id), (c["similarity"], ""))[0]

        sorted_candidates = sorted(candidates, key=sort_key, reverse=True)

        results: list[SearchResultItem] = []
        for i, c in enumerate(sorted_candidates[:top_k]):
            ex_id = str(c["exercise"].id)
            llm_score, reasoning = score_map.get(ex_id, (c["similarity"], "Ranked by semantic similarity."))
            results.append(
                SearchResultItem(
                    rank=i + 1,
                    similarity_score=round(llm_score, 4),
                    matched_description=c["matched_description"],
                    reasoning=reasoning,
                    exercise=c["exercise"],
                )
            )

        return results

    except asyncio.TimeoutError:
        logger.warning(
            "LLM re-ranking timed out after %.1fs — falling back to vector similarity",
            settings.ollama_judge_timeout,
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("LLM re-ranking produced invalid JSON (%s) — falling back", exc)
    except Exception as exc:
        logger.warning("LLM re-ranking failed unexpectedly (%s: %s) — falling back", type(exc).__name__, exc)

    return _vector_fallback(candidates, top_k)


def _vector_fallback(
    candidates: list[HydratedCandidate],
    top_k: int,
) -> list[SearchResultItem]:
    """
    Fallback ranking: sort by raw vector similarity score.
    Used when the LLM judge is unavailable or fails.
    The reasoning field signals to callers that this is a degraded response.
    """
    sorted_c = sorted(candidates, key=lambda c: c["similarity"], reverse=True)
    return [
        SearchResultItem(
            rank=i + 1,
            similarity_score=c["similarity"],
            matched_description=c["matched_description"],
            reasoning="Ranked by semantic similarity (AI re-ranking unavailable).",
            exercise=c["exercise"],
        )
        for i, c in enumerate(sorted_c[:top_k])
    ]

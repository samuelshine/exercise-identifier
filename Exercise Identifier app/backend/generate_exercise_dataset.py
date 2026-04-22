"""
generate_exercise_dataset.py
============================
Local seed-data generator for the Exercise Identifier MVP.

Uses a **local** Ollama server (http://localhost:11434) — no cloud APIs —
to produce structured exercise records for a hand-picked list of common
gym lifts, validates the output against our Pydantic schemas, and writes
it to Postgres via SQLAlchemy.

Prereqs
-------
    ollama serve                       # in another terminal
    ollama pull gemma4:e4b             # or whatever OLLAMA_MODEL resolves to
    # Postgres up and DATABASE_URL pointing at it

Run
---
    cd backend
    source venv/bin/activate
    python generate_exercise_dataset.py

Design
------
* **AI call is isolated** in one helper. The rest of the script is pure
  parse → validate → insert. That boundary is the seam for swapping
  model/provider later (per project guideline: decoupled AI layer).
* **Sequential, not parallel.** A single local Ollama instance queues
  concurrent chats internally — parallelism here just burns RAM.
* **Two-stage validation:** JSON decode first, then strict Pydantic.
  Each failure mode gets its own error + retry path so we can report
  meaningfully when the local model drifts.
* **Idempotent.** Existing exercises (matched by primary_name) are
  skipped, so re-runs top up what's missing rather than duplicating.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass

import ollama
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

from app.core.config import get_settings
from app.core.database import (
    Base,
    async_session_factory,
    engine,
    ensure_database_exists,
)
from app.models import (
    DescriptorCategory,
    DifficultyLevel,
    EquipmentType,
    Exercise,
    ExerciseAlias,
    ExerciseEquipment,
    ExerciseMuscleGroup,
    ForceType,
    MechanicType,
    MovementDescriptor,
    MovementPattern,
    MuscleGroup,
)


# ---------- Configuration ---------------------------------------------------

OLLAMA_HOST = "http://localhost:11434"

# NOTE: As of writing, the Ollama registry does not list `gemma4:e4b`.
# Closest real models are `gemma3n:e4b` and `gemma3:4b`. Using the exact
# name requested — change here if you meant one of the above.
OLLAMA_MODEL = "gemma4:e4b"

REQUEST_TIMEOUT_S = 180.0   # generous — local models can be slow warm starts
MAX_RETRIES = 3             # per exercise
TEMPERATURE = 0.4           # mild variety, still well-grounded


SEED_EXERCISES: list[str] = [
    # ── Chest ────────────────────────────────────────────────────────
    "Barbell Bench Press",
    "Dumbbell Bench Press",
    "Incline Barbell Press",
    "Incline Dumbbell Press",
    "Decline Bench Press",
    "Cable Crossover",
    "Pec Deck Machine",
    "Push-ups",
    # ── Shoulders ────────────────────────────────────────────────────
    "Barbell Overhead Press",
    "Dumbbell Shoulder Press",
    "Arnold Press",
    "Dumbbell Lateral Raise",
    "Cable Lateral Raise",
    "Front Raise",
    "Reverse Pec Deck",
    # ── Triceps ──────────────────────────────────────────────────────
    "Tricep Pushdown",
    "Overhead Tricep Extension",
    "Skull Crushers",
    "Close-Grip Bench Press",
    "Tricep Kickbacks",
    # ── Back ─────────────────────────────────────────────────────────
    "Lat Pulldown",
    "Pull-ups",
    "Barbell Row",
    "Dumbbell Row",
    "Seated Cable Row",
    "T-Bar Row",
    "Straight Arm Pulldown",
    # ── Biceps ───────────────────────────────────────────────────────
    "Barbell Bicep Curl",
    "Dumbbell Alternate Bicep Curl",
    "Hammer Curl",
    "Preacher Curl",
    "Cable Curl",
    # ── Quads / Compound Legs ────────────────────────────────────────
    "Barbell Back Squat",
    "Barbell Front Squat",
    "Leg Press",
    "Goblet Squat",
    "Bulgarian Split Squat",
    "Walking Lunges",
    # ── Posterior Chain ──────────────────────────────────────────────
    "Romanian Deadlift (RDL)",
    "Conventional Deadlift",
    "Leg Extension Machine",
    "Seated Leg Curl",
    "Lying Leg Curl",
    # ── Calves / Glutes ─────────────────────────────────────────────
    "Standing Calf Raise",
    "Seated Calf Raise",
    "Hip Thrust",
    "Cable Pull-Through",
    # ── Core ─────────────────────────────────────────────────────────
    "Cable Woodchopper",
    "Hanging Leg Raise",
    "Ab Rollout",
]


# ---------- LLM I/O schema --------------------------------------------------

# Intentionally a *flatter* shape than ExerciseCreate — easier for a
# small local model to produce consistently. We map to the richer ORM
# model in `persist_exercise`.


class LLMExerciseRecord(BaseModel):
    """Pydantic model defining the JSON shape we ask the local LLM to produce.

    This schema is intentionally *flatter* and *simpler* than the full
    ``ExerciseCreate`` API schema.  A small local model (Ollama / gemma4)
    produces more reliable output when the target structure has fewer
    nesting levels and no UUIDs.  The ``persist_exercise`` function maps
    this flat record into the richer, normalised ORM graph.

    ``beginner_descriptions`` (exactly 4 strings)
    -----------------------------------------------
    These are the **most important field for the RAG pipeline**.  Each
    string describes the exercise from the perspective of a total novice
    who does NOT know the exercise's name.  The 4 descriptions cover
    distinct angles:

    1. First-person body-sensation  ("I feel my ... as I ...")
    2. Third-person visual          ("A person is ...")
    3. Equipment/setup-centred      ("Using a ..., you ...")
    4. Naive/informal               ("It looks kind of like ...")

    These texts are stored as ``MovementDescriptor`` rows with category
    ``BEGINNER_DESCRIPTION`` and will be embedded into the vector database.
    When a user types a natural-language description of a movement, the
    nearest-neighbour search over these embeddings is how the MVP
    identifies the exercise.
    """

    primary_name: str = Field(min_length=1, max_length=128)
    aliases: list[str] = Field(default_factory=list, max_length=10)
    difficulty: DifficultyLevel
    mechanic: MechanicType
    force_type: ForceType
    movement_pattern: MovementPattern
    primary_muscles: list[MuscleGroup] = Field(min_length=1)
    secondary_muscles: list[MuscleGroup] = Field(default_factory=list)
    equipment: list[EquipmentType] = Field(min_length=1)
    is_unilateral: bool = False
    summary: str = Field(min_length=10)
    # Exactly 4 distinct novice-voice descriptions — these are our
    # primary RAG retrieval corpus.
    beginner_descriptions: list[str] = Field(min_length=4, max_length=4)


# ---------- Prompting -------------------------------------------------------


def _enum_values(enum_cls) -> str:
    return ", ".join(f'"{m.value}"' for m in enum_cls)


SYSTEM_PROMPT = (
    "You are an expert Kinesiologist AND an empathetic Gym Trainer. "
    "You combine biomechanics precision with the patience of a coach "
    "explaining things to a total beginner. "
    "You respond ONLY with a single valid JSON object and no other text. "
    "No markdown fences. No prose before or after. No comments."
)


USER_PROMPT_TEMPLATE = """Generate a detailed structured record for the following strength-training exercise:

EXERCISE: {exercise_name}

Return ONE JSON object with EXACTLY these keys:

{{
  "primary_name": string (the canonical name, e.g. "Barbell Bench Press"),
  "aliases": array of 3-6 strings (common alternate names, abbreviations, typos users actually type; exclude the primary name itself),
  "difficulty": one of [{difficulty}],
  "mechanic": one of [{mechanic}],
  "force_type": one of [{force_type}],
  "movement_pattern": one of [{movement_pattern}],
  "primary_muscles": array of 1-2 values from [{muscle_group}],
  "secondary_muscles": array of 0-4 values from [{muscle_group}],
  "equipment": array of 1-3 values from [{equipment}],
  "is_unilateral": boolean (true only if performed one limb at a time),
  "summary": string (2-3 sentence kinesiologist-style summary),
  "beginner_descriptions": array of EXACTLY 4 strings
}}

CRITICAL — `beginner_descriptions` rules:
  Each string describes the movement from the perspective of a TOTAL NOVICE
  who DOES NOT KNOW the exercise name. They describe ONLY what they see or
  feel. The 4 descriptions must be distinct from each other:
    1. First-person body-sensation ("I feel my ... as I ...")
    2. Third-person visual ("A person is ...")
    3. Equipment/setup-centered ("Using a ..., you ...")
    4. Naive/informal ("It looks kind of like ...")
  Each 1-2 sentences. Avoid the exercise name, muscle names in technical
  form, and coaching jargon.

Use ONLY the enum string values listed above. Return only the JSON object."""


def build_user_prompt(exercise_name: str) -> str:
    return USER_PROMPT_TEMPLATE.format(
        exercise_name=exercise_name,
        difficulty=_enum_values(DifficultyLevel),
        mechanic=_enum_values(MechanicType),
        force_type=_enum_values(ForceType),
        movement_pattern=_enum_values(MovementPattern),
        muscle_group=_enum_values(MuscleGroup),
        equipment=_enum_values(EquipmentType),
    )


# ---------- JSON cleaning ---------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def strip_to_json(raw: str) -> str:
    """Make a best effort to extract a JSON object from sloppy LLM output.

    Handles: leading/trailing prose, ```json fences, stray commentary.
    Returns the substring from the first `{` to the matching closing `}`.
    Raises ValueError if no plausible JSON object is found.
    """
    text = raw.strip()

    # 1. If the model wrapped output in a code fence, pull out the fence body.
    m = _FENCE_RE.search(text)
    if m:
        text = m.group(1).strip()

    # 2. Find the outermost {...} by brace counting (survives stray prose).
    start = text.find("{")
    if start == -1:
        raise ValueError("no `{` found in model output")

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("unterminated JSON object in model output")


def safe_json_loads(raw: str) -> dict:
    """json.loads with markdown-fence stripping + outer-object extraction."""
    cleaned = strip_to_json(raw)
    return json.loads(cleaned)


# ---------- Ollama client ---------------------------------------------------


@dataclass
class GenerationError(Exception):
    stage: str  # "connection" | "decode" | "validation"
    detail: str

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.stage}] {self.detail}"


async def call_ollama(exercise_name: str) -> str:
    """Single chat call. Raises GenerationError('connection', ...) on
    transport failure so the retry loop can distinguish from bad output."""
    client = ollama.AsyncClient(host=OLLAMA_HOST, timeout=REQUEST_TIMEOUT_S)
    try:
        response = await client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(exercise_name)},
            ],
            # `format="json"` nudges the model into JSON-only output at the
            # Ollama level. Still not a guarantee, hence the cleaning helper.
            format="json",
            options={
                "temperature": TEMPERATURE,
                "num_predict": 1500,
            },
        )
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        raise GenerationError("connection", f"{type(e).__name__}: {e}") from e
    except Exception as e:
        # ollama-python wraps httpx errors; catch broadly so one test-unfriendly
        # class doesn't crash the whole run.
        name = type(e).__name__
        if "Connect" in name or "Timeout" in name or "Connection" in name:
            raise GenerationError("connection", f"{name}: {e}") from e
        raise
    return response["message"]["content"]


async def generate_exercise_record(exercise_name: str) -> LLMExerciseRecord:
    """Call the LLM with retries. Each retry gets a fresh attempt; we don't
    try to 'repair' responses here — if the model is misbehaving, iterating
    on the prompt is cheaper than building a JSON-repair engine."""
    last_error: str = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = await call_ollama(exercise_name)
        except GenerationError as e:
            if e.stage == "connection":
                # Connection errors aren't "the model is confused" — they're
                # fatal for this attempt and usually for the run. Still give
                # one more try in case of a transient blip.
                last_error = str(e)
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(2.0)
                continue
            raise

        try:
            data = safe_json_loads(raw)
        except (ValueError, json.JSONDecodeError) as e:
            last_error = f"JSON decode failed: {e}. Raw head: {raw[:200]!r}"
            continue

        try:
            return LLMExerciseRecord.model_validate(data)
        except ValidationError as e:
            last_error = f"Pydantic validation failed: {e.errors()[:3]}"
            continue

    raise GenerationError("validation", f"gave up after {MAX_RETRIES} attempts — {last_error}")


# ---------- Persistence -----------------------------------------------------


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


async def exercise_exists(session: AsyncSession, primary_name: str) -> bool:
    stmt = select(Exercise.id).where(Exercise.primary_name == primary_name)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def persist_exercise(session: AsyncSession, record: LLMExerciseRecord) -> Exercise:
    """Map a validated LLM record into ORM rows + flush them.

    Does NOT commit — the caller controls transaction boundaries so a
    failure partway through a batch doesn't leave orphan rows."""
    exercise = Exercise(
        primary_name=record.primary_name,
        slug=slugify(record.primary_name),
        difficulty=record.difficulty,
        mechanic=record.mechanic,
        force_type=record.force_type,
        movement_pattern=record.movement_pattern,
        summary=record.summary,
        is_unilateral=record.is_unilateral,
    )

    # Aliases
    seen_aliases: set[str] = set()
    for alias in record.aliases:
        key = alias.strip().lower()
        if not key or key == record.primary_name.lower() or key in seen_aliases:
            continue
        seen_aliases.add(key)
        exercise.aliases.append(ExerciseAlias(alias=alias.strip()))

    # Muscles — dedupe and prefer "primary" when a muscle appears in both lists.
    primary_set = set(record.primary_muscles)
    for m in primary_set:
        exercise.muscle_groups.append(
            ExerciseMuscleGroup(muscle_group=m, is_primary=True)
        )
    for m in record.secondary_muscles:
        if m in primary_set:
            continue
        exercise.muscle_groups.append(
            ExerciseMuscleGroup(muscle_group=m, is_primary=False)
        )

    # Equipment — dedupe.
    for eq in set(record.equipment):
        exercise.equipment.append(ExerciseEquipment(equipment_type=eq))

    # Beginner descriptions → MovementDescriptor rows, one per description.
    # These are the primary retrieval corpus for the text RAG search.
    # `needs_reindex=True` by default flags them for the (future) vector worker.
    for text in record.beginner_descriptions:
        text = text.strip()
        if not text:
            continue
        exercise.movement_descriptors.append(
            MovementDescriptor(
                category=DescriptorCategory.BEGINNER_DESCRIPTION,
                text=text,
            )
        )

    # Summary also gets a descriptor row so it's embeddable alongside beginner text.
    exercise.movement_descriptors.append(
        MovementDescriptor(
            category=DescriptorCategory.SUMMARY,
            text=record.summary,
        )
    )

    session.add(exercise)
    await session.flush()
    return exercise


# ---------- Orchestration ---------------------------------------------------


async def ensure_schema() -> None:
    """Create the database (if missing) and all tables.

    Two-step because `CREATE DATABASE` and `CREATE TABLE` require
    different connection contexts — see `ensure_database_exists` for
    why.
    """
    created = await ensure_database_exists()
    if created:
        print(f"  Created database {get_settings().database_url.rsplit('/', 1)[-1]!r}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def run(seed: list[str]) -> dict[str, int]:
    stats = {"created": 0, "skipped": 0, "failed": 0}

    progress = tqdm(seed, desc="Generating", unit="ex", file=sys.stdout)
    async with async_session_factory() as session:
        for name in progress:
            progress.set_postfix_str(name[:30])
            try:
                if await exercise_exists(session, name):
                    stats["skipped"] += 1
                    progress.write(f"  - skip  {name} (already in DB)")
                    continue

                record = await generate_exercise_record(name)
                await persist_exercise(session, record)
                await session.commit()
                stats["created"] += 1
                progress.write(f"  + ok    {name}")
            except GenerationError as e:
                stats["failed"] += 1
                await session.rollback()
                progress.write(f"  ! fail  {name}  — {e}")
            except Exception as e:  # noqa: BLE001 — top-level run loop
                stats["failed"] += 1
                await session.rollback()
                progress.write(f"  ! fail  {name}  — {type(e).__name__}: {e}")

    return stats


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument(
        "--no-create-tables",
        action="store_true",
        help="Skip the convenience `CREATE TABLE IF NOT EXISTS` step.",
    )
    p.add_argument(
        "--only",
        nargs="+",
        default=None,
        help="Override seed list (space-separated exercise names).",
    )
    return p.parse_args()


async def main() -> int:
    args = parse_args()
    seed = args.only if args.only else SEED_EXERCISES

    if not args.no_create_tables:
        await ensure_schema()

    print(f"Model: {OLLAMA_MODEL}   Host: {OLLAMA_HOST}   Exercises: {len(seed)}")
    stats = await run(seed)
    print(
        f"\nDone. created={stats['created']}  "
        f"skipped={stats['skipped']}  failed={stats['failed']}"
    )
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

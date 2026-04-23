"""
Exercise CRUD router.

Endpoints:
  GET    /exercises                  — paginated list with filters
  GET    /exercises/{id}             — full detail by UUID
  GET    /exercises/slug/{slug}      — full detail by slug (SEO-friendly)
  POST   /exercises                  — create new exercise
  PATCH  /exercises/{id}             — partial update
  DELETE /exercises/{id}             — delete (cascades to all relations)
  GET    /exercises/{id}/alternatives — biomechanically filtered alternatives
"""

import logging
import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.enums import (
    AlternativeRelationship,
    DifficultyLevel,
    EquipmentType,
    MovementPattern,
    MuscleGroup,
)
from app.models.exercise import (
    Exercise,
    ExerciseAlias,
    ExerciseAlternative,
    ExerciseEquipment,
    ExerciseMuscleGroup,
    MovementDescriptor,
)
from app.schemas.exercise import (
    AlternativeMatch,
    AlternativesResponse,
    ExerciseCreate,
    ExerciseRead,
    ExerciseSummary,
    ExerciseUpdate,
    PaginatedExerciseList,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exercises", tags=["exercises"])

# Priority order for surfacing alternatives (lower index = shown first)
_RELATIONSHIP_PRIORITY: dict[AlternativeRelationship, int] = {
    AlternativeRelationship.SUBSTITUTE_FOR: 0,
    AlternativeRelationship.VARIATION_OF:   1,
    AlternativeRelationship.REGRESSION_OF:  2,
    AlternativeRelationship.PROGRESSION_OF: 3,
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_exercise_or_404(session: AsyncSession, exercise_id: uuid.UUID) -> Exercise:
    stmt = select(Exercise).where(Exercise.id == exercise_id)
    result = await session.execute(stmt)
    ex = result.scalar_one_or_none()
    if ex is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return ex


# ─── GET /exercises ───────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedExerciseList)
async def list_exercises(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    muscle_group: MuscleGroup | None = Query(default=None),
    equipment: EquipmentType | None = Query(default=None),
    difficulty: DifficultyLevel | None = Query(default=None),
    movement_pattern: MovementPattern | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> PaginatedExerciseList:
    """
    Paginated exercise list with optional filters.
    Muscle group and equipment filters use subqueries to avoid join fan-out.
    """
    base_q = select(Exercise)

    if muscle_group is not None:
        ids_with_muscle = (
            select(ExerciseMuscleGroup.exercise_id)
            .where(ExerciseMuscleGroup.muscle_group == muscle_group)
            .scalar_subquery()
        )
        base_q = base_q.where(Exercise.id.in_(ids_with_muscle))

    if equipment is not None:
        ids_with_equipment = (
            select(ExerciseEquipment.exercise_id)
            .where(ExerciseEquipment.equipment_type == equipment)
            .scalar_subquery()
        )
        base_q = base_q.where(Exercise.id.in_(ids_with_equipment))

    if difficulty is not None:
        base_q = base_q.where(Exercise.difficulty == difficulty)

    if movement_pattern is not None:
        base_q = base_q.where(Exercise.movement_pattern == movement_pattern)

    # Total count (for pagination metadata)
    count_stmt = select(func.count()).select_from(base_q.subquery())
    total: int = await session.scalar(count_stmt) or 0

    # Paginated fetch
    paginated_q = (
        base_q
        .order_by(Exercise.primary_name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await session.execute(paginated_q)
    exercises = result.scalars().all()

    return PaginatedExerciseList(
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
        results=[ExerciseSummary.model_validate(ex) for ex in exercises],
    )


# ─── GET /exercises/slug/{slug} ───────────────────────────────────────────────
# Must be defined BEFORE /{id} to prevent "slug" being parsed as a UUID

@router.get("/slug/{slug}", response_model=ExerciseRead)
async def get_exercise_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> ExerciseRead:
    stmt = select(Exercise).where(Exercise.slug == slug)
    result = await session.execute(stmt)
    ex = result.scalar_one_or_none()
    if ex is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return ExerciseRead.model_validate(ex)


# ─── GET /exercises/{id} ─────────────────────────────────────────────────────

@router.get("/{exercise_id}", response_model=ExerciseRead)
async def get_exercise(
    exercise_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> ExerciseRead:
    ex = await _get_exercise_or_404(session, exercise_id)
    return ExerciseRead.model_validate(ex)


# ─── POST /exercises ──────────────────────────────────────────────────────────

@router.post("", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
async def create_exercise(
    body: ExerciseCreate,
    session: AsyncSession = Depends(get_session),
) -> ExerciseRead:
    """
    Create a new exercise with all related records.
    All records are written in a single transaction — atomicity guaranteed.

    After creation, all MovementDescriptors have needs_reindex=True.
    Run `python -m scripts.embed_database` to embed them into ChromaDB.
    """
    exercise = Exercise(
        primary_name=body.primary_name,
        slug=body.slug,
        difficulty=body.difficulty,
        mechanic=body.mechanic,
        force_type=body.force_type,
        movement_pattern=body.movement_pattern,
        summary=body.summary,
        is_unilateral=body.is_unilateral,
    )
    session.add(exercise)

    try:
        # Flush to get the auto-generated UUID before inserting relations
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An exercise named '{body.primary_name}' or with slug '{body.slug}' already exists.",
        )

    # ── Relations ────────────────────────────────────────────────────────────
    for mg in body.primary_muscles:
        session.add(ExerciseMuscleGroup(exercise_id=exercise.id, muscle_group=mg, is_primary=True))
    for mg in body.secondary_muscles:
        session.add(ExerciseMuscleGroup(exercise_id=exercise.id, muscle_group=mg, is_primary=False))

    for eq in body.equipment_required:
        session.add(ExerciseEquipment(exercise_id=exercise.id, equipment_type=eq))

    for alias_data in body.aliases:
        session.add(ExerciseAlias(exercise_id=exercise.id, alias=alias_data.alias))

    for desc_data in body.movement_descriptors:
        session.add(
            MovementDescriptor(
                exercise_id=exercise.id,
                category=desc_data.category,
                text=desc_data.text,
                needs_reindex=True,   # embed_database.py will pick these up
            )
        )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate alias or constraint violation.",
        )

    await session.refresh(exercise)
    logger.info("Created exercise: %s (%s)", exercise.primary_name, exercise.id)
    return ExerciseRead.model_validate(exercise)


# ─── PATCH /exercises/{id} ───────────────────────────────────────────────────

@router.patch("/{exercise_id}", response_model=ExerciseRead)
async def update_exercise(
    exercise_id: uuid.UUID,
    body: ExerciseUpdate,
    session: AsyncSession = Depends(get_session),
) -> ExerciseRead:
    """
    Partial update of scalar fields only (name, slug, difficulty, etc.).
    To update muscle groups, equipment, or descriptors, use the dedicated
    sub-resource endpoints (to be added in Phase 3).
    """
    ex = await _get_exercise_or_404(session, exercise_id)

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )

    for field, value in update_data.items():
        setattr(ex, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update would create a duplicate name or slug.",
        )

    await session.refresh(ex)
    logger.info("Updated exercise: %s (%s)", ex.primary_name, ex.id)
    return ExerciseRead.model_validate(ex)


# ─── DELETE /exercises/{id} ───────────────────────────────────────────────────

@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(
    exercise_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete an exercise and all related records (cascade).
    Also deletes: aliases, muscle groups, equipment, descriptors, alternatives.
    Note: the corresponding ChromaDB vectors are NOT automatically removed.
    Run embed_database.py with a --clean flag (Phase 3) to sync the vector index.
    """
    ex = await _get_exercise_or_404(session, exercise_id)
    await session.delete(ex)
    await session.commit()
    logger.info("Deleted exercise: %s (%s)", ex.primary_name, exercise_id)


# ─── GET /exercises/{id}/alternatives ─────────────────────────────────────────

@router.get("/{exercise_id}/alternatives", response_model=AlternativesResponse)
async def get_alternatives(
    exercise_id: uuid.UUID,
    equipment: list[EquipmentType] = Query(default=[]),
    session: AsyncSession = Depends(get_session),
) -> AlternativesResponse:
    """
    Return biomechanically sound alternatives for an exercise.

    equipment (optional): comma-separated list of available EquipmentType values.
    If provided, only alternatives whose required equipment is a subset of
    the user's available equipment are returned. Bodyweight exercises are
    always included regardless of equipment filter.

    Results are sorted by relationship priority:
      substitute_for > variation_of > regression_of > progression_of
    """
    ex = await _get_exercise_or_404(session, exercise_id)

    if not ex.alternatives_from:
        return AlternativesResponse(
            exercise_id=exercise_id,
            available_equipment=equipment,
            alternatives=[],
        )

    # Collect related exercise IDs for batch loading
    related_ids = [alt.related_id for alt in ex.alternatives_from]
    stmt = select(Exercise).where(Exercise.id.in_(related_ids))
    result = await session.execute(stmt)
    related_exercises: list[Exercise] = result.scalars().all()
    related_map: dict[uuid.UUID, Exercise] = {r.id: r for r in related_exercises}

    alternatives: list[AlternativeMatch] = []
    for alt in ex.alternatives_from:
        related_ex = related_map.get(alt.related_id)
        if related_ex is None:
            continue  # referential integrity issue — skip gracefully

        # Equipment filter: pass if user has all required equipment,
        # or if the exercise is bodyweight (no equipment needed)
        if equipment:
            required = set(related_ex.equipment_required)
            available = set(equipment)
            is_bodyweight = not required  # empty equipment list = bodyweight
            if not is_bodyweight and not required.issubset(available):
                continue

        alternatives.append(
            AlternativeMatch(
                relationship_type=alt.relationship_type,
                note=alt.note,
                exercise=ExerciseSummary.model_validate(related_ex),
            )
        )

    # Sort by relationship priority
    alternatives.sort(key=lambda a: _RELATIONSHIP_PRIORITY.get(a.relationship_type, 99))

    return AlternativesResponse(
        exercise_id=exercise_id,
        available_equipment=equipment,
        alternatives=alternatives,
    )

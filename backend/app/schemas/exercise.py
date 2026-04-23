import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AlternativeRelationship,
    DescriptorCategory,
    DifficultyLevel,
    EquipmentType,
    ForceType,
    MechanicType,
    MovementPattern,
    MuscleGroup,
)


class _ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ─── Alias ────────────────────────────────────────────────────────────────────

class ExerciseAliasRead(_ORMModel):
    id: uuid.UUID
    alias: str


class ExerciseAliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=128)


# ─── MovementDescriptor ───────────────────────────────────────────────────────

class MovementDescriptorRead(_ORMModel):
    id: uuid.UUID
    category: DescriptorCategory
    text: str
    vector_id: str | None
    embedding_model: str | None
    needs_reindex: bool


class MovementDescriptorCreate(BaseModel):
    category: DescriptorCategory
    text: str = Field(min_length=1)


# ─── Alternative ─────────────────────────────────────────────────────────────

class ExerciseAlternativeRead(_ORMModel):
    id: uuid.UUID
    relationship_type: AlternativeRelationship
    related_id: uuid.UUID
    note: str | None


class ExerciseAlternativeCreate(BaseModel):
    related_id: uuid.UUID
    relationship_type: AlternativeRelationship
    note: str | None = None


# ─── Exercise ─────────────────────────────────────────────────────────────────

class ExerciseBase(BaseModel):
    primary_name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9\-]+$")
    difficulty: DifficultyLevel
    mechanic: MechanicType
    force_type: ForceType
    movement_pattern: MovementPattern
    summary: str | None = None
    is_unilateral: bool = False


class ExerciseCreate(ExerciseBase):
    primary_muscles: list[MuscleGroup] = Field(min_length=1)
    secondary_muscles: list[MuscleGroup] = []
    equipment_required: list[EquipmentType] = Field(min_length=1)
    aliases: list[ExerciseAliasCreate] = []
    movement_descriptors: list[MovementDescriptorCreate] = []


class ExerciseUpdate(BaseModel):
    primary_name: str | None = Field(None, min_length=1, max_length=128)
    slug: str | None = Field(None, min_length=1, max_length=160, pattern=r"^[a-z0-9\-]+$")
    difficulty: DifficultyLevel | None = None
    mechanic: MechanicType | None = None
    force_type: ForceType | None = None
    movement_pattern: MovementPattern | None = None
    summary: str | None = None
    is_unilateral: bool | None = None


class ExerciseSummary(_ORMModel):
    """Lightweight exercise representation — used in list endpoints and alternative cards."""
    id: uuid.UUID
    primary_name: str
    slug: str
    difficulty: DifficultyLevel
    movement_pattern: MovementPattern
    primary_muscles: list[MuscleGroup]
    equipment_required: list[EquipmentType]


class ExerciseRead(_ORMModel):
    """Full exercise representation — used in detail pages and search results."""
    id: uuid.UUID
    primary_name: str
    slug: str
    difficulty: DifficultyLevel
    mechanic: MechanicType
    force_type: ForceType
    movement_pattern: MovementPattern
    summary: str | None
    is_unilateral: bool
    created_at: datetime
    updated_at: datetime
    primary_muscles: list[MuscleGroup]
    secondary_muscles: list[MuscleGroup]
    equipment_required: list[EquipmentType]
    aliases: list[ExerciseAliasRead]
    movement_descriptors: list[MovementDescriptorRead]
    alternatives_from: list[ExerciseAlternativeRead]


# ─── Pagination ───────────────────────────────────────────────────────────────

class PaginatedExerciseList(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    results: list[ExerciseSummary]


# ─── Alternatives endpoint ───────────────────────────────────────────────────

class AlternativeMatch(BaseModel):
    """A single alternative exercise with relationship context."""
    relationship_type: AlternativeRelationship
    note: str | None
    exercise: ExerciseSummary


class AlternativesResponse(BaseModel):
    exercise_id: uuid.UUID
    available_equipment: list[EquipmentType]
    alternatives: list[AlternativeMatch]


# ─── Search ───────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class SearchResultItem(BaseModel):
    rank: int
    similarity_score: float = Field(ge=0.0, le=1.0)
    matched_description: str
    reasoning: str
    exercise: ExerciseRead


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    # Populated only by the video search endpoint
    pose_confidence: float | None = None
    classified_patterns: list[str] | None = None

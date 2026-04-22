"""Pydantic v2 schemas for the Exercise aggregate.

These schemas form the **API contract** layer of the application.  They are
decoupled from the SQLAlchemy ORM models so that:

- Column renames or internal restructuring never break the public API.
- Response shapes can be trimmed for performance (e.g. ``ExerciseSummary``
  for list views keeps mobile payloads lean).
- FastAPI's auto-generated OpenAPI docs stay clean -- ORM objects can't
  round-trip reliably due to lazy-loaded relationships and internal state.

Conventions
-----------
- ``*Base``    -- fields common to both input and output.
- ``*Create``  -- accepted on ``POST``.
- ``*Update``  -- accepted on ``PATCH`` (all fields optional).
- ``*Read``    -- returned from ``GET``.
- ``*Summary`` -- lean list-view projection.

NOTE on ``beginner_descriptions``
---------------------------------
The ``MovementDescriptorCreate`` / ``MovementDescriptorRead`` schemas carry
the ``beginner_description`` text that is the **primary retrieval corpus**
for the RAG pipeline.  These descriptions capture how a total novice would
describe a movement *without knowing its canonical name*.  They are
embedded into a vector database and matched against user natural-language
queries at inference time.  See ``app.models.exercise.MovementDescriptor``
for the full design rationale.
"""

from __future__ import annotations

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


# ---------- Shared base -----------------------------------------------------


class _ORMModel(BaseModel):
    """Base model that enables direct construction from SQLAlchemy ORM instances.

    Setting ``from_attributes=True`` allows Pydantic to read values via
    attribute access (``obj.field``) rather than dict subscript, which is
    required for seamless ORM-to-schema serialisation in FastAPI responses.
    """

    model_config = ConfigDict(from_attributes=True)


# ---------- Alias -----------------------------------------------------------


class ExerciseAliasRead(_ORMModel):
    """Read-only view of an exercise alias returned in API responses.

    Aliases are alternate names or common misspellings users might type
    (e.g. 'DB bench', 'dumbell press').  They enable a fast prefix-match
    lookup before falling back to the more expensive vector search.
    """

    id: uuid.UUID
    alias: str


class ExerciseAliasCreate(BaseModel):
    """Payload for creating a new alias via the API."""

    alias: str = Field(min_length=1, max_length=128)


# ---------- Movement descriptor --------------------------------------------


class MovementDescriptorRead(_ORMModel):
    """Read-only view of a movement descriptor returned in API responses.

    Each descriptor is an independently-embeddable text chunk.  The most
    important category is ``BEGINNER_DESCRIPTION`` -- these are the novice-
    voice descriptions that form the **primary retrieval corpus** for the
    RAG pipeline.  They are embedded into a vector database so that when
    a user describes a movement in plain language ('I lie on a bench and
    push a bar up'), the nearest-neighbour search returns the correct
    exercise.

    ``vector_id`` and ``embedding_model`` expose the vector-store sync
    state to API consumers (e.g. an admin dashboard tracking embedding
    freshness).
    """

    id: uuid.UUID
    category: DescriptorCategory
    text: str
    vector_id: str | None = None
    embedding_model: str | None = None
    needs_reindex: bool


class MovementDescriptorCreate(BaseModel):
    """Payload for creating a new movement descriptor.

    Most commonly used with ``category = BEGINNER_DESCRIPTION`` during
    data ingestion to store the novice-voice text that will later be
    embedded into the vector database for RAG retrieval.
    """

    category: DescriptorCategory
    text: str = Field(min_length=1)


# ---------- Alternatives ---------------------------------------------------


class ExerciseAlternativeRead(_ORMModel):
    """Outbound view of a related exercise link.

    We flatten `related` into a minimal dict so clients don't need to
    walk two levels of nesting for the common case ("show me related
    exercise name + id")."""

    id: uuid.UUID
    relationship_type: AlternativeRelationship
    related_id: uuid.UUID
    note: str | None = None


class ExerciseAlternativeCreate(BaseModel):
    related_id: uuid.UUID
    relationship_type: AlternativeRelationship
    note: str | None = None


# ---------- Exercise -------------------------------------------------------


class ExerciseBase(BaseModel):
    """Common fields shared across create, read, and update schemas.

    These represent the scalar attributes of the ``Exercise`` aggregate
    root.  Relationship data (muscles, equipment, descriptors, aliases)
    is handled in child schemas attached to ``ExerciseCreate`` and
    ``ExerciseRead``.
    """

    primary_name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9-]+$")
    difficulty: DifficultyLevel
    mechanic: MechanicType
    force_type: ForceType
    movement_pattern: MovementPattern
    summary: str | None = None
    is_unilateral: bool = False


class ExerciseCreate(ExerciseBase):
    """POST body for creating a new exercise with all child data inline.

    Route handlers are responsible for decomposing this flat payload into
    the normalised child rows (``ExerciseMuscleGroup``,
    ``ExerciseEquipment``, ``MovementDescriptor``, ``ExerciseAlias``).

    The ``movement_descriptors`` list should include
    ``MovementDescriptorCreate`` entries with category
    ``BEGINNER_DESCRIPTION`` -- these are the novice-voice texts that the
    RAG pipeline will embed and search against.  Four per exercise is the
    target (see ``generate_exercise_dataset.py`` for the generation logic).
    """

    primary_muscles: list[MuscleGroup] = Field(default_factory=list)
    secondary_muscles: list[MuscleGroup] = Field(default_factory=list)
    equipment_required: list[EquipmentType] = Field(default_factory=list)
    aliases: list[ExerciseAliasCreate] = Field(default_factory=list)
    movement_descriptors: list[MovementDescriptorCreate] = Field(default_factory=list)


class ExerciseUpdate(BaseModel):
    """PATCH body. All fields optional — only the ones present get applied.
    Child collections are not updated here; use dedicated sub-resource
    routes (POST /exercises/{id}/aliases etc.) for those to keep update
    semantics crisp."""

    primary_name: str | None = Field(default=None, min_length=1, max_length=128)
    slug: str | None = Field(
        default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9-]+$"
    )
    difficulty: DifficultyLevel | None = None
    mechanic: MechanicType | None = None
    force_type: ForceType | None = None
    movement_pattern: MovementPattern | None = None
    summary: str | None = None
    is_unilateral: bool | None = None


class ExerciseSummary(_ORMModel):
    """Lean list-view projection optimised for mobile-friendly payloads.

    Omits relationships (muscles, equipment, descriptors) to keep the
    response body small when listing many exercises.  Clients that need
    full detail should fetch ``ExerciseRead`` via the detail endpoint.
    """

    id: uuid.UUID
    primary_name: str
    slug: str
    difficulty: DifficultyLevel
    movement_pattern: MovementPattern


class ExerciseRead(_ORMModel):
    """Full aggregate view of an exercise, including all child data.

    Requires the ORM relationships to be loaded (the models use
    ``lazy='selectin'``, so a single async fetch is sufficient).

    The ``movement_descriptors`` list includes all descriptor categories,
    including ``BEGINNER_DESCRIPTION`` entries -- the novice-voice texts
    that are embedded into the vector database for RAG matching.  Clients
    can filter by ``category`` to isolate specific descriptor types.
    """

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

    # Flattened taxonomy views (populated by ORM @property accessors).
    primary_muscles: list[MuscleGroup] = Field(default_factory=list)
    secondary_muscles: list[MuscleGroup] = Field(default_factory=list)
    equipment_required: list[EquipmentType] = Field(default_factory=list)

    aliases: list[ExerciseAliasRead] = Field(default_factory=list)
    movement_descriptors: list[MovementDescriptorRead] = Field(default_factory=list)
    alternatives_from: list[ExerciseAlternativeRead] = Field(default_factory=list)

"""ORM models for the exercise taxonomy.

Design notes
------------
* **Exercise** is the aggregate root. Child tables (`ExerciseAlias`,
  `MovementDescriptor`, muscle-group + equipment associations, and the
  self-referential alternatives link) are modeled as separate tables
  rather than JSON columns. Reasons:
    - Aliases and descriptors need per-row metadata (category, vector_id,
      locale, source). JSON would force us to re-query constantly.
    - Vector-DB sync wants a row-per-embedding granularity so we can
      track `vector_id`, embedding model version, and last-synced-at
      per descriptor without rewriting a blob on every update.
    - Filtering by muscle group / equipment is a hot query; a real
      association table with indexed columns is far cheaper than JSONB
      containment.

* **Vector DB seam.** `MovementDescriptor.vector_id` is the single point
  of coupling to Pinecone/Milvus. A background worker (not in scope
  here) reads rows where `vector_id IS NULL OR needs_reindex = true`,
  embeds the `text` field, upserts to the vector store, and writes back
  the vector_id. The ORM layer never talks to the vector store directly.

* **Primary vs. secondary muscles.** One association table with an
  `is_primary` flag. Keeping these split as two tables looks cleaner but
  forces two writes for every update; the flag is fine and indexable.

* **Alternatives are directional.** `(exercise_id=A, related_id=B,
  relationship=PROGRESSION_OF)` reads "A is a progression of B". We do
  NOT auto-insert the inverse — a progression isn't just the mirror of
  a regression (the context matters: a Goblet Squat is a regression of a
  Back Squat; a Back Squat isn't always a "progression of" a goblet
  squat for every lifter). Callers that need inverses should query both
  directions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
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

if TYPE_CHECKING:  # pragma: no cover - type-check only imports
    pass


# ---------- Mixins ----------------------------------------------------------


class TimestampMixin:
    """created_at / updated_at columns, server-managed."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------- Core aggregate --------------------------------------------------


class Exercise(Base, TimestampMixin):
    """A single, canonical strength-training exercise — the aggregate root.

    This is the central entity of the exercise taxonomy. Every exercise has a
    unique ``primary_name`` (e.g. "Barbell Bench Press") and a URL-safe
    ``slug`` derived from it.  All supporting data — aliases, muscle-group
    mappings, equipment associations, movement descriptors, and related-
    exercise links — hang off this row via child tables.

    Key relationships
    -----------------
    * **aliases** — Alternate names a user might type ("DB bench",
      "dumbell press", common abbreviations and typos). Used for fast
      exact/prefix-match lookup *before* falling back to the vector DB.
    * **muscle_groups** — Which muscles the exercise trains, annotated
      with ``is_primary``.  Indexed for the "filter by body part" query.
    * **equipment** — Required equipment  (barbell, cable, bench …).
    * **movement_descriptors** — The most critical child table from a RAG
      perspective.  Each row is an independently-embeddable text chunk.
      Descriptors categorised as ``BEGINNER_DESCRIPTION`` are the primary
      retrieval corpus: they capture how a *total novice* would describe the
      movement without knowing its name, which is exactly the kind of query
      the MVP must match against.  See :class:`MovementDescriptor` for the
      full rationale.
    * **alternatives_from / alternatives_to** — Directional links between
      exercises (progressions, regressions, substitutes, variations).
    """

    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Canonical identity
    primary_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)

    # High-level classification
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SqlEnum(DifficultyLevel, name="difficulty_level"), nullable=False
    )
    mechanic: Mapped[MechanicType] = mapped_column(
        SqlEnum(MechanicType, name="mechanic_type"), nullable=False
    )
    force_type: Mapped[ForceType] = mapped_column(
        SqlEnum(ForceType, name="force_type"), nullable=False
    )
    movement_pattern: Mapped[MovementPattern] = mapped_column(
        SqlEnum(MovementPattern, name="movement_pattern"), nullable=False
    )

    # Free-text overview. Fine-grained text (setup, cues, mistakes) lives
    # in MovementDescriptor rows so it can be embedded individually.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Convenience flag for cheap "is this bilateral" filtering without
    # needing to parse descriptors.
    is_unilateral: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- Relationships ----------------------------------------------------

    aliases: Mapped[list["ExerciseAlias"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    movement_descriptors: Mapped[list["MovementDescriptor"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    muscle_groups: Mapped[list["ExerciseMuscleGroup"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    equipment: Mapped[list["ExerciseEquipment"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Self-referential alternatives. `foreign_keys` is required because
    # ExerciseAlternative has two FKs back to this table.
    alternatives_from: Mapped[list["ExerciseAlternative"]] = relationship(
        back_populates="exercise",
        foreign_keys="ExerciseAlternative.exercise_id",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alternatives_to: Mapped[list["ExerciseAlternative"]] = relationship(
        back_populates="related",
        foreign_keys="ExerciseAlternative.related_id",
        lazy="selectin",
    )

    # --- Convenience accessors -------------------------------------------

    @property
    def primary_muscles(self) -> list[MuscleGroup]:
        return [m.muscle_group for m in self.muscle_groups if m.is_primary]

    @property
    def secondary_muscles(self) -> list[MuscleGroup]:
        return [m.muscle_group for m in self.muscle_groups if not m.is_primary]

    @property
    def equipment_required(self) -> list[EquipmentType]:
        return [e.equipment_type for e in self.equipment]

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Exercise id={self.id} name={self.primary_name!r}>"


# ---------- Child tables ----------------------------------------------------


class ExerciseAlias(Base):
    """Alternate names or common misspellings a user might type for an exercise.

    Examples: 'DB bench', 'dumbell press', 'flat bench', 'bench press flat'.

    Purpose in the retrieval pipeline
    ---------------------------------
    Before invoking the (comparatively expensive) vector-similarity search
    against ``MovementDescriptor`` embeddings, the API layer does a fast
    exact / prefix-match lookup against this table.  If a user's input
    matches a known alias, we can short-circuit the embedding call entirely
    and return the canonical exercise immediately.

    A lower-cased functional index (``ix_exercise_aliases_alias_lower``)
    makes case-insensitive prefix queries efficient.
    """

    __tablename__ = "exercise_aliases"
    __table_args__ = (
        UniqueConstraint("exercise_id", "alias", name="uq_exercise_alias"),
        # `column("alias")` is resolved against this table at bind time —
        # needed because SQLAlchemy otherwise treats the bare string as a
        # SQL string literal, giving `lower('alias')` which indexes a
        # constant.
        Index("ix_exercise_aliases_alias_lower", func.lower(column("alias"))),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(128), nullable=False)
    # Optional: locale, source — add if/when we need them.

    exercise: Mapped["Exercise"] = relationship(back_populates="aliases")


class MovementDescriptor(Base, TimestampMixin):
    """A single, independently-embeddable text chunk describing an exercise.

    This table is the **heart of the RAG retrieval pipeline**.  Each row is
    one piece of descriptive text — a setup cue, an execution note, or,
    most importantly, a **beginner_description**.

    Why ``beginner_descriptions`` exist
    ------------------------------------
    The core problem the MVP solves is: *"a user describes a movement in
    their own words — what exercise is it?"*  Beginners rarely know the
    canonical name ("Barbell Bench Press"); instead they say things like
    "I lie on a bench and push a bar up from my chest".  To bridge this
    vocabulary gap we generate 4 distinct novice-voice descriptions per
    exercise during data ingestion (via ``generate_exercise_dataset.py``
    and a local Ollama model).  Each description deliberately avoids
    the exercise name and technical jargon.

    These 4 descriptions become ``MovementDescriptor`` rows with
    ``category = DescriptorCategory.BEGINNER_DESCRIPTION``.  A background
    worker (not yet built) will:

    1. Read rows where ``vector_id IS NULL OR needs_reindex = True``.
    2. Embed the ``text`` field using the configured embedding model.
    3. Upsert the resulting vector into the vector store (Pinecone/Milvus).
    4. Write back the ``vector_id`` and ``embedding_model`` version.

    At query time the user's natural-language input is embedded with the
    same model and nearest-neighbour search retrieves the closest
    ``MovementDescriptor`` rows, whose ``exercise_id`` tells us the
    canonical exercise.

    Vector DB coupling surface
    --------------------------
    ``vector_id`` and ``embedding_model`` are the **only** points of
    coupling between the relational store and the vector store.  The ORM
    layer never calls the vector store directly — all sync is owned by the
    background embedding worker.
    """

    __tablename__ = "movement_descriptors"
    __table_args__ = (
        Index("ix_movement_descriptors_exercise_category", "exercise_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[DescriptorCategory] = mapped_column(
        SqlEnum(DescriptorCategory, name="descriptor_category"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Vector DB hooks. The ORM layer never calls the vector store —
    # a worker owns that. These fields are its bookkeeping surface.
    vector_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    needs_reindex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    exercise: Mapped["Exercise"] = relationship(back_populates="movement_descriptors")


class ExerciseMuscleGroup(Base):
    """Association table mapping exercises to the muscle groups they train.

    Each row records one ``(exercise, muscle_group, is_primary)`` triple.
    Using a single table with an ``is_primary`` flag (rather than separate
    primary/secondary tables) keeps writes simple and the flag is indexed
    for efficient "filter by body part" queries on the API.
    """

    __tablename__ = "exercise_muscle_groups"
    __table_args__ = (
        UniqueConstraint("exercise_id", "muscle_group", name="uq_exercise_muscle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    muscle_group: Mapped[MuscleGroup] = mapped_column(
        SqlEnum(MuscleGroup, name="muscle_group"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    exercise: Mapped["Exercise"] = relationship(back_populates="muscle_groups")


class ExerciseEquipment(Base):
    """Association table mapping exercises to required equipment.

    A single exercise can require multiple pieces of equipment (e.g. a
    barbell *and* a bench for Barbell Bench Press).  This table is the
    source of truth for the "I only have dumbbells — what can I do?"
    filter query.
    """

    __tablename__ = "exercise_equipment"
    __table_args__ = (
        UniqueConstraint("exercise_id", "equipment_type", name="uq_exercise_equipment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_type: Mapped[EquipmentType] = mapped_column(
        SqlEnum(EquipmentType, name="equipment_type"), nullable=False, index=True
    )

    exercise: Mapped["Exercise"] = relationship(back_populates="equipment")


class ExerciseAlternative(Base):
    """Directional link between two exercises expressing a training relationship.

    Read as: ``exercise`` **is** ``relationship_type`` **of** ``related``.
    Example: ``(Goblet Squat, REGRESSION_OF, Back Squat)`` means "Goblet
    Squat is a regression of Back Squat".

    Inverse links are **not** auto-inserted — a progression isn't always the
    mirror of a regression (context matters). Callers that need bidirectional
    queries should search both ``alternatives_from`` and ``alternatives_to``.
    """

    __tablename__ = "exercise_alternatives"
    __table_args__ = (
        UniqueConstraint(
            "exercise_id", "related_id", "relationship_type",
            name="uq_exercise_alt",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    related_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[AlternativeRelationship] = mapped_column(
        SqlEnum(AlternativeRelationship, name="alternative_relationship"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    exercise: Mapped["Exercise"] = relationship(
        foreign_keys=[exercise_id],
        back_populates="alternatives_from",
    )
    related: Mapped["Exercise"] = relationship(
        foreign_keys=[related_id],
        back_populates="alternatives_to",
    )

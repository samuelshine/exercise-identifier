import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
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


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    primary_name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    difficulty: Mapped[DifficultyLevel]
    mechanic: Mapped[MechanicType]
    force_type: Mapped[ForceType]
    movement_pattern: Mapped[MovementPattern]
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    is_unilateral: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    aliases: Mapped[list["ExerciseAlias"]] = relationship(back_populates="exercise", cascade="all, delete-orphan", lazy="selectin")
    movement_descriptors: Mapped[list["MovementDescriptor"]] = relationship(back_populates="exercise", cascade="all, delete-orphan", lazy="selectin")
    muscle_groups: Mapped[list["ExerciseMuscleGroup"]] = relationship(back_populates="exercise", cascade="all, delete-orphan", lazy="selectin")
    equipment: Mapped[list["ExerciseEquipment"]] = relationship(back_populates="exercise", cascade="all, delete-orphan", lazy="selectin")
    alternatives_from: Mapped[list["ExerciseAlternative"]] = relationship(foreign_keys="ExerciseAlternative.exercise_id", back_populates="exercise", cascade="all, delete-orphan", lazy="selectin")
    alternatives_to: Mapped[list["ExerciseAlternative"]] = relationship(foreign_keys="ExerciseAlternative.related_id", back_populates="related", cascade="all, delete-orphan", lazy="selectin")

    @property
    def primary_muscles(self) -> list[MuscleGroup]:
        return [mg.muscle_group for mg in self.muscle_groups if mg.is_primary]

    @property
    def secondary_muscles(self) -> list[MuscleGroup]:
        return [mg.muscle_group for mg in self.muscle_groups if not mg.is_primary]

    @property
    def equipment_required(self) -> list[EquipmentType]:
        return [eq.equipment_type for eq in self.equipment]


class ExerciseAlias(Base):
    __tablename__ = "exercise_aliases"
    __table_args__ = (
        Index("ix_alias_lower", func.lower("alias")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(128))

    exercise: Mapped["Exercise"] = relationship(back_populates="aliases")


class MovementDescriptor(Base):
    __tablename__ = "movement_descriptors"
    __table_args__ = (
        Index("ix_descriptor_exercise_category", "exercise_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    category: Mapped[DescriptorCategory]
    text: Mapped[str] = mapped_column(Text)
    vector_id: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    embedding_model: Mapped[str | None] = mapped_column(String(64), default=None)
    needs_reindex: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    exercise: Mapped["Exercise"] = relationship(back_populates="movement_descriptors")


class ExerciseMuscleGroup(Base):
    __tablename__ = "exercise_muscle_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    muscle_group: Mapped[MuscleGroup] = mapped_column(index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    exercise: Mapped["Exercise"] = relationship(back_populates="muscle_groups")


class ExerciseEquipment(Base):
    __tablename__ = "exercise_equipment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    equipment_type: Mapped[EquipmentType] = mapped_column(index=True)

    exercise: Mapped["Exercise"] = relationship(back_populates="equipment")


class ExerciseAlternative(Base):
    __tablename__ = "exercise_alternatives"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    related_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    relationship_type: Mapped[AlternativeRelationship]
    note: Mapped[str | None] = mapped_column(Text, default=None)

    exercise: Mapped["Exercise"] = relationship(foreign_keys=[exercise_id], back_populates="alternatives_from")
    related: Mapped["Exercise"] = relationship(foreign_keys=[related_id], back_populates="alternatives_to")

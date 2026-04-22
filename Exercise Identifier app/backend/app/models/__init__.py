"""SQLAlchemy ORM models for the exercise taxonomy.

Re-exported here so callers can `from app.models import Exercise, ...`
without reaching into submodules. Import order matters: enums first,
then Exercise (which references everything via strings to avoid cycles).
"""

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
from app.models.exercise import (
    Exercise,
    ExerciseAlias,
    ExerciseAlternative,
    ExerciseEquipment,
    ExerciseMuscleGroup,
    MovementDescriptor,
)

__all__ = [
    # Enums
    "AlternativeRelationship",
    "DescriptorCategory",
    "DifficultyLevel",
    "EquipmentType",
    "ForceType",
    "MechanicType",
    "MovementPattern",
    "MuscleGroup",
    # ORM
    "Exercise",
    "ExerciseAlias",
    "ExerciseAlternative",
    "ExerciseEquipment",
    "ExerciseMuscleGroup",
    "MovementDescriptor",
]

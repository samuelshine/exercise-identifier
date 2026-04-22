"""Shared taxonomy enums.

Single source of truth for values that appear in both the ORM layer
(as PostgreSQL ENUM types) and Pydantic schemas (as response fields).
Defining them here avoids drift between "what the DB accepts" and
"what the API returns."

Guideline: values here are strictly for *gym strength training*.
Resist adding yoga poses, cardio modalities, etc. — those belong in a
separate taxonomy if they ever become in-scope.
"""

from __future__ import annotations

from enum import Enum


class DifficultyLevel(str, Enum):
    """Coarse skill rating. Intentionally only four buckets — finer grading
    is a UX trap for an MVP (users can't self-assess past four tiers)."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"


class MuscleGroup(str, Enum):
    """Major muscle groups relevant to resistance training."""

    # Upper body — push
    CHEST = "chest"
    FRONT_DELT = "front_delt"
    SIDE_DELT = "side_delt"
    REAR_DELT = "rear_delt"
    TRICEPS = "triceps"

    # Upper body — pull
    LATS = "lats"
    UPPER_BACK = "upper_back"  # rhomboids / mid-traps
    TRAPS = "traps"
    BICEPS = "biceps"
    FOREARMS = "forearms"

    # Core
    CORE = "core"  # catch-all when the LLM can't pick a specific core muscle
    ABS = "abs"
    OBLIQUES = "obliques"
    LOWER_BACK = "lower_back"  # erector spinae

    # Lower body
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    ADDUCTORS = "adductors"
    ABDUCTORS = "abductors"
    CALVES = "calves"
    HIP_FLEXORS = "hip_flexors"


class EquipmentType(str, Enum):
    """Equipment options. A single exercise can need several (barbell + bench)."""

    BARBELL = "barbell"
    DUMBBELL = "dumbbell"
    KETTLEBELL = "kettlebell"
    EZ_CURL_BAR = "ez_curl_bar"
    TRAP_BAR = "trap_bar"
    CABLE = "cable"
    MACHINE = "machine"
    SMITH_MACHINE = "smith_machine"
    BENCH = "bench"
    INCLINE_BENCH = "incline_bench"
    DECLINE_BENCH = "decline_bench"
    SQUAT_RACK = "squat_rack"
    PULL_UP_BAR = "pull_up_bar"
    DIP_BARS = "dip_bars"
    PREACHER_BENCH = "preacher_bench"
    RESISTANCE_BAND = "resistance_band"
    MEDICINE_BALL = "medicine_ball"
    WEIGHT_PLATE = "weight_plate"
    LANDMINE = "landmine"
    BODYWEIGHT = "bodyweight"


class MovementPattern(str, Enum):
    """Biomechanical movement pattern. Useful both as a search facet
    and as a downstream taxonomy input to pose-estimation classifiers."""

    HORIZONTAL_PUSH = "horizontal_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PUSH = "vertical_push"
    VERTICAL_PULL = "vertical_pull"
    SQUAT = "squat"
    HINGE = "hinge"
    LUNGE = "lunge"
    CARRY = "carry"
    ROTATION = "rotation"
    ANTI_ROTATION = "anti_rotation"
    ISOLATION = "isolation"


class MechanicType(str, Enum):
    """Compound (multi-joint) vs. isolation (single-joint)."""

    COMPOUND = "compound"
    ISOLATION = "isolation"


class ForceType(str, Enum):
    """Primary force vector — used by the video pipeline to narrow candidates.

    Extended beyond the original push/pull/static/hinge set because the
    local LLM (correctly) identifies squat, lunge, and rotational patterns
    as biomechanically distinct force profiles."""

    PUSH = "push"
    PULL = "pull"
    STATIC = "static"
    HINGE = "hinge"
    SQUAT = "squat"
    LUNGE = "lunge"
    ROTATION = "rotation"
    ANTI_ROTATION = "anti_rotation"


class DescriptorCategory(str, Enum):
    """Type of a MovementDescriptor row.

    These categories intentionally mirror coaching vocabulary so that
    LLM prompt templates can slot them in directly (e.g. "given the
    following SETUP descriptors, ...")."""

    SUMMARY = "summary"
    SETUP = "setup"
    EXECUTION = "execution"
    CUE = "cue"
    COMMON_MISTAKE = "common_mistake"
    VARIATION_NOTE = "variation_note"
    # Novice-voice descriptions of what the movement looks/feels like without
    # the name. Primary corpus for the text-to-exercise RAG retriever:
    # these match against what a beginner is likely to type.
    BEGINNER_DESCRIPTION = "beginner_description"


class AlternativeRelationship(str, Enum):
    """How a related exercise is related. Directional —
    `(A, progression_of, B)` means A is a progression of B."""

    PROGRESSION_OF = "progression_of"
    REGRESSION_OF = "regression_of"
    SUBSTITUTE_FOR = "substitute_for"
    VARIATION_OF = "variation_of"

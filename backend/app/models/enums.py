from enum import Enum


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"


class MuscleGroup(str, Enum):
    CHEST = "chest"
    FRONT_DELT = "front_delt"
    SIDE_DELT = "side_delt"
    REAR_DELT = "rear_delt"
    TRICEPS = "triceps"
    LATS = "lats"
    UPPER_BACK = "upper_back"
    TRAPS = "traps"
    BICEPS = "biceps"
    FOREARMS = "forearms"
    CORE = "core"
    ABS = "abs"
    OBLIQUES = "obliques"
    LOWER_BACK = "lower_back"
    QUADS = "quads"
    HAMSTRINGS = "hamstrings"
    GLUTES = "glutes"
    ADDUCTORS = "adductors"
    ABDUCTORS = "abductors"
    CALVES = "calves"
    HIP_FLEXORS = "hip_flexors"


class EquipmentType(str, Enum):
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
    COMPOUND = "compound"
    ISOLATION = "isolation"


class ForceType(str, Enum):
    PUSH = "push"
    PULL = "pull"
    STATIC = "static"
    HINGE = "hinge"
    SQUAT = "squat"
    LUNGE = "lunge"
    ROTATION = "rotation"
    ANTI_ROTATION = "anti_rotation"


class DescriptorCategory(str, Enum):
    SUMMARY = "summary"
    SETUP = "setup"
    EXECUTION = "execution"
    CUE = "cue"
    COMMON_MISTAKE = "common_mistake"
    VARIATION_NOTE = "variation_note"
    BEGINNER_DESCRIPTION = "beginner_description"


class AlternativeRelationship(str, Enum):
    PROGRESSION_OF = "progression_of"
    REGRESSION_OF = "regression_of"
    SUBSTITUTE_FOR = "substitute_for"
    VARIATION_OF = "variation_of"

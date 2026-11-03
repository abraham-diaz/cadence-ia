from dataclasses import asdict

from pydantic import BaseModel, ConfigDict, Field

from cadence_ia.api.schemas.common import WorkoutTypeRef
from cadence_ia.api.schemas.exercises import (
    CatalogExerciseOut,
    MuscleOut,
    catalog_exercise_out,
    muscle_out,
)
from cadence_ia.domain.exercise import Muscle, MuscleSuggestion
from cadence_ia.domain.workout_type import Category, WorkoutTypeUsage


class WorkoutTypeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=60)
    category: Category
    muscles: list[Muscle] = []


class WorkoutTypeOut(WorkoutTypeRef):
    session_count: int
    muscles: list[Muscle]


class MuscleSuggestionOut(BaseModel):
    muscle: MuscleOut
    exercises: list[CatalogExerciseOut]


def workout_type_out(usage: WorkoutTypeUsage) -> WorkoutTypeOut:
    return WorkoutTypeOut(
        **asdict(usage.workout_type), session_count=usage.session_count, muscles=list(usage.muscles)
    )


def muscle_suggestion_out(suggestion: MuscleSuggestion) -> MuscleSuggestionOut:
    return MuscleSuggestionOut(
        muscle=muscle_out(suggestion.muscle),
        exercises=[catalog_exercise_out(e) for e in suggestion.exercises],
    )

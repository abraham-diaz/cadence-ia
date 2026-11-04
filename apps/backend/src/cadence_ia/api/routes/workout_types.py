from datetime import date

from fastapi import APIRouter

from cadence_ia.api.deps import Database
from cadence_ia.api.errors import error_responses
from cadence_ia.api.schemas.workout_types import (
    MuscleSuggestionOut,
    WorkoutTypeIn,
    WorkoutTypeOut,
    workout_type_out,
)
from cadence_ia.services import exercises, workout_types

router = APIRouter(prefix="/api/workout-types", tags=["workout types"])

@router.get("")
def list_workout_types(conn: Database) -> list[WorkoutTypeOut]:
    return [workout_type_out(usage) for usage in workout_types.list_types(conn)]


@router.post("", status_code=201, responses=error_responses(409))
def create_workout_type(body: WorkoutTypeIn, conn: Database) -> WorkoutTypeOut:
    return workout_type_out(
        workout_types.create_type(conn, body.name, body.category, tuple(body.muscles))
    )


@router.put("/{type_id}", responses=error_responses(404, 409))
def update_workout_type(type_id: int, body: WorkoutTypeIn, conn: Database) -> WorkoutTypeOut:
    return workout_type_out(
        workout_types.update_type(conn, type_id, body.name, body.category, tuple(body.muscles))
    )


@router.delete("/{type_id}", status_code=204, responses=error_responses(404))
def delete_workout_type(type_id: int, conn: Database) -> None:
    workout_types.delete_type(conn, type_id)


@router.get("/{type_id}/exercises", responses=error_responses(404))
def suggest_exercises(
    type_id: int, conn: Database, day: date | None = None
) -> list[MuscleSuggestionOut]:
    """A few catalog exercises per muscle of the type; `day` (default today) picks which."""
    suggestions = exercises.suggestions_for_type(conn, type_id, day)
    return [MuscleSuggestionOut.model_validate(s) for s in suggestions]

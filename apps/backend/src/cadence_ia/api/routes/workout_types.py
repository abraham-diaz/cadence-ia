from fastapi import APIRouter, Response

from cadence_ia.api.deps import Database
from datetime import date

from cadence_ia.api.schemas import (
    ErrorOut,
    MuscleSuggestionOut,
    WorkoutTypeIn,
    WorkoutTypeOut,
    muscle_suggestion_out,
    workout_type_out,
)
from cadence_ia.services import exercises, workout_types

router = APIRouter(prefix="/api/workout-types", tags=["workout types"])

NOT_FOUND = {404: {"model": ErrorOut}}
DUPLICATE = {409: {"model": ErrorOut}}


@router.get("")
def list_workout_types(conn: Database) -> list[WorkoutTypeOut]:
    return [workout_type_out(usage) for usage in workout_types.list_types(conn)]


@router.post("", status_code=201, responses=DUPLICATE)
def create_workout_type(body: WorkoutTypeIn, conn: Database) -> WorkoutTypeOut:
    return workout_type_out(
        workout_types.create_type(conn, body.name, body.category, tuple(body.muscles))
    )


@router.put("/{type_id}", responses={**NOT_FOUND, **DUPLICATE})
def update_workout_type(type_id: int, body: WorkoutTypeIn, conn: Database) -> WorkoutTypeOut:
    return workout_type_out(
        workout_types.update_type(conn, type_id, body.name, body.category, tuple(body.muscles))
    )


@router.delete("/{type_id}", status_code=204, responses=NOT_FOUND)
def delete_workout_type(type_id: int, conn: Database) -> Response:
    workout_types.delete_type(conn, type_id)
    return Response(status_code=204)


@router.get("/{type_id}/exercises", responses=NOT_FOUND)
def suggest_exercises(
    type_id: int, conn: Database, day: date | None = None
) -> list[MuscleSuggestionOut]:
    """A few catalog exercises per muscle of the type; `day` (default today) picks which."""
    suggestions = exercises.suggestions_for_type(conn, type_id, day or date.today())
    return [muscle_suggestion_out(s) for s in suggestions]

from fastapi import APIRouter, Query

from cadence_ia.api.deps import Database
from cadence_ia.api.schemas import (
    CatalogExerciseOut,
    ErrorOut,
    ExerciseDetailOut,
    catalog_exercise_out,
    exercise_detail_out,
)
from cadence_ia.services import exercises

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
def search_exercises(conn: Database, q: str = Query(max_length=80)) -> list[CatalogExerciseOut]:
    """Catalog exercises whose name has every word of `q`, ignoring accents."""
    return [catalog_exercise_out(e) for e in exercises.search_catalog(conn, q)]


@router.get("/{exercise_id}", responses={404: {"model": ErrorOut}})
def get_exercise(exercise_id: int, conn: Database) -> ExerciseDetailOut:
    """How to do it: picture, instructions and the muscles it trains."""
    return exercise_detail_out(exercises.get_exercise(conn, exercise_id))

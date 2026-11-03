from fastapi import APIRouter, Query

from cadence_ia.api.deps import Database
from cadence_ia.api.schemas.common import ErrorOut
from cadence_ia.api.schemas.exercises import CatalogExerciseOut, ExerciseDetailOut
from cadence_ia.services import exercises

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("")
def search_exercises(conn: Database, q: str = Query(max_length=80)) -> list[CatalogExerciseOut]:
    """Catalog exercises whose name has every word of `q`, ignoring accents."""
    return [CatalogExerciseOut.model_validate(e) for e in exercises.search_catalog(conn, q)]


@router.get("/{exercise_id}", responses={404: {"model": ErrorOut}})
def get_exercise(exercise_id: int, conn: Database) -> ExerciseDetailOut:
    """How to do it: picture, instructions and the muscles it trains."""
    return ExerciseDetailOut.model_validate(exercises.get_exercise(conn, exercise_id))

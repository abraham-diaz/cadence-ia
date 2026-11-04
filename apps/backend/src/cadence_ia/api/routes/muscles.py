from fastapi import APIRouter

from cadence_ia.api.schemas.exercises import MuscleOut
from cadence_ia.domain.exercise import MUSCLE_NAMES

router = APIRouter(prefix="/api/muscles", tags=["exercises"])


@router.get("")
def list_muscles() -> list[MuscleOut]:
    """The muscle groups a workout type can train, in display order."""
    return [MuscleOut.model_validate(muscle) for muscle in MUSCLE_NAMES]

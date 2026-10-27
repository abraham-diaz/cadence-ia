from fastapi import APIRouter

from cadence_ia.api.schemas import MuscleOut, muscle_out
from cadence_ia.domain.exercise import MUSCLE_NAMES

router = APIRouter(prefix="/api/muscles", tags=["exercises"])


@router.get("")
def list_muscles() -> list[MuscleOut]:
    """The muscle groups a workout type can train, in display order."""
    return [muscle_out(muscle) for muscle in MUSCLE_NAMES]

from typing import Any

from pydantic import model_validator

from cadence_ia.api.schemas.common import OutModel
from cadence_ia.domain.exercise import MUSCLE_NAMES, Muscle


class MuscleOut(OutModel):
    id: Muscle
    name: str

    @model_validator(mode="before")
    @classmethod
    def from_muscle_id(cls, data: Any) -> Any:
        return {"id": data, "name": MUSCLE_NAMES[data]} if isinstance(data, str) else data


class CatalogExerciseOut(OutModel):
    id: int
    name: str
    image_url: str | None
    license: str
    author: str | None


class ExerciseDetailOut(CatalogExerciseOut):
    description: str | None  # one paragraph per line
    primary_muscles: list[MuscleOut]
    secondary_muscles: list[MuscleOut]

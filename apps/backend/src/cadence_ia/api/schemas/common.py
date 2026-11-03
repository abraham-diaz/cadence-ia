from pydantic import BaseModel, ConfigDict

from cadence_ia.domain.workout_type import Category
from cadence_ia.services.errors import ErrorCode


class OutModel(BaseModel):
    """Response model: `model_validate` reads it from a domain object of the same shape."""

    model_config = ConfigDict(from_attributes=True)


class ErrorOut(OutModel):
    detail: str
    code: ErrorCode  # stable: the frontend shows a message for each code


class WorkoutTypeRef(OutModel):
    id: int
    name: str
    category: Category

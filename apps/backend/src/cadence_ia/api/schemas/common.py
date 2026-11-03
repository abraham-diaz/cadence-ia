from pydantic import BaseModel

from cadence_ia.domain.workout_type import Category
from cadence_ia.services.errors import ErrorCode


class ErrorOut(BaseModel):
    detail: str
    code: ErrorCode  # stable: the frontend shows a message for each code


class WorkoutTypeRef(BaseModel):
    id: int
    name: str
    category: Category

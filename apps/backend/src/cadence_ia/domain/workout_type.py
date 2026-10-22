"""Workout types created by the user ("Pierna", "Caminata"...)."""

from dataclasses import dataclass
from typing import Literal

Category = Literal["strength", "cardio"]


@dataclass(frozen=True)
class WorkoutType:
    id: int
    name: str
    category: Category

    @property
    def is_strength(self) -> bool:
        return self.category == "strength"


@dataclass(frozen=True)
class WorkoutTypeUsage:
    """A workout type and how many sessions have it."""

    workout_type: WorkoutType
    session_count: int

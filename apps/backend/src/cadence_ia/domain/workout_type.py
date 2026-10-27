from dataclasses import dataclass
from typing import Literal

from cadence_ia.domain.exercise import Muscle

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
    """A workout type, the muscles it trains and how many sessions have it."""

    workout_type: WorkoutType
    session_count: int
    muscles: tuple[Muscle, ...] = ()

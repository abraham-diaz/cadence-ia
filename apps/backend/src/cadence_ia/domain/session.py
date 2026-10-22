"""A workout once it has been analyzed and stored."""

from dataclasses import dataclass
from datetime import datetime

from cadence_ia.domain.workout_type import WorkoutType


@dataclass(frozen=True)
class Session:
    id: str  # TCX file name without extension
    start_time: datetime
    sport: str
    device: str | None
    duration_s: int
    calories: int
    hr_min: int
    hr_avg: int
    hr_max: int
    threshold_bpm: float
    # None when hidden: they only mean something in strength sessions.
    sets: int | None
    rests: int | None
    workout_type: WorkoutType | None

    @property
    def is_strength(self) -> bool:
        return self.workout_type is not None and self.workout_type.is_strength

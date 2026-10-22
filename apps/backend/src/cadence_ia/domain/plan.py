"""A training plan: one or more weeks that repeat in turn (week A, week B...)."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from cadence_ia.domain.workout_type import WorkoutType


@dataclass(frozen=True)
class Exercise:
    name: str
    sets: int | None
    reps: str | None  # text: "10-12", "30 s"...


@dataclass(frozen=True)
class PlanDay:
    week: int  # 0 = the first week of the cycle
    weekday: int  # 0 = Monday
    workout_type: WorkoutType | None  # None if the type was deleted afterwards
    minutes: int
    note: str | None
    exercises: tuple[Exercise, ...]


@dataclass(frozen=True)
class Plan:
    id: int
    title: str
    weeks: int
    cycle_start: date  # the Monday the first week starts
    created_at: datetime
    days: tuple[PlanDay, ...]

    def week_on(self, day: date) -> int:
        return ((day - self.cycle_start).days // 7) % self.weeks


def cycle_start(today: date, current_week: int) -> date:
    """The Monday the cycle started, given which week of it is the current one."""
    monday = today - timedelta(days=today.weekday())
    return monday - timedelta(weeks=current_week)

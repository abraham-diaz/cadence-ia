import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from cadence_ia.domain.exercise import Muscle
from cadence_ia.domain.plan import Exercise, Plan, PlanDay, cycle_start, link_to_catalog
from cadence_ia.domain.week_progress import WeekProgress, week_progress
from cadence_ia.domain.workout_type import Category, WorkoutType
from cadence_ia.services.errors import InvalidInput
from cadence_ia.storage import exercises, plans, sessions, workout_types


@dataclass(frozen=True)
class NewType:
    name: str
    category: Category
    muscles: tuple[Muscle, ...] = ()


@dataclass(frozen=True)
class DayInput:
    week: int
    weekday: int
    workout_type: int | NewType
    minutes: int
    note: str | None
    exercises: tuple[Exercise, ...]


@dataclass(frozen=True)
class CurrentPlan:
    plan: Plan
    week: int  # the week of the cycle we are in today


def save(
    conn: sqlite3.Connection,
    title: str,
    weeks: int,
    current_week: int,
    days: Sequence[DayInput],
    today: date | None = None,
) -> CurrentPlan:
    """Store the plan as the active one, creating the new workout types it uses."""
    if not 0 <= current_week < weeks or any(not 0 <= d.week < weeks for d in days):
        raise InvalidInput("invalid_plan", "Week numbers must be below the number of weeks")
    for day in days:
        if isinstance(day.workout_type, int) and not workout_types.get_type(conn, day.workout_type):
            raise InvalidInput("workout_type_not_found", "Workout type not found")

    # Checked everything first: a bad request doesn't leave new types behind.
    resolved: dict[str, WorkoutType] = {}
    catalog = exercises.list_all(conn) if any(d.exercises for d in days) else []
    plan_days = [
        PlanDay(
            week=day.week,
            weekday=day.weekday,
            workout_type=_resolve(conn, day.workout_type, resolved),
            minutes=day.minutes,
            note=day.note,
            exercises=link_to_catalog(day.exercises, catalog),
        )
        for day in days
    ]
    today = today or date.today()
    plans.save_plan(conn, title, weeks, cycle_start(today, current_week), plan_days)
    return get_current(conn, today)


def get_current(conn: sqlite3.Connection, today: date | None = None) -> CurrentPlan | None:
    plan = plans.get_active_plan(conn)
    if plan is None:
        return None
    return CurrentPlan(plan=plan, week=plan.week_on(today or date.today()))


def week(
    conn: sqlite3.Connection, start: date | None = None, today: date | None = None
) -> WeekProgress:
    """A week (this one by default), day by day, against the plan in force each day."""
    return week_progress(
        plans.list_plans(conn), sessions.list_sessions(conn), today or date.today(), start
    )


def _resolve(
    conn: sqlite3.Connection, choice: int | NewType, resolved: dict[str, WorkoutType]
) -> WorkoutType:
    """A new type whose name already exists reuses that type instead of failing."""
    if isinstance(choice, int):
        return workout_types.get_type(conn, choice).workout_type
    key = choice.name.casefold()
    if key not in resolved:
        existing = workout_types.find_by_name(conn, choice.name)
        if existing is None:
            type_id = workout_types.create_type(conn, choice.name, choice.category, choice.muscles)
            existing = workout_types.get_type(conn, type_id).workout_type
        resolved[key] = existing
    return resolved[key]

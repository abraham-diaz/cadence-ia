import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from cadence_ia.domain.plan import Exercise, Plan, PlanDay, cycle_start
from cadence_ia.domain.week_summary import week_summary
from cadence_ia.domain.workout_type import Category, WorkoutType
from cadence_ia.llm.coach import ChatMessage, Coach, build_context
from cadence_ia.llm.errors import LLMUnavailable
from cadence_ia.llm.planner import PlanExtractor
from cadence_ia.services.errors import Conflict, InvalidInput, Unavailable
from cadence_ia.storage import plans, sessions, workout_types


@dataclass(frozen=True)
class NewType:
    name: str
    category: Category


@dataclass(frozen=True)
class ProposedDay:
    week: int
    weekday: int
    type_name: str
    category: Category
    workout_type_id: int | None  # the user's type with that name; None if it's new
    minutes: int
    note: str | None
    exercises: tuple[Exercise, ...]


@dataclass(frozen=True)
class Proposal:
    """The plan read from the chat, for the user to review before saving."""

    title: str
    weeks: int
    days: list[ProposedDay]


@dataclass(frozen=True)
class DayInput:
    week: int
    weekday: int
    workout_type: int | NewType  # an existing type's id, or one to create
    minutes: int
    note: str | None
    exercises: tuple[Exercise, ...]


@dataclass(frozen=True)
class CurrentPlan:
    plan: Plan
    week: int  # the week of the cycle we are in today


def chat(
    conn: sqlite3.Connection, messages: list[ChatMessage], coach: Coach, today: date | None = None
) -> str:
    """The coach's reply to the conversation so far. Nothing is stored:
    the client keeps the conversation and sends it whole every time."""
    context = build_context(today or date.today(), workout_types.list_types(conn))
    try:
        return coach(context, messages)
    except LLMUnavailable as err:
        raise Unavailable("coach_unavailable", str(err)) from err


def last_week(conn: sqlite3.Connection, today: date | None = None) -> str:
    """The last 7 days as a message the user can edit and send to the coach."""
    return week_summary(sessions.list_sessions(conn), today or date.today())


def propose(
    conn: sqlite3.Connection, messages: list[ChatMessage], extractor: PlanExtractor
) -> Proposal:
    """Read the last plan agreed in the chat. Nothing is saved yet."""
    names = [usage.workout_type.name for usage in workout_types.list_types(conn)]
    try:
        draft = extractor(names, messages)
    except LLMUnavailable as err:
        raise Unavailable("coach_unavailable", str(err)) from err

    days = []
    for week, week_draft in enumerate(draft.weeks):
        for day in week_draft.days:
            if not 0 <= day.weekday <= 6:
                continue
            existing = workout_types.find_by_name(conn, day.workout_type.strip())
            days.append(
                ProposedDay(
                    week=week,
                    weekday=day.weekday,
                    type_name=existing.name if existing else day.workout_type.strip(),
                    category=existing.category if existing else _category(day.category),
                    workout_type_id=existing.id if existing else None,
                    minutes=max(1, day.minutes),
                    note=(day.note or "").strip() or None,
                    exercises=tuple(
                        Exercise(name=e.name.strip(), sets=e.sets, reps=e.reps)
                        for e in day.exercises
                        if e.name.strip()
                    ),
                )
            )
    if not days:
        raise Conflict("no_plan_in_chat", "No plan has been agreed in the chat yet")
    return Proposal(title=draft.title.strip(), weeks=max(1, len(draft.weeks)), days=days)


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
    plan_days = [
        PlanDay(
            week=day.week,
            weekday=day.weekday,
            workout_type=_resolve(conn, day.workout_type, resolved),
            minutes=day.minutes,
            note=day.note,
            exercises=day.exercises,
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


def _category(value: str) -> Category:
    return "cardio" if value.strip().lower() == "cardio" else "strength"


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
            type_id = workout_types.create_type(conn, choice.name, choice.category)
            existing = workout_types.get_type(conn, type_id).workout_type
        resolved[key] = existing
    return resolved[key]

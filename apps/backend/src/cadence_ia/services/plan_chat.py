import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date

from cadence_ia.domain.exercise import CatalogExercise
from cadence_ia.domain.plan import Exercise, link_to_catalog
from cadence_ia.domain.week_summary import week_summary
from cadence_ia.domain.workout_type import Category
from cadence_ia.llm.coach import ChatMessage, Coach, build_context
from cadence_ia.llm.errors import LLMUnavailable
from cadence_ia.llm.planner import DayDraft, PlanExtractor
from cadence_ia.services.errors import Conflict, Unavailable
from cadence_ia.storage import exercises, sessions, workout_types


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
    title: str
    weeks: int
    days: list[ProposedDay]


def chat(
    conn: sqlite3.Connection, messages: list[ChatMessage], coach: Coach, today: date | None = None
) -> str:
    """Nothing is stored: the client keeps the conversation and sends it whole every time."""
    context = build_context(today or date.today(), workout_types.list_types(conn))
    with _coach_errors():
        return coach(context, messages)


def last_week(conn: sqlite3.Connection, today: date | None = None) -> str:
    """The last 7 days as a message the user can edit and send to the coach."""
    return week_summary(sessions.list_sessions(conn), today or date.today())


def propose(
    conn: sqlite3.Connection, messages: list[ChatMessage], extractor: PlanExtractor
) -> Proposal:
    """Read the last plan agreed in the chat. Nothing is saved yet."""
    names = [usage.workout_type.name for usage in workout_types.list_types(conn)]
    with _coach_errors():
        draft = extractor(names, messages)

    catalog = exercises.list_all(conn)
    days = [
        _proposed_day(conn, catalog, week, day)
        for week, week_draft in enumerate(draft.weeks)
        for day in week_draft.days
        if 0 <= day.weekday <= 6
    ]
    if not days:
        raise Conflict("no_plan_in_chat", "No plan has been agreed in the chat yet")
    return Proposal(title=draft.title.strip(), weeks=max(1, len(draft.weeks)), days=days)


def _proposed_day(
    conn: sqlite3.Connection, catalog: list[CatalogExercise], week: int, day: DayDraft
) -> ProposedDay:
    name = day.workout_type.strip()
    existing = workout_types.find_by_name(conn, name)
    items = tuple(
        Exercise(name=e.name.strip(), sets=e.sets, reps=e.reps)
        for e in day.exercises
        if e.name.strip()
    )
    return ProposedDay(
        week=week,
        weekday=day.weekday,
        type_name=existing.name if existing else name,
        category=existing.category if existing else day.category,
        workout_type_id=existing.id if existing else None,
        minutes=max(1, day.minutes),
        note=(day.note or "").strip() or None,
        exercises=link_to_catalog(items, catalog),
    )


@contextmanager
def _coach_errors() -> Iterator[None]:
    try:
        yield
    except LLMUnavailable as err:
        raise Unavailable("coach_unavailable", str(err)) from err

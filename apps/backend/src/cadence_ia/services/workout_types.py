import sqlite3

from cadence_ia.domain.workout_type import Category, WorkoutTypeUsage
from cadence_ia.services.errors import Conflict, NotFound
from cadence_ia.storage import workout_types
from cadence_ia.storage.workout_types import DuplicateName


def _not_found() -> NotFound:
    return NotFound("workout_type_not_found", "Workout type not found")


def _duplicate(name: str) -> Conflict:
    return Conflict("duplicate_workout_type", f"A workout type named '{name}' already exists")


def list_types(conn: sqlite3.Connection) -> list[WorkoutTypeUsage]:
    """Every type, alphabetically, with how many sessions have it."""
    return workout_types.list_types(conn)


def get_type(conn: sqlite3.Connection, type_id: int) -> WorkoutTypeUsage:
    usage = workout_types.get_type(conn, type_id)
    if usage is None:
        raise _not_found()
    return usage


def create_type(conn: sqlite3.Connection, name: str, category: Category) -> WorkoutTypeUsage:
    try:
        type_id = workout_types.create_type(conn, name, category)
    except DuplicateName:
        raise _duplicate(name)
    return get_type(conn, type_id)


def update_type(
    conn: sqlite3.Connection, type_id: int, name: str, category: Category
) -> WorkoutTypeUsage:
    try:
        found = workout_types.update_type(conn, type_id, name, category)
    except DuplicateName:
        raise _duplicate(name)
    if not found:
        raise _not_found()
    return get_type(conn, type_id)


def delete_type(conn: sqlite3.Connection, type_id: int) -> None:
    """Delete a type. Its sessions go back to having no type."""
    if not workout_types.delete_type(conn, type_id):
        raise _not_found()

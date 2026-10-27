import sqlite3

from cadence_ia.domain.exercise import Muscle, sort_muscles
from cadence_ia.domain.workout_type import Category, WorkoutType, WorkoutTypeUsage

TYPE_QUERY = """
    SELECT t.id, t.name, t.category, COUNT(s.id) AS session_count,
        (SELECT GROUP_CONCAT(muscle) FROM workout_type_muscles WHERE workout_type_id = t.id) AS muscles
    FROM workout_types t LEFT JOIN sessions s ON s.workout_type_id = t.id
    WHERE {where}
    GROUP BY t.id
    ORDER BY t.name COLLATE NOCASE
"""


class DuplicateName(Exception):
    pass


def _usage(row: sqlite3.Row) -> WorkoutTypeUsage:
    return WorkoutTypeUsage(
        workout_type=WorkoutType(id=row["id"], name=row["name"], category=row["category"]),
        session_count=row["session_count"],
        muscles=sort_muscles(row["muscles"].split(",")) if row["muscles"] else (),
    )


def list_types(conn: sqlite3.Connection) -> list[WorkoutTypeUsage]:
    return [_usage(row) for row in conn.execute(TYPE_QUERY.format(where="1"))]


def get_type(conn: sqlite3.Connection, type_id: int) -> WorkoutTypeUsage | None:
    row = conn.execute(TYPE_QUERY.format(where="t.id = ?"), (type_id,)).fetchone()
    return _usage(row) if row else None


def _set_muscles(conn: sqlite3.Connection, type_id: int, muscles: tuple[Muscle, ...]) -> None:
    conn.execute("DELETE FROM workout_type_muscles WHERE workout_type_id = ?", (type_id,))
    conn.executemany(
        "INSERT INTO workout_type_muscles (workout_type_id, muscle) VALUES (?, ?)",
        [(type_id, muscle) for muscle in sort_muscles(muscles)],
    )


def create_type(
    conn: sqlite3.Connection, name: str, category: Category, muscles: tuple[Muscle, ...] = ()
) -> int:
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO workout_types (name, category) VALUES (?, ?)", (name, category)
            )
            _set_muscles(conn, cursor.lastrowid, muscles)
    except sqlite3.IntegrityError as err:
        raise DuplicateName(name) from err
    return cursor.lastrowid


def update_type(
    conn: sqlite3.Connection,
    type_id: int,
    name: str,
    category: Category,
    muscles: tuple[Muscle, ...] = (),
) -> bool:
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE workout_types SET name = ?, category = ? WHERE id = ?",
                (name, category, type_id),
            )
            if cursor.rowcount:
                _set_muscles(conn, type_id, muscles)
    except sqlite3.IntegrityError as err:
        raise DuplicateName(name) from err
    return cursor.rowcount > 0


def delete_type(conn: sqlite3.Connection, type_id: int) -> bool:
    """Delete a type. Its sessions go back to having no type."""
    with conn:
        cursor = conn.execute("DELETE FROM workout_types WHERE id = ?", (type_id,))
    return cursor.rowcount > 0


def find_by_name(conn: sqlite3.Connection, name: str) -> WorkoutType | None:
    """Case-insensitive, like the UNIQUE constraint on the name."""
    row = conn.execute(
        "SELECT id, name, category FROM workout_types WHERE name = ? COLLATE NOCASE", (name,)
    ).fetchone()
    return WorkoutType(id=row["id"], name=row["name"], category=row["category"]) if row else None

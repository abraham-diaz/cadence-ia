import sqlite3
from collections.abc import Sequence
from datetime import date, datetime, timezone

from cadence_ia.domain.plan import Exercise, Plan, PlanDay
from cadence_ia.domain.workout_type import WorkoutType


def save_plan(
    conn: sqlite3.Connection, title: str, weeks: int, cycle_start: date, days: Sequence[PlanDay]
) -> int:
    """Store a plan as the active one; the previous active plan is kept, inactive."""
    with conn:
        conn.execute("UPDATE plans SET active = 0 WHERE active = 1")
        plan_id = conn.execute(
            "INSERT INTO plans (title, weeks, cycle_start, created_at) VALUES (?, ?, ?, ?)",
            (
                title,
                weeks,
                cycle_start.isoformat(),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        ).lastrowid
        for day in days:
            day_id = conn.execute(
                """INSERT INTO plan_days (plan_id, week, weekday, workout_type_id, minutes, note)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    plan_id,
                    day.week,
                    day.weekday,
                    day.workout_type.id if day.workout_type else None,
                    day.minutes,
                    day.note,
                ),
            ).lastrowid
            conn.executemany(
                """INSERT INTO plan_exercises (plan_day_id, position, name, sets, reps, catalog_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (day_id, i, e.name, e.sets, e.reps, e.catalog_id)
                    for i, e in enumerate(day.exercises)
                ],
            )
    return plan_id


def get_active_plan(conn: sqlite3.Connection) -> Plan | None:
    row = conn.execute("SELECT * FROM plans WHERE active = 1").fetchone()
    return _plan(conn, row) if row else None


def list_plans(conn: sqlite3.Connection) -> list[Plan]:
    """Every version of the plan, oldest first: editing a plan keeps the old one."""
    rows = conn.execute("SELECT * FROM plans ORDER BY created_at, id").fetchall()
    return [_plan(conn, row) for row in rows]


def _plan(conn: sqlite3.Connection, row: sqlite3.Row) -> Plan:
    return Plan(
        id=row["id"],
        title=row["title"],
        weeks=row["weeks"],
        cycle_start=date.fromisoformat(row["cycle_start"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        days=_days(conn, row["id"]),
    )


def _days(conn: sqlite3.Connection, plan_id: int) -> tuple[PlanDay, ...]:
    rows = conn.execute(
        """SELECT d.id, d.week, d.weekday, d.minutes, d.note,
                  t.id AS type_id, t.name AS type_name, t.category AS type_category
           FROM plan_days d LEFT JOIN workout_types t ON t.id = d.workout_type_id
           WHERE d.plan_id = ?
           ORDER BY d.week, d.weekday, d.id""",
        (plan_id,),
    ).fetchall()
    exercises: dict[int, list[Exercise]] = {}
    for e in conn.execute(
        """SELECT e.plan_day_id, e.name, e.sets, e.reps, e.catalog_id, c.image_url
           FROM plan_exercises e JOIN plan_days d ON d.id = e.plan_day_id
           LEFT JOIN exercises c ON c.id = e.catalog_id
           WHERE d.plan_id = ?
           ORDER BY e.plan_day_id, e.position""",
        (plan_id,),
    ):
        exercises.setdefault(e["plan_day_id"], []).append(
            Exercise(
                name=e["name"],
                sets=e["sets"],
                reps=e["reps"],
                catalog_id=e["catalog_id"],
                image_url=e["image_url"],
            )
        )
    return tuple(
        PlanDay(
            week=row["week"],
            weekday=row["weekday"],
            workout_type=(
                WorkoutType(id=row["type_id"], name=row["type_name"], category=row["type_category"])
                if row["type_id"] is not None
                else None
            ),
            minutes=row["minutes"],
            note=row["note"],
            exercises=tuple(exercises.get(row["id"], [])),
        )
        for row in rows
    )


def unlinked_exercise_names(conn: sqlite3.Connection) -> list[str]:
    """Names of plan exercises not pointing to the catalog yet, in any plan version."""
    rows = conn.execute("SELECT DISTINCT name FROM plan_exercises WHERE catalog_id IS NULL")
    return [row["name"] for row in rows]


def link_exercises(conn: sqlite3.Connection, links: dict[str, int]) -> None:
    """Set the catalog entry of the unlinked plan exercises with these names."""
    with conn:
        conn.executemany(
            "UPDATE plan_exercises SET catalog_id = ? WHERE name = ? AND catalog_id IS NULL",
            [(catalog_id, name) for name, catalog_id in links.items()],
        )

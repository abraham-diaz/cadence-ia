import sqlite3
from collections import defaultdict

from cadence_ia.domain.exercise import CatalogExercise, Muscle, sort_muscles


def replace_catalog(conn: sqlite3.Connection, catalog: list[CatalogExercise]) -> None:
    """Store a fresh download: exercises keep their wger id, the ones gone from wger are removed."""
    with conn:
        conn.executemany(
            """
            INSERT INTO exercises (id, name_es, name_en, image_url, license, author, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                name_es = excluded.name_es, name_en = excluded.name_en,
                image_url = excluded.image_url, license = excluded.license,
                author = excluded.author, description = excluded.description
            """,
            [
                (e.id, e.name_es, e.name_en, e.image_url, e.license, e.author, e.description)
                for e in catalog
            ],
        )
        ids = [e.id for e in catalog]
        conn.execute(
            f"DELETE FROM exercises WHERE id NOT IN ({','.join('?' * len(ids))})", ids
        )
        conn.execute("DELETE FROM exercise_muscles")
        conn.executemany(
            "INSERT INTO exercise_muscles (exercise_id, muscle, is_primary) VALUES (?, ?, ?)",
            [(e.id, m, 1) for e in catalog for m in e.primary_muscles]
            + [(e.id, m, 0) for e in catalog for m in e.secondary_muscles],
        )


def count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]


def for_muscles(conn: sqlite3.Connection, muscles: tuple[Muscle, ...]) -> list[CatalogExercise]:
    """Exercises that train any of these muscles as their main one."""
    if not muscles:
        return []
    return _load(
        conn,
        f"""e.id IN (
            SELECT exercise_id FROM exercise_muscles
            WHERE is_primary = 1 AND muscle IN ({','.join('?' * len(muscles))})
        )""",
        muscles,
    )


def list_all(conn: sqlite3.Connection) -> list[CatalogExercise]:
    return _load(conn, "1", ())


def get(conn: sqlite3.Connection, exercise_id: int) -> CatalogExercise | None:
    found = _load(conn, "e.id = ?", (exercise_id,))
    return found[0] if found else None


def _load(conn: sqlite3.Connection, where: str, params: tuple) -> list[CatalogExercise]:
    rows = conn.execute(
        f"""
        SELECT e.*, m.muscle, m.is_primary
        FROM exercises e JOIN exercise_muscles m ON m.exercise_id = e.id
        WHERE {where}
        ORDER BY e.id
        """,
        params,
    ).fetchall()

    by_id: dict[int, sqlite3.Row] = {}
    primary, secondary = defaultdict(list), defaultdict(list)
    for row in rows:
        by_id[row["id"]] = row
        (primary if row["is_primary"] else secondary)[row["id"]].append(row["muscle"])
    return [
        CatalogExercise(
            id=row["id"],
            name_es=row["name_es"],
            name_en=row["name_en"],
            primary_muscles=sort_muscles(primary[exercise_id]),
            secondary_muscles=sort_muscles(secondary[exercise_id]),
            image_url=row["image_url"],
            license=row["license"],
            author=row["author"],
            description=row["description"],
        )
        for exercise_id, row in by_id.items()
    ]

"""SQLite storage for analyzed sessions and user-defined workout types."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cadence_ia.metrics import WorkoutMetrics
from cadence_ia.tcx import Activity

DEFAULT_DB_PATH = "~/cadencia-ia/cadence.db"

# Each entry upgrades the schema by one version. Never edit an entry once it
# has been released: the database now holds user data (workout types), so it
# can't simply be rebuilt from the TCX files. Append a new entry instead.
MIGRATIONS = [
    # 1: analyzed sessions and their work/rest segments
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id            TEXT PRIMARY KEY,   -- TCX file name without extension
        start_time    TEXT NOT NULL,      -- ISO 8601 with UTC offset
        sport         TEXT NOT NULL,
        device        TEXT,
        duration_s    INTEGER NOT NULL,
        calories      INTEGER NOT NULL,
        hr_min        INTEGER NOT NULL,
        hr_avg        INTEGER NOT NULL,
        hr_max        INTEGER NOT NULL,
        threshold_bpm REAL NOT NULL,
        sets          INTEGER NOT NULL,
        rests         INTEGER NOT NULL,
        heart_rate    TEXT NOT NULL,      -- JSON list of [seconds, bpm]
        analyzed_at   TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS segments (
        session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        position   INTEGER NOT NULL,
        kind       TEXT NOT NULL,         -- "work" or "rest"
        start_s    INTEGER NOT NULL,
        end_s      INTEGER NOT NULL,
        hr_start   INTEGER NOT NULL,
        hr_end     INTEGER NOT NULL,
        hr_avg     INTEGER NOT NULL,
        drop_30s   INTEGER,
        drop_60s   INTEGER,
        PRIMARY KEY (session_id, position)
    );

    CREATE INDEX IF NOT EXISTS sessions_start_time ON sessions(start_time);
    """,
    # 2: workout types chosen by the user ("Pierna", "Caminata"...)
    """
    CREATE TABLE workout_types (
        id       INTEGER PRIMARY KEY,
        name     TEXT NOT NULL UNIQUE COLLATE NOCASE,
        category TEXT NOT NULL CHECK (category IN ('strength', 'cardio'))
    );

    ALTER TABLE sessions
        ADD COLUMN workout_type_id INTEGER REFERENCES workout_types(id) ON DELETE SET NULL;
    """,
]


def db_path() -> Path:
    return Path(os.environ.get("CADENCE_DB", DEFAULT_DB_PATH)).expanduser()


def migrate(conn: sqlite3.Connection) -> None:
    """Apply the migrations this database hasn't seen yet."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
        # executescript commits on its own, so the version bump goes in the script.
        conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;")


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the database, creating the file and upgrading the schema if needed."""
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn


# --- Sessions ---------------------------------------------------------------

SESSION_COLUMNS = """
    s.id, s.start_time, s.sport, s.device, s.duration_s, s.calories,
    s.hr_min, s.hr_avg, s.hr_max, s.threshold_bpm, s.sets, s.rests,
    t.id AS type_id, t.name AS type_name, t.category AS type_category
"""


def session_ids(conn: sqlite3.Connection) -> set[str]:
    return {row["id"] for row in conn.execute("SELECT id FROM sessions")}


def save_session(
    conn: sqlite3.Connection, session_id: str, activity: Activity, metrics: WorkoutMetrics
) -> None:
    """Insert or refresh a session. The workout type chosen by the user is kept."""
    points = [tp for tp in activity.trackpoints if tp.heart_rate is not None]
    t0 = points[0].time
    heart_rate = [[(tp.time - t0).total_seconds(), tp.heart_rate] for tp in points]

    with conn:
        conn.execute(
            """INSERT INTO sessions (id, start_time, sport, device, duration_s, calories,
                   hr_min, hr_avg, hr_max, threshold_bpm, sets, rests, heart_rate, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (id) DO UPDATE SET
                   start_time = excluded.start_time, sport = excluded.sport,
                   device = excluded.device, duration_s = excluded.duration_s,
                   calories = excluded.calories, hr_min = excluded.hr_min,
                   hr_avg = excluded.hr_avg, hr_max = excluded.hr_max,
                   threshold_bpm = excluded.threshold_bpm, sets = excluded.sets,
                   rests = excluded.rests, heart_rate = excluded.heart_rate,
                   analyzed_at = excluded.analyzed_at""",
            (
                session_id,
                activity.laps[0].start_time.isoformat(),
                activity.sport,
                activity.device,
                metrics.duration_s,
                activity.calories,
                metrics.hr_min,
                metrics.hr_avg,
                metrics.hr_max,
                metrics.threshold_bpm,
                len(metrics.sets),
                len(metrics.rests),
                json.dumps(heart_rate, separators=(",", ":")),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        conn.execute("DELETE FROM segments WHERE session_id = ?", (session_id,))
        conn.executemany(
            """INSERT INTO segments (session_id, position, kind, start_s, end_s,
                   hr_start, hr_end, hr_avg, drop_30s, drop_60s)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (session_id, i, s.kind, s.start_s, s.end_s,
                 s.hr_start, s.hr_end, s.hr_avg, s.drop_30s, s.drop_60s)
                for i, s in enumerate(metrics.segments)
            ],
        )


def list_sessions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Session summaries (without the HR curve), newest first."""
    return conn.execute(
        f"""SELECT {SESSION_COLUMNS}
            FROM sessions s LEFT JOIN workout_types t ON t.id = s.workout_type_id
            ORDER BY s.start_time DESC"""
    ).fetchall()


def get_session(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    return conn.execute(
        f"""SELECT {SESSION_COLUMNS}, s.heart_rate
            FROM sessions s LEFT JOIN workout_types t ON t.id = s.workout_type_id
            WHERE s.id = ?""",
        (session_id,),
    ).fetchone()


def get_segments(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM segments WHERE session_id = ? ORDER BY position", (session_id,)
    ).fetchall()


STATS_QUERY = """
    SELECT s.id, s.start_time, s.duration_s, s.hr_avg, s.hr_max, s.sets,
           AVG(g.end_s - g.start_s) AS avg_rest_s,
           AVG(g.drop_30s) AS recovery_30s,
           AVG(g.drop_60s) AS recovery_60s
    FROM sessions s
    LEFT JOIN segments g ON g.session_id = s.id AND g.kind = 'rest'
    WHERE {where}
    GROUP BY s.id
    ORDER BY s.start_time
"""


def session_stats(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    """One session's numbers, including rest and recovery averages."""
    return conn.execute(STATS_QUERY.format(where="s.id = ?"), (session_id,)).fetchone()


def type_history(conn: sqlite3.Connection, type_id: int) -> list[sqlite3.Row]:
    """The numbers of every session of a workout type, oldest first."""
    return conn.execute(
        STATS_QUERY.format(where="s.workout_type_id = ?"), (type_id,)
    ).fetchall()


def set_session_type(conn: sqlite3.Connection, session_id: str, type_id: int | None) -> bool:
    """Assign (or clear, with None) a session's workout type. False if no such session."""
    with conn:
        cursor = conn.execute(
            "UPDATE sessions SET workout_type_id = ? WHERE id = ?", (type_id, session_id)
        )
    return cursor.rowcount > 0


# --- Workout types ----------------------------------------------------------

class DuplicateName(Exception):
    pass


def list_types(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT t.id, t.name, t.category, COUNT(s.id) AS session_count
           FROM workout_types t LEFT JOIN sessions s ON s.workout_type_id = t.id
           GROUP BY t.id ORDER BY t.name COLLATE NOCASE"""
    ).fetchall()


def get_type(conn: sqlite3.Connection, type_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT t.id, t.name, t.category, COUNT(s.id) AS session_count
           FROM workout_types t LEFT JOIN sessions s ON s.workout_type_id = t.id
           WHERE t.id = ? GROUP BY t.id""",
        (type_id,),
    ).fetchone()


def create_type(conn: sqlite3.Connection, name: str, category: str) -> int:
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO workout_types (name, category) VALUES (?, ?)", (name, category)
            )
    except sqlite3.IntegrityError as err:
        raise DuplicateName(name) from err
    return cursor.lastrowid


def update_type(conn: sqlite3.Connection, type_id: int, name: str, category: str) -> bool:
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE workout_types SET name = ?, category = ? WHERE id = ?",
                (name, category, type_id),
            )
    except sqlite3.IntegrityError as err:
        raise DuplicateName(name) from err
    return cursor.rowcount > 0


def delete_type(conn: sqlite3.Connection, type_id: int) -> bool:
    """Delete a type. Its sessions go back to having no type."""
    with conn:
        cursor = conn.execute("DELETE FROM workout_types WHERE id = ?", (type_id,))
    return cursor.rowcount > 0

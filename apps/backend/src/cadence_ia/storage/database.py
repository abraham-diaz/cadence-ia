"""SQLite connection and schema migrations."""

import sqlite3
from pathlib import Path

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
    # 3: the LLM's written assessment of a session (one per session)
    """
    CREATE TABLE assessments (
        session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
        content    TEXT NOT NULL,         -- JSON produced by the model
        model      TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
]


def _version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _statements(script: str) -> list[str]:
    """Split a migration script into single SQL statements."""
    statements, current = [], ""
    for line in script.splitlines(keepends=True):
        current += line
        if sqlite3.complete_statement(current):
            statements.append(current)
            current = ""
    return statements


def migrate(conn: sqlite3.Connection) -> None:
    """Apply the migrations this database hasn't seen yet.

    Safe when several processes (API, ingest timer) or requests open the
    database at the same time: the write lock is taken *before* reading the
    version, so a second process waits and then sees the upgraded schema.
    """
    if _version(conn) == len(MIGRATIONS):
        return  # up to date: the common case, no lock needed

    conn.execute("BEGIN IMMEDIATE")
    try:
        version = _version(conn)  # read again, now that we hold the lock
        for number, script in enumerate(MIGRATIONS[version:], start=version + 1):
            for statement in _statements(script):
                conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {number}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the database, creating the file and upgrading the schema if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI may open the connection in one worker
    # thread and run the endpoint in another. Each request has its own
    # connection and uses it one step at a time, so this is safe.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn

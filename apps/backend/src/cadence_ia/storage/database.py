import sqlite3
from pathlib import Path

# Never edit a released migration, append a new one: the database holds user data
# (workout types, assessments) that can't be rebuilt from the TCX files.
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
    # 4: training plans; only one is active, the old ones are kept for the history
    """
    CREATE TABLE plans (
        id          INTEGER PRIMARY KEY,
        title       TEXT NOT NULL,
        weeks       INTEGER NOT NULL CHECK (weeks >= 1),  -- weeks that repeat in turn
        cycle_start TEXT NOT NULL,        -- ISO date: the Monday the first week starts
        created_at  TEXT NOT NULL,
        active      INTEGER NOT NULL DEFAULT 1
    );

    CREATE UNIQUE INDEX plans_one_active ON plans(active) WHERE active = 1;

    CREATE TABLE plan_days (
        id              INTEGER PRIMARY KEY,
        plan_id         INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
        week            INTEGER NOT NULL,   -- 0 = first week of the cycle
        weekday         INTEGER NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0 = Monday
        workout_type_id INTEGER REFERENCES workout_types(id) ON DELETE SET NULL,
        minutes         INTEGER NOT NULL,
        note            TEXT
    );

    CREATE TABLE plan_exercises (
        plan_day_id INTEGER NOT NULL REFERENCES plan_days(id) ON DELETE CASCADE,
        position    INTEGER NOT NULL,
        name        TEXT NOT NULL,
        sets        INTEGER,
        reps        TEXT,                 -- "10-12", "30 s"...
        PRIMARY KEY (plan_day_id, position)
    );
    """,
    # 5: exercise catalog downloaded from wger, and the muscles each workout type trains
    """
    CREATE TABLE exercises (
        id        INTEGER PRIMARY KEY,    -- wger's id
        name_es   TEXT,
        name_en   TEXT,
        image_url TEXT,
        license   TEXT NOT NULL,          -- "CC-BY-SA 4"...: wger must be credited
        author    TEXT
    );

    CREATE TABLE exercise_muscles (
        exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
        muscle      TEXT NOT NULL,        -- one of domain.exercise.Muscle
        is_primary  INTEGER NOT NULL,
        PRIMARY KEY (exercise_id, muscle)
    );

    CREATE TABLE workout_type_muscles (
        workout_type_id INTEGER NOT NULL REFERENCES workout_types(id) ON DELETE CASCADE,
        muscle          TEXT NOT NULL,
        PRIMARY KEY (workout_type_id, muscle)
    );
    """,
    # 6: how to do each exercise, and the catalog entry a plan exercise refers to
    """
    ALTER TABLE exercises ADD COLUMN description TEXT;  -- plain text, one paragraph per line

    ALTER TABLE plan_exercises
        ADD COLUMN catalog_id INTEGER REFERENCES exercises(id) ON DELETE SET NULL;
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
    The write lock is taken before reading the version, so concurrent opens can't undo one."""
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
    # FastAPI may open the connection and run the endpoint in different threads;
    # each request still uses its own connection one step at a time.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    migrate(conn)
    return conn

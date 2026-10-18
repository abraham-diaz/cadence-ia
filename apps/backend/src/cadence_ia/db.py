"""SQLite storage for analyzed sessions."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cadence_ia.metrics import WorkoutMetrics
from cadence_ia.tcx import Activity

DEFAULT_DB_PATH = "~/cadencia-ia/cadence.db"

SCHEMA = """
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
"""


def db_path() -> Path:
    return Path(os.environ.get("CADENCE_DB", DEFAULT_DB_PATH)).expanduser()


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the database, creating the file and tables if needed."""
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def session_ids(conn: sqlite3.Connection) -> set[str]:
    return {row["id"] for row in conn.execute("SELECT id FROM sessions")}


def save_session(
    conn: sqlite3.Connection, session_id: str, activity: Activity, metrics: WorkoutMetrics
) -> None:
    """Insert a session, replacing it if it was already stored."""
    points = [tp for tp in activity.trackpoints if tp.heart_rate is not None]
    t0 = points[0].time
    heart_rate = [[(tp.time - t0).total_seconds(), tp.heart_rate] for tp in points]

    with conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.execute(
            """INSERT INTO sessions (id, start_time, sport, device, duration_s, calories,
                   hr_min, hr_avg, hr_max, threshold_bpm, sets, rests, heart_rate, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        """SELECT id, start_time, sport, duration_s, calories,
                  hr_min, hr_avg, hr_max, sets, rests
           FROM sessions ORDER BY start_time DESC"""
    ).fetchall()


def get_session(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()


def get_segments(conn: sqlite3.Connection, session_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM segments WHERE session_id = ? ORDER BY position", (session_id,)
    ).fetchall()

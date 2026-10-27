import json
import sqlite3
from datetime import datetime, timezone

from cadence_ia.domain.activity import Activity
from cadence_ia.domain.comparison import STAT_FIELDS, HistoryEntry, Stats
from cadence_ia.domain.heart_rate import Segment, WorkoutMetrics, curve
from cadence_ia.domain.session import Session
from cadence_ia.domain.workout_type import WorkoutType

SESSION_COLUMNS = """
    s.id, s.start_time, s.sport, s.device, s.duration_s, s.calories,
    s.hr_min, s.hr_avg, s.hr_max, s.threshold_bpm, s.sets, s.rests,
    t.id AS type_id, t.name AS type_name, t.category AS type_category
"""

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


def _session(row: sqlite3.Row) -> Session:
    workout_type = (
        WorkoutType(id=row["type_id"], name=row["type_name"], category=row["type_category"])
        if row["type_id"] is not None
        else None
    )
    return Session(
        id=row["id"],
        start_time=datetime.fromisoformat(row["start_time"]),
        sport=row["sport"],
        device=row["device"],
        duration_s=row["duration_s"],
        calories=row["calories"],
        hr_min=row["hr_min"],
        hr_avg=row["hr_avg"],
        hr_max=row["hr_max"],
        threshold_bpm=row["threshold_bpm"],
        sets=row["sets"],
        rests=row["rests"],
        workout_type=workout_type,
    )


def _history_entry(row: sqlite3.Row) -> HistoryEntry:
    return HistoryEntry(
        id=row["id"],
        start_time=datetime.fromisoformat(row["start_time"]),
        stats=Stats(**{name: row[name] for name in STAT_FIELDS}),
    )


def session_ids(conn: sqlite3.Connection) -> set[str]:
    return {row["id"] for row in conn.execute("SELECT id FROM sessions")}


def save_session(
    conn: sqlite3.Connection, session_id: str, activity: Activity, metrics: WorkoutMetrics
) -> None:
    """Insert or refresh a session. The workout type chosen by the user is kept."""
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
                json.dumps(curve(activity.trackpoints), separators=(",", ":")),
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


def list_sessions(conn: sqlite3.Connection) -> list[Session]:
    """Session summaries (without the HR curve), newest first."""
    rows = conn.execute(
        f"""SELECT {SESSION_COLUMNS}
            FROM sessions s LEFT JOIN workout_types t ON t.id = s.workout_type_id
            ORDER BY s.start_time DESC"""
    )
    return [_session(row) for row in rows]


def get_session(conn: sqlite3.Connection, session_id: str) -> Session | None:
    row = conn.execute(
        f"""SELECT {SESSION_COLUMNS}
            FROM sessions s LEFT JOIN workout_types t ON t.id = s.workout_type_id
            WHERE s.id = ?""",
        (session_id,),
    ).fetchone()
    return _session(row) if row else None


def get_heart_rate(conn: sqlite3.Connection, session_id: str) -> list[tuple[float, int]]:
    """The session's HR curve as (seconds since start, bpm); empty if no such session."""
    row = conn.execute("SELECT heart_rate FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return [(t, hr) for t, hr in json.loads(row["heart_rate"])] if row else []


def get_segments(conn: sqlite3.Connection, session_id: str) -> list[Segment]:
    rows = conn.execute(
        """SELECT kind, start_s, end_s, hr_start, hr_end, hr_avg, drop_30s, drop_60s
           FROM segments WHERE session_id = ? ORDER BY position""",
        (session_id,),
    )
    return [Segment(**dict(row)) for row in rows]


def session_stats(conn: sqlite3.Connection, session_id: str) -> HistoryEntry | None:
    """One session's numbers, including rest and recovery averages."""
    row = conn.execute(STATS_QUERY.format(where="s.id = ?"), (session_id,)).fetchone()
    return _history_entry(row) if row else None


def type_history(conn: sqlite3.Connection, type_id: int) -> list[HistoryEntry]:
    """The numbers of every session of a workout type, oldest first."""
    rows = conn.execute(STATS_QUERY.format(where="s.workout_type_id = ?"), (type_id,))
    return [_history_entry(row) for row in rows]


def set_session_type(conn: sqlite3.Connection, session_id: str, type_id: int | None) -> bool:
    """Assign (or clear, with None) a session's workout type. False if no such session."""
    with conn:
        cursor = conn.execute(
            "UPDATE sessions SET workout_type_id = ? WHERE id = ?", (type_id, session_id)
        )
    return cursor.rowcount > 0

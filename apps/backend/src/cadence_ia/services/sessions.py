import sqlite3
from dataclasses import dataclass, replace

from cadence_ia.domain.assessment import Assessment
from cadence_ia.domain.comparison import Baseline, HistoryEntry, Stats, baseline
from cadence_ia.domain.heart_rate import Segment
from cadence_ia.domain.session import Session
from cadence_ia.services.errors import InvalidInput, NotFound
from cadence_ia.storage import assessments, sessions, workout_types


@dataclass(frozen=True)
class SessionDetail:
    session: Session
    segments: list[Segment]
    heart_rate: list[tuple[float, int]]  # (seconds since start, bpm)
    stats: Stats
    # Average of the previous sessions of the same type; None if there are none.
    comparison: Baseline | None
    # Every session of the same type, oldest first (includes this one).
    history: list[HistoryEntry]
    assessment: Assessment | None


def _visible(session: Session) -> Session:
    """Sets and rests mean nothing until the user says it was a strength session."""
    return session if session.is_strength else replace(session, sets=None, rests=None)


def list_sessions(conn: sqlite3.Connection) -> list[Session]:
    """Every session, newest first."""
    return [_visible(session) for session in sessions.list_sessions(conn)]


def get_detail(conn: sqlite3.Connection, session_id: str) -> SessionDetail:
    session = sessions.get_session(conn, session_id)
    if session is None:
        raise NotFound("session_not_found", "Session not found")

    strength = session.is_strength
    history = sessions.type_history(conn, session.workout_type.id) if session.workout_type else []
    comparison = baseline(history, session_id)
    stats = sessions.session_stats(conn, session_id).stats
    if not strength:
        stats = stats.without_strength()
        history = [replace(h, stats=h.stats.without_strength()) for h in history]
        if comparison:
            comparison = replace(comparison, stats=comparison.stats.without_strength())

    return SessionDetail(
        session=_visible(session),
        segments=sessions.get_segments(conn, session_id) if strength else [],
        heart_rate=sessions.get_heart_rate(conn, session_id),
        stats=stats,
        comparison=comparison,
        history=history,
        assessment=assessments.get_assessment(conn, session_id),
    )


def set_workout_type(
    conn: sqlite3.Connection, session_id: str, type_id: int | None
) -> SessionDetail:
    """Assign a workout type to a session, or clear it with None."""
    if type_id is not None and workout_types.get_type(conn, type_id) is None:
        raise InvalidInput("workout_type_not_found", "Workout type not found")
    if not sessions.set_session_type(conn, session_id, type_id):
        raise NotFound("session_not_found", "Session not found")
    return get_detail(conn, session_id)

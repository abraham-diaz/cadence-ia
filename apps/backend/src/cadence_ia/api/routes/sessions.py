from fastapi import APIRouter

from cadence_ia.api.deps import AssessorDep, Database
from cadence_ia.api.schemas import (
    AssessmentOut,
    ErrorOut,
    SessionDetail,
    SessionSummary,
    SessionTypeIn,
    assessment_out,
    session_detail,
    session_summary,
)
from cadence_ia.services import assessments, sessions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

NOT_FOUND = {404: {"model": ErrorOut}}


@router.get("")
def list_sessions(conn: Database) -> list[SessionSummary]:
    return [session_summary(session) for session in sessions.list_sessions(conn)]


@router.get("/{session_id}", responses=NOT_FOUND)
def get_session(session_id: str, conn: Database) -> SessionDetail:
    return session_detail(sessions.get_detail(conn, session_id))


@router.put("/{session_id}/workout-type", responses={**NOT_FOUND, 422: {"model": ErrorOut}})
def set_workout_type(session_id: str, body: SessionTypeIn, conn: Database) -> SessionDetail:
    return session_detail(sessions.set_workout_type(conn, session_id, body.workout_type_id))


@router.post(
    "/{session_id}/assessment",
    responses={**NOT_FOUND, 409: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
def assess(session_id: str, conn: Database, assessor: AssessorDep) -> AssessmentOut:
    """Ask the LLM for a (new) assessment of the session and store it."""
    return assessment_out(assessments.assess(conn, session_id, assessor))

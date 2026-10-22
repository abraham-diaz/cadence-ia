"""Ask the LLM to assess a session and keep its answer."""

import sqlite3

from cadence_ia.domain.assessment import Assessment
from cadence_ia.llm.assessor import Assessor, AssessmentUnavailable, build_payload
from cadence_ia.services.errors import Conflict, Unavailable
from cadence_ia.services.sessions import get_detail
from cadence_ia.storage import assessments


def assess(conn: sqlite3.Connection, session_id: str, assessor: Assessor) -> Assessment:
    """Write a (new) assessment of the session, replacing the previous one."""
    detail = get_detail(conn, session_id)
    if detail.session.workout_type is None:
        raise Conflict("session_without_type", "Elige antes el tipo de entrenamiento")

    payload = build_payload(detail.session, detail.stats, detail.segments, detail.comparison)
    try:
        content = assessor(payload)
    except AssessmentUnavailable as err:
        raise Unavailable("assessment_unavailable", str(err)) from err

    assessments.save_assessment(conn, session_id, content.model_dump(), assessor.model)
    return assessments.get_assessment(conn, session_id)

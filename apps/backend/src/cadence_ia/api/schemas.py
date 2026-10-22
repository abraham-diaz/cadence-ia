"""What the API receives and returns, and how it is built from domain objects."""

from dataclasses import asdict
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cadence_ia.domain.assessment import Assessment
from cadence_ia.domain.session import Session
from cadence_ia.domain.workout_type import Category, WorkoutTypeUsage
from cadence_ia.llm.assessor import AssessmentContent
from cadence_ia.services import sessions
from cadence_ia.services.errors import ErrorCode

# --- Requests ---------------------------------------------------------------

class WorkoutTypeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=40)
    category: Category


class SessionTypeIn(BaseModel):
    workout_type_id: int | None  # None clears the type


# --- Responses --------------------------------------------------------------

class WorkoutTypeRef(BaseModel):
    id: int
    name: str
    category: Category


class WorkoutTypeOut(WorkoutTypeRef):
    session_count: int


class SegmentOut(BaseModel):
    kind: Literal["work", "rest"]
    start_s: int
    end_s: int
    duration_s: int
    hr_start: int
    hr_end: int
    hr_avg: int
    drop_30s: int | None
    drop_60s: int | None


class HeartRatePoint(BaseModel):
    t: float  # seconds since the first trackpoint
    hr: int


class SessionSummary(BaseModel):
    id: str
    start_time: datetime
    sport: str
    duration_s: int
    calories: int
    hr_min: int
    hr_avg: int
    hr_max: int
    workout_type: WorkoutTypeRef | None
    # Only for strength sessions: sets/rests mean nothing until the user
    # says the session was a strength workout.
    sets: int | None
    rests: int | None


class SessionStats(BaseModel):
    duration_s: float | None
    hr_avg: float | None
    hr_max: float | None
    # Strength only:
    sets: float | None
    avg_rest_s: float | None
    recovery_30s: float | None  # average HR drop 30 s into a rest
    recovery_60s: float | None


class HistoryPoint(SessionStats):
    id: str
    start_time: datetime


class Comparison(SessionStats):
    sessions: int  # how many previous sessions the averages come from


class AssessmentOut(AssessmentContent):
    model: str
    created_at: datetime


class SessionDetail(SessionSummary):
    device: str | None
    threshold_bpm: float
    segments: list[SegmentOut]
    heart_rate: list[HeartRatePoint]
    stats: SessionStats
    # Average of the previous sessions of the same type; None if there are none.
    comparison: Comparison | None
    # Every session of the same type, oldest first (includes this one).
    history: list[HistoryPoint]
    assessment: AssessmentOut | None


class ErrorOut(BaseModel):
    detail: str
    code: ErrorCode  # stable: the frontend shows a message for each code


# --- From domain objects ----------------------------------------------------

def workout_type_out(usage: WorkoutTypeUsage) -> WorkoutTypeOut:
    return WorkoutTypeOut(**asdict(usage.workout_type), session_count=usage.session_count)


def session_summary(session: Session) -> SessionSummary:
    workout_type = session.workout_type
    return SessionSummary(
        id=session.id,
        start_time=session.start_time,
        sport=session.sport,
        duration_s=session.duration_s,
        calories=session.calories,
        hr_min=session.hr_min,
        hr_avg=session.hr_avg,
        hr_max=session.hr_max,
        workout_type=WorkoutTypeRef(**asdict(workout_type)) if workout_type else None,
        sets=session.sets,
        rests=session.rests,
    )


def assessment_out(assessment: Assessment) -> AssessmentOut:
    return AssessmentOut(
        **assessment.content, model=assessment.model, created_at=assessment.created_at
    )


def session_detail(detail: sessions.SessionDetail) -> SessionDetail:
    session, comparison = detail.session, detail.comparison
    return SessionDetail(
        **session_summary(session).model_dump(),
        device=session.device,
        threshold_bpm=session.threshold_bpm,
        segments=[SegmentOut(**asdict(s), duration_s=s.duration_s) for s in detail.segments],
        heart_rate=[HeartRatePoint(t=t, hr=hr) for t, hr in detail.heart_rate],
        stats=SessionStats(**asdict(detail.stats)),
        comparison=(
            Comparison(sessions=comparison.sessions, **asdict(comparison.stats))
            if comparison
            else None
        ),
        history=[
            HistoryPoint(id=h.id, start_time=h.start_time, **asdict(h.stats))
            for h in detail.history
        ],
        assessment=assessment_out(detail.assessment) if detail.assessment else None,
    )

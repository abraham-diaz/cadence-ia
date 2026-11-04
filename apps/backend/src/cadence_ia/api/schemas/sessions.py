from dataclasses import asdict
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from cadence_ia.api.schemas.common import OutModel, WorkoutTypeRef
from cadence_ia.domain.assessment import Assessment
from cadence_ia.services import sessions


class SessionTypeIn(BaseModel):
    workout_type_id: int | None  # None clears the type


class SegmentOut(OutModel):
    kind: Literal["work", "rest"]
    start_s: int
    end_s: int
    duration_s: int
    hr_start: int
    hr_end: int
    hr_avg: int
    drop_30s: int | None
    drop_60s: int | None


class HeartRatePoint(OutModel):
    t: float  # seconds since the first trackpoint
    hr: int


class SessionSummary(OutModel):
    id: str
    start_time: datetime
    sport: str
    duration_s: int
    calories: int
    hr_min: int
    hr_avg: int
    hr_max: int
    workout_type: WorkoutTypeRef | None
    # Only for strength sessions.
    sets: int | None
    rests: int | None


class SessionStats(OutModel):
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


class AssessmentOut(OutModel):
    headline: str
    summary: str
    strengths: list[str]
    improvements: list[str]
    advice: str
    model: str
    created_at: datetime


class SessionDetail(SessionSummary):
    device: str | None
    threshold_bpm: float
    segments: list[SegmentOut]
    heart_rate: list[HeartRatePoint]
    stats: SessionStats
    # Average of the previous sessions of the same type.
    comparison: Comparison | None
    # Every session of the same type, oldest first (includes this one).
    history: list[HistoryPoint]
    assessment: AssessmentOut | None


def assessment_out(assessment: Assessment) -> AssessmentOut:
    return AssessmentOut(
        **assessment.content, model=assessment.model, created_at=assessment.created_at
    )


def session_detail(detail: sessions.SessionDetail) -> SessionDetail:
    comparison = detail.comparison
    return SessionDetail(
        **asdict(detail.session),
        segments=detail.segments,
        heart_rate=[HeartRatePoint(t=t, hr=hr) for t, hr in detail.heart_rate],
        stats=detail.stats,
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

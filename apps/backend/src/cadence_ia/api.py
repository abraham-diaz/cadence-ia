"""HTTP API. Run with: uvicorn cadence_ia.api:app --reload"""

from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cadence_ia.sessions import Session, get_session, list_sessions

app = FastAPI(title="cadence-ia", version="0.1.0")


class SegmentOut(BaseModel):
    kind: str
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
    sets: int
    rests: int


class SessionDetail(SessionSummary):
    device: str | None
    threshold_bpm: float
    segments: list[SegmentOut]
    heart_rate: list[HeartRatePoint]


def _summary_fields(session: Session) -> dict:
    a, m = session.activity, session.metrics
    return dict(
        id=session.id,
        start_time=a.laps[0].start_time,
        sport=a.sport,
        duration_s=m.duration_s,
        calories=a.calories,
        hr_min=m.hr_min,
        hr_avg=m.hr_avg,
        hr_max=m.hr_max,
        sets=len(m.sets),
        rests=len(m.rests),
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sessions")
def sessions() -> list[SessionSummary]:
    return [SessionSummary(**_summary_fields(s)) for s in list_sessions()]


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str) -> SessionDetail:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    points = [tp for tp in session.activity.trackpoints if tp.heart_rate is not None]
    t0 = points[0].time
    return SessionDetail(
        **_summary_fields(session),
        device=session.activity.device,
        threshold_bpm=session.metrics.threshold_bpm,
        segments=[
            SegmentOut(**vars(s), duration_s=s.duration_s)
            for s in session.metrics.segments
        ],
        heart_rate=[
            HeartRatePoint(t=(tp.time - t0).total_seconds(), hr=tp.heart_rate)
            for tp in points
        ],
    )

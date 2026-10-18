"""HTTP API. Run with: uvicorn cadence_ia.api:app --reload"""

import json
import os
import sqlite3
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from cadence_ia import assessment, db
from cadence_ia.compare import STAT_FIELDS, baseline
from cadence_ia.frontend import mount_frontend

# Secrets such as GEMINI_API_KEY live in apps/backend/.env (never committed).
load_dotenv()

app = FastAPI(title="cadence-ia", version="0.1.0")

Category = Literal["strength", "cardio"]


@app.middleware("http")
async def no_cache_for_api(request: Request, call_next):
    """API data changes (new workouts every 15 min): never let Safari reuse an old copy."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# --- Models -----------------------------------------------------------------

class WorkoutTypeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=40)
    category: Category


class WorkoutTypeRef(BaseModel):
    id: int
    name: str
    category: Category


class WorkoutTypeOut(WorkoutTypeRef):
    session_count: int


class SessionTypeIn(BaseModel):
    workout_type_id: int | None  # None clears the type


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


class AssessmentOut(assessment.AssessmentContent):
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


# --- Helpers ----------------------------------------------------------------

def get_db() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Database = Annotated[sqlite3.Connection, Depends(get_db)]


def get_assessor() -> Callable[[dict], assessment.AssessmentContent]:
    """The function that writes assessments (replaced by a fake in the tests)."""
    return assessment.generate


Assessor = Annotated[Callable[[dict], assessment.AssessmentContent], Depends(get_assessor)]


def _is_strength(row: sqlite3.Row) -> bool:
    return row["type_category"] == "strength"


def _summary(row: sqlite3.Row) -> SessionSummary:
    strength = _is_strength(row)
    workout_type = (
        WorkoutTypeRef(id=row["type_id"], name=row["type_name"], category=row["type_category"])
        if row["type_id"] is not None
        else None
    )
    return SessionSummary(
        id=row["id"],
        start_time=row["start_time"],
        sport=row["sport"],
        duration_s=row["duration_s"],
        calories=row["calories"],
        hr_min=row["hr_min"],
        hr_avg=row["hr_avg"],
        hr_max=row["hr_max"],
        workout_type=workout_type,
        sets=row["sets"] if strength else None,
        rests=row["rests"] if strength else None,
    )


STRENGTH_ONLY = ("sets", "avg_rest_s", "recovery_30s", "recovery_60s")


def _stats_fields(stats: Mapping, strength: bool) -> dict:
    """Stat values, hiding the strength-only ones for other sessions."""
    return {
        name: stats[name] if strength or name not in STRENGTH_ONLY else None
        for name in STAT_FIELDS
    }


def _detail(conn: sqlite3.Connection, session_id: str) -> SessionDetail:
    row = db.get_session(conn, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    strength = _is_strength(row)
    segments = db.get_segments(conn, session_id) if strength else []
    history = db.type_history(conn, row["type_id"]) if row["type_id"] is not None else []
    previous = baseline(history, session_id)

    return SessionDetail(
        assessment=_assessment(conn, session_id),
        stats=SessionStats(**_stats_fields(db.session_stats(conn, session_id), strength)),
        comparison=(
            Comparison(sessions=previous["sessions"], **_stats_fields(previous, strength))
            if previous
            else None
        ),
        history=[
            HistoryPoint(id=h["id"], start_time=h["start_time"], **_stats_fields(h, strength))
            for h in history
        ],
        **_summary(row).model_dump(),
        device=row["device"],
        threshold_bpm=row["threshold_bpm"],
        segments=[
            SegmentOut(
                **{k: s[k] for k in SegmentOut.model_fields if k != "duration_s"},
                duration_s=s["end_s"] - s["start_s"],
            )
            for s in segments
        ],
        heart_rate=[HeartRatePoint(t=t, hr=hr) for t, hr in json.loads(row["heart_rate"])],
    )


def _assessment(conn: sqlite3.Connection, session_id: str) -> AssessmentOut | None:
    row = db.get_assessment(conn, session_id)
    if row is None:
        return None
    return AssessmentOut(**json.loads(row["content"]), model=row["model"], created_at=row["created_at"])


def _type_or_404(conn: sqlite3.Connection, type_id: int) -> WorkoutTypeOut:
    row = db.get_type(conn, type_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Workout type not found")
    return WorkoutTypeOut(**dict(row))


def _duplicate(name: str) -> HTTPException:
    return HTTPException(status_code=409, detail=f"A workout type named '{name}' already exists")


# --- Routes -----------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sessions")
def sessions(conn: Database) -> list[SessionSummary]:
    return [_summary(row) for row in db.list_sessions(conn)]


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str, conn: Database) -> SessionDetail:
    return _detail(conn, session_id)


@app.put("/api/sessions/{session_id}/workout-type")
def set_session_type(session_id: str, body: SessionTypeIn, conn: Database) -> SessionDetail:
    if body.workout_type_id is not None and db.get_type(conn, body.workout_type_id) is None:
        raise HTTPException(status_code=422, detail="Workout type not found")
    if not db.set_session_type(conn, session_id, body.workout_type_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return _detail(conn, session_id)


@app.post("/api/sessions/{session_id}/assessment")
def create_assessment(session_id: str, conn: Database, write: Assessor) -> AssessmentOut:
    """Ask the LLM for a (new) assessment of the session and store it."""
    detail = _detail(conn, session_id)
    if detail.workout_type is None:
        raise HTTPException(status_code=409, detail="Elige antes el tipo de entrenamiento")
    try:
        content = write(assessment.build_payload(detail.model_dump()))
    except assessment.AssessmentUnavailable as err:
        raise HTTPException(status_code=503, detail=str(err))
    db.save_assessment(conn, session_id, content.model_dump_json(), assessment.model_name())
    return _assessment(conn, session_id)


@app.get("/api/workout-types")
def workout_types(conn: Database) -> list[WorkoutTypeOut]:
    return [WorkoutTypeOut(**dict(row)) for row in db.list_types(conn)]


@app.post("/api/workout-types", status_code=201)
def create_workout_type(body: WorkoutTypeIn, conn: Database) -> WorkoutTypeOut:
    try:
        type_id = db.create_type(conn, body.name, body.category)
    except db.DuplicateName:
        raise _duplicate(body.name)
    return _type_or_404(conn, type_id)


@app.put("/api/workout-types/{type_id}")
def update_workout_type(type_id: int, body: WorkoutTypeIn, conn: Database) -> WorkoutTypeOut:
    try:
        found = db.update_type(conn, type_id, body.name, body.category)
    except db.DuplicateName:
        raise _duplicate(body.name)
    if not found:
        raise HTTPException(status_code=404, detail="Workout type not found")
    return _type_or_404(conn, type_id)


@app.delete("/api/workout-types/{type_id}", status_code=204)
def delete_workout_type(type_id: int, conn: Database) -> Response:
    if not db.delete_type(conn, type_id):
        raise HTTPException(status_code=404, detail="Workout type not found")
    return Response(status_code=204)


# --- Web app ----------------------------------------------------------------

# In production (Docker) CADENCE_STATIC_DIR points to the compiled frontend.
# Registered last: its catch-all route must not shadow the API routes above.
if static_dir := os.environ.get("CADENCE_STATIC_DIR"):
    mount_frontend(app, Path(static_dir))

"""HTTP API. Run with: uvicorn cadence_ia.api:app --reload"""

import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from cadence_ia import db

app = FastAPI(title="cadence-ia", version="0.1.0")

Category = Literal["strength", "cardio"]


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


class SessionDetail(SessionSummary):
    device: str | None
    threshold_bpm: float
    segments: list[SegmentOut]
    heart_rate: list[HeartRatePoint]


# --- Helpers ----------------------------------------------------------------

def get_db() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Database = Annotated[sqlite3.Connection, Depends(get_db)]


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


def _detail(conn: sqlite3.Connection, session_id: str) -> SessionDetail:
    row = db.get_session(conn, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    segments = db.get_segments(conn, session_id) if _is_strength(row) else []
    return SessionDetail(
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

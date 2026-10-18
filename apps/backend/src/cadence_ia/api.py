"""HTTP API. Run with: uvicorn cadence_ia.api:app --reload"""

import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from cadence_ia import db

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


def get_db() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Database = Annotated[sqlite3.Connection, Depends(get_db)]


def _summary_fields(row: sqlite3.Row) -> dict:
    return {name: row[name] for name in SessionSummary.model_fields}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sessions")
def sessions(conn: Database) -> list[SessionSummary]:
    return [SessionSummary(**_summary_fields(row)) for row in db.list_sessions(conn)]


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str, conn: Database) -> SessionDetail:
    row = db.get_session(conn, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetail(
        **_summary_fields(row),
        device=row["device"],
        threshold_bpm=row["threshold_bpm"],
        segments=[
            SegmentOut(
                **{k: s[k] for k in SegmentOut.model_fields if k != "duration_s"},
                duration_s=s["end_s"] - s["start_s"],
            )
            for s in db.get_segments(conn, session_id)
        ],
        heart_rate=[HeartRatePoint(t=t, hr=hr) for t, hr in json.loads(row["heart_rate"])],
    )

"""The LLM's written assessment of a session (one per session)."""

import json
import sqlite3
from datetime import datetime, timezone

from cadence_ia.domain.assessment import Assessment


def get_assessment(conn: sqlite3.Connection, session_id: str) -> Assessment | None:
    row = conn.execute(
        "SELECT content, model, created_at FROM assessments WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return None
    return Assessment(
        content=json.loads(row["content"]),
        model=row["model"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def save_assessment(conn: sqlite3.Connection, session_id: str, content: dict, model: str) -> None:
    """Store a session's assessment, replacing the previous one."""
    with conn:
        conn.execute(
            """INSERT INTO assessments (session_id, content, model, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT (session_id) DO UPDATE SET
                   content = excluded.content, model = excluded.model,
                   created_at = excluded.created_at""",
            (
                session_id,
                json.dumps(content, ensure_ascii=False),
                model,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )

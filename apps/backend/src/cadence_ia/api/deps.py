"""Dependencies the routes ask for: settings, database connection, LLM."""

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from cadence_ia.config import Settings
from cadence_ia.llm.assessor import Assessor
from cadence_ia.llm.gemini import GeminiAssessor
from cadence_ia.storage.database import connect


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_settings)]


def get_db(settings: AppSettings) -> Iterator[sqlite3.Connection]:
    conn = connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


Database = Annotated[sqlite3.Connection, Depends(get_db)]


def get_assessor(settings: AppSettings) -> Assessor:
    """The LLM that writes assessments (replaced by a fake in the tests)."""
    return GeminiAssessor(api_key=settings.gemini_api_key, model=settings.gemini_model)


AssessorDep = Annotated[Assessor, Depends(get_assessor)]

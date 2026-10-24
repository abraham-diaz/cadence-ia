import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from cadence_ia.config import Settings
from cadence_ia.llm.assessor import Assessor
from cadence_ia.llm.coach import Coach
from cadence_ia.llm.gemini import GeminiAssessor, GeminiCoach, GeminiPlanExtractor
from cadence_ia.llm.planner import PlanExtractor
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
    """Replaced by a fake in the tests."""
    return GeminiAssessor(api_key=settings.gemini_api_key, model=settings.gemini_model)


AssessorDep = Annotated[Assessor, Depends(get_assessor)]


def get_coach(settings: AppSettings) -> Coach:
    """Replaced by a fake in the tests."""
    return GeminiCoach(api_key=settings.gemini_api_key, model=settings.gemini_model)


CoachDep = Annotated[Coach, Depends(get_coach)]


def get_plan_extractor(settings: AppSettings) -> PlanExtractor:
    """Replaced by a fake in the tests."""
    return GeminiPlanExtractor(api_key=settings.gemini_api_key, model=settings.gemini_model)


PlanExtractorDep = Annotated[PlanExtractor, Depends(get_plan_extractor)]

import json
from dataclasses import dataclass, field

import pytest
from conftest import write_sample_folder
from fastapi.testclient import TestClient

from cadence_ia.api.deps import get_assessor
from cadence_ia.config import Settings
from cadence_ia.llm.assessor import AssessmentContent
from cadence_ia.llm.errors import LLMUnavailable
from cadence_ia.llm.gemini import GeminiAssessor
from cadence_ia.main import create_app
from cadence_ia.services.ingest import ingest
from cadence_ia.storage import sessions, workout_types
from cadence_ia.storage.database import connect

FAKE = AssessmentContent(
    headline="Buena sesión de pierna",
    summary="Ritmo constante.",
    strengths=["Descansos regulares"],
    improvements=["Recuperar algo más"],
    advice="Alarga un poco los descansos.",
)


@dataclass
class FakeAssessor:
    """Stands in for Gemini: records the payloads it receives."""

    model: str = "test-model"
    calls: list[dict] = field(default_factory=list)
    error: str | None = None  # if set, behave as if Gemini were unavailable

    def __call__(self, payload: dict) -> AssessmentContent:
        self.calls.append(payload)
        if self.error:
            raise LLMUnavailable(self.error)
        return FAKE


@pytest.fixture
def assessor():
    return FakeAssessor()


@pytest.fixture
def calls(assessor):
    """Payloads received by the fake LLM."""
    return assessor.calls


@pytest.fixture
def db_file(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def client(tmp_path, db_file, assessor):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    conn = connect(db_file)
    ingest(conn, folder)
    leg = workout_types.create_type(conn, "Pierna", "strength")
    sessions.set_session_type(conn, "222", leg)
    conn.close()

    app = create_app(Settings(db_path=db_file))
    app.dependency_overrides[get_assessor] = lambda: assessor
    return TestClient(app)


def test_generate_and_store_assessment(client, calls):
    response = client.post("/api/sessions/222/assessment")
    assert response.status_code == 200
    data = response.json()
    assert data["headline"] == "Buena sesión de pierna"
    assert data["model"] == "test-model"

    detail = client.get("/api/sessions/222").json()
    assert detail["assessment"]["advice"] == "Alarga un poco los descansos."
    assert len(calls) == 1  # opening the session doesn't call the LLM again


def test_regenerate_replaces_previous(client, calls, db_file):
    client.post("/api/sessions/222/assessment")
    client.post("/api/sessions/222/assessment")
    assert len(calls) == 2
    conn = connect(db_file)
    assert conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0] == 1
    conn.close()


def test_session_without_type_is_rejected(client, calls):
    response = client.post("/api/sessions/111/assessment")
    assert response.status_code == 409
    assert response.json()["code"] == "session_without_type"
    assert calls == []


def test_unknown_session_is_404(client):
    response = client.post("/api/sessions/999/assessment")
    assert response.status_code == 404
    assert response.json()["code"] == "session_not_found"


def test_llm_unavailable_is_503(client, assessor):
    assessor.error = "Se ha agotado el cupo gratuito de Gemini por hoy"
    response = client.post("/api/sessions/222/assessment")
    assert response.status_code == 503
    assert response.json()["code"] == "assessment_unavailable"
    assert "cupo" in response.json()["detail"]
    assert client.get("/api/sessions/222").json()["assessment"] is None


def test_missing_api_key():
    with pytest.raises(LLMUnavailable, match="GEMINI_API_KEY"):
        GeminiAssessor(api_key=None, model="test-model")({})


def test_gemini_model_comes_from_settings(tmp_path):
    app = create_app(Settings(db_path=tmp_path / "x.db", gemini_model="other-model"))
    assessor = get_assessor(app.state.settings)
    assert assessor == GeminiAssessor(api_key=None, model="other-model")


def test_payload_has_metrics_but_no_identifying_data(client, calls):
    client.post("/api/sessions/222/assessment")
    payload = calls[0]
    assert payload["workout_type"] == "Pierna"
    assert payload["category"] == "strength"
    assert payload["date"] == "2026-10-03"
    assert payload["heart_rate"]["max"] == 140
    assert payload["stats"]["sets"] == 3
    assert {s["kind"] for s in payload["segments"]} == {"set", "rest"}
    text = json.dumps(payload)
    for private in ("222", "Test Device", "heart_rate_points", "tcx"):
        assert private not in text
    assert "comparison" not in payload  # first session of its type

import json

import pytest
from conftest import write_sample_folder
from fastapi.testclient import TestClient

from cadence_ia import assessment, db
from cadence_ia.api import app, get_assessor
from cadence_ia.ingest import ingest

FAKE = assessment.AssessmentContent(
    headline="Buena sesión de pierna",
    summary="Ritmo constante.",
    strengths=["Descansos regulares"],
    improvements=["Recuperar algo más"],
    advice="Alarga un poco los descansos.",
)


@pytest.fixture
def calls():
    """Payloads received by the fake LLM."""
    return []


@pytest.fixture
def client(tmp_path, monkeypatch, calls):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    db_file = tmp_path / "test.db"
    conn = db.connect(db_file)
    ingest(conn, folder)
    leg = db.create_type(conn, "Pierna", "strength")
    db.set_session_type(conn, "222", leg)
    conn.close()
    monkeypatch.setenv("CADENCE_DB", str(db_file))

    def fake_llm(payload):
        calls.append(payload)
        return FAKE

    app.dependency_overrides[get_assessor] = lambda: fake_llm
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_generate_and_store_assessment(client, calls):
    response = client.post("/api/sessions/222/assessment")
    assert response.status_code == 200
    data = response.json()
    assert data["headline"] == "Buena sesión de pierna"
    assert data["model"] == assessment.model_name()

    detail = client.get("/api/sessions/222").json()
    assert detail["assessment"]["advice"] == "Alarga un poco los descansos."
    assert len(calls) == 1  # opening the session doesn't call the LLM again


def test_regenerate_replaces_previous(client, calls):
    client.post("/api/sessions/222/assessment")
    client.post("/api/sessions/222/assessment")
    assert len(calls) == 2
    conn = db.connect()
    assert conn.execute("SELECT COUNT(*) FROM assessments").fetchone()[0] == 1
    conn.close()


def test_session_without_type_is_rejected(client, calls):
    assert client.post("/api/sessions/111/assessment").status_code == 409
    assert calls == []


def test_unknown_session_is_404(client):
    assert client.post("/api/sessions/999/assessment").status_code == 404


def test_llm_unavailable_is_503(client):
    def broken(payload):
        raise assessment.AssessmentUnavailable("Se ha agotado el cupo gratuito de Gemini por hoy")

    app.dependency_overrides[get_assessor] = lambda: broken
    response = client.post("/api/sessions/222/assessment")
    assert response.status_code == 503
    assert "cupo" in response.json()["detail"]
    assert client.get("/api/sessions/222").json()["assessment"] is None


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(assessment.AssessmentUnavailable, match="GEMINI_API_KEY"):
        assessment.generate({})


def test_payload_has_metrics_but_no_identifying_data(client, calls):
    client.post("/api/sessions/222/assessment")
    payload = calls[0]
    assert payload["workout_type"] == "Pierna"
    assert payload["category"] == "strength"
    assert payload["heart_rate"]["max"] == 140
    assert payload["stats"]["sets"] == 3
    assert {s["kind"] for s in payload["segments"]} == {"set", "rest"}
    text = json.dumps(payload)
    for private in ("222", "Test Device", "heart_rate_points", "tcx"):
        assert private not in text
    assert "comparison" not in payload  # first session of its type

import pytest
from conftest import sets_curve, write_sample_folder
from fastapi.testclient import TestClient

from cadence_ia import db
from cadence_ia.api import app
from cadence_ia.ingest import ingest


@pytest.fixture
def client(tmp_path, monkeypatch):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    db_file = tmp_path / "test.db"
    conn = db.connect(db_file)
    ingest(conn, folder)
    conn.close()
    monkeypatch.setenv("CADENCE_DB", str(db_file))
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_sessions_newest_first(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert [s["id"] for s in data] == ["222", "111"]
    assert data[0]["sets"] == 3
    assert data[1]["sets"] == 2
    assert data[0]["hr_max"] == 140
    assert data[0]["start_time"] == "2026-10-03T18:00:00+02:00"


def test_session_detail(client):
    data = client.get("/api/sessions/111").json()
    assert data["device"] == "Test Device"
    assert data["heart_rate"][0] == {"t": 0.0, "hr": 100}
    assert len(data["heart_rate"]) == len(sets_curve(2))
    kinds = [s["kind"] for s in data["segments"]]
    assert kinds[:4] == ["work", "rest", "work", "rest"]
    first = data["segments"][0]
    assert first["duration_s"] == first["end_s"] - first["start_s"]


def test_unknown_session_is_404(client):
    assert client.get("/api/sessions/999").status_code == 404


def test_empty_database(tmp_path, monkeypatch):
    monkeypatch.setenv("CADENCE_DB", str(tmp_path / "empty.db"))
    assert TestClient(app).get("/api/sessions").json() == []

import pytest
from conftest import sets_curve, write_sample_folder
from fastapi.testclient import TestClient

from cadence_ia.config import Settings
from cadence_ia.main import create_app
from cadence_ia.services.ingest import ingest
from cadence_ia.storage.database import connect


@pytest.fixture
def client(tmp_path):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    db_file = tmp_path / "test.db"
    conn = connect(db_file)
    ingest(conn, folder)
    conn.close()
    return TestClient(create_app(Settings(db_path=db_file)))


def make_type(client, name="Pierna", category="strength") -> dict:
    response = client.post("/api/workout-types", json={"name": name, "category": category})
    assert response.status_code == 201
    return response.json()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_sessions_newest_first(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert [s["id"] for s in data] == ["222", "111"]
    assert data[0]["hr_max"] == 140
    assert data[0]["start_time"] == "2026-10-03T18:00:00+02:00"


def test_new_session_has_no_type_and_no_sets(client):
    data = client.get("/api/sessions/111").json()
    assert data["workout_type"] is None
    assert data["sets"] is None
    assert data["segments"] == []
    assert data["device"] == "Test Device"
    assert data["heart_rate"][0] == {"t": 0.0, "hr": 100}
    assert len(data["heart_rate"]) == len(sets_curve(2))


def test_strength_type_shows_sets(client):
    leg = make_type(client)
    data = client.put("/api/sessions/111/workout-type", json={"workout_type_id": leg["id"]}).json()
    assert data["workout_type"] == {"id": leg["id"], "name": "Pierna", "category": "strength"}
    assert data["sets"] == 2
    kinds = [s["kind"] for s in data["segments"]]
    assert kinds[:4] == ["work", "rest", "work", "rest"]
    first = data["segments"][0]
    assert first["duration_s"] == first["end_s"] - first["start_s"]

    listed = {s["id"]: s for s in client.get("/api/sessions").json()}
    assert listed["111"]["workout_type"]["name"] == "Pierna"
    assert listed["111"]["sets"] == 2
    assert listed["222"]["workout_type"] is None


def test_cardio_type_hides_sets(client):
    walk = make_type(client, "Caminata", "cardio")
    data = client.put("/api/sessions/111/workout-type", json={"workout_type_id": walk["id"]}).json()
    assert data["sets"] is None
    assert data["segments"] == []


def test_clear_session_type(client):
    leg = make_type(client)
    client.put("/api/sessions/111/workout-type", json={"workout_type_id": leg["id"]})
    data = client.put("/api/sessions/111/workout-type", json={"workout_type_id": None}).json()
    assert data["workout_type"] is None


def test_assign_errors(client):
    assert client.put("/api/sessions/999/workout-type", json={"workout_type_id": None}).status_code == 404
    assert client.put("/api/sessions/111/workout-type", json={"workout_type_id": 42}).status_code == 422


def test_workout_type_crud(client):
    created = make_type(client, "  Torso  ")
    assert created["name"] == "Torso"  # whitespace trimmed
    assert created["session_count"] == 0

    make_type(client, "Caminata", "cardio")
    names = [t["name"] for t in client.get("/api/workout-types").json()]
    assert names == ["Caminata", "Torso"]  # alphabetical

    updated = client.put(
        f"/api/workout-types/{created['id']}", json={"name": "Torso A", "category": "strength"}
    ).json()
    assert updated["name"] == "Torso A"

    assert client.delete(f"/api/workout-types/{created['id']}").status_code == 204
    assert client.delete(f"/api/workout-types/{created['id']}").status_code == 404
    assert [t["name"] for t in client.get("/api/workout-types").json()] == ["Caminata"]


def test_duplicate_type_name_is_409(client):
    make_type(client, "Pierna")
    response = client.post("/api/workout-types", json={"name": "pierna", "category": "cardio"})
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_workout_type"


def test_errors_carry_a_stable_code(client):
    """The frontend shows a message for each code, so they must not change."""
    cases = [
        (client.get("/api/sessions/999"), 404, "session_not_found"),
        (client.put("/api/sessions/111/workout-type", json={"workout_type_id": 42}), 422, "workout_type_not_found"),
        (client.put("/api/workout-types/42", json={"name": "X", "category": "cardio"}), 404, "workout_type_not_found"),
        (client.delete("/api/workout-types/42"), 404, "workout_type_not_found"),
    ]
    for response, status, code in cases:
        assert response.status_code == status
        assert response.json()["code"] == code


def test_invalid_type_input_is_422(client):
    assert client.post("/api/workout-types", json={"name": "", "category": "strength"}).status_code == 422
    assert client.post("/api/workout-types", json={"name": "Yoga", "category": "flex"}).status_code == 422


def test_deleting_type_keeps_sessions(client):
    leg = make_type(client)
    client.put("/api/sessions/111/workout-type", json={"workout_type_id": leg["id"]})
    assert client.get("/api/workout-types").json()[0]["session_count"] == 1

    client.delete(f"/api/workout-types/{leg['id']}")
    data = client.get("/api/sessions/111").json()
    assert data["workout_type"] is None


def test_unknown_session_is_404(client):
    assert client.get("/api/sessions/999").status_code == 404


def test_empty_database(tmp_path):
    app = create_app(Settings(db_path=tmp_path / "empty.db"))
    assert TestClient(app).get("/api/sessions").json() == []


def test_api_responses_are_never_cached(client):
    assert client.get("/api/sessions").headers["cache-control"] == "no-store"

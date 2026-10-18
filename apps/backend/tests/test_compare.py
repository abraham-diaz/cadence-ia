from datetime import datetime

import pytest
from conftest import write_tcx
from fastapi.testclient import TestClient

from cadence_ia import db
from cadence_ia.api import app
from cadence_ia.compare import baseline
from cadence_ia.ingest import ingest


def entry(session_id, hr_avg, recovery_60s=None):
    return {
        "id": session_id, "duration_s": 600, "hr_avg": hr_avg, "hr_max": 150, "sets": 3,
        "avg_rest_s": 60, "recovery_30s": 10, "recovery_60s": recovery_60s,
    }


def test_baseline_averages_previous_sessions():
    history = [entry("a", 100), entry("b", 110), entry("c", 130)]
    result = baseline(history, "c")
    assert result["sessions"] == 2
    assert result["hr_avg"] == 105


def test_baseline_uses_only_the_last_n():
    history = [entry(str(i), 100 + i) for i in range(8)]
    result = baseline(history, "7", last=5)
    assert result["sessions"] == 5
    assert result["hr_avg"] == pytest.approx(sum(100 + i for i in range(2, 7)) / 5)


def test_baseline_ignores_missing_values():
    history = [entry("a", 100, recovery_60s=None), entry("b", 100, recovery_60s=12), entry("c", 100)]
    assert baseline(history, "c")["recovery_60s"] == 12
    history = [entry("a", 100), entry("b", 100)]
    assert baseline(history, "b")["recovery_60s"] is None


def test_first_session_has_no_baseline():
    assert baseline([entry("a", 100)], "a") is None
    assert baseline([], "a") is None


def strength_curve(n_sets: int, peak: int) -> list[int]:
    """n sets rising 100 -> peak over 60 s and back, sampled every 2 s."""
    step = (peak - 100) / 30
    up = [round(100 + i * step) for i in range(30)]
    return (up + up[::-1]) * n_sets + [peak] * 10


@pytest.fixture
def client(tmp_path, monkeypatch):
    folder = tmp_path / "tcx"
    folder.mkdir()
    days = ["2026-10-01", "2026-10-03", "2026-10-05", "2026-10-07"]
    for i, day in enumerate(days):
        write_tcx(folder / f"{i + 1}.tcx", datetime.fromisoformat(f"{day}T10:00:00+02:00"),
                  strength_curve(2 + i, 130 + 5 * i))
    db_file = tmp_path / "test.db"
    conn = db.connect(db_file)
    ingest(conn, folder)
    leg = db.create_type(conn, "Pierna", "strength")
    walk = db.create_type(conn, "Caminata", "cardio")
    for session_id in ("1", "2", "3"):
        db.set_session_type(conn, session_id, leg)
    db.set_session_type(conn, "4", walk)
    conn.close()
    monkeypatch.setenv("CADENCE_DB", str(db_file))
    return TestClient(app)


def test_detail_compares_with_previous_sessions_of_same_type(client):
    data = client.get("/api/sessions/3").json()
    assert data["comparison"]["sessions"] == 2
    first, second = (client.get(f"/api/sessions/{i}").json()["stats"] for i in ("1", "2"))
    assert data["comparison"]["hr_avg"] == pytest.approx((first["hr_avg"] + second["hr_avg"]) / 2)
    assert data["comparison"]["sets"] == pytest.approx((2 + 3) / 2)
    assert data["stats"]["sets"] == 4
    assert data["stats"]["recovery_30s"] > 0
    assert [h["id"] for h in data["history"]] == ["1", "2", "3"]  # walk excluded


def test_first_session_of_a_type_has_no_comparison(client):
    data = client.get("/api/sessions/1").json()
    assert data["comparison"] is None
    assert len(data["history"]) == 3


def test_cardio_session_has_no_strength_stats(client):
    data = client.get("/api/sessions/4").json()
    assert data["stats"]["hr_avg"] is not None
    assert data["stats"]["sets"] is None
    assert data["stats"]["recovery_30s"] is None
    assert data["comparison"] is None
    assert [h["id"] for h in data["history"]] == ["4"]


def test_untyped_session_has_stats_but_no_history(client, tmp_path):
    client.put("/api/sessions/2/workout-type", json={"workout_type_id": None})
    data = client.get("/api/sessions/2").json()
    assert data["history"] == []
    assert data["comparison"] is None
    assert data["stats"]["sets"] is None
    # and session 3 now only compares with session 1
    assert client.get("/api/sessions/3").json()["comparison"]["sessions"] == 1

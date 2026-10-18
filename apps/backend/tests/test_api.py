from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from cadence_ia.api import app

NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"


def write_tcx(path, start: datetime, bpms: list[int]) -> None:
    """Write a minimal synthetic TCX with one trackpoint every 2 s."""
    points = "".join(
        f"<Trackpoint><Time>{(start + timedelta(seconds=2 * i)).isoformat()}</Time>"
        f"<HeartRateBpm><Value>{hr}</Value></HeartRateBpm></Trackpoint>"
        for i, hr in enumerate(bpms)
    )
    path.write_text(
        f'<TrainingCenterDatabase xmlns="{NS}"><Activities><Activity Sport="Other">'
        f"<Id>{start.isoformat()}</Id>"
        f'<Lap StartTime="{start.isoformat()}"><TotalTimeSeconds>{2 * len(bpms)}</TotalTimeSeconds>'
        f"<DistanceMeters>0</DistanceMeters><Calories>100</Calories>"
        f"<Track>{points}</Track></Lap>"
        f"<Creator><Name>Test Device</Name></Creator>"
        f"</Activity></Activities></TrainingCenterDatabase>"
    )


def sets_curve(n_sets: int) -> list[int]:
    """HR rising 100 -> 140 over 60 s, then falling back over 60 s, n times."""
    up = [100 + i * 4 // 3 for i in range(30)]
    down = [140 - i * 4 // 3 for i in range(30)]
    return (up + down) * n_sets + [140] * 10


@pytest.fixture
def client(tmp_path, monkeypatch):
    write_tcx(tmp_path / "111.tcx", datetime.fromisoformat("2026-10-01T10:00:00+02:00"), sets_curve(2))
    write_tcx(tmp_path / "222.tcx", datetime.fromisoformat("2026-10-03T18:00:00+02:00"), sets_curve(3))
    (tmp_path / "broken.tcx").write_text("not xml")
    monkeypatch.setenv("CADENCE_DATA_DIR", str(tmp_path))
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_sessions_newest_first_and_skips_broken(client):
    response = client.get("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert [s["id"] for s in data] == ["222", "111"]
    assert data[0]["sets"] == 3
    assert data[1]["sets"] == 2
    assert data[0]["hr_max"] == 140


def test_session_detail(client):
    data = client.get("/api/sessions/111").json()
    assert data["device"] == "Test Device"
    assert data["heart_rate"][0] == {"t": 0.0, "hr": 100}
    assert len(data["heart_rate"]) == len(sets_curve(2))
    kinds = [s["kind"] for s in data["segments"]]
    assert kinds[:4] == ["work", "rest", "work", "rest"]


def test_unknown_session_is_404(client):
    assert client.get("/api/sessions/999").status_code == 404


def test_path_traversal_is_rejected(client):
    assert client.get("/api/sessions/..%2F..%2Fsecret").status_code == 404

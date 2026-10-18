import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cadence_ia.frontend import mount_frontend


@pytest.fixture
def client(tmp_path):
    static = tmp_path / "dist"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<html>app</html>")
    (static / "assets" / "index-abc123.js").write_text("console.log(1)")
    (static / "manifest.webmanifest").write_text("{}")
    (tmp_path / "secret.txt").write_text("private")

    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    mount_frontend(app, static)
    return TestClient(app)


def test_root_serves_index(client):
    response = client.get("/")
    assert response.text == "<html>app</html>"
    assert response.headers["cache-control"] == "no-cache"


def test_app_routes_fall_back_to_index(client):
    assert client.get("/sesion/123").text == "<html>app</html>"
    assert client.get("/tipos").text == "<html>app</html>"


def test_static_files_are_served(client):
    response = client.get("/assets/index-abc123.js")
    assert response.text == "console.log(1)"
    assert "immutable" in response.headers["cache-control"]
    assert client.get("/manifest.webmanifest").text == "{}"


def test_api_routes_still_work(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_unknown_api_path_is_404_not_index(client):
    assert client.get("/api/nope").status_code == 404


def test_cannot_read_files_outside_dist(client):
    response = client.get("/..%2Fsecret.txt")
    assert "private" not in response.text


def test_missing_build_fails_loudly(tmp_path):
    with pytest.raises(RuntimeError, match="build the frontend"):
        mount_frontend(FastAPI(), tmp_path)

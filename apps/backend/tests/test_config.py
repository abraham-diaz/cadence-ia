from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cadence_ia import config
from cadence_ia.config import Settings
from cadence_ia.main import create_app

VARIABLES = ("CADENCE_DB", "CADENCE_DATA_DIR", "CADENCE_STATIC_DIR", "GEMINI_API_KEY", "GEMINI_MODEL")


@pytest.fixture
def clean_env(monkeypatch):
    """No settings in the environment, and the real .env file not loaded."""
    for name in VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    return monkeypatch


def test_defaults(clean_env):
    settings = Settings.from_env()
    assert settings.db_path == Path("~/cadencia-ia/cadence.db").expanduser()
    assert settings.data_dir == Path("~/cadencia-ia/entrada").expanduser()
    assert settings.static_dir is None
    assert settings.gemini_api_key is None
    assert settings.gemini_model == config.DEFAULT_GEMINI_MODEL


def test_reads_environment(clean_env, tmp_path):
    clean_env.setenv("CADENCE_DB", str(tmp_path / "x.db"))
    clean_env.setenv("CADENCE_DATA_DIR", str(tmp_path / "tcx"))
    clean_env.setenv("CADENCE_STATIC_DIR", str(tmp_path / "dist"))
    clean_env.setenv("GEMINI_API_KEY", "secret")
    clean_env.setenv("GEMINI_MODEL", "other-model")
    settings = Settings.from_env()
    assert settings.db_path == tmp_path / "x.db"
    assert settings.data_dir == tmp_path / "tcx"
    assert settings.static_dir == tmp_path / "dist"
    assert settings.gemini_api_key == "secret"
    assert settings.gemini_model == "other-model"


def test_empty_api_key_counts_as_missing(clean_env):
    clean_env.setenv("GEMINI_API_KEY", "")
    assert Settings.from_env().gemini_api_key is None


def test_app_serves_frontend_only_with_static_dir(tmp_path):
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("<html>app</html>")

    api_only = TestClient(create_app(Settings(db_path=tmp_path / "a.db")))
    assert api_only.get("/").status_code == 404

    full = TestClient(create_app(Settings(db_path=tmp_path / "a.db", static_dir=static)))
    assert full.get("/").text == "<html>app</html>"
    assert full.get("/api/health").json() == {"status": "ok"}

"""The only place that reads the environment (and apps/backend/.env, never committed)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_DB_PATH = "~/cadencia-ia/cadence.db"
DEFAULT_DATA_DIR = "~/cadencia-ia/entrada"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(DEFAULT_DB_PATH).expanduser()
    data_dir: Path = Path(DEFAULT_DATA_DIR).expanduser()
    # The compiled frontend (apps/frontend/dist). None: serve only the API.
    static_dir: Path | None = None
    gemini_api_key: str | None = None
    gemini_model: str = DEFAULT_GEMINI_MODEL

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        static_dir = os.environ.get("CADENCE_STATIC_DIR")
        return cls(
            db_path=Path(os.environ.get("CADENCE_DB", DEFAULT_DB_PATH)).expanduser(),
            data_dir=Path(os.environ.get("CADENCE_DATA_DIR", DEFAULT_DATA_DIR)).expanduser(),
            static_dir=Path(static_dir) if static_dir else None,
            gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
            gemini_model=os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        )

"""Find TCX files in the data folder and analyze them (cached in memory)."""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cadence_ia.metrics import WorkoutMetrics, analyze
from cadence_ia.tcx import Activity, parse_tcx

log = logging.getLogger(__name__)

DEFAULT_DATA_DIR = "~/cadencia-ia/entrada"


@dataclass
class Session:
    id: str
    activity: Activity
    metrics: WorkoutMetrics


def data_dir() -> Path:
    return Path(os.environ.get("CADENCE_DATA_DIR", DEFAULT_DATA_DIR)).expanduser()


# Workout files never change once exported, so each one is analyzed only once.
@lru_cache(maxsize=256)
def load_session(path: Path) -> Session:
    activity = parse_tcx(path)
    return Session(id=path.stem, activity=activity, metrics=analyze(activity))


def list_sessions() -> list[Session]:
    """All readable sessions, newest first. Broken files are logged and skipped."""
    sessions = []
    for path in data_dir().glob("*.tcx"):
        try:
            sessions.append(load_session(path))
        except Exception:
            log.exception("Could not read %s", path)
    return sorted(sessions, key=lambda s: s.activity.laps[0].start_time, reverse=True)


def get_session(session_id: str) -> Session | None:
    # Only plain file names: no "../" tricks to read outside the data folder.
    if not session_id.isalnum():
        return None
    path = data_dir() / f"{session_id}.tcx"
    return load_session(path) if path.is_file() else None

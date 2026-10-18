"""Analyze new TCX files from the data folder and store them in the database."""

import logging
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from cadence_ia import db
from cadence_ia.metrics import analyze
from cadence_ia.tcx import parse_tcx

log = logging.getLogger(__name__)

DEFAULT_DATA_DIR = "~/cadencia-ia/entrada"


@dataclass
class IngestResult:
    added: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # already in the database
    failed: list[str] = field(default_factory=list)


def data_dir() -> Path:
    return Path(os.environ.get("CADENCE_DATA_DIR", DEFAULT_DATA_DIR)).expanduser()


def ingest(conn: sqlite3.Connection, folder: Path, force: bool = False) -> IngestResult:
    """Store every TCX in `folder` that is not in the database yet.

    With `force`, already stored files are analyzed again (useful after
    improving the metrics). Broken files are logged and retried next run.
    """
    result = IngestResult()
    known = db.session_ids(conn)

    for path in sorted(folder.glob("*.tcx")):
        session_id = path.stem
        if session_id in known and not force:
            result.skipped.append(session_id)
            continue
        try:
            activity = parse_tcx(path)
            db.save_session(conn, session_id, activity, analyze(activity))
            result.added.append(session_id)
        except Exception:
            log.exception("Could not ingest %s", path)
            result.failed.append(path.name)
    return result

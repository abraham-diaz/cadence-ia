import sqlite3

from conftest import write_sample_folder

from cadence_ia.services.ingest import ingest
from cadence_ia.storage import assessments, sessions, workout_types
from cadence_ia.storage.database import MIGRATIONS, connect


def test_new_database_is_at_latest_version(tmp_path):
    conn = connect(tmp_path / "new.db")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
    conn.close()


def test_upgrade_keeps_existing_sessions(tmp_path):
    db_file = tmp_path / "old.db"

    # A database from before workout types existed (schema version 1), with a session.
    old = sqlite3.connect(db_file)
    old.executescript(MIGRATIONS[0])
    old.execute(
        """INSERT INTO sessions VALUES ('111', '2026-10-01T10:00:00+02:00', 'Other', NULL,
               600, 100, 90, 120, 150, 6.0, 3, 2, '[[0, 90]]', '2026-10-01T12:00:00+00:00')"""
    )
    old.execute("INSERT INTO segments VALUES ('111', 0, 'work', 0, 60, 90, 140, 120, NULL, NULL)")
    old.execute("PRAGMA user_version = 1")
    old.commit()
    old.close()

    conn = connect(db_file)  # upgrades to the latest version
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
    session = sessions.get_session(conn, "111")
    assert session.hr_avg == 120 and session.workout_type is None
    assert len(sessions.get_segments(conn, "111")) == 1
    type_id = workout_types.create_type(conn, "Pierna", "strength")
    assert sessions.set_session_type(conn, "111", type_id)
    conn.close()

    conn = connect(db_file)  # reopening must not migrate again or lose data
    assert sessions.get_session(conn, "111").workout_type.name == "Pierna"
    conn.close()


def test_reingest_keeps_chosen_type(tmp_path):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    conn = connect(tmp_path / "test.db")
    ingest(conn, folder)
    type_id = workout_types.create_type(conn, "Pierna", "strength")
    sessions.set_session_type(conn, "111", type_id)

    ingest(conn, folder, force=True)
    assert sessions.get_session(conn, "111").workout_type.name == "Pierna"
    conn.close()


def test_concurrent_first_open_migrates_once(tmp_path):
    """Several processes/requests opening a new database at once must not
    re-run or undo migrations (it used to leave the version behind)."""
    from concurrent.futures import ThreadPoolExecutor

    db_file = tmp_path / "race.db"

    def open_and_close(_):
        connect(db_file).close()

    for _ in range(5):
        if db_file.exists():
            db_file.unlink()
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(open_and_close, range(8)))
        conn = connect(db_file)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(MIGRATIONS)
        conn.close()


def test_connection_can_be_used_from_another_thread(tmp_path):
    """FastAPI may open the connection (dependency) and run the endpoint in
    different worker threads; each request still uses it one step at a time."""
    from concurrent.futures import ThreadPoolExecutor

    conn = connect(tmp_path / "threads.db")
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(sessions.list_sessions, conn).result() == []
    conn.close()


def test_assessment_round_trip_keeps_accents(tmp_path):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    conn = connect(tmp_path / "test.db")
    ingest(conn, folder)
    content = {"headline": "Sesión intensa", "strengths": ["Recuperación rápida"]}

    assessments.save_assessment(conn, "111", content, "test-model")
    stored = assessments.get_assessment(conn, "111")
    assert stored.content == content
    assert stored.model == "test-model"
    assert stored.created_at.tzinfo is not None
    raw = conn.execute("SELECT content FROM assessments").fetchone()[0]
    assert "Sesión" in raw  # not escaped as \u00f3
    assert assessments.get_assessment(conn, "222") is None
    conn.close()

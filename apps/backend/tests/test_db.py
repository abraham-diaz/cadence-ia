import sqlite3

from conftest import write_sample_folder

from cadence_ia import db
from cadence_ia.ingest import ingest


def test_new_database_is_at_latest_version(tmp_path):
    conn = db.connect(tmp_path / "new.db")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    conn.close()


def test_upgrade_keeps_existing_sessions(tmp_path):
    db_file = tmp_path / "old.db"

    # A database from before workout types existed (schema version 1), with a session.
    old = sqlite3.connect(db_file)
    old.executescript(db.MIGRATIONS[0])
    old.execute(
        """INSERT INTO sessions VALUES ('111', '2026-10-01T10:00:00+02:00', 'Other', NULL,
               600, 100, 90, 120, 150, 6.0, 3, 2, '[[0, 90]]', '2026-10-01T12:00:00+00:00')"""
    )
    old.execute("INSERT INTO segments VALUES ('111', 0, 'work', 0, 60, 90, 140, 120, NULL, NULL)")
    old.execute("PRAGMA user_version = 1")
    old.commit()
    old.close()

    conn = db.connect(db_file)  # upgrades to the latest version
    assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
    row = db.get_session(conn, "111")
    assert row["hr_avg"] == 120 and row["type_id"] is None
    assert len(db.get_segments(conn, "111")) == 1
    type_id = db.create_type(conn, "Pierna", "strength")
    assert db.set_session_type(conn, "111", type_id)
    conn.close()

    conn = db.connect(db_file)  # reopening must not migrate again or lose data
    assert db.get_session(conn, "111")["type_name"] == "Pierna"
    conn.close()


def test_reingest_keeps_chosen_type(tmp_path):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    conn = db.connect(tmp_path / "test.db")
    ingest(conn, folder)
    type_id = db.create_type(conn, "Pierna", "strength")
    db.set_session_type(conn, "111", type_id)

    ingest(conn, folder, force=True)
    assert db.get_session(conn, "111")["type_name"] == "Pierna"
    conn.close()


def test_concurrent_first_open_migrates_once(tmp_path):
    """Several processes/requests opening a new database at once must not
    re-run or undo migrations (it used to leave the version behind)."""
    from concurrent.futures import ThreadPoolExecutor

    db_file = tmp_path / "race.db"

    def open_and_close(_):
        db.connect(db_file).close()

    for _ in range(5):
        if db_file.exists():
            db_file.unlink()
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(open_and_close, range(8)))
        conn = db.connect(db_file)
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
        conn.close()


def test_connection_can_be_used_from_another_thread(tmp_path):
    """FastAPI may open the connection (dependency) and run the endpoint in
    different worker threads; each request still uses it one step at a time."""
    from concurrent.futures import ThreadPoolExecutor

    conn = db.connect(tmp_path / "threads.db")
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(db.list_sessions, conn).result() == []
    conn.close()

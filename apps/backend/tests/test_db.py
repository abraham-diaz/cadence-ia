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

from datetime import datetime

import pytest
from conftest import sets_curve, write_sample_folder, write_tcx

from cadence_ia.cli import main
from cadence_ia.services.ingest import ingest
from cadence_ia.storage import sessions
from cadence_ia.storage.database import connect


@pytest.fixture
def folder(tmp_path):
    path = tmp_path / "tcx"
    path.mkdir()
    write_sample_folder(path)
    return path


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_ingest_adds_new_files_and_reports_broken(conn, folder):
    result = ingest(conn, folder)
    assert result.added == ["111", "222"]
    assert result.failed == ["broken.tcx"]
    assert sessions.session_ids(conn) == {"111", "222"}


def test_ingest_skips_files_already_stored(conn, folder):
    ingest(conn, folder)
    write_tcx(folder / "333.tcx", datetime.fromisoformat("2026-10-05T09:00:00+02:00"), sets_curve(1))

    result = ingest(conn, folder)
    assert result.added == ["333"]
    assert result.skipped == ["111", "222"]


def test_force_reanalyzes_without_duplicates(conn, folder):
    ingest(conn, folder)
    result = ingest(conn, folder, force=True)
    assert result.added == ["111", "222"]
    assert len(sessions.list_sessions(conn)) == 2
    segments = conn.execute("SELECT COUNT(*) FROM segments WHERE session_id = '111'").fetchone()[0]
    assert segments == len(sessions.get_segments(conn, "111"))


def test_stored_session_round_trip(conn, folder):
    ingest(conn, folder)
    session = sessions.get_session(conn, "222")
    assert session.start_time.isoformat() == "2026-10-03T18:00:00+02:00"  # offset kept
    assert session.device == "Test Device"
    assert session.sets == 3
    assert session.hr_min == 100 and session.hr_max == 140
    heart_rate = sessions.get_heart_rate(conn, "222")
    assert heart_rate[0] == (0.0, 100)
    assert len(heart_rate) == len(sets_curve(3))
    kinds = [s.kind for s in sessions.get_segments(conn, "222")]
    assert kinds[:2] == ["work", "rest"]


def test_cli_ingest(tmp_path, folder, capsys):
    db_file = tmp_path / "cli.db"
    exit_code = main(["ingest", "--data-dir", str(folder), "--db", str(db_file)])
    assert exit_code == 1  # the broken file counts as a failure
    assert "Added 2, already stored 0, failed 1" in capsys.readouterr().out

    main(["ingest", "--data-dir", str(folder), "--db", str(db_file)])
    assert "Added 0, already stored 2, failed 1" in capsys.readouterr().out


def test_cli_missing_folder(tmp_path, capsys):
    assert main(["ingest", "--data-dir", str(tmp_path / "nope"), "--db", str(tmp_path / "x.db")]) == 1
    assert "not found" in capsys.readouterr().out

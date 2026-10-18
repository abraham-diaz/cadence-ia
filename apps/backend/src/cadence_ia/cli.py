"""Command-line entry point.

    cadence-ia show <file.tcx>     summarize one workout
    cadence-ia ingest [--force]    store new TCX files in the database
"""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from cadence_ia import db
from cadence_ia.ingest import data_dir, ingest
from cadence_ia.metrics import analyze
from cadence_ia.tcx import parse_tcx


def _mmss(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def _avg(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def show(file: str) -> None:
    activity = parse_tcx(file)
    metrics = analyze(activity)

    print(f"Activity:    {activity.id} ({activity.sport})")
    print(f"Device:      {activity.device}")
    print(f"Duration:    {_mmss(metrics.duration_s)} (lap total {_mmss(activity.total_time_s)})")
    print(f"Calories:    {activity.calories} kcal")
    print(f"Trackpoints: {len(activity.trackpoints)}")
    print(f"Heart rate:  min {metrics.hr_min}  avg {metrics.hr_avg}  max {metrics.hr_max} bpm")
    print(f"Threshold:   {metrics.threshold_bpm} bpm (5% of avg HR)")
    print()

    print(f"{'#':>2}  {'type':<4}  {'start':>5}  {'dur':>5}  {'HR':>9}  {'avg':>3}  {'-30s':>4}  {'-60s':>4}")
    for i, s in enumerate(metrics.segments, 1):
        d30 = "" if s.drop_30s is None else s.drop_30s
        d60 = "" if s.drop_60s is None else s.drop_60s
        print(
            f"{i:>2}  {s.kind:<4}  {_mmss(s.start_s):>5}  {_mmss(s.duration_s):>5}  "
            f"{s.hr_start:>3}->{s.hr_end:<3}  {s.hr_avg:>3}  {d30:>4}  {d60:>4}"
        )
    print()

    sets, rests = metrics.sets, metrics.rests
    print(f"Sets:  {len(sets)}, avg {_mmss(_avg([s.duration_s for s in sets]) or 0)}")
    print(f"Rests: {len(rests)}, avg {_mmss(_avg([s.duration_s for s in rests]) or 0)}")
    drops = [s.drop_60s for s in rests if s.drop_60s is not None]
    if drops:
        print(f"Avg HR drop after 60 s of rest: {_avg(drops):.0f} bpm")


def run_ingest(folder: Path, db_file: Path, force: bool) -> int:
    if not folder.is_dir():
        print(f"Data folder not found: {folder}")
        return 1
    conn = db.connect(db_file)
    try:
        result = ingest(conn, folder, force=force)
    finally:
        conn.close()
    print(f"Folder:   {folder}")
    print(f"Database: {db_file}")
    print(f"Added {len(result.added)}, already stored {len(result.skipped)}, failed {len(result.failed)}")
    for name in result.failed:
        print(f"  failed: {name}")
    return 1 if result.failed else 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_dotenv()  # same settings as the API (CADENCE_DB, CADENCE_DATA_DIR...)

    parser = argparse.ArgumentParser(prog="cadence-ia", description="Analyze TCX workouts.")
    commands = parser.add_subparsers(dest="command", required=True)

    show_cmd = commands.add_parser("show", help="summarize one TCX file")
    show_cmd.add_argument("file", help="path to the .tcx file")

    ingest_cmd = commands.add_parser("ingest", help="store new TCX files in the database")
    ingest_cmd.add_argument("--data-dir", type=Path, default=None,
                            help="folder with .tcx files (default: $CADENCE_DATA_DIR)")
    ingest_cmd.add_argument("--db", type=Path, default=None,
                            help="SQLite file (default: $CADENCE_DB)")
    ingest_cmd.add_argument("--force", action="store_true",
                            help="analyze again files already stored")

    args = parser.parse_args(argv)
    if args.command == "show":
        show(args.file)
        return 0
    return run_ingest(args.data_dir or data_dir(), args.db or db.db_path(), args.force)


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line entry point: `cadence-ia <file.tcx>`."""

import argparse

from cadence_ia.tcx import parse_tcx


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a TCX workout.")
    parser.add_argument("file", help="path to the .tcx file")
    args = parser.parse_args()

    activity = parse_tcx(args.file)
    points = activity.trackpoints
    hrs = [tp.heart_rate for tp in points if tp.heart_rate is not None]
    minutes, seconds = divmod(int(activity.total_time_s), 60)

    print(f"Activity:    {activity.id} ({activity.sport})")
    print(f"Device:      {activity.device}")
    print(f"Duration:    {minutes} min {seconds:02d} s")
    print(f"Calories:    {activity.calories} kcal")
    print(f"Trackpoints: {len(points)}")
    if hrs:
        print(f"Heart rate:  min {min(hrs)}  avg {sum(hrs) / len(hrs):.0f}  max {max(hrs)} bpm")


if __name__ == "__main__":
    main()

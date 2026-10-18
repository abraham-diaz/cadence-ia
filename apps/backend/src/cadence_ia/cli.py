"""Command-line entry point: `cadence-ia <file.tcx>`."""

import argparse

from cadence_ia.metrics import analyze
from cadence_ia.tcx import parse_tcx


def _mmss(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def _avg(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a TCX workout.")
    parser.add_argument("file", help="path to the .tcx file")
    args = parser.parse_args()

    activity = parse_tcx(args.file)
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


if __name__ == "__main__":
    main()

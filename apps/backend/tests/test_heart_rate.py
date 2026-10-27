from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cadence_ia.domain.activity import Activity, Lap, Trackpoint
from cadence_ia.domain.heart_rate import (
    analyze,
    auto_threshold,
    curve,
    resample,
    smooth,
    turning_points,
)
from cadence_ia.importers.tcx import parse_tcx

SAMPLE = Path(__file__).parent / "data" / "8730973826466172504.tcx"
T0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def make_activity(samples: list[tuple[float, int]]) -> Activity:
    """Build an activity from (seconds, bpm) pairs."""
    points = [Trackpoint(T0 + timedelta(seconds=s), hr) for s, hr in samples]
    lap = Lap(T0, samples[-1][0], 0.0, 0, points)
    return Activity("test", "Other", None, [lap])


def test_curve_starts_at_zero_and_skips_points_without_hr():
    activity = make_activity([(5, 100), (7, 110), (9, 120)])
    activity.laps[0].trackpoints[1].heart_rate = None
    assert curve(activity.trackpoints) == [(0.0, 100), (4.0, 120)]
    assert curve([]) == []


def test_resample_interpolates_irregular_points():
    activity = make_activity([(0, 100), (2, 110), (5, 110)])
    assert resample(activity.trackpoints) == [100, 105, 110, 110, 110, 110]


def test_resample_without_heart_rate_raises():
    activity = make_activity([(0, 100)])
    activity.laps[0].trackpoints[0].heart_rate = None
    with pytest.raises(ValueError):
        resample(activity.trackpoints)


def test_smooth_centered_average():
    assert smooth([0, 3, 6, 9], window=3) == [1.5, 3, 6, 7.5]


def test_turning_points_ignores_small_wiggles():
    values = [100, 102, 101, 110, 108, 120, 100, 103, 101, 115]
    assert turning_points(values, threshold=7) == [
        (0, "valley"),
        (5, "peak"),
        (6, "valley"),
    ]


def test_auto_threshold_scales_with_average_hr():
    assert auto_threshold(140) == pytest.approx(7)
    assert auto_threshold(100) == pytest.approx(5)
    assert auto_threshold(60) == 4  # never below the noise floor


def test_same_workout_at_lower_hr_finds_same_sets():
    # Same shape (3 sets) shifted 40 bpm lower: detection must not change.
    shape = [0, 20, 40, 20, 0, 20, 40, 20, 0, 20, 40, 20, 0, 20]
    high = make_activity([(i * 30, 120 + v) for i, v in enumerate(shape)])
    low = make_activity([(i * 30, 80 + v) for i, v in enumerate(shape)])
    a, b = analyze(high), analyze(low)
    assert len(a.sets) == len(b.sets) == 3
    assert b.threshold_bpm < a.threshold_bpm


def test_analyze_detects_sets_and_rests():
    # Three sets: 60 s rising 100 -> 140, then 90 s falling back to 100.
    samples = []
    t = 0
    for _ in range(3):
        for i in range(60):
            samples.append((t, 100 + round(40 * i / 60)))
            t += 1
        for i in range(90):
            samples.append((t, 140 - round(40 * i / 90)))
            t += 1
    samples.append((t, 140))  # final rise so the last valley is confirmed

    metrics = analyze(make_activity(samples), smooth_window=1)

    assert [s.kind for s in metrics.segments] == ["work", "rest"] * 3
    assert all(55 <= s.duration_s <= 65 for s in metrics.sets)
    assert all(85 <= s.duration_s <= 95 for s in metrics.rests)
    assert all(s.drop_30s is not None and s.drop_60s > s.drop_30s for s in metrics.rests)
    assert all(s.drop_30s is None for s in metrics.sets)
    assert metrics.hr_min == 100
    assert metrics.hr_max == 140


@pytest.mark.skipif(not SAMPLE.exists(), reason="private sample TCX not present")
def test_analyze_sample_strength_session():
    metrics = analyze(parse_tcx(SAMPLE))
    assert metrics.hr_min == 95
    assert metrics.hr_max == 166
    assert 8 <= len(metrics.sets) <= 12
    kinds = [s.kind for s in metrics.segments]
    assert all(a != b for a, b in zip(kinds, kinds[1:]))  # work/rest alternate


@pytest.mark.parametrize("name", ["8730973826466172504.tcx", "4529926065076776824.tcx"])
def test_recovery_is_never_negative(name):
    """A rest runs from a peak to the next valley, so HR can't end above where it started.
    The frontend relies on it to show recovery as "↓6"."""
    path = SAMPLE.parent / name
    if not path.exists():
        pytest.skip(f"{name} not available")
    rests = analyze(parse_tcx(path)).rests
    drops = [d for r in rests for d in (r.drop_30s, r.drop_60s) if d is not None]
    assert drops and min(drops) >= 0

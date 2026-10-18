from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cadence_ia.tcx import parse_tcx

SAMPLE = Path(__file__).parent / "data" / "8730973826466172504.tcx"
TZ = timezone(timedelta(hours=2))


@pytest.fixture(scope="module")
def activity():
    return parse_tcx(SAMPLE)


def test_activity_metadata(activity):
    assert activity.sport == "Other"
    assert activity.device == "Fitbit Air"
    assert len(activity.laps) == 1
    assert activity.total_time_s == 1772.0
    assert activity.calories == 267
    assert activity.laps[0].distance_m == 0.0


def test_trackpoints(activity):
    points = activity.trackpoints
    assert len(points) == 790
    assert all(tp.heart_rate is not None for tp in points)

    assert points[0].time == datetime(2026, 10, 15, 14, 27, 17, tzinfo=TZ)
    assert points[0].heart_rate == 96
    assert points[-1].time == datetime(2026, 10, 15, 14, 56, 50, tzinfo=TZ)
    assert points[-1].heart_rate == 154


def test_heart_rate_range(activity):
    hrs = [tp.heart_rate for tp in activity.trackpoints]
    assert min(hrs) == 95
    assert max(hrs) == 166


def test_missing_activity_raises(tmp_path):
    empty = tmp_path / "empty.tcx"
    empty.write_text(
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/'
        'TrainingCenterDatabase/v2"><Activities/></TrainingCenterDatabase>'
    )
    with pytest.raises(ValueError):
        parse_tcx(empty)

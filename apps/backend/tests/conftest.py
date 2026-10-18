from datetime import datetime, timedelta

NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"


def write_tcx(path, start: datetime, bpms: list[int]) -> None:
    """Write a minimal synthetic TCX with one trackpoint every 2 s."""
    points = "".join(
        f"<Trackpoint><Time>{(start + timedelta(seconds=2 * i)).isoformat()}</Time>"
        f"<HeartRateBpm><Value>{hr}</Value></HeartRateBpm></Trackpoint>"
        for i, hr in enumerate(bpms)
    )
    path.write_text(
        f'<TrainingCenterDatabase xmlns="{NS}"><Activities><Activity Sport="Other">'
        f"<Id>{start.isoformat()}</Id>"
        f'<Lap StartTime="{start.isoformat()}"><TotalTimeSeconds>{2 * len(bpms)}</TotalTimeSeconds>'
        f"<DistanceMeters>0</DistanceMeters><Calories>100</Calories>"
        f"<Track>{points}</Track></Lap>"
        f"<Creator><Name>Test Device</Name></Creator>"
        f"</Activity></Activities></TrainingCenterDatabase>"
    )


def sets_curve(n_sets: int) -> list[int]:
    """HR rising 100 -> 140 over 60 s, then falling back over 60 s, n times."""
    up = [100 + i * 4 // 3 for i in range(30)]
    down = [140 - i * 4 // 3 for i in range(30)]
    return (up + down) * n_sets + [140] * 10


def write_sample_folder(folder) -> None:
    """Two valid workouts (2 and 3 sets) plus one broken file."""
    write_tcx(folder / "111.tcx", datetime.fromisoformat("2026-10-01T10:00:00+02:00"), sets_curve(2))
    write_tcx(folder / "222.tcx", datetime.fromisoformat("2026-10-03T18:00:00+02:00"), sets_curve(3))
    (folder / "broken.tcx").write_text("not xml")

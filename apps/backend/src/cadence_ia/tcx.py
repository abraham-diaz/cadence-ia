"""Read Fitbit TCX workouts into plain Python objects."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

NS = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}


@dataclass
class Trackpoint:
    time: datetime
    heart_rate: int | None


@dataclass
class Lap:
    start_time: datetime
    total_time_s: float
    distance_m: float
    calories: int
    trackpoints: list[Trackpoint] = field(default_factory=list)


@dataclass
class Activity:
    id: str
    sport: str
    device: str | None
    laps: list[Lap] = field(default_factory=list)

    @property
    def trackpoints(self) -> list[Trackpoint]:
        return [tp for lap in self.laps for tp in lap.trackpoints]

    @property
    def total_time_s(self) -> float:
        return sum(lap.total_time_s for lap in self.laps)

    @property
    def calories(self) -> int:
        return sum(lap.calories for lap in self.laps)


def _text(elem: ET.Element, path: str) -> str | None:
    found = elem.find(path, NS)
    return found.text.strip() if found is not None and found.text else None


def _parse_trackpoint(elem: ET.Element) -> Trackpoint:
    hr = _text(elem, "tcx:HeartRateBpm/tcx:Value")
    return Trackpoint(
        time=datetime.fromisoformat(_text(elem, "tcx:Time")),
        heart_rate=int(hr) if hr is not None else None,
    )


def _parse_lap(elem: ET.Element) -> Lap:
    return Lap(
        start_time=datetime.fromisoformat(elem.get("StartTime")),
        total_time_s=float(_text(elem, "tcx:TotalTimeSeconds") or 0),
        distance_m=float(_text(elem, "tcx:DistanceMeters") or 0),
        calories=int(_text(elem, "tcx:Calories") or 0),
        trackpoints=[
            _parse_trackpoint(tp)
            for tp in elem.findall("tcx:Track/tcx:Trackpoint", NS)
        ],
    )


def parse_tcx(path: str | Path) -> Activity:
    """Parse the first activity of a TCX file."""
    root = ET.parse(path).getroot()
    activity = root.find("tcx:Activities/tcx:Activity", NS)
    if activity is None:
        raise ValueError(f"No activity found in {path}")

    return Activity(
        id=_text(activity, "tcx:Id"),
        sport=activity.get("Sport", "Other"),
        device=_text(activity, "tcx:Creator/tcx:Name"),
        laps=[_parse_lap(lap) for lap in activity.findall("tcx:Lap", NS)],
    )

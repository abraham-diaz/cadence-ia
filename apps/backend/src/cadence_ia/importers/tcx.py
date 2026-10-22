import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from cadence_ia.domain.activity import Activity, Lap, Trackpoint

NS = {"tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}


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

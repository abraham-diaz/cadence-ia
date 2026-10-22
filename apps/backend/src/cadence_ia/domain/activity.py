"""A workout as plain Python objects, whatever file format it came from."""

from dataclasses import dataclass, field
from datetime import datetime


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

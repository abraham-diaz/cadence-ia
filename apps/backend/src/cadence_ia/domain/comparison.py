"""Compare a session with the previous sessions of the same workout type."""

from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from datetime import datetime

COMPARE_LAST = 5


@dataclass(frozen=True)
class Stats:
    duration_s: float | None
    hr_avg: float | None
    hr_max: float | None
    # Strength only:
    sets: float | None
    avg_rest_s: float | None
    recovery_30s: float | None  # average HR drop 30 s into a rest
    recovery_60s: float | None

    def without_strength(self) -> "Stats":
        return replace(self, **dict.fromkeys(STRENGTH_ONLY))


STAT_FIELDS = tuple(f.name for f in fields(Stats))
STRENGTH_ONLY = ("sets", "avg_rest_s", "recovery_30s", "recovery_60s")


@dataclass(frozen=True)
class HistoryEntry:
    """One session's stats, as listed in its workout type's history."""

    id: str
    start_time: datetime
    stats: Stats


@dataclass(frozen=True)
class Baseline:
    sessions: int  # how many previous sessions the averages come from
    stats: Stats


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def baseline(
    history: Sequence[HistoryEntry], session_id: str, last: int = COMPARE_LAST
) -> Baseline | None:
    """Average of the `last` sessions before `session_id` (history is oldest first).
    Each field only counts the sessions that have it, so a missing value doesn't drag it down."""
    ids = [entry.id for entry in history]
    if session_id not in ids:
        return None
    previous = history[max(0, ids.index(session_id) - last) : ids.index(session_id)]
    if not previous:
        return None

    averages = {
        name: _mean([v for e in previous if (v := getattr(e.stats, name)) is not None])
        for name in STAT_FIELDS
    }
    return Baseline(sessions=len(previous), stats=Stats(**averages))

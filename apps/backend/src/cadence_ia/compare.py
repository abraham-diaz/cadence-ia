"""Compare a session with the previous sessions of the same workout type."""

from collections.abc import Mapping, Sequence

COMPARE_LAST = 5

STAT_FIELDS = (
    "duration_s",
    "hr_avg",
    "hr_max",
    "sets",
    "avg_rest_s",
    "recovery_30s",
    "recovery_60s",
)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def baseline(
    history: Sequence[Mapping], session_id: str, last: int = COMPARE_LAST
) -> dict | None:
    """Average of the `last` sessions before `session_id` in `history` (oldest first).

    Each field is averaged over the sessions that have a value for it, so a
    session with no 60 s recovery doesn't drag that average down. Returns None
    when there is nothing earlier to compare with.
    """
    ids = [entry["id"] for entry in history]
    if session_id not in ids:
        return None
    previous = history[max(0, ids.index(session_id) - last) : ids.index(session_id)]
    if not previous:
        return None

    result: dict = {"sessions": len(previous)}
    for name in STAT_FIELDS:
        result[name] = _mean([e[name] for e in previous if e[name] is not None])
    return result

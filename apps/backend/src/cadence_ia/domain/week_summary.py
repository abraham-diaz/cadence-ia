"""The user's last 7 days, written as a chat message they can send to the coach."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from cadence_ia.domain.session import Session

DAYS = 7
WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
UNCLASSIFIED = "Sin clasificar"


@dataclass
class TypeTotals:
    name: str
    sessions: int = 0
    duration_s: int = 0
    weekdays: list[str] = field(default_factory=list)  # in order, no repeats


def week_summary(sessions: Sequence[Session], today: date) -> str:
    start = today - timedelta(days=DAYS - 1)
    recent = sorted(
        (s for s in sessions if start <= s.start_time.date() <= today), key=lambda s: s.start_time
    )
    title = f"Mis últimos entrenos de la semana ({_date_range(start, today)})"
    if not recent:
        return f"{title}: no he entrenado."

    totals: dict[str, TypeTotals] = {}
    for session in recent:
        name = session.workout_type.name if session.workout_type else UNCLASSIFIED
        entry = totals.setdefault(name, TypeTotals(name))
        entry.sessions += 1
        entry.duration_s += session.duration_s
        weekday = WEEKDAYS[session.start_time.weekday()]
        if weekday not in entry.weekdays:
            entry.weekdays.append(weekday)

    # Most minutes first; unclassified always last.
    ordered = sorted(totals.values(), key=lambda t: (t.name == UNCLASSIFIED, -t.duration_s))
    lines = [f"{title}:"]
    lines += [
        f"- {t.name}: {_sessions(t.sessions)}, {_minutes(t.duration_s)} ({_join(t.weekdays)})"
        for t in ordered
    ]
    total_s = sum(s.duration_s for s in recent)
    lines.append(f"Total: {_sessions(len(recent))}, {_minutes(total_s)}")
    return "\n".join(lines)


def _sessions(n: int) -> str:
    return f"{n} sesión" if n == 1 else f"{n} sesiones"


def _minutes(seconds: int) -> str:
    return f"{round(seconds / 60)} min"


def _join(words: list[str]) -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} y {words[-1]}"


def _date_range(start: date, end: date) -> str:
    if start.month == end.month:
        return f"{start.day}-{end.day} {MONTHS[end.month - 1]}"
    return f"{start.day} {MONTHS[start.month - 1]} - {end.day} {MONTHS[end.month - 1]}"

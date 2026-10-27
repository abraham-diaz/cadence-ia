"""What the plan asked for in a week, day by day, against what was actually trained."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from cadence_ia.domain.plan import Plan, PlanDay
from cadence_ia.domain.session import Session

# done: every planned workout has a session of its type. partial: trained, but not all of it.
# missed / pending: planned and nothing trained, before / from today. extra: trained off-plan.
DayStatus = Literal["done", "partial", "missed", "pending", "rest", "extra"]


@dataclass(frozen=True)
class PlannedWorkout:
    day: PlanDay
    done: bool


@dataclass(frozen=True)
class DayProgress:
    date: date
    status: DayStatus
    planned: tuple[PlannedWorkout, ...]
    sessions: tuple[Session, ...]


@dataclass(frozen=True)
class WeekProgress:
    start: date  # Monday
    plan: Plan | None  # the one in force on the week's last day so far
    plan_week: int | None
    days: tuple[DayProgress, ...]

    @property
    def planned_sessions(self) -> int:
        return sum(len(d.planned) for d in self.days)

    @property
    def done_sessions(self) -> int:
        return sum(p.done for d in self.days for p in d.planned)

    @property
    def planned_minutes(self) -> int:
        return sum(p.day.minutes for d in self.days for p in d.planned)

    @property
    def done_minutes(self) -> int:
        return round(sum(s.duration_s for d in self.days for s in d.sessions) / 60)


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def plan_on(plans: Sequence[Plan], day: date) -> Plan | None:
    """The plan in force that day: the last version saved on or before it."""
    saved = [p for p in plans if p.created_at.date() <= day]
    return max(saved, key=lambda p: (p.created_at, p.id), default=None)


def week_progress(
    plans: Sequence[Plan], sessions: Sequence[Session], today: date, start: date | None = None
) -> WeekProgress:
    """Each day is measured against the plan in force that day, so editing
    the plan never turns past weeks into failures."""
    start = monday_of(start or today)
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        trained = tuple(
            sorted((s for s in sessions if s.start_time.date() == day), key=lambda s: s.start_time)
        )
        plan = plan_on(plans, day)
        planned = (
            [d for d in plan.days if d.week == plan.week_on(day) and d.weekday == offset]
            if plan
            else []
        )
        days.append(_day(day, planned, trained, today))

    shown = plan_on(plans, min(today, start + timedelta(days=6)))
    return WeekProgress(
        start=start,
        plan=shown,
        plan_week=shown.week_on(start) if shown else None,
        days=tuple(days),
    )


def _day(day: date, planned: list[PlanDay], trained: tuple[Session, ...], today: date) -> DayProgress:
    unmatched = [s.workout_type.id for s in trained if s.workout_type]
    workouts = []
    for plan_day in planned:
        type_id = plan_day.workout_type.id if plan_day.workout_type else None
        done = type_id in unmatched
        if done:
            unmatched.remove(type_id)  # one session counts for one planned workout
        workouts.append(PlannedWorkout(plan_day, done))

    if not planned:
        status: DayStatus = "extra" if trained else "rest"
    elif all(w.done for w in workouts):
        status = "done"
    elif trained:
        status = "partial"
    else:
        status = "missed" if day < today else "pending"
    return DayProgress(date=day, status=status, planned=tuple(workouts), sessions=trained)

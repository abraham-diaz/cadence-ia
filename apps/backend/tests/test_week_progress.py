from datetime import date, datetime, timezone

from test_week_summary import FRONTON, LEG, session

from cadence_ia.domain.plan import Plan, PlanDay
from cadence_ia.domain.week_progress import plan_on, week_progress
from cadence_ia.domain.workout_type import WorkoutType

WALK = WorkoutType(id=3, name="Caminata", category="cardio")
TODAY = date(2026, 10, 22)  # Thursday; the week starts on Monday the 19th


def day(weekday: int, workout_type: WorkoutType | None, minutes: int = 40, week: int = 0):
    return PlanDay(week, weekday, workout_type, minutes, note=None, exercises=())


def plan(
    *days: PlanDay,
    weeks: int = 1,
    cycle_start=date(2026, 10, 12),
    created=date(2026, 10, 1),
    id=1,
    title="Plan",
):
    return Plan(
        id=id,
        title=title,
        weeks=weeks,
        cycle_start=cycle_start,
        created_at=datetime(created.year, created.month, created.day, tzinfo=timezone.utc),
        days=days,
    )


def statuses(progress) -> list[str]:
    return [d.status for d in progress.days]


def test_each_day_against_the_plan():
    current = plan(day(0, LEG), day(1, WALK), day(2, LEG), day(4, LEG), day(5, FRONTON))
    trained = [
        session("2026-10-19T18:00:00", 35, LEG),  # Monday, as planned
        session("2026-10-21T18:00:00", 30, None),  # Wednesday, not classified
        session("2026-10-22T10:00:00", 20, WALK),  # Thursday, off-plan
    ]
    progress = week_progress([current], trained, TODAY)

    assert progress.start == date(2026, 10, 19)
    assert statuses(progress) == ["done", "missed", "partial", "extra", "pending", "pending", "rest"]
    assert (progress.done_sessions, progress.planned_sessions) == (1, 5)
    assert (progress.done_minutes, progress.planned_minutes) == (85, 200)


def test_two_workouts_on_one_day_need_two_sessions():
    current = plan(day(0, LEG), day(0, WALK))
    one = week_progress([current], [session("2026-10-19T18:00:00", 35, LEG)], TODAY)
    assert one.days[0].status == "partial"
    assert [p.done for p in one.days[0].planned] == [True, False]

    both = [session("2026-10-19T18:00:00", 35, LEG), session("2026-10-19T19:00:00", 20, WALK)]
    assert week_progress([current], both, TODAY).days[0].status == "done"


def test_one_session_counts_once():
    current = plan(day(0, LEG), day(0, LEG))
    progress = week_progress([current], [session("2026-10-19T18:00:00", 35, LEG)], TODAY)
    assert progress.done_sessions == 1


def test_uses_the_week_of_the_cycle():
    # Cycle started on the 12th: the 19th is week B.
    current = plan(day(0, LEG, week=0), day(0, WALK, week=1), weeks=2)
    progress = week_progress([current], [], TODAY)
    assert progress.plan_week == 1
    assert [p.day.workout_type for p in progress.days[0].planned] == [WALK]


def test_days_before_the_plan_was_saved_ask_for_nothing():
    current = plan(day(0, LEG), day(4, LEG), created=date(2026, 10, 21))
    progress = week_progress([current], [session("2026-10-19T18:00:00", 35, LEG)], TODAY)
    assert statuses(progress)[0] == "extra"
    assert progress.planned_sessions == 1


def test_without_a_plan_only_shows_what_was_trained():
    progress = week_progress([], [session("2026-10-20T11:00:00", 57, FRONTON)], TODAY)
    assert statuses(progress) == ["rest", "extra"] + ["rest"] * 5
    assert progress.plan_week is None
    assert progress.planned_sessions == 0


# Past weeks and plan versions


def test_a_past_week_by_any_of_its_days():
    current = plan(day(0, LEG), day(3, WALK))
    trained = [session("2026-10-12T18:00:00", 35, LEG), session("2026-10-19T18:00:00", 35, LEG)]
    progress = week_progress([current], trained, TODAY, start=date(2026, 10, 15))

    assert progress.start == date(2026, 10, 12)
    assert statuses(progress)[0] == "done"
    assert statuses(progress)[3] == "missed"  # in the past, even if it's Thursday today
    assert progress.done_minutes == 35


def test_each_day_uses_the_plan_in_force_that_day():
    old = plan(day(0, LEG), day(2, LEG), created=date(2026, 10, 1), id=1, title="Viejo")
    new = plan(day(0, WALK), day(2, WALK), created=date(2026, 10, 21), id=2, title="Nuevo")
    progress = week_progress([old, new], [session("2026-10-19T18:00:00", 35, LEG)], TODAY)

    # Monday still counts against the old plan; Wednesday, against the new one.
    assert [p.day.workout_type for p in progress.days[0].planned] == [LEG]
    assert statuses(progress)[0] == "done"
    assert [p.day.workout_type for p in progress.days[2].planned] == [WALK]
    assert progress.plan.title == "Nuevo"


def test_a_past_week_shows_the_plan_it_had():
    old = plan(day(0, LEG), created=date(2026, 10, 1), id=1, title="Viejo")
    new = plan(day(0, WALK), created=date(2026, 10, 21), id=2, title="Nuevo")
    progress = week_progress([old, new], [], TODAY, start=date(2026, 10, 12))
    assert progress.plan.title == "Viejo"


def test_weeks_before_the_first_plan_ask_for_nothing():
    current = plan(day(0, LEG), created=date(2026, 10, 15))
    progress = week_progress([current], [], TODAY, start=date(2026, 10, 5))
    assert progress.plan is None
    assert progress.planned_sessions == 0


def test_plan_on_picks_the_last_version_saved_by_then():
    first = plan(created=date(2026, 10, 1), id=1)
    same_day = plan(created=date(2026, 10, 1), id=2)
    later = plan(created=date(2026, 10, 20), id=3)
    versions = [first, same_day, later]

    assert plan_on(versions, date(2026, 9, 30)) is None
    assert plan_on(versions, date(2026, 10, 1)) is same_day
    assert plan_on(versions, date(2026, 10, 19)) is same_day
    assert plan_on(versions, date(2026, 10, 20)) is later

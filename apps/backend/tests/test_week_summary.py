from datetime import date, datetime

from cadence_ia.domain.session import Session
from cadence_ia.domain.week_summary import week_summary
from cadence_ia.domain.workout_type import WorkoutType

LEG = WorkoutType(id=1, name="Pierna", category="strength")
FRONTON = WorkoutType(id=2, name="Frontón", category="cardio")
TODAY = date(2026, 10, 22)  # a Thursday


def session(start: str, minutes: int, workout_type: WorkoutType | None) -> Session:
    return Session(
        id=start,
        start_time=datetime.fromisoformat(f"{start}+02:00"),
        sport="Other",
        device=None,
        duration_s=minutes * 60,
        calories=0,
        hr_min=90,
        hr_avg=130,
        hr_max=160,
        threshold_bpm=6.5,
        sets=None,
        rests=None,
        workout_type=workout_type,
    )


def test_groups_by_type_with_minutes_and_days():
    sessions = [
        session("2026-10-19T18:00:00", 35, LEG),  # Monday
        session("2026-10-21T10:00:00", 30, None),  # Wednesday
        session("2026-10-17T11:00:00", 57, FRONTON),  # Saturday
        session("2026-10-22T18:00:00", 36, LEG),  # Thursday
    ]
    assert week_summary(sessions, TODAY) == (
        "Mis últimos entrenos de la semana (16-22 oct):\n"
        "- Pierna: 2 sesiones, 71 min (lunes y jueves)\n"
        "- Frontón: 1 sesión, 57 min (sábado)\n"
        "- Sin clasificar: 1 sesión, 30 min (miércoles)\n"
        "Total: 4 sesiones, 158 min"
    )


def test_only_the_last_seven_days_count():
    sessions = [
        session("2026-10-15T18:00:00", 40, LEG),  # 8 days ago
        session("2026-10-16T18:00:00", 40, LEG),  # 7 days counting today
        session("2026-10-23T18:00:00", 40, LEG),  # tomorrow
    ]
    assert "Total: 1 sesión, 40 min" in week_summary(sessions, TODAY)


def test_two_sessions_on_the_same_day_name_it_once():
    sessions = [
        session("2026-10-20T09:00:00", 20, LEG),
        session("2026-10-20T19:00:00", 20, LEG),
        session("2026-10-21T19:00:00", 20, LEG),
        session("2026-10-22T19:00:00", 20, LEG),
    ]
    assert "(martes, miércoles y jueves)" in week_summary(sessions, TODAY)


def test_empty_week():
    assert week_summary([], TODAY) == "Mis últimos entrenos de la semana (16-22 oct): no he entrenado."


def test_range_across_months():
    assert week_summary([], date(2026, 11, 2)).startswith("Mis últimos entrenos de la semana (27 oct - 2 nov)")

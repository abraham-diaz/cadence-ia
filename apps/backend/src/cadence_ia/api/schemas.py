from dataclasses import asdict
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cadence_ia.domain.assessment import Assessment
from cadence_ia.domain.exercise import MUSCLE_NAMES, CatalogExercise, Muscle, MuscleSuggestion
from cadence_ia.domain.plan import PlanDay
from cadence_ia.domain.session import Session
from cadence_ia.domain.week_progress import DayStatus, WeekProgress
from cadence_ia.domain.workout_type import Category, WorkoutTypeUsage
from cadence_ia.llm.assessor import AssessmentContent
from cadence_ia.services import plans, sessions
from cadence_ia.services.errors import ErrorCode

class WorkoutTypeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=60)
    category: Category
    muscles: list[Muscle] = []


class SessionTypeIn(BaseModel):
    workout_type_id: int | None  # None clears the type


class WorkoutTypeRef(BaseModel):
    id: int
    name: str
    category: Category


class WorkoutTypeOut(WorkoutTypeRef):
    session_count: int
    muscles: list[Muscle]


class MuscleOut(BaseModel):
    id: Muscle
    name: str


class CatalogExerciseOut(BaseModel):
    id: int
    name: str
    image_url: str | None
    license: str
    author: str | None


class ExerciseDetailOut(CatalogExerciseOut):
    description: str | None  # one paragraph per line
    primary_muscles: list[MuscleOut]
    secondary_muscles: list[MuscleOut]


class MuscleSuggestionOut(BaseModel):
    muscle: MuscleOut
    exercises: list[CatalogExerciseOut]


class SegmentOut(BaseModel):
    kind: Literal["work", "rest"]
    start_s: int
    end_s: int
    duration_s: int
    hr_start: int
    hr_end: int
    hr_avg: int
    drop_30s: int | None
    drop_60s: int | None


class HeartRatePoint(BaseModel):
    t: float  # seconds since the first trackpoint
    hr: int


class SessionSummary(BaseModel):
    id: str
    start_time: datetime
    sport: str
    duration_s: int
    calories: int
    hr_min: int
    hr_avg: int
    hr_max: int
    workout_type: WorkoutTypeRef | None
    # Only for strength sessions.
    sets: int | None
    rests: int | None


class SessionStats(BaseModel):
    duration_s: float | None
    hr_avg: float | None
    hr_max: float | None
    # Strength only:
    sets: float | None
    avg_rest_s: float | None
    recovery_30s: float | None  # average HR drop 30 s into a rest
    recovery_60s: float | None


class HistoryPoint(SessionStats):
    id: str
    start_time: datetime


class Comparison(SessionStats):
    sessions: int  # how many previous sessions the averages come from


class AssessmentOut(AssessmentContent):
    model: str
    created_at: datetime


class SessionDetail(SessionSummary):
    device: str | None
    threshold_bpm: float
    segments: list[SegmentOut]
    heart_rate: list[HeartRatePoint]
    stats: SessionStats
    # Average of the previous sessions of the same type; None if there are none.
    comparison: Comparison | None
    # Every session of the same type, oldest first (includes this one).
    history: list[HistoryPoint]
    assessment: AssessmentOut | None


class ChatMessageIn(BaseModel):
    role: Literal["user", "model"]
    text: str = Field(min_length=1, max_length=4000)


class ConversationIn(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1, max_length=60)


class PlanChatIn(ConversationIn):

    @field_validator("messages")
    @classmethod
    def ends_with_user(cls, messages: list[ChatMessageIn]) -> list[ChatMessageIn]:
        if messages[-1].role != "user":
            raise ValueError("the last message must be the user's")
        return messages


class PlanChatOut(BaseModel):
    reply: str


class WeekSummaryOut(BaseModel):
    text: str


class ExerciseOut(BaseModel):
    name: str
    sets: int | None
    reps: str | None  # text: "10-12", "30 s"...
    catalog_id: int | None  # the catalog entry, with how it's done; None if it isn't there
    image_url: str | None


class ExerciseIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    sets: int | None = Field(default=None, ge=1, le=20)
    reps: str | None = Field(default=None, max_length=40)
    catalog_id: int | None = None


class ProposedDayOut(BaseModel):
    week: int
    weekday: int  # 0 = Monday
    type_name: str
    category: Category
    workout_type_id: int | None  # the user's type with that name; None if it's new
    minutes: int
    note: str | None
    exercises: list[ExerciseOut]


class PlanProposalOut(BaseModel):
    title: str
    weeks: int
    days: list[ProposedDayOut]


class PlanDayIn(BaseModel):
    week: int = Field(ge=0)
    weekday: int = Field(ge=0, le=6)
    # Exactly one of the two: an existing type, or one to create.
    workout_type_id: int | None = None
    new_type: WorkoutTypeIn | None = None
    minutes: int = Field(ge=1, le=600)
    note: str | None = Field(default=None, max_length=500)
    exercises: list[ExerciseIn] = Field(default=[], max_length=30)

    @model_validator(mode="after")
    def one_type(self) -> "PlanDayIn":
        if (self.workout_type_id is None) == (self.new_type is None):
            raise ValueError("give either workout_type_id or new_type")
        return self


class PlanIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=80)
    weeks: int = Field(ge=1, le=4)
    current_week: int = Field(ge=0)  # which week of the cycle this one is
    days: list[PlanDayIn] = Field(min_length=1, max_length=60)


class PlanDayOut(BaseModel):
    week: int
    weekday: int
    workout_type: WorkoutTypeRef | None  # None if the type was deleted afterwards
    minutes: int
    note: str | None
    exercises: list[ExerciseOut]


class PlanOut(BaseModel):
    id: int
    title: str
    weeks: int
    cycle_start: date  # the Monday the first week started
    created_at: datetime
    current_week: int
    days: list[PlanDayOut]


class PlannedWorkoutOut(PlanDayOut):
    done: bool  # a session of this type was trained that day


class DayProgressOut(BaseModel):
    date: date
    status: DayStatus
    planned: list[PlannedWorkoutOut]
    session_ids: list[str]


class WeekProgressOut(BaseModel):
    start: date  # Monday
    plan_title: str | None  # the plan in force that week; null if there was none
    plan_week: int | None
    plan_weeks: int | None
    planned_sessions: int
    done_sessions: int
    planned_minutes: int
    done_minutes: int  # every session of the week counts, planned or not
    days: list[DayProgressOut]


class ErrorOut(BaseModel):
    detail: str
    code: ErrorCode  # stable: the frontend shows a message for each code


def workout_type_out(usage: WorkoutTypeUsage) -> WorkoutTypeOut:
    return WorkoutTypeOut(
        **asdict(usage.workout_type), session_count=usage.session_count, muscles=list(usage.muscles)
    )


def muscle_out(muscle: Muscle) -> MuscleOut:
    return MuscleOut(id=muscle, name=MUSCLE_NAMES[muscle])


def catalog_exercise_out(e: CatalogExercise) -> CatalogExerciseOut:
    return CatalogExerciseOut(
        id=e.id, name=e.name, image_url=e.image_url, license=e.license, author=e.author
    )


def exercise_detail_out(e: CatalogExercise) -> ExerciseDetailOut:
    return ExerciseDetailOut(
        **catalog_exercise_out(e).model_dump(),
        description=e.description,
        primary_muscles=[muscle_out(m) for m in e.primary_muscles],
        secondary_muscles=[muscle_out(m) for m in e.secondary_muscles],
    )


def muscle_suggestion_out(suggestion: MuscleSuggestion) -> MuscleSuggestionOut:
    return MuscleSuggestionOut(
        muscle=muscle_out(suggestion.muscle),
        exercises=[catalog_exercise_out(e) for e in suggestion.exercises],
    )


def session_summary(session: Session) -> SessionSummary:
    workout_type = session.workout_type
    return SessionSummary(
        id=session.id,
        start_time=session.start_time,
        sport=session.sport,
        duration_s=session.duration_s,
        calories=session.calories,
        hr_min=session.hr_min,
        hr_avg=session.hr_avg,
        hr_max=session.hr_max,
        workout_type=WorkoutTypeRef(**asdict(workout_type)) if workout_type else None,
        sets=session.sets,
        rests=session.rests,
    )


def assessment_out(assessment: Assessment) -> AssessmentOut:
    return AssessmentOut(
        **assessment.content, model=assessment.model, created_at=assessment.created_at
    )


def session_detail(detail: sessions.SessionDetail) -> SessionDetail:
    session, comparison = detail.session, detail.comparison
    return SessionDetail(
        **session_summary(session).model_dump(),
        device=session.device,
        threshold_bpm=session.threshold_bpm,
        segments=[SegmentOut(**asdict(s), duration_s=s.duration_s) for s in detail.segments],
        heart_rate=[HeartRatePoint(t=t, hr=hr) for t, hr in detail.heart_rate],
        stats=SessionStats(**asdict(detail.stats)),
        comparison=(
            Comparison(sessions=comparison.sessions, **asdict(comparison.stats))
            if comparison
            else None
        ),
        history=[
            HistoryPoint(id=h.id, start_time=h.start_time, **asdict(h.stats))
            for h in detail.history
        ],
        assessment=assessment_out(detail.assessment) if detail.assessment else None,
    )


def proposal_out(proposal: plans.Proposal) -> PlanProposalOut:
    return PlanProposalOut(
        title=proposal.title,
        weeks=proposal.weeks,
        days=[
            ProposedDayOut(
                **{k: v for k, v in asdict(day).items() if k != "exercises"},
                exercises=[ExerciseOut(**asdict(e)) for e in day.exercises],
            )
            for day in proposal.days
        ],
    )


def plan_out(current: plans.CurrentPlan) -> PlanOut:
    plan = current.plan
    return PlanOut(
        id=plan.id,
        title=plan.title,
        weeks=plan.weeks,
        cycle_start=plan.cycle_start,
        created_at=plan.created_at,
        current_week=current.week,
        days=[PlanDayOut(**_plan_day_fields(day)) for day in plan.days],
    )


def week_progress_out(progress: WeekProgress) -> WeekProgressOut:
    plan = progress.plan
    return WeekProgressOut(
        start=progress.start,
        plan_title=plan.title if plan else None,
        plan_week=progress.plan_week,
        plan_weeks=plan.weeks if plan else None,
        planned_sessions=progress.planned_sessions,
        done_sessions=progress.done_sessions,
        planned_minutes=progress.planned_minutes,
        done_minutes=progress.done_minutes,
        days=[
            DayProgressOut(
                date=day.date,
                status=day.status,
                planned=[
                    PlannedWorkoutOut(**_plan_day_fields(p.day), done=p.done) for p in day.planned
                ],
                session_ids=[s.id for s in day.sessions],
            )
            for day in progress.days
        ],
    )


def _plan_day_fields(day: PlanDay) -> dict:
    return {
        "week": day.week,
        "weekday": day.weekday,
        "workout_type": WorkoutTypeRef(**asdict(day.workout_type)) if day.workout_type else None,
        "minutes": day.minutes,
        "note": day.note,
        "exercises": [ExerciseOut(**asdict(e)) for e in day.exercises],
    }

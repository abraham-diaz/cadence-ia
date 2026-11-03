from dataclasses import asdict
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cadence_ia.api.schemas.common import WorkoutTypeRef
from cadence_ia.api.schemas.workout_types import WorkoutTypeIn
from cadence_ia.domain.plan import Exercise, PlanDay
from cadence_ia.domain.week_progress import DayStatus, WeekProgress
from cadence_ia.domain.workout_type import Category
from cadence_ia.llm.coach import ChatMessage
from cadence_ia.services import plans


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
    catalog_id: int | None
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
    current_week: int = Field(ge=0)
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
    done: bool


class DayProgressOut(BaseModel):
    date: date
    status: DayStatus
    planned: list[PlannedWorkoutOut]
    session_ids: list[str]


class WeekProgressOut(BaseModel):
    start: date  # Monday
    plan_title: str | None
    plan_week: int | None
    plan_weeks: int | None
    planned_sessions: int
    done_sessions: int
    planned_minutes: int
    done_minutes: int  # every session of the week counts, planned or not
    days: list[DayProgressOut]


def chat_messages(body: ConversationIn) -> list[ChatMessage]:
    return [ChatMessage(role=m.role, text=m.text) for m in body.messages]


def day_inputs(body: PlanIn) -> list[plans.DayInput]:
    return [
        plans.DayInput(
            week=day.week,
            weekday=day.weekday,
            workout_type=(
                day.workout_type_id
                if day.workout_type_id is not None
                else plans.NewType(
                    day.new_type.name, day.new_type.category, tuple(day.new_type.muscles)
                )
            ),
            minutes=day.minutes,
            note=day.note or None,
            exercises=tuple(
                Exercise(e.name, e.sets, e.reps or None, e.catalog_id) for e in day.exercises
            ),
        )
        for day in body.days
    ]


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

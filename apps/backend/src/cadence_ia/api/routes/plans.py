from datetime import date

from fastapi import APIRouter

from cadence_ia.api.deps import CoachDep, Database, PlanExtractorDep
from cadence_ia.api.schemas.common import ErrorOut
from cadence_ia.api.schemas.plans import (
    ConversationIn,
    PlanChatIn,
    PlanChatOut,
    PlanIn,
    PlanOut,
    PlanProposalOut,
    WeekProgressOut,
    WeekSummaryOut,
    chat_messages,
    day_inputs,
    plan_out,
    week_progress_out,
)
from cadence_ia.services import plans

router = APIRouter(prefix="/api/plans", tags=["plans"])

UNAVAILABLE = {503: {"model": ErrorOut}}


@router.post("/chat", responses=UNAVAILABLE)
def chat(body: PlanChatIn, conn: Database, coach: CoachDep) -> PlanChatOut:
    """Send the whole conversation and get the coach's next reply."""
    return PlanChatOut(reply=plans.chat(conn, chat_messages(body), coach))


@router.get("/week-summary")
def week_summary(conn: Database) -> WeekSummaryOut:
    """The last 7 days written as a chat message. The user decides whether to send it."""
    return WeekSummaryOut(text=plans.last_week(conn))


@router.post("/proposal", responses={**UNAVAILABLE, 409: {"model": ErrorOut}})
def propose(body: ConversationIn, conn: Database, extractor: PlanExtractorDep) -> PlanProposalOut:
    """Read the plan agreed in the chat, for the user to review. Nothing is saved."""
    return PlanProposalOut.model_validate(plans.propose(conn, chat_messages(body), extractor))


@router.post("", status_code=201, responses={422: {"model": ErrorOut}})
def save_plan(body: PlanIn, conn: Database) -> PlanOut:
    """Save the reviewed plan as the current one, creating its new workout types."""
    days = day_inputs(body)
    return plan_out(plans.save(conn, body.title, body.weeks, body.current_week, days))


@router.get("/current")
def current_plan(conn: Database) -> PlanOut | None:
    """The active plan, with the week of the cycle we are in today; null if there is none."""
    current = plans.get_current(conn)
    return plan_out(current) if current else None


@router.get("/week-progress")
def week_progress(conn: Database, start: date | None = None) -> WeekProgressOut:
    """A week, Monday to Sunday: what the plan in force asked for and what was trained.
    `start` is any day of the week wanted; without it, this week."""
    return week_progress_out(plans.week(conn, start))

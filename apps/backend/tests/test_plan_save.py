from dataclasses import dataclass, field
from datetime import date

import pytest
from conftest import write_sample_folder
from fastapi.testclient import TestClient

from cadence_ia.api.deps import get_plan_extractor
from cadence_ia.config import Settings
from cadence_ia.domain.plan import Plan, cycle_start
from cadence_ia.llm.coach import ChatMessage
from cadence_ia.llm.errors import LLMUnavailable
from cadence_ia.llm.planner import DayDraft, ExerciseDraft, PlanDraft, WeekDraft, transcript
from cadence_ia.main import create_app
from cadence_ia.services import plans
from cadence_ia.services.errors import InvalidInput
from cadence_ia.services.ingest import ingest
from cadence_ia.storage import workout_types
from cadence_ia.storage.database import connect

CHAT = {
    "messages": [
        {"role": "user", "text": "Quiero un plan"},
        {"role": "model", "text": "Semana A: martes Tren superior 35 min..."},
    ]
}

DRAFT = PlanDraft(
    title="Perder peso",
    weeks=[
        WeekDraft(
            days=[
                DayDraft(
                    weekday=1,
                    workout_type="tren superior",
                    category="strength",
                    minutes=35,
                    note="Para si molesta la rodilla.",
                    exercises=[ExerciseDraft(name="Press de pecho", sets=3, reps="10-12")],
                ),
                DayDraft(
                    weekday=2,
                    workout_type="caminata",  # matches the existing "Caminata"
                    category="strength",  # wrong on purpose: the existing type wins
                    minutes=35,
                    note="",
                    exercises=[],
                ),
            ]
        ),
        WeekDraft(
            days=[
                DayDraft(
                    weekday=9, workout_type="Basura", category="cardio", minutes=10,
                    note=None, exercises=[],
                ),
                DayDraft(
                    weekday=4, workout_type="Caminata", category="cardio", minutes=0,
                    note=None, exercises=[ExerciseDraft(name="  ", sets=None, reps=None)],
                ),
            ]
        ),
    ],
)


@dataclass
class FakeExtractor:
    model: str = "test-model"
    draft: PlanDraft = field(default_factory=lambda: DRAFT)
    calls: list[tuple[list[str], list[ChatMessage]]] = field(default_factory=list)
    error: str | None = None

    def __call__(self, type_names, messages):
        self.calls.append((type_names, messages))
        if self.error:
            raise LLMUnavailable(self.error)
        return self.draft


@pytest.fixture
def extractor():
    return FakeExtractor()


@pytest.fixture
def db_file(tmp_path):
    folder = tmp_path / "tcx"
    folder.mkdir()
    write_sample_folder(folder)
    conn = connect(tmp_path / "test.db")
    ingest(conn, folder)
    workout_types.create_type(conn, "Caminata", "cardio")
    conn.close()
    return tmp_path / "test.db"


@pytest.fixture
def conn(db_file):
    conn = connect(db_file)
    yield conn
    conn.close()


@pytest.fixture
def client(db_file, extractor):
    app = create_app(Settings(db_path=db_file))
    app.dependency_overrides[get_plan_extractor] = lambda: extractor
    return TestClient(app)


def walk_id(conn) -> int:
    return workout_types.find_by_name(conn, "Caminata").id


def plan_body(conn, **changes) -> dict:
    body = {
        "title": "Perder peso",
        "weeks": 2,
        "current_week": 0,
        "days": [
            {
                "week": 0,
                "weekday": 1,
                "new_type": {"name": "Tren superior", "category": "strength"},
                "minutes": 35,
                "note": "Para si molesta la rodilla.",
                "exercises": [{"name": "Press de pecho", "sets": 3, "reps": "10-12"}],
            },
            {"week": 0, "weekday": 2, "workout_type_id": walk_id(conn), "minutes": 35},
            {
                "week": 1,
                "weekday": 2,
                "new_type": {"name": "tren SUPERIOR", "category": "strength"},
                "minutes": 30,
            },
        ],
    }
    return {**body, **changes}


# Weeks of the cycle


def test_cycle_start_is_a_monday():
    assert cycle_start(date(2026, 10, 22), 0) == date(2026, 10, 19)
    assert cycle_start(date(2026, 10, 22), 1) == date(2026, 10, 12)


def test_weeks_take_turns():
    plan = Plan(1, "x", 2, date(2026, 10, 19), None, ())
    assert plan.week_on(date(2026, 10, 25)) == 0  # Sunday, same week
    assert plan.week_on(date(2026, 10, 26)) == 1
    assert plan.week_on(date(2026, 11, 2)) == 0
    assert plan.week_on(date(2026, 10, 18)) == 1  # the week before it started


# Reading the plan from the chat


def test_proposal_matches_existing_types_and_cleans_up(client, extractor, conn):
    response = client.post("/api/plans/proposal", json=CHAT)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Perder peso"
    assert data["weeks"] == 2

    upper, walk, friday = data["days"]  # the day with weekday 9 is dropped
    assert upper["type_name"] == "tren superior"
    assert upper["workout_type_id"] is None
    assert upper["exercises"] == [{"name": "Press de pecho", "sets": 3, "reps": "10-12"}]
    assert walk == {
        "week": 0,
        "weekday": 2,
        "type_name": "Caminata",
        "category": "cardio",
        "workout_type_id": walk_id(conn),
        "minutes": 35,
        "note": None,
        "exercises": [],
    }
    assert friday["week"] == 1
    assert friday["minutes"] == 1
    assert friday["exercises"] == []

    type_names, messages = extractor.calls[0]
    assert type_names == ["Caminata"]
    assert [m.role for m in messages] == ["user", "model"]


def test_proposal_without_a_plan_is_409(client, extractor):
    extractor.draft = PlanDraft(title="", weeks=[])
    response = client.post("/api/plans/proposal", json=CHAT)
    assert response.status_code == 409
    assert response.json()["code"] == "no_plan_in_chat"


def test_proposal_when_gemini_is_down_is_503(client, extractor):
    extractor.error = "Se ha agotado el cupo gratuito de Gemini por hoy"
    response = client.post("/api/plans/proposal", json=CHAT)
    assert response.status_code == 503
    assert response.json()["code"] == "coach_unavailable"


def test_transcript_names_who_speaks():
    text = transcript([ChatMessage("user", "Hola"), ChatMessage("model", "¿Objetivo?")])
    assert text == "Usuario: Hola\n\nEntrenador: ¿Objetivo?"


# Saving it


def test_no_current_plan_at_first(client):
    response = client.get("/api/plans/current")
    assert response.status_code == 200
    assert response.json() is None


def test_save_creates_new_types_once(client, conn):
    response = client.post("/api/plans", json=plan_body(conn))
    assert response.status_code == 201
    plan = response.json()
    assert plan["weeks"] == 2
    assert plan["current_week"] == 0

    first, walk, second = plan["days"]
    assert first["workout_type"]["name"] == "Tren superior"
    assert second["workout_type"] == first["workout_type"]  # "tren SUPERIOR" is the same type
    assert walk["workout_type"]["name"] == "Caminata"
    assert first["exercises"] == [{"name": "Press de pecho", "sets": 3, "reps": "10-12"}]
    assert first["note"] == "Para si molesta la rodilla."
    assert walk["note"] is None

    names = [usage.workout_type.name for usage in workout_types.list_types(conn)]
    assert names == ["Caminata", "Tren superior"]
    assert client.get("/api/plans/current").json() == plan


def test_a_new_plan_replaces_the_current_one(client, conn):
    client.post("/api/plans", json=plan_body(conn))
    client.post("/api/plans", json=plan_body(conn, title="Otro", weeks=1, days=plan_body(conn)["days"][:2]))
    assert client.get("/api/plans/current").json()["title"] == "Otro"
    assert conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 2


def test_current_week_sets_where_the_cycle_starts(conn):
    days = [plans.DayInput(1, 0, walk_id(conn), 30, None, ())]
    current = plans.save(conn, "A/B", 2, 1, days, today=date(2026, 10, 22))
    assert current.plan.cycle_start == date(2026, 10, 12)
    assert current.week == 1
    assert plans.get_current(conn, today=date(2026, 10, 26)).week == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"current_week": 2},
        {"weeks": 1},  # a day in week 1 doesn't fit
        {"days": []},
        {"days": [{"week": 0, "weekday": 7, "workout_type_id": 1, "minutes": 30}]},
        {"days": [{"week": 0, "weekday": 0, "minutes": 30}]},  # no type
        {
            "days": [
                {
                    "week": 0,
                    "weekday": 0,
                    "workout_type_id": 1,
                    "new_type": {"name": "X", "category": "cardio"},
                    "minutes": 30,
                }
            ]
        },
    ],
)
def test_invalid_plans_are_rejected(client, conn, changes):
    response = client.post("/api/plans", json=plan_body(conn, **changes))
    assert response.status_code == 422
    assert client.get("/api/plans/current").json() is None
    assert workout_types.find_by_name(conn, "Tren superior") is None


def test_unknown_type_creates_nothing(conn):
    days = [
        plans.DayInput(0, 0, plans.NewType("Tren superior", "strength"), 30, None, ()),
        plans.DayInput(0, 1, 999, 30, None, ()),
    ]
    with pytest.raises(InvalidInput) as err:
        plans.save(conn, "x", 1, 0, days)
    assert err.value.code == "workout_type_not_found"
    assert workout_types.find_by_name(conn, "Tren superior") is None


def test_deleting_a_type_keeps_the_plan_day(client, conn):
    client.post("/api/plans", json=plan_body(conn))
    workout_types.delete_type(conn, walk_id(conn))
    walk = client.get("/api/plans/current").json()["days"][1]
    assert walk["workout_type"] is None
    assert walk["minutes"] == 35


# This week's progress


def test_week_progress_without_a_plan(client):
    progress = client.get("/api/plans/week-progress").json()
    assert progress["plan_title"] is None
    assert len(progress["days"]) == 7
    assert date.fromisoformat(progress["start"]).weekday() == 0
    assert {d["status"] for d in progress["days"]} <= {"rest", "extra"}


def test_week_progress_follows_the_saved_plan(client, conn):
    client.post("/api/plans", json=plan_body(conn))
    progress = client.get("/api/plans/week-progress").json()
    assert progress["plan_title"] == "Perder peso"
    assert (progress["plan_week"], progress["plan_weeks"]) == (0, 2)

    # Saved today: only today and the days after it ask for something.
    today = date.today().weekday()
    planned = [d for d in progress["days"] if d["planned"]]
    assert [date.fromisoformat(d["date"]).weekday() for d in planned] == [
        weekday for weekday in (1, 2) if weekday >= today
    ]
    for day in planned:
        assert day["status"] == "pending"
        assert day["planned"][0]["done"] is False


def test_week_progress_of_another_week(client):
    response = client.get("/api/plans/week-progress", params={"start": "2026-10-15"})
    assert response.status_code == 200
    assert response.json()["start"] == "2026-10-12"
    assert client.get("/api/plans/week-progress", params={"start": "ayer"}).status_code == 422

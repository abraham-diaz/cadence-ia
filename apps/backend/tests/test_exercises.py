from typing import get_args

import pytest
from test_api import client, make_type  # noqa: F401  (fixture)

from cadence_ia.domain.exercise import MUSCLE_NAMES, CatalogExercise, Muscle, search, suggest
from cadence_ia.importers.wger import html_to_text, parse_exercise
from cadence_ia.services.exercises import EmptyCatalog, sync_catalog
from cadence_ia.storage import exercises
from cadence_ia.storage.database import connect


def wger_item(
    id=1, muscles=(10,), secondary=(), names=((4, "Sentadilla"), (2, "Squat")), images=(), category=9
):
    """The parts of a /exerciseinfo/ entry the importer reads."""
    return {
        "id": id,
        "category": {"id": category},
        "muscles": [{"id": m} for m in muscles],
        "muscles_secondary": [{"id": m} for m in secondary],
        "translations": [
            {"language": lang, "name": name, "description": f"<p>{name}: paso 1</p>"}
            for lang, name in names
        ],
        "images": list(images),
        "license": {"short_name": "CC-BY-SA 4"},
        "license_author": "someone",
    }


def exercise(id, muscles=("quads",), name_es="Ejercicio", image=None) -> CatalogExercise:
    return CatalogExercise(
        id=id, name_es=name_es, name_en=f"Exercise {id}", primary_muscles=muscles,
        secondary_muscles=(), image_url=image, license="CC-BY-SA 4", author=None,
    )


def test_every_muscle_has_a_name():
    assert list(MUSCLE_NAMES) == list(get_args(Muscle))


def test_parse_folds_wger_muscles_into_groups():
    # Biceps femoris = hamstrings; gastrocnemius and soleus are both calves.
    parsed = parse_exercise(wger_item(muscles=(11,), secondary=(7, 15, 11)))
    assert parsed.primary_muscles == ("hamstrings",)
    assert parsed.secondary_muscles == ("calves",)  # primary ones aren't repeated
    assert parsed.name == "Sentadilla"
    assert parsed.license == "CC-BY-SA 4"


def test_parse_falls_back_to_english_and_picks_the_main_image():
    parsed = parse_exercise(
        wger_item(
            names=((2, "Squat"),),
            images=({"image": "a.png", "is_main": False}, {"image": "main.png", "is_main": True}),
        )
    )
    assert parsed.name_es is None
    assert parsed.name == "Squat"
    assert parsed.image_url == "main.png"


def test_parse_skips_entries_without_muscle_or_name():
    assert parse_exercise(wger_item(muscles=())) is None
    assert parse_exercise(wger_item(muscles=(99,))) is None  # a muscle the app doesn't use
    assert parse_exercise(wger_item(names=((7, "Agachamento"),))) is None  # only Portuguese


def test_parse_skips_stretches_and_cardio():
    assert parse_exercise(wger_item(names=((4, "Estiramiento de gemelos"),))) is None
    assert parse_exercise(wger_item(names=((4, "Gemelos"), (2, "Calf Stretch")))) is None
    assert parse_exercise(wger_item(names=((4, "Foam Roller cuádriceps"),))) is None
    assert parse_exercise(wger_item(category=15)) is None


def test_suggest_prefers_spanish_and_pictures():
    catalog = [
        exercise(1, name_es=None),
        exercise(2),
        exercise(3, image="x.png"),
        exercise(4, name_es=None, image="y.png"),
    ]
    picks = suggest(catalog, ("quads",), seed="2026-10-27", per_muscle=2)[0].exercises
    assert [e.id for e in picks] == [3, 2]


def test_suggest_is_stable_per_day_and_varies_between_days():
    catalog = [exercise(i) for i in range(30)]
    today = [e.id for e in suggest(catalog, ("quads",), seed="2026-10-27")[0].exercises]
    assert today == [e.id for e in suggest(catalog, ("quads",), seed="2026-10-27")[0].exercises]
    other_days = {
        tuple(e.id for e in suggest(catalog, ("quads",), seed=f"2026-11-{d:02}")[0].exercises)
        for d in range(1, 8)
    }
    assert len(other_days) > 1


def test_suggest_never_repeats_an_exercise_across_muscles():
    catalog = [exercise(i, muscles=("quads", "glutes")) for i in range(4)]
    glutes, quads = suggest(catalog, ("glutes", "quads"), seed="s")
    assert len(glutes.exercises) == 3
    assert [e.id for e in quads.exercises] == list({0, 1, 2, 3} - {e.id for e in glutes.exercises})


def test_sync_updates_in_place_and_removes_what_wger_dropped(tmp_path):
    conn = connect(tmp_path / "test.db")
    assert sync_catalog(conn, lambda: [exercise(1), exercise(2, muscles=("chest",))]) == 2
    sync_catalog(conn, lambda: [exercise(1, name_es="Nuevo nombre")])
    stored = exercises.for_muscles(conn, ("quads", "chest"))
    assert [(e.id, e.name) for e in stored] == [(1, "Nuevo nombre")]


def test_empty_download_keeps_the_stored_catalog(tmp_path):
    conn = connect(tmp_path / "test.db")
    sync_catalog(conn, lambda: [exercise(1)])
    with pytest.raises(EmptyCatalog):
        sync_catalog(conn, lambda: [])
    assert exercises.count(conn) == 1


def test_list_muscles(client):  # noqa: F811
    data = client.get("/api/muscles").json()
    assert data[0] == {"id": "chest", "name": "Pecho"}
    assert len(data) == len(MUSCLE_NAMES)


def test_workout_type_keeps_its_muscles_in_display_order(client):  # noqa: F811
    created = client.post(
        "/api/workout-types",
        json={"name": "Pierna", "category": "strength", "muscles": ["calves", "quads", "quads"]},
    ).json()
    assert created["muscles"] == ["quads", "calves"]

    updated = client.put(
        f"/api/workout-types/{created['id']}",
        json={"name": "Pierna", "category": "strength", "muscles": ["glutes"]},
    ).json()
    assert updated["muscles"] == ["glutes"]
    assert client.get("/api/workout-types").json()[0]["muscles"] == ["glutes"]

    # A type without muscles, and one with a muscle the app doesn't know.
    assert make_type(client, "Caminata", "cardio")["muscles"] == []
    bad = client.post("/api/workout-types", json={"name": "X", "category": "strength", "muscles": ["neck"]})
    assert bad.status_code == 422


def test_suggestions_for_a_type(client, tmp_path):  # noqa: F811
    conn = connect(tmp_path / "test.db")
    sync_catalog(conn, lambda: [exercise(1), exercise(2, muscles=("chest",)), exercise(3, muscles=("calves",))])
    conn.close()
    leg = client.post(
        "/api/workout-types", json={"name": "Pierna", "category": "strength", "muscles": ["quads", "calves"]}
    ).json()

    data = client.get(f"/api/workout-types/{leg['id']}/exercises?day=2026-10-27").json()
    assert [s["muscle"]["name"] for s in data] == ["Cuádriceps", "Gemelos"]
    assert [e["id"] for e in data[0]["exercises"]] == [1]
    assert data[0]["exercises"][0]["license"] == "CC-BY-SA 4"

    assert client.get("/api/workout-types/999/exercises").status_code == 404


def test_html_description_becomes_plain_lines():
    markup = "<p>Ponte de pie &amp; respira.</p><ul><li>Baja</li><li>Sube</li></ul><p> </p>"
    assert html_to_text(markup) == "Ponte de pie & respira.\n• Baja\n• Sube"
    assert html_to_text("<p></p>") is None


def test_parse_prefers_the_spanish_description():
    assert parse_exercise(wger_item()).description == "Sentadilla: paso 1"
    assert parse_exercise(wger_item(names=((2, "Squat"),))).description == "Squat: paso 1"


def test_search_ignores_accents_and_word_order():
    catalog = [
        exercise(1, name_es="Sentadilla búlgara con mancuernas"),
        exercise(2, name_es="Press de banca"),
        exercise(3, name_es="Press de banca inclinado"),
        exercise(4, name_es="Remo con mancuernas"),
    ]
    assert [e.id for e in search(catalog, "bulgara")] == [1]
    assert [e.id for e in search(catalog, "mancuernas sentadilla")] == [1]
    assert [e.id for e in search(catalog, "banca")] == [2, 3]  # shorter name first
    assert [e.id for e in search(catalog, "mancuernas")] == [4, 1]  # "Remo…" is shorter
    assert search(catalog, "  ") == []


def test_search_and_detail_api(client, tmp_path):  # noqa: F811
    conn = connect(tmp_path / "test.db")
    item = parse_exercise(wger_item(id=7, muscles=(4,), secondary=(5,), names=((4, "Press de banca"),)))
    sync_catalog(conn, lambda: [item])
    conn.close()

    found = client.get("/api/exercises?q=press").json()
    assert [e["id"] for e in found] == [7]

    detail = client.get("/api/exercises/7").json()
    assert detail["name"] == "Press de banca"
    assert detail["description"] == "Press de banca: paso 1"
    assert detail["primary_muscles"] == [{"id": "chest", "name": "Pecho"}]
    assert detail["secondary_muscles"] == [{"id": "triceps", "name": "Tríceps"}]

    missing = client.get("/api/exercises/999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "exercise_not_found"


def test_plan_exercises_link_to_the_catalog(client, tmp_path):  # noqa: F811
    conn = connect(tmp_path / "test.db")
    sync_catalog(conn, lambda: [exercise(1, name_es="Press de banca", image="banca.png"), exercise(2)])
    conn.close()
    leg = make_type(client)
    body = {
        "title": "Plan",
        "weeks": 1,
        "current_week": 0,
        "days": [
            {
                "week": 0,
                "weekday": 1,
                "workout_type_id": leg["id"],
                "minutes": 40,
                "exercises": [
                    {"name": "press de BANCA"},  # same name: linked
                    {"name": "Lo que yo llamo así", "catalog_id": 2},  # picked from the catalog
                    {"name": "Invento mío"},  # not in the catalog
                    {"name": "Otro", "catalog_id": 999},  # gone from the catalog
                ],
            }
        ],
    }
    assert client.post("/api/plans", json=body).status_code == 201

    saved = client.get("/api/plans/current").json()["days"][0]["exercises"]
    assert [(e["name"], e["catalog_id"]) for e in saved] == [
        ("press de BANCA", 1),
        ("Lo que yo llamo así", 2),
        ("Invento mío", None),
        ("Otro", None),
    ]
    assert saved[0]["image_url"] == "banca.png"


def test_sync_links_plan_exercises_saved_before_the_catalog(client, tmp_path):  # noqa: F811
    leg = make_type(client)
    day = {"week": 0, "weekday": 1, "workout_type_id": leg["id"], "minutes": 40}
    day["exercises"] = [{"name": "Press de banca"}, {"name": "Invento mío"}]
    client.post("/api/plans", json={"title": "Plan", "weeks": 1, "current_week": 0, "days": [day]})

    conn = connect(tmp_path / "test.db")
    sync_catalog(conn, lambda: [exercise(1, name_es="Press de Banca")])
    conn.close()

    saved = client.get("/api/plans/current").json()["days"][0]["exercises"]
    assert [e["catalog_id"] for e in saved] == [1, None]

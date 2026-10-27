import sqlite3
from collections.abc import Callable
from datetime import date

from cadence_ia.domain.exercise import (
    CatalogExercise,
    MuscleSuggestion,
    find_by_name,
    search,
    suggest,
)
from cadence_ia.importers.wger import fetch_catalog
from cadence_ia.services.errors import NotFound
from cadence_ia.services.workout_types import get_type
from cadence_ia.storage import exercises, plans


class EmptyCatalog(Exception):
    pass


def sync_catalog(
    conn: sqlite3.Connection, fetch: Callable[[], list[CatalogExercise]] = fetch_catalog
) -> int:
    """Download the wger catalog and store it. Plan exercises written before it existed
    get linked by name. Returns how many exercises the catalog has."""
    catalog = fetch()
    if not catalog:
        # A broken download must not wipe the catalog that's already stored.
        raise EmptyCatalog("wger returned no usable exercises")
    exercises.replace_catalog(conn, catalog)
    matches = {name: find_by_name(catalog, name) for name in plans.unlinked_exercise_names(conn)}
    plans.link_exercises(conn, {name: match.id for name, match in matches.items() if match})
    return len(catalog)


def suggestions_for_type(conn: sqlite3.Connection, type_id: int, day: date) -> list[MuscleSuggestion]:
    """A few exercises for each muscle the type trains; they change from one day to the next."""
    muscles = get_type(conn, type_id).muscles
    return suggest(exercises.for_muscles(conn, muscles), muscles, seed=day.isoformat())


def search_catalog(conn: sqlite3.Connection, query: str) -> list[CatalogExercise]:
    return search(exercises.list_all(conn), query)


def get_exercise(conn: sqlite3.Connection, exercise_id: int) -> CatalogExercise:
    exercise = exercises.get(conn, exercise_id)
    if exercise is None:
        raise NotFound("exercise_not_found", "Exercise not found")
    return exercise

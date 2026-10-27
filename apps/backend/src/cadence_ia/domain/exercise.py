import random
import unicodedata
from dataclasses import dataclass
from typing import Literal

Muscle = Literal[
    "chest", "back", "shoulders", "biceps", "triceps",
    "abs", "glutes", "quads", "hamstrings", "calves",
]

# In the order they're shown, roughly top to bottom.
MUSCLE_NAMES: dict[Muscle, str] = {
    "chest": "Pecho",
    "back": "Espalda",
    "shoulders": "Hombros",
    "biceps": "Bíceps",
    "triceps": "Tríceps",
    "abs": "Abdomen",
    "glutes": "Glúteos",
    "quads": "Cuádriceps",
    "hamstrings": "Isquiotibiales",
    "calves": "Gemelos",
}


def sort_muscles(muscles) -> tuple[Muscle, ...]:
    order = list(MUSCLE_NAMES)
    return tuple(sorted(set(muscles), key=order.index))


@dataclass(frozen=True)
class CatalogExercise:
    """An exercise from the wger catalog."""

    id: int  # wger's id, kept so a new sync updates it in place
    name_es: str | None
    name_en: str | None
    primary_muscles: tuple[Muscle, ...]
    secondary_muscles: tuple[Muscle, ...]
    image_url: str | None
    license: str
    author: str | None
    description: str | None = None

    @property
    def name(self) -> str:
        return self.name_es or self.name_en or ""


@dataclass(frozen=True)
class MuscleSuggestion:
    muscle: Muscle
    exercises: list[CatalogExercise]


def suggest(
    catalog: list[CatalogExercise], muscles: tuple[Muscle, ...], seed: str, per_muscle: int = 3
) -> list[MuscleSuggestion]:
    """A few exercises per muscle. The same seed (e.g. the date) gives the same picks,
    so they stay put during the day and change the next."""
    suggestions, used = [], set()
    for muscle in muscles:
        pool = [e for e in catalog if muscle in e.primary_muscles and e.id not in used]
        rng = random.Random(f"{seed}:{muscle}")
        rng.shuffle(pool)
        # Spanish name and a picture first: those entries are usually the better kept ones.
        pool.sort(key=lambda e: (e.name_es is None, e.image_url is None))
        picks = pool[:per_muscle]
        used.update(e.id for e in picks)
        suggestions.append(MuscleSuggestion(muscle, picks))
    return suggestions


def normalize(text: str) -> str:
    """Lowercase and without accents, so "bulgara" finds "búlgara"."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def search(catalog: list[CatalogExercise], query: str, limit: int = 8) -> list[CatalogExercise]:
    """Exercises whose name has every word of the query; names starting with it first."""
    words = normalize(query).split()
    if not words:
        return []
    found = []
    for exercise in catalog:
        names = [normalize(n) for n in (exercise.name_es, exercise.name_en) if n]
        if any(all(w in name for w in words) for name in names):
            starts = any(name.startswith(words[0]) for name in names)
            found.append((not starts, exercise.name_es is None, len(exercise.name), exercise))
    found.sort(key=lambda f: f[:3])
    return [f[3] for f in found[:limit]]


def find_by_name(catalog: list[CatalogExercise], name: str) -> CatalogExercise | None:
    """The exercise called exactly that, ignoring case and accents."""
    wanted = normalize(name)
    for exercise in catalog:
        if wanted in (normalize(n) for n in (exercise.name_es, exercise.name_en) if n):
            return exercise
    return None

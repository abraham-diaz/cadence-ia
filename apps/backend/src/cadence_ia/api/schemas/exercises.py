from pydantic import BaseModel

from cadence_ia.domain.exercise import MUSCLE_NAMES, CatalogExercise, Muscle


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

"""Turn the plan agreed in the coach chat into structured data the user reviews before saving."""

from typing import Protocol

from pydantic import BaseModel, Field

from cadence_ia.llm.coach import ChatMessage

EXTRACT_PROMPT = """\
Recibes una conversación entre un entrenador y un usuario que diseñan un plan de \
entrenamiento semanal. Extrae el último plan que acordaron, en JSON.

Reglas:
- Una entrada en "weeks" por cada variante de semana (semana A, semana B...), en orden. \
Si el plan es igual todas las semanas, solo una.
- Solo los días con entrenamiento: los de descanso no se incluyen.
- "weekday": 0 = lunes, 1 = martes, 2 = miércoles, 3 = jueves, 4 = viernes, 5 = sábado, \
6 = domingo.
- "workout_type": el nombre del tipo de entrenamiento. Si coincide con uno de los tipos \
del usuario (lista al final), escríbelo exactamente igual. Si el plan concreta un enfoque \
("Pesas - Tren superior"), usa el enfoque como nombre ("Tren superior"). Es un nombre \
corto, de 1 a 3 palabras, nunca una explicación: si un día alterna entre varios tipos, \
elige el primero y explica la alternancia en "note".
- "category": "strength" para fuerza y "cardio" para cardio.
- "minutes": si se dio un rango, el valor más alto.
- "exercises": los ejercicios de ese día, si se dieron, con series y repeticiones si se \
indicaron ("reps" es texto: "10-12", "30 s"). Si el mismo bloque de ejercicios se repite \
en varios días, ponlo en cada uno.
- "note": consejos concretos para ese día, en una o dos frases. Vacío si no hay.
- "title": un nombre corto para el plan, de 2 a 5 palabras.
- No inventes nada que no esté en la conversación.
"""

SPEAKERS = {"user": "Usuario", "model": "Entrenador"}


class ExerciseDraft(BaseModel):
    name: str
    sets: int | None = Field(description="Número de series, si se indicó.")
    reps: str | None = Field(description='Repeticiones como texto: "10-12", "30 s".')


class DayDraft(BaseModel):
    weekday: int = Field(description="0 = lunes ... 6 = domingo.")
    workout_type: str
    category: str = Field(description='"strength" o "cardio".')
    minutes: int
    note: str | None
    exercises: list[ExerciseDraft]


class WeekDraft(BaseModel):
    days: list[DayDraft]


class PlanDraft(BaseModel):
    """What the model must return (Gemini fills it as structured JSON)."""

    title: str
    weeks: list[WeekDraft]


class PlanExtractor(Protocol):
    model: str

    def __call__(self, type_names: list[str], messages: list[ChatMessage]) -> PlanDraft: ...


def transcript(messages: list[ChatMessage]) -> str:
    """The chat as one text: the model reads it, it doesn't continue it."""
    return "\n\n".join(f"{SPEAKERS[m.role]}: {m.text}" for m in messages)

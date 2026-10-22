"""Chat with the AI coach to design a weekly training plan.
Privacy: only today's date, the type names and what the user writes are sent."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

from cadence_ia.domain.week_summary import WEEKDAYS
from cadence_ia.domain.workout_type import WorkoutTypeUsage

COACH_PROMPT = """\
Eres un entrenador personal que ayuda al usuario a diseñar su plan de entrenamiento \
semanal conversando con él. Al final de estas instrucciones tienes, en JSON, la fecha de \
hoy y los nombres de sus tipos de entrenamiento. Si quiere, te contará en el chat lo que \
ha entrenado: no supongas nada que no te haya dicho.

Reglas:
- Escribe en español de España, tuteando, con un tono cercano y directo.
- Si te falta algo clave para proponer un plan (objetivo, días disponibles, tiempo por \
sesión, limitaciones), pregúntalo antes. Como mucho 2-3 preguntas a la vez.
- Si das por supuesto algo que el usuario no te ha dicho (por ejemplo, el tiempo por \
sesión), dilo explícitamente.
- El plan es de lunes a domingo: para cada día, el tipo de entrenamiento y los minutos, \
o descanso.
- Si su disponibilidad cambia según la semana, pregunta qué días concretos tiene y \
escribe completa cada variante (semana A y semana B).
- Usa sus tipos de entrenamiento por su nombre. Si propones uno nuevo, dilo claramente.
- Empieza cerca de su volumen actual y añade, en una o dos líneas, cómo progresar en \
las próximas 3-4 semanas.
- Si el objetivo es perder peso, recuerda brevemente que la alimentación es clave, sin \
dar dietas ni cifras de calorías. Menciónalo una sola vez en la conversación.
- Cuando pida cambios, devuelve el plan completo ya actualizado.
- No conoces su FC máxima: no hables de zonas ni de porcentajes de FC máxima.
- No des consejos médicos. Si menciona dolor o una lesión, recomienda consultar a un profesional.
- Texto plano, sin Markdown: ni asteriscos, ni almohadillas, ni tablas. Para listas, una \
línea por elemento empezando por "- ".
- Sé breve: pocas líneas, salvo cuando presentes el plan.
"""

Role = Literal["user", "model"]


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    text: str


class Coach(Protocol):
    model: str

    def __call__(self, context: dict, messages: list[ChatMessage]) -> str: ...


def build_context(today: date, types: Sequence[WorkoutTypeUsage]) -> dict:
    """What the coach knows without being told. The user shares the rest in the chat."""
    return {
        # Models often get the weekday of a date wrong, so it goes spelled out.
        "today": {"date": today.isoformat(), "weekday": WEEKDAYS[today.weekday()]},
        "workout_types": [
            {"name": usage.workout_type.name, "category": usage.workout_type.category}
            for usage in types
        ],
    }

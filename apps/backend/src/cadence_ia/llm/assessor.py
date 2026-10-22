"""What an assessment is and what the LLM receives, whichever LLM it is.

Only the metrics are sent, as JSON: never the TCX file, GPS, device or file
names. Keep it that way: on Gemini's free tier, Google may use what we send
to improve its products.
"""

from dataclasses import asdict
from typing import Protocol

from pydantic import BaseModel, Field

from cadence_ia.domain.comparison import Baseline, Stats
from cadence_ia.domain.heart_rate import Segment
from cadence_ia.domain.session import Session

SYSTEM_PROMPT = """\
Eres un entrenador personal que valora entrenamientos a partir de la frecuencia \
cardiaca (FC) registrada por una pulsera Fitbit. Recibes las métricas de una sesión en JSON.

Reglas:
- Escribe en español de España, tuteando, con un tono cercano y directo.
- Básate solo en los datos. No inventes ejercicios, pesos, repeticiones ni sensaciones.
- En fuerza, la FC refleja el patrón de series y descansos, pero no la carga levantada. \
Tenlo en cuenta y no saques conclusiones sobre fuerza o hipertrofia.
- "recovery_30s" y "recovery_60s" son cuántas pulsaciones baja la FC a los 30 y 60 s de \
empezar un descanso: más es mejor. Muchos descansos duran menos de 60 s.
- Si hay "comparison", es la media de las sesiones anteriores del mismo tipo: comenta la \
evolución con cifras concretas.
- No conoces la FC máxima del usuario: no hables de zonas ni porcentajes de FC máxima.
- Las calorías son una estimación de Fitbit: no les des importancia.
- No des consejos médicos. Si algo parece anómalo, sugiere con prudencia consultarlo.
- Sé breve: el resumen en 2-3 frases, 2-3 puntos por lista, el consejo en 1-2 frases.
"""


class AssessmentContent(BaseModel):
    """What the model must return (Gemini fills it as structured JSON)."""

    headline: str = Field(description="Una frase corta que resuma la sesión.")
    summary: str = Field(description="Valoración general en 2-3 frases.")
    strengths: list[str] = Field(description="2-3 cosas que fueron bien.")
    improvements: list[str] = Field(description="1-3 cosas a mejorar.")
    advice: str = Field(description="Un consejo concreto para la próxima sesión.")


class AssessmentUnavailable(Exception):
    """The LLM can't be used (no API key, quota exceeded, network...)."""


class Assessor(Protocol):
    """Anything that turns the metrics payload into an assessment."""

    model: str  # stored with each assessment

    def __call__(self, payload: dict) -> AssessmentContent: ...


def build_payload(
    session: Session, stats: Stats, segments: list[Segment], comparison: Baseline | None
) -> dict:
    """The metrics sent to the model. `session` must have a workout type."""
    workout_type = session.workout_type
    payload = {
        "workout_type": workout_type.name,
        "category": workout_type.category,
        "date": session.start_time.date().isoformat(),
        "duration_min": round(session.duration_s / 60),
        "heart_rate": {
            "min": session.hr_min,
            "avg": session.hr_avg,
            "max": session.hr_max,
        },
        "estimated_kcal": session.calories,
        "stats": _rounded(stats),
    }
    if segments:
        payload["segments"] = [
            {
                "kind": "set" if s.kind == "work" else "rest",
                "duration_s": s.duration_s,
                "hr_start": s.hr_start,
                "hr_end": s.hr_end,
                **({"recovery_30s": s.drop_30s} if s.drop_30s is not None else {}),
                **({"recovery_60s": s.drop_60s} if s.drop_60s is not None else {}),
            }
            for s in segments
        ]
    if comparison:
        payload["comparison"] = {**_rounded(comparison.stats), "sessions": comparison.sessions}
    return payload


def _rounded(stats: Stats) -> dict:
    return {k: round(float(v), 1) for k, v in asdict(stats).items() if v is not None}

"""Ask an LLM (Gemini) to write an assessment of a session from its metrics.

Only the metrics are sent, as JSON: never the TCX file, GPS, device or file
names. Keep it that way: on Gemini's free tier, Google may use what we send
to improve its products.
"""

import json
import os

from pydantic import BaseModel, Field

DEFAULT_MODEL = "gemini-3.8-flash"

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


def build_payload(detail: dict) -> dict:
    """The metrics sent to the model, taken from a SessionDetail as a dict."""
    workout_type = detail["workout_type"]
    payload = {
        "workout_type": workout_type["name"],
        "category": workout_type["category"],
        "date": str(detail["start_time"])[:10],
        "duration_min": round(detail["duration_s"] / 60),
        "heart_rate": {
            "min": detail["hr_min"],
            "avg": detail["hr_avg"],
            "max": detail["hr_max"],
        },
        "estimated_kcal": detail["calories"],
        "stats": _rounded(detail["stats"]),
    }
    if detail["segments"]:
        payload["segments"] = [
            {
                "kind": "set" if s["kind"] == "work" else "rest",
                "duration_s": s["duration_s"],
                "hr_start": s["hr_start"],
                "hr_end": s["hr_end"],
                **({"recovery_30s": s["drop_30s"]} if s["drop_30s"] is not None else {}),
                **({"recovery_60s": s["drop_60s"]} if s["drop_60s"] is not None else {}),
            }
            for s in detail["segments"]
        ]
    if detail["comparison"]:
        payload["comparison"] = _rounded(detail["comparison"])
    return payload


def _rounded(stats: dict) -> dict:
    return {k: round(v, 1) for k, v in stats.items() if v is not None}


def model_name() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def generate(payload: dict) -> AssessmentContent:
    """Call Gemini and return its assessment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AssessmentUnavailable("Falta la variable GEMINI_API_KEY en el servidor")

    # Imported here so the rest of the app (and the tests) don't need the SDK loaded.
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model_name(),
            contents=json.dumps(payload, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=AssessmentContent,
                temperature=0.7,
            ),
        )
    except errors.APIError as err:
        if err.code == 429:
            raise AssessmentUnavailable("Se ha agotado el cupo gratuito de Gemini por hoy") from err
        raise AssessmentUnavailable(f"Gemini respondió con un error ({err.code})") from err
    except Exception as err:  # network errors, timeouts...
        raise AssessmentUnavailable("No se pudo contactar con Gemini") from err

    if response.parsed is None:
        raise AssessmentUnavailable("Gemini no devolvió una valoración válida")
    return response.parsed

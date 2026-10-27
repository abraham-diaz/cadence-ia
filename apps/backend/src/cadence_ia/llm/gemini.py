import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from cadence_ia.llm.assessor import SYSTEM_PROMPT, AssessmentContent
from cadence_ia.llm.coach import COACH_PROMPT, ChatMessage
from cadence_ia.llm.errors import LLMUnavailable
from cadence_ia.llm.planner import EXTRACT_PROMPT, PlanDraft, transcript


def _client(api_key: str | None):
    if not api_key:
        raise LLMUnavailable("Falta la variable GEMINI_API_KEY en el servidor")
    # Imported here so the rest of the app (and the tests) don't need the SDK loaded.
    from google import genai

    return genai.Client(api_key=api_key)


@contextmanager
def _gemini_errors() -> Iterator[None]:
    from google.genai import errors

    try:
        yield
    except errors.APIError as err:
        if err.code == 429:
            raise LLMUnavailable("Se ha agotado el cupo gratuito de Gemini por hoy") from err
        raise LLMUnavailable(f"Gemini respondió con un error ({err.code})") from err
    except Exception as err:  # network errors, timeouts...
        raise LLMUnavailable("No se pudo contactar con Gemini") from err


@dataclass(frozen=True)
class GeminiAssessor:
    api_key: str | None
    model: str

    def __call__(self, payload: dict) -> AssessmentContent:
        from google.genai import types

        client = _client(self.api_key)
        with _gemini_errors():
            response = client.models.generate_content(
                model=self.model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=AssessmentContent,
                    temperature=0.7,
                ),
            )

        if response.parsed is None:
            raise LLMUnavailable("Gemini no devolvió una valoración válida")
        return response.parsed


@dataclass(frozen=True)
class GeminiCoach:
    api_key: str | None
    model: str

    def __call__(self, context: dict, messages: list[ChatMessage]) -> str:
        from google.genai import types

        client = _client(self.api_key)
        with _gemini_errors():
            response = client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(role=m.role, parts=[types.Part(text=m.text)]) for m in messages
                ],
                config=types.GenerateContentConfig(
                    system_instruction=f"{COACH_PROMPT}\n{json.dumps(context, ensure_ascii=False)}",
                    temperature=0.8,
                ),
            )

        if not response.text:
            raise LLMUnavailable("Gemini no devolvió ninguna respuesta")
        return response.text.strip()


@dataclass(frozen=True)
class GeminiPlanExtractor:
    api_key: str | None
    model: str

    def __call__(self, type_names: list[str], messages: list[ChatMessage]) -> PlanDraft:
        from google.genai import types

        client = _client(self.api_key)
        types_line = json.dumps(type_names, ensure_ascii=False)
        with _gemini_errors():
            response = client.models.generate_content(
                model=self.model,
                contents=transcript(messages),
                config=types.GenerateContentConfig(
                    system_instruction=f"{EXTRACT_PROMPT}\nTipos del usuario: {types_line}",
                    response_mime_type="application/json",
                    response_schema=PlanDraft,
                    temperature=0.2,
                ),
            )

        if response.parsed is None:
            raise LLMUnavailable("Gemini no devolvió un plan válido")
        return response.parsed

import json
from dataclasses import dataclass

from cadence_ia.llm.assessor import SYSTEM_PROMPT, AssessmentContent, AssessmentUnavailable


@dataclass(frozen=True)
class GeminiAssessor:
    api_key: str | None
    model: str

    def __call__(self, payload: dict) -> AssessmentContent:
        if not self.api_key:
            raise AssessmentUnavailable("Falta la variable GEMINI_API_KEY en el servidor")

        # Imported here so the rest of the app (and the tests) don't need the SDK loaded.
        from google import genai
        from google.genai import errors, types

        client = genai.Client(api_key=self.api_key)
        try:
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
        except errors.APIError as err:
            if err.code == 429:
                raise AssessmentUnavailable("Se ha agotado el cupo gratuito de Gemini por hoy") from err
            raise AssessmentUnavailable(f"Gemini respondió con un error ({err.code})") from err
        except Exception as err:  # network errors, timeouts...
            raise AssessmentUnavailable("No se pudo contactar con Gemini") from err

        if response.parsed is None:
            raise AssessmentUnavailable("Gemini no devolvió una valoración válida")
        return response.parsed

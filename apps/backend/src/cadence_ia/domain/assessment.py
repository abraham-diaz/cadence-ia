"""The written assessment of a session, as kept after the LLM answers."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Assessment:
    content: dict  # the fields written by the model (headline, summary...)
    model: str
    created_at: datetime

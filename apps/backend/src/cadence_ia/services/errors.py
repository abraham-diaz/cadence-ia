"""`code` is stable: the frontend shows its own message for each one.
`message` is for whoever reads the API or the logs."""

from typing import Literal

ErrorCode = Literal[
    "session_not_found",
    "workout_type_not_found",
    "exercise_not_found",
    "duplicate_workout_type",
    "session_without_type",
    "assessment_unavailable",
    "coach_unavailable",
    "no_plan_in_chat",
    "invalid_plan",
]


class ServiceError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class NotFound(ServiceError):
    pass


class InvalidInput(ServiceError):
    """The request refers to something that doesn't exist."""


class Conflict(ServiceError):
    pass


class Unavailable(ServiceError):
    """An outside service (the LLM) can't be used right now."""

"""Errors raised by the use cases. The API turns them into HTTP responses.

`code` is stable and machine-readable: the frontend translates it into a
message for the user. `message` is for whoever reads the API or the logs.
"""

from typing import Literal

ErrorCode = Literal[
    "session_not_found",
    "workout_type_not_found",
    "duplicate_workout_type",
    "session_without_type",
    "assessment_unavailable",
]


class ServiceError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class NotFound(ServiceError):
    """The session or workout type asked for doesn't exist."""


class InvalidInput(ServiceError):
    """The request refers to something that doesn't exist."""


class Conflict(ServiceError):
    """The request clashes with the data as it is now."""


class Unavailable(ServiceError):
    """An outside service (the LLM) can't be used right now."""

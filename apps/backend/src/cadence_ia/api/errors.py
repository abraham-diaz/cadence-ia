from fastapi import Request
from fastapi.responses import JSONResponse

from cadence_ia.services.errors import (
    Conflict,
    InvalidInput,
    NotFound,
    ServiceError,
    Unavailable,
)

_STATUS = {NotFound: 404, InvalidInput: 422, Conflict: 409, Unavailable: 503}


def _status(error: ServiceError) -> int:
    # isinstance, so a subclass (e.g. of NotFound) keeps its parent's status.
    return next((code for cls, code in _STATUS.items() if isinstance(error, cls)), 500)


async def service_error_handler(request: Request, error: ServiceError) -> JSONResponse:
    """`detail` keeps FastAPI's usual shape; `code` is what the frontend translates."""
    return JSONResponse(
        status_code=_status(error),
        content={"detail": error.message, "code": error.code},
    )

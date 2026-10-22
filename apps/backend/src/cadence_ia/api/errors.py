"""Turn the use cases' errors into HTTP responses."""

from fastapi import Request
from fastapi.responses import JSONResponse

from cadence_ia.services.errors import (
    Conflict,
    InvalidInput,
    NotFound,
    ServiceError,
    Unavailable,
)

STATUS = {NotFound: 404, InvalidInput: 422, Conflict: 409, Unavailable: 503}


async def service_error_handler(request: Request, error: ServiceError) -> JSONResponse:
    """`detail` keeps FastAPI's usual shape; `code` is what the frontend translates."""
    return JSONResponse(
        status_code=STATUS.get(type(error), 500),
        content={"detail": error.message, "code": error.code},
    )

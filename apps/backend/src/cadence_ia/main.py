"""Run with: uvicorn cadence_ia.main:create_app --factory --reload"""

from fastapi import FastAPI, Request

from cadence_ia.api import router
from cadence_ia.api.errors import service_error_handler
from cadence_ia.config import Settings
from cadence_ia.frontend import mount_frontend
from cadence_ia.services.errors import ServiceError


async def no_cache_for_api(request: Request, call_next):
    """API data changes (new workouts every 15 min): never let Safari reuse an old copy."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Without `settings`, they are read from the environment."""
    settings = settings or Settings.from_env()
    app = FastAPI(title="cadence-ia", version="0.1.0")
    app.state.settings = settings
    app.middleware("http")(no_cache_for_api)
    app.add_exception_handler(ServiceError, service_error_handler)
    app.include_router(router)
    # In production (Docker) static_dir points to the compiled frontend.
    # Mounted last: its catch-all route must not shadow the API routes.
    if settings.static_dir:
        mount_frontend(app, settings.static_dir)
    return app

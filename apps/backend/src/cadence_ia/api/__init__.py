from fastapi import APIRouter

from cadence_ia.api.routes import health, sessions, workout_types

router = APIRouter()
for module in (health, sessions, workout_types):
    router.include_router(module.router)

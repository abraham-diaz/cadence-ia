from fastapi import APIRouter

from cadence_ia.api.routes import health, plans, sessions, workout_types

router = APIRouter()
for module in (health, sessions, workout_types, plans):
    router.include_router(module.router)

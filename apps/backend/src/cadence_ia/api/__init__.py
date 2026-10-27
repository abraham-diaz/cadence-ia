from fastapi import APIRouter

from cadence_ia.api.routes import exercises, health, muscles, plans, sessions, workout_types

router = APIRouter()
for module in (health, sessions, workout_types, muscles, exercises, plans):
    router.include_router(module.router)

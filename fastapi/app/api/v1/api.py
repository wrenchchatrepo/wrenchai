"""FastAPI v1 API router configuration."""

from fastapi import APIRouter

from app.api.v1.endpoints import agents, tasks, playbooks

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    agents.router,
    prefix="/agents",
    tags=["agents"]
)

api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"]
)

api_router.include_router(
    playbooks.router,
    prefix="/playbooks",
    tags=["playbooks"]
) 
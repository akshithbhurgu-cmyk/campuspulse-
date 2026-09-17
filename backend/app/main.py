from fastapi import FastAPI

from app.api.routes.agent import router as agent_router
from app.api.routes.academic import router as academic_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router

app = FastAPI(title="CampusPulse API", version="0.4.0")
app.include_router(health_router)
app.include_router(academic_router)
app.include_router(dashboard_router)
app.include_router(agent_router)
app.include_router(ingestion_router)

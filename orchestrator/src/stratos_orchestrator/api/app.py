"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stratos_orchestrator.api.routes import router
from stratos_orchestrator.api.decision_routes import router as decision_router
from stratos_orchestrator.api.signals_routes import router as signals_router
from stratos_orchestrator.api.workspace_routes import router as workspace_router
from stratos_orchestrator.config import Settings
from stratos_orchestrator.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("orchestrator_startup")
    yield
    # Shutdown logic
    logger.info("orchestrator_shutdown")


def create_app() -> FastAPI:
    settings = Settings()
    
    app = FastAPI(
        title="STRATOS Agent Orchestrator",
        description="LLM-driven financial agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(decision_router)
    app.include_router(signals_router)
    app.include_router(workspace_router)
    
    return app

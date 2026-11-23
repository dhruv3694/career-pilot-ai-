"""
CareerPilot AI - Main FastAPI Application.
Open-Source-First Agentic Career Intelligence Platform.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db
import app.models.models  # Ensure models are loaded into Base.metadata

from app.api.routes import (
    resumes_router,
    jobs_router,
    matching_router,
    career_router,
    interview_router,
    events_router,
    agents_router,
    memory_router,
    demonstrations_router,
    settings_router,
)

logger = logging.getLogger("careerpilot")
logging.basicConfig(level=logging.INFO if not settings.APP_DEBUG else logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: initialize database on startup."""
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./uploads", exist_ok=True)
    try:
        await init_db()
        logger.info("CareerPilot AI database initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize database.")
        raise
    yield


app = FastAPI(
    title="CareerPilot AI API",
    description="Open-Source-First Agentic Career Intelligence Platform with multi-agent orchestration.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(resumes_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(matching_router, prefix="/api")
app.include_router(career_router, prefix="/api")
app.include_router(interview_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(memory_router, prefix="/api")
app.include_router(demonstrations_router, prefix="/api")
app.include_router(settings_router, prefix="/api")


@app.get("/")
async def root():
    index_file = os.path.join(frontend_dist, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return {
        "name": "CareerPilot AI",
        "tagline": "Open-Source-First Agentic Career Intelligence Platform",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "status": "operational",
    }


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "platform": "CareerPilot AI",
        "multi_agent_system": "LangGraph Active (6 specialized agents + Supervisor)",
        "mcp_server": "Enabled (13 tools registered)",
        "offline_deterministic_fallback": "Ready",
    }


project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
frontend_dist = os.path.join(project_root, "frontend", "dist")


@app.get("/{frontend_path:path}", include_in_schema=False)
async def serve_frontend(frontend_path: str):
    """Serve built assets and support direct navigation to frontend routes."""
    if frontend_path == "api" or frontend_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    index_file = os.path.join(frontend_dist, "index.html")
    if not os.path.isfile(index_file):
        raise HTTPException(status_code=404, detail="Not Found")

    requested_file = os.path.realpath(os.path.join(frontend_dist, frontend_path))
    try:
        within_frontend = os.path.commonpath((frontend_dist, requested_file)) == os.path.realpath(frontend_dist)
    except ValueError:
        within_frontend = False
    if not within_frontend:
        raise HTTPException(status_code=404, detail="Not Found")
    if os.path.isfile(requested_file):
        return FileResponse(requested_file)
    return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.APP_DEBUG)

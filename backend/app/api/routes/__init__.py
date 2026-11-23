from app.api.routes.resumes import router as resumes_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matching import router as matching_router
from app.api.routes.career import router as career_router
from app.api.routes.interview import router as interview_router
from app.api.routes.events import router as events_router
from app.api.routes.agents import router as agents_router
from app.api.routes.memory import router as memory_router
from app.api.routes.demonstrations import router as demonstrations_router
from app.api.routes.settings import router as settings_router

__all__ = [
    "resumes_router",
    "jobs_router",
    "matching_router",
    "career_router",
    "interview_router",
    "events_router",
    "agents_router",
    "memory_router",
    "demonstrations_router",
    "settings_router",
]


# PROJECT_CONTEXT_FOR_AI.md

## Quick Reference
- **Name**: CareerPilot AI — Agentic Career Intelligence & ATS Validation System
- **Type**: Full-stack web app (React + FastAPI)
- **Location**: Repository root
- **Backend**: http://127.0.0.1:8000 (FastAPI)
- **Frontend**: http://127.0.0.1:5173 (Vite dev) or built to frontend/dist
- **Database**: SQLite at backend/data/careerpilot.db

## Tech Stack Summary
Frontend: React 18, TypeScript, Vite, TailwindCSS, React Router v6
Backend: FastAPI, SQLAlchemy (async), LangGraph, Pydantic
LLMs: Gemini, Grok/xAI, Groq + deterministic fallback
Storage: SQLite + in-memory stores for some features

## Key Files to Understand
### Backend Entry
- `backend/app/main.py` - FastAPI app, lifespan, routes, static serving
- `backend/app/core/config.py` - Settings via pydantic-settings
- `backend/app/core/database.py` - DB setup
- `backend/app/llm/manager.py` - Multi-provider LLM orchestration
- `backend/app/agents/workflow.py` - LangGraph multi-agent system

### Frontend Entry
- `frontend/src/App.tsx` - Routes
- `frontend/src/main.tsx` - Entry point
- `frontend/src/services/api.ts` - API client

### Routes (Backend)
- `/api/resumes/*` - Resume upload/parse/ATS
- `/api/jobs/*` - Job search/discovery
- `/api/matching/*` - Job matching
- `/api/career/*` - Career roadmap
- `/api/interview/*` - Interview lab
- `/api/events/*` - Career events
- `/api/agents/*` - Agent workflows
- `/api/memory/*` - Memory & privacy
- `/api/settings/*` - Settings & approvals
- `/api/demonstrations/*` - Demos

## Running the Project
```bash
# Backend
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm run dev
```

## Environment Variables
Key vars in `.env` (see `.env.example`):
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `XAI_API_KEY`, `GROK_MODEL`
- `GROQ_API_KEY`, `GROQ_MODEL`
- `LLM_PROVIDER_PRIORITY=gemini,xai,groq`
- `SEARXNG_URL`, `SEARXNG_ENABLED`
- `DATABASE_URL=sqlite+aiosqlite:///./data/careerpilot.db`

## Current Status
- All 51 backend tests passing
- Frontend builds successfully
- All major pages implemented
- Multi-agent system functional
- LLM fallback working

## Development Notes
- Don't modify .env with secrets inappropriately
- Tests use mocks where external APIs needed
- Frontend uses fetch to `/api/*`
- Backend serves frontend in production
- Uses in-memory stores for some features (approvals, workflow runs) alongside DB

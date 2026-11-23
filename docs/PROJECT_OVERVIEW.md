# PROJECT_OVERVIEW.md

## Project Name
CareerPilot AI — Agentic Career Intelligence & ATS Validation System

## Product Purpose
CareerPilot AI is an agentic career intelligence platform that helps job seekers analyze resumes, validate against ATS systems, discover jobs, compare matches, build career roadmaps, prepare for interviews, and track job search activities using AI agents and multi-provider LLM integration.

## Target Users
- Job seekers (students, graduates, professionals)
- Career counselors
- HR/recruiting professionals exploring candidate matching
- Educational institutions supporting placements

## Core Workflows
1. **Resume Analysis**: Upload PDF/DOCX, parse, extract profile, run ATS validation
2. **Job Discovery**: Search across Greenhouse, Lever, and web sources
3. **Job Matching**: Compare resume against job requirements with scoring
4. **Career Planning**: Generate personalized roadmaps with milestones
5. **Interview Preparation**: Practice with role-specific questions and feedback
6. **Agent Orchestration**: Multi-agent workflow for end-to-end intelligence
7. **Memory & Privacy**: Manage stored preferences and data
8. **Approvals & Settings**: Configure providers and manage consequential actions

## Technology Stack
### Frontend
- React 18.3.1 with TypeScript 5.6.3
- Vite 5.4.8 (build tool)
- React Router DOM 6.26.2
- Tailwind CSS 3.4.13
- Lucide React (icons)
- Recharts 2.13.0 (charts)
- Axios-style fetch API client

### Backend
- FastAPI 0.115.0 (Python web framework)
- Uvicorn (ASGI server)
- Pydantic 2.9.2 / pydantic-settings 2.5.2
- SQLAlchemy 2.0.35 with aiosqlite
- LangGraph 0.2.28 (agent orchestration)
- MCP SDK 1.1.0
- ChromaDB 0.5.5 + sentence-transformers 3.1.1 (vector store)

### LLM Providers
- Google Gemini (google-generativeai 0.8.1) - gemini-2.5-flash
- xAI Grok (via HTTP API) - grok-4.7
- Groq (groq 0.11.0) - llama-3.1-70b-versatile
- Deterministic fallback engine

### Document Processing
- PyMuPDF (pymupdf 1.24.10) for PDF
- python-docx 1.1.2 for DOCX
- BeautifulSoup4 4.12.3 + lxml 5.3.0

## Current Status
- Backend: Functional with all major routes implemented
- Frontend: All pages implemented and built successfully
- Tests: 51/51 backend tests passing
- Build: Frontend builds without errors
- Database: SQLite (aiosqlite) initialized
- Agents: LangGraph multi-agent system implemented

## Known Limitations
- Some external APIs require configuration/keys
- SearXNG needs to be enabled for web search
- Gemini/Grok may be unavailable without API keys (falls back to deterministic)
- Some features use in-memory stores alongside database

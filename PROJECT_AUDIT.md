# CareerPilot AI — Repository Audit and Technical Documentation

## 1) Project identity and purpose

### A. Non-technical explanation
CareerPilot AI is a career-intelligence application for job seekers. It helps a user upload or paste a resume, extract structured candidate information, run ATS-style checks, discover public jobs, compare a resume against a job description, plan a career roadmap, and review interview preparation material. The system is meant to be an "agentic" career assistant: multiple specialized AI workflows coordinate to parse documents, search job boards, reason about gaps, and propose next actions.

In plain terms, the project tries to act like a personal career copilot: it reads resume data, looks for relevant jobs, identifies skill mismatches, and suggests training or interview prep paths.

### B. Technical overview
The repository is split into:
- backend/: FastAPI application with routes, service layer, models, AI providers, MCP tools, memory, and agents.
- frontend/: React + TypeScript app with Vite and Tailwind CSS.
- data/: SQLite database storage.
- uploads/: temporary resume upload handling.
- docs/ and root docs: project documentation and status files.

The backend currently exposes a set of API modules under `/api` for resumes, jobs, matching, career, interview, events, agents, memory, demonstrations, and settings. Models are defined with SQLAlchemy 2.0 and created at startup with `Base.metadata.create_all()`. The application relies on SQLite by default via `sqlite+aiosqlite:///./data/careerpilot.db`.

### C. Academic explanation
The project attempts to demonstrate agentic AI concepts:
- specialized agents organized around resume parsing, job discovery, matching, career planning, interviews, and workflow supervision;
- tool use via an MCP-style tool registry; 
- memory management for user preferences, saved jobs, and resume evidence retrieval;
- workflow orchestration with LangGraph;
- graceful degradation through provider fallback (Groq / Gemini / xAI / deterministic fallback);
- privacy-oriented working memory and long-term memory management.

The strongest implemented academic concepts are the LangGraph workflow shell, MCP tool registry, provider fallback chain, and memory/evidence indexing. The project is less complete as a production-grade autonomous system because it still relies heavily on in-memory stores and rule-based fallback logic rather than fully persistent workflow state.

---

## 2) Repository structure and actual implementation status

### Major directories

- backend/app/main.py — FastAPI application entry point and startup lifecycle.
- backend/app/api/routes/ — HTTP route modules for each domain.
- backend/app/services/ — domain services including resume parsing, job discovery, ATS validation, matching, career planning, events, and interview logic.
- backend/app/models/models.py — SQLAlchemy ORM definitions.
- backend/app/llm/ — LLM provider adapters and manager.
- backend/app/mcp/ — MCP server and tool registry.
- backend/app/memory/ — preference and vector-memory management.
- backend/app/agents/ — workflow orchestration and agent graph.
- frontend/src/ — React SPA source files.
- frontend/package.json — frontend dependency manifest.
- backend/requirements.txt — backend dependencies.
- .env.example — safe template for environment variables.

### Repository inventory (key files)

| File path | Purpose | Main contents | Dependencies | Status | Notes |
|---|---|---|---|---|---|
| backend/app/main.py | API bootstrap | Creates FastAPI app, startup DB init, CORS, route registration, frontend asset serving | app.core.config, database, routes | Active | Exposes `/api/health` and serves built frontend assets |
| backend/app/core/config.py | Env-driven configuration | Settings object with provider keys, DB URL, app port, upload limits, CORS origins | pydantic-settings | Active | Reads `.env` and exposes helper properties |
| backend/app/core/database.py | DB engine and startup setup | Async SQLAlchemy engine, sessionmaker, init_db | SQLAlchemy | Active | SQLite default |
| backend/app/models/models.py | Domain persistence model layer | CandidateProfile, ResumeDocument, JobListing, JobMatch, MemoryEntry, InterviewSession, etc. | Base metadata | Active | Large model set, though not every feature is fully persistent in practice |
| backend/app/services/resume/parser.py | Resume extraction | PDF / DOCX / TXT parsing, scanned PDF detection, text normalization, quality scoring | pymupdf, python-docx | Active | Robust parser; passes dedicated unit tests |
| backend/app/services/resume/ats.py | ATS validation | Extracted profile generation and ATS scoring | deterministic rules | Active | Core ATS engine |
| backend/app/api/routes/resumes.py | Resume upload and analysis endpoints | Upload, parse text, retrieve profile, ATS compare, LLM review | parser, ats, memory_manager | Active | Uses in-memory `RESUME_STORE` instead of DB persistence |
| backend/app/services/jobs/discovery.py | Public job aggregation | Greenhouse + Lever + SearXNG orchestration, dedupe, ranking | adapters | Active | Search and dedup logic implemented |
| backend/app/api/routes/jobs.py | Job discovery API | Search, verify, save, list saved jobs | discovery, memory_manager | Active | Contains route mismatches relative to frontend service contract |
| backend/app/mcp/tools.py | MCP tool registry | 13 tool wrappers with sanitization and validation | services, memory, vector store | Active | Central tool catalog |
| backend/app/mcp/server.py | MCP server exposure | Registers tools with FastMCP if available | mcp.tools | Active | Optional if `mcp` SDK is installed |
| backend/app/llm/manager.py | LLM provider broker | Ordered provider fallback chain | groq/gemini/xai providers | Active | Deterministic fallback when external providers fail |
| backend/app/agents/workflow.py | Multi-agent orchestration | LangGraph workflow graph and specialized agent classes | langgraph, services | Active | Implements an orchestrated workflow shell |
| backend/app/memory/memory_manager.py | User memory | preferences, saved jobs, working memory, resume evidence indexing | vector_store | Active | In-memory memory, not persistent DB |
| frontend/src/App.tsx | Application routing | Defines all app routes of the dashboard and feature pages | pages/* | Active | App shell and route registrations |
| frontend/src/services/api.ts | Frontend API client | Fetch wrappers for resumes/jobs/matching/career/interview/events, etc. | backend routes | Active | Some route names do not align with backend contracts |
| frontend/src/pages/*.tsx | Feature pages | Dashboard, Resume Studio, Job Explorer, ATS Validation, roadmap, interviews, settings, demos | api.ts | Active / partially wired | Pages exist visually and are routed; implementation status varies |
| backend/tests/unit/*.py | Test suite | Startup, parser, jobs, matching, MCP, LLM fallback, xAI provider | pytest | Active | Good evidence of key functionality |

---

## 3) Frontend architecture

### Stack
- React 18
- TypeScript
- Vite
- Tailwind CSS
- react-router-dom
- lucide-react
- Recharts

### Routing and app shell
The root app shell is defined in `frontend/src/App.tsx`. The SPA routes include:
- `/` -> Dashboard
- `/resume-studio` -> ResumeStudio
- `/ats-validation` -> ATSValidation
- `/jobs` -> JobExplorer
- `/matching` -> JobMatchComparison
- `/roadmap` -> CareerRoadmap
- `/interview` -> InterviewLab
- `/events` -> CareerFairsEvents
- `/agents` -> AgentControlCenter
- `/memory` -> MemoryPrivacy
- `/settings` -> ApprovalsSettings
- `/demonstrations` -> Demonstrations

### State and data flow
The frontend is not using a large Redux/Zustand store. Instead, it relies on local state and `sessionStorage` for transient session objects such as `careerpilot.resumeId` and `careerpilot.recentJobs`. Fetching is done directly with native `fetch` wrappers in `frontend/src/services/api.ts`.

### Actual implementation confidence
The frontend clearly renders multiple feature pages and offers a polished dashboard-oriented experience. The implemented user flows include:
- resume upload and paste ingestion;
- ATS validation UI;
- public job search UI;
- career roadmap and interview planning screens;
- settings / memory / agent workflows UI.

### Architectural caveats
Several front-end calls are not consistent with the backend contract. Examples include:
- `api.searchJobs()` posts JSON with `sources` and `limit`, while the backend `JobSearchRequest` model expects `source` (singular) and not a `sources` list.
- `api.getSavedJobs()` calls `/api/jobs/saved/list`, but the backend route is `/api/jobs/saved`.
- The frontend uses `saveJob` for a toggling pattern that is inconsistent with the backend’s save/unsave semantics and appears likely to mis-handle the saved-checkbox logic.

This does not mean the UI is entirely broken, but it does mean the frontend and backend are not yet synchronized to a single, production-quality API contract.

---

## 4) Backend architecture

### Framework and application lifecycle
The backend is a FastAPI application initialized in `backend/app/main.py`. The startup process calls `init_db()` from `backend/app/core/database.py` and ensures `./data` and `./uploads` exist. The app config is read from environment variables and `.env` using `pydantic-settings`.

### Route organization
The main routes are:
- `/api/resumes` — resume upload, parsing, ATS, profile review
- `/api/jobs` — job discovery, saved-job persistence, job verification
- `/api/matching` — resume-to-job matching logic
- `/api/career` — career roadmap generation and progress tracking
- `/api/interview` — interview session creation and evaluation
- `/api/events` — career events search
- `/api/agents` — LangGraph workflow execution and traces
- `/api/memory` — user preferences and memory management
- `/api/demonstrations` — scenario runner / walkthrough showcase
- `/api/settings` — provider settings and approvals inventory

### Persistence model
The project does define a SQLAlchemy model layer in `backend/app/models/models.py`, including tables such as `candidate_profiles`, `resume_documents`, `resume_assessments`, `job_listings`, `job_matches`, `career_preferences`, `interview_sessions`, `memory_entries`, and workflow-related tables. This is a strong architectural indicator that the application intends to be database-backed. However, a number of runtime stores remain in-memory dictionaries in route modules rather than using the ORM in any consistent way, especially for resumes and workflow runs.

### Important implementation realization
The app is partially "full-stack working" and partially "architectural prototype". It has actual HTTP routes, service classes, test coverage, and UI pages, but the persistence story is not fully implemented end-to-end.

---

## 5) Core product workflows

### Workflow 1: resume ingestion
User can either upload a PDF/DOCX/TXT file or paste raw text. The `ResumeParser` extracts text and metadata, flags scanned PDFs, and normalizes common Unicode / whitespace issues.

Flow:
1. frontend uploads file through `/api/resumes/upload` or `/api/resumes/parse-text`
2. `ResumeParser` extracts content
3. `ats_validator.extract_structure()` builds a structured candidate profile
4. ATS score is computed and returned to UI
5. result is stored in `RESUME_STORE` in memory for session access

This is functionally working in the current environment and tested.

### Workflow 2: job discovery
The app searches multiple external job sources:
- Greenhouse boards
- Lever companies
- SearXNG meta-search (optional)

The discovery flow is orchestrated by `JobDiscoveryService` in `backend/app/services/jobs/discovery.py`, deduplicating and ranking results by relevance before returning them to the API layer.

### Workflow 3: matching and career guidance
The app includes logic for:
- resume-to-job match scoring;
- skill-gap analysis;
- career roadmap generation;
- interview preparation workflows;
- event discovery and memory-driven preferences.

These modules are present and appear designed for a more complete assistant experience, but not all endpoints are equally complete or fully backed by persisted data.

### Workflow 4: multi-agent orchestration
The `backend/app/agents/workflow.py` file defines a LangGraph-based workflow with a supervisor and specialized agents. The route `POST /api/agents/run` invokes this workflow and serializes the run record. This is a significant project feature and one of the main architectural differentiators.

---

## 6) AI provider and tool integration

### LLM providers
The project attempts to support multiple LLM providers through `backend/app/llm/manager.py`:
- Groq
- Gemini
- xAI / Grok
- deterministic fallback engine

The configuration comes from `.env` or environment variables, as seen in `.env.example`. Provider priority is set by `LLM_PROVIDER_PRIORITY` and defaults to `gemini,xai,groq`.

### MCP layer
The `backend/app/mcp/` package exposes a tool registry with security-oriented wrappers for:
- parsing resume documents;
- validating resume text;
- analyzing resumes against jobs;
- web search;
- Greenhouse / Lever job queries;
- event search;
- verification of public listing URLs;
- job matching;
- evidence retrieval;
- career roadmap generation;
- preference saving and learning progress updates.

This is an important design feature: the project is not just a web app; it is also structured around tool-use patterns and external service abstraction.

### Security focus in tools
The MCP tool layer explicitly sanitizes untrusted text and validates file paths to defend against prompt injection and path traversal. This is a real implementation detail and a notable design decision.

---

## 7) Data and memory architecture

### Database
The default database is SQLite with `aiosqlite`, created in `data/careerpilot.db` by `init_db()` on startup; the app also creates `./uploads`. This is a real persistence layer and is used for ORM models.

### In-memory state
However, several user workflows still store state in Python dictionaries instead of the database:
- `RESUME_STORE` in `backend/app/api/routes/resumes.py`
- `WORKFLOW_RUNS` in `backend/app/api/routes/agents.py`
- `memory_manager` in `backend/app/memory/memory_manager.py` uses Python dictionaries, not a database-backed store

This creates a practical limitation: restart or redeploy can lose session and memory state even if the database is present. It is a real architectural gap, not just a hypothetical concern.

### Privacy and long-term memory
There is an explicit privacy-aware memory model with concepts like `UserPreferences`, `WorkingMemory`, and `purge_user_data()`. This is conceptually aligned with GDPR-style consent and memory deletion, but the implementation is still primitive and mostly in-memory.

---

## 8) Testing and evidence status

The repository includes a meaningful test suite under `backend/tests/unit` covering:
- app startup
- ATS validation
- job adapter behavior
- job search API behavior
- LLM fallback logic
- matching and roadmap logic
- MCP tool behavior
- resume parser behavior
- xAI provider behavior

These tests are an important signal that the project is not just a loose prototype: the resume parsing and job discovery flows have been validated in code. The current audit also confirms the resolver behavior and the unit tests run cleanly in the local environment for the resume parser suite.

---

## 9) Implementation gaps, mismatches, and risks

### High-confidence issues
1. Frontend/backend API contract mismatch for job search
   - `frontend/src/services/api.ts` uses `sources` and `limit` when posting to `/api/jobs/search`.
   - `backend/app/api/routes/jobs.py` expects `source` and `work_mode`, not a `sources` list.
   - This means the UI contract is not aligned with the backend schema.

2. Saved-job API mismatch
   - Frontend calls `/api/jobs/saved/list`.
   - Backend defines `/api/jobs/saved` only.
   - This likely breaks saved-job retrieval in the UI.

3. Resume and workflow state are not truly persistent
   - `RESUME_STORE` and `WORKFLOW_RUNS` are in-memory dictionaries.
   - A restart clears those records.

4. Not all UI pages are backed by fully real data flows
   - Pages render, but some interactions rely on incomplete or mocked-like logic that is not strongly validated by persisted backend data.

5. External provider integration is optional and may be unavailable without environment configuration
   - The app can degrade to deterministic fallback, but real LLM-backed features depend on keys being set and external services being reachable.

### Architectural maturity observations
The project is more advanced than a basic mockup and includes serious domain logic, tool abstractions, multi-agent workflows, and multiple external data sources. It is, however, still best described as a "feature-complete prototype with partial backend integration and persistent-state gaps." That distinction matters for academic, deployment, and handoff purposes.

---

## 10) Actual status summary

### Implemented well
- Resume parser and ATS extraction
- Public job discovery with multiple sources
- API routing with multiple endpoints
- Frontend route shell and core pages
- LangGraph workflow scaffold
- MCP tool registry and security wrappers
- Multi-provider LLM fallback infrastructure

### Partially implemented / inconsistent
- Database persistence for all user workflows
- Full service-to-service API consistency
- End-to-end persistence for memory and workflow state
- Production-ready auth / user management
- Deployment and operational monitoring configuration

### Plausibly planned but not yet production-validated
- Full autonomous agent decision making and approval flows
- Persistent long-term memory beyond in-memory stores
- Deep external integration validation across real jobs / events / LLM APIs
- Production security, audit logging, and user governance

---

## 11) Conclusion
CareerPilot AI is a real, structured project with a strong conceptual architecture: resume intelligence + ATS validation + job discovery + AI-driven career guidance + multi-agent orchestration. It is not merely a landing page or static mockup. It contains a meaningful codebase and actual service logic across frontend, backend, AI providers, and job-source adapters.

The strongest statement supported by the repository is: this is an active prototype / platform skeleton with a good architectural foundation and genuine feature implementation, but it still has important gaps between the frontend experience, backend contracts, and full persistence / production readiness.

This is therefore best understood as a strong developer prototype with some complete flows and some partial or intentionally simulated components, not yet a fully hardened production product.

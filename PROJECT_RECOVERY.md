# CareerPilot AI Project Recovery

## Starting point and architecture

The project has a FastAPI backend under `backend/app`, using SQLAlchemy models, LangGraph workflows, MCP tools, resume/job/event/matching/career/interview services, and Gemini/Groq providers with deterministic fallback. The React 18/Vite frontend is under `frontend/src`; it previously had a dashboard and resume studio but no application entry point or router. No project README, progress notes, migrations, or frontend tests were present. No `.env` file is present; `.env.example` documents optional provider/search settings and the local SQLite URL. Previous conversation history was not available, so the current source and the supplied requirements were used to establish the stopping point.

Git is initialized at the parent user-home directory, not the project folder. The project directory is untracked and has no project-scoped commit history; unrelated pre-existing home-directory changes were left untouched.

## Requirements audit

| Area | Status | Verified state and remaining work |
|---|---|---|
| Resume parsing and deterministic ATS | PARTIAL | Upload/paste APIs and PDF/DOCX parsing, structured extraction, reports, and tests exist. Resume/profile data is held in process memory; durable storage remains. Matching now requires a reviewed profile saved through Resume Studio. |
| LLM resume review | PARTIAL | Analyzer and provider router exist. No credentials are configured in this checkout; verify provider behavior using mocks and complete the review UI. |
| Job discovery and verification | PARTIAL | Job Explorer now queries Greenhouse/Lever feeds and optional SearXNG, shows query/source/retrieval metadata, saves listings, removes fabricated search fixtures, and reports unconfigured web search. Saved jobs remain process-local; no Google CSE integration is configured. |
| Career events | PARTIAL | Discovery service and API exist, but curated entries are presented as verified without demonstrated source checks; harden provenance and verification. |
| Agent workflow and traces | PARTIAL | LangGraph workflow, API run records, and integration tests exist. Run history and some workflow state are in-memory; persistence and frontend trace views remain. |
| MCP tools/server | PARTIAL | MCP tool and server modules exist, with unit coverage. Validate transport/startup and complete integration with the UI/workflows. |
| Memory and retrieval | PARTIAL | Local vector retrieval exists, but preferences, saved jobs, progress, and interviews are stored in Python dictionaries rather than the configured SQLite database. |
| Provider failover | PARTIAL | Gemini-primary → xAI Grok → optional Groq → deterministic fallback is configured; the xAI Responses adapter uses `store: false` and mocked failover tests. API keys are unset; the Gemini SDK remains deprecated. |
| Frontend | PARTIAL | React entry point/router, Dashboard, Resume Studio, ATS Validation, Job Explorer, and Job Match Comparison are implemented; remaining sidebar destinations state that their UI is unavailable rather than implying completed screens. |
| Startup and production serving | PARTIAL | FastAPI routes are registered. Static frontend serving previously resolved the build directory under `backend/frontend`; the path is corrected to the project-level `frontend/dist`. Verify with the smoke check below. |

## Work completed in this recovery

- Added the React entry point and router shell; kept the existing dashboard and resume studio.
- Made non-implemented navigation destinations explicit rather than rendering fake results.
- Replaced hard-coded dashboard scores, job/event counts, and fabricated success-on-error behavior with backend run/provider status and visible errors.
- Removed the prefilled fictional resume so ATS analysis only runs on user-provided content.
- Corrected FastAPI static serving to resolve the project-level frontend build and support SPA navigation while preserving API 404s.
- Changed the navbar and sidebar to avoid reporting provider status as healthy before it is known or the workflow graph as actively running.
- Hardened PDF/DOCX/TXT parsing and upload validation, added scanned-PDF `needs_ocr` reporting, temporary file cleanup, and synthetic parser/upload tests.
- Added an ATS report page connected to the saved-in-session resume ID and job comparison endpoint; report results remain process-local until backend persistence is implemented.
- Added an API-backed Job Explorer with filters, source and retrieval metadata, truthful listing status, saved-job operations, and empty/partial/error states; removed hard-coded job search fixtures and added mock-source tests.
- Implemented Job Match Comparison with explicit required/preferred skills, saved/recent jobs or user-provided job descriptions, evidence-backed skill classification, transparent deterministic score weights, database-backed comparison history, delete/export controls, and a gate requiring the candidate to review and save the extracted profile. URL fetching and external AI interpretation are explicitly not enabled.
- Added `PROJECT_AUDIT.md` with status and root cause for each advertised feature and the next work sequence.

## Verification

- `cd frontend && npm run build` — passed (TypeScript and Vite production bundle).
- `cd backend && python -m pytest -q` — 51 tests passed after Job Match Comparison. Existing warnings include deprecated `fitz` imports, the deprecated `google.generativeai` SDK, and `datetime.utcnow()`.
- Frontend production build after Job Match Comparison — passed (TypeScript and Vite).
- FastAPI `TestClient` startup/static-serving smoke test — passed against an in-memory SQLite database: root HTML, `/resume-studio` SPA fallback, `/api/health`, API 404 behavior, and built JS asset all returned expected responses.
- Resume parser/API regression tests — passed for synthetic PDFs/DOCX/TXT, malformed and unsupported content, scan detection, upload cleanup and API analysis round trip.
- Job discovery API/adapter tests — passed with mocked sources; live Greenhouse smoke test returned 20 source-backed listings and surfaced one unavailable board as a partial-source warning.
- xAI provider tests — passed with mocked Responses API replies, JSON mode, HTTP failure tracking, and Gemini-to-xAI failover. No xAI or Gemini credentials are configured in this checkout.
- Current app servers are running on ports 8000 and 5173. Backend health is `healthy`; provider status lists `gemini`, `xai`, `groq`, and deterministic fallback in that priority order. External provider credentials are not configured, so the deterministic engine is the available provider. The backend was restarted after checking the previous process had zero workflow runs and saved jobs; any process-local resumes would also have been lost. The new process has not received state-changing requests.

## Next implementation steps

1. Configure a supported broad job search source (SearXNG is optional and self-hosted); evaluate Google CSE only if the user already has eligible credentials, given its published availability and retirement limits.
2. Persist resume records/reports, preferences, saved jobs, progress, approvals and workflow runs; provide a non-destructive database upgrade path.
3. Implement remaining advertised frontend workflows (roadmap, interview, events, agent traces, memory and settings) and focused frontend tests.
4. Add authentication, consent and per-user data separation before real candidate data is used.
5. Migrate Gemini to the maintained `google-genai` SDK; configure credentials outside source control, then verify structured output/failover and MCP transport with mocked integrations.

## Run commands and configuration

- Backend: `cd backend; python -m uvicorn app.main:app --reload`
- Backend tests: `cd backend; python -m pytest -q`
- Frontend dev server: `cd frontend; npm run dev`
- Frontend production build: `cd frontend; npm run build`
- For production static serving, build the frontend before starting FastAPI.
- Copy `.env.example` to `.env` only if needed. Optional keys include `GROQ_API_KEY`, `GEMINI_API_KEY`, and SearXNG settings; never commit secret values.

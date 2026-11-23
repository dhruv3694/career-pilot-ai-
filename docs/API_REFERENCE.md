# API_REFERENCE.md

## API Base
- Prefix: `/api`
- Backend: FastAPI with automatic docs at `/docs`

## Key Endpoints

### Resumes
- `POST /api/resumes/upload` - Upload PDF/DOCX
- `POST /api/resumes/parse-text` - Parse raw text
- `GET /api/resumes/{resume_id}` - Get resume details
- `PUT /api/resumes/{resume_id}/profile` - Update profile
- `POST /api/resumes/{resume_id}/llm-review` - LLM review
- `POST /api/resumes/analyze-against-job` - Analyze against job

### Jobs
- `GET /api/jobs/search` - Search jobs (query params)
- `POST /api/jobs/search` - Search jobs (JSON body) - **ADDED**
- `POST /api/jobs/verify` - Verify job URL
- `GET /api/jobs/saved` - Get saved jobs
- `POST /api/jobs/save` - Save job
- `DELETE /api/jobs/saved/{job_id}` - Unsave job

### Matching
- `POST /api/matching/calculate` - Calculate match
- `GET /api/matching/saved/{resume_id}` - Get saved matches
- `DELETE /api/matching/saved/{match_id}` - Delete match

### Career
- `POST /api/career/roadmap` - Generate roadmap
- `GET /api/career/progress` - Get progress
- `POST /api/career/progress/update` - Update progress

### Interview
- `GET /api/interview/roles` - List roles
- `POST /api/interview/session/start` - Start session
- `POST /api/interview/evaluate` - Evaluate answer

### Events
- `GET /api/events/search` - Search events
- `GET /api/events/discover` - Discover events - **ADDED**
- `POST /api/events/reminders/opt-in` - Opt-in to reminders

### Agents
- `POST /api/agents/run` - Run workflow
- `GET /api/agents/runs` - List runs
- `GET /api/agents/runs/{run_id}` - Get run details

### Memory
- `GET /api/memory/` - Get memories
- `GET /api/memory/preferences` - Get preferences
- `POST /api/memory/preferences` - Save preference
- `DELETE /api/memory/{memory_id}` - Delete memory

### Settings
- `GET /api/settings/providers` - Provider status
- `GET /api/settings/compliance-inventory` - Compliance info
- `GET /api/settings/approvals` - List approvals
- `POST /api/settings/approvals/{id}/decision` - Decide approval

### Demonstrations
- `GET /api/demonstrations/` - List demos - **ADDED**
- `POST /api/demonstrations/scenario-{a-f}` - Run scenario

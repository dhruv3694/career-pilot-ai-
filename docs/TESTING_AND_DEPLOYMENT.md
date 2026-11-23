# TESTING_AND_DEPLOYMENT.md

## Testing Status
- **Backend Tests**: 51 passed, 15 warnings (as of last run)
- **Frontend Build**: Successful (vite build completes)
- **Test Framework**: pytest with asyncio

## Running Tests
```bash
cd backend
python -m pytest -v
```

## Build
```bash
cd frontend
npm run build
```

## Development Startup
```bash
# Terminal 1 - Backend
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

## Production
Backend serves frontend static files from `frontend/dist` if built.

## Test Coverage
Tests cover:
- LLM fallback mechanisms
- ATS validation
- Resume parsing
- Job adapters
- Matching and roadmap
- Multi-agent workflows
- MCP tools
- Failure scenarios

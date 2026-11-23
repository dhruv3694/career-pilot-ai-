# BUGS_AND_TECHNICAL_DEBT.md

## Issues Fixed During Recent Work
1. **Job Explorer 405 Method Not Allowed** - Fixed by adding POST route `/api/jobs/search` alongside GET
2. **Career Events returning no results** - Fixed by adding `/api/events/discover` endpoint and updating frontend to display data correctly
3. **Jury Demonstrations empty** - Fixed by adding GET `/api/demonstrations/` endpoint with scenario list
4. **API client mismatches** - Fixed various method calls to match backend

## Current Known Issues
1. **Provider Status** - Gemini/Grok may show unavailable without API keys (by design, falls back to deterministic)
2. **In-memory stores** - Some features use in-memory (approvals, workflow runs) which don't persist across restarts
3. **Mixed data persistence** - Some features use database, others use memory_manager
4. **Deprecation warnings** - Using older google.generativeai package, datetime.utcnow() usage

## Technical Debt
- **High**: Some routes use in-memory storage that won't survive restarts
- **Medium**: Mixed patterns for data persistence
- **Medium**: Some API responses have inconsistent schemas
- **Low**: Deprecation warnings from dependencies
- **Low**: TypeScript strictness could be improved

## Recommendations
1. Migrate in-memory stores to database for persistence
2. Update to newer google.genai SDK
3. Standardize API response formats
4. Add more comprehensive error handling
5. Improve test coverage for integration scenarios

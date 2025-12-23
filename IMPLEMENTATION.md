# Implementation Plan: OpenOutreach → LinkedIn Automation API Server (FastAPI)

This document tracks **remaining work** for the FastAPI-based automation server.

---

## 7.1) Minimal E2E test strategy (UI automation) for the FastAPI job runner

**Status**: Not yet implemented.

The current `tests/` suite is mostly unit tests (e.g., Voyager parsing). For UI automation, add a separate **E2E layer** that is **skipped by default** and only run intentionally (local/dev), because it requires real LinkedIn accounts and a browser.

### Proposed structure

- `tests/e2e/`
  - `conftest.py`
    - loads account from database (or env) for a dedicated test handle
    - provides fixtures for API client + base URL + API key
    - optional: ensures cookie state exists (or skips with instructions)
  - `test_health.py` (server is reachable)
  - `test_runs_profile_visit.py`
  - `test_runs_connect.py`
  - `test_runs_message.py`
  - `test_runs_post_react.py`
  - `test_runs_post_comment.py`
  - `test_runs_inmail.py`

### Markers (pytest)

Add markers and use them consistently:
- `@pytest.mark.e2e` — requires running server + real LinkedIn UI
- `@pytest.mark.slow` — long-running / brittle flows
- `@pytest.mark.requires_inmail` — only run if the account supports standard LinkedIn InMail UI

Default behavior:
- CI runs only unit tests (no markers)
- E2E tests require explicit opt-in, e.g.:
  - `pytest -m e2e`

### What E2E tests should validate (touchpoint execution aligned)

Each E2E test should exercise the system through the **API**, not by calling action functions directly:
1. `POST /runs` with `handle` + single `touchpoint` (not multiple touchpoints)
2. poll `GET /runs/{run_id}` until terminal state
3. assert:
   - run status transitions: "pending" → "running" → "completed"/"failed"
   - touchpoint result recorded correctly
   - `Run` record in database matches API response
   - optional artifacts exist (screenshot/HTML dump) on failure

This keeps the E2E suite compatible with the architecture (server executes single touchpoints, no workflows).

---

## Completed Phases

The following phases have been completed and are documented here for reference:

- ✅ **Phase 1**: Removed AI + templating (no jinja/langchain imports remain)
- ✅ **Phase 2**: Touchpoint abstraction implemented (`linkedin/touchpoints/` with all touchpoint types)
- ✅ **Phase 3**: FastAPI server with all endpoints (runs, schedules, accounts, health)
- ✅ **Phase 4**: Execution model + scheduler (polling-based scheduler, background worker, account locking)
- ✅ **Phase 5**: All touchpoint implementations complete:
  - ✅ Profile visits (`linkedin/actions/visit.py`)
  - ✅ Post reactions (`linkedin/actions/post_react.py`)
  - ✅ Post comments (`linkedin/actions/post_comment.py`)
  - ✅ InMail (`linkedin/actions/inmail.py`)
- ✅ **Phase 7**: Observability + safety controls (structured logging, screenshots, quotas, circuit breakers)
- ✅ **Phase 8**: Docker/deployment (docker-compose.yml updated, Dockerfile at root, scripts/start runs FastAPI server)

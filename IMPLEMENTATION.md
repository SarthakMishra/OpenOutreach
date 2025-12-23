# Implementation Plan: OpenOutreach → LinkedIn Automation API Server (FastAPI)

This document tracks **remaining work** for the FastAPI-based automation server.

**Status**: Most phases are complete. Remaining work focuses on:
1. Full implementation of placeholder touchpoints (post reactions, comments, InMail)
2. E2E test suite for validation

---

## 5) Phase 5 — Complete touchpoint implementations

### 5.2 Post reactions (Placeholder → Full Implementation)
**Current status**: Placeholder exists in `linkedin/actions/post_react.py` - navigates to post but doesn't interact with UI.

**Remaining work**:
- Research LinkedIn post reaction UI selectors
- Implement hover/press-and-hold behavior to open reaction menu
- Select desired reaction (LIKE/CELEBRATE/SUPPORT/LOVE/INSIGHTFUL/CURIOUS)
- Verify toast/selected state
- Handle UI variants and edge cases

**Files to update**:
- `linkedin/actions/post_react.py` - Complete the `react_to_post()` function
- `linkedin/touchpoints/post_react.py` - Already wraps the action correctly

### 5.3 Post comments (Placeholder → Full Implementation)
**Current status**: Placeholder exists in `linkedin/actions/post_comment.py` - navigates to post but doesn't interact with UI.

**Remaining work**:
- Research LinkedIn comment box selectors (may have variants)
- Implement comment box opening logic (may need to click "Comment" button first)
- Type/paste comment text
- Submit comment
- Verify comment was posted (check for comment in DOM or success toast)

**Files to update**:
- `linkedin/actions/post_comment.py` - Complete the `comment_on_post()` function
- `linkedin/touchpoints/post_comment.py` - Already wraps the action correctly

### 5.4 InMail (Placeholder → Full Implementation)
**Current status**: Placeholder exists in `linkedin/actions/inmail.py` - navigates to profile but doesn't interact with UI.

**Remaining work**:
- Research LinkedIn InMail compose modal selectors (standard UI only, no Sales Navigator)
- Implement premium account detection
- Implement InMail availability detection
- Find and click "Message" or "More actions" menu items that open InMail compose modal
- Detect InMail compose modal (distinguish from regular message modal)
- Fill subject (if provided) and body fields
- Send InMail
- Verify success toast
- Handle error cases:
  - `NOT_AVAILABLE`: InMail option not available
  - `NO_CREDITS`: No InMail credits remaining
  - `UI_CHANGED`: Could not find expected UI elements
  - `BLOCKED`: Recipient has blocked InMail

**Files to update**:
- `linkedin/actions/inmail.py` - Complete the `send_inmail()` function
- `linkedin/touchpoints/inmail.py` - Already wraps the action correctly

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
  - `test_runs_inmail.py` (skipped unless InMail available)

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
- ✅ **Phase 5.1**: Profile visits implemented (`linkedin/actions/visit.py`)
- ✅ **Phase 7**: Observability + safety controls (structured logging, screenshots, quotas, circuit breakers)
- ✅ **Phase 8**: Docker/deployment (docker-compose.yml updated, Dockerfile at root, scripts/start runs FastAPI server)

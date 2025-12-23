# Implementation Plan: OpenOutreach → LinkedIn Automation API Server (FastAPI)

This document is a **step-by-step migration plan** to repurpose the repo into a **FastAPI-based automation server** that runs/schedules LinkedIn automations issued by an API client.

Primary goals:
- **Remove AI + templating entirely** (no Jinja templates, no prompt/LLM plumbing, no message generation in this repo).
- Keep the repo focused on **LinkedIn automation primitives** + a **server** that executes them safely.
- Add new touchpoints:
  - **Explicit profile visits** (not just “visited as a side effect”)
  - **Post interactions** (reactions + comments)
  - **InMail** (best-effort UI automation; premium/SalesNav-dependent)

---

## 0) Current `linkedin/` architecture (what exists today)

**Note**: The campaign system will be removed in Phase 2. Current architecture includes legacy campaign code that will be deleted.

### Legacy Orchestration (to be removed)
- `linkedin/campaigns/connect_follow_up.py`
  - Legacy campaign state machine: `DISCOVERED → ENRICHED → PENDING/CONNECTED → COMPLETED`
  - Uses actions: `profile.scrape_profile`, `connect.send_connection_request`, `message.send_follow_up_message`.
  - **Will be deleted** - replaced with single-step touchpoints

### Browser + session
- `linkedin/sessions/account.py`
  - Owns Playwright `page/context/browser` + per-account SQLite DB session.
  - `ensure_browser()` bootstraps via `linkedin/navigation/login.py`.
  - `wait()` contains opportunistic scraping behavior (optional).
- `linkedin/sessions/registry.py`
  - In-process registry keyed by `(handle, campaign_name, run_id)` to reuse `AccountSession`.
  - **Will be updated** to remove `campaign_name` (key by `handle, run_id` only)

### Accounts (current)
- `assets/accounts.secrets.template.yaml` (file-based, manual editing)
- Read at runtime via `linkedin/conf.py` → `get_account_config(handle)`

### Actions (LinkedIn touchpoints implemented)
- **Profile enrichment**: `linkedin/actions/profile.py` (Voyager API fetch via Playwright context)
- **Connection status**: `linkedin/actions/connection_status.py` (UI inspection)
- **Connection request**: `linkedin/actions/connect.py` (send invite; note flow exists)
- **Direct message**: `linkedin/actions/message.py` (only for connected profiles)
- **Search/navigation**: `linkedin/actions/search.py` (human-like search + fallback to direct URL)

### LinkedIn internal API parsing
- `linkedin/api/client.py` + `linkedin/api/voyager.py`
  - Voyager API fetch + parsing into a clean dict.

### Persistence
- `linkedin/db/models.py` + `linkedin/db/engine.py` + `linkedin/db/profiles.py`
  - Per-account SQLite DB.
  - `profiles` table stores `public_identifier`, profile JSON, raw JSON, `cloud_synced`, timestamps, `state`.

### AI/templating (to be removed)
- `linkedin/templates/renderer.py`
  - Jinja rendering + `langchain_openai` call for `ai_prompt`.
- `linkedin/actions/message.py` calls `render_template()` today.
- `linkedin/conf.py` contains `OPENAI_API_KEY` and `AI_MODEL`.

---

## 1) Phase 1 — Remove AI + templating completely (repo focus = LinkedIn automation only)

### 1.1 Remove code + assets
- Delete `linkedin/templates/` package.
- Delete `assets/templates/` (prompts/messages) since server will accept message content from clients.
- Remove all references to:
  - `render_template()`
  - `ai_prompt` / `jinja` template types
  - `OPENAI_API_KEY`, `AI_MODEL`

### 1.2 Refactor messaging APIs (server/client owns message text)
- Update `linkedin/actions/message.py`
  - Remove `template_file` + `template_type` args.
  - Require `message: str` (or allow `None` and return SKIPPED with a clear log).
- Update `linkedin/campaigns/connect_follow_up.py`
  - Remove template constants and CSV handling.
  - Accept message passed in at runtime (API job).

### 1.3 Dependency cleanup
- Remove from `pyproject.toml`:
  - `jinja2`, `langchain`, `langchain-openai` (and any other AI libs that exist)
- Keep only LinkedIn automation + server deps.

**Exit criteria**: no imports of `jinja2`, `langchain*`, `OPENAI_API_KEY`, or `AI_MODEL` remain in the repo.

---

## 2) Phase 2 — Define a clean “touchpoint” abstraction (simple one-step automation primitives)

**Important**: Remove all campaign/workflow terminology from the repo. The API will only execute **single-step touchpoints** - no multi-step workflows or campaign orchestration.

### 2.1 Remove Campaign System

**Cleanup tasks:**
- Delete `linkedin/campaigns/` directory entirely
- Remove `campaign_name` from `SessionKey` (replace with optional `tags` or remove entirely)
- Update `AccountSessionRegistry` to key by `(handle, run_id)` only
- Remove all references to "campaign", "workflow", "orchestration" from code and docs
- Update `AccountSession` to remove `campaign_name` attribute

**Rationale**: Campaigns/workflows add unnecessary complexity. The API client can compose multiple touchpoint calls if needed. The server should only execute atomic, single-step operations.

### 2.2 Define Touchpoint Abstraction

Introduce a simple internal contract:

- **Touchpoint**: a single atomic automation action with validated input and deterministic outcome.
  - Each touchpoint executes **one** LinkedIn action (no chaining, no state machines)
  - Examples:
    - `ProfileEnrich(public_identifier|url)` - Fetch profile data
    - `ProfileVisit(url, duration_s, scroll_depth)` - Visit a profile page
    - `Connect(url, note?)` - Send connection request
    - `DirectMessage(url, message)` - Send a message
    - `PostReact(post_url, reaction_type)` - React to a post
    - `PostComment(post_url, comment_text)` - Comment on a post
    - `InMail(profile_url, subject?, body)` - Send InMail

**Implementation:**
- Create `linkedin/touchpoints/`:
  - `base.py` (protocol/abstract base for all touchpoints)
  - `models.py` (Pydantic models for inputs/outputs)
  - `runner.py` (executes one touchpoint against an `AccountSession`)
  - Individual touchpoint modules: `enrich.py`, `visit.py`, `connect.py`, `message.py`, etc.

**Key principle**: One touchpoint = one API call = one LinkedIn action. No workflows, no state machines, no orchestration.

---

## 3) Phase 3 — Introduce FastAPI server (API client issues automation requests)

### 3.1 Server layout (new package)
Add a top-level package, e.g.:
- `openoutreach_server/`
  - `main.py` (FastAPI app)
  - `routers/` (jobs, schedules, accounts, runs)
  - `schemas/` (Pydantic request/response)
  - `services/executor.py` (background worker + locking)
  - `services/scheduler.py` (APScheduler or internal scheduler)
  - `db/` (server DB models + migrations)

### 3.2 API endpoints (minimum viable)
- `GET /health`
- `GET /accounts` (reads from accounts DB)
- `POST /runs` (submit a single touchpoint execution)
  - body: `{handle, touchpoint: {...}, dry_run?, tags?}`
  - Returns: `{run_id, status, ...}`
- `GET /runs/{run_id}` (get execution status and results)
- `GET /runs` (list runs with filtering: `?handle=...&status=...&limit=...`)
- `POST /schedules` (create **cron** schedule for recurring touchpoint execution)
  - body: `{handle, touchpoint: {...}, cron: "...", tags?}`
- `GET /schedules`
- `DELETE /schedules/{schedule_id}`

### 3.3 Auth
Add a simple API key to start:
- `X-API-Key: <key>`
- Load from env var (later expand to OAuth/JWT if needed).

### 3.4 Account management (DB-backed; endpoints later)
- **Implemented now (DB layer):** `accounts` table and CRUD helpers in `linkedin/db/accounts.py`; `linkedin/conf.py` now reads accounts from the DB (no YAML ingestion; no backward compatibility).
- **To do later (when FastAPI is added):** expose `/accounts` CRUD endpoints that wrap these DB helpers.
- Touchpoint execution:
  - Every `run` payload must include `handle` to select credentials/cookies.
  - Locking remains per-account to avoid concurrent sessions.

### 3.5 Run tracking and logging (critical for diagnostics)

**Database schema for run tracking:**

Add `runs` table to server DB (separate from per-account profile DBs):

```python
class Run(Base):
    __tablename__ = "runs"
    
    run_id = Column(String, primary_key=True)  # UUID
    handle = Column(String, nullable=False, index=True)
    touchpoint_type = Column(String, nullable=False)  # "enrich", "connect", "message", etc.
    touchpoint_input = Column(JSON, nullable=False)  # Full touchpoint payload
    status = Column(String, nullable=False)  # "pending", "running", "completed", "failed"
    result = Column(JSON, nullable=True)  # Touchpoint output/result
    error = Column(Text, nullable=True)  # Error message if failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)  # Optional tags for filtering
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
```

**Implementation:**
- Create `openoutreach_server/db/models.py` with `Run` model
- Log every touchpoint execution:
  - Create `Run` record when `POST /runs` is called (status="pending")
  - Update to "running" when execution starts
  - Update to "completed"/"failed" with result/error when done
  - Store full touchpoint input/output for debugging
- Add indexes on `handle`, `status`, `created_at` for efficient querying
- Use `run_id` from database (UUID) for all `SessionKey` creation

**Benefits:**
- Full audit trail of all automation executions
- Easy debugging: see exactly what was executed and what failed
- Performance monitoring: track duration, success rates
- Filtering: find all runs for an account, by status, by touchpoint type
- Correlation: link runs to profiles, errors, etc.

---

## 4) Phase 4 — Execution model + scheduler (safe automation at scale)

### 4.1 Concurrency and locking (critical)
LinkedIn automation must be conservative:
- **1 active browser session per account** at a time.
- Enforce an account-level lock:
  - in-process `asyncio.Lock` is fine for single-instance
  - for multi-instance later, use DB advisory locks / Redis lock.

### 4.2 Background execution
Start simple:
- Use FastAPI lifespan + a background task runner thread/process that:
  - pulls queued runs from `server.db` (status="pending")
  - acquires account lock
  - creates/reuses `AccountSession` (using `run_id` from DB)
  - executes **single touchpoint** atomically
  - updates `Run` record with result/error
  - releases account lock

### 4.3 Scheduling
Cron-only scheduling for recurring touchpoint execution:
- **Schedule table** in server DB:
  ```python
  class Schedule(Base):
      schedule_id = Column(String, primary_key=True)  # UUID
      handle = Column(String, nullable=False)
      touchpoint = Column(JSON, nullable=False)  # Touchpoint definition
      cron = Column(String, nullable=False)  # Cron expression
      next_run_at = Column(DateTime, nullable=True)
      active = Column(Boolean, default=True)
      tags = Column(JSON, nullable=True)
      created_at = Column(DateTime, server_default=func.now())
  ```
- Background scheduler thread:
  - Polls `Schedule` table for `next_run_at <= now()` and `active=True`
  - Creates a new `Run` record (status="pending") for each scheduled execution
  - Updates `next_run_at` based on cron expression
- Keep it simple: own schedule table + polling (easier debugging than APScheduler)

---

## 5) Phase 5 — Extend touchpoints (one-step actions only)

### 5.1 Explicit profile visits
Add `linkedin/actions/visit.py`:
- Navigate to profile URL (reuse `search_profile` or direct URL)
- Wait a configurable duration
- Scroll (configurable steps) to mimic a real view
- Return status

### 5.2 Post reactions
Add `linkedin/actions/post_react.py`:
- Input: `post_url`, `reaction` (LIKE/CELEBRATE/SUPPORT/LOVE/INSIGHTFUL/CURIOUS)
- Navigate to post URL
- Click the reaction UI (may require hover/press-and-hold depending on UI variant)
- Verify toast/selected state

### 5.3 Post comments
Add `linkedin/actions/post_comment.py`:
- Input: `post_url`, `comment_text`
- Navigate to post URL
- Open comment box (selector variants)
- Type/paste comment
- Submit
- Verify (presence of comment or toast)

### 5.4 InMail
Reality check: InMail UI/availability depends on:
- Premium account (Sales Navigator flows are **not** supported initially)
- Recipient settings
- Credit availability

Implementation approach:
- Add `linkedin/actions/inmail.py` (best-effort)
- Flow:
  - Navigate to profile
  - Try `Message`/`More actions` menu items that open an InMail compose modal (standard LinkedIn UI only)
  - Detect InMail compose modal fields (subject/body)
  - Send, then confirm success toast
- Return explicit error reasons:
  - `NOT_AVAILABLE`, `NO_CREDITS`, `UI_CHANGED`, `BLOCKED`

---

## 7) Phase 7 — Observability + safety controls

**Note**: Run tracking is already implemented in Phase 3.5 (database logging). This phase adds additional observability.

Add operational basics:
- Structured logging per `run_id` and `handle` (correlate with `Run` records)
- Enhanced run tracking:
  - Screenshot capture on failure (store path in `Run.error_screenshot`)
  - Request/response logging for API touchpoints
  - Browser console logs capture
- Hard quotas (enforce at account level):
  - max connects/day, max messages/day, max posts/day per `handle`
  - Store in `Account` model or separate `account_quotas` table
  - Check before executing touchpoint, reject if quota exceeded
- Backoff and circuit breakers:
  - Track consecutive failures per account
  - If UI selectors fail repeatedly, mark account as "paused" and require manual intervention
  - Store pause state in `Account` model or `account_status` table

---

## 7.1) Minimal E2E test strategy (UI automation) for the FastAPI job runner

The current `tests/` suite is mostly unit tests (e.g., Voyager parsing). For UI automation, add a separate **E2E layer**
that is **skipped by default** and only run intentionally (local/dev), because it requires real LinkedIn accounts and a
browser.

### Proposed structure

- `tests/e2e/`
  - `conftest.py`
    - loads `assets/accounts.secrets.yaml` (or env) for a dedicated test handle
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

## 8) Phase 8 — Docker / deployment adjustments

Update `local.yml` (and/or add `compose/server/`) to run:
- API server container: `uvicorn openoutreach_server.main:app`
- Optional worker container (if you split worker from API)
- Optional Redis (if you later adopt Celery/RQ)

---

## Open questions (to decide before implementing)

1. **Scheduling semantics**: cron only, interval, or both? → cron only
2. **Deployment**: single-instance server is acceptable, or do you want scale-out workers soon? → single-instance server only
3. **InMail**: do you require Sales Navigator support, or just “if it’s available in UI, attempt it”? → No Sales Navigator support for now; attempt standard LinkedIn InMail UI only if available
4. **Input format**: will the API always send message content, or should the server support templates later? → No template support, but message formatting must be preserved:
   - Accept raw strings and store/use them **as-is**
   - Preserve newlines (`\\n`) and whitespace; avoid `.strip()` and any whitespace normalization
   - Use `Content-Type: application/json; charset=utf-8` and treat message bodies as UTF-8 end-to-end



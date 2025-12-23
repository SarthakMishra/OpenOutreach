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

### Orchestration
- `linkedin/campaigns/connect_follow_up.py`
  - A single campaign state machine: `DISCOVERED → ENRICHED → PENDING/CONNECTED → COMPLETED`
  - Uses actions: `profile.scrape_profile`, `connect.send_connection_request`, `message.send_follow_up_message`.

### Browser + session
- `linkedin/sessions/account.py`
  - Owns Playwright `page/context/browser` + per-account SQLite DB session.
  - `ensure_browser()` bootstraps via `linkedin/navigation/login.py`.
  - `wait()` contains opportunistic scraping behavior (optional).
- `linkedin/sessions/registry.py`
  - In-process registry keyed by `(handle, campaign_name, csv_hash)` to reuse `AccountSession`.

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

## 2) Phase 2 — Define a clean “touchpoint” abstraction (so API can trigger anything)

Introduce a small internal contract:

- **Touchpoint**: a unit of automation with validated input and deterministic outcomes.
  - Examples:
    - `ProfileEnrich(public_identifier|url)`
    - `ProfileVisit(url, duration_s, scroll_depth)`
    - `Connect(url, note?)`
    - `DirectMessage(url, message)`
    - `PostReact(post_url, reaction_type)`
    - `PostComment(post_url, comment_text)`
    - `InMail(profile_url, subject?, body)`

Implementation suggestion:
- Create `linkedin/touchpoints/`:
  - `base.py` (protocol/abstract base)
  - `models.py` (Pydantic models for inputs/outputs)
  - `runner.py` (executes one touchpoint against an `AccountSession`)

**Why**: campaigns become sequences of touchpoints; the API triggers touchpoints directly or via predefined workflows.

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
- `GET /accounts` (reads from `assets/accounts.secrets.yaml`)
- `POST /runs` (submit a run)
  - body: `{handle, touchpoints: [...], dry_run?, tags?}`
- `GET /runs/{run_id}`
- `POST /schedules` (create **cron** schedule for a run template)
- `GET /schedules`
- `DELETE /schedules/{schedule_id}`

### 3.3 Auth
Add a simple API key to start:
- `X-API-Key: <key>`
- Load from env var (later expand to OAuth/JWT if needed).

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
  - pulls queued jobs from `server.db`
  - acquires account lock
  - creates/reuses `AccountSession`
  - executes touchpoints sequentially
  - records results

### 4.3 Scheduling
Cron-only scheduling options:
1. **APScheduler** with a SQLAlchemy job store (persisted schedules) using cron triggers only.
2. **Own schedule table** (cron string + next_run_at) and poll.

Pick (2) first for transparency and control (easier debugging), move to APScheduler later if desired.

---

## 5) Phase 5 — Extend touchpoints

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

Add operational basics:
- Structured logging per `run_id` and `account`
- Persistent run history table:
  - start/end timestamps
  - per-touchpoint result
  - last error + screenshot path (optional)
- Hard quotas:
  - max connects/day, max messages/day, max posts/day
- Backoff:
  - if UI selectors fail repeatedly, pause that account and require manual intervention

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

### What E2E tests should validate (job runner aligned)

Each E2E test should exercise the system through the **API**, not by calling action functions directly:
1. `POST /runs` with `handle` + `touchpoints`
2. poll `GET /runs/{run_id}` until terminal state
3. assert:
   - run state transitions
   - touchpoint results recorded (success/failure + reason)
   - optional artifacts exist (screenshot/HTML dump) on failure

This keeps the E2E suite compatible with the future architecture (server is the product surface).

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



# OpenOutreach Server

This is a **proof-of-concept** API server implementation based on the [OpenOutreach](https://github.com/eracle/OpenOutreach) project. The API provides programmatic access to LinkedIn automation capabilities through a FastAPI-based REST interface.

**Note:** This implementation is unstable and was put together in an afternoon. Do not use with a live account without thorough testing—if you do, you accept all risks.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) `.env` file for environment variables (API keys, etc.)

### Installation

```bash
# Clone repository
git clone https://github.com/eracle/OpenOutreach.git
cd OpenOutreach

# Build Docker image
docker compose build
```

### Run Server

```bash
# Start FastAPI server with Docker Compose
docker compose up
```

Server runs on `http://localhost:8000` by default. VNC access for browser debugging is available on port `5900`.


## 📡 API Endpoints

### Health

- `GET /health` - Health check

### Accounts

- `POST /api/v1/accounts` - Create or update a LinkedIn account
  ```json
  {
    "handle": "account1",
    "username": "user@example.com",
    "password": "password123",
    "active": true,
    "proxy": null,
    "daily_connections": 50,
    "daily_messages": 20,
    "booking_link": null
  }
  ```
- `GET /api/v1/accounts` - List all accounts
- `GET /api/v1/accounts/{handle}` - Get account by handle
- `DELETE /api/v1/accounts/{handle}` - Delete account

### Runs

- `POST /api/v1/runs` - Create and queue a touchpoint execution
  ```json
  {
    "handle": "account1",
    "touchpoint": {
      "type": "connect",
      "url": "https://www.linkedin.com/in/username/",
      "note": "Optional connection note"
    },
    "dry_run": false,
    "tags": {}
  }
  ```
  #### Available Touchpoints
  - **`profile_enrich`** - Enrich LinkedIn profile data
  - **`profile_visit`** - Visit profile with configurable duration/scrolling
  - **`connect`** - Send connection request (with optional note)
  - **`direct_message`** - Send direct message to connected profile
  - **`post_react`** - React to LinkedIn post
  - **`post_comment`** - Comment on LinkedIn post
  - **`inmail`** - Send InMail
- `GET /api/v1/runs/{run_id}` - Get run status and results
- `GET /api/v1/runs` - List runs (filter by `handle`, `status`, pagination)

### Schedules

- `POST /api/v1/schedules` - Create recurring touchpoint schedule
  ```json
  {
    "handle": "account1",
    "touchpoint": { "type": "profile_visit", "url": "..." },
    "cron": "0 9 * * *",
    "tags": {}
  }
  ```
- `GET /api/v1/schedules` - List schedules
- `DELETE /api/v1/schedules/{schedule_id}` - Delete schedule

### Authentication

All endpoints (except `/health`) require API key authentication via header:
```
X-API-Key: your-secret-key
```

If `API_KEY` environment variable is not set, authentication is disabled (development mode).


## ⚖️ License

[GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0) — see [LICENCE.md](LICENCE.md)


## 📜 Legal Disclaimer

**Not affiliated with LinkedIn.**

Automation may violate LinkedIn's terms. Risk of account suspension exists.

**Use at your own risk — no liability assumed.**


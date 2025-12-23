# api_server/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api_server.routers import accounts, health, runs, schedules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    from api_server.services.scheduler import start_scheduler
    from api_server.services.worker import start_worker

    # Start background worker for pending runs
    start_worker()

    # Start scheduler for due schedules
    start_scheduler()

    logger.info("API server started")

    yield

    # Shutdown
    from api_server.services.scheduler import stop_scheduler
    from api_server.services.worker import stop_worker

    stop_scheduler()
    stop_worker()
    logger.info("Background services stopped")


app = FastAPI(
    title="OpenOutreach API",
    description="API server for LinkedIn automation touchpoints",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health.router, tags=["health"])
app.include_router(accounts.router, prefix="/api/v1", tags=["accounts"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
app.include_router(schedules.router, prefix="/api/v1", tags=["schedules"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

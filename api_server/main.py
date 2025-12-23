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
    from apscheduler.triggers.cron import CronTrigger

    # Load existing schedules and add them to scheduler
    from api_server.db.engine import get_session
    from api_server.db.models import Schedule
    from api_server.services.scheduler import _execute_scheduled_run, get_scheduler

    session = get_session()
    try:
        schedules = session.query(Schedule).filter(Schedule.active == "active").all()
        scheduler = get_scheduler()

        for schedule in schedules:
            try:
                scheduler.add_job(
                    func=_execute_scheduled_run,
                    trigger=CronTrigger.from_crontab(schedule.cron),  # type: ignore
                    args=[schedule.schedule_id],  # type: ignore
                    id=schedule.schedule_id,  # type: ignore
                    replace_existing=True,
                )
                logger.info("Restored schedule %s", schedule.schedule_id)  # type: ignore
            except Exception as e:
                logger.error("Failed to restore schedule %s: %s", schedule.schedule_id, e)  # type: ignore
    finally:
        session.close()

    logger.info("API server started")

    yield

    # Shutdown
    from api_server.services.scheduler import _scheduler

    if _scheduler:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")


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

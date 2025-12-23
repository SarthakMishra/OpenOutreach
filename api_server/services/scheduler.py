# api_server/services/scheduler.py
import logging
import uuid
from typing import Any, Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from api_server.db.engine import get_session
from api_server.db.models import Schedule
from api_server.services.executor import create_run, execute_run

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
        logger.info("Scheduler started")
    return _scheduler


def create_schedule(
    handle: str, touchpoint_input: Dict[str, Any], cron: str, tags: Dict[str, Any] | None = None
) -> str:
    """
    Create a new schedule.

    Returns:
        schedule_id (UUID string)
    """
    schedule_id = str(uuid.uuid4())

    # Extract touchpoint type from input
    touchpoint_type = touchpoint_input.get("type", "unknown")

    session = get_session()
    try:
        schedule = Schedule(
            schedule_id=schedule_id,
            handle=handle,
            touchpoint_type=touchpoint_type,
            touchpoint_input=touchpoint_input,
            cron=cron,
            active="active",
            tags=tags,
        )
        session.add(schedule)
        session.commit()

        # Add job to scheduler
        scheduler = get_scheduler()
        scheduler.add_job(
            func=_execute_scheduled_run,
            trigger=CronTrigger.from_crontab(cron),
            args=[schedule_id],
            id=schedule_id,
            replace_existing=True,
        )

        logger.info("Created schedule %s for handle %s with cron %s", schedule_id, handle, cron)
        return schedule_id
    finally:
        session.close()


def _execute_scheduled_run(schedule_id: str) -> None:
    """Execute a scheduled run."""
    session = get_session()
    try:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            logger.error("Schedule %s not found", schedule_id)
            return

        if schedule.active != "active":
            logger.debug("Schedule %s is not active, skipping", schedule_id)
            return

        # Create and execute run
        run_id = create_run(
            handle=schedule.handle,
            touchpoint_input=schedule.touchpoint_input,
            tags=schedule.tags,
        )
        execute_run(run_id)
        logger.info("Executed scheduled run %s for schedule %s", run_id, schedule_id)
    finally:
        session.close()


def get_schedule(schedule_id: str) -> Schedule | None:
    """Get a schedule by ID."""
    session = get_session()
    try:
        return session.get(Schedule, schedule_id)
    finally:
        session.close()


def list_schedules(handle: str | None = None) -> list[Schedule]:
    """List schedules, optionally filtered by handle."""
    session = get_session()
    try:
        query = session.query(Schedule)
        if handle:
            query = query.filter(Schedule.handle == handle)
        return query.order_by(Schedule.created_at.desc()).all()
    finally:
        session.close()


def delete_schedule(schedule_id: str) -> bool:
    """Delete a schedule and remove its job from scheduler."""
    session = get_session()
    try:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            return False

        # Remove job from scheduler
        scheduler = get_scheduler()
        try:
            scheduler.remove_job(schedule_id)
        except Exception as e:
            logger.warning("Failed to remove job %s from scheduler: %s", schedule_id, e)

        # Delete from database
        session.delete(schedule)
        session.commit()
        logger.info("Deleted schedule %s", schedule_id)
        return True
    finally:
        session.close()


def pause_schedule(schedule_id: str) -> bool:
    """Pause a schedule."""
    session = get_session()
    try:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            return False

        schedule.active = "paused"
        session.commit()

        # Pause job in scheduler
        scheduler = get_scheduler()
        try:
            scheduler.pause_job(schedule_id)
        except Exception as e:
            logger.warning("Failed to pause job %s in scheduler: %s", schedule_id, e)

        logger.info("Paused schedule %s", schedule_id)
        return True
    finally:
        session.close()


def resume_schedule(schedule_id: str) -> bool:
    """Resume a paused schedule."""
    session = get_session()
    try:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            return False

        schedule.active = "active"
        session.commit()

        # Resume job in scheduler
        scheduler = get_scheduler()
        try:
            scheduler.resume_job(schedule_id)
        except Exception as e:
            logger.warning("Failed to resume job %s in scheduler: %s", schedule_id, e)

        logger.info("Resumed schedule %s", schedule_id)
        return True
    finally:
        session.close()

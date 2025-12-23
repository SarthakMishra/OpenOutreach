# api_server/services/scheduler.py
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, cast

from croniter import croniter

from api_server.db.engine import get_session
from api_server.db.models import Schedule
from api_server.services.executor import create_run

logger = logging.getLogger(__name__)

# Global scheduler thread
_scheduler_thread: threading.Thread | None = None
_scheduler_running = False
_scheduler_lock = threading.Lock()


def _calculate_next_run(cron: str, from_time: datetime | None = None) -> datetime:
    """Calculate next run time from cron expression."""
    if from_time is None:
        from_time = datetime.now(timezone.utc)
    iter = croniter(cron, from_time)
    return iter.get_next(datetime)


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

    # Calculate next run time
    next_run_at = _calculate_next_run(cron)

    session = get_session()
    try:
        schedule = Schedule(
            schedule_id=schedule_id,
            handle=handle,
            touchpoint_type=touchpoint_type,
            touchpoint_input=touchpoint_input,
            cron=cron,
            next_run_at=next_run_at,
            active=True,
            tags=tags,
        )
        session.add(schedule)
        session.commit()

        logger.info(
            "Created schedule %s for handle %s with cron %s (next run: %s)",
            schedule_id,
            handle,
            cron,
            next_run_at,
        )
        return schedule_id
    finally:
        session.close()


def _process_due_schedules() -> None:
    """Process schedules that are due for execution."""
    session = get_session()
    try:
        now = datetime.now(timezone.utc)
        # Find schedules that are due and active
        due_schedules = (
            session.query(Schedule)
            .filter(Schedule.active == True)  # noqa: E712
            .filter(Schedule.next_run_at <= now)
            .all()
        )

        for schedule in due_schedules:
            try:
                # Create run for this schedule
                run_id = create_run(
                    handle=cast(str, schedule.handle),
                    touchpoint_input=cast(Dict[str, Any], schedule.touchpoint_input),
                    tags=cast(Dict[str, Any] | None, schedule.tags),
                )

                # Calculate next run time
                cron = cast(str, schedule.cron)
                next_run_at = _calculate_next_run(cron, now)
                schedule.next_run_at = next_run_at
                session.commit()

                schedule_id = cast(str, schedule.schedule_id)
                logger.info(
                    "Created scheduled run %s for schedule %s (next run: %s)",
                    run_id,
                    schedule_id,
                    next_run_at,
                )
            except Exception as e:
                schedule_id = cast(str, schedule.schedule_id)
                logger.error("Failed to process schedule %s: %s", schedule_id, e, exc_info=True)
                session.rollback()
    finally:
        session.close()


def _scheduler_worker() -> None:
    """Background worker that polls for due schedules."""
    logger.info("Scheduler worker started")
    while _scheduler_running:
        try:
            _process_due_schedules()
        except Exception as e:
            logger.error("Error in scheduler worker: %s", e, exc_info=True)

        # Sleep for 30 seconds before next poll
        import time

        for _ in range(30):
            if not _scheduler_running:
                break
            time.sleep(1)

    logger.info("Scheduler worker stopped")


def start_scheduler() -> None:
    """Start the scheduler worker thread."""
    global _scheduler_thread, _scheduler_running

    with _scheduler_lock:
        if _scheduler_running:
            logger.warning("Scheduler already running")
            return

        _scheduler_running = True
        _scheduler_thread = threading.Thread(target=_scheduler_worker, daemon=True)
        _scheduler_thread.start()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler worker thread."""
    global _scheduler_running

    with _scheduler_lock:
        if not _scheduler_running:
            return

        _scheduler_running = False
        if _scheduler_thread:
            _scheduler_thread.join(timeout=5.0)
        logger.info("Scheduler stopped")


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
    """Delete a schedule."""
    session = get_session()
    try:
        schedule = session.get(Schedule, schedule_id)
        if not schedule:
            return False

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

        schedule.active = False
        session.commit()

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

        schedule.active = True
        # Recalculate next_run_at if it's in the past
        next_run_at = cast(datetime | None, schedule.next_run_at)
        if next_run_at and next_run_at < datetime.now(timezone.utc):
            cron = cast(str, schedule.cron)
            schedule.next_run_at = _calculate_next_run(cron)
        session.commit()

        logger.info("Resumed schedule %s", schedule_id)
        return True
    finally:
        session.close()

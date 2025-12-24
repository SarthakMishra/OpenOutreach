# api_server/services/executor.py
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from api_server.db.engine import get_session
from api_server.db.models import Run
from api_server.services.observability import capture_screenshot
from api_server.services.quota import check_quota, increment_quota, record_failure, record_success
from linkedin.touchpoints.models import TouchpointType

logger = logging.getLogger(__name__)


# Structured logging adapter that includes run_id and handle
class RunLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = self.extra or {}
        run_id = str(extra.get("run_id", "unknown"))[:8]
        handle = str(extra.get("handle", "unknown"))
        formatted_msg = f"[run_id={run_id}] [handle={handle}] {msg}"
        return formatted_msg, kwargs


# Per-account locks to prevent concurrent executions
_account_locks: Dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()


def _get_account_lock(handle: str) -> threading.Lock:
    """Get or create a lock for an account."""
    with _locks_lock:
        if handle not in _account_locks:
            _account_locks[handle] = threading.Lock()
        return _account_locks[handle]


def create_run(handle: str, touchpoint_input: Dict[str, Any], tags: Dict[str, Any] | None = None) -> str:
    """
    Create a new run record in the database.

    Returns:
        run_id (UUID string)
    """
    run_id = str(uuid.uuid4())

    # Extract touchpoint type from input
    touchpoint_type = touchpoint_input.get("type", "unknown")

    session = get_session()
    try:
        run = Run(
            run_id=run_id,
            handle=handle,
            touchpoint_type=touchpoint_type,
            touchpoint_input=touchpoint_input,
            status="pending",
            tags=tags,
        )
        session.add(run)
        session.commit()
        logger.info("Created run %s for handle %s", run_id, handle)
        return run_id
    finally:
        session.close()


def execute_run(run_id: str) -> None:
    """
    Execute a run in the background.

    Updates run status: pending → running → completed/failed
    """
    session = get_session()
    try:
        run = session.get(Run, run_id)
        if not run:
            logger.error("Run %s not found", run_id)
            return

        if run.status != "pending":
            logger.warning("Run %s is not pending (status: %s), skipping", run_id, run.status)
            return

        # Update to running
        run.status = "running"
        started_at = datetime.now(timezone.utc)
        run.started_at = started_at
        session.commit()

        # Get account lock to prevent concurrent executions
        account_lock = _get_account_lock(run.handle)

        # Capture run data for inner function
        handle = run.handle
        touchpoint_input = run.touchpoint_input

        def _execute():
            """Execute touchpoint within account lock."""
            # Create structured logger for this run
            run_logger = RunLoggerAdapter(logger, {"run_id": run_id, "handle": handle})

            with account_lock:
                account_session = None
                try:
                    from linkedin.sessions.registry import AccountSessionRegistry
                    from linkedin.touchpoints.factory import create_touchpoint

                    # Extract touchpoint type for quota checking
                    touchpoint_type_str = touchpoint_input.get("type", "unknown")
                    try:
                        touchpoint_type = TouchpointType(touchpoint_type_str)
                    except ValueError:
                        touchpoint_type = TouchpointType.PROFILE_ENRICH  # Default fallback

                    # Check quota before execution
                    quota_allowed, quota_error = check_quota(handle, touchpoint_type)
                    if not quota_allowed:
                        error_msg = f"Quota check failed: {quota_error}"
                        run_logger.error(error_msg)
                        db_session = get_session()
                        try:
                            run = db_session.get(Run, run_id)
                            if run:
                                run.status = "failed"
                                run.error = error_msg
                                run.completed_at = datetime.now(timezone.utc)
                                db_session.commit()
                        finally:
                            db_session.close()
                        return

                    # Create touchpoint instance from input
                    touchpoint = create_touchpoint(touchpoint_input)

                    # Get account session (touchpoint will create SessionKey internally)
                    account_session = AccountSessionRegistry.get_or_create(handle=handle, run_id=run_id)

                    # Execute touchpoint
                    run_logger.info("Executing touchpoint type: %s", touchpoint_type_str)
                    result_data = touchpoint.execute(account_session)

                    # Calculate duration
                    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

                    # Check if successful
                    success = result_data.get("success", False)
                    error_msg = result_data.get("error")

                    # Update quotas and failure tracking
                    if success:
                        increment_quota(handle, touchpoint_type)
                        record_success(handle)
                        run_logger.info("Touchpoint executed successfully")
                    else:
                        record_failure(handle)
                        run_logger.warning("Touchpoint execution failed: %s", error_msg)

                    # Capture screenshot on failure
                    error_screenshot_path = None
                    if not success and account_session:
                        error_screenshot_path = capture_screenshot(account_session, run_id, "error")

                    # Update run with result
                    db_session = get_session()
                    try:
                        run = db_session.get(Run, run_id)
                        if run:
                            run.status = "completed" if success else "failed"
                            run.result = result_data.get("result")
                            run.error = error_msg
                            run.error_screenshot = error_screenshot_path
                            run.completed_at = datetime.now(timezone.utc)
                            run.duration_ms = duration_ms
                            db_session.commit()
                            run_logger.info("Run completed with status: %s", run.status)
                    finally:
                        db_session.close()

                except Exception as e:
                    run_logger.error("Run execution failed with exception: %s", e, exc_info=True)

                    # Capture screenshot on exception
                    error_screenshot_path = None
                    if account_session:
                        error_screenshot_path = capture_screenshot(account_session, run_id, "exception")

                    # Record failure
                    record_failure(handle)

                    # Update run with error
                    db_session = get_session()
                    try:
                        run = db_session.get(Run, run_id)
                        if run:
                            run.status = "failed"
                            run.error = str(e)
                            run.error_screenshot = error_screenshot_path
                            run.completed_at = datetime.now(timezone.utc)
                            db_session.commit()
                    finally:
                        db_session.close()
                finally:
                    # Always close browser session to prevent resource leaks
                    if account_session:
                        try:
                            account_session.close()
                            run_logger.debug("Browser session closed for run %s", run_id)
                        except Exception as e:
                            run_logger.warning("Error closing browser session: %s", e)

        # Execute in background thread
        thread = threading.Thread(target=_execute, daemon=True)
        thread.start()

    finally:
        session.close()


def get_run(run_id: str) -> Run | None:
    """Get a run by ID."""
    session = get_session()
    try:
        return session.get(Run, run_id)
    finally:
        session.close()


def list_runs(
    handle: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Run], int]:
    """
    List runs with filtering.

    Returns:
        (runs, total_count)
    """
    session = get_session()
    try:
        query = session.query(Run)

        if handle:
            query = query.filter(Run.handle == handle)
        if status:
            query = query.filter(Run.status == status)

        total = query.count()
        runs = query.order_by(Run.created_at.desc()).offset(offset).limit(limit).all()

        return runs, total
    finally:
        session.close()

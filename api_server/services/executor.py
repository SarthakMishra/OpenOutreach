# api_server/services/executor.py
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from api_server.db.engine import get_session
from api_server.db.models import Run
from linkedin.touchpoints.models import TouchpointType

logger = logging.getLogger(__name__)

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
        touchpoint_type_str = run.touchpoint_type
        touchpoint_input = run.touchpoint_input

        def _execute():
            """Execute touchpoint within account lock."""
            with account_lock:
                try:
                    from linkedin.actions.connect import send_connection_request
                    from linkedin.actions.message import send_follow_up_message
                    from linkedin.actions.profile import scrape_profile
                    from linkedin.navigation.enums import ProfileState
                    from linkedin.sessions.registry import SessionKey

                    # Parse touchpoint input
                    touchpoint_type = TouchpointType(touchpoint_type_str)
                    input_data = touchpoint_input

                    # Create session key
                    key = SessionKey(handle=handle, run_id=run_id)

                    # Execute based on touchpoint type
                    result_data = {}

                    if touchpoint_type == TouchpointType.PROFILE_ENRICH:
                        profile_dict = {
                            "url": input_data.get("url"),
                            "public_identifier": input_data.get("public_identifier"),
                        }
                        profile, data = scrape_profile(key, profile_dict)
                        result_data = {
                            "success": profile is not None,
                            "result": {"profile": profile, "data": data} if profile else None,
                            "error": None if profile else "Failed to enrich profile",
                        }

                    elif touchpoint_type == TouchpointType.CONNECT:
                        profile_dict = {
                            "url": input_data.get("url"),
                            "public_identifier": input_data.get("public_identifier"),
                        }
                        note = input_data.get("note")
                        status = send_connection_request(key, profile_dict, note=note)
                        result_data = {
                            "success": status in [ProfileState.PENDING, ProfileState.CONNECTED],
                            "result": {"status": status.value},
                            "error": None,
                        }

                    elif touchpoint_type == TouchpointType.DIRECT_MESSAGE:
                        profile_dict = {
                            "url": input_data.get("url"),
                            "public_identifier": input_data.get("public_identifier"),
                        }
                        message = input_data.get("message", "")
                        status = send_follow_up_message(key, profile_dict, message=message)
                        result_data = {
                            "success": status.value == "sent",
                            "result": {"status": status.value},
                            "error": None if status.value == "sent" else "Message not sent",
                        }

                    else:
                        raise ValueError(f"Unsupported touchpoint type: {touchpoint_type}")

                    # Calculate duration
                    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

                    # Update run with result
                    session = get_session()
                    try:
                        run = session.get(Run, run_id)
                        if run:
                            success = result_data.get("success", False)
                            run.status = "completed" if success else "failed"
                            run.result = result_data.get("result")
                            run.error = result_data.get("error")
                            run.completed_at = datetime.now(timezone.utc)
                            run.duration_ms = duration_ms
                            session.commit()
                            logger.info("Run %s completed with status %s", run_id, run.status)
                    finally:
                        session.close()

                except Exception as e:
                    logger.error("Run %s execution failed: %s", run_id, e, exc_info=True)
                    session = get_session()
                    try:
                        run = session.get(Run, run_id)
                        if run:
                            run.status = "failed"
                            run.error = str(e)
                            run.completed_at = datetime.now(timezone.utc)
                            session.commit()
                    finally:
                        session.close()

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

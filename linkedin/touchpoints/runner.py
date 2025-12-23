# linkedin/touchpoints/runner.py
from __future__ import annotations

import logging
import time

from linkedin.sessions.registry import AccountSessionRegistry, SessionKey
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import TouchpointResult

logger = logging.getLogger(__name__)


def execute_touchpoint(
    touchpoint: Touchpoint,
    handle: str,
    run_id: str,
) -> TouchpointResult:
    """
    Execute a single touchpoint against an account session.

    This is the main entry point for touchpoint execution. It:
    1. Validates touchpoint input
    2. Gets or creates account session
    3. Executes touchpoint
    4. Returns standardized result

    Args:
        touchpoint: The touchpoint instance to execute
        handle: Account handle to use
        run_id: Unique run identifier (UUID)

    Returns:
        TouchpointResult with execution outcome
    """
    start_time = time.time()

    try:
        # Validate input before creating session
        touchpoint.validate_input()

        # Get or create account session
        session = AccountSessionRegistry.get_or_create(handle=handle, run_id=run_id)

        # Execute touchpoint
        result_data = touchpoint.execute(session)

        duration_ms = int((time.time() - start_time) * 1000)

        # Extract success/error from result
        success = result_data.get("success", True)
        error = result_data.get("error")

        return TouchpointResult(
            success=success,
            result=result_data.get("result"),
            error=error,
            duration_ms=duration_ms,
        )

    except ValueError as e:
        # Input validation error
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("Touchpoint validation failed: %s", e)
        return TouchpointResult(
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )

    except Exception as e:
        # Execution error
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error("Touchpoint execution failed: %s", e, exc_info=True)
        return TouchpointResult(
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )


def create_session_key(handle: str, run_id: str) -> SessionKey:
    """Helper to create SessionKey for touchpoint execution."""
    return SessionKey(handle=handle, run_id=run_id)

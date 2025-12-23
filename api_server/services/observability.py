# api_server/services/observability.py
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from linkedin.conf import ASSETS_DIR

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)

# Directory for storing screenshots and logs
OBSERVABILITY_DIR = ASSETS_DIR / "observability"
SCREENSHOTS_DIR = OBSERVABILITY_DIR / "screenshots"
LOGS_DIR = OBSERVABILITY_DIR / "logs"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def capture_screenshot(session: "AccountSession", run_id: str, suffix: str = "error") -> Optional[str]:
    """
    Capture a screenshot from the browser session.

    Args:
        session: Account session with browser access
        run_id: Run ID for filename
        suffix: Suffix for filename (default: "error")

    Returns:
        Path to screenshot file, or None if capture failed
    """
    if not session.page:
        logger.warning("Cannot capture screenshot: page not initialized")
        return None

    try:
        filename = f"{session.handle}--{run_id}--{suffix}.png"
        screenshot_path = SCREENSHOTS_DIR / filename
        session.page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info("Screenshot captured → %s", screenshot_path)
        return str(screenshot_path.relative_to(ASSETS_DIR))
    except Exception as e:
        logger.error("Failed to capture screenshot: %s", e, exc_info=True)
        return None


def capture_console_logs(session: "AccountSession", run_id: str) -> List[Dict[str, Any]]:
    """
    Capture browser console logs from the session.

    Args:
        session: Account session with browser access
        run_id: Run ID for logging context

    Returns:
        List of console log entries
    """
    if not session.page:
        return []

    try:
        # Get console logs from the page
        logs = []
        # Note: Playwright doesn't have a direct API to get console logs after they've been emitted
        # We'd need to set up console listeners during page creation
        # For now, return empty list - this would need to be implemented with event listeners
        logger.debug("Console logs capture not yet fully implemented (requires event listeners)")
        return logs
    except Exception as e:
        logger.error("Failed to capture console logs: %s", e, exc_info=True)
        return []


def setup_console_logging(session: "AccountSession") -> None:
    """
    Set up console log listeners for a session.
    This should be called when the page is created.

    Args:
        session: Account session with browser access
    """
    if not session.page:
        return

    try:
        # Store logs in session for later retrieval
        if not hasattr(session, "_console_logs"):
            session._console_logs = []  # type: ignore[attr-defined]

        def handle_console(msg):
            log_entry = {
                "type": msg.type,
                "text": msg.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            session._console_logs.append(log_entry)  # type: ignore[attr-defined]
            # Also log to Python logger
            log_level = logging.INFO
            if msg.type == "error":
                log_level = logging.ERROR
            elif msg.type == "warning":
                log_level = logging.WARNING
            logger.log(log_level, "Browser console [%s]: %s", msg.type, msg.text)

        session.page.on("console", handle_console)
        logger.debug("Console logging set up for session %s", session.handle)
    except Exception as e:
        logger.error("Failed to set up console logging: %s", e, exc_info=True)


def get_console_logs(session: "AccountSession") -> List[Dict[str, Any]]:
    """Get captured console logs from session."""
    if hasattr(session, "_console_logs"):
        return session._console_logs  # type: ignore[attr-defined]
    return []

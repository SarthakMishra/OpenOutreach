# api_server/services/quota.py
import logging
from datetime import datetime, timedelta, timezone

from linkedin.db.accounts import get_account
from linkedin.touchpoints.models import TouchpointType

logger = logging.getLogger(__name__)

# Circuit breaker thresholds
MAX_CONSECUTIVE_FAILURES = 5  # Pause account after 5 consecutive failures


def check_quota(handle: str, touchpoint_type: TouchpointType) -> tuple[bool, str | None]:
    """
    Check if account has quota available for the touchpoint type.

    Returns:
        (allowed: bool, error_message: str | None)
    """
    account = get_account(handle)
    if not account:
        return False, "Account not found"

    # Check if account is paused
    if account.paused:  # type: ignore
        reason = account.paused_reason or "unknown"  # type: ignore
        return False, f"Account is paused: {reason}"

    # Reset daily quotas if needed
    _reset_daily_quotas_if_needed(account)

    # Check quota based on touchpoint type
    if touchpoint_type == TouchpointType.CONNECT:
        if account.connections_today >= account.daily_connections:  # type: ignore
            return False, f"Daily connection quota exceeded ({account.connections_today}/{account.daily_connections})"  # type: ignore
    elif touchpoint_type == TouchpointType.DIRECT_MESSAGE:
        if account.messages_today >= account.daily_messages:  # type: ignore
            return False, f"Daily message quota exceeded ({account.messages_today}/{account.daily_messages})"  # type: ignore
    elif touchpoint_type in (TouchpointType.POST_REACT, TouchpointType.POST_COMMENT):
        # Use a default daily post limit (could be configurable)
        daily_posts_limit = 30
        if account.posts_today >= daily_posts_limit:  # type: ignore
            return False, f"Daily post quota exceeded ({account.posts_today}/{daily_posts_limit})"  # type: ignore

    return True, None


def increment_quota(handle: str, touchpoint_type: TouchpointType) -> None:
    """Increment the quota counter for the touchpoint type."""
    from linkedin.db.accounts import _get_session
    from linkedin.db.models import Account

    session = _get_session()
    try:
        account = session.get(Account, handle)
        if not account:
            return

        _reset_daily_quotas_if_needed(account)

        if touchpoint_type == TouchpointType.CONNECT:
            account.connections_today = (account.connections_today or 0) + 1  # type: ignore
        elif touchpoint_type == TouchpointType.DIRECT_MESSAGE:
            account.messages_today = (account.messages_today or 0) + 1  # type: ignore
        elif touchpoint_type in (TouchpointType.POST_REACT, TouchpointType.POST_COMMENT):
            account.posts_today = (account.posts_today or 0) + 1  # type: ignore

        session.commit()
    finally:
        session.close()


def record_failure(handle: str) -> None:
    """Record a failure and check if account should be paused."""
    from linkedin.db.accounts import _get_session
    from linkedin.db.models import Account

    session = _get_session()
    try:
        account = session.get(Account, handle)
        if not account:
            return

        # Increment consecutive failures
        account.consecutive_failures = (account.consecutive_failures or 0) + 1  # type: ignore

        # Check if we should pause the account
        if account.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:  # type: ignore
            account.paused = True  # type: ignore
            account.paused_reason = f"too_many_failures ({account.consecutive_failures} consecutive)"  # type: ignore
            logger.warning(
                "Account %s paused due to %d consecutive failures",
                handle,
                account.consecutive_failures,  # type: ignore
            )

        session.commit()
    finally:
        session.close()


def record_success(handle: str) -> None:
    """Reset consecutive failures on success."""
    from linkedin.db.accounts import _get_session
    from linkedin.db.models import Account

    session = _get_session()
    try:
        account = session.get(Account, handle)
        if not account:
            return

        if account.consecutive_failures > 0:  # type: ignore
            account.consecutive_failures = 0  # type: ignore
            logger.info("Reset consecutive failures for account %s", handle)
            session.commit()
    finally:
        session.close()


def _reset_daily_quotas_if_needed(account) -> None:
    """Reset daily quotas if quota_reset_at has passed."""

    now = datetime.now(timezone.utc)
    reset_at = account.quota_reset_at  # type: ignore

    # If no reset time set, or reset time has passed, reset quotas
    if reset_at is None or reset_at <= now:
        # Reset to tomorrow at midnight UTC
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        account.quota_reset_at = tomorrow  # type: ignore
        account.connections_today = 0  # type: ignore
        account.messages_today = 0  # type: ignore
        account.posts_today = 0  # type: ignore
        logger.debug("Reset daily quotas for account %s (next reset: %s)", account.handle, tomorrow)  # type: ignore

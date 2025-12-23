# api_server/services/quota.py
import logging
from datetime import datetime, timedelta, timezone
from typing import cast

from linkedin.db.accounts import get_account
from linkedin.db.models import Account
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
    if cast(bool, account.paused):
        reason = cast(str | None, account.paused_reason) or "unknown"
        return False, f"Account is paused: {reason}"

    # Reset daily quotas if needed
    _reset_daily_quotas_if_needed(account)

    # Check quota based on touchpoint type
    if touchpoint_type == TouchpointType.CONNECT:
        connections_today = cast(int, account.connections_today)
        daily_connections = cast(int, account.daily_connections)
        if connections_today >= daily_connections:
            return False, f"Daily connection quota exceeded ({connections_today}/{daily_connections})"
    elif touchpoint_type == TouchpointType.DIRECT_MESSAGE:
        messages_today = cast(int, account.messages_today)
        daily_messages = cast(int, account.daily_messages)
        if messages_today >= daily_messages:
            return False, f"Daily message quota exceeded ({messages_today}/{daily_messages})"
    elif touchpoint_type in (TouchpointType.POST_REACT, TouchpointType.POST_COMMENT):
        # Use a default daily post limit (could be configurable)
        daily_posts_limit = 30
        posts_today = cast(int, account.posts_today)
        if posts_today >= daily_posts_limit:
            return False, f"Daily post quota exceeded ({posts_today}/{daily_posts_limit})"

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
            account.connections_today = cast(int, account.connections_today or 0) + 1
        elif touchpoint_type == TouchpointType.DIRECT_MESSAGE:
            account.messages_today = cast(int, account.messages_today or 0) + 1
        elif touchpoint_type in (TouchpointType.POST_REACT, TouchpointType.POST_COMMENT):
            account.posts_today = cast(int, account.posts_today or 0) + 1

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
        consecutive_failures = cast(int, account.consecutive_failures or 0) + 1
        account.consecutive_failures = consecutive_failures

        # Check if we should pause the account
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            account.paused = True
            account.paused_reason = f"too_many_failures ({consecutive_failures} consecutive)"
            logger.warning(
                "Account %s paused due to %d consecutive failures",
                handle,
                consecutive_failures,
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

        consecutive_failures = cast(int, account.consecutive_failures)
        if consecutive_failures > 0:
            account.consecutive_failures = 0
            logger.info("Reset consecutive failures for account %s", handle)
            session.commit()
    finally:
        session.close()


def _reset_daily_quotas_if_needed(account: Account) -> None:
    """Reset daily quotas if quota_reset_at has passed."""

    now = datetime.now(timezone.utc)
    reset_at = cast(datetime | None, account.quota_reset_at)

    # If no reset time set, or reset time has passed, reset quotas
    if reset_at is None or reset_at <= now:
        # Reset to tomorrow at midnight UTC
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        account.quota_reset_at = tomorrow
        account.connections_today = 0
        account.messages_today = 0
        account.posts_today = 0
        handle = cast(str, account.handle)
        logger.debug("Reset daily quotas for account %s (next reset: %s)", handle, tomorrow)

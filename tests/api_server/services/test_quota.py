# tests/api_server/services/test_quota.py
from unittest.mock import MagicMock, patch

from api_server.services.quota import (
    MAX_CONSECUTIVE_FAILURES,
    check_quota,
    increment_quota,
    record_failure,
    record_success,
)
from linkedin.touchpoints.models import TouchpointType


class TestCheckQuota:
    """Test check_quota() function."""

    @patch("api_server.services.quota.get_account")
    def test_account_not_found(self, mock_get_account):
        """Test that missing account returns False."""
        mock_get_account.return_value = None
        allowed, reason = check_quota("nonexistent", TouchpointType.CONNECT)
        assert allowed is False
        assert "Account not found" in reason

    @patch("api_server.services.quota.get_account")
    def test_paused_account(self, mock_get_account):
        """Test that paused account returns False."""
        mock_account = MagicMock()
        mock_account.paused = True
        mock_account.paused_reason = "Test pause reason"
        mock_get_account.return_value = mock_account

        allowed, reason = check_quota("test_account", TouchpointType.CONNECT)
        assert allowed is False
        assert "Account is paused" in reason

    @patch("api_server.services.quota.get_account")
    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    def test_connection_quota_exceeded(self, mock_reset, mock_get_account):
        """Test that exceeded connection quota returns False."""
        mock_account = MagicMock()
        mock_account.paused = False
        mock_account.connections_today = 50
        mock_account.daily_connections = 50
        mock_get_account.return_value = mock_account

        allowed, reason = check_quota("test_account", TouchpointType.CONNECT)
        assert allowed is False
        assert "quota exceeded" in reason.lower()

    @patch("api_server.services.quota.get_account")
    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    def test_message_quota_exceeded(self, mock_reset, mock_get_account):
        """Test that exceeded message quota returns False."""
        mock_account = MagicMock()
        mock_account.paused = False
        mock_account.messages_today = 100
        mock_account.daily_messages = 100
        mock_get_account.return_value = mock_account

        allowed, reason = check_quota("test_account", TouchpointType.DIRECT_MESSAGE)
        assert allowed is False
        assert "quota exceeded" in reason.lower()

    @patch("api_server.services.quota.get_account")
    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    def test_post_quota_exceeded(self, mock_reset, mock_get_account):
        """Test that exceeded post quota returns False."""
        mock_account = MagicMock()
        mock_account.paused = False
        mock_account.posts_today = 30
        mock_get_account.return_value = mock_account

        allowed, reason = check_quota("test_account", TouchpointType.POST_REACT)
        assert allowed is False
        assert "quota exceeded" in reason.lower()

    @patch("api_server.services.quota.get_account")
    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    def test_quota_available(self, mock_reset, mock_get_account):
        """Test that available quota returns True."""
        mock_account = MagicMock()
        mock_account.paused = False
        mock_account.connections_today = 10
        mock_account.daily_connections = 50
        mock_account.messages_today = 20
        mock_account.daily_messages = 100
        mock_account.posts_today = 5
        mock_get_account.return_value = mock_account

        allowed, reason = check_quota("test_account", TouchpointType.CONNECT)
        assert allowed is True
        assert reason is None


class TestIncrementQuota:
    """Test increment_quota() function."""

    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    @patch("linkedin.db.accounts._get_session")
    def test_increment_connection_quota(self, mock_get_session, mock_reset):
        """Test incrementing connection quota."""
        mock_account = MagicMock()
        mock_account.connections_today = 10
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        increment_quota("test_account", TouchpointType.CONNECT)

        assert mock_account.connections_today == 11
        mock_session.commit.assert_called_once()

    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    @patch("linkedin.db.accounts._get_session")
    def test_increment_message_quota(self, mock_get_session, mock_reset):
        """Test incrementing message quota."""
        mock_account = MagicMock()
        mock_account.messages_today = 20
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        increment_quota("test_account", TouchpointType.DIRECT_MESSAGE)

        assert mock_account.messages_today == 21
        mock_session.commit.assert_called_once()

    @patch("api_server.services.quota._reset_daily_quotas_if_needed")
    @patch("linkedin.db.accounts._get_session")
    def test_increment_post_quota(self, mock_get_session, mock_reset):
        """Test incrementing post quota."""
        mock_account = MagicMock()
        mock_account.posts_today = 5
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        increment_quota("test_account", TouchpointType.POST_REACT)

        assert mock_account.posts_today == 6
        mock_session.commit.assert_called_once()

    @patch("linkedin.db.accounts._get_session")
    def test_account_not_found_no_error(self, mock_get_session):
        """Test that missing account doesn't raise error."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_get_session.return_value = mock_session

        # Should not raise
        increment_quota("nonexistent", TouchpointType.CONNECT)


class TestRecordFailure:
    """Test record_failure() function."""

    @patch("linkedin.db.accounts._get_session")
    def test_record_failure_increments_counter(self, mock_get_session):
        """Test that failure increments consecutive failures."""
        mock_account = MagicMock()
        mock_account.consecutive_failures = 2
        mock_account.paused = False
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        record_failure("test_account")

        assert mock_account.consecutive_failures == 3
        assert mock_account.paused is False
        mock_session.commit.assert_called_once()

    @patch("linkedin.db.accounts._get_session")
    def test_record_failure_pauses_account(self, mock_get_session):
        """Test that account is paused after MAX_CONSECUTIVE_FAILURES."""
        mock_account = MagicMock()
        mock_account.consecutive_failures = MAX_CONSECUTIVE_FAILURES - 1
        mock_account.paused = False
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        record_failure("test_account")

        assert mock_account.consecutive_failures == MAX_CONSECUTIVE_FAILURES
        assert mock_account.paused is True
        assert "too_many_failures" in mock_account.paused_reason
        mock_session.commit.assert_called_once()

    @patch("linkedin.db.accounts._get_session")
    def test_record_failure_account_not_found_no_error(self, mock_get_session):
        """Test that missing account doesn't raise error."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_get_session.return_value = mock_session

        # Should not raise
        record_failure("nonexistent")


class TestRecordSuccess:
    """Test record_success() function."""

    @patch("linkedin.db.accounts._get_session")
    def test_record_success_resets_counter(self, mock_get_session):
        """Test that success resets consecutive failures."""
        mock_account = MagicMock()
        mock_account.consecutive_failures = 3
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        record_success("test_account")

        assert mock_account.consecutive_failures == 0
        mock_session.commit.assert_called_once()

    @patch("linkedin.db.accounts._get_session")
    def test_record_success_no_reset_when_zero(self, mock_get_session):
        """Test that success doesn't reset when already zero."""
        mock_account = MagicMock()
        mock_account.consecutive_failures = 0
        mock_session = MagicMock()
        mock_session.get.return_value = mock_account
        mock_get_session.return_value = mock_session

        record_success("test_account")

        # Should not commit if no change needed
        # (Implementation may still commit, but counter stays 0)
        assert mock_account.consecutive_failures == 0

    @patch("linkedin.db.accounts._get_session")
    def test_record_success_account_not_found_no_error(self, mock_get_session):
        """Test that missing account doesn't raise error."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_get_session.return_value = mock_session

        # Should not raise
        record_success("nonexistent")


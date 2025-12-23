# tests/api_server/test_auth.py
import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException, status

from api_server.auth import get_api_key, verify_api_key


class TestGetApiKey:
    """Test get_api_key() function."""

    @patch.dict(os.environ, {"API_KEY": "test-key-123"})
    def test_get_api_key_from_env(self):
        """Test getting API key from environment."""
        key = get_api_key()
        assert key == "test-key-123"

    @patch.dict(os.environ, {}, clear=True)
    def test_get_api_key_not_set(self):
        """Test getting API key when not set."""
        key = get_api_key()
        assert key is None


class TestVerifyApiKey:
    """Test verify_api_key() function."""

    @patch("api_server.auth.get_api_key")
    def test_verify_api_key_success(self, mock_get_api_key):
        """Test successful API key verification."""
        mock_get_api_key.return_value = "test-key-123"
        verified_key = verify_api_key("test-key-123")
        assert verified_key == "test-key-123"

    @patch("api_server.auth.get_api_key")
    def test_verify_api_key_invalid(self, mock_get_api_key):
        """Test invalid API key raises HTTPException."""
        mock_get_api_key.return_value = "correct-key"
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key("wrong-key")
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Invalid API key" in exc_info.value.detail

    @patch("api_server.auth.get_api_key")
    def test_verify_api_key_missing(self, mock_get_api_key):
        """Test missing API key raises HTTPException."""
        mock_get_api_key.return_value = "test-key-123"
        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing" in exc_info.value.detail

    @patch("api_server.auth.get_api_key")
    def test_verify_api_key_dev_mode(self, mock_get_api_key):
        """Test that no API key configured allows all requests (dev mode)."""
        mock_get_api_key.return_value = None
        # Should not raise when no API key is configured
        verified_key = verify_api_key(None)
        assert verified_key == ""

    @patch("api_server.auth.get_api_key")
    def test_verify_api_key_dev_mode_with_key(self, mock_get_api_key):
        """Test that dev mode allows any key when no API key is configured."""
        mock_get_api_key.return_value = None
        # In dev mode (no API_KEY set), any provided key is accepted
        # Actually, looking at the implementation, it returns empty string when no key is configured
        verified_key = verify_api_key("any-key")
        # The implementation returns "" when no API_KEY is configured, regardless of input
        assert verified_key == ""


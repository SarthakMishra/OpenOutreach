# tests/api_server/services/conftest.py
"""Test configuration for api_server.services tests."""
import sys
from unittest.mock import MagicMock

# Mock the circular import before importing any api_server services
sys.modules["linkedin.sessions.account"] = MagicMock()


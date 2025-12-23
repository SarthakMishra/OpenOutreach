# tests/e2e/conftest.py
"""E2E test configuration and fixtures."""

import os
import time
from typing import Generator

import pytest
import requests

from linkedin.db.accounts import get_account


class APIClient:
    """API client wrapper for E2E tests."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"X-API-Key": api_key})

    def get(self, path: str, **kwargs):
        """GET request."""
        return self.session.get(f"{self.base_url}{path}", **kwargs)

    def post(self, path: str, **kwargs):
        """POST request."""
        return self.session.post(f"{self.base_url}{path}", **kwargs)

    def put(self, path: str, **kwargs):
        """PUT request."""
        return self.session.put(f"{self.base_url}{path}", **kwargs)

    def delete(self, path: str, **kwargs):
        """DELETE request."""
        return self.session.delete(f"{self.base_url}{path}", **kwargs)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Get API base URL from environment or default."""
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_key() -> str | None:
    """Get API key from environment."""
    return os.getenv("API_KEY")


@pytest.fixture(scope="session")
def test_handle() -> str:
    """Get test account handle from environment."""
    handle = os.getenv("E2E_TEST_HANDLE")
    if not handle:
        pytest.skip("E2E_TEST_HANDLE environment variable not set")
    return handle


@pytest.fixture(scope="session")
def api_client(api_base_url: str, api_key: str | None) -> APIClient:
    """Create API client with authentication."""
    return APIClient(api_base_url, api_key)


@pytest.fixture(scope="session")
def ensure_test_account(test_handle: str) -> None:
    """Ensure test account exists in database."""
    account = get_account(test_handle)
    if not account:
        pytest.skip(f"Test account '{test_handle}' not found in database. Please create it first.")
    if not account.active:
        pytest.skip(f"Test account '{test_handle}' is not active.")


@pytest.fixture(scope="session")
def ensure_cookies_exist(test_handle: str) -> None:
    """Ensure cookie file exists for test account (optional check)."""
    from linkedin.conf import COOKIES_DIR

    cookie_file = COOKIES_DIR / f"{test_handle}.json"
    if not cookie_file.exists():
        pytest.skip(
            f"Cookie file not found for '{test_handle}'. "
            "Please login first or skip cookie check with --skip-cookie-check"
        )


def poll_run_status(
    api_client: APIClient,
    run_id: str,
    timeout: int = 300,
    poll_interval: int = 2,
) -> dict:
    """
    Poll run status until terminal state.

    Args:
        api_client: API client session
        run_id: Run ID to poll
        timeout: Maximum time to wait in seconds (default: 300)
        poll_interval: Time between polls in seconds (default: 2)

    Returns:
        Final run response dict

    Raises:
        TimeoutError: If run doesn't reach terminal state within timeout
    """
    start_time = time.time()
    terminal_states = {"completed", "failed"}

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise TimeoutError(f"Run {run_id} did not reach terminal state within {timeout}s")

        response = api_client.get(f"/api/v1/runs/{run_id}")
        response.raise_for_status()
        run_data = response.json()

        status = run_data.get("status")
        if status in terminal_states:
            return run_data

        time.sleep(poll_interval)


@pytest.fixture
def poll_run(api_client: APIClient) -> Generator:
    """Fixture that provides poll_run_status function."""
    yield lambda run_id, timeout=300, poll_interval=2: poll_run_status(api_client, run_id, timeout, poll_interval)

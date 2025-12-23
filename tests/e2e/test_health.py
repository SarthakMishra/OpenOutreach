# tests/e2e/test_health.py
"""E2E test for health check endpoint."""
import pytest

from tests.e2e.conftest import APIClient


@pytest.mark.e2e
def test_health_check(api_client: APIClient):
    """Test that the API server is reachable."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


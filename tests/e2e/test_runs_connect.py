# tests/e2e/test_runs_connect.py
"""E2E test for connection request touchpoint."""
import pytest

from tests.e2e.conftest import APIClient


@pytest.mark.e2e
@pytest.mark.slow
def test_connect_run(
    api_client: APIClient,
    test_handle: str,
    ensure_test_account,
    poll_run,
):
    """Test connection request touchpoint execution via API."""
    # Create run request
    run_request = {
        "handle": test_handle,
        "touchpoint": {
            "type": "connect",
            "url": "https://www.linkedin.com/in/test-profile/",
            "public_identifier": "test-profile",
            "note": None,
        },
        "tags": {"test": "e2e_connect"},
    }

    # Create run
    response = api_client.post("/api/v1/runs", json=run_request)
    assert response.status_code == 201
    run_data = response.json()
    run_id = run_data["run_id"]

    assert run_data["handle"] == test_handle
    assert run_data["touchpoint_type"] == "connect"
    assert run_data["status"] == "pending"

    # Poll until terminal state
    final_run = poll_run(run_id, timeout=120)

    # Assert status transition
    assert final_run["status"] in ["completed", "failed"]

    # Assert result structure
    if final_run["status"] == "completed":
        assert final_run["result"] is not None
        assert final_run["error"] is None
    else:
        assert final_run["error"] is not None

    # Verify run record matches API response
    get_response = api_client.get(f"/api/v1/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json() == final_run


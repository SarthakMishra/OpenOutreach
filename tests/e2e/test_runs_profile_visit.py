# tests/e2e/test_runs_profile_visit.py
"""E2E test for profile visit touchpoint."""

import pytest

from tests.e2e.conftest import APIClient
from tests.fixtures.e2e_test_data import PROFILE_VISIT_DATA


@pytest.mark.e2e
@pytest.mark.slow
def test_profile_visit_run(
    api_client: APIClient,
    test_handle: str,
    ensure_test_account,
    poll_run,
):
    """Test profile visit touchpoint execution via API."""
    # Create run request
    run_request = {
        "handle": test_handle,
        "touchpoint": {
            "type": "profile_visit",
            "url": PROFILE_VISIT_DATA["url"],
            "duration_s": PROFILE_VISIT_DATA["duration_s"],
            "scroll_depth": PROFILE_VISIT_DATA["scroll_depth"],
        },
        "tags": PROFILE_VISIT_DATA["tags"],
    }

    # Create run
    response = api_client.post("/api/v1/runs", json=run_request)
    assert response.status_code == 201
    run_data = response.json()
    run_id = run_data["run_id"]

    assert run_data["handle"] == test_handle
    assert run_data["touchpoint_type"] == "profile_visit"
    assert run_data["status"] == "pending"

    # Poll until terminal state
    final_run = poll_run(run_id, timeout=60)

    # Assert successful completion
    assert final_run["status"] == "completed", f"Run failed with error: {final_run.get('error')}"
    assert final_run["result"] is not None
    assert final_run["error"] is None

    # Verify run record matches API response
    get_response = api_client.get(f"/api/v1/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json() == final_run

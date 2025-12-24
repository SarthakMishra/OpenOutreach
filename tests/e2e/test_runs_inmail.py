# tests/e2e/test_runs_inmail.py
"""E2E test for InMail touchpoint."""

import pytest

from tests.e2e.conftest import APIClient
from tests.fixtures.e2e_test_data import INMAIL_DATA


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.requires_inmail
def test_inmail_run(
    api_client: APIClient,
    test_handle: str,
    ensure_test_account,
    poll_run,
):
    """Test InMail touchpoint execution via API."""
    # Create run request
    run_request = {
        "handle": test_handle,
        "touchpoint": {
            "type": "inmail",
            "profile_url": INMAIL_DATA["profile_url"],
            "subject": INMAIL_DATA["subject"],
            "body": INMAIL_DATA["body"],
        },
        "tags": INMAIL_DATA["tags"],
    }

    # Create run
    response = api_client.post("/api/v1/runs", json=run_request)
    assert response.status_code == 201
    run_data = response.json()
    run_id = run_data["run_id"]

    assert run_data["handle"] == test_handle
    assert run_data["touchpoint_type"] == "inmail"
    assert run_data["status"] == "pending"

    # Poll until terminal state
    final_run = poll_run(run_id, timeout=120)

    # Assert successful completion
    assert final_run["status"] == "completed", f"Run failed with error: {final_run.get('error')}"
    assert final_run["result"] is not None
    assert final_run["error"] is None

    # Verify run record matches API response
    get_response = api_client.get(f"/api/v1/runs/{run_id}")
    assert get_response.status_code == 200
    assert get_response.json() == final_run

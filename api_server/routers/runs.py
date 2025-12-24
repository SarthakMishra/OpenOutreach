# api_server/routers/runs.py
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_server.auth import verify_api_key
from api_server.db.models import Run
from api_server.schemas.runs import RunCreateRequest, RunListResponse, RunResponse
from api_server.services.executor import create_run, get_run, list_runs
from linkedin.touchpoints.models import TouchpointType

router = APIRouter()


def _run_to_response(run: Run) -> RunResponse:
    """Convert Run model to RunResponse schema."""
    from datetime import datetime
    from typing import Any, cast

    return RunResponse(
        run_id=cast(str, run.run_id),
        handle=cast(str, run.handle),
        touchpoint_type=TouchpointType(cast(str, run.touchpoint_type)),
        status=cast(str, run.status),
        result=cast(dict[str, Any] | None, run.result),
        error=cast(str | None, run.error),
        error_screenshot=cast(str | None, run.error_screenshot),
        console_logs=cast(list[dict[str, Any]] | None, getattr(run, "console_logs", None)),
        started_at=cast(datetime | None, run.started_at),
        completed_at=cast(datetime | None, run.completed_at),
        duration_ms=cast(int | None, run.duration_ms),
        tags=cast(dict[str, Any] | None, run.tags),
        created_at=cast(datetime, run.created_at),
    )


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(request: RunCreateRequest, api_key: str = Depends(verify_api_key)):
    """Create a new run."""
    import logging
    import uuid

    logger = logging.getLogger(__name__)

    try:
        # Add run_id to touchpoint input
        run_id = str(uuid.uuid4())
        touchpoint_input = request.touchpoint.copy()
        touchpoint_input["handle"] = request.handle
        touchpoint_input["run_id"] = run_id

        # Create run record
        run_id_db = create_run(
            handle=request.handle,
            touchpoint_input=touchpoint_input,
            tags=request.tags,
        )

        # Execute if not dry run (background worker will pick it up)
        if not request.dry_run:
            # Don't execute immediately - let background worker handle it
            # This ensures proper queuing and account locking
            pass

        # Return run
        run = get_run(run_id_db)
        if not run:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create run")

        return _run_to_response(run)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating run: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}"
        )


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run_endpoint(run_id: str, api_key: str = Depends(verify_api_key)):
    """Get run status and results."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    return _run_to_response(run)


@router.get("/runs", response_model=RunListResponse)
def list_runs_endpoint(
    handle: str | None = Query(None, description="Filter by account handle"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of runs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    api_key: str = Depends(verify_api_key),
):
    """List runs with filtering."""
    runs, total = list_runs(handle=handle, status=status, limit=limit, offset=offset)

    return RunListResponse(
        runs=[_run_to_response(run) for run in runs],
        total=total,
        limit=limit,
        offset=offset,
    )

# api_server/routers/runs.py
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_server.auth import verify_api_key
from api_server.schemas.runs import RunCreateRequest, RunListResponse, RunResponse
from api_server.services.executor import create_run, get_run, list_runs
from linkedin.touchpoints.models import TouchpointType

router = APIRouter()


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run_endpoint(request: RunCreateRequest, api_key: str = Depends(verify_api_key)):
    """Create a new run."""
    # Add run_id to touchpoint input
    import uuid

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

    return RunResponse(
        run_id=run.run_id,  # type: ignore
        handle=run.handle,  # type: ignore
        touchpoint_type=TouchpointType(run.touchpoint_type),  # type: ignore
        status=run.status,  # type: ignore
        result=run.result,  # type: ignore
        error=run.error,  # type: ignore
        error_screenshot=run.error_screenshot,  # type: ignore
        console_logs=run.console_logs,  # type: ignore
        started_at=run.started_at,  # type: ignore
        completed_at=run.completed_at,  # type: ignore
        duration_ms=run.duration_ms,  # type: ignore
        tags=run.tags,  # type: ignore
        created_at=run.created_at,  # type: ignore
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run_endpoint(run_id: str, api_key: str = Depends(verify_api_key)):
    """Get run status and results."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    return RunResponse(
        run_id=run.run_id,  # type: ignore
        handle=run.handle,  # type: ignore
        touchpoint_type=TouchpointType(run.touchpoint_type),  # type: ignore
        status=run.status,  # type: ignore
        result=run.result,  # type: ignore
        error=run.error,  # type: ignore
        error_screenshot=run.error_screenshot,  # type: ignore
        console_logs=run.console_logs,  # type: ignore
        started_at=run.started_at,  # type: ignore
        completed_at=run.completed_at,  # type: ignore
        duration_ms=run.duration_ms,  # type: ignore
        tags=run.tags,  # type: ignore
        created_at=run.created_at,  # type: ignore
    )


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
        runs=[
            RunResponse(
                run_id=run.run_id,  # type: ignore
                handle=run.handle,  # type: ignore
                touchpoint_type=TouchpointType(run.touchpoint_type),  # type: ignore
                status=run.status,  # type: ignore
                result=run.result,  # type: ignore
                error=run.error,  # type: ignore
                error_screenshot=run.error_screenshot,  # type: ignore
                console_logs=run.console_logs,  # type: ignore
                started_at=run.started_at,  # type: ignore
                completed_at=run.completed_at,  # type: ignore
                duration_ms=run.duration_ms,  # type: ignore
                tags=run.tags,  # type: ignore
                created_at=run.created_at,  # type: ignore
            )
            for run in runs
        ],
        total=total,
        limit=limit,
        offset=offset,
    )

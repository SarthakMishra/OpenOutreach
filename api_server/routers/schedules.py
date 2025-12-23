# api_server/routers/schedules.py
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api_server.auth import verify_api_key
from api_server.db.models import Schedule
from api_server.schemas.schedules import ScheduleCreateRequest, ScheduleListResponse, ScheduleResponse
from api_server.services.scheduler import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
)
from linkedin.touchpoints.models import TouchpointType

router = APIRouter()


def _schedule_to_response(schedule: Schedule) -> ScheduleResponse:
    """Convert Schedule model to ScheduleResponse schema."""
    return ScheduleResponse(
        schedule_id=cast(str, schedule.schedule_id),
        handle=cast(str, schedule.handle),
        touchpoint_type=TouchpointType(cast(str, schedule.touchpoint_type)),
        cron=cast(str, schedule.cron),
        next_run_at=cast(datetime | None, schedule.next_run_at),
        active=cast(bool, schedule.active),
        tags=cast(dict[str, Any] | None, schedule.tags),
        created_at=cast(datetime, schedule.created_at),
        updated_at=cast(datetime, schedule.updated_at),
    )


@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule_endpoint(request: ScheduleCreateRequest, api_key: str = Depends(verify_api_key)):
    """Create a new schedule."""
    # Add run_id placeholder to touchpoint input (will be generated on each execution)
    touchpoint_input = request.touchpoint.copy()
    touchpoint_input["handle"] = request.handle

    schedule_id = create_schedule(
        handle=request.handle,
        touchpoint_input=touchpoint_input,
        cron=request.cron,
        tags=request.tags,
    )

    schedule = get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create schedule")

    return _schedule_to_response(schedule)


@router.get("/schedules", response_model=ScheduleListResponse)
def list_schedules_endpoint(
    handle: str | None = Query(None, description="Filter by account handle"),
    api_key: str = Depends(verify_api_key),
):
    """List schedules."""
    schedules = list_schedules(handle=handle)

    return ScheduleListResponse(schedules=[_schedule_to_response(schedule) for schedule in schedules])


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_endpoint(schedule_id: str, api_key: str = Depends(verify_api_key)):
    """Delete a schedule."""
    success = delete_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

# api_server/schemas/schedules.py
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from linkedin.touchpoints.models import TouchpointType


class ScheduleCreateRequest(BaseModel):
    """Request to create a new schedule."""

    handle: str = Field(..., description="Account handle to execute touchpoint")
    touchpoint: Dict[str, Any] = Field(..., description="Touchpoint input payload")
    cron: str = Field(..., description="Cron expression (e.g., '0 9 * * *' for daily at 9 AM)")
    tags: Optional[Dict[str, Any]] = Field(None, description="Optional tags for filtering")


class ScheduleResponse(BaseModel):
    """Schedule response."""

    schedule_id: str
    handle: str
    touchpoint_type: TouchpointType
    cron: str
    active: str  # "active" or "paused"
    tags: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ScheduleListResponse(BaseModel):
    """List of schedules."""

    schedules: list[ScheduleResponse]

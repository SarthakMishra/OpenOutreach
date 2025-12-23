# api_server/schemas/runs.py
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from linkedin.touchpoints.models import TouchpointType


class RunCreateRequest(BaseModel):
    """Request to create a new run."""

    handle: str = Field(..., description="Account handle to execute touchpoint")
    touchpoint: Dict[str, Any] = Field(..., description="Touchpoint input payload")
    dry_run: bool = Field(False, description="If true, validate but don't execute")
    tags: Optional[Dict[str, Any]] = Field(None, description="Optional tags for filtering")


class RunResponse(BaseModel):
    """Run status and result response."""

    run_id: str
    handle: str
    touchpoint_type: TouchpointType
    status: str  # "pending", "running", "completed", "failed"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_screenshot: Optional[str] = None  # Path to screenshot on failure
    console_logs: Optional[list[Dict[str, Any]]] = None  # Browser console logs
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    tags: Optional[Dict[str, Any]] = None
    created_at: datetime


class RunListResponse(BaseModel):
    """List of runs with pagination."""

    runs: list[RunResponse]
    total: int
    limit: int
    offset: int

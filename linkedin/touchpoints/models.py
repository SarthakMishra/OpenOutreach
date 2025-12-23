# linkedin/touchpoints/models.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TouchpointType(str, Enum):
    """Supported touchpoint types."""

    PROFILE_ENRICH = "profile_enrich"
    PROFILE_VISIT = "profile_visit"
    CONNECT = "connect"
    DIRECT_MESSAGE = "direct_message"
    POST_REACT = "post_react"
    POST_COMMENT = "post_comment"
    INMAIL = "inmail"


class TouchpointInput(BaseModel):
    """Base class for touchpoint input models."""

    type: TouchpointType
    handle: str = Field(..., description="Account handle to execute touchpoint")
    run_id: str = Field(..., description="Unique run identifier (UUID)")

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, v: str) -> str:
        """Validate run_id is a valid UUID format."""
        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"run_id must be a valid UUID, got: {v}")
        return v


class ProfileEnrichInput(TouchpointInput):
    """Input for profile enrichment touchpoint."""

    type: Literal[TouchpointType.PROFILE_ENRICH] = TouchpointType.PROFILE_ENRICH
    public_identifier: Optional[str] = Field(None, description="LinkedIn public identifier")
    url: Optional[str] = Field(None, description="Full LinkedIn profile URL")

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one identifier is provided."""
        if not self.public_identifier and not self.url:
            raise ValueError("Either public_identifier or url must be provided")


class ProfileVisitInput(TouchpointInput):
    """Input for profile visit touchpoint."""

    type: Literal[TouchpointType.PROFILE_VISIT] = TouchpointType.PROFILE_VISIT
    url: str = Field(..., description="LinkedIn profile URL to visit")
    duration_s: float = Field(5.0, ge=0.0, description="Duration to stay on page (seconds)")
    scroll_depth: int = Field(3, ge=0, description="Number of scroll steps to perform")


class ConnectInput(TouchpointInput):
    """Input for connection request touchpoint."""

    type: Literal[TouchpointType.CONNECT] = TouchpointType.CONNECT
    url: str = Field(..., description="LinkedIn profile URL")
    public_identifier: Optional[str] = Field(None, description="LinkedIn public identifier")
    note: Optional[str] = Field(None, description="Optional connection note")


class DirectMessageInput(TouchpointInput):
    """Input for direct message touchpoint."""

    type: Literal[TouchpointType.DIRECT_MESSAGE] = TouchpointType.DIRECT_MESSAGE
    url: str = Field(..., description="LinkedIn profile URL")
    public_identifier: Optional[str] = Field(None, description="LinkedIn public identifier")
    message: str = Field(..., min_length=1, description="Message text to send")


class PostReactInput(TouchpointInput):
    """Input for post reaction touchpoint."""

    type: Literal[TouchpointType.POST_REACT] = TouchpointType.POST_REACT
    post_url: str = Field(..., description="LinkedIn post URL")
    reaction: Literal["LIKE", "CELEBRATE", "SUPPORT", "LOVE", "INSIGHTFUL", "CURIOUS"] = Field(
        ..., description="Reaction type"
    )


class PostCommentInput(TouchpointInput):
    """Input for post comment touchpoint."""

    type: Literal[TouchpointType.POST_COMMENT] = TouchpointType.POST_COMMENT
    post_url: str = Field(..., description="LinkedIn post URL")
    comment_text: str = Field(..., min_length=1, description="Comment text to post")


class InMailInput(TouchpointInput):
    """Input for InMail touchpoint."""

    type: Literal[TouchpointType.INMAIL] = TouchpointType.INMAIL
    profile_url: str = Field(..., description="LinkedIn profile URL")
    subject: Optional[str] = Field(None, description="InMail subject line")
    body: str = Field(..., min_length=1, description="InMail body text")


class TouchpointResult(BaseModel):
    """Standard touchpoint execution result."""

    success: bool = Field(..., description="Whether touchpoint executed successfully")
    result: Optional[Dict[str, Any]] = Field(None, description="Touchpoint-specific result data")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")

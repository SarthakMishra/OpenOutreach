# api_server/schemas/accounts.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AccountCreateRequest(BaseModel):
    """Request to create or update an account."""

    handle: str = Field(..., description="Unique account handle/identifier")
    username: str = Field(..., description="LinkedIn username/email")
    password: str = Field(..., description="LinkedIn password")
    active: bool = Field(True, description="Whether account is active")
    proxy: Optional[str] = Field(None, description="Optional proxy configuration")
    daily_connections: int = Field(50, ge=0, description="Daily connection limit")
    daily_messages: int = Field(20, ge=0, description="Daily message limit")
    booking_link: Optional[str] = Field(None, description="Optional booking link")


class AccountResponse(BaseModel):
    """Account response."""

    handle: str
    active: bool
    proxy: Optional[str] = None
    daily_connections: int
    daily_messages: int
    booking_link: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    """List of accounts."""

    accounts: list[AccountResponse]

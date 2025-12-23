# api_server/schemas/accounts.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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

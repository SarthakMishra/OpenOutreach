# api_server/routers/accounts.py
from datetime import datetime
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status

from api_server.auth import verify_api_key
from api_server.schemas.accounts import (
    AccountCreateRequest,
    AccountListResponse,
    AccountResponse,
)
from linkedin.db.accounts import delete_account, get_account, list_accounts, upsert_account
from linkedin.db.models import Account

router = APIRouter()


def _account_to_response(account: Account) -> AccountResponse:
    """Convert Account model to AccountResponse schema."""
    return AccountResponse(
        handle=cast(str, account.handle),
        active=cast(bool, account.active),
        proxy=cast(str | None, account.proxy),
        daily_connections=cast(int, account.daily_connections),
        daily_messages=cast(int, account.daily_messages),
        booking_link=cast(str | None, account.booking_link),
        consecutive_failures=cast(int, account.consecutive_failures or 0),
        paused=cast(bool, account.paused or False),
        paused_reason=cast(str | None, account.paused_reason),
        connections_today=cast(int, account.connections_today or 0),
        messages_today=cast(int, account.messages_today or 0),
        posts_today=cast(int, account.posts_today or 0),
        created_at=cast(datetime, account.created_at),
        updated_at=cast(datetime, account.updated_at),
    )


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(request: AccountCreateRequest, api_key: str = Depends(verify_api_key)):
    """Create or update a LinkedIn account."""
    try:
        upsert_account(request.model_dump())
        account = get_account(request.handle)
        if not account:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create account")
        return _account_to_response(account)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/accounts", response_model=AccountListResponse)
def get_accounts(api_key: str = Depends(verify_api_key)):
    """List all accounts."""
    accounts = list_accounts(active_only=False)
    return AccountListResponse(accounts=[_account_to_response(acc) for acc in accounts])


@router.get("/accounts/{handle}", response_model=AccountResponse)
def get_account_endpoint(handle: str, api_key: str = Depends(verify_api_key)):
    """Get a specific account by handle."""
    account = get_account(handle)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return _account_to_response(account)


@router.delete("/accounts/{handle}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_endpoint(handle: str, api_key: str = Depends(verify_api_key)):
    """Delete an account."""
    success = delete_account(handle)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

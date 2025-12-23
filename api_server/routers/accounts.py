# api_server/routers/accounts.py
from fastapi import APIRouter, Depends, HTTPException, status

from api_server.auth import verify_api_key
from api_server.schemas.accounts import (
    AccountCreateRequest,
    AccountListResponse,
    AccountResponse,
)
from linkedin.db.accounts import delete_account, get_account, list_accounts, upsert_account

router = APIRouter()


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(request: AccountCreateRequest, api_key: str = Depends(verify_api_key)):
    """Create or update a LinkedIn account."""
    try:
        upsert_account(request.model_dump())
        account = get_account(request.handle)
        if not account:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create account")
        return AccountResponse(
            handle=account.handle,  # type: ignore
            active=account.active,  # type: ignore
            proxy=account.proxy,  # type: ignore
            daily_connections=account.daily_connections,  # type: ignore
            daily_messages=account.daily_messages,  # type: ignore
            booking_link=account.booking_link,  # type: ignore
            consecutive_failures=account.consecutive_failures or 0,  # type: ignore
            paused=account.paused or False,  # type: ignore
            paused_reason=account.paused_reason,  # type: ignore
            connections_today=account.connections_today or 0,  # type: ignore
            messages_today=account.messages_today or 0,  # type: ignore
            posts_today=account.posts_today or 0,  # type: ignore
            created_at=account.created_at,  # type: ignore
            updated_at=account.updated_at,  # type: ignore
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/accounts", response_model=AccountListResponse)
def get_accounts(api_key: str = Depends(verify_api_key)):
    """List all accounts."""
    accounts = list_accounts(active_only=False)
    return AccountListResponse(
        accounts=[
            AccountResponse(
                handle=acc.handle,  # type: ignore
                active=acc.active,  # type: ignore
                proxy=acc.proxy,  # type: ignore
                daily_connections=acc.daily_connections,  # type: ignore
                daily_messages=acc.daily_messages,  # type: ignore
                booking_link=acc.booking_link,  # type: ignore
                created_at=acc.created_at,  # type: ignore
                updated_at=acc.updated_at,  # type: ignore
            )
            for acc in accounts
        ]
    )


@router.get("/accounts/{handle}", response_model=AccountResponse)
def get_account_endpoint(handle: str, api_key: str = Depends(verify_api_key)):
    """Get a specific account by handle."""
    account = get_account(handle)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return AccountResponse(
        handle=account.handle,  # type: ignore
        active=account.active,  # type: ignore
        proxy=account.proxy,  # type: ignore
        daily_connections=account.daily_connections,  # type: ignore
        daily_messages=account.daily_messages,  # type: ignore
        booking_link=account.booking_link,  # type: ignore
        created_at=account.created_at,  # type: ignore
        updated_at=account.updated_at,  # type: ignore
    )


@router.delete("/accounts/{handle}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_endpoint(handle: str, api_key: str = Depends(verify_api_key)):
    """Delete an account."""
    success = delete_account(handle)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

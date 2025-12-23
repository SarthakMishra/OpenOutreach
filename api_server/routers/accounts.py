# api_server/routers/accounts.py
from fastapi import APIRouter, Depends

from api_server.auth import verify_api_key
from api_server.schemas.accounts import AccountListResponse, AccountResponse
from linkedin.db.accounts import list_accounts

router = APIRouter()


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

# api_server/auth.py
import os
from typing import Optional

from fastapi import Header, HTTPException, status

API_KEY_HEADER = "X-API-Key"


def get_api_key() -> Optional[str]:
    """Get API key from environment variable."""
    return os.getenv("API_KEY")


def verify_api_key(api_key: Optional[str] = Header(None, alias=API_KEY_HEADER)) -> str:
    """
    Verify API key from request header.

    Raises HTTPException if key is missing or invalid.
    """
    expected_key = get_api_key()

    if not expected_key:
        # If no API key is configured, allow all requests (development mode)
        return ""

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {API_KEY_HEADER} header",
        )

    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key

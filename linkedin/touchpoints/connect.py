# linkedin/touchpoints/connect.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.connect import send_connection_request
from linkedin.navigation.enums import ProfileState
from linkedin.sessions.registry import SessionKey
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import ConnectInput

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class ConnectTouchpoint(Touchpoint):
    """Touchpoint for sending LinkedIn connection requests."""

    def __init__(self, input: ConnectInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        if not self.input.url and not self.input.public_identifier:
            raise ValueError("Either url or public_identifier must be provided")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute connection request.

        Returns:
            Dictionary with:
            - success: bool
            - result: dict with status, or None
            - error: str or None
        """
        try:
            # Create session key
            key = SessionKey(handle=self.input.handle, run_id=self.input.run_id)

            # Prepare profile dict for action
            profile_dict: Dict[str, Any] = {}
            if self.input.url:
                profile_dict["url"] = self.input.url
            if self.input.public_identifier:
                profile_dict["public_identifier"] = self.input.public_identifier

            # Execute action
            status = send_connection_request(key, profile_dict, note=self.input.note)

            # Normalize result
            # Success if status is PENDING (request sent) or CONNECTED (already connected)
            success = status in [ProfileState.PENDING, ProfileState.CONNECTED]
            return {
                "success": success,
                "result": {"status": status.value},
                "error": None,
            }

        except Exception as e:
            logger.error("Connection request failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }

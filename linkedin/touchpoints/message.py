# linkedin/touchpoints/message.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.message import send_follow_up_message
from linkedin.navigation.enums import MessageStatus
from linkedin.sessions.registry import SessionKey
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import DirectMessageInput

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class DirectMessageTouchpoint(Touchpoint):
    """Touchpoint for sending LinkedIn direct messages."""

    def __init__(self, input: DirectMessageInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        if not self.input.message or not self.input.message.strip():
            raise ValueError("Message text must not be empty")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute direct message sending.

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
            status = send_follow_up_message(key, profile_dict, message=self.input.message)

            # Normalize result
            success = status == MessageStatus.SENT
            return {
                "success": success,
                "result": {"status": status.value},
                "error": None if success else f"Message not sent: {status.value}",
            }

        except Exception as e:
            logger.error("Direct message failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }

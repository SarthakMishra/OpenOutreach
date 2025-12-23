# linkedin/touchpoints/inmail.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.inmail import send_inmail
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import InMailInput

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class InMailTouchpoint(Touchpoint):
    """Touchpoint for sending LinkedIn InMails."""

    def __init__(self, input: InMailInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        if not self.input.body or not self.input.body.strip():
            raise ValueError("InMail body must not be empty")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute InMail sending.

        Returns:
            Dictionary with:
            - success: bool
            - result: dict with InMail details, or None
            - error: str or None (error reason: NOT_AVAILABLE, NO_CREDITS, UI_CHANGED, BLOCKED, etc.)
        """
        try:
            # Execute action
            success, error_reason = send_inmail(
                session=session,
                profile_url=self.input.profile_url,
                subject=self.input.subject,
                body=self.input.body,
            )

            # Normalize result
            return {
                "success": success,
                "result": {
                    "profile_url": self.input.profile_url,
                    "subject": self.input.subject,
                } if success else None,
                "error": error_reason if not success else None,
            }

        except Exception as e:
            logger.error("InMail failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }


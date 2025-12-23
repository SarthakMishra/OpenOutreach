# linkedin/touchpoints/visit.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.visit import visit_profile
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import ProfileVisitInput

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class ProfileVisitTouchpoint(Touchpoint):
    """Touchpoint for visiting LinkedIn profiles."""

    def __init__(self, input: ProfileVisitInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        if not self.input.url:
            raise ValueError("Profile URL is required")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute profile visit.

        Returns:
            Dictionary with:
            - success: bool
            - result: dict with visit details, or None
            - error: str or None
        """
        try:
            # Prepare profile dict for action
            profile_dict: Dict[str, Any] = {"url": self.input.url}

            # Execute action
            success = visit_profile(
                session=session,
                profile=profile_dict,
                duration_s=self.input.duration_s,
                scroll_depth=self.input.scroll_depth,
            )

            # Normalize result
            return {
                "success": success,
                "result": {
                    "url": self.input.url,
                    "duration_s": self.input.duration_s,
                    "scroll_depth": self.input.scroll_depth,
                }
                if success
                else None,
                "error": None if success else "Failed to visit profile",
            }

        except Exception as e:
            logger.error("Profile visit failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }

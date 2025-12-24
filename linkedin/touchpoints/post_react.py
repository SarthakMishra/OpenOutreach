# linkedin/touchpoints/post_react.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.post_react import react_to_post
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import PostReactInput

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class PostReactTouchpoint(Touchpoint):
    """Touchpoint for reacting to LinkedIn posts."""

    def __init__(self, input: PostReactInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        valid_reactions = ["LIKE", "CELEBRATE", "SUPPORT", "LOVE", "INSIGHTFUL", "CURIOUS"]
        if self.input.reaction not in valid_reactions:
            raise ValueError(f"Invalid reaction type: {self.input.reaction}")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute post reaction.

        Returns:
            Dictionary with:
            - success: bool
            - result: dict with reaction details, or None
            - error: str or None
        """
        try:
            # Ensure browser is initialized
            session.ensure_browser()

            # Execute action
            success = react_to_post(
                session=session,
                post_url=self.input.post_url,
                reaction=self.input.reaction,
            )

            # Normalize result
            return {
                "success": success,
                "result": {
                    "post_url": self.input.post_url,
                    "reaction": self.input.reaction,
                }
                if success
                else None,
                "error": None if success else "Failed to react to post",
            }

        except Exception as e:
            logger.error("Post reaction failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }

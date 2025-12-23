# linkedin/touchpoints/post_comment.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.post_comment import comment_on_post
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import PostCommentInput

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class PostCommentTouchpoint(Touchpoint):
    """Touchpoint for commenting on LinkedIn posts."""

    def __init__(self, input: PostCommentInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        if not self.input.comment_text or not self.input.comment_text.strip():
            raise ValueError("Comment text must not be empty")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute post comment.

        Returns:
            Dictionary with:
            - success: bool
            - result: dict with comment details, or None
            - error: str or None
        """
        try:
            # Execute action
            success = comment_on_post(
                session=session,
                post_url=self.input.post_url,
                comment_text=self.input.comment_text,
            )

            # Normalize result
            return {
                "success": success,
                "result": {
                    "post_url": self.input.post_url,
                    "comment_text": self.input.comment_text,
                } if success else None,
                "error": None if success else "Post comment not yet implemented",
            }

        except Exception as e:
            logger.error("Post comment failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }


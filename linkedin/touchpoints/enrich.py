# linkedin/touchpoints/enrich.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict

from linkedin.actions.profile import scrape_profile

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession
from linkedin.sessions.account import AccountSession
from linkedin.sessions.registry import SessionKey
from linkedin.touchpoints.base import Touchpoint
from linkedin.touchpoints.models import ProfileEnrichInput

logger = logging.getLogger(__name__)


class ProfileEnrichTouchpoint(Touchpoint):
    """Touchpoint for enriching LinkedIn profiles."""

    def __init__(self, input: ProfileEnrichInput):
        self.input = input

    def validate_input(self) -> None:
        """Validate touchpoint input."""
        # Pydantic already validates, but can add business logic here
        if not self.input.public_identifier and not self.input.url:
            raise ValueError("Either public_identifier or url must be provided")

    def execute(self, session: "AccountSession") -> Dict[str, Any]:
        """
        Execute profile enrichment.

        Returns:
            Dictionary with:
            - success: bool
            - result: dict with profile and data, or None
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
            profile, data = scrape_profile(key, profile_dict)

            # Normalize result
            success = profile is not None
            return {
                "success": success,
                "result": {"profile": profile, "data": data} if profile else None,
                "error": None if success else "Failed to enrich profile",
            }

        except Exception as e:
            logger.error("Profile enrichment failed: %s", e, exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": str(e),
            }

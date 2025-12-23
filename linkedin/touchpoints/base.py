# linkedin/touchpoints/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from linkedin.sessions.account import AccountSession


class Touchpoint(ABC):
    """
    Base class for all touchpoints.

    A touchpoint is a single atomic automation action with validated input
    and deterministic outcome. Each touchpoint executes ONE LinkedIn action.
    """

    @abstractmethod
    def execute(self, session: AccountSession) -> Dict[str, Any]:
        """
        Execute the touchpoint against an AccountSession.

        Args:
            session: The account session with browser and database access

        Returns:
            Dictionary with execution results:
            - success: bool
            - result: Any (touchpoint-specific result data)
            - error: str | None (error message if failed)
        """
        pass

    @abstractmethod
    def validate_input(self) -> None:
        """
        Validate touchpoint input parameters.
        Raises ValueError if input is invalid.
        """
        pass

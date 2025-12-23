# linkedin/actions/inmail.py
import logging

from linkedin.navigation.utils import goto_page
from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


# InMail error reasons
class InMailError:
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NO_CREDITS = "NO_CREDITS"
    UI_CHANGED = "UI_CHANGED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


def send_inmail(session: AccountSession, profile_url: str, subject: str | None, body: str) -> tuple[bool, str | None]:
    """
    Send an InMail to a LinkedIn profile.

    Args:
        session: Account session with browser access
        profile_url: URL of the LinkedIn profile to send InMail to
        subject: Optional InMail subject line
        body: InMail body text

    Returns:
        Tuple of (success: bool, error_reason: str | None)
        error_reason can be: NOT_AVAILABLE, NO_CREDITS, UI_CHANGED, BLOCKED, UNKNOWN

    Note:
        This is a placeholder implementation. Requires research on:
        - Premium account detection
        - InMail availability detection
        - InMail compose modal selectors (standard LinkedIn UI only)
        - Credit availability checking
        - Sales Navigator flows (not supported initially)
    """
    assert session.page is not None, "page must be initialized via ensure_browser()"
    page = session.page

    if not body or not body.strip():
        logger.error("InMail body cannot be empty")
        return False, InMailError.UNKNOWN

    try:
        # Navigate to profile
        logger.info("Navigating to profile → %s", profile_url)
        goto_page(
            session,
            action=lambda: page.goto(profile_url),
            expected_url_pattern="/in/",
            error_message="Failed to navigate to profile",
            to_scrape=False,
        )

        logger.info("Sending InMail (subject: %s)", subject or "None")

        # TODO: Implement InMail logic
        # 1. Check if InMail is available (premium account, recipient settings)
        # 2. Try to open InMail compose modal via "Message" or "More actions" menu
        # 3. Detect InMail compose modal (not regular message)
        # 4. Fill subject (if provided) and body fields
        # 5. Send InMail
        # 6. Verify success toast
        # 7. Handle errors:
        #    - NOT_AVAILABLE: InMail option not available
        #    - NO_CREDITS: No InMail credits remaining
        #    - UI_CHANGED: Could not find expected UI elements
        #    - BLOCKED: Recipient has blocked InMail

        # Placeholder: Just wait a bit to simulate action
        session.wait(to_scrape=False)

        logger.warning("InMail not yet implemented - placeholder only")
        return False, InMailError.NOT_AVAILABLE  # Return error until properly implemented

    except Exception as e:
        logger.error("InMail failed: %s", e, exc_info=True)
        return False, InMailError.UNKNOWN

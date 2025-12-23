# linkedin/actions/visit.py
import logging
import time
from typing import TYPE_CHECKING, Any, Dict
from urllib.parse import urlparse

from linkedin.navigation.utils import goto_page

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


def visit_profile(
    session: "AccountSession", profile: Dict[str, Any], duration_s: float = 5.0, scroll_depth: int = 3
) -> bool:
    """
    Visit a LinkedIn profile and simulate human behavior.

    Args:
        session: Account session with browser access
        profile: Profile dict with 'url' and optionally 'public_identifier'
        duration_s: Duration to stay on page in seconds (default: 5.0)
        scroll_depth: Number of scroll steps to perform (default: 3)

    Returns:
        True if visit was successful, False otherwise
    """
    assert session.page is not None, "page must be initialized via ensure_browser()"
    page = session.page

    url = profile.get("url")
    if not url:
        logger.error("Profile URL is required for visit")
        return False

    # Extract public_identifier from URL if not provided
    public_identifier = profile.get("public_identifier")
    if not public_identifier:
        # Try to extract from URL
        parsed = urlparse(url)
        if "/in/" in parsed.path:
            public_identifier = parsed.path.split("/in/")[-1].split("/")[0]

    if not public_identifier:
        logger.warning("Could not determine public_identifier from URL: %s", url)
        # Still proceed with visit using URL pattern matching

    try:
        # Navigate to profile
        expected_pattern = f"/in/{public_identifier}" if public_identifier else "/in/"
        goto_page(
            session,
            action=lambda: page.goto(url),
            expected_url_pattern=expected_pattern,
            error_message="Failed to navigate to profile",
            to_scrape=False,  # Don't scrape during visit
        )

        logger.info("Visiting profile → %s (duration: %.1fs, scrolls: %d)", url, duration_s, scroll_depth)

        # Simulate scrolling
        for i in range(scroll_depth):
            # Scroll down
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            # Wait a bit between scrolls
            time.sleep(duration_s / scroll_depth)

        # Wait for remaining duration
        remaining_time = duration_s - (duration_s / scroll_depth * scroll_depth)
        if remaining_time > 0:
            time.sleep(remaining_time)

        logger.info("Profile visit completed → %s", url)
        return True

    except Exception as e:
        logger.error("Profile visit failed: %s", e, exc_info=True)
        return False

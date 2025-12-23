# linkedin/actions/post_react.py
import logging
import time
from typing import TYPE_CHECKING

from linkedin.navigation.utils import goto_page

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)

# Reaction types
REACTION_TYPES = ["LIKE", "CELEBRATE", "SUPPORT", "LOVE", "INSIGHTFUL", "CURIOUS"]

# Reaction label mapping for selectors
REACTION_LABELS = {
    "LIKE": "like",
    "CELEBRATE": "celebrate",
    "SUPPORT": "support",
    "LOVE": "love",
    "INSIGHTFUL": "insightful",
    "CURIOUS": "curious",
}


def react_to_post(session: "AccountSession", post_url: str, reaction: str) -> bool:
    """
    React to a LinkedIn post.

    Args:
        session: Account session with browser access
        post_url: URL of the LinkedIn post
        reaction: Reaction type (LIKE/CELEBRATE/SUPPORT/LOVE/INSIGHTFUL/CURIOUS)

    Returns:
        True if reaction was successful, False otherwise
    """
    assert session.page is not None, "page must be initialized via ensure_browser()"
    page = session.page

    if reaction not in REACTION_TYPES:
        logger.error("Invalid reaction type: %s. Must be one of: %s", reaction, REACTION_TYPES)
        return False

    try:
        # Navigate to post URL
        logger.info("Navigating to post → %s", post_url)
        goto_page(
            session,
            action=lambda: page.goto(post_url, wait_until="domcontentloaded", timeout=60000),
            expected_url_pattern="/feed/update/",
            error_message="Failed to navigate to post",
            to_scrape=False,
        )

        # Wait for page to fully render
        try:
            page.wait_for_load_state("load", timeout=30000)
        except Exception:
            logger.debug("Page load timeout, continuing anyway...")
        time.sleep(2)  # Additional wait for dynamic content

        logger.info("Reacting to post with: %s", reaction)

        # Find the like button (primary selector)
        like_button = page.locator('button[aria-label*="like" i]').first
        if like_button.count() == 0:
            # Try alternative selectors for like button
            alt_like_selectors = [
                'button[data-control-name*="like"]',
                'button[class*="reactions-react-button"]',
                'button[aria-label*="React" i]',
            ]
            for selector in alt_like_selectors:
                alt_button = page.locator(selector).first
                if alt_button.count() > 0:
                    logger.debug("Found like button using alternative selector: %s", selector)
                    like_button = alt_button
                    break

        if like_button.count() == 0:
            logger.error("Could not find like/reaction button on post")
            return False

        # Hover over like button to open reaction menu
        logger.debug("Hovering over like button to open reaction menu")
        like_button.hover()
        time.sleep(1)  # Wait for reaction menu to appear

        # Find the specific reaction button
        reaction_label = REACTION_LABELS.get(reaction.upper(), "like")
        reaction_button = page.locator(f'button[aria-label*="{reaction_label}" i]').first

        if reaction_button.count() == 0:
            # Try alternative selectors for reaction button
            alt_reaction_selectors = [
                f'button[data-testid*="{reaction_label}" i]',
                f'button[aria-label*="React with {reaction_label}" i]',
                f'div[role="button"][aria-label*="{reaction_label}" i]',
            ]
            for selector in alt_reaction_selectors:
                alt_button = page.locator(selector).first
                if alt_button.count() > 0:
                    logger.debug("Found reaction button using alternative selector: %s", selector)
                    reaction_button = alt_button
                    break

        if reaction_button.count() == 0:
            logger.error("Could not find %s reaction button in menu", reaction)
            return False

        # Click the reaction button
        logger.debug("Clicking %s reaction button", reaction)
        reaction_button.click()
        time.sleep(1)  # Wait for reaction to register

        # Verify success by checking if button state changed or toast appeared
        # For now, assume success if no error occurred
        logger.info("Successfully reacted to post with %s", reaction)
        return True

    except Exception as e:
        logger.error("Post reaction failed: %s", e, exc_info=True)
        return False

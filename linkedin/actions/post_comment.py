# linkedin/actions/post_comment.py
import logging
import time

from linkedin.navigation.utils import goto_page
from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


def comment_on_post(session: AccountSession, post_url: str, comment_text: str) -> bool:
    """
    Comment on a LinkedIn post.

    Args:
        session: Account session with browser access
        post_url: URL of the LinkedIn post
        comment_text: Text of the comment to post

    Returns:
        True if comment was successful, False otherwise
    """
    assert session.page is not None, "page must be initialized via ensure_browser()"
    page = session.page

    if not comment_text or not comment_text.strip():
        logger.error("Comment text cannot be empty")
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

        logger.info("Commenting on post: %s", comment_text[:50])

        # Step 1: Find and click "Comment" button to open comment box
        comment_button = page.locator('button[aria-label*="comment" i]').first
        if comment_button.count() == 0:
            # Try alternative selectors for comment button
            alt_comment_selectors = [
                'button[data-control-name*="comment"]',
                'button[aria-label*="Comment"]',
                'button:has-text("Comment")',
            ]
            for selector in alt_comment_selectors:
                alt_button = page.locator(selector).first
                if alt_button.count() > 0:
                    logger.debug("Found comment button using: %s", selector)
                    comment_button = alt_button
                    break

        if comment_button.count() > 0:
            logger.debug("Clicking comment button to open comment box")
            comment_button.click()
            time.sleep(1)  # Wait for comment box to appear
        else:
            logger.debug("Comment button not found, comment box might already be visible")

        # Step 2: Find comment input field
        comment_input = page.locator('div[contenteditable="true"]').first
        if comment_input.count() == 0:
            # Try alternative selectors
            alt_input_selectors = [
                'textarea[placeholder*="comment" i]',
                'div[class*="comment"][contenteditable="true"]',
                'div[role="textbox"]',
                'div[data-placeholder*="comment" i]',
            ]
            for selector in alt_input_selectors:
                alt_input = page.locator(selector).first
                if alt_input.count() > 0:
                    logger.debug("Found comment input using: %s", selector)
                    comment_input = alt_input
                    break

        if comment_input.count() == 0:
            logger.error("Could not find comment input field")
            return False

        logger.debug("Found comment input field, filling text")

        # Step 3: Fill comment text
        try:
            # Try fill() first
            comment_input.fill(comment_text)
            logger.debug("Comment text filled using fill()")
        except Exception:
            # Fallback: Use evaluate to set text content for contenteditable divs
            logger.debug("fill() failed, trying evaluate() method")
            comment_input.click()
            time.sleep(0.5)
            page.evaluate(
                f"""
                (element) => {{
                    element.textContent = `{comment_text.replace("`", "\\`")}`;
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                """,
                comment_input.first.element_handle(),
            )
            logger.debug("Comment text filled using evaluate()")

        time.sleep(1)  # Wait for text to be set

        # Step 4: Find submit button
        submit_button = page.locator('button[class*="comments-comment-box__submit-button"]').first
        if submit_button.count() == 0:
            # Try alternative selectors
            alt_submit_selectors = [
                'button:has-text("Comment")',
                'button[type="submit"]',
                'button[aria-label*="Post" i]',
                'button[aria-label*="Comment" i]',
                'button[data-control-name*="post_comment"]',
                'button[class*="comment-submit"]',
            ]
            for selector in alt_submit_selectors:
                alt_button = page.locator(selector).first
                if alt_button.count() > 0:
                    logger.debug("Found submit button using: %s", selector)
                    submit_button = alt_button
                    break

        if submit_button.count() == 0:
            logger.error("Could not find submit button")
            return False

        # Step 5: Submit comment
        logger.debug("Clicking submit button to post comment")
        submit_button.click()
        time.sleep(2)  # Wait for comment to be posted

        # Step 6: Verify success (check if comment box closed or comment appears)
        # For now, assume success if no error occurred
        logger.info("Comment posted successfully")
        return True

    except Exception as e:
        logger.error("Post comment failed: %s", e, exc_info=True)
        return False

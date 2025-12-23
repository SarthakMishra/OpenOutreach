# linkedin/actions/inmail.py
import logging
import re
import time

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


def _extract_first_name(page) -> str | None:
    """Extract first name from profile page."""
    try:
        # Strategy 1: Try to get name from parent <a> tag's aria-label (most reliable)
        name_link = page.locator('a[aria-label][href*="/in/"]').first
        if name_link.count() > 0:
            aria_label = name_link.get_attribute("aria-label")
            if aria_label:
                full_name = aria_label.strip()
                first_name = full_name.split()[0] if full_name else None
                if first_name:
                    logger.debug("Extracted first name from aria-label: %s", first_name)
                    return first_name

        # Strategy 2: Fall back to extracting from h1 text content
        name_selectors = [
            "h1.inline.t-24.v-align-middle.break-words",
            "h1.inline.t-24",
            "main section h1",
            "span.artdeco-hoverable-trigger h1",
        ]
        for selector in name_selectors:
            name_h1 = page.locator(selector).first
            if name_h1.count() > 0:
                full_name = name_h1.inner_text().strip()
                first_name = full_name.split()[0] if full_name else None
                if first_name:
                    logger.debug("Extracted first name from h1: %s", first_name)
                    return first_name

        logger.warning("Could not extract first name from profile")
        return None
    except Exception as e:
        logger.warning("Error extracting first name: %s", e)
        return None


def _check_inmail_credits(page) -> tuple[bool, str | None]:
    """
    Check if InMail credits are available.

    Returns:
        Tuple of (has_credits: bool, credits_text: str | None)
    """
    try:
        credits_section = page.locator(".msg-inmail-credits-display").first
        if credits_section.count() == 0:
            logger.warning("Could not find InMail credits display section")
            return False, None

        credits_text = credits_section.locator("p.t-12").first.inner_text()
        logger.debug("Credits info: %s", credits_text)

        # Check if credits are available (e.g., "Use 1 of 45 InMail credits")
        if "Use" in credits_text and "of" in credits_text:
            numbers = re.findall(r"\d+", credits_text)
            if len(numbers) >= 2:
                used = int(numbers[0])
                total = int(numbers[1])
                has_credits = used < total
                logger.info("InMail credits: %d/%d (%s)", used, total, "Available" if has_credits else "Exhausted")
                return has_credits, credits_text
        elif "No InMail credits" in credits_text or "0 of" in credits_text:
            logger.warning("No InMail credits available")
            return False, credits_text

        # Default: assume credits available if we can't parse
        logger.warning("Could not parse credits, assuming available")
        return True, credits_text

    except Exception as e:
        logger.error("Error checking credits: %s", e)
        return False, None


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
            action=lambda: page.goto(profile_url, wait_until="domcontentloaded", timeout=60000),
            expected_url_pattern="/in/",
            error_message="Failed to navigate to profile",
            to_scrape=False,
        )
        session.wait(to_scrape=False)
        time.sleep(2)  # Wait for page to fully render

        # Step 1: Extract first name from profile
        first_name = _extract_first_name(page)

        # Step 2: Find and click "Message" button
        message_button = None
        button_found = False

        # Build selectors - prioritize specific aria-label with first name
        selectors_to_try = []

        # If we have first name, use specific aria-label selector first
        if first_name:
            selectors_to_try.append(f'button[aria-label="Message {first_name}"]')
            selectors_to_try.append(f'button[aria-label*="Message {first_name}" i]')

        # Add generic selectors
        selectors_to_try.extend(
            [
                'button[aria-label*="Message" i]',
                'button:has-text("Message")',
                'button[data-control-name*="message"]',
                'button.artdeco-button:has-text("Message")',
            ]
        )

        for selector in selectors_to_try:
            try:
                locator = page.locator(selector).first
                count = locator.count()
                if count > 0:
                    message_button = locator
                    logger.debug("Found message button using: %s", selector)
                    button_found = True
                    break
            except Exception as e:
                logger.debug("Selector '%s' failed: %s", selector, e)
                continue

        if not button_found or message_button is None:
            logger.error("Could not find Message button - InMail may not be available")
            return False, InMailError.NOT_AVAILABLE

        # Step 3: Click message button using JavaScript (bypasses visibility checks)
        logger.info("Clicking Message button to open InMail modal...")
        try:
            button_element = message_button.first.element_handle()
            # Scroll first
            page.evaluate("(button) => button.scrollIntoView({ behavior: 'smooth', block: 'center' })", button_element)
            time.sleep(0.5)

            # Click using JavaScript (synchronous)
            page.evaluate(
                """
                (button) => {
                    if (button.click) {
                        button.click();
                    } else {
                        const clickEvent = new MouseEvent('click', {
                            view: window,
                            bubbles: true,
                            cancelable: true
                        });
                        button.dispatchEvent(clickEvent);
                    }
                }
                """,
                button_element,
            )
            time.sleep(3)  # Wait for modal to appear
        except Exception as e:
            logger.error("Failed to click message button: %s", e)
            return False, InMailError.UI_CHANGED

        # Step 4: Wait for InMail modal to appear
        modal = page.locator(".msg-overlay-conversation-bubble--inmail").first
        if modal.count() == 0:
            logger.error("InMail modal did not appear")
            return False, InMailError.UI_CHANGED

        logger.info("InMail modal appeared")

        # Step 5: Check for InMail credits
        has_credits, credits_text = _check_inmail_credits(page)
        if not has_credits:
            logger.error("No InMail credits available: %s", credits_text)
            return False, InMailError.NO_CREDITS

        # Step 6: Fill subject (if provided)
        if subject:
            subject_input = page.locator('input[name="subject"]').first
            if subject_input.count() == 0:
                subject_input = page.locator('input[placeholder*="Subject" i]').first

            if subject_input.count() > 0:
                logger.debug("Filling subject: %s", subject)
                subject_input.fill(subject)
                time.sleep(0.5)
            else:
                logger.warning("Could not find subject input (optional field)")

        # Step 7: Find and fill message body
        message_input = page.locator("div.msg-form__contenteditable[contenteditable='true']").first
        if message_input.count() == 0:
            # Try alternative selectors
            alt_message_selectors = [
                'div[contenteditable="true"][aria-label*="Write a message" i]',
                "div.msg-form__contenteditable",
                'div[role="textbox"][contenteditable="true"]',
            ]
            for selector in alt_message_selectors:
                alt_input = page.locator(selector).first
                if alt_input.count() > 0:
                    message_input = alt_input
                    break

        if message_input.count() == 0:
            logger.error("Could not find message input field")
            return False, InMailError.UI_CHANGED

        logger.debug("Filling message body...")
        try:
            message_input.click()
            time.sleep(0.5)
            message_input.fill(body)
        except Exception:
            # Fallback: Use evaluate to set text content for contenteditable divs
            logger.debug("fill() failed, using evaluate() method...")
            page.evaluate(
                f"""
                (element) => {{
                    element.textContent = `{body.replace("`", "\\`")}`;
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                """,
                message_input.first.element_handle(),
            )

        time.sleep(1)  # Wait for text to be set and send button to enable

        # Step 8: Find and click send button
        send_button = page.locator("button.msg-form__send-btn").first
        if send_button.count() == 0:
            # Try alternative selectors
            alt_send_selectors = [
                'button[type="submit"].msg-form__send-btn',
                'button.artdeco-button--primary:has(svg[data-test-icon="send-privately-small"])',
                'button[aria-label*="Send" i]',
            ]
            for selector in alt_send_selectors:
                alt_button = page.locator(selector).first
                if alt_button.count() > 0:
                    send_button = alt_button
                    break

        if send_button.count() == 0:
            logger.error("Could not find send button")
            return False, InMailError.UI_CHANGED

        # Check if button is disabled
        is_disabled = send_button.get_attribute("disabled") is not None
        if is_disabled:
            logger.warning("Send button is disabled, waiting...")
            time.sleep(2)
            send_button = page.locator("button.msg-form__send-btn").first
            is_disabled = send_button.get_attribute("disabled") is not None
            if is_disabled:
                logger.error("Send button still disabled after waiting")
                return False, InMailError.UI_CHANGED

        logger.info("Clicking send button to send InMail...")
        send_button.click()
        session.wait(to_scrape=False)
        time.sleep(2)  # Wait for send to complete

        logger.info("InMail sent successfully!")
        return True, None

    except Exception as e:
        logger.error("InMail failed: %s", e, exc_info=True)
        return False, InMailError.UNKNOWN

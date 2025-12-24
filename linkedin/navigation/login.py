# linkedin/navigation/login.py
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from patchright.sync_api import sync_playwright

from linkedin.conf import get_account_config
from linkedin.navigation.utils import goto_page
from linkedin.sessions.registry import AccountSessionRegistry, SessionKey

if TYPE_CHECKING:
    from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"

SELECTORS = {
    "email": "input#username",
    "password": "input#password",
    "submit": 'button[type="submit"]',
}


def playwright_login(session: "AccountSession"):
    assert session.page is not None, "page must be initialized via ensure_browser()"
    page = session.page
    config = get_account_config(session.handle)
    logger.info("\033[36mFresh login sequence starting for @%s\033[0m", session.handle)

    goto_page(
        session,
        action=lambda: page.goto(LINKEDIN_LOGIN_URL),
        expected_url_pattern="/login",
        error_message="Failed to load login page",
        to_scrape=False,
    )

    page.locator(SELECTORS["email"]).type(config["username"], delay=80)
    session.wait(to_scrape=False)
    page.locator(SELECTORS["password"]).type(config["password"], delay=80)
    session.wait(to_scrape=False)

    goto_page(
        session,
        action=lambda: page.locator(SELECTORS["submit"]).click(),
        expected_url_pattern="/feed",
        timeout=40_000,
        error_message="Login failed – no redirect to feed",
        to_scrape=False,
    )


def build_playwright(user_data_dir=None):
    """
    Build Playwright session using Chrome with persistent context.

    Following Patchright best practices:
    - Use Chrome instead of Chromium
    - Use launch_persistent_context for better stealth
    - no_viewport=True to avoid fingerprint injection
    - No custom headers/user_agent (let Chrome handle it naturally)

    Args:
        user_data_dir: Directory for persistent browser data
    """
    logger.debug("Launching Patchright with Chrome (undetected)")

    playwright = sync_playwright().start()

    # Use persistent context with Chrome (Patchright best practice)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir) if user_data_dir else None,
        channel="chrome",  # Use Google Chrome instead of Chromium
        headless=False,
        no_viewport=True,  # Avoid fingerprint injection
        slow_mo=200,
        # Do NOT add custom browser headers or user_agent - let Chrome handle it
    )

    # Patchright automatically patches CDP leaks - no stealth wrapper needed
    page = context.pages[0] if context.pages else context.new_page()
    browser = None  # Persistent context doesn't expose browser object

    return page, context, browser, playwright


def init_playwright_session(session: "AccountSession", handle: str):
    logger.info("\033[96mConfiguring browser for @%s\033[0m", handle)
    config = get_account_config(handle)
    cookie_file = Path(config["cookie_file"])

    # Use user_data_dir for persistent context (better than storage_state for stealth)
    # Store user data in a directory based on the cookie file location
    user_data_dir = cookie_file.parent / f"{handle}_user_data"

    # If we have existing cookies/storage_state, we can migrate it
    # For now, persistent context will handle cookies automatically
    if cookie_file.exists():
        logger.info("Found existing session data → %s", cookie_file)

    session.page, session.context, session.browser, session.playwright = build_playwright(user_data_dir=user_data_dir)
    page = session.page  # Capture for type narrowing

    # Set up console logging for observability
    try:
        from api_server.services.observability import setup_console_logging

        setup_console_logging(session)
    except ImportError:
        # If observability module not available, continue without it
        pass

    # Check if we're already logged in (persistent context maintains session)
    try:
        goto_page(
            session,
            action=lambda: page.goto(LINKEDIN_FEED_URL),
            expected_url_pattern="/feed",
            timeout=10_000,
            error_message="Checking existing session",
            to_scrape=False,
        )
        # Verify we're actually on /feed and not redirected to login page
        current_url = page.url
        if "/uas/login" in current_url or "/login" in current_url:
            raise RuntimeError(f"Redirected to login page: {current_url}")
        logger.info("\033[92mUsing existing session from persistent context\033[0m")
    except RuntimeError:
        # Not logged in, perform login
        logger.info("No existing session found, performing login...")
        try:
            playwright_login(session)
            # Verify login was successful - check we're on /feed and not still on login page
            session.page.wait_for_load_state("load")
            current_url = session.page.url
            if "/uas/login" in current_url or "/login" in current_url:
                raise RuntimeError(
                    f"Login failed – still on login page: {current_url}. Actions will not work without authentication."
                )
            if "/feed" not in current_url:
                raise RuntimeError(
                    f"Login failed – expected /feed but got: {current_url}. "
                    "Actions will not work without authentication."
                )
            logger.info("\033[92mLogin successful – session saved in persistent context → %s\033[0m", user_data_dir)
        except Exception as e:
            # If login fails, raise an error - actions won't work without authentication
            logger.error("\033[91mLogin failed: %s\033[0m", e)
            raise RuntimeError(
                f"Authentication failed for @{handle}. Actions will not work without authentication. Error: {e}"
            ) from e

    session.page.wait_for_load_state("load")
    logger.info("\033[1;32mBrowser awake and fully authenticated!\033[0m")


if __name__ == "__main__":
    import sys

    logging.getLogger().handlers.clear()
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    if len(sys.argv) != 2:
        logger.error("Usage: python -m linkedin.navigation.login <handle>")
        sys.exit(1)

    import uuid

    handle = sys.argv[1]
    run_id = str(uuid.uuid4())
    key = SessionKey(handle=handle, run_id=run_id)

    session, _ = AccountSessionRegistry.get_or_create_for_run(
        handle=handle,
        run_id=run_id,
    )

    session.ensure_browser()

    init_playwright_session(session=session, handle=handle)
    logger.info("Logged in! Close browser manually.")
    assert session.page is not None, "page must be initialized via ensure_browser()"
    session.page.pause()

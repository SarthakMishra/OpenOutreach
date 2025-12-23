# linkedin/navigation/login.py
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from linkedin.conf import get_account_config
from linkedin.navigation.utils import goto_page
from linkedin.sessions.account import AccountSession
from linkedin.sessions.registry import AccountSessionRegistry, SessionKey

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


def build_playwright(storage_state=None):
    logger.debug("Launching Playwright")
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False, slow_mo=200)
    context = browser.new_context(storage_state=storage_state)
    Stealth().apply_stealth_sync(context)
    page = context.new_page()
    return page, context, browser, playwright


def init_playwright_session(session: "AccountSession", handle: str):
    logger.info("\033[96mConfiguring browser for @%s\033[0m", handle)
    config = get_account_config(handle)
    state_file = Path(config["cookie_file"])

    storage_state = str(state_file) if state_file.exists() else None
    if storage_state:
        logger.info("Devouring saved cookies → %s", state_file)

    session.page, session.context, session.browser, session.playwright = build_playwright(storage_state=storage_state)
    page = session.page  # Capture for type narrowing

    if not storage_state:
        playwright_login(session)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        session.context.storage_state(path=str(state_file))
        logger.info("\033[92mLogin successful – session saved → %s\033[0m", state_file)
    else:
        goto_page(
            session,
            action=lambda: page.goto(LINKEDIN_FEED_URL),
            expected_url_pattern="/feed",
            timeout=30_000,
            error_message="Saved session invalid",
            to_scrape=False,
        )

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

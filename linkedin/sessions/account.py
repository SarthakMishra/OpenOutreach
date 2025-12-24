# linkedin/sessions/account.py
from __future__ import annotations

import logging
import random
import time
from typing import TYPE_CHECKING

from linkedin.api.client import PlaywrightLinkedinAPI
from linkedin.conf import (
    MAX_DELAY,
    MIN_DELAY,
    OPPORTUNISTIC_SCRAPING,
    get_account_config,
)
from linkedin.navigation.login import init_playwright_session
from linkedin.navigation.throttle import determine_batch_size
from linkedin.sessions.registry import SessionKey

if TYPE_CHECKING:
    from patchright.sync_api import Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)

MIN_API_DELAY = 0.250
MAX_API_DELAY = 0.500


def human_delay(min, max):
    delay = random.uniform(min, max)
    logger.debug(f"Pause: {delay:.2f}s")
    time.sleep(delay)


class AccountSession:
    def __init__(self, key: "SessionKey"):
        from linkedin.db.engine import Database

        self.key = key
        self.handle = key.handle
        self.run_id = key.run_id

        self.account_cfg = get_account_config(self.handle)
        self.db = Database.from_handle(self.handle)
        self.db_session = self.db.get_session()  # one long-lived session per account run

        # Playwright objects – created on first access or after crash
        self.page: Page | None = None
        self.context: BrowserContext | None = None
        self.browser: Browser | None = None
        self.playwright: Playwright | None = None

    def ensure_browser(self):
        """Launch or recover browser + login if needed. Call before using .page"""
        if not self.page or self.page.is_closed():
            logger.info(
                "Launching/recovering browser for %s (run: %s)",
                self.handle,
                self.run_id[:8],
            )
            init_playwright_session(session=self, handle=self.handle)

    def wait(self, min_delay=MIN_DELAY, max_delay=MAX_DELAY, to_scrape=OPPORTUNISTIC_SCRAPING):
        assert self.page is not None, "page must be initialized via ensure_browser()"
        if not to_scrape:
            human_delay(min_delay, max_delay)
            self.page.wait_for_load_state("load")
            return

        from linkedin.db.profiles import get_next_url_to_scrape

        logger.debug(f"Pausing: {MAX_DELAY}s")
        amount_to_scrape = determine_batch_size(self)

        urls = get_next_url_to_scrape(self, limit=amount_to_scrape)
        if not urls:
            human_delay(min_delay, max_delay)
            self.page.wait_for_load_state("load")
            return

        from linkedin.db.profiles import save_scraped_profile

        min_api_delay = max(min_delay / len(urls), MIN_API_DELAY)
        max_api_delay = max(max_delay / len(urls), MAX_API_DELAY)
        api = PlaywrightLinkedinAPI(session=self)

        for url in urls:
            human_delay(min_api_delay, max_api_delay)
            profile, data = api.get_profile(profile_url=url)
            if profile:
                save_scraped_profile(self, url, profile, data)
                logger.debug(f"Auto-scraped → {profile.get('full_name')} – {url}")

    def close(self):
        if self.context:
            try:
                self.context.close()
                if self.browser:
                    self.browser.close()
                if self.playwright:
                    self.playwright.stop()
                logger.info("Browser closed gracefully (%s)", self.handle)
            except Exception as e:
                logger.debug("Error closing browser: %s", e)
            finally:
                self.page = self.context = self.browser = self.playwright = None

        self.db.close()
        logger.info("Account session closed → %s", self.key)

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"<AccountSession {self.key}>"

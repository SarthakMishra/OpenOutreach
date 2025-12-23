# linkedin/sessions/registry.py
from __future__ import annotations

import logging
from typing import NamedTuple, Optional

from linkedin.sessions.account import AccountSession

logger = logging.getLogger(__name__)


class AccountSessionRegistry:
    _instances: dict["SessionKey", "AccountSession"] = {}

    @classmethod
    def get_or_create(
        cls,
        handle: str,
        run_id: str,
    ) -> "AccountSession":
        from .account import AccountSession

        key = SessionKey(handle, run_id)

        if key not in cls._instances:
            cls._instances[key] = AccountSession(key)
            logger.info("Created new account session → %s", key)
        else:
            logger.debug("Reusing existing account session → %s", key)

        return cls._instances[key]

    @classmethod
    def get_or_create_for_run(
        cls,
        handle: str,
        run_id: str,
    ) -> tuple["AccountSession", "SessionKey"]:
        """Convenience method that returns both session and key."""
        session = cls.get_or_create(handle, run_id)
        key = SessionKey(handle=handle, run_id=run_id)
        return session, key

    @classmethod
    def get_existing(cls, key: SessionKey) -> Optional["AccountSession"]:
        return cls._instances.get(key)

    @classmethod
    def clear_all(cls):
        for session in list(cls._instances.values()):
            session.close()
        cls._instances.clear()


class SessionKey(NamedTuple):
    handle: str
    run_id: str

    def __str__(self) -> str:
        return f"{self.handle}::{self.run_id}"

    def as_filename_safe(self) -> str:
        return f"{self.handle}--{self.run_id}"


# ——————————————————————————————————————————————————————————————
if __name__ == "__main__":
    import logging

    logging.getLogger().handlers.clear()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )

    import sys

    if len(sys.argv) != 2:
        logger.error("Usage: python -m linkedin.sessions.registry <handle>")
        sys.exit(1)

    import uuid

    handle = sys.argv[1]
    run_id = str(uuid.uuid4())
    session, _ = AccountSessionRegistry.get_or_create_for_run(
        handle=handle,
        run_id=run_id,
    )

    session.ensure_browser()  # ← this does everything

    logger.info("\nSession ready! Use session.page, session.context, etc.")
    logger.info("   Handle   : %s", session.handle)
    logger.info("   Run ID   : %s", session.run_id)
    logger.info("   Key      : %s", session.key)
    logger.info("   Browser survives crash/reboot/Ctrl+C\n")

    assert session.page is not None, "page must be initialized via ensure_browser()"
    session.page.pause()  # keeps browser open for manual testing
